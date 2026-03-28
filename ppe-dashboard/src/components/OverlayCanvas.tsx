import React, { useEffect, useRef } from 'react';
import type { StreamData } from '../types';

interface OverlayCanvasProps {
  stream: StreamData;
}

export const OverlayCanvas: React.FC<OverlayCanvasProps> = ({ stream }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const parent = canvas.parentElement;
    if (parent) {
      canvas.width = parent.clientWidth;
      canvas.height = parent.clientHeight;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // The WS message stored in backendMessage has shape:
    // { id, name, status, detections: [{id, class, confidence, box:{x,y,w,h}}], metrics }
    const msg = stream.backendMessage as any;
    if (!msg?.detections?.length) return;

    const detections: Array<{
      id: string;
      class: string;
      confidence: number;
      box: { x: number; y: number; w: number; h: number };
    }> = msg.detections;

    // Backend sends absolute pixel coords based on original frame size.
    // We scale to canvas display size using a reasonable default (640x480).
    // TODO: backend could send frame_width/frame_height in WS payload for accuracy.
    const frameW = msg.frame_width ?? 640;
    const frameH = msg.frame_height ?? 480;
    const scaleX = canvas.width / frameW;
    const scaleY = canvas.height / frameH;

    detections.forEach(det => {
      const { x, y, w, h } = det.box;
      const cx = x * scaleX;
      const cy = y * scaleY;
      const cw = w * scaleX;
      const ch = h * scaleY;

      const isPerson = det.class === 'person';
      const color = isPerson ? '#10b981' : 'rgba(255,255,255,0.5)';

      ctx.strokeStyle = color;
      ctx.lineWidth = isPerson ? 1.5 : 0.8;
      ctx.strokeRect(cx, cy, cw, ch);

      if (isPerson) {
        const label = `${det.class} ${Math.round(det.confidence * 100)}%`;
        ctx.font = '10px monospace';
        const tw = ctx.measureText(label).width;
        ctx.fillStyle = 'rgba(0,0,0,0.7)';
        ctx.fillRect(cx, cy - 16, tw + 8, 16);
        ctx.fillStyle = '#fff';
        ctx.fillText(label, cx + 4, cy - 4);
      }
    });
  }, [stream.backendMessage]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute top-0 left-0 w-full h-full pointer-events-none"
    />
  );
};
