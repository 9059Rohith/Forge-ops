"use client";

import { useEffect, useState } from "react";
import { KeyRound, LoaderCircle } from "lucide-react";
import { authorizeRepair, getAuthorization } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface Props {
  taskId: string;
  severity: string;
  summary: string;
  confidence: number | null;
  creditsRemaining?: number;
  onAuthorized?: () => void;
}

export function AuthorizationCard({ taskId, severity, summary, confidence, creditsRemaining, onAuthorized }: Props) {
  const [available, setAvailable] = useState(creditsRemaining);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (available !== undefined) return;
    getAuthorization(taskId).then((value) => setAvailable(value.credits_remaining)).catch(() => setError("Unable to load credit availability."));
  }, [available, taskId]);

  async function authorize() {
    setBusy(true);
    setError("");
    try {
      const result = await authorizeRepair(taskId);
      setAvailable(result.credits_remaining);
      if (onAuthorized) onAuthorized();
      else window.location.reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to authorize repair.");
      setBusy(false);
    }
  }

  return (
    <section className="rounded-lg border border-amber-400/45 bg-amber-400/5 p-5" aria-label="Repair authorization required">
      <div className="flex items-start gap-3"><KeyRound className="mt-0.5 size-5 text-amber-300" /><div><p className="font-mono text-[10px] uppercase tracking-[.18em] text-amber-300">Authorization required · {severity}</p><h2 className="mt-1 font-semibold">{summary}</h2></div></div>
      <div className="mt-4 grid gap-2 font-mono text-xs text-muted sm:grid-cols-3"><span>Confidence: {confidence ?? "—"}%</span><span>Estimated usage: 1 Repair Credit</span><span>Available: {available ?? "…"}</span></div>
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
      <Button type="button" className="mt-4" disabled={busy || !available} onClick={() => void authorize()}>{busy && <LoaderCircle className="size-4 animate-spin" />}Authorize Repair</Button>
    </section>
  );
}
