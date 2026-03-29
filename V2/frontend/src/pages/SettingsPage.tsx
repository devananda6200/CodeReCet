import { useEffect, useState, type FormEvent } from "react";

import { useDashboardData } from "../hooks/useDashboardData";
import type { RuntimeConfig } from "../types";

export function SettingsPage() {
  const { config, saveConfig, usingFallback } = useDashboardData();
  const [draft, setDraft] = useState<RuntimeConfig>(config);
  const [classMappingsText, setClassMappingsText] = useState(JSON.stringify(config.class_mappings, null, 2));

  useEffect(() => {
    setDraft(config);
    setClassMappingsText(JSON.stringify(config.class_mappings, null, 2));
  }, [config]);

  const updateField = <K extends keyof RuntimeConfig>(key: K, value: RuntimeConfig[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const parsedMappings = JSON.parse(classMappingsText) as RuntimeConfig["class_mappings"];
      await saveConfig({ ...draft, class_mappings: parsedMappings });
    } catch {
      return;
    }
  };

  return (
    <section className="rounded-[2rem] border border-white/10 bg-panelAlt p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-accent">Runtime Controls</p>
          <h2 className="mt-3 font-display text-3xl text-white">Inference and system configuration</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-mist">
            These controls now feed the backend runtime config for model path, CPU threads, frame skipping, and safety
            rule mappings.
          </p>
        </div>
        {usingFallback ? (
          <span className="rounded-full border border-warning/30 bg-warning/10 px-3 py-2 text-xs uppercase tracking-[0.18em] text-warning">
            Fallback mode
          </span>
        ) : null}
      </div>

      <form className="mt-8 grid gap-5 md:grid-cols-2" onSubmit={handleSubmit}>
        <label className="space-y-2">
          <span className="text-sm font-medium text-white">Model path</span>
          <input
            className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none transition focus:border-accent"
            value={draft.model_path}
            onChange={(event) => updateField("model_path", event.target.value)}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-white">Backend</span>
          <select
            className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none focus:border-accent"
            value={draft.backend}
            onChange={(event) => updateField("backend", event.target.value as RuntimeConfig["backend"])}
          >
            <option value="pytorch">PyTorch baseline</option>
            <option value="onnxruntime">ONNX Runtime CPU</option>
            <option value="openvino">OpenVINO optimized</option>
          </select>
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-white">CPU threads</span>
          <input
            type="number"
            min={1}
            max={8}
            className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none transition focus:border-accent"
            value={draft.cpu_threads}
            onChange={(event) => updateField("cpu_threads", Number(event.target.value))}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-white">Input size</span>
          <input
            type="number"
            min={320}
            max={1280}
            step={32}
            className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none transition focus:border-accent"
            value={draft.input_size}
            onChange={(event) => updateField("input_size", Number(event.target.value))}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-white">Frame skip rate</span>
          <input
            type="number"
            min={1}
            max={8}
            className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none transition focus:border-accent"
            value={draft.frame_skip_rate}
            onChange={(event) => updateField("frame_skip_rate", Number(event.target.value))}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-white">Confidence threshold</span>
          <input
            type="number"
            min={0}
            max={1}
            step="0.01"
            className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none transition focus:border-accent"
            value={draft.confidence_threshold}
            onChange={(event) => updateField("confidence_threshold", Number(event.target.value))}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-white">IoU threshold</span>
          <input
            type="number"
            min={0}
            max={1}
            step="0.01"
            className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none transition focus:border-accent"
            value={draft.iou_threshold}
            onChange={(event) => updateField("iou_threshold", Number(event.target.value))}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-white">Machine proximity distance (px)</span>
          <input
            type="number"
            min={40}
            max={600}
            className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-white outline-none transition focus:border-accent"
            value={draft.machine_proximity_px}
            onChange={(event) => updateField("machine_proximity_px", Number(event.target.value))}
          />
        </label>

        <label className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
          <span className="text-sm font-medium text-white">Adaptive resolution</span>
          <input
            type="checkbox"
            checked={draft.adaptive_resolution}
            onChange={(event) => updateField("adaptive_resolution", event.target.checked)}
          />
        </label>

        <label className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
          <span className="text-sm font-medium text-white">Smart frame skip</span>
          <input
            type="checkbox"
            checked={draft.smart_frame_skip}
            onChange={(event) => updateField("smart_frame_skip", event.target.checked)}
          />
        </label>

        <label className="space-y-2 md:col-span-2">
          <span className="text-sm font-medium text-white">Class mappings JSON</span>
          <textarea
            rows={8}
            className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 font-mono text-sm text-white outline-none transition focus:border-accent"
            value={classMappingsText}
            onChange={(event) => setClassMappingsText(event.target.value)}
          />
        </label>

        <div className="md:col-span-2">
          <button
            type="submit"
            className="rounded-full bg-accent px-6 py-3 font-semibold text-slate-950 transition hover:bg-orange-300"
          >
            Save Settings
          </button>
        </div>
      </form>
    </section>
  );
}
