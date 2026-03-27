import React, { useMemo } from 'react';
import type { StreamData, Alert } from '../types';
import { evaluateCompliance } from '../utils/compliance';

interface BottomBarProps {
  streams: StreamData[];
  alerts: Alert[];
}

export const BottomBar: React.FC<BottomBarProps> = ({ streams, alerts }) => {
  const stats = useMemo(() => {
    let total = 0, compliant = 0;
    streams.forEach(s => {
      const p = evaluateCompliance(s.detections);
      total += p.length;
      compliant += p.filter(x => x.status === 'compliant').length;
    });
    return { total, compliant, violations: total - compliant };
  }, [streams]);

  return (
    <div className="flex w-full h-full">
      {/* LEFT: Summary */}
      <div className="w-1/3 border-r border-gray-800 p-6 flex flex-col justify-center">
        <h3 className="text-gray-500 text-xs font-bold tracking-widest uppercase mb-4">Coverage Summary</h3>
        <div className="flex items-center gap-8">
          <div className="flex flex-col">
            <span className="text-4xl font-mono text-gray-200">{stats.total}</span>
            <span className="text-[10px] text-gray-500 uppercase tracking-widest mt-1">Total</span>
          </div>
          <div className="flex flex-col">
            <span className="text-4xl font-mono text-emerald-500">{stats.compliant}</span>
            <span className="text-[10px] text-gray-500 uppercase tracking-widest mt-1">Compliant</span>
          </div>
          <div className="flex flex-col">
            <span className={`text-4xl font-mono ${stats.violations > 0 ? 'text-red-500' : 'text-gray-400'}`}>
              {stats.violations}
            </span>
            <span className="text-[10px] text-gray-500 uppercase tracking-widest mt-1">Violations</span>
          </div>
        </div>
      </div>

      {/* RIGHT: Alerts & Metrics */}
      <div className="w-2/3 p-6 flex flex-col justify-between">
        <div className="flex-1 overflow-hidden flex flex-col">
          <h3 className="text-gray-500 text-xs font-bold tracking-widest uppercase mb-3">Recent Alerts (Max 5)</h3>
          <div className="space-y-1.5 overflow-hidden">
            {alerts.slice(0, 5).map(alert => (
               <div key={alert.id} className="text-sm font-mono text-gray-300 flex items-center gap-3">
                 <span className="text-gray-500 w-24">[{alert.streamId}]</span>
                 <span className={`w-32 ${alert.type === 'missing_both' ? 'text-red-500' : 'text-orange-400'}`}>
                   {alert.type.replace('_', ' ').toUpperCase()}
                 </span>
                 <span className="text-gray-600 ml-auto">
                   {new Date(alert.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                 </span>
               </div>
            ))}
            {alerts.length === 0 && <div className="text-sm text-gray-600 font-mono italic">System clear. No violations.</div>}
          </div>
        </div>

      </div>
    </div>
  );
};
