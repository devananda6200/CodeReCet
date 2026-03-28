import os
from pathlib import Path
import numpy as np
import time
import logging
import openvino as ov

logger = logging.getLogger(__name__)

def benchmark_models(cfg):
    """
    Benchmark FP32 and INT8 OpenVINO models on CPU.
    Compares latency, throughput, and model size.
    """
    fp32_dir = Path(cfg['openvino_export_dir'])
    int8_dir = Path(cfg['int8_output_dir'])
    imgsz = cfg.get('imgsz', 640)
    num_inferences = 100
    
    ie = ov.Core()
    
    results = {}
    
    # Benchmark FP32 model
    try:
        fp32_model_xml = list(fp32_dir.rglob('*.xml'))[0]
        logger.info(f"Benchmarking FP32 model: {fp32_model_xml}")
        fp32_model = ie.read_model(str(fp32_model_xml))
        compiled_fp32 = ie.compile_model(fp32_model, device_name="CPU")
        
        # Warmup
        input_shape = compiled_fp32.input(0).shape
        dummy_input = {compiled_fp32.input(0).any_name: np.random.rand(*input_shape).astype(np.float32)}
        compiled_fp32(dummy_input)
        
        # Benchmark
        times = []
        for _ in range(num_inferences):
            start = time.time()
            compiled_fp32(dummy_input)
            times.append(time.time() - start)
        
        fp32_latency = np.mean(times[10:]) * 1000  # Skip warmup, convert to ms
        fp32_throughput = 1000.0 / fp32_latency
        fp32_size = sum(f.stat().st_size for f in fp32_dir.rglob('*') if f.is_file()) / (1024*1024)  # MB
        
        results['fp32'] = {
            'latency_ms': round(fp32_latency, 2),
            'throughput_fps': round(fp32_throughput, 2),
            'model_size_mb': round(fp32_size, 2)
        }
        logger.info(f"FP32: {fp32_latency:.2f}ms latency, {fp32_throughput:.2f} fps")
    except Exception as e:
        logger.error(f"Failed to benchmark FP32: {e}")
        results['fp32'] = {'error': str(e)}
    
    # Benchmark INT8 model
    try:
        int8_model_xml = list(int8_dir.rglob('*.xml'))[0]
        logger.info(f"Benchmarking INT8 model: {int8_model_xml}")
        int8_model = ie.read_model(str(int8_model_xml))
        compiled_int8 = ie.compile_model(int8_model, device_name="CPU")
        
        # Warmup
        input_shape = compiled_int8.input(0).shape
        dummy_input = {compiled_int8.input(0).any_name: np.random.rand(*input_shape).astype(np.float32)}
        compiled_int8(dummy_input)
        
        # Benchmark
        times = []
        for _ in range(num_inferences):
            start = time.time()
            compiled_int8(dummy_input)
            times.append(time.time() - start)
        
        int8_latency = np.mean(times[10:]) * 1000  # Skip warmup, convert to ms
        int8_throughput = 1000.0 / int8_latency
        int8_size = sum(f.stat().st_size for f in int8_dir.rglob('*') if f.is_file()) / (1024*1024)  # MB
        
        results['int8'] = {
            'latency_ms': round(int8_latency, 2),
            'throughput_fps': round(int8_throughput, 2),
            'model_size_mb': round(int8_size, 2)
        }
        logger.info(f"INT8: {int8_latency:.2f}ms latency, {int8_throughput:.2f} fps")
    except Exception as e:
        logger.error(f"Failed to benchmark INT8: {e}")
        results['int8'] = {'error': str(e)}
    
    # Print comparison
    logger.info("\n" + "="*60)
    logger.info("BENCHMARK COMPARISON")
    logger.info("="*60)
    if 'fp32' in results and 'int8' in results:
        if 'error' not in results['fp32'] and 'error' not in results['int8']:
            speedup = results['fp32']['latency_ms'] / results['int8']['latency_ms']
            size_reduction = (1 - results['int8']['model_size_mb'] / results['fp32']['model_size_mb']) * 100
            logger.info(f"Speedup: {speedup:.2f}x")
            logger.info(f"Size reduction: {size_reduction:.1f}%")
    
    logger.info(f"Results: {results}")
    
    # Save results
    import json
    results_file = Path(cfg['int8_output_dir']).parent / 'benchmark_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {results_file}")
