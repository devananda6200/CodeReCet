"""
tracker.py — Lightweight IoU-based object tracker with anti-flicker.

Assigns persistent track IDs to detections across frames using
Hungarian matching. On skipped frames (no inference), predicts
new positions via linear velocity extrapolation.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.config import settings
from app.models import BBox, Detection

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """Internal state for a tracked object."""
    track_id: int
    bbox: BBox
    class_id: int
    class_name: str
    confidence: float
    velocity: Tuple[float, float] = (0.0, 0.0)  # (dx, dy) per frame
    hits: int = 1               # Consecutive frames with match
    age: int = 0                # Total frames since creation
    disappeared: int = 0        # Consecutive frames without match
    emitted: bool = False       # Has reached anti-flicker threshold


class IoUTracker:
    """
    Multi-class IoU tracker with anti-flicker suppression.

    Features
    --------
    - Hungarian assignment via IoU cost matrix
    - Linear velocity prediction for skipped frames
    - Anti-flicker: detection must appear ≥ min_hits consecutive
      frames before being emitted to downstream stages
    - Grace period: tracks survive `max_disappeared` frames
      without a match before being pruned
    """

    def __init__(self) -> None:
        cfg = settings.pipeline
        self.iou_threshold = cfg.tracker_iou_threshold
        self.max_disappeared = cfg.tracker_max_disappeared
        self.min_hits = cfg.anti_flicker_min_hits
        self.velocity_alpha = cfg.tracker_velocity_smoothing

        self._tracks: OrderedDict[int, Track] = OrderedDict()
        self._next_id = 1

    # ── Public API ────────────────────────────────────────────────

    def update(self, detections: List[Detection]) -> List[Detection]:
        """
        Match new detections to existing tracks and return
        updated detections with track IDs.

        Only detections that have been consistently seen for
        at least `min_hits` frames are returned (anti-flicker).
        """
        if len(self._tracks) == 0:
            # First frame — register all detections
            for det in detections:
                self._register(det)
            return self._emit()

        if len(detections) == 0:
            # No detections — age all tracks
            for track in list(self._tracks.values()):
                track.disappeared += 1
                track.hits = 0
            self._prune()
            return self._emit()

        # Build IoU cost matrix
        track_ids = list(self._tracks.keys())
        track_list = [self._tracks[tid] for tid in track_ids]
        cost_matrix = np.zeros((len(track_list), len(detections)), dtype=np.float32)

        for t, trk in enumerate(track_list):
            for d, det in enumerate(detections):
                cost_matrix[t, d] = trk.bbox.iou(det.bbox)

        # Hungarian matching (maximise IoU → minimise negative IoU)
        row_indices, col_indices = linear_sum_assignment(-cost_matrix)

        matched_tracks: set[int] = set()
        matched_dets: set[int] = set()

        for r, c in zip(row_indices, col_indices):
            if cost_matrix[r, c] >= self.iou_threshold:
                tid = track_ids[r]
                self._update_track(tid, detections[c])
                matched_tracks.add(r)
                matched_dets.add(c)

        # Unmatched tracks → increment disappeared
        for t in range(len(track_list)):
            if t not in matched_tracks:
                tid = track_ids[t]
                self._tracks[tid].disappeared += 1
                self._tracks[tid].hits = 0

        # Unmatched detections → new tracks
        for d in range(len(detections)):
            if d not in matched_dets:
                self._register(detections[d])

        self._prune()
        return self._emit()

    def predict(self) -> List[Detection]:
        """
        On skipped frames (no inference), extrapolate tracked
        positions using stored velocities.

        Returns detections for currently emitted tracks.
        """
        for track in self._tracks.values():
            dx, dy = track.velocity
            track.bbox = BBox(
                x1=track.bbox.x1 + dx,
                y1=track.bbox.y1 + dy,
                x2=track.bbox.x2 + dx,
                y2=track.bbox.y2 + dy,
            )
            track.age += 1

        return self._emit()

    def reset(self) -> None:
        """Clear all tracks."""
        self._tracks.clear()
        self._next_id = 1

    # ── Internal ──────────────────────────────────────────────────

    def _register(self, det: Detection) -> None:
        """Create a new track from a detection."""
        tid = self._next_id
        self._next_id += 1
        self._tracks[tid] = Track(
            track_id=tid,
            bbox=det.bbox,
            class_id=det.class_id,
            class_name=det.class_name,
            confidence=det.confidence,
        )

    def _update_track(self, tid: int, det: Detection) -> None:
        """Update an existing track with a matched detection."""
        trk = self._tracks[tid]

        # Compute velocity (EMA-smoothed)
        old_cx, old_cy = trk.bbox.center
        new_cx, new_cy = det.bbox.center
        dx = new_cx - old_cx
        dy = new_cy - old_cy
        alpha = self.velocity_alpha
        trk.velocity = (
            alpha * dx + (1 - alpha) * trk.velocity[0],
            alpha * dy + (1 - alpha) * trk.velocity[1],
        )

        trk.bbox = det.bbox
        trk.class_id = det.class_id
        trk.class_name = det.class_name
        trk.confidence = det.confidence
        trk.hits += 1
        trk.age += 1
        trk.disappeared = 0

        if trk.hits >= self.min_hits:
            trk.emitted = True

    def _prune(self) -> None:
        """Remove tracks that have disappeared for too long."""
        to_remove = [
            tid for tid, trk in self._tracks.items()
            if trk.disappeared > self.max_disappeared
        ]
        for tid in to_remove:
            del self._tracks[tid]

    def _emit(self) -> List[Detection]:
        """Return detections for tracks that have met the anti-flicker threshold."""
        result: List[Detection] = []
        for trk in self._tracks.values():
            if trk.emitted:
                result.append(Detection(
                    bbox=trk.bbox,
                    class_id=trk.class_id,
                    class_name=trk.class_name,
                    confidence=trk.confidence,
                    track_id=trk.track_id,
                ))
        return result
