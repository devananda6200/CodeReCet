import React, { useState, useEffect } from 'react';
import { initialStreams, initialAlerts, mockScenarios, mockMetrics } from '../mock/mockData';
import { StreamGrid } from './StreamGrid';
import { BottomBar } from './BottomBar';
import type { Alert, StreamData } from '../types';

export const Dashboard: React.FC = () => {
  const [streams, setStreams] = useState<StreamData[]>(initialStreams);
  const [alerts, setAlerts] = useState<Alert[]>(initialAlerts);
  const [selectedScenario, setSelectedScenario] = useState<keyof typeof mockScenarios>('mixed');

  // Simulator
  useEffect(() => {
    const interval = setInterval(() => {
      setStreams(prev => prev.map(stream => ({
        ...stream,
        metrics: {
          ...stream.metrics,
          fps: mockMetrics.fps + (Math.random() * 4 - 2),
          cpu: Math.max(10, Math.min(100, mockMetrics.cpu + (Math.random() * 10 - 5))),
        },
        detections: stream.detections.map(det => ({
          ...det,
          box: {
            ...det.box,
            x: det.box.x + (Math.random() * 2 - 1),
            y: det.box.y + (Math.random() * 2 - 1),
          }
        }))
      })));

      if (Math.random() > 0.8) {
        const types: Alert['type'][] = ['missing_helmet', 'missing_vest', 'missing_both'];
        const randomType = types[Math.floor(Math.random() * types.length)];
        
        setAlerts(prev => [{
          id: `alert_${Date.now()}`,
          streamId: `stream_${Math.floor(Math.random() * 4) + 1}`,
          timestamp: new Date().toISOString(),
          type: randomType,
          severity: (randomType === 'missing_both' ? 'critical' : 'medium') as Alert['severity'],
          resolved: false
        }, ...prev].slice(0, 5)); // Keep only latest 5 alerts!
      }
    }, 500);

    return () => clearInterval(interval);
  }, []);

  const handleScenarioChange = (scenario: keyof typeof mockScenarios) => {
    setSelectedScenario(scenario);
    setStreams(prev => prev.map(s => ({ ...s, detections: mockScenarios[scenario] })));
  };

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
          <select 
            className="bg-gray-900 border border-gray-700 px-3 py-1.5 rounded outline-none appearance-none cursor-pointer focus:border-gray-500 text-xs uppercase tracking-widest"
            value={selectedScenario}
            onChange={(e) => handleScenarioChange(e.target.value as any)}
          >
            <option value="compliant">All Compliant</option>
            <option value="missingHelmet">Missing Helmet</option>
            <option value="missingVest">Missing Vest</option>
            <option value="missingBoth">Missing Both</option>
            <option value="mixed">Mixed Demo</option>
          </select>
          <span>{new Date().toLocaleTimeString([], { hour12: false })}</span>
        </div>
      </header>

      {/* Main Area - 70vh */}
      <main className="h-[70vh] p-4 shrink-0 flex items-center justify-center overflow-hidden">
        <StreamGrid streams={streams} />
      </main>

      {/* Bottom Panel - 20vh */}
      <footer className="h-[20vh] border-t border-gray-800 shrink-0 flex bg-[#070a0d]">
        <BottomBar streams={streams} alerts={alerts} />
      </footer>
    </div>
  );
};
