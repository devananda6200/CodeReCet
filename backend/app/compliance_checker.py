"""
compliance_checker.py — Spatial PPE compliance logic.

For each detected person, checks whether a helmet overlaps
the head region and a safety vest overlaps the torso region.
Outputs a ComplianceResult per person.
"""

from __future__ import annotations

import logging
from typing import List

from app.config import settings
from app.models import (
    BBox,
    ComplianceResult,
    ComplianceStatus,
    Detection,
)

logger = logging.getLogger(__name__)


class ComplianceChecker:
    """
    Determines PPE compliance by spatial association.

    For each `person` detection:
    - Head region = top `head_region_ratio` of the person bbox
    - Torso region = from `torso_region_top` to `torso_region_bottom` of the bbox
    - A `helmet` overlapping the head region → helmet present
    - A `safety_vest` overlapping the torso region → vest present
    """

    def __init__(self) -> None:
        cfg = settings.compliance
        self.head_ratio = cfg.head_region_ratio
        self.torso_top = cfg.torso_region_top
        self.torso_bottom = cfg.torso_region_bottom
        self.overlap_threshold = cfg.overlap_iou_threshold

    def check(self, detections: List[Detection]) -> List[ComplianceResult]:
        """
        Evaluate compliance for all persons in the detection list.

        Parameters
        ----------
        detections : List[Detection]
            Tracked detections for the current frame.

        Returns
        -------
        List[ComplianceResult]
            One result per detected person.
        """
        persons = [d for d in detections if d.class_name == "person"]
        helmets = [d for d in detections if d.class_name == "helmet"]
        vests = [d for d in detections if d.class_name == "safety_vest"]

        results: List[ComplianceResult] = []

        for person in persons:
            head_region = person.bbox.sub_region(0.0, self.head_ratio)
            torso_region = person.bbox.sub_region(self.torso_top, self.torso_bottom)

            # Find best matching helmet
            matched_helmet = self._best_match(head_region, helmets)
            has_helmet = matched_helmet is not None

            # Find best matching vest
            matched_vest = self._best_match(torso_region, vests)
            has_vest = matched_vest is not None

            # Determine status
            if has_helmet and has_vest:
                status = ComplianceStatus.COMPLIANT
            elif not has_helmet and not has_vest:
                status = ComplianceStatus.NON_COMPLIANT
            elif not has_helmet:
                status = ComplianceStatus.HELMET_MISSING
            else:
                status = ComplianceStatus.VEST_MISSING

            results.append(ComplianceResult(
                person_detection=person,
                has_helmet=has_helmet,
                has_vest=has_vest,
                status=status,
                matched_helmet=matched_helmet,
                matched_vest=matched_vest,
            ))

        return results

    # ── Internal ──────────────────────────────────────────────────

    def _best_match(
        self,
        region: BBox,
        candidates: List[Detection],
    ) -> Detection | None:
        """Return the candidate with highest IoU above threshold, or None."""
        best: Detection | None = None
        best_iou = self.overlap_threshold

        for det in candidates:
            iou = region.iou(det.bbox)
            if iou > best_iou:
                best_iou = iou
                best = det

        return best
