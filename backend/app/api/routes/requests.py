from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from sqlalchemy import func, select

from app.agents.evaluator import catalog_review_reasons
from app.api.schemas.requests import (
    CheckoutOrder,
    CheckoutRequest,
    ClarificationMessage,
    CreateRequest,
    EvaluationOut,
    PaymentHistoryItem,
    PaymentOut,
    PaymentReceiptOut,
    ProductOut,
    RequestCreated,
    RequestDetail,
    RequestHistoryItem,
)
from app.core.config import get_settings
from app.db.models import (
    ConversationMessage,
    Evaluation,
    PaymentTransaction,
    ProcurementReport,
    ProcurementRequest,
    ProductCandidate,
    WorkflowEvent,
)
from app.services.paypal import PayPalClient, PayPalError
from app.services.workflow import ensure_demo_workspace, run_demo_workflow

router = APIRouter(prefix="/requests", tags=["requests"])


async def record_event(session, request_id: UUID, event_type: str, payload: dict) -> None:
    next_sequence = await session.scalar(
        select(func.coalesce(func.max(WorkflowEvent.sequence_number), 0) + 1).where(
            WorkflowEvent.procurement_request_id == request_id
        )
    )
    session.add(
        WorkflowEvent(
            procurement_request_id=request_id,
            event_type=event_type,
            payload=payload,
            sequence_number=next_sequence,
        )
    )


def paypal_client() -> PayPalClient:
    settings = get_settings()
    if settings.paypal_client_id is None or settings.paypal_client_secret is None:
        raise HTTPException(status_code=503, detail="PayPal Sandbox is not configured")
    return PayPalClient(
        client_id=settings.paypal_client_id,
        client_secret=settings.paypal_client_secret.get_secret_value(),
        base_url=settings.paypal_base_url,
    )


@router.get("", response_model=list[RequestHistoryItem])
async def list_requests(request: Request) -> list[RequestHistoryItem]:
    """Return this workspace's saved procurement requests, newest first."""
    async with request.app.state.session_factory() as session:
        workspace = await ensure_demo_workspace(session)
        procurement_requests = (
            await session.scalars(
                select(ProcurementRequest)
                .where(ProcurementRequest.workspace_id == workspace.id)
                .order_by(ProcurementRequest.updated_at.desc())
            )
        ).all()
        result: list[RequestHistoryItem] = []
        for procurement_request in procurement_requests:
            report = await session.scalar(
                select(ProcurementReport)
                .where(ProcurementReport.procurement_request_id == procurement_request.id)
                .order_by(ProcurementReport.created_at.desc())
            )
            payment = await session.scalar(
                select(PaymentTransaction)
                .where(PaymentTransaction.procurement_request_id == procurement_request.id)
                .order_by(PaymentTransaction.created_at.desc())
            )
            result.append(
                RequestHistoryItem(
                    id=procurement_request.id,
                    status=procurement_request.status,
                    original_prompt=procurement_request.original_prompt,
                    created_at=procurement_request.created_at,
                    updated_at=procurement_request.updated_at,
                    report=report.structured_content if report else None,
                    payment=(
                        PaymentHistoryItem(
                            status=payment.status,
                            amount=payment.amount,
                            currency=payment.currency,
                            paypal_capture_id=payment.paypal_capture_id,
                        )
                        if payment is not None
                        else None
                    ),
                )
            )
        return result


@router.post("", response_model=RequestCreated, status_code=status.HTTP_202_ACCEPTED)
async def create_request(
    payload: CreateRequest, request: Request, background_tasks: BackgroundTasks
) -> RequestCreated:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        workspace = await ensure_demo_workspace(session)
        procurement_request = ProcurementRequest(
            workspace_id=workspace.id, original_prompt=payload.message, status="CREATED"
        )
        session.add(procurement_request)
        await session.commit()
        await session.refresh(procurement_request)
    background_tasks.add_task(run_demo_workflow, session_factory, procurement_request.id)
    return RequestCreated(id=procurement_request.id, status=procurement_request.status)


@router.post(
    "/{request_id}/messages", response_model=RequestCreated, status_code=status.HTTP_202_ACCEPTED
)
async def submit_clarification(
    request_id: UUID,
    payload: ClarificationMessage,
    request: Request,
    background_tasks: BackgroundTasks,
) -> RequestCreated:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        procurement_request = await session.get(ProcurementRequest, request_id)
        if procurement_request is None:
            raise HTTPException(status_code=404, detail="Procurement request not found")
        if procurement_request.status != "NEEDS_CLARIFICATION":
            raise HTTPException(
                status_code=409, detail="This request is not awaiting clarification"
            )
        session.add(
            ConversationMessage(
                procurement_request_id=procurement_request.id,
                role="user_clarification",
                content=payload.message,
            )
        )
        procurement_request.status = "CREATED"
        await session.commit()
    background_tasks.add_task(run_demo_workflow, session_factory, procurement_request.id)
    return RequestCreated(id=procurement_request.id, status="CREATED")


@router.get("/{request_id}", response_model=RequestDetail)
async def get_request(request_id: UUID, request: Request) -> RequestDetail:
    async with request.app.state.session_factory() as session:
        procurement_request = await session.get(ProcurementRequest, request_id)
        if procurement_request is None:
            raise HTTPException(status_code=404, detail="Procurement request not found")
        report = await session.scalar(
            select(ProcurementReport)
            .where(ProcurementReport.procurement_request_id == procurement_request.id)
            .order_by(ProcurementReport.created_at.desc())
        )
        return RequestDetail(
            id=procurement_request.id,
            status=procurement_request.status,
            original_prompt=procurement_request.original_prompt,
            structured_requirements=procurement_request.structured_requirements,
            report=report.structured_content if report else None,
        )


@router.get("/{request_id}/products", response_model=list[ProductOut])
async def get_products(request_id: UUID, request: Request) -> list[ProductOut]:
    async with request.app.state.session_factory() as session:
        products = (
            await session.scalars(
                select(ProductCandidate).where(
                    ProductCandidate.procurement_request_id == request_id
                )
            )
        ).all()
        return [
            ProductOut(
                id=item.id,
                name=item.name,
                brand=item.brand,
                merchant=item.merchant,
                price=item.price,
                currency=item.currency,
                specifications={
                    **item.specifications,
                    "price_requires_verification": item.provider == "channel3"
                    and item.specifications.get("product_category", "computer_monitor")
                    == "computer_monitor"
                    and item.price < get_settings().channel3_minimum_monitor_price,
                },
                source=item.provider,
                product_url=item.product_url,
                image_url=item.image_url,
            )
            for item in products
        ]


@router.get("/{request_id}/evaluations", response_model=list[EvaluationOut])
async def get_evaluations(request_id: UUID, request: Request) -> list[EvaluationOut]:
    async with request.app.state.session_factory() as session:
        evaluations = (
            await session.scalars(
                select(Evaluation)
                .where(Evaluation.procurement_request_id == request_id)
                .order_by(Evaluation.score.desc().nullslast())
            )
        ).all()
        candidates = {
            product.id: product
            for product in (
                await session.scalars(
                    select(ProductCandidate).where(
                        ProductCandidate.procurement_request_id == request_id
                    )
                )
            ).all()
        }
        review_reasons = {
            item.product_candidate_id: catalog_review_reasons(
                candidates[item.product_candidate_id],
                get_settings().channel3_minimum_monitor_price,
            )
            for item in evaluations
        }
        return [
            EvaluationOut(
                product_candidate_id=item.product_candidate_id,
                eligible=item.eligible and not review_reasons[item.product_candidate_id],
                score=None if review_reasons[item.product_candidate_id] else item.score,
                score_breakdown=item.score_breakdown,
                rejection_reasons=list(
                    dict.fromkeys(
                        [*item.rejection_reasons, *review_reasons[item.product_candidate_id]]
                    )
                ),
                explanation="; ".join(review_reasons[item.product_candidate_id])
                if review_reasons[item.product_candidate_id]
                else item.explanation,
            )
            for item in evaluations
        ]


@router.get("/{request_id}/payment", response_model=PaymentOut | None)
async def get_payment(request_id: UUID, request: Request) -> PaymentOut | None:
    async with request.app.state.session_factory() as session:
        payment = await session.scalar(
            select(PaymentTransaction)
            .where(PaymentTransaction.procurement_request_id == request_id)
            .order_by(PaymentTransaction.created_at.desc())
        )
        if payment is None:
            return None
        return PaymentOut(
            id=payment.id,
            product_candidate_id=payment.product_candidate_id,
            paypal_order_id=payment.paypal_order_id,
            paypal_capture_id=payment.paypal_capture_id,
            status=payment.status,
            amount=payment.amount,
            currency=payment.currency,
            quantity=payment.quantity,
        )


@router.get("/{request_id}/receipt", response_model=PaymentReceiptOut)
async def get_payment_receipt(request_id: UUID, request: Request) -> PaymentReceiptOut:
    """Return the persisted receipt only for a PayPal-confirmed Sandbox capture."""
    async with request.app.state.session_factory() as session:
        procurement_request = await session.get(ProcurementRequest, request_id)
        if procurement_request is None:
            raise HTTPException(status_code=404, detail="Procurement request not found")
        payment = await session.scalar(
            select(PaymentTransaction)
            .where(
                PaymentTransaction.procurement_request_id == request_id,
                PaymentTransaction.status == "COMPLETED",
            )
            .order_by(PaymentTransaction.updated_at.desc())
        )
        if payment is None or payment.paypal_capture_id is None:
            raise HTTPException(status_code=404, detail="No completed PayPal receipt is available")
        product = await session.get(ProductCandidate, payment.product_candidate_id)
        if product is None:
            raise HTTPException(
                status_code=404, detail="The purchased product record is unavailable"
            )
        return PaymentReceiptOut(
            procurement_request_id=procurement_request.id,
            original_prompt=procurement_request.original_prompt,
            product_name=product.name,
            brand=product.brand,
            merchant=product.merchant,
            quantity=payment.quantity,
            amount=payment.amount,
            currency=payment.currency,
            payment_status=payment.status,
            paypal_order_id=payment.paypal_order_id,
            paypal_capture_id=payment.paypal_capture_id,
            issued_at=payment.updated_at,
            environment="PayPal Sandbox",
        )


@router.post("/{request_id}/checkout", response_model=CheckoutOrder)
async def create_checkout_order(
    request_id: UUID, payload: CheckoutRequest, request: Request
) -> CheckoutOrder:
    """Create a PayPal Sandbox order only after an explicit user action."""
    settings = get_settings()
    client = paypal_client()
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        procurement_request = await session.get(ProcurementRequest, request_id)
        if procurement_request is None:
            raise HTTPException(status_code=404, detail="Procurement request not found")
        if procurement_request.status != "AWAITING_APPROVAL":
            raise HTTPException(status_code=409, detail="This request is not ready for approval")
        product = await session.scalar(
            select(ProductCandidate).where(
                ProductCandidate.id == payload.product_candidate_id,
                ProductCandidate.procurement_request_id == request_id,
            )
        )
        evaluation = await session.scalar(
            select(Evaluation).where(
                Evaluation.procurement_request_id == request_id,
                Evaluation.product_candidate_id == payload.product_candidate_id,
            )
        )
        if product is None or evaluation is None or not evaluation.eligible:
            raise HTTPException(
                status_code=409, detail="Select an eligible recommendation to continue"
            )
        review_reasons = catalog_review_reasons(product, settings.channel3_minimum_monitor_price)
        if review_reasons:
            raise HTTPException(status_code=409, detail="; ".join(review_reasons))
        if product.currency != "USD":
            raise HTTPException(
                status_code=409, detail="PayPal Sandbox checkout currently supports USD offers"
            )
        existing = await session.scalar(
            select(PaymentTransaction).where(
                PaymentTransaction.procurement_request_id == request_id,
                PaymentTransaction.product_candidate_id == product.id,
                PaymentTransaction.status == "CREATED",
            )
        )
        if existing is not None and existing.approval_url:
            return CheckoutOrder(
                payment_id=existing.id,
                paypal_order_id=existing.paypal_order_id,
                approval_url=existing.approval_url,
                status=existing.status,
                amount=existing.amount,
                currency=existing.currency,
            )

        quantity = int((procurement_request.structured_requirements or {}).get("quantity", 1))
        quantity = max(quantity, 1)
        amount = (Decimal(product.price) * quantity).quantize(Decimal("0.01"))
        payment = PaymentTransaction(
            procurement_request_id=request_id,
            product_candidate_id=product.id,
            paypal_order_id=f"pending-{uuid4()}",
            status="CREATING",
            currency=product.currency,
            amount=amount,
            quantity=quantity,
        )
        session.add(payment)
        await session.flush()
        payment_id = payment.id
        # Persist the id before calling PayPal so every external order has an ARC audit record.
        await session.commit()

    return_url = f"{settings.frontend_origin}/?requestId={request_id}&paypal=return"
    cancel_url = f"{settings.frontend_origin}/?requestId={request_id}&paypal=cancel"
    try:
        paypal_order_id, approval_url = await client.create_order(
            payment_id=payment_id,
            product_name=product.name,
            amount=amount,
            currency=product.currency,
            return_url=return_url,
            cancel_url=cancel_url,
        )
    except PayPalError as exc:
        async with session_factory() as session:
            failed_payment = await session.get(PaymentTransaction, payment_id)
            if failed_payment is not None:
                failed_payment.status = "FAILED"
                await session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    async with session_factory() as session:
        created_payment = await session.get(PaymentTransaction, payment_id)
        if created_payment is None:
            raise HTTPException(status_code=500, detail="ARC could not persist the payment order")
        created_payment.paypal_order_id = paypal_order_id
        created_payment.approval_url = approval_url
        created_payment.status = "CREATED"
        await record_event(
            session,
            request_id,
            "payment.order_created",
            {"provider": "paypal", "mode": "sandbox"},
        )
        await session.commit()
    return CheckoutOrder(
        payment_id=payment_id,
        paypal_order_id=paypal_order_id,
        approval_url=approval_url,
        status="CREATED",
        amount=amount,
        currency=product.currency,
    )


@router.post("/{request_id}/checkout/{paypal_order_id}/capture", response_model=PaymentOut)
async def capture_checkout_order(
    request_id: UUID, paypal_order_id: str, request: Request
) -> PaymentOut:
    """Capture the order server-side after PayPal redirects an approving buyer back."""
    client = paypal_client()
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        payment = await session.scalar(
            select(PaymentTransaction).where(
                PaymentTransaction.procurement_request_id == request_id,
                PaymentTransaction.paypal_order_id == paypal_order_id,
            )
        )
        if payment is None:
            raise HTTPException(status_code=404, detail="PayPal order not found for this request")
        if payment.status == "COMPLETED":
            return PaymentOut(
                id=payment.id,
                product_candidate_id=payment.product_candidate_id,
                paypal_order_id=payment.paypal_order_id,
                paypal_capture_id=payment.paypal_capture_id,
                status=payment.status,
                amount=payment.amount,
                currency=payment.currency,
                quantity=payment.quantity,
            )
        payment_id = payment.id

    try:
        capture_id, capture_status = await client.capture_order(
            payment_id=payment_id, paypal_order_id=paypal_order_id
        )
    except PayPalError as exc:
        async with session_factory() as session:
            payment = await session.get(PaymentTransaction, payment_id)
            if payment is not None:
                payment.status = "CAPTURE_FAILED"
                await record_event(
                    session, request_id, "payment.capture_failed", {"provider": "paypal"}
                )
                await session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    async with session_factory() as session:
        payment = await session.get(PaymentTransaction, payment_id)
        procurement_request = await session.get(ProcurementRequest, request_id)
        if payment is None or procurement_request is None:
            raise HTTPException(status_code=404, detail="ARC payment record is unavailable")
        payment.paypal_capture_id = capture_id
        payment.status = capture_status
        procurement_request.status = "COMPLETED"
        await record_event(
            session, request_id, "payment.completed", {"provider": "paypal", "mode": "sandbox"}
        )
        await session.commit()
        return PaymentOut(
            id=payment.id,
            product_candidate_id=payment.product_candidate_id,
            paypal_order_id=payment.paypal_order_id,
            paypal_capture_id=payment.paypal_capture_id,
            status=payment.status,
            amount=payment.amount,
            currency=payment.currency,
            quantity=payment.quantity,
        )
