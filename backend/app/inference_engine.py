"""
inference_engine.py — Pluggable YOLO inference backends.

Supports PyTorch (Ultralytics), ONNX Runtime, and OpenVINO.
The active backend is selected by config and can be swapped at
startup without changing any other module.
"""

from __future__ import annotations

import abc
import logging
from typing import Any

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Abstract base
# ═══════════════════════════════════════════════════════════════════

class InferenceBackend(abc.ABC):
    """Common interface for all YOLO inference backends."""

    @abc.abstractmethod
    def load(self, model_path: str) -> None:
        """Load the model from disk."""
        ...

    @abc.abstractmethod
    def infer(self, tensor: np.ndarray) -> np.ndarray:
        """
        Run inference on a preprocessed tensor.

        Parameters
        ----------
        tensor : np.ndarray
            Shape (1, 3, H, W), float32, range [0, 1].

        Returns
        -------
        np.ndarray
            Raw model output — shape varies by backend, but typically
            (1, num_classes + 4, num_detections) for YOLO.
        """
        ...

    @abc.abstractmethod
    def warmup(self) -> None:
        """Run a dummy inference to warm caches."""
        ...


# ═══════════════════════════════════════════════════════════════════
# PyTorch (Ultralytics) backend
# ═══════════════════════════════════════════════════════════════════

class PyTorchBackend(InferenceBackend):
    """Uses the Ultralytics YOLO Python API."""

    def __init__(self) -> None:
        self._model: Any = None

    def load(self, model_path: str) -> None:
        from ultralytics import YOLO
        self._model = YOLO(model_path, task="detect")
        logger.info("PyTorch backend loaded: %s", model_path)

    def infer(self, tensor: np.ndarray) -> np.ndarray:
        """
        Run Ultralytics predict and return raw result tensors.

        We call model.predict with the numpy tensor and extract
        the raw boxes output.
        """
        import torch
        # Ultralytics treats 4D numpy arrays as images by mistake.
        # Passing a torch.Tensor bypasses internal image preprocessing.
        tensor_pt = torch.from_numpy(tensor)
        
        results = self._model.predict(
            source=tensor_pt,
            conf=settings.model.confidence_threshold,
            iou=settings.model.nms_iou_threshold,
            verbose=False,
            device="cpu",
        )
        # Return the Ultralytics Results object directly —
        # the postprocessor knows how to handle both raw arrays
        # and Ultralytics Results.
        return results

    def warmup(self) -> None:
        dummy = np.zeros(
            (1, 3, settings.model.input_size, settings.model.input_size),
            dtype=np.float32,
        )
        self.infer(dummy)
        logger.info("PyTorch backend warmed up")


# ═══════════════════════════════════════════════════════════════════
# ONNX Runtime backend
# ═══════════════════════════════════════════════════════════════════

class ONNXBackend(InferenceBackend):
    """Uses ONNX Runtime with CPU execution provider."""

    def __init__(self) -> None:
        self._session: Any = None
        self._input_name: str = ""
        self._output_names: list[str] = []

    def load(self, model_path: str) -> None:
        import onnxruntime as ort

        sess_opts = ort.SessionOptions()
        sess_opts.inter_op_num_threads = settings.resources.onnx_inter_threads
        sess_opts.intra_op_num_threads = settings.resources.onnx_intra_threads
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self._session = ort.InferenceSession(
            model_path,
            sess_options=sess_opts,
            providers=["CPUExecutionProvider"],
        )
        self._input_name = self._session.get_inputs()[0].name
        self._output_names = [o.name for o in self._session.get_outputs()]
        logger.info("ONNX backend loaded: %s (inputs=%s, outputs=%s)",
                     model_path, self._input_name, self._output_names)

    def infer(self, tensor: np.ndarray) -> np.ndarray:
        outputs = self._session.run(
            self._output_names,
            {self._input_name: tensor},
        )
        return outputs[0]  # Primary output tensor

    def warmup(self) -> None:
        dummy = np.zeros(
            (1, 3, settings.model.input_size, settings.model.input_size),
            dtype=np.float32,
        )
        self.infer(dummy)
        logger.info("ONNX backend warmed up")


# ═══════════════════════════════════════════════════════════════════
# OpenVINO backend
# ═══════════════════════════════════════════════════════════════════

class OpenVINOBackend(InferenceBackend):
    """Uses OpenVINO Inference Engine with CPU plugin."""

    def __init__(self) -> None:
        self._compiled_model: Any = None
        self._infer_request: Any = None
        self._input_layer: Any = None
        self._output_layer: Any = None

    def load(self, model_path: str) -> None:
        import openvino as ov
        from pathlib import Path
        
        model_path = Path(model_path) if not isinstance(model_path, Path) else model_path
        
        # Handle directory paths by looking for best.xml or model.xml
        if model_path.is_dir():
            xml_candidates = list(model_path.glob("*.xml"))
            if xml_candidates:
                model_path = xml_candidates[0]
            else:
                raise FileNotFoundError(f"No .xml model file found in {model_path}")
        
        # Load model using OpenVINO API
        core = ov.Core()
        model = core.read_model(str(model_path))
        self._compiled_model = core.compile_model(
            model,
            device_name="CPU",
            config={
                "NUM_STREAMS": str(settings.resources.openvino_num_requests),
                "INFERENCE_NUM_THREADS": str(settings.resources.max_cpu_cores),
            },
        )
        self._infer_request = self._compiled_model.create_infer_request()
        self._input_layer = self._compiled_model.input(0)
        self._output_layer = self._compiled_model.output(0)
        logger.info("OpenVINO backend loaded: %s", model_path.parent.name)

    def infer(self, tensor: np.ndarray) -> np.ndarray:
        self._infer_request.infer({self._input_layer: tensor})
        return self._infer_request.get_output_tensor(0).data.copy()

    def warmup(self) -> None:
        dummy = np.zeros(
            (1, 3, settings.model.input_size, settings.model.input_size),
            dtype=np.float32,
        )
        self.infer(dummy)
        logger.info("OpenVINO backend warmed up")


# ═══════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════

_BACKENDS = {
    "pytorch": PyTorchBackend,
    "onnx": ONNXBackend,
    "openvino": OpenVINOBackend,
}


def create_engine(backend: str | None = None) -> InferenceBackend:
    """
    Instantiate and load the configured inference backend.

    Parameters
    ----------
    backend : str, optional
        Override the config backend name (pytorch / onnx / openvino).

    Returns
    -------
    InferenceBackend
        Ready-to-use backend with the model loaded and warmed up.
    """
    name = (backend or settings.model.backend).lower()
    if name not in _BACKENDS:
        raise ValueError(f"Unknown backend '{name}'. Choose from: {list(_BACKENDS)}")

    engine = _BACKENDS[name]()
    model_path = str(settings.project_root / settings.model.path)
    logger.info("Initialising '%s' backend with model: %s", name, model_path)
    engine.load(model_path)
    engine.warmup()
    return engine
