# arakkunnam-99
Real-Time YOLO11Ops Challenge — Arakkunnam 99 | Code Recet powered by Armada

## Problem Statement
In industrial environments such as construction sites, warehouses, and manufacturing floors, worker safety depends heavily on proper use of Personal Protective Equipment (PPE) like helmets and safety vests. Manual monitoring is difficult, inconsistent, and not scalable across multiple camera feeds..

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

## V2 Implementation Snapshot

The V2 codebase is a full-stack monorepo under `V2/` with:

- FastAPI backend for streams, alerts, zones, runtime config, metrics, and health
- CPU-first streaming pipeline with YOLO inference and deterministic fallback mode
- Rule engine for PPE compliance, no-go zone violations, and proximity checks
- React + Vite + TypeScript dashboard for live operations and controls
- Dockerized backend + frontend with a compose workflow

## Repository Layout (Current)

```text
arakkunnam-99/
  README.md
  V2/
    docker-compose.yml
    backend/
      .env.example
      app/
        api/routes/
        core/
        models/
        pipeline/
        safety/
        services/
        tracking/
        utils/
        main.py
      scripts/
      tests/
      Dockerfile
      requirements.txt
    frontend/
      .env.example
      src/
        components/
        hooks/
        pages/
        services/
        types/
        utils/
      Dockerfile
      package.json
```

## Runtime Architecture (V2)

1. Stream intake: webcam/file/RTSP/HTTP-MJPEG/demo sources
2. Frame pipeline: decode and process frames per stream
3. Inference: model loaded via service layer (CPU-first)
4. Safety engine: PPE, zone, and proximity rules
5. Stores and APIs: alerts/config/zones persisted and served over REST/WebSocket
6. Frontend dashboard: live stream cards, controls, timeline alerts, metrics

## Quick Start (V2)

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+
- Optional: Docker Desktop

### Backend (Windows PowerShell)

```powershell
cd V2/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Windows PowerShell)

```powershell
cd V2/frontend
npm install
copy .env.example .env
npm run dev
```

Frontend: `http://localhost:5173`
Backend docs: `http://localhost:8000/docs`

### Docker Compose (from `V2/`)

```powershell
cd V2
docker compose up --build
```

Frontend: `http://localhost:8080`  
Backend: `http://localhost:8000`

## Environment Variables (V2)

Backend env file: `V2/backend/.env.example` (prefix `OPS_`)

Common backend keys:

- `OPS_MODEL_PATH`
- `OPS_DEFAULT_BACKEND`
- `OPS_DEFAULT_CPU_THREADS`
- `OPS_DEFAULT_FRAME_SKIP`
- `OPS_ALERT_PERSISTENCE_FRAMES`
- `OPS_ADAPTIVE_RESOLUTION`
- `OPS_DEMO_MODE`
- `OPS_DEMO_SEED_STREAMS`

Frontend env file: `V2/frontend/.env.example`

Common frontend keys:

- `VITE_API_BASE_URL`
- `VITE_STREAM_WS_URL`
- `VITE_ALERT_WS_URL`
- `VITE_METRICS_WS_URL`

## API Reference (V2)

### REST Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/` | Basic API status message |
| `GET` | `/health` | Health and system snapshot |
| `GET` | `/config` | Read runtime config |
| `POST` | `/config` | Update runtime config |
| `GET` | `/metrics/summary` | Aggregate pipeline metrics |
| `POST` | `/streams/add` | Add a stream by source type |
| `POST` | `/streams/upload` | Upload a video and create stream |
| `POST` | `/streams/{stream_id}/start` | Start stream processing |
| `POST` | `/streams/{stream_id}/stop` | Stop stream processing |
| `GET` | `/streams` | List streams |
| `GET` | `/streams/{stream_id}/metrics` | Stream-level metrics |
| `GET` | `/streams/{stream_id}/frame` | Latest JPEG frame |
| `GET` | `/alerts` | Recent alerts |
| `POST` | `/zones/{stream_id}` | Save a polygon zone |
| `GET` | `/zones/{stream_id}` | Get polygon zone |

### WebSocket Endpoints

- `WS /ws/streams`
- `WS /ws/alerts`
- `WS /ws/metrics`

## Useful Commands (V2)

### Add demo stream

```powershell
curl -X POST http://localhost:8000/streams/add `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Demo Camera\",\"source_type\":\"demo\"}"
```

### Add RTSP stream

```powershell
curl -X POST http://localhost:8000/streams/add `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Dock Camera\",\"source_type\":\"rtsp\",\"source_uri\":\"rtsp://user:pass@host/stream\"}"
```

### Update runtime config

```powershell
curl -X POST http://localhost:8000/config `
  -H "Content-Type: application/json" `
  -d "{\"backend\":\"onnxruntime\",\"cpu_threads\":8,\"frame_skip_rate\":3,\"adaptive_resolution\":true}"
```

### Save no-go polygon

```powershell
curl -X POST http://localhost:8000/zones/demo-stream-id `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Forklift Lane\",\"points\":[{\"x\":140,\"y\":120},{\"x\":540,\"y\":160},{\"x\":620,\"y\":420},{\"x\":120,\"y\":460}]}"
```

## Model and Demo Notes

- Place the trained checkpoint at `V2/backend/models/best.pt` (or set `OPS_MODEL_PATH`)
- If model/runtime is unavailable, backend can continue in deterministic fallback mode for UI demos
- Demo streams are controlled by `OPS_DEMO_MODE` and `OPS_DEMO_SEED_STREAMS`

## Phase 3 Scripts (V2)

### Export ONNX and optional INT8 ONNX

```powershell
cd V2/backend
python scripts/export_model.py --model models/best.pt --onnx --quantize-onnx-int8 --output-dir models/exports
```

### Export OpenVINO

```powershell
cd V2/backend
python scripts/export_model.py --model models/best.pt --openvino --output-dir models/exports
```

### Benchmark variants

```powershell
cd V2/backend
python scripts/benchmark_backends.py `
  --baseline models/best.pt `
  --onnx models/exports/best.onnx `
  --quantized-onnx models/exports/best.int8.onnx `
  --openvino models/exports/best_openvino_model `
  --sample data/uploads/demo.mp4 `
  --threads 8
```

## Current Performance Targets

| Metric | Target |
|--------|--------|
| Effective detection rate | >= 10 FPS |
| Max CPU cores | 8 |
| Concurrent streams | 4 |
| RAM usage | < 4 GB |
| Alert latency | < 300 ms |
