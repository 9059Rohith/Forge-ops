from __future__ import annotations

from app.db import session_scope
from app.models import FlightLog


async def record_event(task_id: str, event: str) -> None:
    safe_event = event.replace("\x00", "")[:2_000]
    async with session_scope() as session:
        session.add(FlightLog(task_id=task_id, event=safe_event))
        await session.commit()
