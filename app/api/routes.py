"""
routes.py — FastAPI REST + WebSocket endpoints.

REST endpoints for stream management, metrics, and alerts.
WebSocket endpoint for live detection and compliance updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.metrics import metrics_collector
from app.models import FramePacket
from app.stream_manager import stream_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── Request / Response models ─────────────────────────────────────

class AddStreamRequest(BaseModel):
    stream_id: str = Field(..., description="Unique identifier for the stream")
    source: str = Field(..., description="Video source: file path, RTSP URL, or webcam index (as string)")


class StreamInfoResponse(BaseModel):
    stream_id: str
    source: str
    state: str
    current_resolution_tier: int
    fps: float
    frames_processed: int
    frames_skipped: int
    frames_dropped: int
    error_message: str | None = None


class AlertResponse(BaseModel):
    alert_id: str
    stream_id: str
    track_id: int
    violation: str
    bbox: Dict[str, float]
    timestamp: float
    acknowledged: bool


# ── Health ────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_streams": stream_manager.active_count,
        "timestamp": time.time(),
    }


# ── Stream Management ────────────────────────────────────────────

@router.get("/streams", response_model=List[StreamInfoResponse])
async def list_streams():
    """List all active streams and their status."""
    infos = stream_manager.list_streams()
    return [
        StreamInfoResponse(
            stream_id=info.stream_id,
            source=info.source,
            state=info.state.value,
            current_resolution_tier=info.current_resolution_tier,
            fps=round(info.fps, 2),
            frames_processed=info.frames_processed,
            frames_skipped=info.frames_skipped,
            frames_dropped=info.frames_dropped,
            error_message=info.error_message,
        )
        for info in infos
    ]


@router.post("/streams", response_model=StreamInfoResponse, status_code=201)
async def add_stream(req: AddStreamRequest):
    """Add a new video stream to the pipeline."""
    try:
        info = stream_manager.add_stream(req.stream_id, req.source)
        return StreamInfoResponse(
            stream_id=info.stream_id,
            source=info.source,
            state=info.state.value,
            current_resolution_tier=info.current_resolution_tier,
            fps=0.0,
            frames_processed=0,
            frames_skipped=0,
            frames_dropped=0,
        )
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=429, detail=str(e))


@router.delete("/streams/{stream_id}")
async def remove_stream(stream_id: str):
    """Stop and remove a stream."""
    removed = stream_manager.remove_stream(stream_id)
    if not removed:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Stream '{stream_id}' not found")
    return {"status": "removed", "stream_id": stream_id}


# ── Metrics ───────────────────────────────────────────────────────

@router.get("/metrics")
async def get_metrics():
    """Return current performance metrics."""
    return metrics_collector.get_snapshot()


# ── Alerts ────────────────────────────────────────────────────────

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(limit: int = 50):
    """Return recent alerts."""
    # Import AlertManager from stream pipelines — we need access to the
    # global alert history. For simplicity, alerts are stored per-pipeline,
    # so we aggregate from all stream pipelines here.
    alerts = []
    for info in stream_manager.list_streams():
        pipeline = stream_manager._pipelines.get(info.stream_id)
        if pipeline:
            for a in pipeline._alerts.get_recent_alerts(limit):
                alerts.append(AlertResponse(
                    alert_id=a.alert_id,
                    stream_id=a.stream_id,
                    track_id=a.track_id,
                    violation=a.violation.value if hasattr(a.violation, 'value') else str(a.violation),
                    bbox={
                        "x1": a.bbox.x1, "y1": a.bbox.y1,
                        "x2": a.bbox.x2, "y2": a.bbox.y2,
                    },
                    timestamp=a.timestamp,
                    acknowledged=a.acknowledged,
                ))
    # Sort by timestamp descending and limit
    alerts.sort(key=lambda x: x.timestamp, reverse=True)
    return alerts[:limit]


# ═════════════════════════════════════════════════════════════════════
# WebSocket — live detection stream
# ═════════════════════════════════════════════════════════════════════

_ws_clients: Set[WebSocket] = set()


def _frame_result_callback(packet: FramePacket) -> None:
    """
    Called by StreamPipeline when a frame is processed.
    Serialises results and queues them for WebSocket broadcast.
    """
    if not _ws_clients:
        return

    # Build lightweight JSON payload (no raw frame data)
    detections = [
        {
            "class": d.class_name,
            "confidence": round(d.confidence, 3),
            "track_id": d.track_id,
            "bbox": {"x1": d.bbox.x1, "y1": d.bbox.y1,
                     "x2": d.bbox.x2, "y2": d.bbox.y2},
        }
        for d in packet.detections
    ]

    compliance = [
        {
            "track_id": c.person_detection.track_id,
            "status": c.status.value,
            "has_helmet": c.has_helmet,
            "has_vest": c.has_vest,
        }
        for c in packet.compliance_results
    ]

    alerts_data = [
        {
            "alert_id": a.alert_id,
            "track_id": a.track_id,
            "violation": a.violation.value if hasattr(a.violation, 'value') else str(a.violation),
        }
        for a in packet.alerts
    ]

    payload = json.dumps({
        "stream_id": packet.stream_id,
        "frame_number": packet.frame_number,
        "timestamp": packet.timestamp,
        "is_inference_frame": packet.is_inference_frame,
        "detections": detections,
        "compliance": compliance,
        "alerts": alerts_data,
        "stage_timings_ms": {
            k: round(v * 1000, 2) for k, v in packet.stage_timings.items()
        },
    })

    # Broadcast to all connected clients (fire-and-forget)
    disconnected: List[WebSocket] = []
    for ws in list(_ws_clients):
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                asyncio.ensure_future, ws.send_text(payload)
            )
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        _ws_clients.discard(ws)


# Expose callback for main.py to pass into StreamManager
get_result_callback = lambda: _frame_result_callback


# ── WebSocket endpoint ────────────────────────────────────────────

ws_router = APIRouter()


@ws_router.websocket("/ws/detections")
async def ws_detections(websocket: WebSocket):
    """
    WebSocket endpoint for live detection + compliance updates.

    Clients receive a JSON message per processed frame containing
    detections, compliance results, alerts, and stage timings.
    """
    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info("WebSocket client connected (%d total)", len(_ws_clients))

    try:
        while True:
            # Keep connection alive; client can send pings or config
            data = await websocket.receive_text()
            # Optionally handle client commands here
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)
        logger.info("WebSocket client disconnected (%d remaining)", len(_ws_clients))
