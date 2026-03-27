"""
models.py — Shared data models used across the PPE detection pipeline.

All pipeline stages communicate through these well-defined structures
to keep the codebase decoupled and type-safe.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ── Bounding Box ──────────────────────────────────────────────────

@dataclass(slots=True)
class BBox:
    """Axis-aligned bounding box in pixel coordinates (x1, y1, x2, y2)."""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(self.x2 - self.x1, 0)

    @property
    def height(self) -> float:
        return max(self.y2 - self.y1, 0)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def iou(self, other: BBox) -> float:
        """Compute Intersection-over-Union with another box."""
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        inter = max(ix2 - ix1, 0) * max(iy2 - iy1, 0)
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0

    def sub_region(self, top_frac: float, bottom_frac: float) -> BBox:
        """Return a horizontal slice of this box (fraction from top)."""
        h = self.height
        return BBox(
            x1=self.x1,
            y1=self.y1 + h * top_frac,
            x2=self.x2,
            y2=self.y1 + h * bottom_frac,
        )


# ── Detection ────────────────────────────────────────────────────

@dataclass(slots=True)
class Detection:
    """A single object detection."""
    bbox: BBox
    class_id: int
    class_name: str
    confidence: float
    track_id: Optional[int] = None


# ── Compliance ───────────────────────────────────────────────────

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    HELMET_MISSING = "helmet_missing"
    VEST_MISSING = "vest_missing"
    NON_COMPLIANT = "non_compliant"  # both missing


@dataclass(slots=True)
class ComplianceResult:
    """Compliance assessment for a single detected person."""
    person_detection: Detection
    has_helmet: bool
    has_vest: bool
    status: ComplianceStatus
    matched_helmet: Optional[Detection] = None
    matched_vest: Optional[Detection] = None


# ── Alert ────────────────────────────────────────────────────────

@dataclass(slots=True)
class Alert:
    """A PPE violation alert."""
    alert_id: str
    stream_id: str
    track_id: int
    violation: ComplianceStatus
    bbox: BBox
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


# ── Frame Wrapper ────────────────────────────────────────────────

@dataclass
class FramePacket:
    """Carries a decoded frame through the pipeline with metadata."""
    stream_id: str
    frame_number: int
    timestamp: float
    frame: object  # numpy ndarray — kept as object to avoid numpy import at module level
    original_size: Tuple[int, int] = (0, 0)     # (height, width)
    current_size: Tuple[int, int] = (0, 0)      # after adaptive resize
    is_inference_frame: bool = True               # False for skipped frames
    preprocessed: Optional[object] = None         # preprocessed tensor
    detections: List[Detection] = field(default_factory=list)
    compliance_results: List[ComplianceResult] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
    stage_timings: Dict[str, float] = field(default_factory=dict)


# ── Stream Info ──────────────────────────────────────────────────

class StreamState(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    RECONNECTING = "reconnecting"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class StreamInfo:
    """Metadata about an active video stream."""
    stream_id: str
    source: str                          # URL, file path, or webcam index
    state: StreamState = StreamState.STARTING
    current_resolution_tier: int = 0     # Index into resolution tiers
    fps: float = 0.0
    frames_processed: int = 0
    frames_skipped: int = 0
    frames_dropped: int = 0
    error_message: Optional[str] = None


# ── Pipeline Metrics Snapshot ────────────────────────────────────

@dataclass
class PipelineMetricsSnapshot:
    """Point-in-time metrics for the entire system."""
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    ram_mb: float = 0.0
    active_streams: int = 0
    total_fps: float = 0.0
    per_stream: Dict[str, Dict] = field(default_factory=dict)
    active_alerts: int = 0
