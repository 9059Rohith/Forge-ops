from __future__ import annotations

import json

from app.agents.prompts import SCOPE_AGENT_SYSTEM_PROMPT
from app.providers.base import JSONProvider
from app.schemas import ReviewResult


async def run_scope_review(provider: JSONProvider, task: str, changed_files: list[str]) -> dict:
    raw = await provider.complete_json(
        SCOPE_AGENT_SYSTEM_PROMPT,
        f"TASK:\n{task}\n\nCHANGED FILES:\n{json.dumps(changed_files)}",
    )
    return ReviewResult.model_validate(raw).model_dump()
