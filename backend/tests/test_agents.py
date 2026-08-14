from pathlib import Path

import pytest

from app.agents.demo import demo_engineer, demo_repair, demo_security_review


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
