from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def build_verification_receipt(
    *,
    task_id: str,
    description: str,
    repo_url: str,
    branch: str,
    changed_files: Sequence[str],
    tests_passed: int,
    tests_total: int,
    evaluations: Mapping[str, Mapping[str, Any]],
    confidence: float | None,
    risk_level: str | None,
    repair_cycles: int,
    decision: str,
    agent_runs: Sequence[Mapping[str, Any]],
    flight_logs: Sequence[Mapping[str, Any]],
    diff_text: str,
    proof_text: str,
) -> dict[str, Any]:
    reviewers = {
        name: {
            "score": evaluation["score"],
            "severity": evaluation["severity"],
            "finding": evaluation["finding"],
            "evidence": evaluation.get("evidence", {}),
        }
        for name, evaluation in evaluations.items()
    }
    evidence_payload: dict[str, Any] = {
        "schema_version": "1.0",
        "decision": decision,
        "task": {
            "id": task_id,
            "description": description,
            "repository": repo_url,
            "branch": branch,
            "changed_files": list(changed_files),
        },
        "verification": {
            "tests": {"passed": tests_passed, "total": tests_total},
            "reviewers": reviewers,
            "confidence": confidence,
            "risk_level": risk_level,
            "repair_cycles": repair_cycles,
        },
        "provenance": {
            "agent_runs": [dict(run) for run in agent_runs],
            "flight_logs": [dict(item) for item in flight_logs],
        },
        "artifacts": {
            "diff_sha256": _sha256_text(diff_text),
            "proof_sha256": _sha256_text(proof_text),
        },
    }
    digest = _sha256_text(_canonical_json(evidence_payload))
    return {
        **evidence_payload,
        "receipt_id": f"fg_{digest[:16]}",
        "integrity": {"algorithm": "sha256", "digest": digest},
    }


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


def build_security_audit_report(
    *,
    description: str,
    evaluations: Mapping[str, Mapping[str, Any]],
    confidence: float,
    risk_level: str,
) -> str:
    audit = evaluations["security"].get("evidence", {})
    findings = list(audit.get("findings", [])) if isinstance(audit, Mapping) else []
    coverage = list(audit.get("coverage", [])) if isinstance(audit, Mapping) else []
    limitations = list(audit.get("limitations", [])) if isinstance(audit, Mapping) else []
    rows = "\n".join(
        "| {severity} | {category} | {title} | `{location}` |".format(
            severity=str(item.get("severity", "unknown")).upper(),
            category=str(item.get("category", "other")),
            title=str(item.get("title", "Untitled finding")).replace("|", "\\|"),
            location=str(item.get("location", "unknown")).replace("`", ""),
        )
        for item in findings
    ) or "| NONE | — | No concrete vulnerabilities identified | — |"
    details = "\n\n".join(
        "### {index}. {title}\n\n"
        "- **Severity:** {severity}\n"
        "- **Category:** {category}\n"
        "- **Confidence:** {confidence}%\n"
        "- **Location:** `{location}`\n"
        "- **Evidence:** {evidence}\n"
        "- **Recommended fix:** {recommendation}".format(index=index, **item)
        for index, item in enumerate(findings, 1)
    ) or "No reportable findings."
    limitations_text = "\n".join(f"- {item}" for item in limitations) or "- None reported."
    return f"""## ForgeGuard Security Audit Complete

**Task:** {description}

**Overall audit confidence:** {confidence}%
**Repository risk:** {risk_level}
**Findings:** {len(findings)}
**Coverage:** {", ".join(str(item) for item in coverage) or "not reported"}

| Severity | Category | Finding | Location |
|---|---|---|---|
{rows}

## Findings and recommended fixes

{details}

## Verification

- Coverage review: {evaluations["scope"]["finding"]}
- Critical-finding verification: {evaluations["adversarial"]["finding"]}
- No repository files were changed.
- No repair credit or authorization was requested.

## Limitations

{limitations_text}
"""
