"""
postprocessor.py — Parse raw YOLO output into Detection objects.

Handles both raw ONNX/OpenVINO tensor output and Ultralytics
Results objects. Applies confidence filtering and coordinate
rescaling back to original frame coordinates.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

from app.config import settings
from app.models import BBox, Detection

logger = logging.getLogger(__name__)


class Postprocessor:
    """Converts raw model output into a list of Detection objects."""

    def __init__(self) -> None:
        self.conf_threshold = settings.model.confidence_threshold
        self.iou_threshold = settings.model.nms_iou_threshold
        self.class_map = settings.classes

    def process(self, raw_output: Any, meta: Dict) -> List[Detection]:
        """
        Parse model output and return rescaled detections.

        Parameters
        ----------
        raw_output
            Either a numpy array (ONNX/OpenVINO) or an Ultralytics
            Results list (PyTorch backend).
        meta : dict
            Preprocessing metadata from preprocessor (ratio, padding, etc.).

        Returns
        -------
        List[Detection]
        """
        # Ultralytics Results path
        if not isinstance(raw_output, np.ndarray):
            return self._parse_ultralytics(raw_output, meta)

        # Raw tensor path (ONNX / OpenVINO)
        return self._parse_raw_tensor(raw_output, meta)

    # ── Ultralytics path ──────────────────────────────────────────

    def _parse_ultralytics(self, results: Any, meta: Dict) -> List[Detection]:
        """Extract detections from Ultralytics Results objects."""
        detections: List[Detection] = []

        for result in results:
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue

            for i in range(len(boxes)):
                conf = float(boxes.conf[i])
                if conf < self.conf_threshold:
                    continue

                cls_id = int(boxes.cls[i])
                xyxy = boxes.xyxy[i].cpu().numpy()

                # Rescale from model input coords → original frame coords
                bbox = self._rescale_box(
                    xyxy[0], xyxy[1], xyxy[2], xyxy[3], meta
                )

                class_name = self.class_map.get(cls_id, f"class_{cls_id}")
                detections.append(Detection(
                    bbox=bbox,
                    class_id=cls_id,
                    class_name=class_name,
                    confidence=conf,
                ))

        return detections

    # ── Raw tensor path (ONNX / OpenVINO) ─────────────────────────

    def _parse_raw_tensor(self, output: np.ndarray, meta: Dict) -> List[Detection]:
        """
        Parse the standard YOLO output tensor.

        Expected shape: (1, 4 + num_classes, num_predictions) — transposed YOLO format
        or (1, num_predictions, 4 + num_classes).
        """
        # Squeeze batch dim
        if output.ndim == 3:
            output = output[0]

        # YOLO v8/11 output is (4+nc, N) — transpose to (N, 4+nc)
        if output.shape[0] < output.shape[1]:
            output = output.T

        num_predictions = output.shape[0]
        num_classes = settings.num_classes

        detections: List[Detection] = []
        boxes_for_nms: List[List[float]] = []
        scores_for_nms: List[float] = []
        class_ids_for_nms: List[int] = []

        for i in range(num_predictions):
            # First 4 values: cx, cy, w, h
            cx, cy, w, h = output[i, :4]
            class_scores = output[i, 4: 4 + num_classes]

            max_cls = int(np.argmax(class_scores))
            max_conf = float(class_scores[max_cls])

            if max_conf < self.conf_threshold:
                continue

            # Convert cx, cy, w, h → x1, y1, x2, y2
            x1 = cx - w / 2
            y1 = cy - h / 2
            x2 = cx + w / 2
            y2 = cy + h / 2

            boxes_for_nms.append([x1, y1, x2, y2])
            scores_for_nms.append(max_conf)
            class_ids_for_nms.append(max_cls)

        # Class-agnostic NMS
        if len(boxes_for_nms) > 0:
            keep = self._nms(
                np.array(boxes_for_nms),
                np.array(scores_for_nms),
                self.iou_threshold,
            )
            for idx in keep:
                x1, y1, x2, y2 = boxes_for_nms[idx]
                bbox = self._rescale_box(x1, y1, x2, y2, meta)
                cls_id = class_ids_for_nms[idx]
                class_name = self.class_map.get(cls_id, f"class_{cls_id}")
                detections.append(Detection(
                    bbox=bbox,
                    class_id=cls_id,
                    class_name=class_name,
                    confidence=scores_for_nms[idx],
                ))

        return detections

    # ── NMS ───────────────────────────────────────────────────────

    @staticmethod
    def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float) -> List[int]:
        """Simple greedy NMS. Returns indices to keep."""
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)

        order = scores.argsort()[::-1]
        keep: List[int] = []

        while order.size > 0:
            i = order[0]
            keep.append(int(i))

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            union = areas[i] + areas[order[1:]] - inter
            ious = inter / np.maximum(union, 1e-6)

            inds = np.where(ious <= iou_thresh)[0]
            order = order[inds + 1]

        return keep

    # ── Coordinate rescaling ──────────────────────────────────────

    @staticmethod
    def _rescale_box(
        x1: float, y1: float, x2: float, y2: float,
        meta: Dict,
    ) -> BBox:
        """Undo letterbox padding + scaling to get original-frame coords."""
        pad_w = meta.get("pad_w", 0)
        pad_h = meta.get("pad_h", 0)
        ratio = meta.get("ratio", 1.0)

        x1 = (x1 - pad_w) / ratio
        y1 = (y1 - pad_h) / ratio
        x2 = (x2 - pad_w) / ratio
        y2 = (y2 - pad_h) / ratio

        # Clamp to original frame
        orig_w = meta.get("orig_w", 99999)
        orig_h = meta.get("orig_h", 99999)
        x1 = max(0, min(x1, orig_w))
        y1 = max(0, min(y1, orig_h))
        x2 = max(0, min(x2, orig_w))
        y2 = max(0, min(y2, orig_h))

        return BBox(x1=x1, y1=y1, x2=x2, y2=y2)
