from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def demo_repo_path() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-repo"


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("WORK_ROOT", str(tmp_path / "worktrees"))
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    yield
    os.environ.pop("DATABASE_URL", None)
