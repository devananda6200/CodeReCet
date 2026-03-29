from fastapi import APIRouter, Depends

from app.api.deps import get_zone_store
from app.models.schemas import MessageResponse, PolygonZone
from app.services.zone_store import ZoneStore

router = APIRouter(prefix="/zones", tags=["zones"])


@router.post("/{stream_id}", response_model=MessageResponse)
async def save_zone(
    stream_id: str,
    payload: PolygonZone,
    zone_store: ZoneStore = Depends(get_zone_store),
) -> MessageResponse:
    zone_store.save_zone(stream_id, payload)
    return MessageResponse(message=f"Zone saved for stream {stream_id}")


@router.get("/{stream_id}", response_model=PolygonZone | None)
async def get_zone(
    stream_id: str,
    zone_store: ZoneStore = Depends(get_zone_store),
) -> PolygonZone | None:
    return zone_store.get_zone(stream_id)

