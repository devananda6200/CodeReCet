import { AlertTimeline } from "../components/alerts/AlertTimeline";
import { MetricBadge } from "../components/charts/MetricBadge";
import { StreamMetricsPanel } from "../components/charts/StreamMetricsPanel";
import { StreamControlPanel } from "../components/streams/StreamControlPanel";
import { StreamGrid } from "../components/streams/StreamGrid";
import { ZoneEditor } from "../components/streams/ZoneEditor";
import { useDashboardData } from "../hooks/useDashboardData";

export function DashboardPage() {
  const {
    streams,
    alerts,
    config,
    summary,
    zones,
    loading,
    usingFallback,
    toggleStream,
    saveConfig,
    addStream,
    uploadStream,
    loadZone,
    saveZone
  } = useDashboardData();

  const avgFps =
    streams.length > 0 ? (streams.reduce((sum, stream) => sum + stream.metrics.fps, 0) / streams.length).toFixed(1) : "0.0";
  const avgLatency =
    streams.length > 0
      ? Math.round(
          streams.reduce((sum, stream) => sum + stream.metrics.end_to_end_latency_ms, 0) / streams.length
        ).toString()
      : "0";

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-glow">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-accent">Live Operations Overview</p>
            <h2 className="mt-3 max-w-3xl font-display text-4xl leading-tight text-white">
              Safety monitoring dashboard for up to four CPU-optimized camera feeds.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-mist">
              This dashboard now supports live backend previews, stream intake controls, and CPU-focused runtime tuning.
              When `best.pt` is available, the backend can switch from deterministic demo detections to real YOLO output.
            </p>
          </div>
          {usingFallback ? (
            <div className="rounded-2xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning">
              API unreachable. Showing local demo fallback data.
            </div>
          ) : null}
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <MetricBadge
            label="Streams Online"
            value={`${summary.active_streams}`}
            hint={loading ? "Loading..." : `${summary.total_streams} configured`}
          />
          <MetricBadge label="Average FPS" value={avgFps} hint="Target >= 10 FPS" />
          <MetricBadge label="Average Latency" value={`${avgLatency} ms`} hint="Target <= 300 ms alert SLA" />
        </div>
      </section>

      <StreamControlPanel
        config={config}
        onSaveConfig={saveConfig}
        onAddStream={addStream}
        onUploadStream={uploadStream}
      />

      <StreamMetricsPanel streams={streams} summary={summary} />

      <StreamGrid streams={streams} onToggle={toggleStream} />

      <ZoneEditor streams={streams} zones={zones} onLoadZone={loadZone} onSaveZone={saveZone} />

      <AlertTimeline alerts={alerts} />
    </div>
  );
}
