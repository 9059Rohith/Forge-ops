import hashlib
import json
import re

from app.core.proof_package import build_proof_package, build_verification_receipt


def test_proof_package_contains_required_evidence_and_scores():
    markdown = build_proof_package(
        description="Add retry handling",
        changed_files=["checkout.py", "tests/test_checkout.py"],
        tests_passed=8,
        tests_total=8,
        evaluations={
            "security": {"score": 94, "severity": "none"},
            "scope": {"score": 96, "severity": "none"},
            "adversarial": {"score": 93, "severity": "low"},
        },
        confidence=94.6,
        risk_level="LOW",
        repair_cycles=1,
        decision="VERIFIED",
    )

    assert "## 🛡️ ForgeGuard Verified" in markdown
    assert "**Tests:** 8/8 PASS" in markdown
    assert "| Security | 94% | ✅ |" in markdown
    assert "**Overall confidence:** 94.6%" in markdown
    assert "Full agent execution trace" in markdown


def test_verification_receipt_is_deterministic_and_seals_the_evidence():
    arguments = {
        "task_id": "task-123",
        "description": "Add retry handling",
        "repo_url": "demo",
        "branch": "main",
        "changed_files": ["checkout.py", "tests/test_checkout.py"],
        "tests_passed": 8,
        "tests_total": 8,
        "evaluations": {
            "security": {"score": 94, "severity": "none", "finding": "Safe"},
            "scope": {"score": 96, "severity": "none", "finding": "Focused"},
            "adversarial": {"score": 93, "severity": "low", "finding": "Bounded"},
        },
        "confidence": 94.6,
        "risk_level": "LOW",
        "repair_cycles": 1,
        "decision": "VERIFIED",
        "agent_runs": [
            {
                "agent_name": "engineer",
                "status": "completed",
                "started_at": "2026-08-15T10:00:00+00:00",
                "completed_at": "2026-08-15T10:00:02+00:00",
            }
        ],
        "flight_logs": [
            {"timestamp": "2026-08-15T10:00:00+00:00", "event": "Task received"}
        ],
        "diff_text": "diff --git a/checkout.py b/checkout.py\n",
        "proof_text": "## ForgeGuard Verified\n",
    }

    first = build_verification_receipt(**arguments)
    second = build_verification_receipt(**arguments)

    assert first == second
    assert first["schema_version"] == "1.0"
    assert re.fullmatch(r"fg_[0-9a-f]{16}", first["receipt_id"])
    assert first["artifacts"]["diff_sha256"] == hashlib.sha256(
        arguments["diff_text"].encode()
    ).hexdigest()
    assert first["artifacts"]["proof_sha256"] == hashlib.sha256(
        arguments["proof_text"].encode()
    ).hexdigest()

    evidence_payload = {
        key: value for key, value in first.items() if key not in {"receipt_id", "integrity"}
    }
    expected_digest = hashlib.sha256(
        json.dumps(
            evidence_payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    ).hexdigest()
    assert first["integrity"] == {"algorithm": "sha256", "digest": expected_digest}
    assert first["receipt_id"] == f"fg_{expected_digest[:16]}"
