import json
from pathlib import Path
from types import SimpleNamespace

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
async def test_submission_reuses_project_when_concurrent_requests_created_duplicates(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.db import session_scope
    from app.models import Project
    from app.routers import tasks

    monkeypatch.setattr(tasks, "schedule_task", lambda _task_id: None)
    async with session_scope() as session:
        session.add_all([
            Project(repo_url="demo", branch="main"),
            Project(repo_url="demo", branch="main"),
        ])
        await session.commit()

    response = await client.post(
        "/api/tasks",
        json={"repo_url": "demo", "branch": "main", "description": "Add safe retries"},
    )
    assert response.status_code == 202
    detail = await client.get(f"/api/tasks/{response.json()['task_id']}")
    assert detail.json()["project"]["repo_url"] == "demo"


@pytest.mark.asyncio
async def test_real_repository_never_gets_a_demo_billing_owner(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from app.routers import tasks

    monkeypatch.setattr(tasks, "schedule_task", lambda _task_id: None)
    repository = tmp_path / "real-repository"
    repository.mkdir()
    response = await client.post(
        "/api/tasks",
        json={
            "repo_url": str(repository),
            "branch": "main",
            "description": "Add bounded retries",
        },
    )

    assert response.status_code == 202
    detail = await client.get(f"/api/tasks/{response.json()['task_id']}")
    assert detail.json()["user_id"] is None


@pytest.mark.asyncio
async def test_production_rejects_unsigned_manual_task_creation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.routers import tasks

    monkeypatch.setattr(
        tasks,
        "get_settings",
        lambda: SimpleNamespace(
            environment="production", demo_mode=False, allowed_repos=["acme/widget"]
        ),
    )
    monkeypatch.setattr(tasks, "schedule_task", lambda _task_id: None)

    response = await client.post(
        "/api/tasks",
        json={
            "repo_url": "https://github.com/acme/widget",
            "branch": "main",
            "description": "Add bounded retries",
        },
    )

    assert response.status_code == 403
    assert "signed GitHub webhook" in response.json()["detail"]


@pytest.mark.asyncio
async def test_live_mode_rejects_the_bundled_demo_repository(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.routers import tasks

    monkeypatch.setattr(
        tasks,
        "get_settings",
        lambda: SimpleNamespace(environment="development", demo_mode=False, allowed_repos=[]),
    )
    monkeypatch.setattr(tasks, "schedule_task", lambda _task_id: None)

    response = await client.post(
        "/api/tasks",
        json={"repo_url": "demo", "branch": "main", "description": "Add bounded retries"},
    )

    assert response.status_code == 422
    assert "DEMO_MODE=true" in response.json()["detail"]


@pytest.mark.asyncio
async def test_github_task_persists_repository_full_name(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.routers import tasks

    monkeypatch.setattr(tasks, "schedule_task", lambda _task_id: None)
    response = await client.post(
        "/api/tasks",
        json={
            "repo_url": "https://github.com/acme/widget.git",
            "branch": "main",
            "description": "Add bounded retries",
        },
    )

    assert response.status_code == 202
    detail = await client.get(f"/api/tasks/{response.json()['task_id']}")
    assert detail.json()["project"]["repo_full_name"] == "acme/widget"


@pytest.mark.asyncio
async def test_create_rejects_invalid_payload(client: AsyncClient):
    response = await client.post(
        "/api/tasks",
        json={"repo_url": "http://unsafe.example/repo", "branch": "main", "description": "x"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_caller_supplied_billing_owner(client: AsyncClient):
    response = await client.post(
        "/api/tasks",
        json={
            "repo_url": "demo",
            "branch": "main",
            "description": "Add bounded retries",
            "user_id": "someone-elses-user-id",
        },
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
async def test_security_audit_receipt_is_not_mislabeled_as_blocked(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.routers import tasks

    monkeypatch.setattr(tasks, "schedule_task", lambda _task_id: None)
    created = await client.post(
        "/api/tasks",
        json={
            "repo_url": "demo",
            "branch": "main",
            "description": "Audit security vulnerabilities and document recommended fixes",
        },
    )
    task_id = created.json()["task_id"]

    from app.db import session_scope
    from app.models import Task

    async with session_scope() as session:
        task = await session.get(Task, task_id)
        assert task is not None
        task.status = "audit_complete"
        task.risk_level = "HIGH"
        task.confidence_score = 94
        task.proof_text = "## ForgeGuard Security Audit Complete\n"
        await session.commit()

    response = await client.get(f"/api/tasks/{task_id}/proof")

    assert response.status_code == 200
    assert response.json()["receipt"]["decision"] == "AUDIT_COMPLETE"


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
