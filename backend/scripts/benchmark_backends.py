from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np
import psutil


@dataclass
class BenchmarkResult:
    name: str
    artifact: str
    frames: int
    avg_inference_latency_ms: float
    avg_end_to_end_latency_ms: float
    fps: float
    avg_detection_agreement: float | None
    memory_mb: float
    cpu_percent: float
    threads: int
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark YOLO CPU backends and exported artifacts.")
    parser.add_argument("--baseline", default="models/best.pt", help="Baseline PyTorch checkpoint.")
    parser.add_argument("--onnx", default="", help="Optional ONNX artifact path.")
    parser.add_argument("--openvino", default="", help="Optional OpenVINO artifact path.")
    parser.add_argument("--quantized-onnx", default="", help="Optional INT8 ONNX artifact path.")
    parser.add_argument("--sample", default="", help="Optional sample video/image path.")
    parser.add_argument("--frames", type=int, default=32, help="Number of frames to benchmark.")
    parser.add_argument("--imgsz", type=int, default=960, help="Inference image size.")
    parser.add_argument("--threads", type=int, default=4, help="CPU thread budget.")
    parser.add_argument("--output", default="data/benchmark_results.json", help="Where to save benchmark JSON.")
    return parser.parse_args()


def load_frames(sample_path: str, frames: int, size: int) -> list[np.ndarray]:
    if sample_path:
        path = Path(sample_path)
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
            image = cv2.imread(str(path))
            if image is not None:
                return [cv2.resize(image, (size, size)) for _ in range(frames)]
        if path.is_file():
            capture = cv2.VideoCapture(str(path))
            loaded: list[np.ndarray] = []
            try:
                while len(loaded) < frames:
                    ok, frame = capture.read()
                    if not ok or frame is None:
                        break
                    loaded.append(cv2.resize(frame, (size, size)))
            finally:
                capture.release()
            if loaded:
                while len(loaded) < frames:
                    loaded.append(loaded[-1].copy())
                return loaded

    synthetic: list[np.ndarray] = []
    for idx in range(frames):
        frame = np.zeros((size, size, 3), dtype=np.uint8)
        frame[:, :, 0] = np.linspace(0, 180, size, dtype=np.uint8)
        frame[:, :, 1] = 40 + (idx * 3) % 120
        cv2.putText(frame, f"frame {idx}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        synthetic.append(frame)
    return synthetic


def load_model(artifact: str, threads: int):
    import torch
    from ultralytics import YOLO

    torch.set_num_threads(threads)
    return YOLO(artifact)


def run_candidate(
    name: str,
    artifact: str,
    frames: list[np.ndarray],
    imgsz: int,
    threads: int,
    baseline_boxes: list[list[tuple[str, tuple[float, float, float, float]]]] | None,
) -> BenchmarkResult:
    process = psutil.Process()
    started = perf_counter()
    try:
        model = load_model(artifact, threads)
        inference_latencies: list[float] = []
        candidate_boxes: list[list[tuple[str, tuple[float, float, float, float]]]] = []
        for frame in frames:
            infer_started = perf_counter()
            result = model.predict(source=frame, imgsz=imgsz, device="cpu", verbose=False)[0]
            inference_latencies.append((perf_counter() - infer_started) * 1000)
            names = result.names
            detections: list[tuple[str, tuple[float, float, float, float]]] = []
            for box in result.boxes:
                class_name = str(names[int(box.cls.item())])
                coords = tuple(float(value) for value in box.xyxy[0].tolist())
                detections.append((class_name, coords))
            candidate_boxes.append(detections)

        total_ms = (perf_counter() - started) * 1000
        agreement = (
            sum(compare_detections(candidate, baseline) for candidate, baseline in zip(candidate_boxes, baseline_boxes or candidate_boxes))
            / len(candidate_boxes)
        )
        return BenchmarkResult(
            name=name,
            artifact=str(Path(artifact).resolve()),
            frames=len(frames),
            avg_inference_latency_ms=round(sum(inference_latencies) / len(inference_latencies), 2),
            avg_end_to_end_latency_ms=round(total_ms / len(frames), 2),
            fps=round(len(frames) / max(total_ms / 1000, 1e-6), 2),
            avg_detection_agreement=round(agreement, 3) if baseline_boxes is not None else None,
            memory_mb=round(process.memory_info().rss / (1024 * 1024), 1),
            cpu_percent=round(psutil.cpu_percent(interval=None), 1),
            threads=threads,
        )
    except Exception as exc:
        return BenchmarkResult(
            name=name,
            artifact=str(Path(artifact).resolve()),
            frames=len(frames),
            avg_inference_latency_ms=0.0,
            avg_end_to_end_latency_ms=0.0,
            fps=0.0,
            avg_detection_agreement=None,
            memory_mb=round(process.memory_info().rss / (1024 * 1024), 1),
            cpu_percent=round(psutil.cpu_percent(interval=None), 1),
            threads=threads,
            error=str(exc),
        )


def compare_detections(
    candidate: list[tuple[str, tuple[float, float, float, float]]],
    baseline: list[tuple[str, tuple[float, float, float, float]]],
) -> float:
    if not baseline and not candidate:
        return 1.0
    if not baseline or not candidate:
        return 0.0

    matches = 0
    used = set()
    for class_name, bbox in candidate:
        for idx, (base_class, base_bbox) in enumerate(baseline):
            if idx in used or base_class != class_name:
                continue
            if iou(bbox, base_bbox) >= 0.5:
                matches += 1
                used.add(idx)
                break
    return matches / max(len(baseline), len(candidate))


def iou(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> float:
    lx1, ly1, lx2, ly2 = left
    rx1, ry1, rx2, ry2 = right
    inter_x1 = max(lx1, rx1)
    inter_y1 = max(ly1, ry1)
    inter_x2 = min(lx2, rx2)
    inter_y2 = min(ly2, ry2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0
    intersection = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    left_area = (lx2 - lx1) * (ly2 - ly1)
    right_area = (rx2 - rx1) * (ry2 - ry1)
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def extract_baseline_boxes(result: BenchmarkResult, frames: list[np.ndarray], imgsz: int, threads: int):
    if result.error:
        return None
    model = load_model(result.artifact, threads)
    outputs: list[list[tuple[str, tuple[float, float, float, float]]]] = []
    for frame in frames:
        prediction = model.predict(source=frame, imgsz=imgsz, device="cpu", verbose=False)[0]
        names = prediction.names
        detections: list[tuple[str, tuple[float, float, float, float]]] = []
        for box in prediction.boxes:
            class_name = str(names[int(box.cls.item())])
            coords = tuple(float(value) for value in box.xyxy[0].tolist())
            detections.append((class_name, coords))
        outputs.append(detections)
    return outputs


def main() -> None:
    args = parse_args()
    frames = load_frames(args.sample, args.frames, args.imgsz)
    candidates = [("fp32_baseline", args.baseline)]
    if args.onnx:
        candidates.append(("onnxruntime_cpu", args.onnx))
    if args.openvino:
        candidates.append(("openvino_cpu", args.openvino))
    if args.quantized_onnx:
        candidates.append(("onnx_int8", args.quantized_onnx))

    baseline_result = run_candidate("fp32_baseline", args.baseline, frames, args.imgsz, args.threads, None)
    baseline_boxes = extract_baseline_boxes(baseline_result, frames, args.imgsz, args.threads) if not baseline_result.error else None

    results: list[BenchmarkResult] = [baseline_result]
    for name, artifact in candidates[1:]:
        results.append(run_candidate(name, artifact, frames, args.imgsz, args.threads, baseline_boxes))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frames": args.frames,
        "imgsz": args.imgsz,
        "threads": args.threads,
        "results": [result.__dict__ for result in results],
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
