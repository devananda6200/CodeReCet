import type { Alert, Detection, StreamData, SystemMetrics } from '../types';

export const mockMetrics: SystemMetrics = {
  fps: 29.8,
  latency: 45,
  cpu: 42,
  ram: 2.1,
  healthy: true,
};

// Scenario: 1 Compliant person
const scenarioCompliant: Detection[] = [
  { id: '1', class: 'person', confidence: 0.95, box: { x: 100, y: 100, w: 200, h: 500 } },
  { id: '2', class: 'helmet', confidence: 0.92, box: { x: 140, y: 105, w: 120, h: 100 } },
  { id: '3', class: 'safety_vest', confidence: 0.88, box: { x: 120, y: 220, w: 160, h: 180 } },
];

// Scenario: 1 Non-compliant missing helmet
const scenarioMissingHelmet: Detection[] = [
  { id: '4', class: 'person', confidence: 0.96, box: { x: 400, y: 120, w: 180, h: 480 } },
  { id: '5', class: 'safety_vest', confidence: 0.91, box: { x: 410, y: 230, w: 160, h: 180 } },
];

// Scenario: 1 Non-compliant missing vest
const scenarioMissingVest: Detection[] = [
  { id: '6', class: 'person', confidence: 0.94, box: { x: 150, y: 150, w: 210, h: 520 } },
  { id: '7', class: 'helmet', confidence: 0.93, box: { x: 190, y: 155, w: 130, h: 110 } },
];

// Scenario: Missing Both
const scenarioMissingBoth: Detection[] = [
  { id: '8', class: 'person', confidence: 0.97, box: { x: 300, y: 100, w: 200, h: 550 } },
];

export const mockScenarios = {
  compliant: scenarioCompliant,
  missingHelmet: scenarioMissingHelmet,
  missingVest: scenarioMissingVest,
  missingBoth: scenarioMissingBoth,
  mixed: [...scenarioCompliant, ...scenarioMissingHelmet, ...scenarioMissingVest],
};

export const initialStreams: StreamData[] = [
  { id: 'stream_1', name: 'Assembly Line A', status: 'active', detections: mockScenarios.mixed, metrics: mockMetrics },
  { id: 'stream_2', name: 'Loading Dock', status: 'active', detections: mockScenarios.compliant, metrics: mockMetrics },
  { id: 'stream_3', name: 'Warehouse Entrance', status: 'active', detections: mockScenarios.missingBoth, metrics: mockMetrics },
  { id: 'stream_4', name: 'Packing Zone', status: 'active', detections: mockScenarios.missingHelmet, metrics: mockMetrics },
];

export const initialAlerts: Alert[] = [
  {
    id: 'alert_1',
    streamId: 'stream_1',
    timestamp: new Date().toISOString(),
    type: 'missing_helmet',
    severity: 'medium',
    personId: '4',
    resolved: false,
  },
  {
    id: 'alert_2',
    streamId: 'stream_3',
    timestamp: new Date(Date.now() - 50000).toISOString(),
    type: 'missing_both',
    severity: 'critical',
    personId: '8',
    resolved: false,
  }
];
