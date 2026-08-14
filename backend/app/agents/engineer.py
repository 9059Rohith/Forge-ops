from __future__ import annotations

import json
from pathlib import Path

from app.agents.prompts import ENGINEER_SYSTEM_PROMPT
from app.core.repository import build_repository_context
from app.providers.base import JSONProvider
from app.schemas import EngineerResult


async def run_engineer(provider: JSONProvider, root: Path, description: str) -> dict[str, object]:
    context = build_repository_context(root)
    raw = await provider.complete_json(
        ENGINEER_SYSTEM_PROMPT,
        f"TASK:\n{description}\n\nREPOSITORY CONTENTS:\n{context}",
    )
    return json.loads(EngineerResult.model_validate(raw).model_dump_json())
