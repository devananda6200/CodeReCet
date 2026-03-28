"""
Export YOLO11 PyTorch model to OpenVINO IR (FP32)
"""
import argparse
from model_quantization.src.config import load_config
from model_quantization.src.export_utils import export_to_openvino

def main():
    parser = argparse.ArgumentParser(description="Export YOLO11 PyTorch model to OpenVINO IR (FP32)")
    parser.add_argument('--config', type=str, default="../configs/default.yaml", help="Path to config YAML")
    args = parser.parse_args()
    cfg = load_config(args.config)
    export_to_openvino(cfg)

if __name__ == "__main__":
    main()
