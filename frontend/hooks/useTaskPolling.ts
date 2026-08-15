"use client";

import { useEffect, useRef, useState } from "react";
import { getDiff, getFlightLog, getProof, getTask } from "@/lib/api";
import type { FlightLog, TaskDetail, VerificationReceipt } from "@/lib/types";

const TERMINAL = new Set(["verified", "failed", "awaiting_authorization", "manual_review_required"]);

export function useTaskPolling(taskId: string, intervalMs = 1500) {
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [logs, setLogs] = useState<FlightLog[]>([]);
  const [diff, setDiff] = useState("");
  const [proof, setProof] = useState("");
  const [receipt, setReceipt] = useState<VerificationReceipt | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let active = true;

    async function refresh() {
      try {
        const [nextTask, nextLogs, nextDiff, nextProof] = await Promise.all([
          getTask(taskId),
          getFlightLog(taskId),
          getDiff(taskId),
          getProof(taskId),
        ]);
        if (!active) return;
        setTask(nextTask);
        setLogs(nextLogs);
        setDiff(nextDiff.diff);
        setProof(nextProof.markdown);
        setReceipt(nextProof.receipt);
        setError("");
        setLoading(false);
        if (!TERMINAL.has(nextTask.status)) timer.current = setTimeout(refresh, intervalMs);
      } catch (cause) {
        if (!active) return;
        setError(cause instanceof Error ? cause.message : "Unable to load task evidence.");
        setLoading(false);
        timer.current = setTimeout(refresh, Math.max(intervalMs, 3000));
      }
    }

    void refresh();
    return () => {
      active = false;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [intervalMs, taskId]);

  return { task, logs, diff, proof, receipt, error, loading };
}

