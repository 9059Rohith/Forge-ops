import { ArrowRight, Braces, Cpu, FileCheck2, ShieldCheck } from "lucide-react";

const steps = [
  { label: "Engineer", icon: Braces },
  { label: "Security · Scope · Adversarial", icon: ShieldCheck },
  { label: "Risk Engine", icon: Cpu },
  { label: "Proof", icon: FileCheck2 },
];

export function WorkflowRail() {
  return (
    <ol aria-label="ForgeGuard workflow" className="grid gap-4 rounded-[10px] border border-line bg-panel/55 px-5 py-7 md:grid-cols-[1fr_auto_2fr_auto_1fr_auto_1fr] md:items-center md:px-10">
      {steps.map(({ label, icon: Icon }, index) => (
        <li key={label} className="contents">
          <div className="flex items-center gap-4 font-mono text-sm text-ink md:text-[15px]">
            <span className="grid size-12 shrink-0 place-items-center rounded-lg border border-line bg-surface text-mint">
              <Icon className="size-6" strokeWidth={1.7} aria-hidden="true" />
            </span>
            <span>{label}</span>
          </div>
          {index < steps.length - 1 && (
            <ArrowRight className="hidden size-4 text-muted/60 md:block" aria-hidden="true" />
          )}
        </li>
      ))}
    </ol>
  );
}
