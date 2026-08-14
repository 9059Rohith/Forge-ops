"use client";

import Link from "next/link";
import { LoaderCircle, RotateCcw } from "lucide-react";
import { Brand } from "@/components/Brand";
import { TaskDashboard } from "@/components/TaskDashboard";
import { useTaskPolling } from "@/hooks/useTaskPolling";

export function TaskView({ taskId }: { taskId: string }) {
  const state = useTaskPolling(taskId);
  if (state.loading && !state.task) {
    return <main className="grid min-h-screen place-items-center bg-canvas text-ink"><div className="text-center"><LoaderCircle className="mx-auto size-7 animate-spin text-mint" /><p className="mt-4 font-mono text-xs text-muted">Loading the flight recorder…</p></div></main>;
  }
  if (!state.task) {
    return <main className="min-h-screen bg-canvas p-6 text-ink"><Brand /><div className="mx-auto mt-32 max-w-lg rounded-lg border border-danger/40 bg-danger/10 p-8 text-center"><h1 className="text-xl font-semibold">Unable to load this task</h1><p role="alert" className="mt-3 text-sm text-danger">{state.error}</p><Link href="/" className="mt-6 inline-flex items-center gap-2 font-mono text-xs text-mint"><RotateCcw className="size-4" />Return to task entry</Link></div></main>;
  }
  return <TaskDashboard task={state.task} logs={state.logs} diff={state.diff} proof={state.proof} loading={state.loading} />;
}

