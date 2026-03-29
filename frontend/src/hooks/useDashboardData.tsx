import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";

import { api } from "../services/api";
import { mockAlerts, mockConfig, mockStreams, mockSummary } from "../services/mockData";
import { createSocket } from "../services/ws";
import type { AlertRecord, PolygonZone, RuntimeConfig, StreamRecord, SummaryMetrics } from "../types";

const STREAM_WS_URL = import.meta.env.VITE_STREAM_WS_URL ?? "ws://localhost:8000/ws/streams";
const ALERT_WS_URL = import.meta.env.VITE_ALERT_WS_URL ?? "ws://localhost:8000/ws/alerts";
const METRICS_WS_URL = import.meta.env.VITE_METRICS_WS_URL ?? "ws://localhost:8000/ws/metrics";

interface DashboardDataState {
  streams: StreamRecord[];
  alerts: AlertRecord[];
  config: RuntimeConfig;
  summary: SummaryMetrics;
  zones: Record<string, PolygonZone | null>;
  loading: boolean;
  usingFallback: boolean;
  refresh: () => Promise<void>;
  toggleStream: (stream: StreamRecord) => Promise<void>;
  saveConfig: (payload: Partial<RuntimeConfig>) => Promise<void>;
  addStream: (payload: { name: string; source_type: "demo" | "rtsp" | "http" | "webcam" | "file"; source_uri?: string }) => Promise<void>;
  uploadStream: (file: File) => Promise<void>;
  loadZone: (streamId: string) => Promise<void>;
  saveZone: (streamId: string, zone: PolygonZone) => Promise<void>;
}

const DashboardContext = createContext<DashboardDataState | undefined>(undefined);

export function DashboardDataProvider({ children }: { children: ReactNode }) {
  const [streams, setStreams] = useState<StreamRecord[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [config, setConfig] = useState<RuntimeConfig>(mockConfig);
  const [summary, setSummary] = useState<SummaryMetrics>(mockSummary);
  const [zones, setZones] = useState<Record<string, PolygonZone | null>>({});
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  const refresh = async () => {
    try {
      const [streamData, alertData, configData, summaryData] = await Promise.all([
        api.listStreams(),
        api.listAlerts(),
        api.getConfig(),
        api.getSummaryMetrics()
      ]);
      setStreams(streamData.items);
      setAlerts(alertData.items);
      setConfig(configData);
      setSummary(summaryData);
      setUsingFallback(false);
    } catch {
      setStreams(mockStreams);
      setAlerts(mockAlerts);
      setConfig(mockConfig);
      setSummary(mockSummary);
      setUsingFallback(true);
    } finally {
      setLoading(false);
    }
  };

  const toggleStream = async (stream: StreamRecord) => {
    if (usingFallback) {
      setStreams((current) =>
        current.map((item) =>
          item.id === stream.id
            ? {
                ...item,
                runtime_status: item.runtime_status === "running" ? "stopped" : "running"
              }
            : item
        )
      );
      return;
    }

    if (stream.runtime_status === "running") {
      await api.stopStream(stream.id);
    } else {
      await api.startStream(stream.id);
    }
    await refresh();
  };

  const saveConfig = async (payload: Partial<RuntimeConfig>) => {
    if (usingFallback) {
      setConfig((current) => ({ ...current, ...payload }));
      return;
    }
    const updated = await api.updateConfig(payload);
    setConfig(updated);
  };

  const addStream = async (payload: {
    name: string;
    source_type: "demo" | "rtsp" | "http" | "webcam" | "file";
    source_uri?: string;
  }) => {
    if (usingFallback) {
      setStreams((current) => [
        ...current,
        {
          ...mockStreams[0],
          id: crypto.randomUUID(),
          name: payload.name,
          source_type: payload.source_type,
          source_uri: payload.source_uri ?? null,
          runtime_status: "stopped"
        }
      ]);
      return;
    }
    await api.addStream(payload);
    await refresh();
  };

  const uploadStream = async (file: File) => {
    if (usingFallback) {
      setStreams((current) => [
        ...current,
        {
          ...mockStreams[0],
          id: crypto.randomUUID(),
          name: file.name,
          source_type: "file",
          source_uri: file.name,
          runtime_status: "stopped"
        }
      ]);
      return;
    }
    await api.uploadStream(file);
    await refresh();
  };

  const loadZone = async (streamId: string) => {
    if (usingFallback) {
      setZones((current) => ({ ...current, [streamId]: current[streamId] ?? null }));
      return;
    }
    const zone = await api.getZone(streamId);
    setZones((current) => ({ ...current, [streamId]: zone }));
  };

  const saveZone = async (streamId: string, zone: PolygonZone) => {
    setZones((current) => ({ ...current, [streamId]: zone }));
    if (usingFallback) {
      return;
    }
    await api.saveZone(streamId, zone);
  };

  useEffect(() => {
    void refresh();

    const streamSocket = createSocket(STREAM_WS_URL, (payload) => {
      const typed = payload as { streams?: StreamRecord[]; summary?: SummaryMetrics };
      if (typed.streams) {
        setStreams(typed.streams);
      }
      if (typed.summary) {
        setSummary(typed.summary);
      }
    });

    const alertSocket = createSocket(ALERT_WS_URL, (payload) => {
      const typed = payload as { alerts?: AlertRecord[] };
      if (typed.alerts) {
        setAlerts(typed.alerts);
      }
    });

    const metricsSocket = createSocket(METRICS_WS_URL, (payload) => {
      const typed = payload as { summary?: SummaryMetrics };
      if (typed.summary) {
        setSummary(typed.summary);
      }
    });

    const interval = window.setInterval(() => {
      void refresh();
    }, 5000);

    return () => {
      window.clearInterval(interval);
      streamSocket?.close();
      alertSocket?.close();
      metricsSocket?.close();
    };
  }, []);

  const value = useMemo<DashboardDataState>(
    () => ({
      streams,
      alerts,
      config,
      summary,
      zones,
      loading,
      usingFallback,
      refresh,
      toggleStream,
      saveConfig,
      addStream,
      uploadStream,
      loadZone,
      saveZone
    }),
    [alerts, config, loading, streams, summary, usingFallback, zones]
  );

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboardData(): DashboardDataState {
  const value = useContext(DashboardContext);
  if (!value) {
    throw new Error("useDashboardData must be used within DashboardDataProvider");
  }
  return value;
}
