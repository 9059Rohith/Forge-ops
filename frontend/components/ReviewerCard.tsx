import { Crosshair, ShieldCheck, Swords } from "lucide-react";
import type { Evaluation } from "@/lib/types";

const metadata = {
  security: { label: "Security Review", icon: ShieldCheck },
  scope: { label: "Scope Review", icon: Crosshair },
  adversarial: { label: "Adversarial Review", icon: Swords },
};

export function ReviewerCard({ evaluation, defaultOpen = false }: { evaluation: Evaluation; defaultOpen?: boolean }) {
  const { label, icon: Icon } = metadata[evaluation.category];
  const good = evaluation.severity === "none" || evaluation.severity === "low";
  return (
    <details className="group rounded-lg border border-line bg-panel/70 open:border-mint/35" open={defaultOpen}>
      <summary className="grid cursor-pointer list-none items-center gap-4 px-4 py-3 outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-mint md:grid-cols-[minmax(220px,1.6fr)_minmax(180px,2fr)_100px_110px_20px]">
        <span className="flex items-center gap-3 font-medium text-ink">
          <span className={`grid size-9 place-items-center rounded-md border ${good ? "border-mint/35 bg-mint/10 text-mint" : "border-danger/35 bg-danger/10 text-danger"}`}>
            <Icon className="size-4" strokeWidth={1.8} aria-hidden="true" />
          </span>
          {label}
        </span>
        <span className="line-clamp-2 text-sm leading-6 text-muted">{evaluation.finding}</span>
        <span className={`font-mono text-xs uppercase ${good ? "text-mint" : "text-danger"}`}>{good ? "Approved" : evaluation.severity}</span>
        <strong className={good ? "font-mono text-sm text-mint" : "font-mono text-sm text-danger"}>{evaluation.score.toFixed(1)}%</strong>
        <span className="text-muted transition group-open:rotate-180">⌄</span>
      </summary>
      <div className="border-t border-line/80 px-4 py-4 font-mono text-xs leading-6 text-muted">
        <pre className="overflow-x-auto whitespace-pre-wrap">{JSON.stringify(evaluation.evidence, null, 2)}</pre>
      </div>
    </details>
  );
}
