import json
from pathlib import Path

from app.models.schemas import PolygonZone


class ZoneStore:
    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path
        self._zones: dict[str, PolygonZone] = {}
        self._load()

    def save_zone(self, stream_id: str, zone: PolygonZone) -> None:
        self._zones[stream_id] = zone
        self._persist()

    def get_zone(self, stream_id: str) -> PolygonZone | None:
        return self._zones.get(stream_id)

    def _load(self) -> None:
        if self.storage_path is None or not self.storage_path.exists():
            return
        raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
        self._zones = {stream_id: PolygonZone.model_validate(zone) for stream_id, zone in raw.items()}

    def _persist(self) -> None:
        if self.storage_path is None:
            return
        payload = {stream_id: zone.model_dump(mode="json") for stream_id, zone in self._zones.items()}
        self.storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
