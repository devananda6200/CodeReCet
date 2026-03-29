import type { StreamRecord } from "../../types";
import { StreamCard } from "./StreamCard";

export function StreamGrid({
  streams,
  onToggle
}: {
  streams: StreamRecord[];
  onToggle: (stream: StreamRecord) => void;
}) {
  return (
    <section className="grid gap-5 xl:grid-cols-2">
      {streams.slice(0, 4).map((stream) => (
        <StreamCard key={stream.id} stream={stream} onToggle={onToggle} />
      ))}
    </section>
  );
}

