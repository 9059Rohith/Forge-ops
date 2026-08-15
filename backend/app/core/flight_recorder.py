from __future__ import annotations

from app.db import session_scope
from app.models import AuditLog, FlightLog


async def record_event(task_id: str, event: str, actor: str = "system") -> None:
    safe_event = event.replace("\x00", "")[:2_000]
    async with session_scope() as session:
        session.add_all(
            [
                FlightLog(task_id=task_id, event=safe_event),
                AuditLog(
                    job_id=task_id,
                    actor=actor,
                    action=safe_event.split(":", 1)[0][:120],
                    detail={"event": safe_event},
                ),
            ]
        )
        await session.commit()
