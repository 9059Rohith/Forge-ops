import { Copy } from "lucide-react";
import type { FlightLog } from "@/lib/types";

export function FlightRecorder({ logs }: { logs: FlightLog[] }) {
  const text = logs.map((log) => `${new Date(log.timestamp).toLocaleTimeString()}  ${log.event}`).join("\n");
  return (
    <section className="flex h-[480px] min-h-[360px] flex-col rounded-lg border border-line bg-panel/75 p-4" aria-labelledby="flight-title">
      <div className="flex items-center justify-between">
        <h2 id="flight-title" className="font-mono text-[11px] uppercase tracking-[.14em] text-muted">Flight recorder</h2>
        <span className="inline-flex items-center gap-2 font-mono text-[10px] text-mint"><span className="size-1.5 animate-pulse rounded-full bg-mint" />Live</span>
      </div>
      <ol className="mt-3 flex-1 space-y-0 overflow-auto rounded-md border border-line bg-canvas/45 p-3 font-mono text-[11px] leading-6">
        {logs.length === 0 && <li className="text-muted">Waiting for the first recorded event…</li>}
        {logs.map((log) => (
          <li key={log.id} className="relative grid grid-cols-[68px_1fr] gap-2 border-l border-mint/30 pl-4 text-muted before:absolute before:-left-[3px] before:top-[9px] before:size-[5px] before:rounded-full before:bg-mint">
            <time>{new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}</time>
            <span className={/blocked|failed|critical/i.test(log.event) ? "text-danger" : /repair/i.test(log.event) ? "text-amber" : "text-slate-300"}>{log.event}</span>
          </li>
        ))}
      </ol>
      <button onClick={() => navigator.clipboard.writeText(text)} className="mt-3 inline-flex h-9 items-center justify-center gap-2 self-end rounded-md border border-line px-3 font-mono text-[11px] text-muted hover:border-mint/50 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mint">
        <Copy className="size-3.5" />Copy log
      </button>
    </section>
  );
}
