import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db import get_session_factory, init_db, reset_engine_for_tests
from app.models import Project, Task
from billing.entitlement_service import EntitlementService
from billing.models import RepairCredit, RepairUsage, User


@pytest.fixture
async def billing_session():
    from app.config import get_settings

    get_settings.cache_clear()
    await reset_engine_for_tests()
    await init_db()
    async with get_session_factory()() as session:
        yield session


async def _seed(session, credits: int = 1):
    now = datetime.now(UTC)
    user = User(github_username="demo")
    project = Project(repo_url="demo", branch="main")
    session.add_all([user, project])
    await session.flush()
    task = Task(project_id=project.id, user_id=user.id, description="repair checkout")
    credit = RepairCredit(
        user_id=user.id,
        credits_remaining=credits,
        credits_used=0,
        period_start=now,
        period_end=now + timedelta(days=30),
    )
    session.add_all([task, credit])
    await session.commit()
    return user, task, credit


@pytest.mark.asyncio
async def test_reservation_consumes_exactly_one_credit_per_job(billing_session):
    user, task, credit = await _seed(billing_session, credits=2)
    service = EntitlementService(billing_session)

    first = await service.reserve_for_job(user.id, task.id)
    second = await service.reserve_for_job(user.id, task.id)
    await billing_session.refresh(credit)

    assert first.has_credit is True
    assert second.has_credit is True
    assert credit.credits_remaining == 1
    assert credit.credits_used == 1
    usages = (await billing_session.scalars(select(RepairUsage))).all()
    assert len(usages) == 1


@pytest.mark.asyncio
async def test_reservation_fails_without_available_credit(billing_session):
    user, task, _ = await _seed(billing_session, credits=0)

    result = await EntitlementService(billing_session).reserve_for_job(user.id, task.id)

    assert result.has_credit is False
    assert result.credits_remaining == 0


@pytest.mark.asyncio
async def test_refund_only_applies_to_pre_repair_system_failure(billing_session):
    user, task, credit = await _seed(billing_session)
    service = EntitlementService(billing_session)
    await service.reserve_for_job(user.id, task.id)

    await service.record_repair_outcome(task.id, "pre_repair_failure")
    await billing_session.refresh(credit)
    usage = await billing_session.scalar(select(RepairUsage).where(RepairUsage.repair_job_id == task.id))

    assert credit.credits_remaining == 1
    assert credit.credits_used == 0
    assert usage is not None and usage.status == "refunded"


@pytest.mark.asyncio
async def test_cycle_failure_consumes_credit(billing_session):
    user, task, credit = await _seed(billing_session)
    service = EntitlementService(billing_session)
    await service.reserve_for_job(user.id, task.id)

    await service.record_repair_outcome(task.id, "cycle_failed")
    await billing_session.refresh(credit)
    usage = await billing_session.scalar(select(RepairUsage).where(RepairUsage.repair_job_id == task.id))

    assert credit.credits_remaining == 0
    assert credit.credits_used == 1
    assert usage is not None and usage.status == "consumed"


@pytest.mark.asyncio
async def test_concurrent_reservations_cannot_double_spend(billing_session):
    user, first_task, credit = await _seed(billing_session)
    second_task = Task(
        project_id=first_task.project_id,
        user_id=user.id,
        description="second repair",
    )
    billing_session.add(second_task)
    await billing_session.commit()
    factory = get_session_factory()

    async def reserve(task_id: str):
        async with factory() as session:
            return await EntitlementService(session).reserve_for_job(user.id, task_id)

    results = await asyncio.gather(reserve(first_task.id), reserve(second_task.id))
    billing_session.expire_all()
    await billing_session.refresh(credit)
    usages = (await billing_session.scalars(select(RepairUsage))).all()

    assert sum(result.has_credit for result in results) == 1
    assert credit.credits_remaining == 0
    assert len(usages) == 1
