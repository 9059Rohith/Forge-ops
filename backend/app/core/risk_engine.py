from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def compute_risk(
    security: Mapping[str, Any],
    scope: Mapping[str, Any],
    adversarial: Mapping[str, Any],
    tests_passed: int,
    tests_total: int,
    *,
    test_exit_code: int = 0,
) -> dict[str, Any]:
    incomplete_tests = test_exit_code != 0 or tests_total <= 0 or tests_passed != tests_total
    test_score = 0 if incomplete_tests else 100
    weights = {"security": 0.30, "scope": 0.20, "adversarial": 0.30, "tests": 0.20}
    overall = (
        int(security["score"]) * weights["security"]
        + int(scope["score"]) * weights["scope"]
        + int(adversarial["score"]) * weights["adversarial"]
        + test_score * weights["tests"]
    )
    critical = any(
        str(evaluation.get("severity", "")).lower() == "critical"
        for evaluation in (security, scope, adversarial)
    )
    if critical or incomplete_tests or overall < 75:
        risk_level = "HIGH" if overall < 60 or critical else "MEDIUM"
        decision = "BLOCKED"
    else:
        risk_level = "LOW"
        decision = "VERIFIED"
    return {
        "overall_confidence": round(overall, 1),
        "risk_level": risk_level,
        "decision": decision,
    }
