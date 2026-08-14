import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export function Brand({ compact = false, entry = false }: { compact?: boolean; entry?: boolean }) {
  return (
    <Link
      href="/"
      className="inline-flex items-center gap-3 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mint"
      aria-label="ForgeGuard home"
    >
      <span className={`grid place-items-center rounded-lg border border-line bg-surface text-mint shadow-panel ${entry ? "size-11" : "size-9"}`}>
        <ShieldCheck className={entry ? "size-6" : "size-5"} strokeWidth={1.8} aria-hidden="true" />
      </span>
      {!compact && <span className={`${entry ? "text-[22px]" : "text-lg"} font-semibold tracking-tight text-ink`}>ForgeGuard</span>}
    </Link>
  );
}
