"""
preprocessor.py — Frame preprocessing for YOLO inference.

Handles letterbox resize, colour conversion, normalization,
and HWC→CHW transposition. Uses pre-allocated buffers to
reduce memory churn.
"""

from __future__ import annotations

import logging
from typing import Tuple

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class Preprocessor:
    """
    Prepares raw BGR frames for YOLO inference.

    Maintains a reusable buffer to avoid repeated allocation.
    Output shape: (1, 3, input_size, input_size), float32, 0-1 range.
    """

    def __init__(self, input_size: int | None = None):
        self.input_size = input_size or settings.model.input_size
        # Pre-allocated output buffer
        self._buffer: np.ndarray = np.zeros(
            (1, 3, self.input_size, self.input_size), dtype=np.float32
        )
        # Letterbox fill colour (grey)
        self._pad_colour = (114, 114, 114)

    def preprocess(
        self,
        frame: np.ndarray,
        target_width: int | None = None,
    ) -> Tuple[np.ndarray, dict]:
        """
        Preprocess a single BGR frame for inference.

        Parameters
        ----------
        frame : np.ndarray
            Raw BGR frame from the decoder (H, W, 3).
        target_width : int, optional
            If given, resize frame to this width first (adaptive resolution).

        Returns
        -------
        tensor : np.ndarray
            Preprocessed tensor of shape (1, 3, H, W), float32.
        meta : dict
            Metadata needed for post-processing (scale, padding).
        """
        # 1. Optional adaptive downscale
        if target_width is not None and frame.shape[1] > target_width:
            scale = target_width / frame.shape[1]
            new_h = int(frame.shape[0] * scale)
            frame = cv2.resize(frame, (target_width, new_h), interpolation=cv2.INTER_LINEAR)

        orig_h, orig_w = frame.shape[:2]

        # 2. Letterbox resize to square input
        img, ratio, (pad_w, pad_h) = self._letterbox(
            frame, (self.input_size, self.input_size)
        )

        # 3. BGR → RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 4. HWC → CHW, normalize to [0, 1]
        img = img.astype(np.float32) / 255.0
        img = np.ascontiguousarray(img.transpose(2, 0, 1))  # (3, H, W)

        # 5. Add batch dimension → (1, 3, H, W)
        np.copyto(self._buffer[0], img)

        meta = {
            "orig_h": orig_h,
            "orig_w": orig_w,
            "ratio": ratio,
            "pad_w": pad_w,
            "pad_h": pad_h,
            "input_size": self.input_size,
        }

        return self._buffer, meta

    # ── Letterbox ─────────────────────────────────────────────────

    def _letterbox(
        self,
        img: np.ndarray,
        new_shape: Tuple[int, int],
    ) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Resize and pad image to `new_shape` while preserving aspect ratio.
        """
        h, w = img.shape[:2]
        target_h, target_w = new_shape

        # Compute scale (fit shorter side)
        ratio = min(target_w / w, target_h / h)
        new_w = int(round(w * ratio))
        new_h = int(round(h * ratio))

        # Resize
        if (new_w, new_h) != (w, h):
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Compute padding
        pad_w = (target_w - new_w) // 2
        pad_h = (target_h - new_h) // 2

        # Add border
        img = cv2.copyMakeBorder(
            img,
            pad_h, target_h - new_h - pad_h,
            pad_w, target_w - new_w - pad_w,
            cv2.BORDER_CONSTANT,
            value=self._pad_colour,
        )

        return img, ratio, (pad_w, pad_h)
