from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import Project, Task
from app.routers.tasks import schedule_task
from billing.service import ensure_demo_user

router = APIRouter(tags=["webhooks"])
_requests: dict[str, deque[float]] = defaultdict(deque)


def _rate_limit(request: Request) -> None:
    source = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = _requests[source]
    while recent and recent[0] < now - 60:
        recent.popleft()
    if len(recent) >= 60:
        raise HTTPException(status_code=429, detail="Webhook rate limit exceeded")
    recent.append(now)


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(request: Request, session: AsyncSession = Depends(get_db)):
    _rate_limit(request)
    raw = await request.body()
    if len(raw) > 1_000_000:
        raise HTTPException(status_code=413, detail="Webhook payload too large")
    settings = get_settings()
    if not settings.github_webhook_secret:
        raise HTTPException(status_code=503, detail="GITHUB_WEBHOOK_SECRET is not configured")
    supplied = request.headers.get("x-hub-signature-256", "")
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(), raw, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event = request.headers.get("x-github-event", "")
    if event == "ping":
        return {"received": True, "event": "ping"}
    if event != "push":
        return {"received": True, "event": event, "ignored": True}

    repository = payload.get("repository")
    if not isinstance(repository, dict):
        raise HTTPException(status_code=422, detail="Missing repository payload")
    full_name = str(repository.get("full_name", ""))
    installation = payload.get("installation")
    installation_id = (
        int(installation["id"])
        if isinstance(installation, dict) and str(installation.get("id", "")).isdigit()
        else None
    )
    if settings.allowed_repos and full_name not in settings.allowed_repos:
        raise HTTPException(status_code=403, detail="Repository is not allowlisted")
    repo_url = str(repository.get("clone_url", ""))
    ref = str(payload.get("ref", ""))
    if not repo_url.startswith("https://github.com/") or not ref.startswith("refs/heads/"):
        raise HTTPException(status_code=422, detail="Unsafe repository or branch payload")
    branch = ref.removeprefix("refs/heads/")
    commit = payload.get("head_commit") if isinstance(payload.get("head_commit"), dict) else {}
    description = str(commit.get("message") or "Review and repair the pushed commit")[:10_000]

    project = await session.scalar(
        select(Project).where(Project.repo_url == repo_url, Project.branch == branch)
    )
    if project is None:
        project = Project(
            repo_url=repo_url,
            repo_full_name=full_name,
            github_installation_id=installation_id,
            branch=branch,
        )
        session.add(project)
        await session.flush()
    else:
        project.repo_full_name = full_name
        if installation_id is not None:
            project.github_installation_id = installation_id
    user = await ensure_demo_user(session)
    task = Task(project_id=project.id, user_id=user.id, description=description)
    session.add(task)
    await session.commit()
    schedule_task(task.id)
    return {"received": True, "task_id": task.id}
