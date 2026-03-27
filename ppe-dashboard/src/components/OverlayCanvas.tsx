import React, { useEffect, useRef } from 'react';
import type { Detection, PersonRecord } from '../types';

interface OverlayCanvasProps {
  detections: Detection[];
  persons: PersonRecord[];
}

export const OverlayCanvas: React.FC<OverlayCanvasProps> = ({ detections, persons }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Optional: resize to fit container accurately if desired
    const parent = canvas.parentElement;
    if (parent && (canvas.width !== parent.clientWidth || canvas.height !== parent.clientHeight)) {
      canvas.width = parent.clientWidth;
      canvas.height = parent.clientHeight;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const getPersonColor = (status: string) => {
      switch (status) {
        case 'compliant': return '#10b981';
        case 'missing_helmet': return '#ef4444';
        case 'missing_vest': return '#f97316';
        case 'missing_both': return '#7f1d1d';
        default: return '#ffffff';
      }
    };

    persons.forEach(person => {
      const color = getPersonColor(person.status);
      
      // Thin Border
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.strokeRect(person.box.x, person.box.y, person.box.w, person.box.h);

      // Label
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      const labelText = `[PERSON #${person.id} - ${person.status.replace('_', ' ').toUpperCase()}]`;
      
      ctx.font = '10px monospace';
      const textWidth = ctx.measureText(labelText).width;
      
      ctx.fillRect(person.box.x, person.box.y - 14, textWidth + 8, 14);

      ctx.fillStyle = '#ffffff';
      ctx.fillText(labelText, person.box.x + 4, person.box.y - 4);
    });

    // Sub items very faint
    detections.forEach(det => {
      if (det.class === 'person') return;
      
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 0.5;
      ctx.strokeRect(det.box.x, det.box.y, det.box.w, det.box.h);
      
      ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.font = '8px monospace';
      ctx.fillText(det.class, det.box.x, det.box.y - 2);
    });

  }, [detections, persons]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute top-0 left-0 w-full h-full pointer-events-none"
    />
  );
};
