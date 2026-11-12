"""Add persisted Phase 2 procurement workflow tables.

Revision ID: 0002_procurement_workflow
Revises: 0001_create_workspaces
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_procurement_workflow"
down_revision: str | None = "0001_create_workspaces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "procurement_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("original_prompt", sa.Text(), nullable=False),
        sa.Column("structured_requirements", sa.JSON()),
        sa.Column("status", sa.String(48), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_procurement_requests_workspace_id", "procurement_requests", ["workspace_id"]
    )
    op.create_index("ix_procurement_requests_status", "procurement_requests", ["status"])
    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "procurement_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_requests.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_conversation_messages_procurement_request_id",
        "conversation_messages",
        ["procurement_request_id"],
    )
    op.create_table(
        "product_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "procurement_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_requests.id"),
            nullable=False,
        ),
        sa.Column("external_product_id", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(48), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("brand", sa.String(128)),
        sa.Column("merchant", sa.String(128)),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("product_url", sa.Text()),
        sa.Column("image_url", sa.Text()),
        sa.Column("specifications", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "procurement_request_id", "external_product_id", name="uq_request_external_product"
        ),
    )
    op.create_index(
        "ix_product_candidates_procurement_request_id",
        "product_candidates",
        ["procurement_request_id"],
    )
    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "procurement_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_requests.id"),
            nullable=False,
        ),
        sa.Column(
            "product_candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_candidates.id"),
            nullable=False,
        ),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Numeric(5, 2)),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("rejection_reasons", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_evaluations_procurement_request_id", "evaluations", ["procurement_request_id"]
    )
    op.create_index("ix_evaluations_product_candidate_id", "evaluations", ["product_candidate_id"])
    op.create_table(
        "agent_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "procurement_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_requests.id"),
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(48), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("model_name", sa.String(128)),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer()),
    )
    op.create_index(
        "ix_agent_executions_procurement_request_id", "agent_executions", ["procurement_request_id"]
    )
    op.create_table(
        "workflow_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "procurement_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_requests.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "procurement_request_id", "sequence_number", name="uq_request_event_sequence"
        ),
    )
    op.create_index(
        "ix_workflow_events_procurement_request_id", "workflow_events", ["procurement_request_id"]
    )
    op.create_table(
        "procurement_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "procurement_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_requests.id"),
            nullable=False,
        ),
        sa.Column("report_type", sa.String(32), nullable=False),
        sa.Column("structured_content", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_procurement_reports_procurement_request_id",
        "procurement_reports",
        ["procurement_request_id"],
    )


def downgrade() -> None:
    for table in (
        "procurement_reports",
        "workflow_events",
        "agent_executions",
        "evaluations",
        "product_candidates",
        "conversation_messages",
        "procurement_requests",
    ):
        op.drop_table(table)
