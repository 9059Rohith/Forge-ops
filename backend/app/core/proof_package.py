from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _icon(severity: str) -> str:
    return {"none": "✅", "low": "✅", "medium": "⚠️", "high": "❌", "critical": "❌"}.get(
        severity.lower(), "⚠️"
    )


def build_proof_package(
    *,
    description: str,
    changed_files: Sequence[str],
    tests_passed: int,
    tests_total: int,
    evaluations: Mapping[str, Mapping[str, Any]],
    confidence: float,
    risk_level: str,
    repair_cycles: int,
    decision: str,
) -> str:
    security = evaluations["security"]
    scope = evaluations["scope"]
    adversarial = evaluations["adversarial"]
    title = "Verified" if decision == "VERIFIED" else "Blocked"
    return f"""## 🛡️ ForgeGuard {title}

**Task:** {description}

**Files changed:** {len(changed_files)}
**Tests:** {tests_passed}/{tests_total} PASS

| Check | Score | Status |
|---|---:|:---:|
| Security | {security["score"]}% | {_icon(str(security["severity"]))} |
| Scope | {scope["score"]}% | {_icon(str(scope["severity"]))} |
| Adversarial Review | {adversarial["score"]}% | {_icon(str(adversarial["severity"]))} |

**Overall confidence:** {confidence}%
**Risk:** {risk_level}
**Repair cycles:** {repair_cycles}

### Evidence
- ✓ Git diff captured
- ✓ Test logs captured
- ✓ Independent security review
- ✓ Independent scope review
- ✓ Adversarial review
- ✓ Full agent execution trace (Flight Recorder)
"""
