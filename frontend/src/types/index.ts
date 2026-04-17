export type BackendChoice = "pytorch" | "onnxruntime" | "openvino" | "mock";

export type StreamRuntimeStatus = "stopped" | "starting" | "running" | "error";

export type StreamSafetyStatus =
  | "SAFE"
  | "PPE MISSING"
  | "NO-GO ZONE BREACH"
  | "MACHINE PROXIMITY ALERT";

export interface StreamMetrics {
  fps: number;
  inference_latency_ms: number;
  decode_latency_ms: number;
  end_to_end_latency_ms: number;
  alert_latency_ms: number;
  cpu_percent: number;
  memory_mb: number;
  current_resolution: string;
  frame_skip_rate: number;
  adaptive_resolution_enabled: boolean;
  tracking_mode: string;
  processed_frames: number;
  detection_count: number;
  mode: string;
  updated_at: string;
}

export interface StreamRecord {
  id: string;
  name: string;
  source_type: "demo" | "rtsp" | "http" | "webcam" | "file";
  source_uri?: string | null;
  runtime_status: StreamRuntimeStatus;
  safety_status: StreamSafetyStatus;
  preview_url?: string | null;
  model_backend: BackendChoice;
  active_alerts: number;
  last_seen_at: string;
  metrics: StreamMetrics;
}

export interface StreamListResponse {
  items: StreamRecord[];
}

export interface AlertRecord {
  id: string;
  stream_id: string;
  stream_name: string;
  type: "ppe_violation" | "zone_breach" | "machine_proximity";
  severity: "low" | "medium" | "high";
  confidence: number;
  status_label: StreamSafetyStatus;
  snapshot_path?: string | null;
  created_at: string;
  details: string;
}

export interface AlertListResponse {
  items: AlertRecord[];
}

export interface RuntimeConfig {
  model_path: string;
  backend: BackendChoice;
  cpu_threads: number;
  confidence_threshold: number;
  iou_threshold: number;
  alert_persistence_frames: number;
  input_size: number;
  machine_proximity_px: number;
  adaptive_resolution: boolean;
  smart_frame_skip: boolean;
  frame_skip_rate: number;
  class_mappings: Record<string, string[]>;
  label_remap: Record<string, string>;
}

export interface SummaryMetrics {
  active_streams: number;
  total_streams: number;
  alerts_in_memory: number;
  avg_fps: number;
  avg_latency_ms: number;
  avg_cpu_percent: number;
  process_memory_mb: number;
  active_hazard_streams: number;
  backends_in_use: string[];
  generated_at: string;
}

export interface ZonePoint {
  x: number;
  y: number;
}

export interface PolygonZone {
  name: string;
  points: ZonePoint[];
}
