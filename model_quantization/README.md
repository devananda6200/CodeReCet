# Model Quantization Workflow for PPE Detection (YOLO11 + OpenVINO)

This module provides an isolated, reproducible workflow for exporting, quantizing, and benchmarking a YOLO11 PPE detection model using OpenVINO and NNCF. All outputs are contained within this folder for safe collaboration.

## Purpose
- Export YOLO11 PyTorch model to OpenVINO IR (FP32)
- INT8 post-training quantization with NNCF
- Benchmarking FP32 vs INT8 models
- Configurable, hackathon-friendly scripts

## Prerequisites
- Python 3.8+
- PyTorch (for export)
- OpenVINO >=2023.0
- NNCF >=2.6.0
- numpy, opencv-python, pyyaml

## Installation
```bash
cd model_quantization
python -m venv .venv
.venv\Scripts\activate  # or source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration
Edit `configs/default.yaml` to set paths for:
- `source_pt_model_path`: Path to YOLO11 .pt file
- `openvino_export_dir`: Output dir for FP32 IR
- `int8_output_dir`: Output dir for INT8 IR
- `calibration_images_dir`: Folder with calibration images
- `calibration_sample_size`: Number of images for calibration
- `imgsz`: Image size
- `device`: "CPU"
- `class_names`: Class index mapping

## Export to OpenVINO IR
```bash
python scripts/export_openvino.py --config configs/default.yaml
```
- Exports YOLO11 PyTorch model to OpenVINO IR (FP32) in `artifacts/openvino_fp32/`

## INT8 Quantization
```bash
python scripts/quantize_int8.py --config configs/default.yaml
```
- Quantizes FP32 IR to INT8 using NNCF and calibration images
- Output in `artifacts/openvino_int8/`

## Benchmarking
```bash
python scripts/benchmark_models.py --config configs/default.yaml
```
- Compares FP32 and INT8 models on CPU
- Reports latency, throughput, file size
- Results in `artifacts/`

## Notes
- All outputs are written inside `model_quantization/artifacts/`
- No changes are made to other parts of the repository
- No dataset files are committed
- Paths are configurable via YAML

## Expected Inputs/Outputs
- **Input:** Trained YOLO11 .pt model, calibration images folder
- **Output:** OpenVINO FP32 and INT8 models, benchmark results

---
For details, see comments in each script. For help, contact the maintainers.
