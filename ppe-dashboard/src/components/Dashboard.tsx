import React, { useState, useEffect } from 'react';
import { StreamGrid } from './StreamGrid';
import { BottomBar } from './BottomBar';
import type { Alert, StreamData, BackendSocketMessage } from '../types';

export const Dashboard: React.FC = () => {
  const [streams, setStreams] = useState<StreamData[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [time, setTime] = useState(new Date());
  
  // Real active streams connection!
  useEffect(() => {
    // Clock tick
    const clockInterval = setInterval(() => setTime(new Date()), 1000);

    // WebSocket connection to FastAPI Backend
    let ws: WebSocket;
    const connectWS = () => {
      ws = new WebSocket('ws://localhost:8000/ws/detections');
      
      ws.onmessage = (event) => {
        try {
          const data: BackendSocketMessage = JSON.parse(event.data);
          
          setStreams(prev => {
            const idx = prev.findIndex(s => s.id === data.stream_id);
            if (idx !== -1) {
              const newStreams = [...prev];
              newStreams[idx] = { ...newStreams[idx], backendMessage: data };
              return newStreams;
            } else {
               // Auto-discover any new YOLO stream dynamically pushed via WS
               return [...prev, {
                 id: data.stream_id,
                 name: data.stream_id.toUpperCase(),
                 status: 'active',
                 backendMessage: data
               }];
            }
          });

          // Intercept alerts dynamically
          if (data.alerts && data.alerts.length > 0) {
            setAlerts(prev => {
               const newAlerts = data.alerts.map(a => ({
                  id: a.alert_id,
                  streamId: data.stream_id,
                  timestamp: new Date(data.timestamp * 1000).toISOString(),
                  type: a.violation,
                  severity: 'medium' as any,
                  resolved: false,
               }));
               // Prepend new alerts and filter out duplicate IDs, keep max 5
               const merged = [...newAlerts, ...prev];
               const unique = merged.filter((val, index, self) => 
                  index === self.findIndex((t) => t.id === val.id)
               );
               return unique.slice(0, 5);
            });
          }
        } catch (e) {
          console.error("Malformed websocket response", e);
        }
      };

      ws.onclose = () => {
        console.warn("WebSocket disconnected, retrying in 3s...");
        setTimeout(connectWS, 3000); // rudimentary reconnect logic
      };
    };

    connectWS();

    return () => {
      clearInterval(clockInterval);
      if (ws) ws.close();
    };
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0b0f14] text-gray-200">
      {/* Top Bar - 10vh */}
      <header className="h-[10vh] border-b border-gray-800 flex items-center justify-between px-6 shrink-0 bg-[#070a0d]">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold tracking-widest text-white uppercase">PPE Monitor</h1>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>
            <span className="text-emerald-500 text-xs font-bold tracking-wide uppercase">Live</span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm font-mono text-gray-400">
          <span className="bg-gray-900 border border-gray-700 px-3 py-1.5 rounded outline-none tracking-widest text-white font-bold text-xs uppercase">
            FULL DEMO
          </span>
          <span>{time.toLocaleTimeString([], { hour12: false })}</span>
        </div>
      </header>

      {/* Main Area - 70vh */}
      <main className="h-[70vh] p-4 shrink-0 flex items-center justify-center overflow-hidden">
        {streams.length === 0 ? (
          <div className="text-gray-600 font-mono tracking-widest uppercase">
            Waiting for backend connection... (ws://localhost:8000/ws/detections)
          </div>
        ) : (
          <StreamGrid streams={streams} />
        )}
      </main>

      {/* Bottom Panel - 20vh */}
      <footer className="h-[20vh] border-t border-gray-800 shrink-0 flex bg-[#070a0d]">
        <BottomBar streams={streams} alerts={alerts} />
      </footer>
    </div>
  );
};
