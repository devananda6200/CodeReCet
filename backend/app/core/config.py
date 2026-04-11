from functools import lru_cache
from pathlib import Path
import zipfile
import logging
import json
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent.parent


def extract_model_if_needed(model_path: Path) -> None:
    """Extract model from zip file if it exists and the actual model directory doesn't."""
    model_dir = model_path.parent
    model_zip = model_dir / "best.pt.zip"
    
    if model_zip.exists() and not model_path.exists():
        try:
            logger.info(f"Extracting model from {model_zip}...")
            with zipfile.ZipFile(model_zip, 'r') as zip_ref:
                zip_ref.extractall(model_dir)
            logger.info(f"Model extracted successfully to {model_path}")
        except Exception as e:
            logger.warning(f"Failed to extract model: {e}")


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
    allowed_origins: str = ""  # Raw string from env, parsed manually
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
    
    # Parse allowed_origins from raw string
    default_origins = ["http://localhost:5173", "http://localhost:8080"]
    if settings.allowed_origins.strip():
        try:
            parsed = json.loads(settings.allowed_origins)
            if isinstance(parsed, list):
                # Replace the string with a list (hacky but works)
                object.__setattr__(settings, "allowed_origins", parsed)
            else:
                logger.warning(f"OPS_ALLOWED_ORIGINS is not a list: {parsed}")
                object.__setattr__(settings, "allowed_origins", default_origins)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse OPS_ALLOWED_ORIGINS as JSON: {settings.allowed_origins}. Error: {e}")
            object.__setattr__(settings, "allowed_origins", default_origins)
    else:
        object.__setattr__(settings, "allowed_origins", default_origins)
    
    # Extract model from zip if needed
    extract_model_if_needed(bundled_model)
    
    if not bundled_model.exists() and external_model.exists():
        bundled_model.parent.mkdir(parents=True, exist_ok=True)
        bundled_model.write_bytes(external_model.read_bytes())
    return settings
