# Ops Safety System

Hackathon-ready monorepo for a CPU-first industrial safety monitoring system built around a trained YOLO11 checkpoint at `backend/models/best.pt`.

## Phase 1 to 3 status

This repository now includes:

- A FastAPI backend with stream, config, alert, zone, health, frame preview, and WebSocket endpoints.
- A CPU-oriented stream pipeline that can read demo feeds, webcam/file/RTSP sources, run YOLO when available, and fall back to deterministic mock detections when the model or runtime is unavailable.
- Safety logic for PPE checks, no-go zone entry, machine proximity, temporal persistence, and lightweight tracking continuity.
- Export and benchmarking scripts for ONNX, OpenVINO, and optional dynamic INT8 ONNX quantization.
- A React + Vite + TypeScript + Tailwind frontend with live stream previews, stream intake controls, alert timeline, richer settings, live metric summaries, and a zone-drawing editor.
- Dockerfiles for backend and frontend plus a `docker-compose.yml` for local full-stack startup.
- Real-camera-first startup (no seeded demo streams by default) with optional demo mode when needed.

## Repository layout

```text
ops-safety-system/
  backend/
    app/
      api/
      core/
      models/
      pipeline/
      safety/
      services/
      tracking/
      utils/
      main.py
    data/
    models/
    scripts/
    tests/
    Dockerfile
    requirements.txt
  frontend/
    public/
    src/
      components/
      hooks/
      pages/
      services/
      types/
      utils/
    Dockerfile
    package.json
  docker-compose.yml
  README.md
```

## Architecture

### Backend flow

1. Source intake: RTSP URL, HTTP/MJPEG URL, webcam index, uploaded video file, or optional demo feed.
2. Decode and frame generation: handled per stream in `StreamManager` and `FramePipeline`.
3. Inference path: lazy model loading via `ModelService`, with deterministic mock fallback when the model or runtime is unavailable.
4. Tracking and smoothing: centroid-style tracking continuity and temporal persistence in the safety engine.
5. Safety rules: PPE checks, no-go zone polygon checks, and machine proximity alerts.
6. Delivery: REST APIs, JPEG preview endpoint, and WebSocket summaries for streams, alerts, and metrics.

### Frontend flow

1. Dashboard provider fetches config, streams, alerts, zones, and summary metrics.
2. WebSocket subscriptions keep stream cards, alerts, and summary metrics live.
3. Operators can add sources, upload videos, tune runtime settings, and draw no-go polygons.
4. Stream cards render the latest annotated JPEG frame from the backend.

## Quick start

### Backend

Model placement:

```text
ops-safety-system/backend/models/best.pt
```

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Linux/macOS shell:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API docs will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Frontend

Windows PowerShell:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Linux/macOS shell:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The dashboard will be available at [http://localhost:5173](http://localhost:5173).

### Docker Compose

```powershell
docker compose up --build
```

The frontend will be available at [http://localhost:8080](http://localhost:8080) and the backend at [http://localhost:8000](http://localhost:8000).

## Environment files

Backend sample values live in `backend/.env.example`.

Key backend knobs:

- `OPS_MODEL_PATH`
- `OPS_DEFAULT_BACKEND`
- `OPS_DEMO_MODE`
- `OPS_DEMO_SEED_STREAMS`
- `OPS_DEFAULT_CPU_THREADS`
- `OPS_DEFAULT_FRAME_SKIP`
- `OPS_ALERT_PERSISTENCE_FRAMES`
- `OPS_ADAPTIVE_RESOLUTION`

Frontend sample values live in `frontend/.env.example`.

Key frontend knobs:

- `VITE_API_BASE_URL`
- `VITE_STREAM_WS_URL`
- `VITE_ALERT_WS_URL`
- `VITE_METRICS_WS_URL`

## Implemented starter endpoints

- `POST /streams/add`
- `POST /streams/upload`
- `POST /streams/{id}/start`
- `POST /streams/{id}/stop`
- `GET /streams`
- `GET /streams/{id}/metrics`
- `GET /streams/{id}/frame`
- `GET /alerts`
- `GET /health`
- `GET /metrics/summary`
- `GET /config`
- `POST /config`
- `POST /zones/{stream_id}`
- `GET /zones/{stream_id}`
- `WS /ws/streams`
- `WS /ws/alerts`
- `WS /ws/metrics`

## Mobile camera feeds on local network

For real phone cameras on the same LAN, use apps that expose RTSP or HTTP/MJPEG streams:

- Android: IP Webcam (HTTP/MJPEG), Larix Broadcaster (RTSP)
- iOS: Larix Broadcaster (RTSP)

Steps:

1. Keep your phone and this machine on the same Wi-Fi/network.
2. Start streaming in the phone app and copy the stream URL.
3. In the dashboard, add a new stream with:
  - `RTSP stream` and a URL like `rtsp://192.168.1.50:8554/live`
  - or `HTTP/MJPEG stream` and a URL like `http://192.168.1.50:8080/video`
4. Click Start on that stream card to begin live inference.

## Demo assumptions

- `backend/models/best.pt` is intentionally ignored from git. Drop your trained checkpoint there before Phase 2.
- The backend tries to load the configured model lazily and run on CPU. If the model is unavailable or the runtime import fails, it falls back to deterministic demo detections so the UI still works.
- Export and benchmark helpers now live in `backend/scripts/export_model.py` and `backend/scripts/benchmark_backends.py`.

## Phase 3 commands

### Export ONNX and INT8 ONNX

```powershell
cd backend
python scripts/export_model.py --model models/best.pt --onnx --quantize-onnx-int8 --output-dir models/exports
```

### Export OpenVINO

```powershell
cd backend
python scripts/export_model.py --model models/best.pt --openvino --output-dir models/exports
```

### Benchmark baseline and exported variants

```powershell
cd backend
python scripts/benchmark_backends.py `
  --baseline models/best.pt `
  --onnx models/exports/best.onnx `
  --quantized-onnx models/exports/best.int8.onnx `
  --openvino models/exports/best_openvino_model `
  --sample data/uploads/demo.mp4 `
  --threads 8
```

## Example API calls

Add a demo stream:

```powershell
curl -X POST http://localhost:8000/streams/add `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Demo Camera X\",\"source_type\":\"demo\"}"
```

Add an RTSP stream:

```powershell
curl -X POST http://localhost:8000/streams/add `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Dock Camera\",\"source_type\":\"rtsp\",\"source_uri\":\"rtsp://user:pass@host/stream\"}"
```

Update runtime config:

```powershell
curl -X POST http://localhost:8000/config `
  -H "Content-Type: application/json" `
  -d "{\"backend\":\"onnxruntime\",\"cpu_threads\":8,\"frame_skip_rate\":3,\"adaptive_resolution\":true}"
```

Save a no-go polygon:

```powershell
curl -X POST http://localhost:8000/zones/demo-stream-id `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Forklift Lane\",\"points\":[{\"x\":140,\"y\":120},{\"x\":540,\"y\":160},{\"x\":620,\"y\":420},{\"x\":120,\"y\":460}]}"
```

Read the latest summary metrics:

```powershell
curl http://localhost:8000/metrics/summary
```

## Demo notes

- If `best.pt` is missing, the app still runs in a deterministic mock-inference mode for demos.
- Demo streams are disabled by default (`OPS_DEMO_MODE=false`, `OPS_DEMO_SEED_STREAMS=0`).
- The zone editor works against the latest JPEG preview emitted by each stream.
- Stream cards show current FPS, latency, frame-skip mode, detection count, and runtime mode.
- The current OpenVINO and ONNX export path depends on the local Ultralytics runtime being installed successfully.

## Verification notes

- Backend syntax was verified with Python 3.13 using `python -m compileall`.
- Backend pytest collection was attempted, but local dependency installation is still required in this workspace. The first missing package was `aiofiles`.
- Frontend dependency installation and build verification were not run in this workspace yet.

## Hackathon pitch angles

- CPU-first deployment: the project is designed for industrial PCs without GPUs.
- Practical optimization path: baseline PyTorch, ONNX export, OpenVINO export, and optional INT8 ONNX quantization.
- Operator-friendly UX: live previews, quick runtime controls, and interactive no-go zone editing.
- Demo resilience: the product still works without cameras or a ready model, which is useful during judging.
- Clear extension story: alert snapshots, benchmark dashboards, and production camera resilience can be added without changing the overall architecture.

## Next phases

1. Extend the live pipeline with camera resilience, bounded buffers, and optional saved alert snapshots/clips.
2. Add deeper benchmark telemetry, profiling overlays, and side-by-side backend comparison views.
3. Finalize docs, deployment notes, and hackathon pitch improvements.
