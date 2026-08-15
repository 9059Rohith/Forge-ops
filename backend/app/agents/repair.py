from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from app.agents.prompts import REPAIR_SYSTEM_PROMPT
from app.core.repository import build_repository_context, resolve_safe_path
from app.providers.base import JSONProvider
from app.schemas import EngineerResult

_NON_FILE_RESPONSE_KEYS = {
    "detail",
    "error",
    "explanation",
    "message",
    "plan",
    "reason",
    "status",
    "warning",
}
_KNOWN_EXTENSIONLESS_FILES = {"dockerfile", "license", "makefile", "procfile", "readme"}


def _is_legacy_file_path(root: Path, candidate: str) -> bool:
    normalized = PurePosixPath(candidate.replace("\\", "/"))
    if not candidate.strip() or candidate.casefold() in _NON_FILE_RESPONSE_KEYS:
        return False
    if not (
        normalized.suffix
        or len(normalized.parts) > 1
        or normalized.name.casefold() in _KNOWN_EXTENSIONLESS_FILES
        or normalized.name.startswith(".")
    ):
        return False
    resolve_safe_path(root, candidate)
    return True


async def run_repair(
    provider: JSONProvider, root: Path, task: str, diff: str, findings: str
) -> dict[str, object]:
    raw = await provider.complete_json(
        REPAIR_SYSTEM_PROMPT,
        f"TASK:\n{task}\n\nFINDINGS TO FIX:\n{findings}\n\nCURRENT DIFF:\n{diff[:80_000]}\n\nREPOSITORY:\n{build_repository_context(root)}",
    )
    if "files" not in raw and raw and all(
        isinstance(path, str)
        and isinstance(content, str)
        and _is_legacy_file_path(root, path)
        for path, content in raw.items()
    ):
        raw = {
            "plan": "Apply the scoped reviewer-requested repair.",
            "constraints_identified": [],
            "files": [{"path": path, "content": content} for path, content in raw.items()],
        }
    return json.loads(EngineerResult.model_validate(raw).model_dump_json())
