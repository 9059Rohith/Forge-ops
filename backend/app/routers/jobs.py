from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import AuditLog, Task
from billing.models import RepairUsage

router = APIRouter(tags=["evidence"])


@router.get("/{job_id}/evidence")
async def evidence(job_id: str, session: AsyncSession = Depends(get_db)):
    task = await session.scalar(
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.evaluations),
            selectinload(Task.agent_runs),
            selectinload(Task.flight_logs),
        )
        .where(Task.id == job_id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Job not found")
    usage = await session.scalar(
        select(RepairUsage).where(RepairUsage.repair_job_id == job_id)
    )
    audits = (
        await session.scalars(
            select(AuditLog).where(AuditLog.job_id == job_id).order_by(AuditLog.timestamp)
        )
    ).all()
    plans = [
        run.output.get("plan")
        for run in task.agent_runs
        if run.agent_name == "engineer" and run.output.get("plan")
    ]
    return {
        "job": {
            "id": task.id,
            "status": task.status,
            "description": task.description,
            "repository": task.project.repo_url,
            "branch": task.project.branch,
            "repair_branch": task.repair_branch,
            "pull_request": {
                "url": task.pr_url,
                "number": task.pr_number,
            }
            if task.pr_url
            else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        },
        "findings": [
            {
                "agent": item.category,
                "severity": item.severity,
                "score": item.score,
                "finding": item.finding,
                "evidence": item.evidence,
            }
            for item in task.evaluations
        ],
        "plan": task.pending_plan or (plans[-1] if plans else None),
        "diff": task.diff_text,
        "tests": {"passed": task.tests_passed, "total": task.tests_total},
        "review_verdict": {
            "status": task.status,
            "risk_level": task.risk_level,
            "confidence": task.confidence_score,
            "repair_cycles": task.repair_cycles,
        },
        "credit_usage": (
            {
                "credits_consumed": usage.credits_consumed,
                "status": usage.status,
                "created_at": usage.created_at.isoformat(),
            }
            if usage
            else None
        ),
        "audit_log": [
            {
                "actor": item.actor,
                "action": item.action,
                "detail": item.detail,
                "timestamp": item.timestamp.isoformat(),
            }
            for item in audits
        ],
    }
