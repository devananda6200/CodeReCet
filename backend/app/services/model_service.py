from __future__ import annotations

import os
import threading
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from app.models.schemas import BackendChoice, DetectionRecord, RuntimeConfig


class ModelService:
    """Loads the selected YOLO artifact lazily and falls back to deterministic demo detections."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model: Any | None = None
        self._model_signature: tuple[str, str, int, str] | None = None
        self._last_error: str | None = None
        self._runtime_mode: str = "mock"

    def predict(
        self,
        frame: np.ndarray,
        config: RuntimeConfig,
        frame_index: int,
        stream_seed: int,
    ) -> tuple[list[DetectionRecord], float, str]:
        started = perf_counter()
        runtime_artifact = self._resolve_runtime_artifact(config)
        self._ensure_loaded(config, runtime_artifact)

        if self._model is None:
            detections = self._mock_detections(frame, frame_index, stream_seed)
            latency_ms = (perf_counter() - started) * 1000
            return detections, latency_ms, "mock"

        try:
            results = self._model.predict(
                source=frame,
                conf=config.confidence_threshold,
                iou=config.iou_threshold,
                imgsz=config.input_size,
                device="cpu",
                verbose=False,
            )
            detections = self._parse_results(results)
            detections = [
                detection.model_copy(update={"class_name": self._apply_label_remap(detection.class_name, config)})
                for detection in detections
            ]
            latency_ms = (perf_counter() - started) * 1000
            return detections, latency_ms, self._runtime_mode
        except Exception as exc:  # pragma: no cover - depends on local runtime
            self._last_error = str(exc)
            detections = self._mock_detections(frame, frame_index, stream_seed)
            latency_ms = (perf_counter() - started) * 1000
            return detections, latency_ms, "mock"

    def last_error(self) -> str | None:
        return self._last_error

    def _ensure_loaded(self, config: RuntimeConfig, runtime_artifact: Path) -> None:
        signature = (config.model_path, config.backend.value, config.cpu_threads, str(runtime_artifact))
        if self._model_signature == signature:
            return

        with self._lock:
            if self._model_signature == signature:
                return

            if not runtime_artifact.exists():
                self._model = None
                self._model_signature = signature
                self._runtime_mode = "mock"
                self._last_error = f"Model artifact not found at {runtime_artifact}"
                return

            try:  # pragma: no cover - optional runtime path
                import torch
                from ultralytics import YOLO

                torch.set_num_threads(config.cpu_threads)
                os.environ["OMP_NUM_THREADS"] = str(config.cpu_threads)
                os.environ["OPENBLAS_NUM_THREADS"] = str(config.cpu_threads)
                self._model = YOLO(str(runtime_artifact))
                self._model_signature = signature
                self._runtime_mode = config.backend.value
                self._last_error = None
            except Exception as exc:  # pragma: no cover - optional runtime path
                self._model = None
                self._model_signature = signature
                self._runtime_mode = "mock"
                self._last_error = str(exc)

    def _resolve_runtime_artifact(self, config: RuntimeConfig) -> Path:
        model_path = Path(config.model_path)
        if config.backend == BackendChoice.pytorch:
            return model_path

        exports_dir = model_path.parent / "exports"
        model_stem = model_path.stem

        if config.backend == BackendChoice.onnx:
            if model_path.suffix.lower() == ".onnx":
                return model_path

            preferred_candidates = [
                exports_dir / f"{model_stem}.int8.onnx",
                exports_dir / f"{model_stem}.onnx",
                model_path.with_suffix(".int8.onnx"),
                model_path.with_suffix(".onnx"),
            ]
            for candidate in preferred_candidates:
                if candidate.exists():
                    return candidate
            return preferred_candidates[0]

        if config.backend == BackendChoice.openvino:
            if model_path.is_dir():
                return model_path
            if model_path.suffix.lower() == ".xml":
                return model_path

            preferred_candidates = [
                exports_dir / f"{model_stem}_openvino_model",
                model_path.parent / f"{model_stem}_openvino_model",
            ]
            for candidate in preferred_candidates:
                if candidate.exists():
                    return candidate
            return preferred_candidates[0]

        return model_path

    def _parse_results(self, results: Any) -> list[DetectionRecord]:
        parsed: list[DetectionRecord] = []
        if not results:
            return parsed

        result = results[0]
        names = result.names
        for box in result.boxes:
            class_id = int(box.cls.item())
            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
            class_name = self._normalize_class_name(str(names[class_id]))
            parsed.append(
                DetectionRecord(
                    class_name=class_name,
                    confidence=float(box.conf.item()),
                    bbox=(x1, y1, x2, y2),
                )
            )
        return parsed

    def _apply_label_remap(self, class_name: str, config: RuntimeConfig) -> str:
        if not config.label_remap:
            return class_name

        normalized_map = {
            key.strip().lower().replace("-", "_").replace(" ", "_"): value.strip().lower().replace("-", "_").replace(" ", "_")
            for key, value in config.label_remap.items()
            if key and value
        }
        return normalized_map.get(class_name, class_name)

    @staticmethod
    def _normalize_class_name(class_name: str) -> str:
        normalized = class_name.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "persons": "person",
            "person": "person",
            "worker": "person",
            "workers": "person",
            "helmets": "helmet",
            "helmet": "helmet",
            "hardhat": "helmet",
            "hard_hat": "helmet",
            "vests": "safety_vest",
            "vest": "safety_vest",
            "ppe_vest": "safety_vest",
            "safety_vest": "safety_vest",
            "jacket": "safety_vest",
        }
        return aliases.get(normalized, normalized)

    def _mock_detections(
        self,
        frame: np.ndarray,
        frame_index: int,
        stream_seed: int,
    ) -> list[DetectionRecord]:
        height, width = frame.shape[:2]
        available_span = max(width - 260, 1)
        person_x = 80 + (abs(stream_seed) % min(available_span, 240))
        person_box = (float(person_x), float(height * 0.28), float(person_x + 120), float(height * 0.84))
        machine_box = (float(width * 0.68), float(height * 0.32), float(width * 0.92), float(height * 0.82))

        detections = [
            DetectionRecord(class_name="person", confidence=0.92, bbox=person_box),
            DetectionRecord(class_name="machine", confidence=0.88, bbox=machine_box),
            DetectionRecord(
                class_name="helmet",
                confidence=0.86,
                bbox=(person_box[0] + 18, person_box[1] - 10, person_box[0] + 102, person_box[1] + 62),
            ),
            DetectionRecord(
                class_name="safety_vest",
                confidence=0.84,
                bbox=(person_box[0] + 10, person_box[1] + 120, person_box[2] - 10, person_box[1] + 280),
            ),
        ]

        return detections
