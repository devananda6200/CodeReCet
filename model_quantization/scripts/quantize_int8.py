"""
Quantize OpenVINO FP32 model to INT8 using NNCF
"""
import argparse
from model_quantization.src.config import load_config
from model_quantization.src.quant_utils import quantize_model_int8

def main():
    parser = argparse.ArgumentParser(description="Quantize OpenVINO FP32 model to INT8 using NNCF")
    parser.add_argument('--config', type=str, default="../configs/default.yaml", help="Path to config YAML")
    args = parser.parse_args()
    cfg = load_config(args.config)
    quantize_model_int8(cfg)

if __name__ == "__main__":
    main()
