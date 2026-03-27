"""
alert_manager.py — Alert generation and deduplication.

Generates alerts from compliance results and enforces
a cooldown window to avoid flooding downstream consumers
with duplicate alerts for the same violation.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from typing import Deque, Dict, List, Tuple

from app.config import settings
from app.models import Alert, ComplianceResult, ComplianceStatus

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Converts compliance violations into alerts.

    Features
    --------
    - Per-track + per-violation cooldown to avoid re-alerting
    - Bounded alert history (ring buffer)
    - Active alert count tracking
    """

    def __init__(self) -> None:
        self.cooldown_sec = settings.alerts.cooldown_sec
        self.max_history = settings.alerts.max_history

        # (stream_id, track_id, violation) → last alert timestamp
        self._cooldowns: Dict[Tuple[str, int, str], float] = {}

        # Recent alerts (bounded)
        self._history: Deque[Alert] = deque(maxlen=self.max_history)

        # Currently active (non-acknowledged) alerts
        self._active_count = 0

    # ── Public API ────────────────────────────────────────────────

    def process(
        self,
        stream_id: str,
        compliance_results: List[ComplianceResult],
    ) -> List[Alert]:
        """
        Generate alerts for any non-compliant persons.

        Returns only *new* alerts (those not suppressed by cooldown).
        """
        now = time.time()
        new_alerts: List[Alert] = []

        for result in compliance_results:
            if result.status == ComplianceStatus.COMPLIANT:
                continue

            track_id = result.person_detection.track_id
            if track_id is None:
                continue  # untracked detection — skip

            violation = result.status.value
            key = (stream_id, track_id, violation)

            # Check cooldown
            last_alert_time = self._cooldowns.get(key, 0.0)
            if now - last_alert_time < self.cooldown_sec:
                continue  # Still in cooldown

            alert = Alert(
                alert_id=uuid.uuid4().hex[:12],
                stream_id=stream_id,
                track_id=track_id,
                violation=result.status,
                bbox=result.person_detection.bbox,
                timestamp=now,
            )

            self._cooldowns[key] = now
            self._history.append(alert)
            self._active_count += 1
            new_alerts.append(alert)

            logger.info(
                "ALERT [%s] stream=%s track=%d: %s",
                alert.alert_id, stream_id, track_id, violation,
            )

        # Periodic cleanup of expired cooldowns
        self._cleanup_cooldowns(now)

        return new_alerts

    def get_recent_alerts(self, limit: int = 50) -> List[Alert]:
        """Return the most recent alerts."""
        alerts = list(self._history)
        return alerts[-limit:]

    def acknowledge(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged."""
        for alert in self._history:
            if alert.alert_id == alert_id and not alert.acknowledged:
                alert.acknowledged = True
                self._active_count = max(0, self._active_count - 1)
                return True
        return False

    @property
    def active_alert_count(self) -> int:
        return self._active_count

    # ── Internal ──────────────────────────────────────────────────

    def _cleanup_cooldowns(self, now: float) -> None:
        """Remove expired cooldown entries to prevent memory growth."""
        expired = [
            key for key, ts in self._cooldowns.items()
            if now - ts > self.cooldown_sec * 3
        ]
        for key in expired:
            del self._cooldowns[key]
