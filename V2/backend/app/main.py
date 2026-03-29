import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.alerts import router as alerts_router
from app.api.routes.config import router as config_router
from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.streams import router as streams_router
from app.api.routes.zones import router as zones_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.safety.rule_engine import SafetyRuleEngine
from app.services.alert_store import AlertStore
from app.services.config_store import ConfigStore
from app.services.model_service import ModelService
from app.services.stream_manager import StreamManager
from app.services.zone_store import ZoneStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    config_store = ConfigStore(settings)
    alert_store = AlertStore(settings.alert_store_path)
    zone_store = ZoneStore(settings.zone_store_path)
    model_service = ModelService()
    safety_engine = SafetyRuleEngine()
    stream_manager = StreamManager(
        settings,
        config_store,
        alert_store,
        zone_store,
        model_service,
        safety_engine,
    )
    await stream_manager.seed_demo_streams()

    app.state.settings = settings
    app.state.config_store = config_store
    app.state.alert_store = alert_store
    app.state.zone_store = zone_store
    app.state.model_service = model_service
    app.state.stream_manager = stream_manager

    yield

    await stream_manager.shutdown()


app = FastAPI(
    title="Ops Safety System API",
    version="0.1.0",
    description="Starter API for a CPU-first industrial safety monitoring system.",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(config_router)
app.include_router(metrics_router)
app.include_router(streams_router)
app.include_router(alerts_router)
app.include_router(zones_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Ops Safety System API is running"}


@app.websocket("/ws/streams")
async def stream_updates(websocket: WebSocket) -> None:
    await websocket.accept()
    manager = websocket.app.state.stream_manager
    try:
        while True:
            payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "streams": [stream.model_dump(mode="json") for stream in manager.list_streams()],
                "summary": manager.get_summary_metrics().model_dump(mode="json"),
            }
            await websocket.send_json(payload)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/alerts")
async def alert_updates(websocket: WebSocket) -> None:
    await websocket.accept()
    alert_store = websocket.app.state.alert_store
    last_version = -1
    try:
        while True:
            if alert_store.last_version() != last_version:
                last_version = alert_store.last_version()
                payload = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "alerts": [item.model_dump(mode="json") for item in alert_store.list_alerts(limit=25)],
                }
                await websocket.send_json(payload)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/metrics")
async def metrics_updates(websocket: WebSocket) -> None:
    await websocket.accept()
    manager = websocket.app.state.stream_manager
    try:
        while True:
            payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": manager.get_summary_metrics().model_dump(mode="json"),
            }
            await websocket.send_json(payload)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
