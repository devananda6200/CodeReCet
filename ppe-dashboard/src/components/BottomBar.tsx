import React, { useMemo } from 'react';
import type { StreamData, Alert } from '../types';

interface BottomBarProps {
  streams: StreamData[];
  alerts: Alert[];
}

export const BottomBar: React.FC<BottomBarProps> = ({ streams, alerts }) => {
  const stats = useMemo(() => {
    let total = 0, compliant = 0;
    streams.forEach(s => {
      if (s.backendMessage) {
        total += s.backendMessage.compliance.length;
        compliant += s.backendMessage.compliance.filter(c => c.status === 'compliant').length;
      }
    });
    return { total, compliant, violations: total - compliant };
  }, [streams]);

  return (
    <div className="flex w-full h-full">
      {/* LEFT: Summary */}
      <div className="w-1/3 border-r border-gray-800 px-4 flex flex-col justify-center">
        <h3 className="text-gray-500 text-xs font-bold tracking-widest uppercase mb-2">Coverage Summary</h3>
        <div className="flex items-center gap-6">
          <div className="flex flex-col">
            <span className="text-4xl font-mono text-gray-200 leading-none">{stats.total}</span>
            <span className="text-[9px] text-gray-500 uppercase tracking-widest mt-1">Total</span>
          </div>
          <div className="flex flex-col">
            <span className="text-4xl font-mono text-emerald-500 leading-none">{stats.compliant}</span>
            <span className="text-[9px] text-gray-500 uppercase tracking-widest mt-1">Compliant</span>
          </div>
          <div className="flex flex-col">
            <span className={`text-4xl font-mono leading-none ${stats.violations > 0 ? 'text-red-500' : 'text-gray-400'}`}>
              {stats.violations}
            </span>
            <span className="text-[9px] text-gray-500 uppercase tracking-widest mt-1">Violations</span>
          </div>
        </div>
      </div>

      {/* RIGHT: Alerts & Metrics */}
      <div className="w-2/3 px-4 py-2 flex flex-col justify-center">
        <div className="flex-1 flex flex-col justify-center">
          <h3 className="text-gray-500 text-xs font-bold tracking-widest uppercase mb-2">Recent Alerts (Max 5)</h3>
          <div className="space-y-1">
            {alerts.slice(0, 5).map(alert => (
               <div key={alert.id} className="text-[11px] font-mono text-gray-300 flex items-center gap-3">
                 <span className="text-gray-500 w-20">[{alert.streamId}]</span>
                 <span className={`w-32 ${alert.type === 'missing_both' ? 'text-red-500' : 'text-orange-400'}`}>
                   {alert.type.replace('_', ' ').toUpperCase()}
                 </span>
                 <span className="text-gray-600 ml-auto">
                   {new Date(alert.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                 </span>
               </div>
            ))}
            {alerts.length === 0 && <div className="text-[11px] text-gray-600 font-mono italic">System clear. No violations.</div>}
          </div>
        </div>
      </div>
    </div>
  );
};
