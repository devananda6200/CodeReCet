from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.models.schemas import AlertRecord, AlertType, DetectionRecord, PolygonZone, RuntimeConfig, StreamSafetyStatus


@dataclass
class HazardState:
    count: int = 0
    first_seen_at: datetime | None = None
    emitted: bool = False


@dataclass
class StreamHazardState:
    hazards: dict[str, HazardState] = field(default_factory=dict)


class SafetyRuleEngine:
    def __init__(self) -> None:
        self._state: dict[str, StreamHazardState] = {}

    def evaluate(
        self,
        *,
        stream_id: str,
        stream_name: str,
        detections: list[DetectionRecord],
        zone: PolygonZone | None,
        config: RuntimeConfig,
    ) -> tuple[StreamSafetyStatus, list[AlertRecord], float]:
        state = self._state.setdefault(stream_id, StreamHazardState())
        hazard_rows = self._collect_hazards(detections, zone, config)
        seen_keys = {row["key"] for row in hazard_rows}
        emitted_alerts: list[AlertRecord] = []
        latest_alert_latency_ms = 0.0

        for row in hazard_rows:
            hazard = state.hazards.setdefault(row["key"], HazardState())
            hazard.count += 1
            if hazard.first_seen_at is None:
                hazard.first_seen_at = datetime.now(timezone.utc)
            if hazard.count >= config.alert_persistence_frames and not hazard.emitted:
                hazard.emitted = True
                now = datetime.now(timezone.utc)
                latest_alert_latency_ms = max(
                    latest_alert_latency_ms,
                    (now - hazard.first_seen_at).total_seconds() * 1000,
                )
                emitted_alerts.append(
                    AlertRecord(
                        id=uuid4().hex,
                        stream_id=stream_id,
                        stream_name=stream_name,
                        type=row["alert_type"],
                        severity=row["severity"],
                        confidence=row["confidence"],
                        status_label=row["status"],
                        details=row["details"],
                    )
                )

        for hazard_key in list(state.hazards):
            if hazard_key not in seen_keys:
                state.hazards.pop(hazard_key, None)

        safety_status = self._overall_status(hazard_rows)
        return safety_status, emitted_alerts, latest_alert_latency_ms

    def _collect_hazards(
        self,
        detections: list[DetectionRecord],
        zone: PolygonZone | None,
        config: RuntimeConfig,
    ) -> list[dict]:
        mappings = {key: {item.lower() for item in values} for key, values in config.class_mappings.items()}
        persons = [item for item in detections if item.class_name.lower() in mappings.get("person", {"person"})]
        helmets = [item for item in detections if item.class_name.lower() in mappings.get("helmet", {"helmet"})]
        vests = [item for item in detections if item.class_name.lower() in mappings.get("vest", {"vest"})]
        machines = [item for item in detections if item.class_name.lower() in mappings.get("machine", {"machine"})]

        hazards: list[dict] = []

        for person in persons:
            track_key = person.track_id or 0
            if not self._has_related_item(person, helmets, ppe_type="helmet"):
                hazards.append(
                    {
                        "key": f"ppe-helmet-{track_key}",
                        "status": StreamSafetyStatus.ppe_missing,
                        "alert_type": AlertType.ppe_violation,
                        "severity": "medium",
                        "confidence": person.confidence,
                        "details": "Helmet missing for tracked worker.",
                    }
                )
            if not self._has_related_item(person, vests, ppe_type="vest"):
                hazards.append(
                    {
                        "key": f"ppe-vest-{track_key}",
                        "status": StreamSafetyStatus.ppe_missing,
                        "alert_type": AlertType.ppe_violation,
                        "severity": "medium",
                        "confidence": person.confidence,
                        "details": "Safety vest missing for tracked worker.",
                    }
                )
            if zone and self._point_inside_polygon(self._bottom_midpoint(person.bbox), zone):
                hazards.append(
                    {
                        "key": f"zone-{track_key}",
                        "status": StreamSafetyStatus.no_go_zone,
                        "alert_type": AlertType.zone_breach,
                        "severity": "high",
                        "confidence": person.confidence,
                        "details": f"Worker entered restricted area: {zone.name}.",
                    }
                )
            for machine in machines:
                if self._distance_between_boxes(person.bbox, machine.bbox) <= config.machine_proximity_px:
                    hazards.append(
                        {
                            "key": f"machine-{track_key}-{machine.track_id or 0}",
                            "status": StreamSafetyStatus.machine_proximity,
                            "alert_type": AlertType.machine_proximity,
                            "severity": "high",
                            "confidence": min(person.confidence, machine.confidence),
                            "details": "Worker is within machine proximity threshold.",
                        }
                    )

        return hazards

    @staticmethod
    def _has_related_item(person: DetectionRecord, candidates: list[DetectionRecord], ppe_type: str) -> bool:
        px1, py1, px2, py2 = person.bbox
        person_w = max(px2 - px1, 1)
        person_h = max(py2 - py1, 1)
        for candidate in candidates:
            x1, y1, x2, y2 = candidate.bbox
            overlap = SafetyRuleEngine._intersection_area(person.bbox, candidate.bbox)
            candidate_area = max((x2 - x1) * (y2 - y1), 1.0)
            inside_ratio = overlap / candidate_area
            if inside_ratio < 0.55:
                continue

            candidate_cx = (x1 + x2) / 2
            candidate_cy = (y1 + y2) / 2
            rel_x = (candidate_cx - px1) / person_w
            rel_y = (candidate_cy - py1) / person_h

            # Keep PPE matching anchored to plausible body regions.
            if ppe_type == "helmet":
                if 0.12 <= rel_x <= 0.88 and 0.0 <= rel_y <= 0.38:
                    return True
                continue
            if ppe_type == "vest":
                if 0.08 <= rel_x <= 0.92 and 0.25 <= rel_y <= 0.82:
                    return True
                continue

            if x1 >= px1 - 20 and x2 <= px2 + 20 and y1 >= py1 - 40 and y2 <= py2 + 40:
                return True
        return False

    @staticmethod
    def _intersection_area(
        left: tuple[float, float, float, float],
        right: tuple[float, float, float, float],
    ) -> float:
        lx1, ly1, lx2, ly2 = left
        rx1, ry1, rx2, ry2 = right
        ix1 = max(lx1, rx1)
        iy1 = max(ly1, ry1)
        ix2 = min(lx2, rx2)
        iy2 = min(ly2, ry2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        return (ix2 - ix1) * (iy2 - iy1)

    @staticmethod
    def _bottom_midpoint(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
        x1, _, x2, y2 = bbox
        return ((x1 + x2) / 2, y2)

    @staticmethod
    def _distance_between_boxes(
        left: tuple[float, float, float, float],
        right: tuple[float, float, float, float],
    ) -> float:
        lx1, ly1, lx2, ly2 = left
        rx1, ry1, rx2, ry2 = right
        lcx = (lx1 + lx2) / 2
        lcy = (ly1 + ly2) / 2
        rcx = (rx1 + rx2) / 2
        rcy = (ry1 + ry2) / 2
        return ((lcx - rcx) ** 2 + (lcy - rcy) ** 2) ** 0.5

    @staticmethod
    def _point_inside_polygon(point: tuple[float, float], zone: PolygonZone) -> bool:
        x, y = point
        inside = False
        points = zone.points
        j = len(points) - 1
        for i in range(len(points)):
            xi, yi = points[i].x, points[i].y
            xj, yj = points[j].x, points[j].y
            intersects = ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-6) + xi
            )
            if intersects:
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _overall_status(hazard_rows: list[dict]) -> StreamSafetyStatus:
        statuses = [row["status"] for row in hazard_rows]
        if StreamSafetyStatus.machine_proximity in statuses:
            return StreamSafetyStatus.machine_proximity
        if StreamSafetyStatus.no_go_zone in statuses:
            return StreamSafetyStatus.no_go_zone
        if StreamSafetyStatus.ppe_missing in statuses:
            return StreamSafetyStatus.ppe_missing
        return StreamSafetyStatus.safe

