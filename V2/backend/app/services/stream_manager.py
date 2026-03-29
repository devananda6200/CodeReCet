import asyncio
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.core.config import Settings
from app.models.schemas import (
    AddStreamRequest,
    SummaryMetrics,
    StreamMetrics,
    StreamRecord,
    StreamRuntimeStatus,
    StreamSafetyStatus,
    StreamSourceType,
)
from app.pipeline.frame_pipeline import FramePipeline
from app.safety.rule_engine import SafetyRuleEngine
from app.services.alert_store import AlertStore
from app.services.config_store import ConfigStore
from app.services.model_service import ModelService
from app.services.zone_store import ZoneStore
from app.utils.system import get_process_memory_mb, get_system_cpu_percent

logger = logging.getLogger(__name__)


@dataclass
class ManagedStream:
    record: StreamRecord
    task: asyncio.Task | None = None
    pipeline: FramePipeline | None = None
    latest_frame: bytes = b""
    frame_version: int = 0


class StreamManager:
    def __init__(
        self,
        settings: Settings,
        config_store: ConfigStore,
        alert_store: AlertStore,
        zone_store: ZoneStore,
        model_service: ModelService,
        safety_engine: SafetyRuleEngine,
    ) -> None:
        self.settings = settings
        self.config_store = config_store
        self.alert_store = alert_store
        self.zone_store = zone_store
        self.model_service = model_service
        self.safety_engine = safety_engine
        self._streams: dict[str, ManagedStream] = {}
        self._lock = asyncio.Lock()

    async def seed_demo_streams(self) -> None:
        if not self.settings.demo_mode:
            return
        for index in range(self.settings.demo_seed_streams):
            stream = await self.add_stream(
                AddStreamRequest(
                    name=f"Demo Camera {index + 1}",
                    source_type=StreamSourceType.demo,
                    source_uri=f"demo://camera-{index + 1}",
                )
            )
            if index < 2:
                await self.start_stream(stream.id)

    async def shutdown(self) -> None:
        for stream in list(self._streams.values()):
            if stream.task:
                stream.task.cancel()
        tasks = [stream.task for stream in self._streams.values() if stream.task]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def add_stream(self, payload: AddStreamRequest) -> StreamRecord:
        stream_id = uuid.uuid4().hex[:12]
        normalized_source_uri = self._normalize_source_uri(payload.source_type, payload.source_uri)
        record = StreamRecord(
            id=stream_id,
            name=payload.name,
            source_type=payload.source_type,
            source_uri=normalized_source_uri,
            runtime_status=StreamRuntimeStatus.stopped,
            model_backend=self.config_store.get().backend,
            preview_url=f"/streams/{stream_id}/frame",
        )
        async with self._lock:
            self._streams[stream_id] = ManagedStream(record=record)
        return record

    async def add_uploaded_stream(self, file: UploadFile) -> StreamRecord:
        extension = Path(file.filename or "upload.mp4").suffix or ".mp4"
        target_path = self.settings.upload_dir / f"{uuid.uuid4().hex}{extension}"
        async with aiofiles.open(target_path, "wb") as target:
            while chunk := await file.read(1024 * 1024):
                await target.write(chunk)
        display_name = (file.filename or "Uploaded video")[:80]
        return await self.add_stream(
            AddStreamRequest(
                name=display_name,
                source_type=StreamSourceType.file,
                source_uri=str(target_path),
            )
        )

    async def start_stream(self, stream_id: str) -> None:
        stream = self._streams.get(stream_id)
        if stream is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
        if stream.task and not stream.task.done():
            return
        stream.record.runtime_status = StreamRuntimeStatus.starting
        stream.record.model_backend = self.config_store.get().backend
        stream.pipeline = FramePipeline(
            stream_id=stream.record.id,
            stream_name=stream.record.name,
            source_type=stream.record.source_type.value,
            source_uri=stream.record.source_uri,
            model_service=self.model_service,
            safety_engine=self.safety_engine,
        )
        stream.task = asyncio.create_task(self._run_stream(stream_id))

    async def stop_stream(self, stream_id: str) -> None:
        stream = self._streams.get(stream_id)
        if stream is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
        if stream.task:
            stream.task.cancel()
            await asyncio.gather(stream.task, return_exceptions=True)
        stream.task = None
        if stream.pipeline:
            stream.pipeline.close()
            stream.pipeline = None
        stream.record.runtime_status = StreamRuntimeStatus.stopped
        stream.record.safety_status = StreamSafetyStatus.safe
        stream.record.active_alerts = 0
        stream.record.metrics.fps = 0
        stream.record.metrics.inference_latency_ms = 0
        stream.record.metrics.end_to_end_latency_ms = 0
        stream.record.last_seen_at = datetime.now(timezone.utc)

    def list_streams(self) -> list[StreamRecord]:
        records: list[StreamRecord] = []
        for item in self._streams.values():
            record = item.record.model_copy(deep=True)
            if item.frame_version:
                record.preview_url = f"/streams/{record.id}/frame?v={item.frame_version}"
            records.append(record)
        return records

    def get_metrics(self, stream_id: str) -> StreamMetrics | None:
        stream = self._streams.get(stream_id)
        return stream.record.metrics.model_copy(deep=True) if stream else None

    def count_running(self) -> int:
        return sum(1 for stream in self._streams.values() if stream.record.runtime_status == StreamRuntimeStatus.running)

    def count_total(self) -> int:
        return len(self._streams)

    def get_latest_frame(self, stream_id: str) -> bytes | None:
        stream = self._streams.get(stream_id)
        if stream is None or not stream.latest_frame:
            return None
        return stream.latest_frame

    def get_summary_metrics(self) -> SummaryMetrics:
        streams = list(self._streams.values())
        if streams:
            avg_fps = sum(item.record.metrics.fps for item in streams) / len(streams)
            avg_latency = sum(item.record.metrics.end_to_end_latency_ms for item in streams) / len(streams)
            avg_cpu = sum(item.record.metrics.cpu_percent for item in streams) / len(streams)
        else:
            avg_fps = 0.0
            avg_latency = 0.0
            avg_cpu = 0.0

        backends = sorted({item.record.model_backend.value for item in streams})
        active_hazard_streams = sum(1 for item in streams if item.record.safety_status != StreamSafetyStatus.safe)

        return SummaryMetrics(
            active_streams=self.count_running(),
            total_streams=self.count_total(),
            alerts_in_memory=len(self.alert_store.list_alerts(limit=250)),
            avg_fps=round(avg_fps, 2),
            avg_latency_ms=round(avg_latency, 1),
            avg_cpu_percent=round(avg_cpu, 1),
            process_memory_mb=round(get_process_memory_mb(), 1),
            active_hazard_streams=active_hazard_streams,
            backends_in_use=backends,
        )

    async def _run_stream(self, stream_id: str) -> None:
        stream = self._streams[stream_id]
        consecutive_failures = 0
        stream.record.runtime_status = StreamRuntimeStatus.starting
        try:
            while True:
                loop_started = perf_counter()
                runtime_config = self.config_store.get()
                stream.record.model_backend = runtime_config.backend
                stream.record.last_seen_at = datetime.now(timezone.utc)
                if stream.pipeline is None:
                    raise RuntimeError("Pipeline not initialized for stream")

                zone = self.zone_store.get_zone(stream.record.id)
                try:
                    result = await asyncio.to_thread(stream.pipeline.step, runtime_config, zone)
                    consecutive_failures = 0
                except RuntimeError as exc:
                    consecutive_failures += 1
                    stream.record.runtime_status = StreamRuntimeStatus.starting
                    if consecutive_failures >= 15:
                        stream.record.runtime_status = StreamRuntimeStatus.error
                        logger.exception("Stream %s failed after retries", stream.record.id)
                        return
                    logger.warning(
                        "Stream %s frame read retry %s/15: %s",
                        stream.record.id,
                        consecutive_failures,
                        exc,
                    )
                    await asyncio.sleep(0.5)
                    continue
                stream.record.runtime_status = StreamRuntimeStatus.running
                metrics = result.metrics.model_copy(
                    update={
                        "cpu_percent": round(get_system_cpu_percent(), 1),
                        "memory_mb": round(get_process_memory_mb(), 1),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                stream.record.metrics = metrics
                stream.record.safety_status = result.safety_status
                stream.record.active_alerts = 0 if result.safety_status == StreamSafetyStatus.safe else 1
                stream.latest_frame = result.frame_bytes
                stream.frame_version += 1
                for alert in result.alerts:
                    self.alert_store.add_alert(alert)

                target_interval_seconds = 1 / max(stream.pipeline.config.target_fps, 1)
                elapsed_seconds = perf_counter() - loop_started
                sleep_seconds = max(0.0, target_interval_seconds - elapsed_seconds)
                await asyncio.sleep(sleep_seconds)
        except asyncio.CancelledError:
            stream.record.runtime_status = StreamRuntimeStatus.stopped
            raise
        except Exception:
            stream.record.runtime_status = StreamRuntimeStatus.error
            logger.exception("Unexpected stream failure for %s", stream.record.id)

    def _normalize_source_uri(self, source_type: StreamSourceType, source_uri: str | None) -> str | None:
        if source_uri is None:
            return None
        if source_type != StreamSourceType.http:
            return source_uri

        normalized_source_uri = source_uri.strip()
        parsed = urlparse(normalized_source_uri)
        if not parsed.scheme or not parsed.netloc:
            return normalized_source_uri

        # Recover from common typo: 192.168.1.50.8080 -> 192.168.1.50:8080
        if ":" not in parsed.netloc:
            typo_match = re.match(r"^(\d+\.\d+\.\d+\.\d+)\.(\d{2,5})$", parsed.netloc)
            if typo_match:
                host = typo_match.group(1)
                port = typo_match.group(2)
                normalized_source_uri = f"{parsed.scheme}://{host}:{port}{parsed.path or ''}"
                if parsed.query:
                    normalized_source_uri += f"?{parsed.query}"
                parsed = urlparse(normalized_source_uri)

        if parsed.path and parsed.path != "/":
            return normalized_source_uri

        # Common Android IP Webcam default MJPEG endpoint.
        return normalized_source_uri.rstrip("/") + "/video"
