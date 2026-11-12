from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateRequest(BaseModel):
    message: str = Field(min_length=3, max_length=4000)


class ClarificationMessage(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class RequestCreated(BaseModel):
    id: UUID
    status: str


class ProductOut(BaseModel):
    id: UUID
    name: str
    brand: str | None
    merchant: str | None
    price: Decimal
    currency: str
    specifications: dict
    source: str
    product_url: str | None
    image_url: str | None


class EvaluationOut(BaseModel):
    product_candidate_id: UUID
    eligible: bool
    score: Decimal | None
    score_breakdown: dict
    rejection_reasons: list[str]
    explanation: str


class RequestDetail(BaseModel):
    id: UUID
    status: str
    original_prompt: str
    structured_requirements: dict | None
    report: dict | None


class PaymentHistoryItem(BaseModel):
    status: str
    amount: Decimal
    currency: str
    paypal_capture_id: str | None


class RequestHistoryItem(BaseModel):
    id: UUID
    status: str
    original_prompt: str
    created_at: datetime
    updated_at: datetime
    report: dict | None
    payment: PaymentHistoryItem | None


class CheckoutRequest(BaseModel):
    product_candidate_id: UUID


class CheckoutOrder(BaseModel):
    payment_id: UUID
    paypal_order_id: str
    approval_url: str
    status: str
    amount: Decimal
    currency: str


class PaymentOut(BaseModel):
    id: UUID
    product_candidate_id: UUID
    paypal_order_id: str
    paypal_capture_id: str | None
    status: str
    amount: Decimal
    currency: str
    quantity: int


class PaymentReceiptOut(BaseModel):
    procurement_request_id: UUID
    original_prompt: str
    product_name: str
    brand: str | None
    merchant: str | None
    quantity: int
    amount: Decimal
    currency: str
    payment_status: str
    paypal_order_id: str
    paypal_capture_id: str
    issued_at: datetime
    environment: str
