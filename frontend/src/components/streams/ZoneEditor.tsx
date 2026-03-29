import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";

import { resolveApiUrl } from "../../services/api";
import type { PolygonZone, StreamRecord, ZonePoint } from "../../types";

interface Props {
  streams: StreamRecord[];
  zones: Record<string, PolygonZone | null>;
  onLoadZone: (streamId: string) => Promise<void>;
  onSaveZone: (streamId: string, zone: PolygonZone) => Promise<void>;
}

export function ZoneEditor({ streams, zones, onLoadZone, onSaveZone }: Props) {
  const [selectedStreamId, setSelectedStreamId] = useState<string>(streams[0]?.id ?? "");
  const [draftPoints, setDraftPoints] = useState<ZonePoint[]>([]);
  const [zoneName, setZoneName] = useState("No-Go Zone");
  const [imageSize, setImageSize] = useState({ width: 1, height: 1 });
  const imageRef = useRef<HTMLImageElement | null>(null);

  const selectedStream = useMemo(
    () => streams.find((stream) => stream.id === selectedStreamId) ?? streams[0] ?? null,
    [selectedStreamId, streams]
  );
  const zone = selectedStream ? zones[selectedStream.id] : null;

  useEffect(() => {
    if (!selectedStream && streams[0]) {
      setSelectedStreamId(streams[0].id);
      return;
    }
    if (selectedStream) {
      void onLoadZone(selectedStream.id);
    }
  }, [selectedStream?.id, streams]);

  useEffect(() => {
    if (zone) {
      setDraftPoints(zone.points);
      setZoneName(zone.name);
    } else {
      setDraftPoints([]);
      setZoneName("No-Go Zone");
    }
  }, [zone, selectedStreamId]);

  const previewUrl = resolveApiUrl(selectedStream?.preview_url);

  const handleCanvasClick = (event: MouseEvent<SVGSVGElement>) => {
    if (!imageRef.current || !selectedStream) {
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    const naturalWidth = imageRef.current.naturalWidth || imageSize.width;
    const naturalHeight = imageRef.current.naturalHeight || imageSize.height;
    const x = ((event.clientX - rect.left) / rect.width) * naturalWidth;
    const y = ((event.clientY - rect.top) / rect.height) * naturalHeight;
    setDraftPoints((current) => [...current, { x: Math.round(x), y: Math.round(y) }]);
  };

  const scaledPoints = draftPoints.map((point) => ({
    x: (point.x / imageSize.width) * 100,
    y: (point.y / imageSize.height) * 100
  }));

  return (
    <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
      <div className="rounded-3xl border border-white/10 bg-panelAlt p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-accent">Zone Editor</p>
            <h3 className="mt-2 font-display text-2xl text-white">Draw or update no-go polygons</h3>
          </div>
          <select
            className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none focus:border-accent"
            value={selectedStream?.id ?? ""}
            onChange={(event) => setSelectedStreamId(event.target.value)}
          >
            {streams.map((stream) => (
              <option key={stream.id} value={stream.id}>
                {stream.name}
              </option>
            ))}
          </select>
        </div>

        <div className="relative mt-5 overflow-hidden rounded-3xl border border-white/10 bg-black/20">
          {selectedStream && previewUrl ? (
            <>
              <img
                ref={imageRef}
                src={previewUrl}
                alt={selectedStream.name}
                className="block h-[360px] w-full object-contain"
                onLoad={(event) =>
                  setImageSize({
                    width: event.currentTarget.naturalWidth || 1,
                    height: event.currentTarget.naturalHeight || 1
                  })
                }
              />
              <svg
                className="absolute inset-0 h-full w-full cursor-crosshair"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                onClick={handleCanvasClick}
              >
                {scaledPoints.length >= 2 ? (
                  <polyline
                    points={scaledPoints.map((point) => `${point.x},${point.y}`).join(" ")}
                    fill="rgba(249,115,22,0.18)"
                    stroke="#f97316"
                    strokeWidth={0.8}
                  />
                ) : null}
                {scaledPoints.length >= 3 ? (
                  <polygon
                    points={scaledPoints.map((point) => `${point.x},${point.y}`).join(" ")}
                    fill="rgba(239,68,68,0.18)"
                    stroke="#ef4444"
                    strokeWidth={0.8}
                  />
                ) : null}
                {scaledPoints.map((point, index) => (
                  <circle key={`${point.x}-${point.y}-${index}`} cx={point.x} cy={point.y} r={1.3} fill="#ffffff" />
                ))}
              </svg>
            </>
          ) : (
            <div className="flex h-[360px] items-center justify-center text-sm text-mist">
              Start a stream to draw a zone over its latest preview frame.
            </div>
          )}
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-panel p-5">
        <p className="text-xs uppercase tracking-[0.24em] text-accent">Zone Details</p>
        <h3 className="mt-2 font-display text-2xl text-white">Polygon configuration</h3>

        <label className="mt-5 block space-y-2">
          <span className="text-sm text-white">Zone name</span>
          <input
            className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none focus:border-accent"
            value={zoneName}
            onChange={(event) => setZoneName(event.target.value)}
          />
        </label>

        <div className="mt-5 rounded-2xl border border-white/10 bg-black/10 p-4">
          <p className="text-sm text-white">Points: {draftPoints.length}</p>
          <p className="mt-2 text-sm text-mist">
            Click on the preview to add polygon vertices. Use at least 3 points before saving.
          </p>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setDraftPoints([])}
            className="rounded-full border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            Clear Points
          </button>
          <button
            type="button"
            disabled={!selectedStream || draftPoints.length < 3}
            onClick={() => selectedStream && void onSaveZone(selectedStream.id, { name: zoneName, points: draftPoints })}
            className="rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-orange-300 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Save Zone
          </button>
        </div>

        <pre className="mt-5 overflow-x-auto rounded-2xl border border-white/10 bg-black/20 p-4 text-xs text-mist">
          {JSON.stringify({ name: zoneName, points: draftPoints }, null, 2)}
        </pre>
      </div>
    </section>
  );
}
