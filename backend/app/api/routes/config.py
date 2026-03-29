from fastapi import APIRouter, Depends

from app.api.deps import get_config_store
from app.models.schemas import RuntimeConfig, UpdateRuntimeConfig
from app.services.config_store import ConfigStore

router = APIRouter(tags=["config"])


@router.get("/config", response_model=RuntimeConfig)
async def get_config(config_store: ConfigStore = Depends(get_config_store)) -> RuntimeConfig:
    return config_store.get()


@router.post("/config", response_model=RuntimeConfig)
async def update_config(
    payload: UpdateRuntimeConfig,
    config_store: ConfigStore = Depends(get_config_store),
) -> RuntimeConfig:
    return config_store.update(payload)

