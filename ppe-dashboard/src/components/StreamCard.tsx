import React, { useRef, useState } from 'react';
import { OverlayCanvas } from './OverlayCanvas';
import type { StreamData } from '../types';

export const StreamCard: React.FC<{ stream: StreamData }> = ({ stream }) => {
  const [feedError, setFeedError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  return (
    <div className="relative border border-gray-800 bg-black overflow-hidden w-full h-full">
      {/* Stream label */}
      <div className="absolute top-2 left-2 z-20 px-2 py-1 bg-black/80 text-[10px] font-mono text-gray-300 tracking-widest uppercase">
        {stream.name} [{stream.id}]
      </div>

      {/* Status dot */}
      <div className={`absolute top-2 right-2 z-20 w-2 h-2 rounded-full ${stream.status === 'active' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />

      {/* Live MJPEG Feed — always show, no onLoad needed for MJPEG */}
      {!feedError ? (
        <img
          ref={imgRef}
          src={`/api/streams/${stream.id}/feed`}
          alt={`Stream ${stream.id}`}
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', zIndex: 1 }}
          onError={() => setFeedError(true)}
        />
      ) : (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 text-gray-600 font-mono text-xs uppercase tracking-widest">
          <div className="text-2xl">📷</div>
          <span>Feed unavailable</span>
          <button
            className="mt-1 text-gray-500 underline text-[10px]"
            onClick={() => setFeedError(false)}
          >
            Retry
          </button>
        </div>
      )}

      {/* Detection overlay canvas — sits above the video */}
      <div className="absolute inset-0 z-10 pointer-events-none">
        <OverlayCanvas stream={stream} />
      </div>
    </div>
  );
};
