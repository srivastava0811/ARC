from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ProcurementRequest(Base):
    __tablename__ = "procurement_requests"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id"), nullable=False, index=True
    )
    original_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    structured_requirements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(48), nullable=False, default="CREATED", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_requests.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProductCandidate(Base):
    __tablename__ = "product_candidates"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_requests.id"), nullable=False, index=True
    )
    external_product_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(128))
    merchant: Mapped[str | None] = mapped_column(String(128))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    product_url: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    specifications: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        UniqueConstraint(
            "procurement_request_id", "external_product_id", name="uq_request_external_product"
        ),
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_requests.id"), nullable=False, index=True
    )
    product_candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_candidates.id"), nullable=False, index=True
    )
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rejection_reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AgentExecution(Base):
    __tablename__ = "agent_executions"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_requests.id"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_requests.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        UniqueConstraint(
            "procurement_request_id", "sequence_number", name="uq_request_event_sequence"
        ),
    )


class ProcurementReport(Base):
    __tablename__ = "procurement_reports"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_requests.id"), nullable=False, index=True
    )
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    structured_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PaymentTransaction(Base):
    """A PayPal Sandbox order for an explicitly approved ARC recommendation."""

    __tablename__ = "payment_transactions"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_requests.id"), nullable=False, index=True
    )
    product_candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_candidates.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="paypal")
    paypal_order_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    paypal_capture_id: Mapped[str | None] = mapped_column(String(128))
    approval_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
