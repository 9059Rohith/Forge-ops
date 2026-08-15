from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.agents.adversarial_agent import run_adversarial_review
from app.agents.demo import (
    demo_adversarial_review,
    demo_engineer,
    demo_repair,
    demo_scope_review,
    demo_security_review,
)
from app.agents.engineer import run_engineer
from app.agents.repair import run_repair
from app.agents.scope_agent import run_scope_review
from app.agents.security_agent import run_security_review
from app.config import get_settings
from app.core.deterministic_verifier import verify_repository
from app.core.flight_recorder import record_event
from app.core.proof_package import build_proof_package
from app.core.repository import apply_file_changes
from app.core.risk_engine import compute_risk
from app.core.worktree import Worktree, WorktreeManager
from app.db import session_scope
from app.integrations.github_app import create_pull_request, get_installation_token
from app.models import AgentRun, Evaluation, FlightLog, Task, utcnow
from app.providers.groq_client import create_groq_provider
from app.providers.openai_client import create_openai_provider
from billing.entitlement_service import EntitlementService
from billing.service import ensure_demo_user

logger = logging.getLogger(__name__)


async def _load_task(task_id: str) -> Task:
    async with session_scope() as session:
        result = await session.execute(
            select(Task).options(selectinload(Task.project)).where(Task.id == task_id)
        )
        task = result.scalar_one()
        return task


async def _update_task(task_id: str, **values: Any) -> None:
    async with session_scope() as session:
        task = await session.get(Task, task_id)
        if task is None:
            raise LookupError(f"task {task_id} not found")
        for key, value in values.items():
            setattr(task, key, value)
        task.updated_at = utcnow()
        await session.commit()


async def _finalize_task(task_id: str, event: str, **values: Any) -> None:
    """Commit the terminal task state and its final evidence event atomically."""
    async with session_scope() as session:
        task = await session.get(Task, task_id)
        if task is None:
            raise LookupError(f"task {task_id} not found")
        for key, value in values.items():
            setattr(task, key, value)
        task.updated_at = utcnow()
        session.add(FlightLog(task_id=task_id, event=event.replace("\x00", "")[:2_000]))
        await session.commit()


async def _start_agent(task_id: str, name: str) -> str:
    async with session_scope() as session:
        run = AgentRun(task_id=task_id, agent_name=name, status="running")
        session.add(run)
        await session.commit()
        return run.id


async def _finish_agent(run_id: str, output: dict[str, Any], status: str = "completed") -> None:
    async with session_scope() as session:
        run = await session.get(AgentRun, run_id)
        if run:
            run.status = status
            run.completed_at = datetime.now(UTC)
            run.output_json = json.dumps(output, ensure_ascii=False, default=str)
            await session.commit()


async def _execute_agent(
    task_id: str, name: str, call: Awaitable[dict[str, Any]]
) -> dict[str, Any]:
    run_id = await _start_agent(task_id, name)
    await record_event(task_id, f"{name.title()} Agent started")
    try:
        output = await call
        await _finish_agent(run_id, output)
        await record_event(task_id, f"{name.title()} Agent completed")
        return output
    except Exception as exc:
        await _finish_agent(run_id, {"error": type(exc).__name__}, "failed")
        await record_event(task_id, f"{name.title()} Agent failed")
        raise


def _providers():
    settings = get_settings()
    if not settings.openai_api_key or not settings.groq_api_key:
        raise RuntimeError("OPENAI_API_KEY and GROQ_API_KEY are required when DEMO_MODE=false")
    openai = create_openai_provider(
        settings.openai_api_key, settings.openai_model, settings.engineer_timeout_seconds
    )
    groq = create_groq_provider(
        settings.groq_api_key, settings.groq_model, settings.reviewer_timeout_seconds
    )
    return openai, groq


def _github_access_token(task: Task) -> str | None:
    settings = get_settings()
    if settings.github_token:
        return settings.github_token
    if (
        task.project.github_installation_id
        and settings.github_app_id
        and settings.github_private_key
    ):
        return get_installation_token(
            settings.github_app_id,
            settings.github_private_key,
            task.project.github_installation_id,
        )
    if settings.environment == "production" and task.project.repo_url.startswith(
        "https://github.com/"
    ):
        raise RuntimeError("GitHub App installation ID is required to publish the repair PR")
    return None


async def _engineer(task: Task, worktree: Worktree) -> dict[str, Any]:
    settings = get_settings()
    if settings.demo_mode or task.project.repo_url == "demo":
        return await _execute_agent(
            task.id, "engineer", demo_engineer(worktree.path, task.description)
        )
    openai, _ = _providers()
    return await _execute_agent(
        task.id, "engineer", run_engineer(openai, worktree.path, task.description)
    )


async def _repair(task: Task, worktree: Worktree, diff: str, findings: str) -> dict[str, Any]:
    settings = get_settings()
    if settings.demo_mode or task.project.repo_url == "demo":
        return await _execute_agent(task.id, "repair", demo_repair(worktree.path, findings))
    openai, _ = _providers()
    return await _execute_agent(
        task.id, "repair", run_repair(openai, worktree.path, task.description, diff, findings)
    )


async def _review(
    task: Task, diff: str, changed_files: list[str], test_output: str
) -> dict[str, dict[str, Any]]:
    settings = get_settings()
    if settings.demo_mode or task.project.repo_url == "demo":
        calls = {
            "security": demo_security_review(diff, changed_files),
            "scope": demo_scope_review(task.description, changed_files, diff),
            "adversarial": demo_adversarial_review(task.description, diff, test_output),
        }
    else:
        openai, groq = _providers()
        calls = {
            "security": run_security_review(groq, diff, changed_files),
            "scope": run_scope_review(groq, task.description, changed_files),
            "adversarial": run_adversarial_review(openai, task.description, diff, test_output),
        }

    async def named(name: str, call: Awaitable[dict[str, Any]]):
        return name, await _execute_agent(task.id, name, call)

    pending = [asyncio.create_task(named(name, call)) for name, call in calls.items()]
    results: dict[str, dict[str, Any]] = {}
    async with session_scope() as session:
        await session.execute(delete(Evaluation).where(Evaluation.task_id == task.id))
        await session.commit()
    for completed in asyncio.as_completed(pending):
        name, review = await completed
        results[name] = review
        async with session_scope() as session:
            session.add(
                Evaluation(
                    task_id=task.id,
                    category=name,
                    score=int(review["score"]),
                    severity=str(review["severity"]),
                    finding=str(review["finding"]),
                    evidence_json=json.dumps(review.get("evidence", {}), ensure_ascii=False),
                )
            )
            await session.commit()
        await record_event(
            task.id, f"{name.title()} review: {review['score']}% ({review['severity']})"
        )
    return results


async def run_task(task_id: str) -> None:
    settings = get_settings()
    manager: WorktreeManager | None = None
    worktree: Worktree | None = None
    github_token: str | None = None
    try:
        task = await _load_task(task_id)
        if task.user_id is None and (settings.demo_mode or task.project.repo_url == "demo"):
            async with session_scope() as session:
                demo_user = await ensure_demo_user(session)
            await _update_task(task_id, user_id=demo_user.id)
            task = await _load_task(task_id)
        await record_event(task_id, "Task received")
        await _update_task(task_id, status="planning", error_message=None)
        await record_event(task_id, "Repository reconnaissance complete")

        github_token = await asyncio.to_thread(_github_access_token, task)
        repair_branch = f"forgeguard/repair-{task_id}"
        await _update_task(task_id, repair_branch=repair_branch)
        manager = WorktreeManager(settings.work_root)
        worktree = await asyncio.to_thread(
            manager.create,
            task_id,
            task.project.repo_url,
            task.project.branch,
            settings.demo_repo_path,
            github_token,
        )
        await _update_task(task_id, worktree_path=str(worktree.path))
        await record_event(task_id, "Worktree created")
        await _update_task(task_id, status="engineering")

        result = await _engineer(task, worktree)
        files = result.get("files", [])
        if not files:
            raise RuntimeError("Engineer Agent produced no changes")
        changed = apply_file_changes(worktree.path, files)
        for path in changed:
            await record_event(task_id, f"Wrote {path}")
        changed_files, diff = await asyncio.to_thread(worktree.stage_and_diff)
        if not diff.strip():
            raise RuntimeError("Engineer Agent produced no changes")
        await _update_task(
            task_id,
            diff_text=diff,
            changed_files_json=json.dumps(changed_files),
            pending_plan=str(result.get("plan", ""))[:8_000] or None,
        )
        await record_event(task_id, f"Patch captured ({len(changed_files)} files)")

        while True:
            verification = await verify_repository(worktree.path, settings.command_timeout_seconds)
            await _update_task(
                task_id,
                tests_passed=verification.passed,
                tests_total=verification.total,
            )
            await record_event(
                task_id, f"Deterministic tests: {verification.passed}/{verification.total} passed"
            )
            await _update_task(task_id, status="reviewing")
            task = await _load_task(task_id)
            reviews = await _review(task, diff, changed_files, verification.output)
            risk = compute_risk(
                reviews["security"],
                reviews["scope"],
                reviews["adversarial"],
                verification.passed,
                verification.total,
            )
            await _update_task(
                task_id,
                confidence_score=risk["overall_confidence"],
                risk_level=risk["risk_level"],
            )
            await record_event(
                task_id,
                f"Risk Engine: {risk['risk_level']} ({risk['overall_confidence']}% confidence)",
            )

            task = await _load_task(task_id)
            if risk["decision"] == "VERIFIED":
                proof = build_proof_package(
                    description=task.description,
                    changed_files=changed_files,
                    tests_passed=verification.passed,
                    tests_total=verification.total,
                    evaluations=reviews,
                    confidence=float(risk["overall_confidence"]),
                    risk_level=str(risk["risk_level"]),
                    repair_cycles=task.repair_cycles,
                    decision="VERIFIED",
                )
                final_values: dict[str, Any] = {"status": "verified", "proof_text": proof}
                final_event = "PR verified"
                if github_token and task.project.repo_url.startswith("https://github.com/"):
                    repo_full_name = task.project.repo_full_name
                    if not repo_full_name:
                        raise RuntimeError("GitHub repository full_name is required to create a PR")
                    await asyncio.to_thread(
                        worktree.commit_and_push, repair_branch, github_token
                    )
                    published = await asyncio.to_thread(
                        create_pull_request,
                        token=github_token,
                        repo_full_name=repo_full_name,
                        base_branch=task.project.branch,
                        repair_branch=repair_branch,
                        title=f"ForgeGuard repair: {task.description[:120]}",
                        body=proof,
                    )
                    final_values.update(pr_url=published.url, pr_number=published.number)
                    final_event = f"PR created: {published.url}"
                await _finalize_task(task_id, final_event, **final_values)
                async with session_scope() as session:
                    await EntitlementService(session).record_repair_outcome(task_id, "completed")
                break

            await _update_task(task_id, status="blocked")
            await record_event(task_id, "Patch blocked by independent evidence")
            if task.repair_cycles >= settings.max_repair_cycles:
                proof = build_proof_package(
                    description=task.description,
                    changed_files=changed_files,
                    tests_passed=verification.passed,
                    tests_total=verification.total,
                    evaluations=reviews,
                    confidence=float(risk["overall_confidence"]),
                    risk_level=str(risk["risk_level"]),
                    repair_cycles=task.repair_cycles,
                    decision="BLOCKED",
                )
                await _finalize_task(
                    task_id,
                    "Max repair attempts reached — worktree preserved for inspection",
                    status="manual_review_required",
                    proof_text=proof,
                    error_message="Maximum repair attempts reached; human review is required.",
                )
                async with session_scope() as session:
                    await EntitlementService(session).record_repair_outcome(
                        task_id, "cycle_failed"
                    )
                break

            if not task.user_id:
                await _update_task(
                    task_id,
                    status="awaiting_authorization",
                    error_message="Repair is ready but this job has no billing owner.",
                )
                await record_event(task_id, "Repair awaiting authorization")
                break
            async with session_scope() as session:
                entitlement = await EntitlementService(session).reserve_for_job(
                    task.user_id, task_id
                )
            if not entitlement.has_credit:
                await _update_task(
                    task_id,
                    status="awaiting_authorization",
                    error_message="Repair plan ready — add a Repair Credit to continue.",
                )
                await record_event(task_id, "Repair awaiting authorization")
                break
            await record_event(
                task_id,
                f"Repair credit authorized ({entitlement.credits_remaining} remaining)",
            )

            cycle = task.repair_cycles + 1
            await _update_task(task_id, status="repairing", repair_cycles=cycle)
            await record_event(task_id, f"Repair cycle {cycle} started")
            findings = "\n".join(
                f"- {name}: {review['finding']}"
                for name, review in reviews.items()
                if str(review["severity"]).lower() in {"high", "critical"}
            )
            repair_result = await _repair(task, worktree, diff, findings)
            apply_file_changes(worktree.path, repair_result.get("files", []))
            changed_files, diff = await asyncio.to_thread(worktree.stage_and_diff)
            await _update_task(
                task_id,
                diff_text=diff,
                changed_files_json=json.dumps(changed_files),
            )
            await record_event(task_id, f"Repair cycle {cycle} completed")
    except Exception as exc:
        public_error = f"{type(exc).__name__}: {str(exc)[:500]}"
        try:
            failed_task = await _load_task(task_id)
            async with session_scope() as session:
                if failed_task.repair_cycles == 0:
                    await EntitlementService(session).record_repair_outcome(
                        task_id, "pre_repair_failure"
                    )
                else:
                    await EntitlementService(session).record_repair_outcome(
                        task_id, "system_failed"
                    )
            await _update_task(task_id, status="failed", error_message=public_error)
            await record_event(task_id, f"Task failed: {public_error}")
        except Exception:
            return
    finally:
        if manager and worktree and settings.workspace_retention_hours == 0:
            try:
                await asyncio.to_thread(manager.remove, worktree)
                await _update_task(task_id, worktree_path=None)
            except Exception:
                logger.warning("Unable to clean task worktree %s", task_id, exc_info=True)
