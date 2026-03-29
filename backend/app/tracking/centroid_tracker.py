from dataclasses import dataclass
from math import dist

from app.models.schemas import DetectionRecord


@dataclass
class TrackState:
    track_id: int
    centroid: tuple[float, float]
    bbox: tuple[float, float, float, float]
    class_name: str
    missed: int = 0


class CentroidTracker:
    def __init__(self, max_distance: float = 110.0, max_missed: int = 6) -> None:
        self.max_distance = max_distance
        self.max_missed = max_missed
        self._next_id = 1
        self._tracks: dict[int, TrackState] = {}

    def update(self, detections: list[DetectionRecord]) -> list[DetectionRecord]:
        assigned_tracks: set[int] = set()
        updated: list[DetectionRecord] = []

        for detection in detections:
            centroid = self._centroid(detection.bbox)
            candidate_id = self._match_track(detection.class_name, centroid, assigned_tracks)
            if candidate_id is None:
                candidate_id = self._next_id
                self._next_id += 1

            self._tracks[candidate_id] = TrackState(
                track_id=candidate_id,
                centroid=centroid,
                bbox=detection.bbox,
                class_name=detection.class_name,
                missed=0,
            )
            assigned_tracks.add(candidate_id)
            updated.append(detection.model_copy(update={"track_id": candidate_id}))

        self._age_missing_tracks(assigned_tracks)
        return updated

    def project(self) -> list[DetectionRecord]:
        projected: list[DetectionRecord] = []
        stale_ids: list[int] = []
        for track_id, track in self._tracks.items():
            track.missed += 1
            if track.missed > self.max_missed:
                stale_ids.append(track_id)
                continue
            # Only project very recent tracks; older projected tracks create visual trails.
            if track.missed > 1:
                continue
            projected.append(
                DetectionRecord(
                    track_id=track_id,
                    class_name=track.class_name,
                    confidence=max(0.4, 0.86 - track.missed * 0.08),
                    bbox=track.bbox,
                )
            )

        for track_id in stale_ids:
            self._tracks.pop(track_id, None)

        return projected

    def _match_track(
        self,
        class_name: str,
        centroid: tuple[float, float],
        assigned_tracks: set[int],
    ) -> int | None:
        best_track_id: int | None = None
        best_distance = self.max_distance
        for track_id, track in self._tracks.items():
            if track_id in assigned_tracks or track.class_name != class_name:
                continue
            current_distance = dist(track.centroid, centroid)
            if current_distance <= best_distance:
                best_distance = current_distance
                best_track_id = track_id
        return best_track_id

    def _age_missing_tracks(self, assigned_tracks: set[int]) -> None:
        stale_ids: list[int] = []
        for track_id, track in self._tracks.items():
            if track_id not in assigned_tracks:
                track.missed += 1
            if track.missed > self.max_missed:
                stale_ids.append(track_id)
        for track_id in stale_ids:
            self._tracks.pop(track_id, None)

    @staticmethod
    def _centroid(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

