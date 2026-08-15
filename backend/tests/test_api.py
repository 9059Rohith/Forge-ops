import json
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


@pytest.mark.asyncio
async def test_proof_endpoint_includes_a_sealed_terminal_receipt(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.routers import tasks

    monkeypatch.setattr(tasks, "schedule_task", lambda _task_id: None)
    created = await client.post(
        "/api/tasks",
        json={"repo_url": "demo", "branch": "main", "description": "Add safe retries"},
    )
    task_id = created.json()["task_id"]

    from app.db import session_scope
    from app.models import AgentRun, Evaluation, FlightLog, Task

    async with session_scope() as session:
        task = await session.get(Task, task_id)
        assert task is not None
        task.status = "verified"
        task.risk_level = "LOW"
        task.confidence_score = 95.5
        task.repair_cycles = 1
        task.tests_passed = 5
        task.tests_total = 5
        task.changed_files_json = json.dumps(["checkout.py"])
        task.diff_text = "diff --git a/checkout.py b/checkout.py\n"
        task.proof_text = "## ForgeGuard Verified\n"
        for category, score in (("security", 96), ("scope", 97), ("adversarial", 94)):
            session.add(
                Evaluation(
                    task_id=task_id,
                    category=category,
                    score=score,
                    severity="none",
                    finding=f"{category} approved",
                    evidence_json="{}",
                )
            )
        session.add(AgentRun(task_id=task_id, agent_name="engineer", status="completed"))
        session.add(FlightLog(task_id=task_id, event="Task received"))
        await session.commit()

    response = await client.get(f"/api/tasks/{task_id}/proof")

    assert response.status_code == 200
    body = response.json()
    assert body["markdown"] == "## ForgeGuard Verified\n"
    assert body["receipt"]["task"]["id"] == task_id
    assert body["receipt"]["decision"] == "VERIFIED"
    assert len(body["receipt"]["integrity"]["digest"]) == 64


@pytest.mark.asyncio
async def test_evidence_endpoint_returns_the_complete_persisted_chain(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.routers import tasks

    monkeypatch.setattr(tasks, "schedule_task", lambda _task_id: None)
    created = await client.post(
        "/api/tasks",
        json={"repo_url": "demo", "branch": "main", "description": "Add safe retries"},
    )
    task_id = created.json()["task_id"]

    response = await client.get(f"/api/jobs/{task_id}/evidence")

    assert response.status_code == 200
    body = response.json()
    assert body["job"]["id"] == task_id
    assert body["findings"] == []
    assert body["credit_usage"] is None
    assert "audit_log" in body
