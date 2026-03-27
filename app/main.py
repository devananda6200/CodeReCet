"""
main.py — FastAPI application entrypoint.

Sets up CORS, includes API routers, and manages the
StreamManager lifecycle via lifespan hooks.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import get_result_callback, router, ws_router
from app.config import settings
from app.stream_manager import stream_manager

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks for the application."""
    logger.info("=" * 60)
    logger.info("  PPE Compliance Detection — Backend Starting")
    logger.info("=" * 60)

    # Initialise the inference engine and stream manager
    callback = get_result_callback()
    stream_manager.startup(result_callback=callback)

    yield  # ← Application is running

    logger.info("Shutting down stream manager…")
    stream_manager.shutdown()
    logger.info("Shutdown complete")


# ── App factory ───────────────────────────────────────────────────

app = FastAPI(
    title="PPE Compliance Detection API",
    description=(
        "Real-time PPE compliance monitoring backend. "
        "Detects person, helmet, and safety vest using YOLO11 "
        "and checks for PPE compliance."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)            # REST  → /api/*
app.include_router(ws_router)         # WS    → /ws/*


# ── Standalone run ────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=False,
        workers=1,              # Single-process — threads handle concurrency
        log_level="info",
    )
