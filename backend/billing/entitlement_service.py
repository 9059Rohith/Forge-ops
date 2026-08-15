from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from billing.models import RepairCredit, RepairUsage


@dataclass(frozen=True, slots=True)
class EntitlementResult:
    has_credit: bool
    credits_remaining: int
    reason: str


class EntitlementService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def reserve_for_job(self, user_id: str, repair_job_id: str) -> EntitlementResult:
        existing = await self.session.scalar(
            select(RepairUsage).where(RepairUsage.repair_job_id == repair_job_id)
        )
        if existing and existing.status != "refunded":
            credit = await self.session.get(RepairCredit, existing.credit_id)
            return EntitlementResult(True, credit.credits_remaining if credit else 0, "already authorized")

        credit = await self.session.scalar(
            select(RepairCredit)
            .where(RepairCredit.user_id == user_id)
            .order_by(RepairCredit.period_end.desc())
            .limit(1)
        )
        if credit is None:
            return EntitlementResult(False, 0, "no active credit period")

        result = await self.session.execute(
            update(RepairCredit)
            .where(RepairCredit.id == credit.id, RepairCredit.credits_remaining > 0)
            .values(
                credits_remaining=RepairCredit.credits_remaining - 1,
                credits_used=RepairCredit.credits_used + 1,
            )
        )
        if result.rowcount != 1:
            await self.session.rollback()
            return EntitlementResult(False, 0, "repair credits exhausted")

        if existing:
            existing.status = "authorized"
            existing.credits_consumed = 1
            existing.credit_id = credit.id
        else:
            self.session.add(
                RepairUsage(
                    user_id=user_id,
                    repair_job_id=repair_job_id,
                    credit_id=credit.id,
                    status="authorized",
                )
            )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            usage = await self.session.scalar(
                select(RepairUsage).where(RepairUsage.repair_job_id == repair_job_id)
            )
            if usage and usage.status != "refunded":
                stored_credit = await self.session.get(RepairCredit, usage.credit_id)
                return EntitlementResult(
                    True,
                    stored_credit.credits_remaining if stored_credit else 0,
                    "already authorized",
                )
            raise
        await self.session.refresh(credit)
        return EntitlementResult(True, credit.credits_remaining, "repair credit reserved")

    async def record_repair_outcome(self, repair_job_id: str, status: str) -> None:
        usage = await self.session.scalar(
            select(RepairUsage).where(RepairUsage.repair_job_id == repair_job_id)
        )
        if usage is None or usage.status == "refunded":
            return
        if status == "pre_repair_failure" and usage.status == "authorized":
            await self.session.execute(
                update(RepairCredit)
                .where(RepairCredit.id == usage.credit_id)
                .values(
                    credits_remaining=RepairCredit.credits_remaining + usage.credits_consumed,
                    credits_used=RepairCredit.credits_used - usage.credits_consumed,
                )
            )
            usage.status = "refunded"
        else:
            usage.status = "consumed"
        await self.session.commit()


async def check_and_reserve_credit(
    session: AsyncSession, user_id: str, repair_job_id: str
) -> EntitlementResult:
    return await EntitlementService(session).reserve_for_job(user_id, repair_job_id)


async def record_repair_authorized(
    session: AsyncSession, user_id: str, repair_job_id: str
) -> EntitlementResult:
    return await EntitlementService(session).reserve_for_job(user_id, repair_job_id)


async def record_repair_outcome(
    session: AsyncSession, repair_job_id: str, status: str
) -> None:
    await EntitlementService(session).record_repair_outcome(repair_job_id, status)
