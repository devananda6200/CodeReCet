import json
from collections import deque
from pathlib import Path

from app.models.schemas import AlertRecord


class AlertStore:
    def __init__(self, storage_path: Path, max_items: int = 250) -> None:
        self.storage_path = storage_path
        self._items: deque[AlertRecord] = deque(maxlen=max_items)
        self._last_version = 0
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        for item in data:
            self._items.append(AlertRecord.model_validate(item))
        self._last_version = len(self._items)

    def _persist(self) -> None:
        serialized = [item.model_dump(mode="json") for item in self._items]
        self.storage_path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

    def add_alert(self, alert: AlertRecord) -> None:
        self._items.appendleft(alert)
        self._last_version += 1
        self._persist()

    def list_alerts(self, limit: int = 50) -> list[AlertRecord]:
        return list(self._items)[:limit]

    def last_version(self) -> int:
        return self._last_version

