"use client";

import dynamic from "next/dynamic";
import { FileCode2 } from "lucide-react";

const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div className="grid h-[220px] place-items-center font-mono text-xs text-muted">Loading diff renderer…</div>,
});

export function DiffViewer({ diff, fileCount }: { diff: string; fileCount: number }) {
  return (
    <section className="overflow-hidden rounded-lg border border-line bg-panel/75" aria-labelledby="diff-title">
      <div className="flex h-11 items-center justify-between border-b border-line px-4">
        <div className="flex items-center gap-4">
          <h2 id="diff-title" className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[.14em] text-ink"><FileCode2 className="size-4 text-mint" />Diff</h2>
          <span className="font-mono text-[10px] text-muted">Files changed ({fileCount})</span>
        </div>
        <span className="font-mono text-[10px] text-muted">Read only</span>
      </div>
      <Editor
        height="220px"
        defaultLanguage="diff"
        value={diff || "Waiting for the Engineer Agent to produce a patch…"}
        theme="vs-dark"
        options={{
          readOnly: true,
          minimap: { enabled: false },
          fontSize: 12,
          lineHeight: 20,
          fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
          scrollBeyondLastLine: false,
          wordWrap: "on",
          renderLineHighlight: "none",
          padding: { top: 14, bottom: 14 },
          overviewRulerBorder: false,
        }}
      />
    </section>
  );
}
