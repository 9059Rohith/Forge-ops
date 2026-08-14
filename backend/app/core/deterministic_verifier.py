from __future__ import annotations

import asyncio
import json
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


def detect_test_command(root: Path) -> list[str]:
    package_path = root / "package.json"
    if package_path.exists():
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
            if package.get("scripts", {}).get("test"):
                return ["npm", "test", "--", "--run"]
        except (json.JSONDecodeError, OSError):
            pass
    if (
        (root / "tests").exists()
        or (root / "pytest.ini").exists()
        or (root / "pyproject.toml").exists()
    ):
        return [sys.executable, "-m", "pytest", "-q"]
    return []


def parse_pytest_summary(output: str) -> tuple[int, int]:
    passed = sum(int(value) for value in re.findall(r"(\d+)\s+passed", output))
    failed = sum(int(value) for value in re.findall(r"(\d+)\s+failed", output))
    errors = sum(int(value) for value in re.findall(r"(\d+)\s+errors?", output))
    return passed, passed + failed + errors


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


async def verify_repository(root: Path, timeout_seconds: float = 120.0) -> VerificationResult:
    command = detect_test_command(root)
    if not command:
        return VerificationResult(0, 0, 2, [], "No supported test suite detected.")
    try:
        result = await asyncio.to_thread(_run, command, root, timeout_seconds)
        output = f"{result.stdout}\n{result.stderr}".strip()[-50_000:]
        passed, total = parse_pytest_summary(output)
        return VerificationResult(passed, total, result.returncode, command, output)
    except subprocess.TimeoutExpired:
        return VerificationResult(0, 0, 124, command, f"Tests timed out after {timeout_seconds}s")
