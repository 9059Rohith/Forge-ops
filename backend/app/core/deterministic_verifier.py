from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class VerificationResult:
    passed: int
    total: int
    exit_code: int
    command: list[str]
    output: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TestSuite:
    command: list[str]
    root: Path
    framework: str


def detect_test_command(root: Path) -> list[str]:
    package_path = root / "package.json"
    if package_path.exists():
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
            if package.get("scripts", {}).get("test"):
                npm = "npm.cmd" if os.name == "nt" else "npm"
                return [npm, "test", "--", "--run"]
        except (json.JSONDecodeError, OSError):
            pass
    if (
        (root / "tests").exists()
        or (root / "pytest.ini").exists()
        or (root / "pyproject.toml").exists()
    ):
        return [sys.executable, "-m", "pytest", "-q", "-o", "addopts="]
    return []


def detect_test_suites(root: Path, changed_files: list[str] | None = None) -> list[TestSuite]:
    candidates = [root, root / "backend", root / "frontend"]
    suites: list[TestSuite] = []
    for candidate in candidates:
        command = detect_test_command(candidate)
        if command:
            framework = "vitest" if Path(command[0]).name.lower().startswith("npm") else "pytest"
            suites.append(TestSuite(command, candidate, framework))
    if not changed_files:
        return suites

    touched_roots = {
        Path(path.replace("\\", "/")).parts[0]
        for path in changed_files
        if Path(path.replace("\\", "/")).parts
    }
    selected = [
        suite
        for suite in suites
        if suite.root == root or suite.root.relative_to(root).parts[0] in touched_roots
    ]
    return selected or suites


def parse_pytest_summary(output: str) -> tuple[int, int]:
    passed = sum(int(value) for value in re.findall(r"(\d+)\s+passed", output))
    failed = sum(int(value) for value in re.findall(r"(\d+)\s+failed", output))
    errors = sum(int(value) for value in re.findall(r"(\d+)\s+errors?", output))
    return passed, passed + failed + errors


def parse_vitest_summary(output: str) -> tuple[int, int]:
    test_lines = [line for line in output.splitlines() if re.match(r"\s*Tests\s+", line)]
    if not test_lines:
        return 0, 0
    counts = {
        status: int(value)
        for value, status in re.findall(r"(\d+)\s+(passed|failed)", test_lines[-1])
    }
    passed = counts.get("passed", 0)
    return passed, passed + counts.get("failed", 0)


def _run(command: list[str], root: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - command comes from the fixed detector above, never user input
        command,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )


async def verify_repository(
    root: Path,
    timeout_seconds: float = 120.0,
    changed_files: list[str] | None = None,
) -> VerificationResult:
    suites = detect_test_suites(root, changed_files)
    if not suites:
        return VerificationResult(0, 0, 2, [], "No supported test suite detected.")

    passed = 0
    total = 0
    exit_code = 0
    outputs: list[str] = []
    for suite in suites:
        try:
            result = await asyncio.to_thread(
                _run, suite.command, suite.root, timeout_seconds
            )
            output = f"{result.stdout}\n{result.stderr}".strip()
            suite_passed, suite_total = (
                parse_vitest_summary(output)
                if suite.framework == "vitest"
                else parse_pytest_summary(output)
            )
            passed += suite_passed
            total += suite_total
            if result.returncode and exit_code == 0:
                exit_code = result.returncode
            outputs.append(f"[{suite.root.name}] {' '.join(suite.command)}\n{output}")
        except subprocess.TimeoutExpired:
            if exit_code == 0:
                exit_code = 124
            outputs.append(f"[{suite.root.name}] Tests timed out after {timeout_seconds}s")
    return VerificationResult(
        passed,
        total,
        exit_code,
        suites[0].command,
        "\n\n".join(outputs)[-50_000:],
    )
