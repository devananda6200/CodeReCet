from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import cv2
import numpy as np

from app.models.schemas import AlertRecord, DetectionRecord, PolygonZone, RuntimeConfig, StreamMetrics, StreamSafetyStatus
from app.safety.rule_engine import SafetyRuleEngine
from app.services.model_service import ModelService
from app.tracking.centroid_tracker import CentroidTracker


@dataclass
class PipelineResult:
    frame_bytes: bytes
    metrics: StreamMetrics
    safety_status: StreamSafetyStatus
    alerts: list[AlertRecord]


@dataclass
class FramePipelineConfig:
    target_fps: int = 12
    jpeg_quality: int = 65
    max_buffer_drains: int = 12


class FramePipeline:
    def __init__(
        self,
        *,
        stream_id: str,
        stream_name: str,
        source_type: str,
        source_uri: str | None,
        model_service: ModelService,
        safety_engine: SafetyRuleEngine,
        config: FramePipelineConfig | None = None,
    ) -> None:
        self.stream_id = stream_id
        self.stream_name = stream_name
        self.source_type = source_type
        self.source_uri = source_uri
        self.model_service = model_service
        self.safety_engine = safety_engine
        self.config = config or FramePipelineConfig()
        self.frame_index = 0
        self.tracker = CentroidTracker()
        self.capture: cv2.VideoCapture | None = None
        self.last_frame_shape = (720, 1280)
        self._last_detections: list[DetectionRecord] = []
        self._last_safety_status = StreamSafetyStatus.safe
        self._dynamic_skip_rate = 1

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def step(self, runtime_config: RuntimeConfig, zone: PolygonZone | None) -> PipelineResult:
        started = perf_counter()
        frame, decode_latency_ms, source_mode = self._next_frame()
        self.frame_index += 1

        effective_skip_rate = self._effective_skip_rate(runtime_config)
        should_run_inference = (
            not runtime_config.smart_frame_skip
            or self.frame_index % effective_skip_rate == 0
            or not self._last_detections
        )

        if should_run_inference:
            detections, inference_latency_ms, source_mode = self.model_service.predict(
                frame,
                runtime_config,
                self.frame_index,
                stream_seed=abs(hash(self.stream_id)) % 97,
            )
            detections = self.tracker.update(detections)
            self._last_detections = detections
        else:
            detections = self.tracker.project()
            if not detections:
                detections = self._last_detections
            inference_latency_ms = 0.2

        safety_status, alerts, alert_latency_ms = self.safety_engine.evaluate(
            stream_id=self.stream_id,
            stream_name=self.stream_name,
            detections=detections,
            zone=zone,
            config=runtime_config,
        )
        self._last_safety_status = safety_status

        annotated = self._annotate_frame(frame, detections, safety_status, zone)
        success, buffer = cv2.imencode(
            ".jpg",
            annotated,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.config.jpeg_quality],
        )
        frame_bytes = buffer.tobytes() if success else b""
        end_to_end_latency_ms = (perf_counter() - started) * 1000

        metrics = StreamMetrics(
            fps=round(1000 / max(end_to_end_latency_ms, 1), 2),
            inference_latency_ms=round(inference_latency_ms, 1),
            decode_latency_ms=round(decode_latency_ms, 1),
            end_to_end_latency_ms=round(end_to_end_latency_ms, 1),
            alert_latency_ms=round(alert_latency_ms, 1),
            current_resolution=f"{annotated.shape[1]}x{annotated.shape[0]}",
            frame_skip_rate=effective_skip_rate,
            adaptive_resolution_enabled=runtime_config.adaptive_resolution,
            tracking_mode="centroid-lite",
            processed_frames=self.frame_index,
            detection_count=len(detections),
            mode=source_mode,
        )
        self._update_dynamic_skip(runtime_config, end_to_end_latency_ms)
        return PipelineResult(
            frame_bytes=frame_bytes,
            metrics=metrics,
            safety_status=safety_status,
            alerts=alerts,
        )

    def _next_frame(self) -> tuple[np.ndarray, float, str]:
        started = perf_counter()
        if self.source_type == "demo":
            return self._demo_frame(), (perf_counter() - started) * 1000, "mock"

        if self.capture is None:
            self.capture = self._open_capture()

        if self.capture is not None:
            # Drain buffered frames aggressively and keep only the newest one.
            success, frame = self._read_latest_frame(self.capture)
            if success and frame is not None:
                self.last_frame_shape = frame.shape[:2]
                return frame, (perf_counter() - started) * 1000, "live"
            # Attempt one transparent reconnect on dropped network/live streams.
            self.capture.release()
            self.capture = self._open_capture()
            if self.capture is not None:
                success, frame = self._read_latest_frame(self.capture)
                if success and frame is not None:
                    self.last_frame_shape = frame.shape[:2]
                    return frame, (perf_counter() - started) * 1000, "live"

        raise RuntimeError(f"Unable to read live frame for stream source: {self.source_uri or self.source_type}")

    def _open_capture(self) -> cv2.VideoCapture | None:
        source: int | str | None
        if self.source_type == "webcam":
            source = int(self.source_uri or "0")
        else:
            source = self.source_uri
        if source is None:
            return None

        if isinstance(source, str) and self.source_type == "http":
            candidates = [
                source,
                source.rstrip("/") + "/video",
                source.rstrip("/") + "/videofeed",
                source.rstrip("/") + "/mjpeg",
            ]
            for candidate in dict.fromkeys(candidates):
                capture = cv2.VideoCapture(candidate)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if capture.isOpened():
                    self.source_uri = candidate
                    return capture
                capture.release()
            return None

        capture = cv2.VideoCapture(source)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return capture if capture.isOpened() else None

    def _read_latest_frame(self, capture: cv2.VideoCapture) -> tuple[bool, np.ndarray | None]:
        """Read the most recent frame available to minimize transport and decode lag."""
        grabbed = False
        for _ in range(max(self.config.max_buffer_drains, 1)):
            if not capture.grab():
                break
            grabbed = True

        if grabbed:
            return capture.retrieve()

        return capture.read()

    def _effective_skip_rate(self, runtime_config: RuntimeConfig) -> int:
        base_skip = runtime_config.frame_skip_rate if runtime_config.smart_frame_skip else 1
        return max(1, base_skip, self._dynamic_skip_rate)

    def _update_dynamic_skip(self, runtime_config: RuntimeConfig, end_to_end_latency_ms: float) -> None:
        if not runtime_config.smart_frame_skip:
            self._dynamic_skip_rate = 1
            return

        base_skip = max(1, runtime_config.frame_skip_rate)
        max_skip = 8

        if end_to_end_latency_ms > 130:
            self._dynamic_skip_rate = min(max_skip, self._dynamic_skip_rate + 1)
            return
        if end_to_end_latency_ms < 75:
            self._dynamic_skip_rate = max(base_skip, self._dynamic_skip_rate - 1)
            return

        self._dynamic_skip_rate = max(base_skip, self._dynamic_skip_rate)

    def _demo_frame(self) -> np.ndarray:
        height, width = self.last_frame_shape
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        gradient = np.linspace(30, 110, width, dtype=np.uint8)
        frame[:, :, 0] = gradient
        frame[:, :, 1] = gradient[::-1] // 2
        frame[:, :, 2] = 40
        cv2.putText(
            frame,
            f"{self.stream_name} | frame {self.frame_index}",
            (40, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            (240, 240, 240),
            2,
            cv2.LINE_AA,
        )
        cv2.rectangle(frame, (40, 90), (width - 40, height - 60), (255, 255, 255), 2)
        return frame

    def _annotate_frame(
        self,
        frame: np.ndarray,
        detections: list[DetectionRecord],
        safety_status: StreamSafetyStatus,
        zone: PolygonZone | None,
    ) -> np.ndarray:
        annotated = frame.copy()
        if zone:
            points = np.array([[int(point.x), int(point.y)] for point in zone.points], dtype=np.int32)
            cv2.polylines(annotated, [points], isClosed=True, color=(0, 80, 255), thickness=2)

        for detection in detections:
            x1, y1, x2, y2 = [int(value) for value in detection.bbox]
            color = (34, 197, 94)
            if "machine" in detection.class_name.lower():
                color = (255, 191, 0)
            if safety_status != StreamSafetyStatus.safe and "person" in detection.class_name.lower():
                color = (0, 75, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{detection.class_name} #{detection.track_id or 0} {detection.confidence:.2f}"
            cv2.putText(
                annotated,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA,
            )

        cv2.putText(
            annotated,
            safety_status.value,
            (30, annotated.shape[0] - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return annotated
