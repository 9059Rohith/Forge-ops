"use client";

import Link from "next/link";
import { ArrowRight, ExternalLink, TriangleAlert } from "lucide-react";
import type { FlightLog, TaskDetail, VerificationReceipt } from "@/lib/types";
import { AgentGraph } from "@/components/AgentGraph";
import { Brand } from "@/components/Brand";
import { DiffViewer } from "@/components/DiffViewer";
import { FlightRecorder } from "@/components/FlightRecorder";
import { ProofPackage } from "@/components/ProofPackage";
import { ReviewerCard } from "@/components/ReviewerCard";
import { RiskPanel } from "@/components/RiskPanel";
import { StatusSummary } from "@/components/StatusSummary";
import { AuthorizationCard } from "@/components/AuthorizationCard";

interface Props {
  task: TaskDetail;
  logs: FlightLog[];
  diff: string;
  proof: string;
  receipt: VerificationReceipt | null;
  loading: boolean;
}

export function TaskDashboard({ task, logs, diff, proof, receipt }: Props) {
  const severityRank = { none: 0, low: 1, medium: 2, high: 3, critical: 4 };
  const mostSevere = [...task.evaluations].sort(
    (a, b) => severityRank[b.severity] - severityRank[a.severity] || a.score - b.score,
  )[0];
  return (
    <main className="min-h-screen bg-canvas px-3 pb-5 text-ink sm:px-5">
      <header className="mx-auto flex h-[62px] max-w-[1580px] items-center justify-between">
        <Brand />
        <Link href="/" className="inline-flex h-9 items-center gap-2 rounded-md border border-mint/50 px-3 font-mono text-[11px] text-ink transition hover:bg-mint/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mint">
          Run another task <ArrowRight className="size-3.5" />
        </Link>
      </header>
      <div className="mx-auto max-w-[1580px] space-y-3">
        <StatusSummary task={task} />
        {task.pr_url && (
          <a
            href={task.pr_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-between rounded-lg border border-mint/45 bg-mint/10 px-4 py-3 text-sm text-mint transition hover:bg-mint/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mint"
          >
            <span>Evidence-backed pull request #{task.pr_number} is ready for human review.</span>
            <ExternalLink className="size-4" />
          </a>
        )}
        {task.status === "awaiting_authorization" && (
          <AuthorizationCard
            taskId={task.id}
            severity={mostSevere?.severity || task.risk_level || "review"}
            summary={mostSevere?.finding || task.pending_plan || "A repair plan is ready to run."}
            confidence={task.confidence_score}
          />
        )}
        {task.error_message && (
          <div role="alert" className="flex items-start gap-3 rounded-lg border border-danger/40 bg-danger/10 p-4 text-sm text-danger"><TriangleAlert className="mt-0.5 size-4 shrink-0" />{task.error_message}</div>
        )}
        <div className="grid gap-3 xl:grid-cols-[minmax(0,3fr)_360px]">
          <div className="min-w-0 space-y-3">
            <AgentGraph task={task} />
            <section className="space-y-2" aria-label="Independent reviews">
              {task.evaluations.length === 0 ? (
                <div className="rounded-lg border border-line bg-panel/55 px-4 py-6 font-mono text-xs text-muted">Independent reviewers will appear when the patch is ready.</div>
              ) : task.evaluations.map((evaluation) => <ReviewerCard key={evaluation.id} evaluation={evaluation} auditMode={task.status === "audit_complete" || task.pending_plan === "Read-only security audit"} />)}
            </section>
            <DiffViewer
              diff={diff}
              fileCount={task.changed_files.length}
              emptyState={
                task.status === "audit_complete"
                  ? "No repository files were changed — this was a read-only security audit."
                  : undefined
              }
            />
          </div>
          <aside className="space-y-3">
            <RiskPanel task={task} />
            <FlightRecorder logs={logs} />
          </aside>
        </div>
        <ProofPackage proof={proof} receipt={receipt} />
        <footer className="flex flex-wrap items-center justify-between gap-3 px-2 pt-2 font-mono text-[10px] text-muted">
          <span>ForgeGuard v1.0.0</span>
          <span>Deterministic · Reproducible · Auditable</span>
          <span className="inline-flex items-center gap-2 text-mint"><span className="size-1.5 rounded-full bg-mint" />System healthy</span>
        </footer>
      </div>
    </main>
  );
}

