"""Create the consolidated ForgeGuard and Repair Credits schema.

Revision ID: 0001
Revises: None
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import Column, Integer, String, Text, inspect

import billing.models  # noqa: F401
from app.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names())

    # Fresh databases are created from the same metadata used by the app,
    # keeping one authoritative schema for SQLite and Postgres.
    Base.metadata.create_all(bind=bind, checkfirst=True)

    # Older hackathon databases already have tasks; add ownership and the
    # pending repair plan without rebuilding or deleting those rows.
    if "tasks" in existing:
        columns = {item["name"] for item in inspector.get_columns("tasks")}
        if "user_id" not in columns:
            op.add_column("tasks", Column("user_id", String(36), nullable=True))
            op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
        if "pending_plan" not in columns:
            op.add_column("tasks", Column("pending_plan", Text(), nullable=True))
        if "repair_branch" not in columns:
            op.add_column("tasks", Column("repair_branch", String(255), nullable=True))
        if "pr_url" not in columns:
            op.add_column("tasks", Column("pr_url", String(500), nullable=True))
        if "pr_number" not in columns:
            op.add_column("tasks", Column("pr_number", Integer(), nullable=True))

    if "projects" in existing:
        columns = {item["name"] for item in inspector.get_columns("projects")}
        if "repo_full_name" not in columns:
            op.add_column("projects", Column("repo_full_name", String(255), nullable=True))
            op.create_index("ix_projects_repo_full_name", "projects", ["repo_full_name"])
        if "github_installation_id" not in columns:
            op.add_column(
                "projects", Column("github_installation_id", Integer(), nullable=True)
            )


def downgrade() -> None:
    # The initial migration is deliberately additive. Billing and audit history
    # must never be destroyed by an automated downgrade.
    pass
