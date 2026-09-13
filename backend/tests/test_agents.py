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


@pytest.mark.asyncio
async def test_repository_security_audit_returns_structured_redacted_findings(tmp_path: Path):
    (tmp_path / "settings.py").write_text(
        'JWT_SECRET_KEY: str = "credential-shaped-value"\n', encoding="utf-8"
    )
    observed_prompt = ""

    async def completion(_: str, user_prompt: str) -> str:
        nonlocal observed_prompt
        observed_prompt = user_prompt
        return json.dumps(
            {
                "summary": "One high-severity issue requires remediation.",
                "coverage": [
                    "secrets",
                    "authentication",
                    "authorization",
                    "api",
                    "dependencies",
                ],
                "limitations": ["Runtime authorization behavior was not exercised."],
                "findings": [
                    {
                        "title": "Hardcoded API credential",
                        "category": "secrets",
                        "severity": "high",
                        "confidence": 1,
                        "location": "settings.py:99",
                        "evidence": "JWT_SECRET_KEY is assigned credential-shaped-value in source.",
                        "recommendation": "Rotate the credential and load it from a secret store.",
                    },
                    {
                        "title": "Missing rate limiting",
                        "category": "api",
                        "severity": "medium",
                        "confidence": 100,
                        "location": "auth.py:0",
                        "evidence": "No rate limiting is present.",
                        "recommendation": "Add rate limiting.",
                    },
                    {
                        "title": "Outdated dependencies",
                        "category": "dependencies",
                        "severity": "low",
                        "confidence": 100,
                        "location": "requirements.txt:0",
                        "evidence": "Some packages may be outdated.",
                        "recommendation": "Update dependencies.",
                    },
                ],
            }
        )

    from app.agents.audit_agent import run_repository_security_audit

    result = await run_repository_security_audit(
        JSONProvider(completion=completion, timeout_seconds=1),
        tmp_path,
        "Audit secrets, authentication, authorization, APIs, and dependencies",
    )

    assert "settings.py" in observed_prompt
    assert result["findings"][0]["severity"] == "high"
    assert result["findings"][0]["confidence"] == 100
    assert result["findings"][0]["location"] == "settings.py:1"
    assert [finding["title"] for finding in result["findings"]] == [
        "Hardcoded API credential"
    ]
    assert "credential-shaped-value" not in result["findings"][0]["evidence"]

    from app.agents.audit_agent import build_audit_reviews

    reviews = build_audit_reviews(tmp_path, result)
    assert reviews["security"]["severity"] == "high"
    assert reviews["security"]["score"] == 100
    assert reviews["scope"]["score"] == 100
    assert reviews["scope"]["evidence"]["missing_categories"] == []
    assert reviews["adversarial"]["score"] == 95
    assert reviews["adversarial"]["evidence"]["verified_findings"] == [
        "Hardcoded API credential"
    ]


@pytest.mark.asyncio
async def test_repository_security_audit_prioritizes_dependency_and_authentication_files(
    tmp_path: Path,
):
    distraction = tmp_path / "aaa"
    distraction.mkdir()
    for index in range(90):
        (distraction / f"module_{index:03}.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "package-lock.json").write_text(
        '{"lockfileVersion": 3, "packages": {}}', encoding="utf-8"
    )
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "auth.py").write_text(
        "def authorize(user):\n    return bool(user)\n", encoding="utf-8"
    )
    observed_prompt = ""

    async def completion(_: str, user_prompt: str) -> str:
        nonlocal observed_prompt
        observed_prompt = user_prompt
        return json.dumps(
            {
                "summary": "No concrete findings.",
                "coverage": [
                    "secrets",
                    "authentication",
                    "authorization",
                    "api",
                    "dependencies",
                ],
                "limitations": [],
                "findings": [],
            }
        )

    from app.agents.audit_agent import run_repository_security_audit

    await run_repository_security_audit(
        JSONProvider(completion=completion, timeout_seconds=1), tmp_path, "Security audit"
    )

    assert "frontend/package-lock.json" in observed_prompt
    assert "backend/auth.py" in observed_prompt


@pytest.mark.asyncio
async def test_repository_security_audit_reconciles_mitigations_and_drops_unsupported_claims(
    tmp_path: Path,
):
    (tmp_path / "config.py").write_text(
        'JWT_SECRET_KEY: str = "development-placeholder"\n'
        'if APP_ENV == "production" and JWT_SECRET_KEY == "development-placeholder":\n'
        '    raise ValueError("production secret required")\n',
        encoding="utf-8",
    )
    (tmp_path / "auth.py").write_text(
        'raise HTTPException(status_code=401, detail="Invalid email or password")\n'
        "import bcrypt\n",
        encoding="utf-8",
    )

    async def completion(_: str, __: str) -> str:
        return json.dumps(
            {
                "summary": "Potential issues found.",
                "coverage": [
                    "secrets",
                    "authentication",
                    "authorization",
                    "api",
                    "dependencies",
                ],
                "limitations": [],
                "findings": [
                    {
                        "title": "Hardcoded JWT Secret Key",
                        "category": "secrets",
                        "severity": "high",
                        "confidence": 90,
                        "location": "config.py:1",
                        "evidence": "JWT_SECRET_KEY has a development placeholder.",
                        "recommendation": "Use a deployment secret.",
                    },
                    {
                        "title": "Potential User Enumeration",
                        "category": "authentication",
                        "severity": "medium",
                        "confidence": 85,
                        "location": "auth.py:1",
                        "evidence": "The response is Invalid email or password.",
                        "recommendation": "Use a generic error.",
                    },
                    {
                        "title": "Outdated bcrypt dependency",
                        "category": "dependencies",
                        "severity": "low",
                        "confidence": 70,
                        "location": "auth.py:2",
                        "evidence": "The application imports bcrypt.",
                        "recommendation": "Update it.",
                    },
                ],
            }
        )

    from app.agents.audit_agent import run_repository_security_audit

    result = await run_repository_security_audit(
        JSONProvider(completion=completion, timeout_seconds=1), tmp_path, "Security audit"
    )

    assert [finding["title"] for finding in result["findings"]] == [
        "Development-only placeholder secret"
    ]
    assert result["findings"][0]["severity"] == "low"
    assert "production validation rejects" in result["findings"][0]["evidence"]


@pytest.mark.asyncio
async def test_repository_security_audit_detects_hardcoded_fallback_password(tmp_path: Path):
    (tmp_path / "accounts.py").write_text(
        'password = payload.password or "predictable-default"\n', encoding="utf-8"
    )

    async def completion(_: str, __: str) -> str:
        return json.dumps(
            {
                "summary": "No model findings.",
                "coverage": [
                    "secrets",
                    "authentication",
                    "authorization",
                    "api",
                    "dependencies",
                ],
                "limitations": [],
                "findings": [],
            }
        )

    from app.agents.audit_agent import run_repository_security_audit

    result = await run_repository_security_audit(
        JSONProvider(completion=completion, timeout_seconds=1), tmp_path, "Security audit"
    )

    assert result["summary"] == "1 evidence-backed finding retained; highest severity is high."
    assert result["findings"] == [
        {
            "title": "Hardcoded fallback password",
            "category": "authentication",
            "severity": "high",
            "confidence": 99,
            "location": "accounts.py:1",
            "evidence": "Account creation falls back to a predictable password embedded in source (value redacted).",
            "recommendation": "Require a caller-supplied password or issue a single-use account setup token instead of a shared fallback.",
        }
    ]
def test_audit_context_never_reads_files_outside_repository(tmp_path: Path):
    from app.agents.audit_agent import _build_audit_context

    root = tmp_path / "repo"
    root.mkdir()
    secret = tmp_path / "private.py"
    secret.write_text("PRIVATE_TOKEN = 'outside-repo-secret'", encoding="utf-8")
    try:
        (root / "config.py").symlink_to(secret)
    except OSError:
        pytest.skip("Symlinks require developer mode on Windows")
    assert "outside-repo-secret" not in _build_audit_context(root)
