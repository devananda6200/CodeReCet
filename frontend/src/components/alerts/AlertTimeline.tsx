import type { AlertRecord } from "../../types";
import { formatConfidence, formatTime } from "../../utils/format";

export function AlertTimeline({ alerts }: { alerts: AlertRecord[] }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-panelAlt p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-mist">Recent Alerts</p>
          <h2 className="mt-2 font-display text-2xl text-white">Violation timeline</h2>
        </div>
        <span className="rounded-full bg-danger/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-danger">
          {alerts.length} active
        </span>
      </div>

      <div className="mt-5 space-y-3">
        {alerts.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-mist">
            No alerts yet. Start a stream to populate the safety timeline.
          </div>
        ) : null}

        {alerts.map((alert) => (
          <article key={alert.id} className="rounded-2xl border border-white/10 bg-black/10 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-white">{alert.stream_name}</p>
                <p className="mt-1 text-sm text-mist">{alert.details}</p>
              </div>
              <span className="text-xs uppercase tracking-[0.18em] text-mist">{formatTime(alert.created_at)}</span>
            </div>
            <div className="mt-3 flex items-center justify-between text-sm">
              <span className="rounded-full bg-white/10 px-3 py-1 text-white">{alert.status_label}</span>
              <span className="text-mist">Confidence {formatConfidence(alert.confidence)}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

