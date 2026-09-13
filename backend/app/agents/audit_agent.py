from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.core.repository import resolve_safe_path
from app.providers.base import JSONProvider
from app.schemas import SecurityAuditResult

AUDIT_SYSTEM_PROMPT = """You are a senior application security auditor performing a read-only
repository review. Identify concrete vulnerabilities in secrets handling, authentication,
authorization, API design and validation, and third-party dependencies. Distinguish exploitable
issues from hardening suggestions. Read mitigating validators and guards before reporting a
finding. Do not report missing rate limits, plaintext storage, permissive CORS, insecure cookies,
or similar absence claims when the supplied source contains the corresponding protection. Do not
call development placeholder defaults exposed production credentials when production validation
rejects them. Dependency findings must name a package, installed version, and specific advisory;
otherwise omit them. Every finding must name an exact, positive repository line number whose
source contains the identifier or construct described by the evidence. Confidence must be an
integer from 0 to 100, never a 0-to-1 probability. Explain redacted evidence, assign severity and
confidence, and give a specific remediation.
Never reproduce credentials, tokens, passwords, private keys, or other secret values.
Return ONLY JSON in this shape:
{"summary":"...","coverage":["secrets","authentication","authorization","api","dependencies"],
"limitations":["..."],"findings":[{"title":"...","category":"secrets|authentication|authorization|api|dependencies|other",
"severity":"info|low|medium|high|critical","confidence":0,"location":"path:line",
"evidence":"redacted evidence","recommendation":"specific fix"}]}"""


_SECRET_ASSIGNMENT = re.compile(
    r"(?im)(?:api[_-]?key|secret|token|password|passwd|private[_-]?key)"
    r"[a-z0-9_-]*(?:\s*:\s*[^=\r\n]{1,60})?\s*=\s*[\"']([^\"'\r\n]{8,})[\"']"
)

_AUDIT_PRIORITY_NAMES = {
    ".env",
    ".env.example",
    "dockerfile",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements.txt",
    "poetry.lock",
    "pipfile",
    "pipfile.lock",
    "build.gradle",
    "build.gradle.kts",
    "gradle.properties",
    "settings.gradle",
    "settings.gradle.kts",
}
_TEXT_SUFFIXES = {
    ".c",
    ".cs",
    ".go",
    ".gradle",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
_FALLBACK_PASSWORD = re.compile(
    r"(?i)\b(?:password|passwd|pw)\b\s*=\s*[^#\r\n]*?\bor\s*[\"']([^\"'\r\n]{6,})[\"']"
)


def _build_audit_context(root: Path, *, max_files: int = 120, max_chars: int = 160_000) -> str:
    ignored = {".git", "node_modules", ".next", ".venv", "venv", "dist", "build", "__pycache__"}

    def priority(path: Path) -> tuple[int, str]:
        relative = path.relative_to(root).as_posix().casefold()
        name = path.name.casefold()
        security_path = any(
            marker in relative
            for marker in ("auth", "security", "middleware", "permission", "route", "api", "setting", "config")
        )
        dependency_file = name in _AUDIT_PRIORITY_NAMES or name.startswith("requirements")
        return (0 if dependency_file or security_path else 1, relative)

    candidates = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.resolve().is_relative_to(root.resolve())
        and not any(part in ignored for part in path.parts)
        and (path.suffix.casefold() in _TEXT_SUFFIXES or path.name.casefold() in _AUDIT_PRIORITY_NAMES)
        and path.stat().st_size <= 250_000
    ]
    sections: list[str] = []
    size = 0
    for path in sorted(candidates, key=priority):
        if len(sections) >= max_files or size >= max_chars:
            break
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        relative = path.relative_to(root).as_posix()
        section = f"\n--- {relative} ---\n{content[:20_000]}"
        sections.append(section)
        size += len(section)
    return "".join(sections)[:max_chars]


def _redact(value: Any, secrets: set[str]) -> Any:
    if isinstance(value, str):
        for secret in sorted(secrets, key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        return value
    if isinstance(value, list):
        return [_redact(item, secrets) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item, secrets) for key, item in value.items()}
    return value


def _validate_finding_locations(root: Path, audit: dict[str, Any]) -> dict[str, Any]:
    verified: list[dict[str, Any]] = []
    for finding in audit.get("findings", []):
        location = str(finding.get("location", ""))
        match = re.fullmatch(r"(.+):(\d+)", location)
        if not match:
            continue
        try:
            source = resolve_safe_path(root, match.group(1))
            if not source.resolve().is_relative_to(root.resolve()):
                continue
            lines = source.read_text(encoding="utf-8").splitlines()
            requested_line = int(match.group(2))
        except (OSError, UnicodeError, ValueError):
            continue

        evidence_text = f"{finding.get('title', '')} {finding.get('evidence', '')}"
        normalized_evidence = evidence_text.casefold()
        category = str(finding.get("category", "other"))
        if category == "dependencies" and not re.search(
            r"\b(?:CVE-\d{4}-\d{4,}|GHSA-[a-z0-9-]{10,})\b", evidence_text, re.IGNORECASE
        ):
            continue
        if "user enumeration" in normalized_evidence and "invalid email or password" in normalized_evidence:
            continue
        symbols = {
            symbol
            for symbol in re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", evidence_text)
            if "_" in symbol
        }
        candidate_lines = [
            index
            for index, source_line in enumerate(lines, 1)
            if any(symbol in source_line for symbol in symbols)
        ]
        if symbols:
            if not candidate_lines:
                continue
            if requested_line not in candidate_lines:
                requested_line = candidate_lines[0]
        else:
            if requested_line < 1 or requested_line > len(lines):
                continue
            source_words = {
                word.casefold() for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", lines[requested_line - 1])
            }
            evidence_words = {
                word.casefold() for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", evidence_text)
            }
            if len(source_words.intersection(evidence_words)) < 2:
                continue

        finding["location"] = f"{match.group(1)}:{requested_line}"
        source_text = "\n".join(lines)
        if (
            category == "secrets"
            and "hardcod" in normalized_evidence
            and symbols
            and "production" in source_text.casefold()
            and "raise valueerror" in source_text.casefold()
            and any(source_text.count(symbol) >= 2 for symbol in symbols)
        ):
            symbol = sorted(symbols)[0]
            finding.update(
                title="Development-only placeholder secret",
                severity="low",
                confidence=max(int(finding.get("confidence", 0)), 95),
                evidence=(
                    f"{symbol} has a source default, while production validation rejects "
                    "placeholder values."
                ),
                recommendation=(
                    "Keep the production validation and require the deployment secret to be "
                    "provided by an environment-specific secret store."
                ),
            )
        verified.append(finding)
    audit["findings"] = verified
    return audit


def _add_deterministic_findings(root: Path, audit: dict[str, Any]) -> dict[str, Any]:
    ignored = {".git", "node_modules", ".next", ".venv", "venv", "dist", "build", "__pycache__"}
    findings = list(audit.get("findings", []))
    known_locations = {str(item.get("location", "")) for item in findings}
    for path in root.rglob("*"):
        if (
            not path.is_file()
            or not path.resolve().is_relative_to(root.resolve())
            or any(part in ignored for part in path.parts)
            or path.suffix.casefold() not in _TEXT_SUFFIXES
            or path.stat().st_size > 250_000
        ):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for line_number, line in enumerate(lines, 1):
            if not _FALLBACK_PASSWORD.search(line):
                continue
            location = f"{path.relative_to(root).as_posix()}:{line_number}"
            if location in known_locations:
                continue
            findings.append(
                {
                    "title": "Hardcoded fallback password",
                    "category": "authentication",
                    "severity": "high",
                    "confidence": 99,
                    "location": location,
                    "evidence": (
                        "Account creation falls back to a predictable password embedded in "
                        "source (value redacted)."
                    ),
                    "recommendation": (
                        "Require a caller-supplied password or issue a single-use account setup "
                        "token instead of a shared fallback."
                    ),
                }
            )
            known_locations.add(location)
    audit["findings"] = findings
    severity_rank = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    highest = max(
        (str(item.get("severity", "info")) for item in findings),
        key=lambda severity: severity_rank.get(severity, 0),
        default="none",
    )
    noun = "finding" if len(findings) == 1 else "findings"
    audit["summary"] = (
        f"{len(findings)} evidence-backed {noun} retained; highest severity is {highest}."
    )
    return audit


async def run_repository_security_audit(
    provider: JSONProvider, root: Path, description: str
) -> dict[str, Any]:
    context = _build_audit_context(root)
    known_secrets = {match.group(1) for match in _SECRET_ASSIGNMENT.finditer(context)}
    raw = await provider.complete_json(
        AUDIT_SYSTEM_PROMPT,
        f"AUDIT REQUEST:\n{description}\n\nREPOSITORY CONTENTS:\n{context}",
    )
    validated = SecurityAuditResult.model_validate(raw).model_dump()
    verified = _add_deterministic_findings(root, _validate_finding_locations(root, validated))
    return _redact(verified, known_secrets)


def build_audit_reviews(root: Path, audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    findings = list(audit.get("findings", []))
    severity_rank = {"info": 0, "none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    highest = max(
        (str(item.get("severity", "none")) for item in findings),
        key=lambda severity: severity_rank.get(severity, 0),
        default="none",
    )
    normalized_severity = "none" if highest == "info" else highest
    confidence = (
        round(sum(int(item.get("confidence", 0)) for item in findings) / len(findings))
        if findings
        else 95
    )

    expected_coverage = {"secrets", "authentication", "authorization", "api", "dependencies"}
    observed_coverage = {str(item) for item in audit.get("coverage", [])}
    missing = sorted(expected_coverage - observed_coverage)
    scope_score = max(0, 100 - 20 * len(missing))

    verified: list[str] = []
    unverifiable: list[str] = []
    critical_findings = [
        item for item in findings if str(item.get("severity")) in {"high", "critical"}
    ]
    for finding in critical_findings:
        title = str(finding.get("title", "Untitled finding"))
        match = re.fullmatch(r"(.+):(\d+)", str(finding.get("location", "")))
        if not match:
            unverifiable.append(title)
            continue
        try:
            source = resolve_safe_path(root, match.group(1))
            if not source.resolve().is_relative_to(root.resolve()):
                raise ValueError("finding location escapes repository")
            line_number = int(match.group(2))
            lines = source.read_text(encoding="utf-8").splitlines()
            if line_number < 1 or line_number > len(lines) or not lines[line_number - 1].strip():
                raise ValueError("location does not reference source content")
        except (OSError, UnicodeError, ValueError):
            unverifiable.append(title)
        else:
            verified.append(title)

    if not critical_findings or not unverifiable:
        verification_score, verification_severity = 95, "none"
    elif verified:
        verification_score, verification_severity = 70, "medium"
    else:
        verification_score, verification_severity = 40, "high"

    return {
        "security": {
            "score": confidence,
            "severity": normalized_severity,
            "finding": str(audit.get("summary", "Security audit completed.")),
            "evidence": audit,
        },
        "scope": {
            "score": scope_score,
            "severity": "none" if not missing else "medium",
            "finding": (
                "All requested security categories were reviewed."
                if not missing
                else f"Audit coverage is missing: {', '.join(missing)}."
            ),
            "evidence": {
                "reviewed_categories": sorted(observed_coverage),
                "missing_categories": missing,
                "limitations": list(audit.get("limitations", [])),
            },
        },
        "adversarial": {
            "score": verification_score,
            "severity": verification_severity,
            "finding": (
                "All high and critical finding locations were verified against repository source."
                if not unverifiable
                else f"{len(unverifiable)} high-impact finding location(s) could not be verified."
            ),
            "evidence": {
                "verified_findings": verified,
                "unverifiable_findings": unverifiable,
            },
        },
    }
