from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.api.deps import get_stream_manager
from app.models.schemas import AddStreamRequest, MessageResponse, StreamListResponse, StreamMetrics, StreamRecord
from app.services.stream_manager import StreamManager

router = APIRouter(prefix="/streams", tags=["streams"])


@router.post("/add", response_model=StreamRecord, status_code=status.HTTP_201_CREATED)
async def add_stream(
    payload: AddStreamRequest,
    manager: StreamManager = Depends(get_stream_manager),
) -> StreamRecord:
    return await manager.add_stream(payload)


@router.post("/upload", response_model=StreamRecord, status_code=status.HTTP_201_CREATED)
async def upload_stream(
    file: UploadFile = File(...),
    manager: StreamManager = Depends(get_stream_manager),
) -> StreamRecord:
    return await manager.add_uploaded_stream(file)


@router.post("/{stream_id}/start", response_model=MessageResponse)
async def start_stream(
    stream_id: str,
    manager: StreamManager = Depends(get_stream_manager),
) -> MessageResponse:
    await manager.start_stream(stream_id)
    return MessageResponse(message=f"Stream {stream_id} started")


@router.post("/{stream_id}/stop", response_model=MessageResponse)
async def stop_stream(
    stream_id: str,
    manager: StreamManager = Depends(get_stream_manager),
) -> MessageResponse:
    await manager.stop_stream(stream_id)
    return MessageResponse(message=f"Stream {stream_id} stopped")


@router.get("", response_model=StreamListResponse)
async def list_streams(manager: StreamManager = Depends(get_stream_manager)) -> StreamListResponse:
    return StreamListResponse(items=manager.list_streams())


@router.get("/{stream_id}/metrics", response_model=StreamMetrics)
async def get_stream_metrics(
    stream_id: str,
    manager: StreamManager = Depends(get_stream_manager),
) -> StreamMetrics:
    metrics = manager.get_metrics(stream_id)
    if metrics is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
    return metrics


@router.get("/{stream_id}/frame")
async def get_stream_frame(
    stream_id: str,
    manager: StreamManager = Depends(get_stream_manager),
) -> Response:
    frame = manager.get_latest_frame(stream_id)
    if frame is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame not available")
    return Response(content=frame, media_type="image/jpeg")
