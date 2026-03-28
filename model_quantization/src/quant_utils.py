import os
from pathlib import Path
import numpy as np
import logging
import openvino as ov
from nncf import quantize
import cv2

logger = logging.getLogger(__name__)


class CalibrationDataset:
    """Simple dataset wrapper for NNCF calibration."""
    
    def __init__(self, data_list):
        self.data_list = data_list
    
    def __iter__(self):
        for data in self.data_list:
            yield {0: data}  # NNCF expects dict with input index
    
    def __len__(self):
        return len(self.data_list)
    
    def get_batch_size(self):
        return 1
    
    def get_length(self):
        return len(self.data_list)

def create_calibration_dataset(calib_dir, sample_size, imgsz=640):
    """
    Create calibration dataset from images.
    Returns a list of calibration samples.
    Falls back to synthetic data if calibration_images_dir is empty.
    """
    calib_path = Path(calib_dir)
    calibration_samples = []
    
    # Try to load real images
    image_files = []
    if calib_path.exists():
        image_exts = {'.jpg', '.jpeg', '.png', '.bmp'}
        image_files = [f for f in calib_path.rglob('*') if f.suffix.lower() in image_exts]
    
    if image_files:
        logger.info(f"Found {len(image_files)} calibration images")
        # Use real images
        for img_path in image_files[:sample_size]:
            try:
                img = cv2.imread(str(img_path))
                if img is not None:
                    img = cv2.resize(img, (imgsz, imgsz))
                    img = np.transpose(img, (2, 0, 1))  # HWC -> CHW
                    img = np.expand_dims(img, 0)  # Add batch dimension
                    calibration_samples.append(img.astype(np.float32) / 255.0)
            except Exception as e:
                logger.warning(f"Failed to load {img_path}: {e}")
    else:
        logger.warning(f"No calibration images found in {calib_dir}, using synthetic data")
        # Use synthetic data for calibration
        for _ in range(sample_size):
            synthetic_img = np.random.rand(1, 3, imgsz, imgsz).astype(np.float32)
            calibration_samples.append(synthetic_img)
    
    return calibration_samples

def quantize_model_int8(cfg):
    """
    Quantize OpenVINO FP32 model to INT8 using NNCF.
    """
    fp32_dir = Path(cfg['openvino_export_dir'])
    int8_dir = Path(cfg['int8_output_dir'])
    calib_dir = Path(cfg['calibration_images_dir'])
    sample_size = cfg.get('calibration_sample_size', 200)
    imgsz = cfg.get('imgsz', 640)
    
    int8_dir.mkdir(parents=True, exist_ok=True)
    
    # Find OpenVINO model files
    model_xml = fp32_dir / 'best_openvino_model' / 'best.xml'
    if not model_xml.exists():
        # Try alternative paths
        xml_files = list(fp32_dir.rglob('*.xml'))
        if xml_files:
            model_xml = xml_files[0]
        else:
            raise FileNotFoundError(f"No OpenVINO .xml model found in {fp32_dir}")
    
    logger.info(f"Loading FP32 OpenVINO model from {model_xml}...")
    ie = ov.Core()
    model = ie.read_model(str(model_xml))
    
    logger.info(f"Creating calibration dataset with {sample_size} samples...")
    calibration_data = create_calibration_dataset(calib_dir, sample_size, imgsz)
    
    quantized_model = model  # Default to FP32
    
    if calibration_data and len(calibration_data) > 0:
        logger.info("Quantizing model to INT8...")
        try:
            # Create dataset wrapper
            dataset = CalibrationDataset(calibration_data)
            # Quantize with NNCF  
            quantized_model = quantize(model, dataset)
            logger.info("✓ Quantization successful!")
        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            logger.warning("Using FP32 model instead")
            quantized_model = model
    else:
        logger.warning("No calibration data, using FP32 model")
    
    output_model_path = int8_dir / 'best.xml'
    logger.info(f"Saving model to {output_model_path}...")
    ov.serialize(quantized_model, str(output_model_path), str(int8_dir / 'best.bin'))
    
    logger.info(f"✓ Model saved to: {int8_dir}")
    return quantized_model
