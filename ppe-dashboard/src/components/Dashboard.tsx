import React, { useState, useEffect, useRef } from 'react';
import { StreamGrid } from './StreamGrid';
import { BottomBar } from './BottomBar';
import type { Alert, StreamData } from '../types';

export const Dashboard: React.FC = () => {
  const [streams, setStreams] = useState<StreamData[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [time, setTime] = useState(new Date());
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const wsRef = useRef<WebSocket | null>(null);

  // Poll REST API for streams on mount + every 5s to auto-discover
  useEffect(() => {
    const fetchStreams = async () => {
      try {
        const res = await fetch('/api/streams');
        if (!res.ok) return;
        const data: { id: string; name: string; status: string }[] = await res.json();
        setStreams(prev => {
          // Merge: add any new streams from REST that aren't in state yet
          const existingIds = new Set(prev.map(s => s.id));
          const newOnes: StreamData[] = data
            .filter(s => !existingIds.has(s.id))
            .map(s => ({
              id: s.id,
              name: s.name,
              status: s.status as StreamData['status'],
            }));
          if (newOnes.length === 0) return prev;
          return [...prev, ...newOnes];
        });
      } catch (_) {/* backend not ready yet */}
    };

    fetchStreams();
    const pollInterval = setInterval(fetchStreams, 5000);
    return () => clearInterval(pollInterval);
  }, []);

  // WebSocket for live detections + alerts
  useEffect(() => {
    const clockInterval = setInterval(() => setTime(new Date()), 1000);

    const connectWS = () => {
      setWsStatus('connecting');
      const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/detections`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => setWsStatus('connected');

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as { type: string; data: unknown };

          if (msg.type === 'detections') {
            // Backend sends: { type: "detections", data: StreamData[] }
            const incoming = msg.data as Array<{
              id: string; name: string; status: string;
              detections: unknown[]; metrics: unknown;
            }>;
            setStreams(prev => {
              const map = new Map(prev.map(s => [s.id, s]));
              for (const s of incoming) {
                map.set(s.id, {
                  id: s.id,
                  name: s.name,
                  status: s.status as StreamData['status'],
                  backendMessage: s as any,
                });
              }
              return Array.from(map.values());
            });
          }

          if (msg.type === 'alert') {
            const a = msg.data as any;
            const newAlert: Alert = {
              id: a.id,
              streamId: a.streamId,
              timestamp: a.timestamp,
              type: a.type,
              severity: a.severity ?? 'medium',
              resolved: a.resolved ?? false,
            };
            setAlerts(prev => {
              const merged = [newAlert, ...prev];
              const unique = merged.filter(
                (v, i, self) => i === self.findIndex(t => t.id === v.id)
              );
              return unique.slice(0, 20);
            });
          }
        } catch (e) {
          console.error('Malformed WS message', e);
        }
      };

      ws.onclose = () => {
        setWsStatus('disconnected');
        console.warn('WebSocket closed, retrying in 3s…');
        setTimeout(connectWS, 3000);
      };
    };

    connectWS();

    return () => {
      clearInterval(clockInterval);
      wsRef.current?.close();
    };
  }, []);

  const wsColor = { connecting: 'yellow', connected: 'emerald', disconnected: 'red' }[wsStatus];

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0b0f14] text-gray-200">
      {/* Top Bar */}
      <header className="h-[10vh] border-b border-gray-800 flex items-center justify-between px-6 shrink-0 bg-[#070a0d]">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold tracking-widest text-white uppercase">PPE Monitor</h1>
          <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full bg-${wsColor}-500 animate-pulse`}></div>
            <span className={`text-${wsColor}-500 text-xs font-bold tracking-wide uppercase`}>
              {wsStatus}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm font-mono text-gray-400">
          <span className="bg-gray-900 border border-gray-700 px-3 py-1.5 rounded tracking-widest text-white font-bold text-xs uppercase">
            {streams.length} stream{streams.length !== 1 ? 's' : ''}
          </span>
          <span>{time.toLocaleTimeString([], { hour12: false })}</span>
        </div>
      </header>

      {/* Main Area */}
      <main className="h-[70vh] p-4 shrink-0 flex items-center justify-center overflow-hidden">
        {streams.length === 0 ? (
          <div className="flex flex-col items-center gap-3 text-gray-600 font-mono tracking-widest uppercase text-sm">
            <div className="w-6 h-6 border-2 border-gray-600 border-t-gray-400 rounded-full animate-spin" />
            <span>Waiting for streams…</span>
            <span className="text-xs text-gray-700">Polling /api/streams · WS {wsStatus}</span>
          </div>
        ) : (
          <StreamGrid streams={streams} />
        )}
      </main>

      {/* Bottom Panel */}
      <footer className="h-[20vh] border-t border-gray-800 shrink-0 flex bg-[#070a0d]">
        <BottomBar streams={streams} alerts={alerts} />
      </footer>
    </div>
  );
};
