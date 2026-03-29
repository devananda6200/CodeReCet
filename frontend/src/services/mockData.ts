import type { AlertRecord, RuntimeConfig, StreamRecord, SummaryMetrics } from "../types";

export const mockStreams: StreamRecord[] = [
  {
    id: "demo-1",
    name: "Fallback Camera 1",
    source_type: "demo",
    source_uri: "demo://fallback-1",
    runtime_status: "running",
    safety_status: "SAFE",
    model_backend: "pytorch",
    last_seen_at: new Date().toISOString(),
    metrics: {
      fps: 11.7,
      inference_latency_ms: 64,
      decode_latency_ms: 12,
      end_to_end_latency_ms: 87,
      alert_latency_ms: 210,
      cpu_percent: 35,
      memory_mb: 620,
      current_resolution: "1280x720",
      frame_skip_rate: 2,
      adaptive_resolution_enabled: true,
      tracking_mode: "centroid-lite",
      processed_frames: 320,
      detection_count: 3,
      mode: "mock",
      updated_at: new Date().toISOString()
    },
    active_alerts: 0
  },
  {
    id: "demo-2",
    name: "Fallback Camera 2",
    source_type: "demo",
    source_uri: "demo://fallback-2",
    runtime_status: "running",
    safety_status: "PPE MISSING",
    model_backend: "onnxruntime",
    last_seen_at: new Date().toISOString(),
    metrics: {
      fps: 10.8,
      inference_latency_ms: 72,
      decode_latency_ms: 14,
      end_to_end_latency_ms: 98,
      alert_latency_ms: 260,
      cpu_percent: 49,
      memory_mb: 710,
      current_resolution: "1024x576",
      frame_skip_rate: 3,
      adaptive_resolution_enabled: true,
      tracking_mode: "centroid-lite",
      processed_frames: 280,
      detection_count: 2,
      mode: "mock",
      updated_at: new Date().toISOString()
    },
    active_alerts: 1
  }
];

export const mockAlerts: AlertRecord[] = [
  {
    id: "alert-1",
    stream_id: "demo-2",
    stream_name: "Fallback Camera 2",
    type: "ppe_violation",
    severity: "medium",
    confidence: 0.88,
    status_label: "PPE MISSING",
    created_at: new Date().toISOString(),
    details: "Fallback alert shown because the API is unreachable."
  }
];

export const mockConfig: RuntimeConfig = {
  model_path: "models/best.pt",
  backend: "pytorch",
  cpu_threads: 4,
  confidence_threshold: 0.35,
  iou_threshold: 0.45,
  alert_persistence_frames: 3,
  input_size: 960,
  machine_proximity_px: 140,
  adaptive_resolution: true,
  smart_frame_skip: true,
  frame_skip_rate: 2,
  class_mappings: {
    person: ["persons", "person", "worker"],
    helmet: ["helmets", "helmet", "hardhat", "hard_hat"],
    vest: ["vests", "vest", "safety_vest", "jacket"],
    machine: []
  }
};

export const mockSummary: SummaryMetrics = {
  active_streams: 2,
  total_streams: 2,
  alerts_in_memory: 1,
  avg_fps: 11.25,
  avg_latency_ms: 92.5,
  avg_cpu_percent: 42,
  process_memory_mb: 710,
  active_hazard_streams: 1,
  backends_in_use: ["pytorch", "onnxruntime"],
  generated_at: new Date().toISOString()
};
