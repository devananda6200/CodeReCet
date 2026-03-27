# arakkunnam-99
Real-Time YOLO11Ops Challenge — Arakkunnam 99 | Code Recet powered by Armada

## Problem Statement
In industrial environments such as construction sites, warehouses, and manufacturing floors, worker safety depends heavily on proper use of Personal Protective Equipment (PPE) like helmets and safety vests. Manual monitoring is difficult, inconsistent, and not scalable across multiple camera feeds.

Although modern object detection models such as YOLO11 Large offer strong accuracy for safety-critical applications, they are often too slow to run in real time on standard industrial PCs that rely only on CPUs. This creates a challenge: how can we maintain high detection accuracy while achieving real-time performance without expensive GPU hardware?

## Proposed Solution
We propose a **Real-Time PPE Compliance Monitoring System** optimized for **CPU-only edge deployment**.

The system focuses on detecting(based on Industrial hazards):
- Person
- Helmet
- Safety Vest

Using these detections, the system determines whether a worker is:
- PPE compliant
- Missing helmet
- Missing safety vest
- Missing both

To make the solution practical for industrial environments, we combine:
- a YOLO11-based PPE detection model
- optimized inference using ONNX/OpenVINO
- an asynchronous decode and inference pipeline
- frame skipping with lightweight tracking
- adaptive resolution control
- support for multiple simultaneous video streams
- a live dashboard with overlays, alerts, and performance metrics

---

## Architecture

```
┌─────────────┐
│  Video      │  webcam / file / RTSP   (up to 4 streams)
│  Sources    │
└─────┬───────┘
      │
┌─────▼───────┐   Bounded queue (5 frames), drop-oldest on overflow
│  Decoder    │   Threaded per-stream via OpenCV VideoCapture
└─────┬───────┘
      │
┌─────▼───────┐   Letterbox resize, BGR→RGB, float32 normalize
│ Preprocessor│   Reusable numpy buffers
└─────┬───────┘
      │
      ├─── Inference frame? ──► YES ──┐
      │                                │
      │                         ┌──────▼──────┐
      │                         │  Inference   │  PyTorch / ONNX / OpenVINO
      │                         │  Engine      │  (pluggable via config)
      │                         └──────┬───────┘
      │                                │
      │                         ┌──────▼──────┐
      │                         │ Postprocessor│  NMS + coord rescaling
      │                         └──────┬───────┘
      │                                │
      └─── NO (skipped frame) ─► ┌─────▼──────┐
                                 │  Tracker    │  IoU + Hungarian matching
                                 │  (predict)  │  Anti-flicker (≥3 hits)
                                 └─────┬───────┘
                                       │
                                ┌──────▼───────┐
                                │  Compliance  │  Head/torso region matching
                                │  Checker     │  → compliant / missing PPE
                                └──────┬───────┘
                                       │
                                ┌──────▼───────┐
                                │  Alert       │  Cooldown dedup per track
                                │  Manager     │  < 300ms latency target
                                └──────┬───────┘
                                       │
                            ┌──────────▼──────────┐
                            │  FastAPI Server      │
                            │  REST + WebSocket    │
                            └──────────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.10+
- A YOLO11 model file (`.pt`, `.onnx`, or OpenVINO IR) trained on PPE classes

### Installation

```bash
# Clone and enter the project
cd arakkunnam-99

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Edit `config.yaml` to set your model path and preferred backend:

```yaml
model:
  path: "models/yolo11l.pt"     # Your model file
  backend: "pytorch"             # pytorch | onnx | openvino
  confidence_threshold: 0.45
```

You can also override via environment variables:
```bash
set PPE_MODEL_PATH=models/best.onnx
set PPE_INFERENCE_BACKEND=onnx
```

### Running the Server

```bash
# Option 1: Direct python
python -m app.main

# Option 2: uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The server starts, loads the model, and waits for streams to be added.

---

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/streams` | List active streams |
| `POST` | `/api/streams` | Add a stream |
| `DELETE` | `/api/streams/{id}` | Remove a stream |
| `GET` | `/api/metrics` | Performance metrics |
| `GET` | `/api/alerts` | Recent alerts |

### Add a Stream

```bash
curl -X POST http://localhost:8000/api/streams \
  -H "Content-Type: application/json" \
  -d '{"stream_id": "cam1", "source": "0"}'          # webcam

curl -X POST http://localhost:8000/api/streams \
  -H "Content-Type: application/json" \
  -d '{"stream_id": "vid1", "source": "test_video.mp4"}'  # file

curl -X POST http://localhost:8000/api/streams \
  -H "Content-Type: application/json" \
  -d '{"stream_id": "rtsp1", "source": "rtsp://192.168.1.10:554/stream"}'
```

### WebSocket — Live Detections

Connect to `ws://localhost:8000/ws/detections` to receive per-frame JSON:

```json
{
  "stream_id": "cam1",
  "frame_number": 42,
  "timestamp": 1711567890.123,
  "is_inference_frame": true,
  "detections": [
    {"class": "person", "confidence": 0.92, "track_id": 1,
     "bbox": {"x1": 100, "y1": 50, "x2": 300, "y2": 400}}
  ],
  "compliance": [
    {"track_id": 1, "status": "helmet_missing",
     "has_helmet": false, "has_vest": true}
  ],
  "alerts": [
    {"alert_id": "a1b2c3", "track_id": 1, "violation": "helmet_missing"}
  ],
  "stage_timings_ms": {
    "preprocess": 2.1, "inference": 85.3,
    "postprocess": 1.2, "tracking": 0.5,
    "compliance": 0.1, "alerts": 0.05
  }
}
```

---

## Project Structure

```
app/
├── __init__.py
├── main.py               # FastAPI entrypoint + lifespan
├── config.py              # Pydantic config from config.yaml
├── models.py              # Shared data models
├── decoder.py             # Threaded frame capture
├── preprocessor.py        # Letterbox + normalize
├── inference_engine.py    # PyTorch / ONNX / OpenVINO backends
├── postprocessor.py       # NMS + detection parsing
├── tracker.py             # IoU tracker with anti-flicker
├── compliance_checker.py  # Spatial PPE compliance
├── alert_manager.py       # Alert generation + cooldown
├── metrics.py             # Performance metrics collector
├── stream_manager.py      # Multi-stream orchestrator
└── api/
    ├── __init__.py
    └── routes.py          # REST + WebSocket endpoints
config.yaml                # Runtime configuration
requirements.txt           # Python dependencies
```

## Optimization Features

| Feature | Details |
|---------|---------|
| **Frame skipping** | Full inference every N-th frame (default: 3); tracker predicts on skipped frames |
| **Adaptive resolution** | Auto-downgrades 1080p → 720p → 480p when FPS drops below threshold |
| **Bounded queues** | Max 5 frames buffered per stream; oldest dropped on overflow |
| **Inference backends** | Switch between PyTorch → ONNX → OpenVINO via config for CPU optimization |
| **Anti-flicker** | Detections must persist ≥ 3 frames before being emitted |
| **Thread affinity** | ONNX/OpenVINO thread count configurable for CPU core budget |

## Performance Targets

| Metric | Target |
|--------|--------|
| Effective detection rate | ≥ 10 FPS |
| Max CPU cores | 8 |
| Concurrent streams | 4 |
| RAM usage | < 4 GB |
| Alert latency | < 300 ms |
