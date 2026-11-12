"""Create the initial workspace table.

Revision ID: 0001_create_workspaces
Revises:
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_workspaces"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )


def downgrade() -> None:
    op.drop_table("workspaces")
