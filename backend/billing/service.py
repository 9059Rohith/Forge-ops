from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import new_id, utcnow
from billing.models import PLAN_CREDITS, RepairCredit, Subscription, User


def _datetime(value: Any, fallback: datetime) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return fallback


async def ensure_demo_user(session: AsyncSession) -> User:
    user = await session.scalar(select(User).where(User.github_username == "forgeguard-demo"))
    if user is None:
        values = {
            "id": new_id(),
            "github_username": "forgeguard-demo",
            "dodo_customer_id": None,
            "created_at": utcnow(),
        }
        dialect = session.bind.dialect.name if session.bind else "sqlite"
        statement = (
            postgres_insert(User).values(**values).on_conflict_do_nothing(
                index_elements=["github_username"]
            )
            if dialect == "postgresql"
            else sqlite_insert(User).values(**values).on_conflict_do_nothing(
                index_elements=["github_username"]
            )
        )
        await session.execute(statement)
        await session.commit()
        user = await session.scalar(
            select(User).where(User.github_username == "forgeguard-demo")
        )
        if user is None:
            raise RuntimeError("Unable to create demo billing user")

    now = datetime.now(UTC)
    period_start = datetime(now.year, now.month, 1, tzinfo=UTC)
    period_end = (
        datetime(now.year + 1, 1, 1, tzinfo=UTC)
        if now.month == 12
        else datetime(now.year, now.month + 1, 1, tzinfo=UTC)
    )
    credit = await session.scalar(
        select(RepairCredit)
        .where(
            RepairCredit.user_id == user.id,
            RepairCredit.period_start == period_start,
            RepairCredit.period_end == period_end,
        )
    )
    if credit is None:
        values = {
            "id": new_id(),
            "user_id": user.id,
            "credits_remaining": PLAN_CREDITS["free"],
            "credits_used": 0,
            "period_start": period_start,
            "period_end": period_end,
        }
        dialect = session.bind.dialect.name if session.bind else "sqlite"
        statement = (
            postgres_insert(RepairCredit).values(**values).on_conflict_do_nothing(
                index_elements=["user_id", "period_start", "period_end"]
            )
            if dialect == "postgresql"
            else sqlite_insert(RepairCredit).values(**values).on_conflict_do_nothing(
                index_elements=["user_id", "period_start", "period_end"]
            )
        )
        await session.execute(statement)
    await session.commit()
    return user


async def process_subscription_event(session: AsyncSession, event: dict[str, Any]) -> None:
    event_type = str(event.get("type", ""))
    data = event.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("object"), dict):
        data = data["object"]
    if not isinstance(data, dict):
        return

    aliases = {
        "subscription.created": "active",
        "subscription.active": "active",
        "subscription.updated": "updated",
        "subscription.renewed": "renewed",
        "invoice.paid": "renewed",
        "subscription.canceled": "canceled",
        "subscription.cancelled": "canceled",
    }
    action = aliases.get(event_type)
    if action is None:
        return

    subscription_id = str(data.get("subscription_id") or data.get("id") or "")
    existing = await session.scalar(
        select(Subscription).where(Subscription.dodo_subscription_id == subscription_id)
    ) if subscription_id else None

    if action == "canceled":
        if existing:
            existing.status = "canceled"
            await session.commit()
        return

    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    user_id = str(metadata.get("user_id") or data.get("user_id") or "")
    plan = str(metadata.get("plan") or data.get("plan") or "free").lower()
    if plan not in PLAN_CREDITS:
        plan = "free"
    user = await session.get(User, user_id) if user_id else None
    if user is None and data.get("customer_id"):
        user = await session.scalar(
            select(User).where(User.dodo_customer_id == str(data["customer_id"]))
        )
    if user is None or not subscription_id:
        return

    now = datetime.now(UTC)
    period_start = _datetime(
        data.get("current_period_start") or data.get("previous_billing_date"), now
    )
    period_end = _datetime(
        data.get("current_period_end") or data.get("next_billing_date"),
        period_start + timedelta(days=30),
    )
    status = str(data.get("status", "active")).lower().replace("cancelled", "canceled")
    if status not in {"active", "past_due", "canceled"}:
        status = "active" if action in {"active", "renewed"} else "past_due"

    if existing is None:
        existing = Subscription(
            user_id=user.id,
            dodo_subscription_id=subscription_id,
            plan=plan,
            status=status,
            current_period_start=period_start,
            current_period_end=period_end,
        )
        session.add(existing)
    else:
        existing.user_id = user.id
        existing.plan = plan
        existing.status = status
        existing.current_period_start = period_start
        existing.current_period_end = period_end

    credit = await session.scalar(
        select(RepairCredit).where(
            RepairCredit.user_id == user.id,
            RepairCredit.period_start == period_start,
            RepairCredit.period_end == period_end,
        )
    )
    if credit is None:
        session.add(
            RepairCredit(
                user_id=user.id,
                credits_remaining=PLAN_CREDITS[plan],
                credits_used=0,
                period_start=period_start,
                period_end=period_end,
            )
        )
    await session.commit()
