"""Add persisted PayPal Sandbox payment records.

Revision ID: 0003_paypal_sandbox_payments
Revises: 0002_procurement_workflow
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_paypal_sandbox_payments"
down_revision: str | None = "0002_procurement_workflow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_transactions",
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
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("paypal_order_id", sa.String(128), nullable=False, unique=True),
        sa.Column("paypal_capture_id", sa.String(128)),
        sa.Column("approval_url", sa.Text()),
        sa.Column("status", sa.String(48), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_payment_transactions_procurement_request_id",
        "payment_transactions",
        ["procurement_request_id"],
    )
    op.create_index(
        "ix_payment_transactions_product_candidate_id",
        "payment_transactions",
        ["product_candidate_id"],
    )
    op.create_index("ix_payment_transactions_status", "payment_transactions", ["status"])


def downgrade() -> None:
    op.drop_table("payment_transactions")
