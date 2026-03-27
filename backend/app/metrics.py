"""
metrics.py — Thread-safe performance metrics collection.

Tracks per-stream FPS, stage latencies, queue lengths, dropped/skipped
frames, plus system-wide CPU and RAM usage.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict

import psutil

from app.config import settings

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Centralised, thread-safe metrics store.

    Every pipeline stage calls `record_*` methods; the API
    layer calls `get_snapshot` for the current state.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fps_window = settings.metrics.fps_window_sec

        # Per-stream sliding-window timestamps for FPS
        self._frame_times: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=500)
        )

        # Per-stream stage latencies (most recent value in seconds)
        self._stage_latencies: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Per-stream counters
        self._frames_processed: Dict[str, int] = defaultdict(int)
        self._frames_skipped: Dict[str, int] = defaultdict(int)
        self._frames_dropped: Dict[str, int] = defaultdict(int)

        # Per-stream queue lengths (most recent snapshot)
        self._queue_lengths: Dict[str, int] = defaultdict(int)

        # Process handle for CPU/RAM
        self._process = psutil.Process()
        self._cpu_percent: float = 0.0
        self._ram_mb: float = 0.0

        # Background refresh
        self._running = threading.Event()

    # ── Recording API (called by pipeline stages) ─────────────────

    def record_frame(self, stream_id: str) -> None:
        """Record that a frame was fully processed."""
        now = time.time()
        with self._lock:
            self._frame_times[stream_id].append(now)
            self._frames_processed[stream_id] += 1

    def record_skip(self, stream_id: str) -> None:
        """Record a skipped (tracker-only) frame."""
        with self._lock:
            self._frames_skipped[stream_id] += 1

    def record_drop(self, stream_id: str) -> None:
        """Record a dropped frame (queue overflow)."""
        with self._lock:
            self._frames_dropped[stream_id] += 1

    def record_stage_latency(self, stream_id: str, stage: str, duration: float) -> None:
        """Record latency for a specific pipeline stage (in seconds)."""
        with self._lock:
            self._stage_latencies[stream_id][stage] = duration

    def record_queue_length(self, stream_id: str, length: int) -> None:
        """Snapshot the current decode queue length for a stream."""
        with self._lock:
            self._queue_lengths[stream_id] = length

    # ── Query API (called by routes / WebSocket) ──────────────────

    def get_fps(self, stream_id: str) -> float:
        """Compute current FPS using a sliding time window."""
        now = time.time()
        with self._lock:
            times = self._frame_times.get(stream_id)
            if not times:
                return 0.0
            cutoff = now - self._fps_window
            # Count frames within window
            count = sum(1 for t in times if t >= cutoff)
            return count / self._fps_window if self._fps_window > 0 else 0.0

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Return a complete metrics snapshot.

        Returns
        -------
        dict
            System + per-stream metrics.
        """
        self._refresh_system_stats()

        with self._lock:
            per_stream: Dict[str, Dict[str, Any]] = {}
            for sid in set(
                list(self._frames_processed.keys())
                + list(self._frame_times.keys())
            ):
                per_stream[sid] = {
                    "fps": round(self.get_fps(sid), 2),
                    "frames_processed": self._frames_processed.get(sid, 0),
                    "frames_skipped": self._frames_skipped.get(sid, 0),
                    "frames_dropped": self._frames_dropped.get(sid, 0),
                    "queue_length": self._queue_lengths.get(sid, 0),
                    "stage_latencies_ms": {
                        k: round(v * 1000, 2)
                        for k, v in self._stage_latencies.get(sid, {}).items()
                    },
                }

            total_fps = sum(
                self.get_fps(sid) for sid in self._frame_times
            )

            return {
                "timestamp": time.time(),
                "cpu_percent": self._cpu_percent,
                "ram_mb": round(self._ram_mb, 1),
                "active_streams": len(per_stream),
                "total_fps": round(total_fps, 2),
                "per_stream": per_stream,
            }

    # ── Stream lifecycle ──────────────────────────────────────────

    def remove_stream(self, stream_id: str) -> None:
        """Clean up metrics for a removed stream."""
        with self._lock:
            self._frame_times.pop(stream_id, None)
            self._stage_latencies.pop(stream_id, None)
            self._frames_processed.pop(stream_id, None)
            self._frames_skipped.pop(stream_id, None)
            self._frames_dropped.pop(stream_id, None)
            self._queue_lengths.pop(stream_id, None)

    # ── Internal ──────────────────────────────────────────────────

    def _refresh_system_stats(self) -> None:
        """Update CPU / RAM readings."""
        try:
            self._cpu_percent = self._process.cpu_percent(interval=0)
            mem = self._process.memory_info()
            self._ram_mb = mem.rss / (1024 * 1024)
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────
metrics_collector = MetricsCollector()
