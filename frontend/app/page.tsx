import { ShieldCheck } from "lucide-react";
import { Brand } from "@/components/Brand";
import { TaskForm } from "@/components/TaskForm";
import { WorkflowRail } from "@/components/WorkflowRail";
import { RepairCreditsCard } from "@/components/RepairCreditsCard";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-canvas text-ink">
      <header className="border-b border-line/80">
        <div className="mx-auto flex h-[86px] max-w-[1584px] items-center px-8">
          <Brand entry />
        </div>
      </header>
      <div className="mx-auto max-w-[1500px] px-6 pb-8 pt-14 lg:px-10 lg:pt-10">
        <section className="grid items-center gap-12 lg:grid-cols-2 lg:gap-11">
          <div className="max-w-2xl lg:pl-8">
            <h1 className="max-w-[700px] text-[clamp(3rem,4.1vw,4rem)] font-semibold leading-[1.05] tracking-[-.05em] text-ink">
              Autonomous engineering, with proof.
            </h1>
            <p className="mt-7 max-w-[600px] text-lg leading-8 text-muted md:text-xl">
              Give an agent a task. ForgeGuard builds the patch, challenges it, repairs it, and returns evidence you can trust.
            </p>
          </div>
          <div className="w-full space-y-3 lg:max-w-[647px]"><TaskForm /><RepairCreditsCard /></div>
        </section>
        <section className="mx-auto mt-14 max-w-[1372px] lg:mt-14">
          <WorkflowRail />
        </section>
        <footer className="mt-16 flex items-center justify-center gap-3 border-t border-line/45 pt-7 text-center font-mono text-xs text-muted md:text-sm">
          <ShieldCheck className="size-4" aria-hidden="true" />
          <p>Codex can write the code. ForgeGuard makes autonomous coding accountable.</p>
        </footer>
      </div>
    </main>
  );
}
