"""
decoder.py — Frame capture and decode from video sources.

Each stream gets a dedicated capture thread that reads frames from
webcam, video file, or RTSP and pushes them into a bounded queue.
Old frames are dropped if the consumer cannot keep up.
"""

from __future__ import annotations

import logging
import threading
import time
from queue import Full, Queue
from typing import Optional

import cv2
import numpy as np

from app.config import settings
from app.models import FramePacket

logger = logging.getLogger(__name__)


class FrameDecoder:
    """
    Threaded frame decoder for a single video source.

    Captures frames in a background thread and pushes them into a
    bounded queue. If the queue is full, the oldest frame is discarded
    to keep latency low.
    """

    def __init__(self, stream_id: str, source: str | int):
        self.stream_id = stream_id
        self.source = source
        self._queue: Queue[FramePacket] = Queue(maxsize=settings.streams.queue_size)
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._frame_count = 0
        self._frames_dropped = 0

        # Adaptive resolution: start with the highest tier
        self._target_width: int = settings.resolution.tiers[0]

    # ── Public API ────────────────────────────────────────────────

    def start(self) -> None:
        """Open the capture device and start the decode thread."""
        self._cap = self._open_capture()
        if self._cap is None or not self._cap.isOpened():
            raise RuntimeError(f"[{self.stream_id}] Cannot open source: {self.source}")

        self._running.set()
        self._thread = threading.Thread(
            target=self._decode_loop,
            name=f"decoder-{self.stream_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("[%s] Decoder started for source: %s", self.stream_id, self.source)

    def stop(self) -> None:
        """Signal the decode thread to stop and release resources."""
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        logger.info("[%s] Decoder stopped", self.stream_id)

    def get_frame(self, timeout: float = 0.1) -> Optional[FramePacket]:
        """Consume the next frame packet from the queue (blocking)."""
        try:
            return self._queue.get(timeout=timeout)
        except Exception:
            return None

    def set_target_width(self, width: int) -> None:
        """Update the target capture width for adaptive resolution."""
        self._target_width = width
        if self._cap is not None:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            # Height will auto-adjust to maintain aspect ratio
            logger.info("[%s] Decoder target width → %d", self.stream_id, width)

    @property
    def frames_decoded(self) -> int:
        return self._frame_count

    @property
    def frames_dropped(self) -> int:
        return self._frames_dropped

    @property
    def queue_length(self) -> int:
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    # ── Internal ──────────────────────────────────────────────────

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        """Create a VideoCapture for the configured source."""
        try:
            # Integer source → webcam index
            if isinstance(self.source, int) or (isinstance(self.source, str) and self.source.isdigit()):
                src = int(self.source)
            else:
                src = self.source

            cap = cv2.VideoCapture(src)

            # Set initial resolution request
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._target_width)

            # Reduce internal buffer to 1 frame to avoid stale RTSP frames
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            return cap
        except Exception as e:
            logger.error("[%s] Failed to open capture: %s", self.stream_id, e)
            return None

    def _decode_loop(self) -> None:
        """Background loop: read frames and enqueue them."""
        retry_count = 0

        while self._running.is_set():
            if self._cap is None or not self._cap.isOpened():
                # Reconnect logic
                if retry_count >= settings.streams.reconnect_max_retries:
                    logger.error("[%s] Max reconnect retries reached, stopping", self.stream_id)
                    self._running.clear()
                    break
                logger.warning("[%s] Source lost, reconnecting (attempt %d)…",
                               self.stream_id, retry_count + 1)
                time.sleep(settings.streams.reconnect_delay_sec)
                if self._cap is not None:
                    self._cap.release()
                self._cap = self._open_capture()
                retry_count += 1
                continue

            ret, frame = self._cap.read()
            if not ret or frame is None:
                # End of video file or read failure
                if isinstance(self.source, str) and not self.source.startswith("rtsp"):
                    # Video file ended — stop gracefully
                    logger.info("[%s] End of video file", self.stream_id)
                    self._running.clear()
                    break
                # RTSP / webcam → attempt reconnect
                retry_count += 1
                continue

            retry_count = 0  # Reset on successful read
            self._frame_count += 1

            h, w = frame.shape[:2]
            packet = FramePacket(
                stream_id=self.stream_id,
                frame_number=self._frame_count,
                timestamp=time.time(),
                frame=frame,
                original_size=(h, w),
                current_size=(h, w),
            )

            # Non-blocking enqueue — drop oldest if full
            try:
                self._queue.put_nowait(packet)
            except Full:
                try:
                    self._queue.get_nowait()  # discard oldest
                except Exception:
                    pass
                try:
                    self._queue.put_nowait(packet)
                except Full:
                    pass
                self._frames_dropped += 1

        logger.debug("[%s] Decode loop exited", self.stream_id)
