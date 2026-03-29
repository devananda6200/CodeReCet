from fastapi import APIRouter, Depends

from app.api.deps import get_stream_manager
from app.core.config import get_settings
from app.models.schemas import HealthResponse
from app.services.stream_manager import StreamManager
from app.utils.system import get_process_memory_mb, get_system_cpu_percent

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(stream_manager: StreamManager = Depends(get_stream_manager)) -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
        demo_mode=settings.demo_mode,
        active_streams=stream_manager.count_running(),
        total_streams=stream_manager.count_total(),
        model_path=str(settings.model_path),
        cpu_percent=get_system_cpu_percent(),
        memory_mb=get_process_memory_mb(),
    )

