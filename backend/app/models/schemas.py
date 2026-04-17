from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StreamSourceType(str, Enum):
    demo = "demo"
    rtsp = "rtsp"
    http = "http"
    webcam = "webcam"
    file = "file"


class StreamRuntimeStatus(str, Enum):
    stopped = "stopped"
    starting = "starting"
    running = "running"
    error = "error"


class StreamSafetyStatus(str, Enum):
    safe = "SAFE"
    ppe_missing = "PPE MISSING"
    no_go_zone = "NO-GO ZONE BREACH"
    machine_proximity = "MACHINE PROXIMITY ALERT"


class AlertType(str, Enum):
    ppe_violation = "ppe_violation"
    zone_breach = "zone_breach"
    machine_proximity = "machine_proximity"


class BackendChoice(str, Enum):
    pytorch = "pytorch"
    onnx = "onnxruntime"
    openvino = "openvino"
    mock = "mock"


class MessageResponse(BaseModel):
    message: str


class StreamMetrics(BaseModel):
    fps: float = 0.0
    inference_latency_ms: float = 0.0
    decode_latency_ms: float = 0.0
    end_to_end_latency_ms: float = 0.0
    alert_latency_ms: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    current_resolution: str = "1280x720"
    frame_skip_rate: int = 1
    adaptive_resolution_enabled: bool = True
    tracking_mode: str = "centroid-lite"
    processed_frames: int = 0
    detection_count: int = 0
    mode: str = "mock"
    updated_at: datetime = Field(default_factory=utc_now)


class StreamRecord(BaseModel):
    id: str
    name: str
    source_type: StreamSourceType
    source_uri: str | None = None
    runtime_status: StreamRuntimeStatus = StreamRuntimeStatus.stopped
    safety_status: StreamSafetyStatus = StreamSafetyStatus.safe
    preview_url: str | None = None
    model_backend: BackendChoice = BackendChoice.pytorch
    active_alerts: int = 0
    last_seen_at: datetime = Field(default_factory=utc_now)
    metrics: StreamMetrics = Field(default_factory=StreamMetrics)


class StreamListResponse(BaseModel):
    items: list[StreamRecord]


class AddStreamRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    source_type: StreamSourceType
    source_uri: str | None = None


class AlertRecord(BaseModel):
    id: str
    stream_id: str
    stream_name: str
    type: AlertType
    severity: Literal["low", "medium", "high"] = "medium"
    confidence: float = Field(ge=0.0, le=1.0)
    status_label: StreamSafetyStatus
    snapshot_path: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    details: str


class AlertListResponse(BaseModel):
    items: list[AlertRecord]


class ZonePoint(BaseModel):
    x: float = Field(ge=0.0)
    y: float = Field(ge=0.0)


class PolygonZone(BaseModel):
    name: str = "No-Go Zone"
    points: list[ZonePoint] = Field(default_factory=list, min_length=3)


class RuntimeConfig(BaseModel):
    model_path: str
    backend: BackendChoice = BackendChoice.pytorch
    cpu_threads: int = Field(default=4, ge=1, le=8)
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    alert_persistence_frames: int = Field(default=3, ge=1, le=10)
    input_size: int = Field(default=960, ge=320, le=1280)
    machine_proximity_px: int = Field(default=140, ge=40, le=600)
    adaptive_resolution: bool = True
    smart_frame_skip: bool = True
    frame_skip_rate: int = Field(default=2, ge=1, le=8)
    label_remap: dict[str, str] = Field(default_factory=dict)
    class_mappings: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "person": ["persons", "person", "worker"],
            "helmet": ["helmets", "helmet", "hardhat", "hard_hat"],
            "vest": ["vests", "vest", "safety_vest", "jacket"],
            "machine": [],
        }
    )


class UpdateRuntimeConfig(BaseModel):
    model_path: str | None = None
    backend: BackendChoice | None = None
    cpu_threads: int | None = Field(default=None, ge=1, le=8)
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    iou_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    alert_persistence_frames: int | None = Field(default=None, ge=1, le=10)
    input_size: int | None = Field(default=None, ge=320, le=1280)
    machine_proximity_px: int | None = Field(default=None, ge=40, le=600)
    adaptive_resolution: bool | None = None
    smart_frame_skip: bool | None = None
    frame_skip_rate: int | None = Field(default=None, ge=1, le=8)
    label_remap: dict[str, str] | None = None
    class_mappings: dict[str, list[str]] | None = None


class DetectionRecord(BaseModel):
    track_id: int | None = None
    class_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: tuple[float, float, float, float]


class SummaryMetrics(BaseModel):
    active_streams: int
    total_streams: int
    alerts_in_memory: int
    avg_fps: float
    avg_latency_ms: float
    avg_cpu_percent: float
    process_memory_mb: float
    active_hazard_streams: int
    backends_in_use: list[str]
    generated_at: datetime = Field(default_factory=utc_now)


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    demo_mode: bool
    active_streams: int
    total_streams: int
    model_path: str
    cpu_percent: float
    memory_mb: float
