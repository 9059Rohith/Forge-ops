import hashlib
import hmac
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


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


def _push(repo: str = "acme/widget") -> bytes:
    return json.dumps(
        {
            "ref": "refs/heads/main",
            "after": "a" * 40,
            "repository": {
                "full_name": repo,
                "clone_url": f"https://github.com/{repo}.git",
            },
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
