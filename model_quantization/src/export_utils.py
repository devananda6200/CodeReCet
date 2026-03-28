import os
from pathlib import Path
from ultralytics import YOLO
import logging

logger = logging.getLogger(__name__)

def export_to_openvino(cfg):
    """
    Export YOLO11 PyTorch model to OpenVINO IR (FP32).
    Uses Ultralytics YOLOv11 built-in export functionality.
    """
    pt_path = Path(cfg['source_pt_model_path'])
    export_dir = Path(cfg['openvino_export_dir'])
    imgsz = cfg.get('imgsz', 640)
    device = cfg.get('device', 'cpu')
    
    if not pt_path.exists():
        raise FileNotFoundError(f"Model file not found: {pt_path}")
    
    export_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Loading YOLO11 model from {pt_path}...")
    model = YOLO(str(pt_path))
    
    logger.info(f"Exporting to OpenVINO IR (FP32) at {export_dir}...")
    export_results = model.export(
        format='openvino',
        imgsz=imgsz,
        device=device,
        half=False,  # FP32
        dynamic=False,
        simplify=False,
        opset=12
    )
    
    logger.info(f"✓ Export successful! OpenVINO model saved to: {export_dir}")
    return export_results
