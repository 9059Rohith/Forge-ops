from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

Completion = Callable[[str, str], Awaitable[str]]


def extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("provider response must be a JSON object")
    return parsed


@dataclass(slots=True)
class JSONProvider:
    completion: Completion
    timeout_seconds: float

    async def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for _ in range(2):
            try:
                raw = await asyncio.wait_for(
                    self.completion(system_prompt, user_prompt), timeout=self.timeout_seconds
                )
                return extract_json(raw)
            except (TimeoutError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
        raise ValueError("AI provider did not return valid JSON after one retry") from last_error
