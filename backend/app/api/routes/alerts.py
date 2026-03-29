from fastapi import APIRouter, Depends, Query

from app.api.deps import get_alert_store
from app.models.schemas import AlertListResponse
from app.services.alert_store import AlertStore

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    alert_store: AlertStore = Depends(get_alert_store),
) -> AlertListResponse:
    return AlertListResponse(items=alert_store.list_alerts(limit=limit))

