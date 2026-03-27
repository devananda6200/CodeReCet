export type DetectionClass = 'person' | 'helmet' | 'safety_vest';

export interface BoundingBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Detection {
  id: string;
  class: DetectionClass;
  confidence: number;
  box: BoundingBox;
}

export type PersonStatus =
  | 'compliant'
  | 'missing_helmet'
  | 'missing_vest'
  | 'missing_both';

export interface PersonRecord {
  id: string;
  box: BoundingBox;
  status: PersonStatus;
  helmetDetected: boolean;
  vestDetected: boolean;
}

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface Alert {
  id: string;
  streamId: string;
  timestamp: string;
  type: PersonStatus;
  severity: AlertSeverity;
  personId?: string;
  resolved: boolean;
}

export interface SystemMetrics {
  fps: number;
  latency: number;
  cpu: number;
  ram: number;
  healthy: boolean;
}

export interface StreamData {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'error';
  detections: Detection[];
  metrics: SystemMetrics;
}
