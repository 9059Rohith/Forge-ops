"""Add immutable GitHub user identity.

Revision ID: 0002
Revises: 0001
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import BigInteger, Column, inspect

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("users")}
    if "github_user_id" not in columns:
        op.add_column("users", Column("github_user_id", BigInteger(), nullable=True))
        op.create_index(
            "ix_users_github_user_id",
            "users",
            ["github_user_id"],
            unique=True,
        )


def downgrade() -> None:
    # User and billing identity history must never be destroyed automatically.
    pass
