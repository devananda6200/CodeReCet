import type { AlertListResponse, PolygonZone, RuntimeConfig, StreamListResponse, SummaryMetrics } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json"
    },
    ...init
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  listStreams: () => request<StreamListResponse>("/streams"),
  listAlerts: () => request<AlertListResponse>("/alerts"),
  getConfig: () => request<RuntimeConfig>("/config"),
  getSummaryMetrics: () => request<SummaryMetrics>("/metrics/summary"),
  getZone: (streamId: string) => request<PolygonZone | null>(`/zones/${streamId}`),
  saveZone: (streamId: string, payload: PolygonZone) =>
    request<{ message: string }>(`/zones/${streamId}`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  addStream: (payload: { name: string; source_type: "demo" | "rtsp" | "http" | "webcam" | "file"; source_uri?: string }) =>
    request("/streams/add", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  uploadStream: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/streams/upload`, {
      method: "POST",
      body: formData
    });
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`);
    }
    return response.json();
  },
  updateConfig: (payload: Partial<RuntimeConfig>) =>
    request<RuntimeConfig>("/config", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  startStream: (streamId: string) =>
    request<{ message: string }>(`/streams/${streamId}/start`, {
      method: "POST"
    }),
  stopStream: (streamId: string) =>
    request<{ message: string }>(`/streams/${streamId}/stop`, {
      method: "POST"
    })
};

export function resolveApiUrl(path?: string | null): string | null {
  if (!path) {
    return null;
  }
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}
