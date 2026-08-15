# Repair Credits

Repair Credits are the entitlement behind autonomous repair jobs.
One credit authorizes one job—not one agent call or repair cycle.
Retries up to `MAX_REPAIR_CYCLES` reuse the job's original credit.
The reservation is an atomic conditional database update.
A unique usage row prevents duplicate authorization and webhook retries.
Pre-repair system failures refund the reserved credit.
Failed repair cycles and exhausted retries still consume it.
Plans include free 3, developer 50, pro 150, and team 500 monthly credits.
Dodo Checkout sells plan subscriptions; ForgeGuard remains usable without checkout.
Dodo webhook signatures are verified against the exact raw request body.
Secrets and product IDs come only from environment variables.
The dashboard always surfaces paused jobs instead of discarding findings.
