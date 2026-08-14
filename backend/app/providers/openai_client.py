from __future__ import annotations

from app.providers.base import JSONProvider


def create_openai_provider(api_key: str, model: str, timeout_seconds: float) -> JSONProvider:
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise RuntimeError("OpenAI provider is not installed") from exc

    client = AsyncOpenAI(api_key=api_key)

    async def completion(system_prompt: str, user_prompt: str) -> str:
        response = await client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or "{}"

    return JSONProvider(completion, timeout_seconds)
