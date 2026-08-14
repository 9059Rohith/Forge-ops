from app.core.proof_package import build_proof_package


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
