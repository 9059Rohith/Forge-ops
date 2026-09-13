"use client";

import { useEffect, useState } from "react";
import { Coins, LoaderCircle } from "lucide-react";
import { createCheckout, getBillingStatus } from "@/lib/api";
import type { BillingStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";

export function RepairCreditsCard({ userId }: { userId: string }) {
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [error, setError] = useState(false);
  const [opening, setOpening] = useState(false);

  useEffect(() => {
    let active = true;
    getBillingStatus(userId)
      .then((value) => active && setBilling(value))
      .catch(() => active && setError(true));
    return () => { active = false; };
  }, [userId]);

  async function openCheckout(plan: "developer" | "pro") {
    setOpening(true);
    setError(false);
    try {
      const result = await createCheckout(userId, plan);
      window.location.assign(result.checkout_url);
    } catch {
      setError(true);
      setOpening(false);
    }
  }

  if (error && !billing) {
    return <section role="alert" className="rounded-[10px] border border-danger/35 bg-danger/10 p-5 text-sm text-danger">Repair Credits are temporarily unavailable.</section>;
  }
  if (!billing) {
    return <section aria-label="Loading Repair Credits" className="flex min-h-36 items-center justify-center rounded-[10px] border border-line bg-panel/75"><LoaderCircle className="size-5 animate-spin text-mint" /></section>;
  }

  const percent = billing.credits_total ? Math.min(100, (billing.credits_used / billing.credits_total) * 100) : 0;
  const reset = billing.period_end ? new Date(billing.period_end).toLocaleDateString() : "Not scheduled";
  const planName = billing.plan[0].toUpperCase() + billing.plan.slice(1);
  return (
    <section className="rounded-[10px] border border-line bg-panel/90 p-5 shadow-panel" aria-label="Repair Credits">
      <div className="flex items-start justify-between gap-4">
        <div><p className="font-mono text-[10px] uppercase tracking-[.18em] text-mint">Repair Credits</p><h2 className="mt-1 text-lg font-semibold">{planName} plan</h2></div>
        <Coins className="size-5 text-mint" aria-hidden="true" />
      </div>
      <p className="mt-4 text-2xl font-semibold">{billing.credits_remaining} repairs remaining</p>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-line" aria-label={`${billing.credits_used} of ${billing.credits_total} credits used`}><div className="h-full rounded-full bg-mint" style={{ width: `${percent}%` }} /></div>
      <div className="mt-2 flex justify-between font-mono text-[10px] text-muted"><span>{billing.credits_used} used</span><span>Resets {reset}</span></div>
      {error && <p role="alert" className="mt-3 text-xs text-danger">Checkout is not configured yet.</p>}
      <div className="mt-4 grid grid-cols-2 gap-2">
        <Button type="button" className="bg-transparent text-mint hover:bg-mint/10" disabled={opening} onClick={() => void openCheckout("developer")}>Buy Credits</Button>
        <Button type="button" disabled={opening} onClick={() => void openCheckout("pro")}>Upgrade</Button>
      </div>
    </section>
  );
}
