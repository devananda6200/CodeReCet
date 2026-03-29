from fastapi import Request

from app.services.alert_store import AlertStore
from app.services.config_store import ConfigStore
from app.services.model_service import ModelService
from app.services.stream_manager import StreamManager
from app.services.zone_store import ZoneStore


def get_alert_store(request: Request) -> AlertStore:
    return request.app.state.alert_store


def get_config_store(request: Request) -> ConfigStore:
    return request.app.state.config_store


def get_stream_manager(request: Request) -> StreamManager:
    return request.app.state.stream_manager


def get_zone_store(request: Request) -> ZoneStore:
    return request.app.state.zone_store


def get_model_service(request: Request) -> ModelService:
    return request.app.state.model_service
