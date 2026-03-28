import sys
sys.path.append('d:/arakkunnam-99/backend')
from app.config import settings
from app.inference_engine import create_engine

try:
    engine = create_engine('openvino')
    print("Engine loaded in test!")
except Exception as e:
    print("Error:", e)
