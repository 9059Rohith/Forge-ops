from __future__ import annotations

import json

from app.agents.prompts import SECURITY_AGENT_SYSTEM_PROMPT
from app.providers.base import JSONProvider
from app.schemas import ReviewResult


async def run_security_review(provider: JSONProvider, diff: str, changed_files: list[str]) -> dict:
    raw = await provider.complete_json(
        SECURITY_AGENT_SYSTEM_PROMPT,
        f"CHANGED FILES:\n{json.dumps(changed_files)}\n\nUNIFIED DIFF:\n{diff[:100_000]}",
    )
    return ReviewResult.model_validate(raw).model_dump()
