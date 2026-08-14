from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_demo_pipeline_blocks_repairs_and_verifies(
    tmp_path: Path, demo_repo_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'flow.db'}")
    monkeypatch.setenv("DEMO_REPO_PATH", str(demo_repo_path))
    monkeypatch.setenv("WORK_ROOT", str(tmp_path / "work"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.core.orchestrator import run_task
    from app.db import init_db, reset_engine_for_tests, session_scope
    from app.models import Project, Task

    await reset_engine_for_tests()
    await init_db()
    async with session_scope() as session:
        project = Project(repo_url="demo", branch="main")
        session.add(project)
        await session.flush()
        task = Task(
            project_id=project.id, description="Add retry handling with exponential backoff"
        )
        session.add(task)
        await session.commit()
        task_id = task.id

    await run_task(task_id)

    async with session_scope() as session:
        task = await session.get(Task, task_id)
        await session.refresh(task, ["flight_logs", "evaluations"])
        assert task.status == "verified"
        assert task.repair_cycles == 1
        assert task.tests_passed == task.tests_total
        assert task.tests_total >= 3
        assert "ForgeGuard Verified" in task.proof_text
        events = [log.event for log in task.flight_logs]
        assert any("Patch blocked" in event for event in events)
        assert any("Repair cycle 1" in event for event in events)
        assert events[-1] == "PR verified"
