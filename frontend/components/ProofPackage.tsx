"use client";

import { Check, Copy, Download, FileCheck2, ShieldCheck } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { VerificationReceipt } from "@/lib/types";

export function ProofPackage({ proof, receipt }: { proof: string; receipt: VerificationReceipt | null }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard.writeText(proof);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  function downloadReceipt() {
    if (!receipt) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(receipt, null, 2)], { type: "application/json" }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `forgeguard-${receipt.receipt_id}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="rounded-lg border border-line bg-panel/75" aria-labelledby="proof-title">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h2 id="proof-title" className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[.14em] text-ink"><FileCheck2 className="size-4 text-mint" />Proof package</h2>
          {receipt && (
            <span className="inline-flex items-center gap-2 font-mono text-[10px] text-mint" aria-label={`Evidence sealed ${receipt.receipt_id}`}>
              <ShieldCheck className="size-3.5" />
              <span className="text-muted">Evidence sealed</span>
              <span>{receipt.receipt_id}</span>
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={downloadReceipt} disabled={!receipt} className="inline-flex h-9 items-center gap-2 rounded-md border border-mint/40 px-3 font-mono text-[11px] text-mint transition hover:bg-mint/10 disabled:border-line disabled:text-muted disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mint">
            <Download className="size-3.5" />Download receipt
          </button>
          <button onClick={copy} disabled={!proof} className="inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 font-mono text-[11px] text-muted hover:border-mint/50 hover:text-ink disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mint">
            {copied ? <Check className="size-3.5 text-mint" /> : <Copy className="size-3.5" />}
            {copied ? "Copied" : "Copy proof"}
          </button>
        </div>
      </div>
      <div className="prose prose-invert max-h-[70px] max-w-none overflow-auto p-4 text-sm leading-6 text-muted prose-headings:text-ink prose-strong:text-ink prose-table:font-mono prose-th:text-left prose-td:border-line prose-th:border-line">
        {proof ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{proof}</ReactMarkdown> : <p>Proof is generated when verification reaches a terminal decision.</p>}
      </div>
    </section>
  );
}
