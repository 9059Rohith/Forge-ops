import asyncio
import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest.fixture
async def billing_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'billing-api.db'}")
    monkeypatch.setenv("DODO_WEBHOOK_SECRET", "whsec_dGVzdC1zZWNyZXQ=")
    monkeypatch.setenv("DEMO_MODE", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.db import reset_engine_for_tests

    await reset_engine_for_tests()
    from app.main import app

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


def _signature(raw: bytes, webhook_id: str, timestamp: str) -> str:
    message = b".".join((webhook_id.encode(), timestamp.encode(), raw))
    digest = hmac.new(b"test-secret", message, hashlib.sha256).digest()
    return f"v1,{base64.b64encode(digest).decode()}"


@pytest.mark.asyncio
async def test_fresh_demo_has_free_repair_credits(billing_client: AsyncClient):
    response = await billing_client.get("/api/billing/status/demo")

    assert response.status_code == 200
    assert response.json()["plan"] == "free"
    assert response.json()["credits_remaining"] == 3


@pytest.mark.asyncio
async def test_live_mode_never_bootstraps_demo_billing_user(
    billing_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from billing import router

    monkeypatch.setattr(router, "get_settings", lambda: SimpleNamespace(demo_mode=False))
    response = await billing_client.get("/api/billing/status/demo")

    assert response.status_code == 404
    from app.db import session_scope
    from billing.models import User

    async with session_scope() as session:
        assert (await session.scalars(select(User))).all() == []


@pytest.mark.asyncio
async def test_concurrent_demo_status_bootstrap_is_idempotent(billing_client: AsyncClient):
    from app.db import session_scope
    from billing.models import RepairCredit, User

    responses = await asyncio.gather(
        billing_client.get("/api/billing/status/demo"),
        billing_client.get("/api/billing/status/demo"),
    )

    assert [response.status_code for response in responses] == [200, 200]
    async with session_scope() as session:
        assert len((await session.scalars(select(User))).all()) == 1
        assert len((await session.scalars(select(RepairCredit))).all()) == 1


@pytest.mark.asyncio
async def test_webhook_rejects_tampered_payload(billing_client: AsyncClient):
    timestamp = str(int(time.time()))
    response = await billing_client.post(
        "/api/billing/webhook",
        content=b'{"type":"subscription.active"}',
        headers={
            "Content-Type": "application/json",
            "webhook-id": "evt_1",
            "webhook-timestamp": timestamp,
            "webhook-signature": "v1,invalid",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_subscription_webhook_upserts_period_credit(billing_client: AsyncClient):
    from app.db import session_scope
    from billing.models import RepairCredit, Subscription, User

    async with session_scope() as session:
        user = User(github_username="octocat")
        session.add(user)
        await session.commit()
        user_id = user.id

    payload = {
        "type": "subscription.active",
        "data": {
            "subscription_id": "sub_123",
            "status": "active",
            "current_period_start": "2026-08-01T00:00:00Z",
            "current_period_end": "2026-09-01T00:00:00Z",
            "metadata": {"user_id": user_id, "plan": "pro"},
        },
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    response = await billing_client.post(
        "/api/billing/webhook",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "webhook-id": "evt_2",
            "webhook-timestamp": timestamp,
            "webhook-signature": _signature(raw, "evt_2", timestamp),
        },
    )

    assert response.status_code == 200
    async with session_scope() as session:
        subscription = await session.scalar(select(Subscription))
        credit = await session.scalar(select(RepairCredit))
        assert subscription is not None and subscription.plan == "pro"
        assert credit is not None and credit.credits_remaining == 150


async def _pending_job(credits: int):
    from app.db import session_scope
    from app.models import Project, Task
    from billing.models import RepairCredit, User

    now = datetime.now(UTC)
    async with session_scope() as session:
        user = User(github_username=f"user-{credits}")
        project = Project(repo_url="demo", branch="main")
        session.add_all([user, project])
        await session.flush()
        task = Task(
            project_id=project.id,
            user_id=user.id,
            description="repair",
            status="awaiting_authorization",
            pending_plan="restore authorization",
        )
        session.add_all(
            [
                task,
                RepairCredit(
                    user_id=user.id,
                    credits_remaining=credits,
                    credits_used=0,
                    period_start=now,
                    period_end=now + timedelta(days=30),
                ),
            ]
        )
        await session.commit()
        return task.id


@pytest.mark.asyncio
async def test_authorize_returns_402_without_credit(billing_client: AsyncClient):
    task_id = await _pending_job(0)

    response = await billing_client.post(f"/api/repairs/{task_id}/authorize")

    assert response.status_code == 402


@pytest.mark.asyncio
async def test_authorize_resumes_pending_job(billing_client: AsyncClient, monkeypatch):
    from app.routers import repairs

    scheduled: list[str] = []
    monkeypatch.setattr(repairs, "schedule_task", lambda task_id: scheduled.append(task_id))
    task_id = await _pending_job(1)

    response = await billing_client.post(f"/api/repairs/{task_id}/authorize")

    assert response.status_code == 200
    assert response.json()["credits_remaining"] == 0
    assert scheduled == [task_id]
