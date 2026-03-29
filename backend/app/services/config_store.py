from app.core.config import Settings
from app.models.schemas import RuntimeConfig, UpdateRuntimeConfig


class ConfigStore:
    def __init__(self, settings: Settings) -> None:
        self._config = RuntimeConfig(
            model_path=str(settings.model_path),
            backend=settings.default_backend,
            cpu_threads=settings.default_cpu_threads,
            confidence_threshold=settings.default_confidence,
            iou_threshold=settings.default_iou,
            alert_persistence_frames=settings.alert_persistence_frames,
            input_size=settings.default_input_size,
            machine_proximity_px=140,
            adaptive_resolution=settings.adaptive_resolution,
            smart_frame_skip=True,
            frame_skip_rate=settings.default_frame_skip,
        )

    def get(self) -> RuntimeConfig:
        return self._config

    def update(self, payload: UpdateRuntimeConfig) -> RuntimeConfig:
        updates = payload.model_dump(exclude_none=True)
        self._config = self._config.model_copy(update=updates)
        return self._config
