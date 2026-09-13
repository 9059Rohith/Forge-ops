import { CheckCircle2, FlaskConical, Gauge, RotateCcw } from "lucide-react";
import type { TaskDetail } from "@/lib/types";

export function RiskPanel({ task }: { task: TaskDetail }) {
  const auditComplete = task.status === "audit_complete";
  const rows = [
    { label: "Overall confidence", value: task.confidence_score == null ? "Pending" : `${task.confidence_score.toFixed(1)}%`, icon: Gauge },
    { label: auditComplete ? "Mode" : "Tests", value: auditComplete ? "Read-only audit" : `${task.tests_passed} / ${task.tests_total} passed`, icon: FlaskConical },
    { label: "Risk level", value: task.risk_level || "Pending", icon: CheckCircle2 },
    { label: "Repair cycles", value: String(task.repair_cycles), icon: RotateCcw },
  ];
  return (
    <section className="rounded-lg border border-line bg-panel/75 p-4" aria-labelledby="evidence-summary-title">
      <h2 id="evidence-summary-title" className="font-mono text-[11px] uppercase tracking-[.14em] text-muted">Evidence summary</h2>
      <dl className="mt-3 divide-y divide-line overflow-hidden rounded-md border border-line">
        {rows.map(({ label, value, icon: Icon }) => (
          <div key={label} className="flex items-center justify-between gap-4 px-3 py-3">
            <dt className="flex items-center gap-2 font-mono text-xs text-muted"><Icon className="size-3.5" />{label}</dt>
            <dd className="font-mono text-xs font-semibold text-mint">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
