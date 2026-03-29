import { useMemo, useState } from "react";

import type { RuntimeConfig } from "../../types";

interface Props {
  config: RuntimeConfig;
  onSaveConfig: (payload: Partial<RuntimeConfig>) => Promise<void>;
  onAddStream: (payload: { name: string; source_type: "demo" | "rtsp" | "http" | "webcam" | "file"; source_uri?: string }) => Promise<void>;
  onUploadStream: (file: File) => Promise<void>;
}

export function StreamControlPanel({ config, onSaveConfig, onAddStream, onUploadStream }: Props) {
  const [name, setName] = useState("New Camera");
  const [sourceType, setSourceType] = useState<"demo" | "rtsp" | "http" | "webcam" | "file">("rtsp");
  const [sourceUri, setSourceUri] = useState("");
  const sourceHint = useMemo(() => {
    if (sourceType === "rtsp") return "rtsp://user:pass@camera/stream";
    if (sourceType === "http") return "http://phone-ip:8080/video";
    if (sourceType === "webcam") return "0";
    return "Optional source URI";
  }, [sourceType]);

  const submitAddStream = async () => {
    let normalizedSourceUri = sourceUri;
    if (sourceType === "http" && sourceUri) {
      try {
        const parsed = new URL(sourceUri);
        const pathWithoutTrailingSlash = parsed.pathname.replace(/\/$/, "");
        if (!pathWithoutTrailingSlash) {
          normalizedSourceUri = `${sourceUri.replace(/\/$/, "")}/video`;
        }
      } catch {
        normalizedSourceUri = sourceUri;
      }
    }

    await onAddStream({
      name,
      source_type: sourceType,
      source_uri: normalizedSourceUri || undefined
    });
    setName("New Camera");
    setSourceUri("");
  };

  return (
    <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
      <div className="rounded-3xl border border-white/10 bg-panelAlt p-5">
        <p className="text-xs uppercase tracking-[0.24em] text-accent">Stream Intake</p>
        <h3 className="mt-2 font-display text-2xl text-white">Add RTSP or HTTP mobile camera feeds</h3>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <input
            className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none focus:border-accent"
            placeholder="Camera name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <select
            className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none focus:border-accent"
            value={sourceType}
            onChange={(event) => setSourceType(event.target.value as "demo" | "rtsp" | "http" | "webcam" | "file")}
          >
            <option value="rtsp">RTSP stream</option>
            <option value="http">HTTP/MJPEG stream</option>
            <option value="webcam">Webcam index</option>
            <option value="file">File path</option>
            <option value="demo">Demo feed</option>
          </select>
          <input
            className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none focus:border-accent"
            placeholder={sourceHint}
            value={sourceUri}
            onChange={(event) => setSourceUri(event.target.value)}
          />
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void submitAddStream()}
            className="rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-orange-300"
          >
            Add Stream
          </button>
          <label className="cursor-pointer rounded-full border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10">
            Upload Video
            <input
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  void onUploadStream(file);
                }
              }}
            />
          </label>
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-panel p-5">
        <p className="text-xs uppercase tracking-[0.24em] text-accent">Runtime Tuning</p>
        <h3 className="mt-2 font-display text-2xl text-white">Fast controls for CPU pressure</h3>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
            <span className="text-sm text-white">Adaptive resolution</span>
            <input
              type="checkbox"
              checked={config.adaptive_resolution}
              onChange={(event) => void onSaveConfig({ adaptive_resolution: event.target.checked })}
            />
          </label>
          <label className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
            <span className="text-sm text-white">Smart frame skip</span>
            <input
              type="checkbox"
              checked={config.smart_frame_skip}
              onChange={(event) => void onSaveConfig({ smart_frame_skip: event.target.checked })}
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-white">Frame skip rate</span>
            <input
              type="range"
              min={1}
              max={8}
              value={config.frame_skip_rate}
              className="w-full"
              onChange={(event) => void onSaveConfig({ frame_skip_rate: Number(event.target.value) })}
            />
            <p className="text-sm text-mist">{config.frame_skip_rate}x</p>
          </label>
          <label className="space-y-2">
            <span className="text-sm text-white">Input size</span>
            <input
              type="range"
              min={320}
              max={1280}
              step={32}
              value={config.input_size}
              className="w-full"
              onChange={(event) => void onSaveConfig({ input_size: Number(event.target.value) })}
            />
            <p className="text-sm text-mist">{config.input_size}px</p>
          </label>
        </div>
      </div>
    </section>
  );
}

