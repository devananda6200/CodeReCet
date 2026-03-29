import clsx from "clsx";

import type { StreamSafetyStatus } from "../../types";

const styles: Record<StreamSafetyStatus, string> = {
  SAFE: "bg-signal/15 text-signal border-signal/30",
  "PPE MISSING": "bg-warning/15 text-warning border-warning/30",
  "NO-GO ZONE BREACH": "bg-danger/15 text-danger border-danger/30",
  "MACHINE PROXIMITY ALERT": "bg-danger/20 text-red-200 border-danger/40"
};

export function StatusPill({ status }: { status: StreamSafetyStatus }) {
  return (
    <span
      className={clsx(
        "rounded-full border px-3 py-1 text-[11px] font-semibold tracking-[0.18em]",
        styles[status]
      )}
    >
      {status}
    </span>
  );
}

