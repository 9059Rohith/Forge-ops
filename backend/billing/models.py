from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, new_id, utcnow

PLAN_CREDITS = {"free": 3, "developer": 50, "pro": 150, "team": 500}
PLANS = tuple(PLAN_CREDITS)
SUBSCRIPTION_STATUSES = ("active", "past_due", "canceled")
USAGE_STATUSES = ("authorized", "consumed", "refunded")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    github_username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    dodo_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(f"plan IN {PLANS}", name="ck_subscriptions_plan"),
        CheckConstraint(
            f"status IN {SUBSCRIPTION_STATUSES}", name="ck_subscriptions_status"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    dodo_subscription_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RepairCredit(Base):
    __tablename__ = "repair_credits"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", "period_end", name="uq_credit_period"),
        CheckConstraint("credits_remaining >= 0", name="ck_credit_remaining_nonnegative"),
        CheckConstraint("credits_used >= 0", name="ck_credit_used_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    credits_remaining: Mapped[int] = mapped_column(Integer, default=0)
    credits_used: Mapped[int] = mapped_column(Integer, default=0)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RepairUsage(Base):
    __tablename__ = "repair_usages"
    __table_args__ = (
        CheckConstraint(f"status IN {USAGE_STATUSES}", name="ck_repair_usage_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    repair_job_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, index=True
    )
    credit_id: Mapped[str] = mapped_column(
        ForeignKey("repair_credits.id", ondelete="RESTRICT"), index=True
    )
    credits_consumed: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="authorized")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
