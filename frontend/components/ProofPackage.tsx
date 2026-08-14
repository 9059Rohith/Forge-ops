"use client";

import { Check, Copy, FileCheck2 } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function ProofPackage({ proof }: { proof: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard.writeText(proof);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }
  return (
    <section className="rounded-lg border border-line bg-panel/75" aria-labelledby="proof-title">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <h2 id="proof-title" className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[.14em] text-ink"><FileCheck2 className="size-4 text-mint" />Proof package</h2>
        <button onClick={copy} disabled={!proof} className="inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 font-mono text-[11px] text-muted hover:border-mint/50 hover:text-ink disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mint">
          {copied ? <Check className="size-3.5 text-mint" /> : <Copy className="size-3.5" />}
          {copied ? "Copied" : "Copy proof"}
        </button>
      </div>
      <div className="prose prose-invert max-h-[70px] max-w-none overflow-auto p-4 text-sm leading-6 text-muted prose-headings:text-ink prose-strong:text-ink prose-table:font-mono prose-th:text-left prose-td:border-line prose-th:border-line">
        {proof ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{proof}</ReactMarkdown> : <p>Proof is generated when verification reaches a terminal decision.</p>}
      </div>
    </section>
  );
}
