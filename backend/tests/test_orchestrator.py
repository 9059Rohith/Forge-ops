from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        (
            "Test this repository to identify security vulnerabilities, authentication issues, API risks, and dependency vulnerabilities. Document severity and recommended fixes.",
            "security_audit",
        ),
        ("Add authorization checks to the admin API", "change"),
        ("Fix the exposed secret in settings.py", "change"),
        ("Audit security vulnerabilities. Do not change any files.", "security_audit"),
        ("Perform a read-only security audit and recommend a fix.", "security_audit"),
        ("Review security and fix the authorization bypass", "change"),
    ],
)
def test_task_intent_separates_read_only_security_audits_from_changes(
    description: str, expected: str
):
    from app.core.orchestrator import classify_task

    assert classify_task(description) == expected


def test_real_repository_never_selects_demo_agents(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.core.orchestrator import is_explicit_demo

    assert is_explicit_demo("https://github.com/acme/checkout") is False
    assert is_explicit_demo("demo") is True


def test_ownerless_local_job_has_an_explicit_nonbilling_repair_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("ENVIRONMENT", "development")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.core.orchestrator import ownerless_local_repair_allowed
    from app.models import Project, Task

    local_task = Task(
        project=Project(repo_url=str(tmp_path / "repository"), branch="main"),
        description="Add bounded retries",
    )
    github_task = Task(
        project=Project(repo_url="https://github.com/acme/widget", branch="main"),
        description="Add bounded retries",
    )

    assert ownerless_local_repair_allowed(local_task) is True
    assert ownerless_local_repair_allowed(github_task) is False


@pytest.mark.asyncio
async def test_ownerless_local_pipeline_repairs_without_billing_owner(
    tmp_path: Path, demo_repo_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'local-flow.db'}")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("WORK_ROOT", str(tmp_path / "work"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.agents.demo import (
        demo_adversarial_review,
        demo_engineer,
        demo_repair,
        demo_scope_review,
        demo_security_review,
    )
    from app.core import orchestrator
    from app.db import init_db, reset_engine_for_tests, session_scope
    from app.models import Project, Task

    async def engineer(task: Task, worktree):
        return await demo_engineer(worktree.path, task.description)

    async def repair(task: Task, worktree, diff: str, findings: str):
        return await demo_repair(worktree.path, findings)

    async def review(task: Task, diff: str, changed_files: list[str], test_output: str):
        return {
            "security": await demo_security_review(diff, changed_files),
            "scope": await demo_scope_review(task.description, changed_files, diff),
            "adversarial": await demo_adversarial_review(task.description, diff, test_output),
        }

    monkeypatch.setattr(orchestrator, "_engineer", engineer)
    monkeypatch.setattr(orchestrator, "_repair", repair)
    monkeypatch.setattr(orchestrator, "_review", review)
    await reset_engine_for_tests()
    await init_db()
    async with session_scope() as session:
        project = Project(repo_url=str(demo_repo_path), branch="main")
        session.add(project)
        await session.flush()
        task = Task(project_id=project.id, description="Add bounded retries")
        session.add(task)
        await session.commit()
        task_id = task.id

    await orchestrator.run_task(task_id)

    async with session_scope() as session:
        task = await session.get(Task, task_id)
        await session.refresh(task, ["flight_logs"])
        assert task.status == "verified"
        assert task.user_id is None
        assert task.repair_cycles == 1
        assert any(
            event.event == "Local operator authorized repair (billing disabled)"
            for event in task.flight_logs
        )


@pytest.mark.asyncio
async def test_security_audit_completes_without_patch_or_repair_authorization(
    tmp_path: Path, demo_repo_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'audit-flow.db'}")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("WORK_ROOT", str(tmp_path / "work"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.core import orchestrator
    from app.db import init_db, reset_engine_for_tests, session_scope
    from app.models import Project, Task

    async def reject_engineer(*_args, **_kwargs):
        raise AssertionError("a read-only audit must not invoke the Engineer Agent")

    async def audit_repository(_task: Task, _worktree):
        return {
            "security": {
                "score": 92,
                "severity": "high",
                "finding": "One verified high-severity secret exposure.",
                "evidence": {
                    "findings": [
                        {
                            "title": "Hardcoded credential",
                            "category": "secrets",
                            "severity": "high",
                            "confidence": 96,
                            "location": "backend/settings.py:12",
                            "evidence": "Credential-shaped value assigned in source (redacted).",
                            "recommendation": "Rotate it and load the replacement from a secret store.",
                        }
                    ],
                    "coverage": [
                        "secrets",
                        "authentication",
                        "authorization",
                        "api",
                        "dependencies",
                    ],
                },
            },
            "scope": {
                "score": 100,
                "severity": "none",
                "finding": "All requested security categories were reviewed.",
                "evidence": {"missing_categories": []},
            },
            "adversarial": {
                "score": 94,
                "severity": "none",
                "finding": "The high-severity finding is supported by repository evidence.",
                "evidence": {"verified_findings": ["Hardcoded credential"]},
            },
        }

    monkeypatch.setattr(orchestrator, "_engineer", reject_engineer)
    monkeypatch.setattr(orchestrator, "_audit_repository", audit_repository, raising=False)
    await reset_engine_for_tests()
    await init_db()
    async with session_scope() as session:
        project = Project(repo_url=str(demo_repo_path), branch="main")
        session.add(project)
        await session.flush()
        task = Task(
            project_id=project.id,
            description=(
                "Test this repository to identify security vulnerabilities, authentication and "
                "authorization issues, API risks, and dependency vulnerabilities. Document "
                "severity and recommended fixes."
            ),
        )
        session.add(task)
        await session.commit()
        task_id = task.id

    await orchestrator.run_task(task_id)

    async with session_scope() as session:
        task = await session.get(Task, task_id)
        await session.refresh(task, ["flight_logs", "evaluations"])
        assert task.status == "audit_complete"
        assert task.changed_files == []
        assert task.diff_text == ""
        assert task.error_message is None
        assert task.repair_cycles == 0
        assert task.risk_level == "HIGH"
        assert "Security Audit Complete" in task.proof_text
        assert "Hardcoded credential" in task.proof_text
        assert {item.category for item in task.evaluations} == {
            "security",
            "scope",
            "adversarial",
        }
        events = [log.event for log in task.flight_logs]
        assert "Read-only security audit selected" in events
        assert events[-1] == "Security audit completed with 1 finding"
        assert not any("authorization" in event.casefold() for event in events)


@pytest.mark.asyncio
async def test_demo_pipeline_blocks_repairs_and_verifies(
    tmp_path: Path, demo_repo_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'flow.db'}")
    monkeypatch.setenv("DEMO_REPO_PATH", str(demo_repo_path))
    monkeypatch.setenv("WORK_ROOT", str(tmp_path / "work"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.core import orchestrator
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

    terminal_commits: list[str] = []
    original_finalize_task = orchestrator._finalize_task

    async def finalize_task_spy(observed_task_id: str, event: str, **values: object) -> None:
        terminal_commits.append(f"{values.get('status')}:{event}")
        await original_finalize_task(observed_task_id, event, **values)

    monkeypatch.setattr(orchestrator, "_finalize_task", finalize_task_spy)
    await orchestrator.run_task(task_id)

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
        assert terminal_commits == ["verified:PR verified"]


@pytest.mark.asyncio
async def test_repair_ceiling_requires_manual_review(
    tmp_path: Path, demo_repo_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'ceiling.db'}")
    monkeypatch.setenv("DEMO_REPO_PATH", str(demo_repo_path))
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "work"))
    monkeypatch.setenv("MAX_REPAIR_CYCLES", "0")
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
        task = Task(project_id=project.id, description="Add retry handling")
        session.add(task)
        await session.commit()
        task_id = task.id

    await run_task(task_id)

    async with session_scope() as session:
        task = await session.get(Task, task_id)
        assert task is not None
        assert task.status == "manual_review_required"
