from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from onnxruntime.quantization import QuantType, quantize_dynamic


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export YOLO11 checkpoints for CPU-oriented deployment.")
    parser.add_argument("--model", default="models/best.pt", help="Path to the trained PyTorch checkpoint.")
    parser.add_argument("--output-dir", default="models/exports", help="Directory for exported artifacts.")
    parser.add_argument("--imgsz", type=int, default=960, help="Export image size.")
    parser.add_argument("--dynamic", action="store_true", help="Enable dynamic ONNX axes.")
    parser.add_argument("--onnx", action="store_true", help="Export ONNX format.")
    parser.add_argument("--openvino", action="store_true", help="Export OpenVINO format.")
    parser.add_argument("--quantize-onnx-int8", action="store_true", help="Create a dynamically quantized ONNX INT8 artifact.")
    return parser.parse_args()


def export_yolo_artifact(model_path: Path, output_dir: Path, fmt: str, imgsz: int, dynamic: bool) -> Path:
    from ultralytics import YOLO

    output_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(model_path))
    exported_path = model.export(format=fmt, imgsz=imgsz, dynamic=dynamic, device="cpu")
    exported = Path(exported_path)
    target = output_dir / exported.name
    if exported.resolve() != target.resolve():
        if exported.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(exported, target)
        else:
            shutil.copy2(exported, target)
    return target


def quantize_onnx_model(onnx_path: Path) -> Path:
    quantized_path = onnx_path.with_name(f"{onnx_path.stem}.int8{onnx_path.suffix}")
    quantize_dynamic(
        model_input=str(onnx_path),
        model_output=str(quantized_path),
        weight_type=QuantType.QInt8,
    )
    return quantized_path


def main() -> None:
    args = parse_args()
    model_path = Path(args.model).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, str] = {}
    if args.onnx or args.quantize_onnx_int8 or (not args.onnx and not args.openvino):
        onnx_path = export_yolo_artifact(model_path, output_dir, "onnx", args.imgsz, args.dynamic)
        artifacts["onnx"] = str(onnx_path)
        if args.quantize_onnx_int8:
            artifacts["onnx_int8"] = str(quantize_onnx_model(onnx_path))

    if args.openvino:
        openvino_path = export_yolo_artifact(model_path, output_dir, "openvino", args.imgsz, args.dynamic)
        artifacts["openvino"] = str(openvino_path)

    manifest = {
        "model": str(model_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "imgsz": args.imgsz,
        "dynamic": args.dynamic,
        "artifacts": artifacts,
    }
    manifest_path = output_dir / "export_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
