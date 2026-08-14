from __future__ import annotations

from app.agents.prompts import ADVERSARIAL_AGENT_SYSTEM_PROMPT
from app.providers.base import JSONProvider
from app.schemas import ReviewResult


async def run_adversarial_review(provider: JSONProvider, task: str, diff: str, tests: str) -> dict:
    raw = await provider.complete_json(
        ADVERSARIAL_AGENT_SYSTEM_PROMPT,
        f"TASK:\n{task}\n\nTEST RESULTS:\n{tests[-20_000:]}\n\nUNIFIED DIFF:\n{diff[:100_000]}",
    )
    return ReviewResult.model_validate(raw).model_dump()
