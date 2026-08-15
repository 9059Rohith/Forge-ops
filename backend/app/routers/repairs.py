from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Task
from app.routers.tasks import schedule_task
from billing.entitlement_service import EntitlementService
from billing.models import RepairCredit

router = APIRouter(tags=["repairs"])


async def _task(task_id: str, session: AsyncSession) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Repair job not found")
    return task


async def _remaining(session: AsyncSession, user_id: str | None) -> int:
    if not user_id:
        return 0
    credit = await session.scalar(
        select(RepairCredit)
        .where(RepairCredit.user_id == user_id)
        .order_by(RepairCredit.period_end.desc())
    )
    return credit.credits_remaining if credit else 0


@router.get("/{task_id}/authorization")
async def authorization(task_id: str, session: AsyncSession = Depends(get_db)):
    task = await _task(task_id, session)
    return {
        "task_id": task.id,
        "awaiting_authorization": task.status == "awaiting_authorization",
        "credits_remaining": await _remaining(session, task.user_id),
        "pending_plan": task.pending_plan,
    }


@router.post("/{task_id}/authorize")
async def authorize(task_id: str, session: AsyncSession = Depends(get_db)):
    task = await _task(task_id, session)
    if task.status != "awaiting_authorization":
        raise HTTPException(status_code=409, detail="Repair job is not awaiting authorization")
    if not task.user_id:
        raise HTTPException(status_code=409, detail="Repair job has no billable owner")
    result = await EntitlementService(session).reserve_for_job(task.user_id, task.id)
    if not result.has_credit:
        raise HTTPException(status_code=402, detail=result.reason)
    task = await _task(task_id, session)
    task.status = "queued"
    await session.commit()
    schedule_task(task.id)
    return {
        "task_id": task.id,
        "status": "authorized",
        "credits_remaining": result.credits_remaining,
    }
