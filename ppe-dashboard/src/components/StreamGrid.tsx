import React from 'react';
import type { StreamData } from '../types';
import { StreamCard } from './StreamCard';

export const StreamGrid: React.FC<{ streams: StreamData[] }> = ({ streams }) => {
  const count = streams.length;
  
  let gridClass = "w-full h-full grid gap-4";
  if (count === 1) gridClass += " grid-cols-1 grid-rows-1";
  else if (count === 2) gridClass += " grid-cols-2 grid-rows-1";
  else gridClass += " grid-cols-2 grid-rows-2";

  return (
    <div className={gridClass}>
      {streams.slice(0, 4).map(stream => (
        <StreamCard key={stream.id} stream={stream} />
      ))}
    </div>
  );
};
