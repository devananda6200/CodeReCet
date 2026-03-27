"""
stream_manager.py — Multi-stream pipeline orchestrator.

Manages the full lifecycle of concurrent video streams:
decode → preprocess → infer/track → postprocess → compliance → alert.

Features:
- Frame skipping with tracker-only prediction on skipped frames
- Adaptive resolution control based on running FPS
- Bounded queues and threaded decode
- Up to max_concurrent simultaneous streams
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional

import numpy as np

from app.alert_manager import AlertManager
from app.compliance_checker import ComplianceChecker
from app.config import settings
from app.decoder import FrameDecoder
from app.inference_engine import InferenceBackend, create_engine
from app.metrics import metrics_collector
from app.models import (
    ComplianceResult,
    Detection,
    FramePacket,
    StreamInfo,
    StreamState,
)
from app.postprocessor import Postprocessor
from app.preprocessor import Preprocessor
from app.tracker import IoUTracker

logger = logging.getLogger(__name__)


class StreamPipeline:
    """Pipeline for a single video stream."""

    def __init__(
        self,
        stream_id: str,
        name: str,
        source: str | int,
        engine: InferenceBackend,
        on_result: Optional[Callable[[FramePacket], None]] = None,
    ):
        self.stream_id = stream_id
        self.source = source
        self.info = StreamInfo(stream_id=stream_id, name=name, source=str(source))

        # Shared inference engine (thread-safe for single-stream sequential use)
        self._engine = engine
        self._on_result = on_result

        # Per-stream components
        self._decoder = FrameDecoder(stream_id, source)
        self._preprocessor = Preprocessor()
        self._postprocessor = Postprocessor()
        self._tracker = IoUTracker()
        self._compliance = ComplianceChecker()
        self._alerts = AlertManager()

        # Adaptive resolution state
        self._current_tier_idx = 0
        self._resolution_tiers = settings.resolution.tiers
        self._fps_history: list[float] = []
        self._last_resolution_eval = time.time()

        # Control
        self._running = threading.Event()
        self._frame_skip = settings.pipeline.frame_skip
        self.latest_frame_jpg = b""

    # ── Lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        self._decoder.start()
        self._running.set()
        self.info.state = StreamState.RUNNING
        logger.info("[%s] Pipeline started", self.stream_id)

    def stop(self) -> None:
        self._running.clear()
        self._decoder.stop()
        self.info.state = StreamState.STOPPED
        metrics_collector.remove_stream(self.stream_id)
        logger.info("[%s] Pipeline stopped", self.stream_id)

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    # ── Main loop (runs in thread pool) ───────────────────────────

    def run(self) -> None:
        """
        Main pipeline loop. Designed to run inside a thread.

        Continuously dequeues frames, processes them through the
        pipeline stages, and pushes results downstream.
        """
        self.start()
        frame_counter = 0

        try:
            while self._running.is_set():
                packet = self._decoder.get_frame(timeout=0.1)
                if packet is None:
                    # Check if decoder stopped (e.g. end of video)
                    if not self._decoder.is_running:
                        logger.info("[%s] Decoder finished, stopping pipeline", self.stream_id)
                        break
                    continue

                frame_counter += 1
                is_infer_frame = (frame_counter % self._frame_skip) == 1 or self._frame_skip <= 1
                packet.is_inference_frame = is_infer_frame

                # Record queue length
                metrics_collector.record_queue_length(
                    self.stream_id, self._decoder.queue_length
                )

                try:
                    self._process_frame(packet, is_infer_frame)
                except Exception as e:
                    logger.error("[%s] Pipeline error: %s", self.stream_id, e, exc_info=True)
                    self.info.error_message = str(e)

                # Adaptive resolution check
                self._maybe_adjust_resolution()

        except Exception as e:
            logger.error("[%s] Fatal pipeline error: %s", self.stream_id, e, exc_info=True)
            self.info.state = StreamState.ERROR
            self.info.error_message = str(e)
        finally:
            self.stop()

    # ── Per-frame processing ──────────────────────────────────────

    def _process_frame(self, packet: FramePacket, do_inference: bool) -> None:
        """Run a single frame through all pipeline stages."""

        # 1. Preprocess
        t0 = time.time()
        
        # Save exact JPEG clone for MJPEG streaming
        import cv2
        _, buffer = cv2.imencode('.jpg', packet.frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        self.latest_frame_jpg = buffer.tobytes()

        target_w = self._resolution_tiers[self._current_tier_idx]
        tensor, meta = self._preprocessor.preprocess(
            packet.frame, target_width=target_w
        )
        t_preprocess = time.time() - t0
        metrics_collector.record_stage_latency(self.stream_id, "preprocess", t_preprocess)
        packet.stage_timings["preprocess"] = t_preprocess

        if do_inference:
            # 2. Inference
            t0 = time.time()
            raw_output = self._engine.infer(tensor)
            t_infer = time.time() - t0
            metrics_collector.record_stage_latency(self.stream_id, "inference", t_infer)
            packet.stage_timings["inference"] = t_infer

            # 3. Postprocess
            t0 = time.time()
            detections = self._postprocessor.process(raw_output, meta)
            t_post = time.time() - t0
            metrics_collector.record_stage_latency(self.stream_id, "postprocess", t_post)
            packet.stage_timings["postprocess"] = t_post

            # 4. Tracking (update with new detections)
            t0 = time.time()
            tracked = self._tracker.update(detections)
            t_track = time.time() - t0
            metrics_collector.record_stage_latency(self.stream_id, "tracking", t_track)
            packet.stage_timings["tracking"] = t_track

        else:
            # Skipped frame — tracker prediction only
            t0 = time.time()
            tracked = self._tracker.predict()
            t_track = time.time() - t0
            metrics_collector.record_stage_latency(self.stream_id, "tracking", t_track)
            packet.stage_timings["tracking"] = t_track
            metrics_collector.record_skip(self.stream_id)
            self.info.frames_skipped += 1

        packet.detections = tracked

        # 5. Compliance check
        t0 = time.time()
        compliance_results = self._compliance.check(tracked)
        t_compliance = time.time() - t0
        metrics_collector.record_stage_latency(self.stream_id, "compliance", t_compliance)
        packet.stage_timings["compliance"] = t_compliance
        packet.compliance_results = compliance_results

        # 6. Alert generation
        t0 = time.time()
        alerts = self._alerts.process(self.stream_id, compliance_results)
        t_alert = time.time() - t0
        metrics_collector.record_stage_latency(self.stream_id, "alerts", t_alert)
        packet.stage_timings["alerts"] = t_alert
        packet.alerts = alerts

        # Record frame completion
        metrics_collector.record_frame(self.stream_id)
        self.info.frames_processed += 1
        self.info.fps = metrics_collector.get_fps(self.stream_id)

        # Deliver to callback (e.g. WebSocket broadcast)
        if self._on_result:
            self._on_result(packet)

    # ── Adaptive resolution ───────────────────────────────────────

    def _maybe_adjust_resolution(self) -> None:
        """Adjust resolution tier based on current FPS."""
        now = time.time()
        if now - self._last_resolution_eval < settings.resolution.eval_window_sec:
            return

        self._last_resolution_eval = now
        fps = metrics_collector.get_fps(self.stream_id)

        if fps < settings.resolution.fps_low_threshold:
            # Drop down one tier
            if self._current_tier_idx < len(self._resolution_tiers) - 1:
                self._current_tier_idx += 1
                new_w = self._resolution_tiers[self._current_tier_idx]
                self._decoder.set_target_width(new_w)
                logger.warning(
                    "[%s] FPS=%.1f below threshold, dropping resolution to tier %d (%dpx)",
                    self.stream_id, fps, self._current_tier_idx, new_w,
                )
                self.info.current_resolution_tier = self._current_tier_idx

        elif fps > settings.resolution.fps_high_threshold:
            # Step up one tier
            if self._current_tier_idx > 0:
                self._current_tier_idx -= 1
                new_w = self._resolution_tiers[self._current_tier_idx]
                self._decoder.set_target_width(new_w)
                logger.info(
                    "[%s] FPS=%.1f above threshold, restoring resolution to tier %d (%dpx)",
                    self.stream_id, fps, self._current_tier_idx, new_w,
                )
                self.info.current_resolution_tier = self._current_tier_idx


# ═════════════════════════════════════════════════════════════════════
# Stream Manager — manages all active pipelines
# ═════════════════════════════════════════════════════════════════════

class StreamManager:
    """
    Top-level manager for concurrent video stream pipelines.

    Handles stream add/remove and dispatches pipeline loops
    into a bounded thread pool.
    """

    def __init__(self) -> None:
        self._pipelines: Dict[str, StreamPipeline] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=settings.streams.max_concurrent,
            thread_name_prefix="stream-pipeline",
        )
        self._engine: Optional[InferenceBackend] = None
        self._result_callback: Optional[Callable[[FramePacket], None]] = None
        self._started = False

    # ── Lifecycle ─────────────────────────────────────────────────

    def startup(self, result_callback: Optional[Callable[[FramePacket], None]] = None) -> None:
        """Register the result callback. Model loading is deferred to first stream add."""
        self._result_callback = result_callback
        self._started = True
        logger.info("StreamManager ready (model will load on first stream add)")

    def _ensure_engine(self) -> None:
        """Lazily load the inference engine on first use (thread-safe)."""
        if self._engine is not None:
            return
        with self._lock:
            if self._engine is not None:
                return  # Double-check after acquiring lock
            logger.info("Loading inference engine…")
            self._engine = create_engine()
            logger.info("Inference engine loaded successfully")

    def shutdown(self) -> None:
        """Stop all streams and release resources."""
        with self._lock:
            for sid in list(self._pipelines):
                self._pipelines[sid].stop()
            self._pipelines.clear()
        self._executor.shutdown(wait=False)
        logger.info("StreamManager shut down")

    # ── Stream CRUD ───────────────────────────────────────────────

    def add_stream(self, stream_id: str, source: str | int, name: str = "") -> StreamInfo:
        """Add a new video stream and start processing."""
        # Ensure inference engine is loaded (lazy init)
        self._ensure_engine()

        with self._lock:
            if stream_id in self._pipelines:
                raise ValueError(f"Stream '{stream_id}' already exists")
            if len(self._pipelines) >= settings.streams.max_concurrent:
                raise RuntimeError(
                    f"Maximum concurrent streams ({settings.streams.max_concurrent}) reached"
                )

            if not name:
                name = stream_id

            pipeline = StreamPipeline(
                stream_id=stream_id,
                name=name,
                source=source,
                engine=self._engine,
                on_result=self._result_callback,
            )
            self._pipelines[stream_id] = pipeline

        # Submit pipeline to thread pool
        self._executor.submit(pipeline.run)
        logger.info("Added stream '%s' → %s", stream_id, source)
        return pipeline.info

    def remove_stream(self, stream_id: str) -> bool:
        """Stop and remove a stream."""
        with self._lock:
            pipeline = self._pipelines.pop(stream_id, None)
        if pipeline is None:
            return False
        pipeline.stop()
        logger.info("Removed stream '%s'", stream_id)
        return True

    def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        with self._lock:
            p = self._pipelines.get(stream_id)
            return p.info if p else None

    def list_streams(self) -> List[StreamInfo]:
        with self._lock:
            return [p.info for p in self._pipelines.values()]

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._pipelines)


# ── Singleton ─────────────────────────────────────────────────────
stream_manager = StreamManager()
