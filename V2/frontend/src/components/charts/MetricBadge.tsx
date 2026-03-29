export function MetricBadge({
  label,
  value,
  hint
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-glow">
      <p className="text-xs uppercase tracking-[0.24em] text-mist">{label}</p>
      <p className="mt-2 font-display text-3xl text-white">{value}</p>
      {hint ? <p className="mt-1 text-sm text-mist">{hint}</p> : null}
    </div>
  );
}

