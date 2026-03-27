import React, { useEffect, useRef } from 'react';
import type { BackendSocketMessage } from '../types';

interface OverlayCanvasProps {
  message?: BackendSocketMessage;
}

export const OverlayCanvas: React.FC<OverlayCanvasProps> = ({ message }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const parent = canvas.parentElement;
    if (parent && (canvas.width !== parent.clientWidth || canvas.height !== parent.clientHeight)) {
      canvas.width = parent.clientWidth;
      canvas.height = parent.clientHeight;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!message) return;

    const { detections, compliance } = message;

    const getPersonColor = (status: string) => {
      switch (status) {
        case 'compliant': return '#10b981';
        case 'helmet_missing': return '#ef4444';
        case 'vest_missing': return '#f97316';
        case 'both_missing': return '#7f1d1d';
        default: return '#ffffff';
      }
    };

    // Calculate dynamic scaling from a standard 640x480 YOLO stream output format to our responsive CSS canvas size.
    // If backend dynamically sets resolution, this could be refactored, assuming 640x480 for classic YOLO aspect.
    const scaleX = canvas.width / 640;
    const scaleY = canvas.height / 480;

    // 1. Draw Persons
    detections.filter(d => d.class === 'person').forEach(det => {
      const comp = compliance.find(c => c.track_id === det.track_id);
      const status = comp ? comp.status : 'unknown';
      const color = getPersonColor(status);

      const x = det.bbox.x1 * scaleX;
      const y = det.bbox.y1 * scaleY;
      const w = (det.bbox.x2 - det.bbox.x1) * scaleX;
      const h = (det.bbox.y2 - det.bbox.y1) * scaleY;

      // Draw box
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y, w, h);

      // Label background
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      const labelText = `[ID:${det.track_id} - ${status.toUpperCase()}]`;
      
      ctx.font = '10px monospace';
      const textWidth = ctx.measureText(labelText).width;
      
      ctx.fillRect(x, y - 14, textWidth + 8, 14);

      // Label text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(labelText, x + 4, y - 4);
    });

    // 2. Draw PPE items faintly
    detections.filter(d => d.class !== 'person').forEach(det => {
      const x = det.bbox.x1 * scaleX;
      const y = det.bbox.y1 * scaleY;
      const w = (det.bbox.x2 - det.bbox.x1) * scaleX;
      const h = (det.bbox.y2 - det.bbox.y1) * scaleY;

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 0.5;
      ctx.strokeRect(x, y, w, h);
      
      ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.font = '8px monospace';
      ctx.fillText(det.class, x, y - 2);
    });

  }, [message]);

  return <canvas ref={canvasRef} className="absolute top-0 left-0 w-full h-full pointer-events-none" />;
};
