from pathlib import Path

import pytest

from app.core.deterministic_verifier import detect_test_command, parse_pytest_summary


def test_detects_pytest_without_using_a_shell(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    command = detect_test_command(tmp_path)

    assert command[-3:] == ["-m", "pytest", "-q"]
    assert all(";" not in item for item in command)


def test_detects_npm_test_script(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest run"}}', encoding="utf-8")

    assert detect_test_command(tmp_path) == ["npm", "test", "--", "--run"]


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
