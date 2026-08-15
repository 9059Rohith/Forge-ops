from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_creates_complete_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from alembic import command
    from alembic.config import Config

    database = tmp_path / "migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")

    tables = set(inspect(create_engine(f"sqlite:///{database}")).get_table_names())
    assert {"tasks", "users", "subscriptions", "repair_credits", "repair_usages", "audit_logs"} <= tables
