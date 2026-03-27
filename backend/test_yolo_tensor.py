import numpy as np
import torch
from ultralytics import YOLO

def test():
    model = YOLO("yolo11n.pt", task="detect")
    
    # Test numpy (1, 3, 640, 640)
    try:
        dummy_np = np.zeros((1, 3, 640, 640), dtype=np.float32)
        model.predict(source=dummy_np, device="cpu", verbose=False)
        print("NumPy array succeeded!")
    except Exception as e:
        print(f"NumPy array failed: {e}")

    # Test torch tensor (1, 3, 640, 640)
    try:
        dummy_tf = torch.zeros((1, 3, 640, 640), dtype=torch.float32)
        model.predict(source=dummy_tf, device="cpu", verbose=False)
        print("Torch tensor succeeded!")
    except Exception as e:
        print(f"Torch tensor failed: {e}")

    # What if we pass an image to predict instead of preprocessed tensor when using pytorch backend?
    # Wait, the application has pipelines that provide `tensor` of shape (1, 3, H, W).
    
if __name__ == "__main__":
    test()
