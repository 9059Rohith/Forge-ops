from __future__ import annotations

import json
from pathlib import Path

from app.agents.prompts import REPAIR_SYSTEM_PROMPT
from app.core.repository import build_repository_context
from app.providers.base import JSONProvider
from app.schemas import EngineerResult


async def run_repair(
    provider: JSONProvider, root: Path, task: str, diff: str, findings: str
) -> dict[str, object]:
    raw = await provider.complete_json(
        REPAIR_SYSTEM_PROMPT,
        f"TASK:\n{task}\n\nFINDINGS TO FIX:\n{findings}\n\nCURRENT DIFF:\n{diff[:80_000]}\n\nREPOSITORY:\n{build_repository_context(root)}",
    )
    return json.loads(EngineerResult.model_validate(raw).model_dump_json())
