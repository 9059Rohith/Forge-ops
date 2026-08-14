import pytest

from app.providers.base import JSONProvider, extract_json


def test_extract_json_accepts_plain_or_fenced_payload():
    assert extract_json('{"score": 91}') == {"score": 91}
    assert extract_json('```json\n{"score": 92}\n```') == {"score": 92}


@pytest.mark.asyncio
async def test_provider_retries_once_after_malformed_json():
    responses = iter(["not-json", '{"score": 97}'])

    async def completion(_: str, __: str) -> str:
        return next(responses)

    provider = JSONProvider(completion=completion, timeout_seconds=1)

    assert await provider.complete_json("system", "user") == {"score": 97}


@pytest.mark.asyncio
async def test_provider_stops_after_two_invalid_responses():
    async def completion(_: str, __: str) -> str:
        return "bad"

    provider = JSONProvider(completion=completion, timeout_seconds=1)

    with pytest.raises(ValueError, match="valid JSON"):
        await provider.complete_json("system", "user")
