import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import type { StreamRecord, SummaryMetrics } from "../../types";

export function StreamMetricsPanel({
  streams,
  summary
}: {
  streams: StreamRecord[];
  summary: SummaryMetrics;
}) {
  const chartData = streams.slice(0, 4).map((stream) => ({
    name: stream.name.replace("Demo Camera ", "Cam "),
    fps: stream.metrics.fps,
    latency: stream.metrics.end_to_end_latency_ms
  }));

  return (
    <section className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
      <div className="rounded-3xl border border-white/10 bg-panelAlt p-5">
        <p className="text-xs uppercase tracking-[0.24em] text-accent">System Metrics</p>
        <h3 className="mt-2 font-display text-2xl text-white">Live CPU-side summary</h3>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <MetricRow label="Running streams" value={`${summary.active_streams}/${summary.total_streams}`} />
          <MetricRow label="Hazard streams" value={`${summary.active_hazard_streams}`} />
          <MetricRow label="Average FPS" value={summary.avg_fps.toFixed(1)} />
          <MetricRow label="Average latency" value={`${Math.round(summary.avg_latency_ms)} ms`} />
          <MetricRow label="Average CPU" value={`${Math.round(summary.avg_cpu_percent)}%`} />
          <MetricRow label="Process memory" value={`${Math.round(summary.process_memory_mb)} MB`} />
        </div>
        <p className="mt-4 text-sm text-mist">
          Backends in use: {summary.backends_in_use.length > 0 ? summary.backends_in_use.join(", ") : "none"}
        </p>
      </div>

      <div className="rounded-3xl border border-white/10 bg-panel p-5">
        <p className="text-xs uppercase tracking-[0.24em] text-accent">Per-Stream Comparison</p>
        <h3 className="mt-2 font-display text-2xl text-white">FPS vs. end-to-end latency</h3>
        <div className="mt-5 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid stroke="rgba(148,163,184,0.18)" vertical={false} />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis yAxisId="fps" stroke="#22c55e" />
              <YAxis yAxisId="latency" orientation="right" stroke="#f97316" />
              <Tooltip
                contentStyle={{
                  background: "#101b2b",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "16px"
                }}
              />
              <Bar yAxisId="fps" dataKey="fps" fill="#22c55e" radius={[6, 6, 0, 0]} />
              <Bar yAxisId="latency" dataKey="latency" fill="#f97316" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
      <p className="text-xs uppercase tracking-[0.18em] text-mist">{label}</p>
      <p className="mt-2 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}

