import { GitBranch, GitFork, ShieldCheck } from "lucide-react";
import type { TaskDetail } from "@/lib/types";

const statusColors: Record<string, string> = {
  queued: "text-muted",
  planning: "text-sky-300",
  engineering: "text-sky-300",
  reviewing: "text-sky-300",
  blocked: "text-danger",
  repairing: "text-amber",
  verified: "text-mint",
  failed: "text-danger",
};

function Metric({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 border-line px-4 py-3 first:pl-0 lg:border-l lg:first:border-l-0 lg:first:pl-4">
      <div className="font-mono text-[10px] uppercase tracking-[.14em] text-muted">{label}</div>
      <div className="mt-2 truncate font-mono text-sm text-ink">{children}</div>
    </div>
  );
}

export function StatusSummary({ task }: { task: TaskDetail }) {
  return (
    <section className="grid rounded-lg border border-line bg-panel/85 px-4 md:grid-cols-2 lg:grid-cols-[2.4fr_1.35fr_.6fr_1fr_.7fr_.7fr_.65fr] lg:divide-x lg:divide-line">
      <Metric label="Task"><span className="font-sans font-medium">{task.description}</span></Metric>
      <Metric label="Repository"><span className="inline-flex items-center gap-2"><GitFork className="size-3.5" />{task.project.repo_url}</span></Metric>
      <Metric label="Branch"><span className="inline-flex items-center gap-2"><GitBranch className="size-3.5" />{task.project.branch}</span></Metric>
      <Metric label="Status"><strong className={`inline-flex items-center gap-2 ${statusColors[task.status]}`}><ShieldCheck className="size-4" />{task.status.toUpperCase()}</strong></Metric>
      <Metric label="Confidence"><strong className="text-mint">{task.confidence_score == null ? "—" : `${task.confidence_score.toFixed(1)}%`}</strong></Metric>
      <Metric label="Tests"><strong className={task.tests_total > 0 && task.tests_passed === task.tests_total ? "text-mint" : "text-muted"}>{task.tests_passed} / {task.tests_total}</strong></Metric>
      <Metric label="Repair cycles"><strong className="text-amber">{task.repair_cycles}</strong></Metric>
    </section>
  );
}

