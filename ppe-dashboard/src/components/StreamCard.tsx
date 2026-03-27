import React, { useMemo } from 'react';
import { OverlayCanvas } from './OverlayCanvas';
import { evaluateCompliance } from '../utils/compliance';
import type { StreamData } from '../types';

export const StreamCard: React.FC<{ stream: StreamData }> = ({ stream }) => {
  const persons = useMemo(() => evaluateCompliance(stream.detections), [stream.detections]);

  return (
    <div className="relative border border-gray-800 bg-black flex items-center justify-center overflow-hidden w-full h-full">
      {/* Stream label */}
      <div className="absolute top-2 left-2 z-10 px-2 py-1 bg-black/80 text-[10px] font-mono text-gray-300 tracking-widest uppercase">
        {stream.name} [{stream.id}]
      </div>
      
      {/* Status dot */}
      <div className={`absolute top-2 right-2 z-10 w-2 h-2 rounded-full ${stream.status === 'active' ? 'bg-green-500' : 'bg-red-500'}`}></div>

      {/* Video / Overlay Container */}
      <div className="relative w-full h-full flex items-center justify-center">
         <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-gray-900 to-black opacity-50"></div>
         
         <OverlayCanvas detections={stream.detections} persons={persons} />
      </div>
    </div>
  );
};
