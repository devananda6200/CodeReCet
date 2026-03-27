export interface BackendDetection {
  class: string;
  confidence: number;
  track_id: number;
  bbox: { x1: number; y1: number; x2: number; y2: number };
}

export interface BackendCompliance {
  track_id: number;
  status: 'compliant' | 'helmet_missing' | 'vest_missing' | 'both_missing';
  has_helmet: boolean;
  has_vest: boolean;
}

export interface BackendAlert {
  alert_id: string;
  track_id: number;
  violation: string;
}

export interface BackendSocketMessage {
  stream_id: string;
  frame_number: number;
  timestamp: number;
  is_inference_frame: boolean;
  detections: BackendDetection[];
  compliance: BackendCompliance[];
  alerts: BackendAlert[];
  stage_timings_ms: Record<string, number>;
}

export interface StreamData {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'error';
  backendMessage?: BackendSocketMessage;
}

export interface Alert {
  id: string;
  streamId: string;
  timestamp: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  resolved: boolean;
}
