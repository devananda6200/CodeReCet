"""
config.py — Central configuration for the PPE Compliance Detection backend.

Loads settings from config.yaml with environment variable overrides.
All modules import `settings` from this module.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import BaseModel, Field


# ── Locate config file ────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


# ── Nested Pydantic models ────────────────────────────────────────

class ModelConfig(BaseModel):
    path: str = "models/yolo11l.pt"
    backend: str = "pytorch"  # pytorch | onnx | openvino
    input_size: int = 640
    confidence_threshold: float = 0.45
    nms_iou_threshold: float = 0.50
    half_precision: bool = False


class StreamsConfig(BaseModel):
    max_concurrent: int = 4
    queue_size: int = 5
    reconnect_delay_sec: float = 5.0
    reconnect_max_retries: int = 10


class PipelineConfig(BaseModel):
    frame_skip: int = 3
    tracker_max_disappeared: int = 15
    tracker_iou_threshold: float = 0.30
    anti_flicker_min_hits: int = 3
    tracker_velocity_smoothing: float = 0.5


class ResolutionConfig(BaseModel):
    tiers: List[int] = Field(default_factory=lambda: [1920, 1280, 854, 640])
    fps_low_threshold: float = 8.0
    fps_high_threshold: float = 14.0
    eval_window_sec: float = 3.0


class ComplianceConfig(BaseModel):
    head_region_ratio: float = 0.30
    torso_region_top: float = 0.25
    torso_region_bottom: float = 0.65
    overlap_iou_threshold: float = 0.15


class AlertsConfig(BaseModel):
    cooldown_sec: float = 10.0
    max_history: int = 500
    latency_target_ms: float = 300.0


class MetricsConfig(BaseModel):
    collection_interval_sec: float = 1.0
    fps_window_sec: float = 5.0


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])


class ResourcesConfig(BaseModel):
    max_cpu_cores: int = 8
    onnx_inter_threads: int = 2
    onnx_intra_threads: int = 4
    openvino_num_requests: int = 2


# ── Root settings ─────────────────────────────────────────────────

class Settings(BaseModel):
    """Root configuration aggregating all sub-configs."""

    model: ModelConfig = Field(default_factory=ModelConfig)
    classes: Dict[int, str] = Field(default_factory=lambda: {0: "person", 1: "helmet", 2: "safety_vest"})
    streams: StreamsConfig = Field(default_factory=StreamsConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    resolution: ResolutionConfig = Field(default_factory=ResolutionConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)

    # Derived / convenience -------------------------------------------------

    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    @property
    def class_names(self) -> List[str]:
        """Ordered list of class names by index."""
        return [self.classes[i] for i in sorted(self.classes)]

    @property
    def num_classes(self) -> int:
        return len(self.classes)


def _load_settings() -> Settings:
    """Load settings from YAML, falling back to defaults."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    else:
        raw = {}

    # Allow env-var overrides for key fields
    if env_backend := os.getenv("PPE_INFERENCE_BACKEND"):
        raw.setdefault("model", {})["backend"] = env_backend
    if env_model := os.getenv("PPE_MODEL_PATH"):
        raw.setdefault("model", {})["path"] = env_model

    return Settings(**raw)


# ── Singleton ─────────────────────────────────────────────────────
settings = _load_settings()
