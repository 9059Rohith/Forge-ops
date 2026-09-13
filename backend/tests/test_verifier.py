import os
import subprocess
from pathlib import Path

import pytest

from app.core.deterministic_verifier import (
    detect_test_command,
    parse_pytest_summary,
    verify_repository,
)


def test_detects_pytest_without_using_a_shell(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    command = detect_test_command(tmp_path)

    assert command[-5:] == ["-m", "pytest", "-q", "-o", "addopts="]
    assert all(";" not in item for item in command)


def test_detects_npm_test_script(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest run"}}', encoding="utf-8")

    npm = "npm.cmd" if os.name == "nt" else "npm"
    assert detect_test_command(tmp_path) == [npm, "test", "--", "--run"]


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("8 passed in 0.12s", (8, 8)),
        ("7 passed, 1 failed in 1.2s", (7, 8)),
        ("2 failed, 3 passed, 1 skipped", (3, 5)),
    ],
)
def test_parse_pytest_summary(output: str, expected: tuple[int, int]):
    assert parse_pytest_summary(output) == expected


@pytest.mark.asyncio
async def test_runs_nested_backend_suite_for_a_backend_change(tmp_path: Path):
    tests = tmp_path / "backend" / "tests"
    tests.mkdir(parents=True)
    (tests / "test_health.py").write_text(
        "def test_health():\n    assert True\n",
        encoding="utf-8",
    )
    (tmp_path / "backend" / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = "-q"\n',
        encoding="utf-8",
    )

    result = await verify_repository(
        tmp_path,
        timeout_seconds=30,
        changed_files=["backend/tests/test_health.py"],
    )

    assert (result.passed, result.total, result.exit_code) == (1, 1, 0)


@pytest.mark.asyncio
async def test_counts_vitest_tests_without_counting_test_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"test":"node test-runner.js"}}',
        encoding="utf-8",
    )

    from app.core import deterministic_verifier

    monkeypatch.setattr(
        deterministic_verifier,
        "_run",
        lambda command, root, timeout: subprocess.CompletedProcess(
            command,
            0,
            stdout=" Test Files  1 passed (1)\n Tests  2 passed (2)",
            stderr="",
        ),
    )

    result = await verify_repository(tmp_path, timeout_seconds=30)

    assert (result.passed, result.total, result.exit_code) == (2, 2, 0)
