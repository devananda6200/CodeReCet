"""
Benchmark FP32 and INT8 OpenVINO models
"""
import argparse
from model_quantization.src.config import load_config
from model_quantization.src.benchmark_utils import benchmark_models

def main():
    parser = argparse.ArgumentParser(description="Benchmark FP32 and INT8 OpenVINO models")
    parser.add_argument('--config', type=str, default="../configs/default.yaml", help="Path to config YAML")
    args = parser.parse_args()
    cfg = load_config(args.config)
    benchmark_models(cfg)

if __name__ == "__main__":
    main()
