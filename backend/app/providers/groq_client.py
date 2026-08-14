from __future__ import annotations

from app.providers.base import JSONProvider


def create_groq_provider(api_key: str, model: str, timeout_seconds: float) -> JSONProvider:
    try:
        from groq import AsyncGroq
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise RuntimeError("Groq provider is not installed") from exc

    client = AsyncGroq(api_key=api_key)

    async def completion(system_prompt: str, user_prompt: str) -> str:
        response = await client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or "{}"

    return JSONProvider(completion, timeout_seconds)
