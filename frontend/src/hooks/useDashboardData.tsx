import {
  createContext,
  useCallback,
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

const getWsUrl = (path: string, envVar: string) => {
  const envUrl = import.meta.env[envVar];
  if (envUrl) return envUrl;

  const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const wsBase = apiBase.replace(/^http/, "ws");
  // Ensure we don't have double slashes if apiBase ends with /
  const normalizedBase = wsBase.endsWith("/") ? wsBase.slice(0, -1) : wsBase;
  return `${normalizedBase}${path}`;
};

const STREAM_WS_URL = getWsUrl("/ws/streams", "VITE_STREAM_WS_URL");
const ALERT_WS_URL = getWsUrl("/ws/alerts", "VITE_ALERT_WS_URL");
const METRICS_WS_URL = getWsUrl("/ws/metrics", "VITE_METRICS_WS_URL");

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

  const refresh = useCallback(async () => {
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
    } catch (error) {
      console.error("Failed to fetch dashboard data, using mock fallback:", error);
      setStreams(mockStreams);
      setAlerts(mockAlerts);
      setConfig(mockConfig);
      setSummary(mockSummary);
      setUsingFallback(true);
    } finally {
      setLoading(false);
    }
  }, []);

  const toggleStream = useCallback(
    async (stream: StreamRecord) => {
      try {
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
      } catch (error) {
        console.error("Failed to toggle stream:", error);
        alert(`Failed to ${stream.runtime_status === "running" ? "stop" : "start"} stream. Check backend logs.`);
      }
    },
    [usingFallback, refresh]
  );

  const saveConfig = useCallback(
    async (payload: Partial<RuntimeConfig>) => {
      try {
        if (usingFallback) {
          setConfig((current) => ({ ...current, ...payload }));
          return;
        }
        const updated = await api.updateConfig(payload);
        setConfig(updated);
      } catch (error) {
        console.error("Failed to save config:", error);
        alert("Failed to save configuration. Check backend logs.");
      }
    },
    [usingFallback]
  );

  const addStream = useCallback(
    async (payload: {
      name: string;
      source_type: "demo" | "rtsp" | "http" | "webcam" | "file";
      source_uri?: string;
    }) => {
      try {
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
      } catch (error) {
        console.error("Failed to add stream:", error);
        alert("Failed to add stream. Check backend logs.");
      }
    },
    [usingFallback, refresh]
  );

  const uploadStream = useCallback(
    async (file: File) => {
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
    },
    [usingFallback, refresh]
  );

  const loadZone = useCallback(
    async (streamId: string) => {
      if (usingFallback) {
        setZones((current) => ({ ...current, [streamId]: current[streamId] ?? null }));
        return;
      }
      const zone = await api.getZone(streamId);
      setZones((current) => ({ ...current, [streamId]: zone }));
    },
    [usingFallback]
  );

  const saveZone = useCallback(
    async (streamId: string, zone: PolygonZone) => {
      setZones((current) => ({ ...current, [streamId]: zone }));
      if (usingFallback) {
        return;
      }
      await api.saveZone(streamId, zone);
    },
    [usingFallback]
  );

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
    [
      alerts,
      config,
      loading,
      streams,
      summary,
      usingFallback,
      zones,
      refresh,
      toggleStream,
      saveConfig,
      addStream,
      uploadStream,
      loadZone,
      saveZone
    ]
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
