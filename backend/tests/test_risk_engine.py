import pytest

from app.core.risk_engine import compute_risk


def review(score: int, severity: str = "none") -> dict[str, object]:
    return {"score": score, "severity": severity, "finding": "", "evidence": {}}


def test_verifies_when_weighted_score_reaches_threshold_and_tests_pass():
    result = compute_risk(review(75), review(75), review(75), 4, 4)

    assert result == {
        "overall_confidence": 80.0,
        "risk_level": "LOW",
        "decision": "VERIFIED",
    }


def test_blocks_when_no_tests_ran_even_if_reviewers_are_positive():
    result = compute_risk(review(90), review(90), review(90), 0, 0)

    assert result["decision"] == "BLOCKED"
    assert result["overall_confidence"] == 72.0
    assert result["risk_level"] == "MEDIUM"


def test_critical_finding_is_a_hard_failure():
    result = compute_risk(review(100, "critical"), review(100), review(100), 8, 8)

    assert result["decision"] == "BLOCKED"
    assert result["risk_level"] == "HIGH"


@pytest.mark.parametrize("severity", ["critical", "CRITICAL", "Critical"])
def test_critical_matching_is_case_insensitive(severity: str):
    assert (
        compute_risk(review(100, severity), review(100), review(100), 1, 1)["decision"] == "BLOCKED"
    )
