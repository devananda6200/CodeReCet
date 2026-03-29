from fastapi import APIRouter, Depends

from app.api.deps import get_stream_manager
from app.models.schemas import SummaryMetrics
from app.services.stream_manager import StreamManager

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary", response_model=SummaryMetrics)
async def get_summary_metrics(
    manager: StreamManager = Depends(get_stream_manager),
) -> SummaryMetrics:
    return manager.get_summary_metrics()

