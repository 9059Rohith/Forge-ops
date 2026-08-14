from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'api.db'}")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.db import reset_engine_for_tests

    await reset_engine_for_tests()
    from app.main import app

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
            yield value


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_and_read_task(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.routers import tasks

    scheduled: list[str] = []
    monkeypatch.setattr(tasks, "schedule_task", lambda task_id: scheduled.append(task_id))
    response = await client.post(
        "/api/tasks",
        json={"repo_url": "demo", "branch": "main", "description": "Add safe retries"},
    )

    assert response.status_code == 202
    task_id = response.json()["task_id"]
    assert scheduled == [task_id]
    detail = await client.get(f"/api/tasks/{task_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "queued"
    assert detail.json()["project"]["repo_url"] == "demo"


@pytest.mark.asyncio
async def test_create_rejects_invalid_payload(client: AsyncClient):
    response = await client.post(
        "/api/tasks",
        json={"repo_url": "http://unsafe.example/repo", "branch": "main", "description": "x"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unknown_task_returns_404(client: AsyncClient):
    assert (await client.get("/api/tasks/not-a-task")).status_code == 404
