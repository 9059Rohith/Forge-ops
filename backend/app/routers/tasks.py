from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.orchestrator import run_task
from app.core.proof_package import build_verification_receipt
from app.db import get_db
from app.models import Project, Task
from app.schemas import ProofView, TaskCreate, TaskCreated
from billing.models import User
from billing.service import ensure_demo_user

router = APIRouter(tags=["tasks"])
_running_tasks: set[asyncio.Task[None]] = set()


def schedule_task(task_id: str) -> None:
    background = asyncio.create_task(run_task(task_id), name=f"forgeguard-{task_id}")
    _running_tasks.add(background)
    background.add_done_callback(_running_tasks.discard)


async def _task_or_404(session: AsyncSession, task_id: str) -> Task:
    result = await session.execute(
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.evaluations),
            selectinload(Task.agent_runs),
            selectinload(Task.flight_logs),
        )
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _serialize_task(task: Task) -> dict[str, Any]:
    order = {"security": 0, "scope": 1, "adversarial": 2}
    return {
        "id": task.id,
        "user_id": task.user_id,
        "description": task.description,
        "status": task.status,
        "risk_level": task.risk_level,
        "confidence_score": task.confidence_score,
        "repair_cycles": task.repair_cycles,
        "tests_passed": task.tests_passed,
        "tests_total": task.tests_total,
        "changed_files": task.changed_files,
        "error_message": task.error_message,
        "pending_plan": task.pending_plan,
        "repair_branch": task.repair_branch,
        "pr_url": task.pr_url,
        "pr_number": task.pr_number,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "project": {
            "id": task.project.id,
            "repo_url": task.project.repo_url,
            "repo_full_name": task.project.repo_full_name,
            "branch": task.project.branch,
            "created_at": task.project.created_at.isoformat(),
        },
        "evaluations": [
            {
                "id": item.id,
                "category": item.category,
                "score": item.score,
                "severity": item.severity,
                "finding": item.finding,
                "evidence": item.evidence,
            }
            for item in sorted(task.evaluations, key=lambda item: order.get(item.category, 99))
        ],
        "agent_runs": [
            {
                "id": item.id,
                "agent_name": item.agent_name,
                "status": item.status,
                "started_at": item.started_at.isoformat(),
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "output": item.output,
            }
            for item in sorted(task.agent_runs, key=lambda item: item.started_at)
        ],
    }


@router.post("", response_model=TaskCreated, status_code=status.HTTP_202_ACCEPTED)
async def create_task(payload: TaskCreate, session: AsyncSession = Depends(get_db)):
    if payload.user_id:
        user = await session.get(User, payload.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        user = await ensure_demo_user(session)
    result = await session.execute(
        select(Project).where(
            Project.repo_url == payload.repo_url,
            Project.branch == payload.branch,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        project = Project(repo_url=payload.repo_url, branch=payload.branch)
        session.add(project)
        await session.flush()
    task = Task(project_id=project.id, user_id=user.id, description=payload.description)
    session.add(task)
    await session.commit()
    schedule_task(task.id)
    return TaskCreated(task_id=task.id)


@router.get("/{task_id}")
async def get_task(task_id: str, session: AsyncSession = Depends(get_db)):
    return _serialize_task(await _task_or_404(session, task_id))


@router.get("/{task_id}/flight-log")
async def get_flight_log(task_id: str, session: AsyncSession = Depends(get_db)):
    task = await _task_or_404(session, task_id)
    return [
        {"id": item.id, "timestamp": item.timestamp.isoformat(), "event": item.event}
        for item in task.flight_logs
    ]


@router.get("/{task_id}/diff")
async def get_diff(task_id: str, session: AsyncSession = Depends(get_db)):
    task = await _task_or_404(session, task_id)
    return {"diff": task.diff_text}


@router.get("/{task_id}/proof", response_model=ProofView)
async def get_proof(task_id: str, session: AsyncSession = Depends(get_db)):
    task = await _task_or_404(session, task_id)
    if not task.proof_text:
        return {"markdown": task.proof_text, "receipt": None}

    evaluations = {
        item.category: {
            "score": item.score,
            "severity": item.severity,
            "finding": item.finding,
            "evidence": item.evidence,
        }
        for item in sorted(task.evaluations, key=lambda item: item.category)
    }
    receipt = build_verification_receipt(
        task_id=task.id,
        description=task.description,
        repo_url=task.project.repo_url,
        branch=task.project.branch,
        changed_files=task.changed_files,
        tests_passed=task.tests_passed,
        tests_total=task.tests_total,
        evaluations=evaluations,
        confidence=task.confidence_score,
        risk_level=task.risk_level,
        repair_cycles=task.repair_cycles,
        decision="VERIFIED" if task.status == "verified" else "BLOCKED",
        agent_runs=[
            {
                "agent_name": item.agent_name,
                "status": item.status,
                "started_at": item.started_at.isoformat(),
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            }
            for item in sorted(task.agent_runs, key=lambda item: item.started_at)
        ],
        flight_logs=[
            {"timestamp": item.timestamp.isoformat(), "event": item.event}
            for item in task.flight_logs
        ],
        diff_text=task.diff_text,
        proof_text=task.proof_text,
    )
    return {"markdown": task.proof_text, "receipt": receipt}


@router.post("/{task_id}/repair", status_code=status.HTTP_202_ACCEPTED)
async def repair_task(task_id: str, session: AsyncSession = Depends(get_db)):
    task = await _task_or_404(session, task_id)
    if task.status != "blocked":
        raise HTTPException(status_code=409, detail="Only blocked tasks can be repaired")
    if task.repair_cycles >= get_settings().max_repair_cycles:
        raise HTTPException(status_code=409, detail="Maximum repair cycles reached")
    task.status = "repairing"
    task.repair_cycles += 1
    await session.commit()
    schedule_task(task_id)
    return {"task_id": task_id, "status": "repairing"}
