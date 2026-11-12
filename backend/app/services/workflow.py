import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agents.evaluator import evaluate_candidate, explain_evaluations_with_gemini
from app.agents.planner import plan_request
from app.agents.reporter import create_initial_report, create_report_with_gemini
from app.agents.research import research_catalog
from app.core.config import get_settings
from app.db.models import (
    AgentExecution,
    ConversationMessage,
    Evaluation,
    ProcurementReport,
    ProcurementRequest,
    ProductCandidate,
    WorkflowEvent,
    Workspace,
)
from app.providers import create_product_provider

logger = logging.getLogger(__name__)


async def _event(session, request_id: UUID, event_type: str, payload: dict) -> None:
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


async def _agent(
    session, request_id: UUID, name: str, mode: str, model_name: str
) -> AgentExecution:
    execution = AgentExecution(
        procurement_request_id=request_id,
        agent_name=name,
        status="RUNNING",
        model_name=model_name,
    )
    session.add(execution)
    await session.flush()
    await _event(
        session,
        request_id,
        "agent.started",
        {"agent": name, "mode": mode, "model": model_name},
    )
    return execution


async def _complete(session, request_id: UUID, execution: AgentExecution) -> None:
    execution.status, execution.completed_at = "COMPLETED", datetime.now(UTC)
    await _event(session, request_id, "agent.completed", {"agent": execution.agent_name})


async def _degrade(session, request_id: UUID, execution: AgentExecution, message: str) -> None:
    execution.status = "DEGRADED"
    execution.completed_at = datetime.now(UTC)
    execution.error_message = message
    await _event(
        session,
        request_id,
        "agent.degraded",
        {"agent": execution.agent_name, "message": message},
    )


async def run_demo_workflow(session_factory: async_sessionmaker, request_id: UUID) -> None:
    try:
        await _run_workflow(session_factory, request_id)
    except Exception:
        logger.exception("Procurement workflow failed", extra={"request_id": str(request_id)})
        async with session_factory() as session:
            request = await session.get(ProcurementRequest, request_id)
            if request is not None:
                request.status = "FAILED"
                await _event(
                    session,
                    request_id,
                    "workflow.failed",
                    {"message": "The agent workflow could not be completed."},
                )
                await session.commit()


async def _run_workflow(session_factory: async_sessionmaker, request_id: UUID) -> None:
    settings = get_settings()
    product_provider = create_product_provider(settings)
    gemini_api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None
    async with session_factory() as session:
        request = await session.get(ProcurementRequest, request_id)
        if request is None or request.status != "CREATED":
            return
        request.status = "PLANNING"
        await _event(session, request_id, "workflow.started", {"mode": settings.agent_mode})
        planner = await _agent(session, request_id, "planner", "deterministic", "rule-based parser")
        clarifications = (
            await session.scalars(
                select(ConversationMessage.content)
                .where(
                    ConversationMessage.procurement_request_id == request_id,
                    ConversationMessage.role == "user_clarification",
                )
                .order_by(ConversationMessage.created_at)
            )
        ).all()
        combined_request = "\n".join([request.original_prompt, *clarifications])
        # A deterministic plan is intentionally the critical path. It lets ARC start
        # the live catalog search immediately instead of waiting on model latency.
        requirements = plan_request(combined_request)
        request.structured_requirements = requirements
        await _complete(session, request_id, planner)
        if requirements["requires_clarification"]:
            request.status = "NEEDS_CLARIFICATION"
            await _event(
                session,
                request_id,
                "planner.clarification_required",
                {"missing": requirements["missing_information"]},
            )
            await session.commit()
            return
        request.status = "RESEARCHING"
        researcher = await _agent(
            session,
            request_id,
            "research",
            settings.catalog_provider,
            settings.model_for_agent("research"),
        )
        # Commit the stage change before the potentially slow live-provider request so
        # the workspace can accurately show that research is underway.
        await session.commit()
        products = await research_catalog(product_provider, requirements)
        for product in products:
            session.add(
                ProductCandidate(
                    procurement_request_id=request_id,
                    external_product_id=product.external_id,
                    provider=product_provider.name,
                    name=product.name,
                    brand=product.brand,
                    merchant=product.merchant,
                    price=product.price,
                    currency=product.currency,
                    product_url=product.product_url,
                    image_url=product.image_url,
                    specifications=product.specifications,
                    metadata_json=product.metadata,
                )
            )
        await _complete(session, request_id, researcher)
        await session.flush()
        await _event(
            session,
            request_id,
            "research.products_found",
            {"count": len(products), "provider": product_provider.name},
        )
        request.status = "EVALUATING"
        evaluator = await _agent(
            session,
            request_id,
            "evaluator",
            "deterministic",
            "rule-based evaluator",
        )
        candidates = (
            await session.scalars(
                select(ProductCandidate).where(
                    ProductCandidate.procurement_request_id == request_id
                )
            )
        ).all()
        results = []
        for candidate in candidates:
            result = evaluate_candidate(
                candidate, requirements, settings.channel3_minimum_monitor_price
            )
            results.append(result)
            session.add(
                Evaluation(
                    procurement_request_id=request_id,
                    product_candidate_id=candidate.id,
                    eligible=result.eligible,
                    score=result.score,
                    score_breakdown=result.score_breakdown,
                    rejection_reasons=result.rejection_reasons,
                    explanation=result.explanation,
                )
            )
        await _complete(session, request_id, evaluator)
        request.status = "GENERATING_REPORT"
        reporter = await _agent(
            session,
            request_id,
            "reporter",
            "deterministic",
            "rule-based report",
        )
        report = create_initial_report(results, settings.catalog_provider)
        await _complete(session, request_id, reporter)
        initial_report = ProcurementReport(
            procurement_request_id=request_id, report_type="INITIAL", structured_content=report
        )
        session.add(initial_report)
        request.status = "AWAITING_APPROVAL" if report["eligible_count"] else "COMPLETED"
        await _event(
            session,
            request_id,
            "approval.required" if report["eligible_count"] else "workflow.completed",
            {"eligible_count": report["eligible_count"]},
        )
        # The deterministic recommendation is now durable and immediately usable.
        # Gemini only enriches explanations and the report; it never blocks the
        # decision, catalog cards, or PayPal approval path.
        await session.commit()

        if settings.agent_mode != "gemini" or not gemini_api_key:
            return

        evaluator_enrichment = await _agent(
            session,
            request_id,
            "evaluator enrichment",
            "gemini",
            settings.gemini_evaluator_model,
        )
        reporter_enrichment = await _agent(
            session,
            request_id,
            "reporter enrichment",
            "gemini",
            settings.gemini_reporter_model,
        )
        await session.commit()

        evaluation_outcome, report_outcome = await asyncio.gather(
            explain_evaluations_with_gemini(
                results, requirements, gemini_api_key, settings.gemini_evaluator_model
            ),
            create_report_with_gemini(
                results,
                gemini_api_key,
                settings.gemini_reporter_model,
                settings.catalog_provider,
            ),
            return_exceptions=True,
        )

        if isinstance(evaluation_outcome, Exception):
            logger.warning(
                "Gemini evaluator enrichment unavailable; deterministic explanations retained",
                exc_info=evaluation_outcome,
            )
            await _degrade(
                session,
                request_id,
                evaluator_enrichment,
                "Gemini explanation unavailable; deterministic evaluation retained.",
            )
        else:
            pending_evaluations = (
                await session.scalars(
                    select(Evaluation).where(Evaluation.procurement_request_id == request_id)
                )
            ).all()
            explanations = {item.candidate.id: item.explanation for item in evaluation_outcome}
            for evaluation in pending_evaluations:
                evaluation.explanation = explanations[evaluation.product_candidate_id]
            await _complete(session, request_id, evaluator_enrichment)

        if isinstance(report_outcome, Exception):
            logger.warning(
                "Gemini reporter enrichment unavailable; deterministic report retained",
                exc_info=report_outcome,
            )
            await _degrade(
                session,
                request_id,
                reporter_enrichment,
                "Gemini report unavailable; deterministic report retained.",
            )
        else:
            initial_report.structured_content = report_outcome
            await _complete(session, request_id, reporter_enrichment)
        await session.commit()


async def ensure_demo_workspace(session) -> Workspace:
    workspace = await session.scalar(select(Workspace).where(Workspace.slug == "demo"))
    if workspace is None:
        workspace = Workspace(slug="demo", name="ARC demo workspace")
        session.add(workspace)
        await session.flush()
    return workspace
