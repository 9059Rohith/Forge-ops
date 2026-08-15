"""Create idempotent local billing data so a fresh demo can start immediately."""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
# The backend is intentionally not packaged at the repository root; insert it
# only for this operator script so application imports behave exactly as in Uvicorn.
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'backend' / 'forgeguard.db'}")

from app.db import init_db, session_scope  # noqa: E402
from billing.models import PLAN_CREDITS, RepairCredit, Subscription, User  # noqa: E402


async def seed() -> None:
    await init_db()
    now = datetime.now(UTC)
    period_end = now + timedelta(days=30)
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.github_username == "forgeguard-demo"))
        if user is None:
            user = User(github_username="forgeguard-demo", dodo_customer_id="demo_customer")
            session.add(user)
            await session.flush()

        subscription = await session.scalar(
            select(Subscription).where(Subscription.dodo_subscription_id == "demo_pro")
        )
        if subscription is None:
            subscription = Subscription(
                user_id=user.id,
                dodo_subscription_id="demo_pro",
                plan="pro",
                status="active",
                current_period_start=now,
                current_period_end=period_end,
            )
            session.add(subscription)

        credit = await session.scalar(
            select(RepairCredit)
            .where(RepairCredit.user_id == user.id)
            .order_by(RepairCredit.period_end.desc())
        )
        if credit is None:
            session.add(
                RepairCredit(
                    user_id=user.id,
                    credits_remaining=PLAN_CREDITS["pro"],
                    credits_used=0,
                    period_start=now,
                    period_end=period_end,
                )
            )
        await session.commit()
    print("ForgeGuard demo user ready: Pro plan, 150 Repair Credits")


if __name__ == "__main__":
    asyncio.run(seed())
