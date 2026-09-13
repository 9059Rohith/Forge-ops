import hashlib
import hmac
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest.fixture
async def webhook_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'webhook.db'}")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "github-secret")
    monkeypatch.setenv("ALLOWED_REPOS", "acme/widget")
    monkeypatch.setenv("DEMO_MODE", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.db import reset_engine_for_tests

    await reset_engine_for_tests()
    from app.main import app

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


def _push(
    repo: str = "acme/widget",
    sender_login: str = "octocat",
    sender_id: int = 583231,
) -> bytes:
    return json.dumps(
        {
            "ref": "refs/heads/main",
            "after": "a" * 40,
            "repository": {
                "full_name": repo,
                "clone_url": f"https://github.com/{repo}.git",
            },
            "sender": {"id": sender_id, "login": sender_login},
            "head_commit": {"message": "fix checkout"},
        },
        separators=(",", ":"),
    ).encode()


@pytest.mark.asyncio
async def test_github_webhook_rejects_invalid_signature(webhook_client: AsyncClient):
    response = await webhook_client.post(
        "/api/webhooks/github",
        content=_push(),
        headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": "sha256=bad"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_github_webhook_enforces_repository_allowlist(webhook_client: AsyncClient):
    raw = _push("other/repo")
    signature = hmac.new(b"github-secret", raw, hashlib.sha256).hexdigest()
    response = await webhook_client.post(
        "/api/webhooks/github",
        content=raw,
        headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": f"sha256={signature}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_github_push_creates_a_repair_job(webhook_client: AsyncClient, monkeypatch):
    from app.routers import webhooks

    scheduled: list[str] = []
    monkeypatch.setattr(webhooks, "schedule_task", lambda task_id: scheduled.append(task_id))
    raw = _push()
    signature = hmac.new(b"github-secret", raw, hashlib.sha256).hexdigest()
    response = await webhook_client.post(
        "/api/webhooks/github",
        content=raw,
        headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": f"sha256={signature}"},
    )

    assert response.status_code == 202
    assert scheduled == [response.json()["task_id"]]

    from app.db import session_scope
    from app.models import Task
    from billing.models import RepairCredit, User

    async with session_scope() as session:
        task = await session.get(Task, response.json()["task_id"])
        users = (await session.scalars(select(User))).all()
        credits = (await session.scalars(select(RepairCredit))).all()
        assert task is not None and task.user_id == users[0].id
        assert [user.github_username for user in users] == ["octocat"]
        assert users[0].github_user_id == 583231
        assert len(credits) == 1 and credits[0].credits_remaining == 3


@pytest.mark.asyncio
async def test_github_sender_rename_keeps_one_billing_identity(
    webhook_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.routers import webhooks

    monkeypatch.setattr(webhooks, "schedule_task", lambda _task_id: None)
    for login in ("octocat", "renamed-octocat"):
        raw = _push(sender_login=login, sender_id=583231)
        signature = hmac.new(b"github-secret", raw, hashlib.sha256).hexdigest()
        response = await webhook_client.post(
            "/api/webhooks/github",
            content=raw,
            headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": f"sha256={signature}"},
        )
        assert response.status_code == 202

    from app.db import session_scope
    from billing.models import RepairCredit, User

    async with session_scope() as session:
        users = (await session.scalars(select(User))).all()
        credits = (await session.scalars(select(RepairCredit))).all()
        assert len(users) == 1
        assert users[0].github_username == "renamed-octocat"
        assert users[0].github_user_id == 583231
        assert len(credits) == 1


@pytest.mark.asyncio
async def test_github_webhook_does_not_give_reassigned_username_legacy_billing_identity(
    webhook_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.db import session_scope
    from app.routers import webhooks
    from billing.models import User

    async with session_scope() as session:
        session.add(User(github_username="octocat"))
        await session.commit()

    monkeypatch.setattr(webhooks, "schedule_task", lambda _task_id: None)
    raw = _push(sender_login="octocat", sender_id=583231)
    signature = hmac.new(b"github-secret", raw, hashlib.sha256).hexdigest()
    response = await webhook_client.post(
        "/api/webhooks/github",
        content=raw,
        headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": f"sha256={signature}"},
    )

    assert response.status_code == 409
    assert "verified identity backfill" in response.json()["detail"]
    async with session_scope() as session:
        from app.models import Task

        users = (await session.scalars(select(User))).all()
        tasks = (await session.scalars(select(Task))).all()
        assert len(users) == 1
        assert users[0].github_user_id is None
        assert tasks == []
