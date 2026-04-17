import { useEffect, useMemo, useState } from "react";

import { resolveApiUrl } from "../../services/api";
import { formatMs } from "../../utils/format";
import type { StreamRecord } from "../../types";
import { StatusPill } from "../ui/StatusPill";

export function StreamCard({
  stream,
  onToggle
}: {
  stream: StreamRecord;
  onToggle: (stream: StreamRecord) => void;
}) {
  const running = stream.runtime_status === "running";
  const [previewNonce, setPreviewNonce] = useState(0);

  useEffect(() => {
    if (!running) {
      return;
    }
    const interval = window.setInterval(() => {
      setPreviewNonce((value) => value + 1);
    }, 100);
    return () => {
      window.clearInterval(interval);
    };
  }, [running]);

  const previewUrl = useMemo(() => {
    const baseUrl = resolveApiUrl(stream.preview_url);
    if (!baseUrl) {
      return null;
    }
    if (!running) {
      return baseUrl;
    }
    const separator = baseUrl.includes("?") ? "&" : "?";
    return `${baseUrl}${separator}rt=${previewNonce}`;
  }, [previewNonce, running, stream.preview_url]);

  return (
    <article className="overflow-hidden rounded-3xl border border-white/10 bg-panel shadow-glow">
      <div className="relative h-56 overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(249,115,22,0.22),_transparent_35%),linear-gradient(135deg,_#091018,_#152337_55%,_#1e293b)]">
        {previewUrl ? (
          <img
            src={previewUrl}
            alt={stream.name}
            className="absolute inset-0 h-full w-full object-cover opacity-85"
          />
        ) : null}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-[size:32px_32px] opacity-30" />
        <div className="absolute left-4 top-4 flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${running ? "bg-signal" : "bg-mist"}`} />
          <span className="text-xs uppercase tracking-[0.24em] text-white/80">{stream.source_type}</span>
        </div>
        <div className="absolute bottom-4 left-4 right-4 flex items-end justify-between gap-3">
          <div>
            <h3 className="font-display text-xl text-white">{stream.name}</h3>
            <p className="mt-1 text-sm text-mist">Backend: {stream.model_backend}</p>
          </div>
          <StatusPill status={stream.safety_status} />
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div className="grid grid-cols-2 gap-3 text-sm text-mist md:grid-cols-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em]">FPS</p>
            <p className="mt-1 text-lg font-semibold text-white">{stream.metrics.fps.toFixed(1)}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em]">Latency</p>
            <p className="mt-1 text-lg font-semibold text-white">
              {formatMs(stream.metrics.end_to_end_latency_ms)}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em]">Resolution</p>
            <p className="mt-1 text-lg font-semibold text-white">{stream.metrics.current_resolution}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em]">Skip</p>
            <p className="mt-1 text-lg font-semibold text-white">{stream.metrics.frame_skip_rate}x</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-sm text-mist">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em]">Decode</p>
            <p className="mt-1 text-base font-semibold text-white">{formatMs(stream.metrics.decode_latency_ms)}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em]">Detections</p>
            <p className="mt-1 text-base font-semibold text-white">{stream.metrics.detection_count}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em]">Mode</p>
            <p className="mt-1 text-base font-semibold uppercase text-white">{stream.metrics.mode}</p>
          </div>
        </div>

        <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-mist">Runtime</p>
            <p className={`mt-1 text-sm font-medium ${stream.runtime_status === "error" ? "text-signal" : "text-white"}`}>
              {stream.runtime_status} {stream.active_alerts > 0 ? `| ${stream.active_alerts} active` : ""}
            </p>
            {stream.runtime_status === "error" && stream.error_message && (
              <p className="mt-1 text-[10px] italic leading-tight text-signal/80">
                {stream.error_message}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => onToggle(stream)}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              running
                ? "bg-white/10 text-white hover:bg-white/20"
                : "bg-accent text-slate-950 hover:bg-orange-300"
            }`}
          >
            {running ? "Stop Stream" : "Start Stream"}
          </button>
        </div>
      </div>
    </article>
  );
}
