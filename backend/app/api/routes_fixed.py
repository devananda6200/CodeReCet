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
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.metrics import metrics_collector
from app.models import FramePacket
from app.stream_manager import stream_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

START_TIME = time.time()


# ── Request / Response models ─────────────────────────────────────

class AddStreamRequest(BaseModel):
    stream_id: str = Field(..., description="Unique identifier for the stream")
    name: Optional[str] = Field(None, description="Stream name")
    source: str = Field(..., description="Video source: file path, RTSP URL, or webcam index (as string)")


class BoundingBoxResponse(BaseModel):
    x: float
    y: float
    w: float
    h: float


class DetectionResponse(BaseModel):
    id: str
    class_: str = Field(alias="class")
    confidence: float
    box: BoundingBoxResponse


class SystemMetricsResponse(BaseModel):
    fps: float
    latency: float
    cpu: float
    ram: float
    healthy: bool


class StreamDataResponse(BaseModel):
    id: str
    name: str
    status: str
    detections: List[DetectionResponse]
    metrics: SystemMetricsResponse


class AlertResponse(BaseModel):
    id: str
    streamId: str
    timestamp: str
    type: str
    severity: str
    personId: str
    resolved: bool


# ── Health ────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "uptime": int(time.time() - START_TIME),
    }


# ── Stream Management ────────────────────────────────────────────

@router.get("/streams", response_model=List[StreamDataResponse])
async def list_streams():
    """List all active streams and their status."""
    infos = await asyncio.to_thread(stream_manager.list_streams)
    metrics_snap = await asyncio.to_thread(metrics_collector.get_snapshot)
    
    result = []
    for info in infos:
        stream_metrics = metrics_snap.get("per_stream", {}).get(info.stream_id, {})
        sys_metrics = SystemMetricsResponse(
            fps=round(stream_metrics.get("fps", 0.0), 1),
            latency=round(stream_metrics.get("latency_ms", 0.0), 1),
            cpu=round(metrics_snap.get("cpu_percent", 0.0), 1),
            ram=round(metrics_snap.get("ram_mb", 0.0), 1),
            healthy=info.state.value == "running"
        )
        
        status_map = {
            "starting": "inactive",
            "running": "active",
            "paused": "inactive",
            "reconnecting": "error",
            "stopped": "inactive",
            "error": "error"
        }
        
        result.append(StreamDataResponse(
            id=info.stream_id,
            name=info.name or info.stream_id,
            status=status_map.get(info.state.value, "error"),
            detections=[],
            metrics=sys_metrics
        ))
    return result


@router.post("/streams", response_model=StreamDataResponse, status_code=201)
async def add_stream(req: AddStreamRequest):
    """Add a new video stream to the pipeline."""
    try:
        info = await asyncio.to_thread(
            stream_manager.add_stream, req.stream_id, req.source, req.name or ""
        )
        return StreamDataResponse(
            id=info.stream_id,
            name=info.name or info.stream_id,
            status="inactive",
            detections=[],
            metrics=SystemMetricsResponse(fps=0, latency=0, cpu=0, ram=0, healthy=True)
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


@router.get("/streams/{stream_id}/feed")
async def stream_feed(stream_id: str):
    """MJPEG continuous video feed for a stream."""
    import asyncio
    from fastapi.responses import StreamingResponse
    from fastapi import HTTPException

    pipeline = stream_manager._pipelines.get(stream_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Stream '{stream_id}' not found")

    async def frame_generator():
        while pipeline.is_running:
            if getattr(pipeline, "latest_frame_jpg", b""):
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + pipeline.latest_frame_jpg + b'\r\n')
            await asyncio.sleep(0.05)  # Cap at ~20 FPS

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


# ── Metrics ───────────────────────────────────────────────────────

@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_metrics():
    """Return current performance metrics."""
    metrics_snap = metrics_collector.get_snapshot()
    return SystemMetricsResponse(
        fps=metrics_snap.get(" total_fps\, 0.0),
        latency=0.0,
        cpu=metrics_snap.get(\cpu_percent\, 0.0),
        ram=metrics_snap.get(\ram_mb\, 0.0),
        healthy=True
    )


# ── Alerts ────────────────────────────────────────────────────────

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(limit: int = 50):
    """Return recent alerts."""
    alerts = []
    for info in stream_manager.list_streams():
        pipeline = stream_manager._pipelines.get(info.stream_id)
        if pipeline:
            for a in pipeline._alerts.get_recent_alerts(limit):
                severity = "critical" if getattr(a.violation, "value", str(a.violation)) == "missing_both" else "medium"
                ts_iso = datetime.fromtimestamp(a.timestamp, tz=timezone.utc).isoformat()
                alerts.append(AlertResponse(
                    id=a.alert_id,
                    streamId=a.stream_id,
                    timestamp=ts_iso,
                    type=getattr(a.violation, "value", str(a.violation)),
                    severity=severity,
                    personId=str(a.track_id),
                    resolved=a.acknowledged,
                ))
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

    sys_metrics = metrics_collector.get_snapshot()
    stream_metrics = sys_metrics.get("per_stream", {}).get(packet.stream_id, {})
    
    metrics_payload = {
        "fps": round(stream_metrics.get("fps", 0.0), 1),
        "latency": round(sum(packet.stage_timings.values()) * 1000, 1),
        "cpu": round(sys_metrics.get("cpu_percent", 0.0), 1),
        "ram": round(sys_metrics.get("ram_mb", 0.0), 1),
        "healthy": True
    }
    
    detections_payload = [
        {
            "id": str(d.track_id) if d.track_id is not None else f"det_{id(d)}",
            "class": d.class_name,
            "confidence": round(d.confidence, 3),
            "box": {
                 "x": round(d.bbox.x1, 1),
                 "y": round(d.bbox.y1, 1),
                 "w": round(d.bbox.width, 1),
                 "h": round(d.bbox.height, 1)
            }
        }
        for d in packet.detections
    ]
    
    info = stream_manager.get_stream_info(packet.stream_id)
    stream_name = info.name if info and info.name else packet.stream_id

    stream_data = {
        "id": packet.stream_id,
        "name": stream_name,
        "status": "active",
        "frame_width": packet.current_size[1],
        "frame_height": packet.current_size[0],
        "detections": detections_payload,
        "metrics": metrics_payload
    }
    
    payload = json.dumps({
        "type": "detections",
        "data": [stream_data]
    })
    
    # Send alerts individually if any
    alert_payloads = []
    for a in packet.alerts:
        severity = "critical" if getattr(a.violation, "value", str(a.violation)) == "missing_both" else "medium"
        ts_iso = datetime.fromtimestamp(a.timestamp, tz=timezone.utc).isoformat()
        alert_payloads.append(json.dumps({
            "type": "alert",
            "data": {
                "id": a.alert_id,
                "streamId": a.stream_id,
                "timestamp": ts_iso,
                "type": getattr(a.violation, "value", str(a.violation)),
                "severity": severity,
                "personId": str(a.track_id),
                "resolved": a.acknowledged
            }
        }))

    disconnected: List[WebSocket] = []
    
    for ws in list(_ws_clients):
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(asyncio.ensure_future, ws.send_text(payload))
            for ap in alert_payloads:
                loop.call_soon_threadsafe(asyncio.ensure_future, ws.send_text(ap))
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        _ws_clients.discard(ws)


get_result_callback = lambda: _frame_result_callback


# ── WebSocket endpoint ────────────────────────────────────────────

ws_router = APIRouter()


@ws_router.websocket("/ws/detections")
async def ws_detections(websocket: WebSocket):
    """WebSocket endpoint for live detection + compliance updates."""
    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info("WebSocket client connected (%d total)", len(_ws_clients))

    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)
        logger.info("WebSocket client disconnected (%d remaining)", len(_ws_clients))
