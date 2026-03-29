from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="OPS_",
        extra="ignore",
    )

    app_name: str = "Ops Safety System API"
    environment: str = "development"
    demo_mode: bool = False
    model_path: Path = PROJECT_ROOT / "models" / "best.pt"
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    snapshot_dir: Path = PROJECT_ROOT / "data" / "snapshots"
    alert_store_path: Path = PROJECT_ROOT / "data" / "alerts" / "recent_alerts.json"
    zone_store_path: Path = PROJECT_ROOT / "data" / "zones.json"
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:8080"]
    )
    default_backend: str = "pytorch"
    default_cpu_threads: int = 4
    max_cpu_threads: int = 8
    default_confidence: float = 0.35
    default_iou: float = 0.45
    default_input_size: int = 512
    default_frame_skip: int = 4
    alert_persistence_frames: int = 3
    adaptive_resolution: bool = True
    demo_seed_streams: int = 0


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    bundled_model = settings.model_path
    external_model = WORKSPACE_ROOT / "best (1).pt"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.snapshot_dir.mkdir(parents=True, exist_ok=True)
    settings.alert_store_path.parent.mkdir(parents=True, exist_ok=True)
    settings.zone_store_path.parent.mkdir(parents=True, exist_ok=True)
    if not bundled_model.exists() and external_model.exists():
        bundled_model.parent.mkdir(parents=True, exist_ok=True)
        bundled_model.write_bytes(external_model.read_bytes())
    return settings
