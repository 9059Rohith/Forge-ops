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
    if "files" not in raw and raw and all(
        isinstance(path, str) and isinstance(content, str) for path, content in raw.items()
    ):
        raw = {
            "plan": "Apply the scoped reviewer-requested repair.",
            "constraints_identified": [],
            "files": [{"path": path, "content": content} for path, content in raw.items()],
        }
    return json.loads(EngineerResult.model_validate(raw).model_dump_json())
