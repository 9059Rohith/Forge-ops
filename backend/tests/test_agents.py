import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agents.demo import demo_engineer, demo_repair, demo_security_review
from app.agents.repair import run_repair
from app.providers.base import JSONProvider


@pytest.mark.asyncio
async def test_demo_first_pass_contains_planted_authorization_regression(demo_repo_path: Path):
    result = await demo_engineer(demo_repo_path, "Add retry handling with exponential backoff")

    paths = {item["path"] for item in result["files"]}
    assert {"checkout.py", "auth.py", "tests/test_checkout.py"} <= paths
    auth = next(item["content"] for item in result["files"] if item["path"] == "auth.py")
    assert "DEMO-ONLY planted regression" in auth


@pytest.mark.asyncio
async def test_demo_security_reviewer_blocks_auth_change():
    review = await demo_security_review("diff --git a/auth.py b/auth.py", ["auth.py"])

    assert review["severity"] == "critical"
    assert review["score"] < 60


@pytest.mark.asyncio
async def test_demo_repair_restores_role_validation(demo_repo_path: Path):
    result = await demo_repair(demo_repo_path, "findings")
    auth = next(item["content"] for item in result["files"] if item["path"] == "auth.py")

    assert "if user_role != role" in auth
    assert "DEMO-ONLY planted regression" not in auth


@pytest.mark.asyncio
async def test_provider_repair_normalizes_a_filename_to_content_map(tmp_path: Path):
    (tmp_path / "auth.py").write_text("def authorize():\n    return True\n", encoding="utf-8")

    async def completion(_: str, __: str) -> str:
        return json.dumps({"auth.py": "def authorize():\n    return False\n"})

    result = await run_repair(
        JSONProvider(completion=completion, timeout_seconds=1),
        tmp_path,
        "Preserve authorization",
        "diff",
        "Authorization was weakened",
    )

    assert result["plan"] == "Apply the scoped reviewer-requested repair."
    assert result["constraints_identified"] == []
    assert result["files"] == [
        {"path": "auth.py", "content": "def authorize():\n    return False\n"}
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        {"error": "unable to repair"},
        {"message": "refused"},
        {"plan": "I would update the authorization check."},
        {"../outside.py": "malicious"},
        {r"C:\outside.py": "malicious"},
    ],
)
async def test_provider_repair_rejects_prose_errors_and_unsafe_legacy_maps(
    tmp_path: Path, response: dict[str, str]
):
    async def completion(_: str, __: str) -> str:
        return json.dumps(response)

    with pytest.raises((ValidationError, ValueError)):
        await run_repair(
            JSONProvider(completion=completion, timeout_seconds=1),
            tmp_path,
            "Preserve authorization",
            "diff",
            "Authorization was weakened",
        )
