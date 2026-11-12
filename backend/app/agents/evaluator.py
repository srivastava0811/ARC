import json
import re
from dataclasses import dataclass, replace
from decimal import Decimal

from pydantic import BaseModel

from app.agents.gemini import generate_structured
from app.db.models import ProductCandidate


@dataclass(frozen=True)
class EvaluationResult:
    candidate: ProductCandidate
    eligible: bool
    score: Decimal | None
    score_breakdown: dict
    rejection_reasons: list[str]
    explanation: str


class CandidateNarrative(BaseModel):
    product_candidate_id: str
    explanation: str


class EvaluationNarratives(BaseModel):
    candidates: list[CandidateNarrative]


def catalog_review_reasons(
    candidate: ProductCandidate, minimum_monitor_price: Decimal = Decimal("50.00")
) -> list[str]:
    if candidate.provider != "channel3":
        return []
    if candidate.specifications.get("product_category", "computer_monitor") != "computer_monitor":
        return []
    reasons = []
    if candidate.price < minimum_monitor_price:
        reasons.append(
            "Unusually low catalog price requires merchant verification; "
            "excluded from recommendations and checkout"
        )
    if re.search(
        r"\b(privacy filter|screen protector|monitor (?:arm|stand|mount)|replacement screen)\b",
        candidate.name,
        re.I,
    ):
        reasons.append("This catalog item is a monitor accessory, not a complete monitor")
    return reasons


def evaluate_candidate(
    candidate: ProductCandidate,
    requirements: dict,
    minimum_monitor_price: Decimal = Decimal("50.00"),
) -> EvaluationResult:
    """Apply hard constraints and only score evidence actually present in a record."""
    budget = Decimal(requirements["maximum_total_budget"])
    quantity = requirements["quantity"]
    category = requirements.get("category", "computer_monitor")
    total = candidate.price * quantity
    reasons = catalog_review_reasons(candidate, minimum_monitor_price)
    if candidate.specifications.get("product_category", "computer_monitor") != category:
        reasons.append("Catalog product category does not match the requested product")
    if category == "computer_monitor":
        required_size = requirements.get("required_screen_size_inches")
        actual_size = candidate.specifications.get("screen_size_inches")
        if actual_size is None:
            reasons.append("Screen size could not be verified from the catalog evidence")
        elif actual_size != required_size:
            reasons.append(f"Screen size is {actual_size} inches, not {required_size} inches")
    required_connection = requirements.get("required_connection")
    if required_connection and required_connection not in candidate.specifications.get(
        "connections", []
    ):
        reasons.append(f"Requested {required_connection} connection could not be verified")
    if total > budget:
        reasons.append(f"Quantity-adjusted total ${total:.2f} exceeds budget ${budget:.2f}")
    eligible = not reasons
    warranty_points = Decimal("10") if candidate.specifications.get("warranty") else Decimal("0")
    score = (
        (Decimal("70") + warranty_points + ((budget - total) / budget * Decimal("20"))).quantize(
            Decimal("0.01")
        )
        if eligible
        else None
    )
    return EvaluationResult(
        candidate=candidate,
        eligible=eligible,
        score=score,
        score_breakdown={
            "budget_headroom": str(budget - total),
            "warranty_points": str(warranty_points),
        },
        rejection_reasons=reasons,
        explanation="Eligible based on category, budget, and requested specification checks."
        if eligible
        else "; ".join(reasons),
    )


async def explain_evaluations_with_gemini(
    evaluations: list[EvaluationResult], requirements: dict, api_key: str, model: str
) -> list[EvaluationResult]:
    evidence = [
        {
            "product_candidate_id": str(item.candidate.id),
            "name": item.candidate.name,
            "price": str(item.candidate.price),
            "specifications": item.candidate.specifications,
            "eligible": item.eligible,
            "deterministic_score": str(item.score) if item.score is not None else None,
            "rejection_reasons": item.rejection_reasons,
        }
        for item in evaluations
    ]
    narratives = await generate_structured(
        api_key=api_key,
        model=model,
        system_instruction=(
            "You are ARC's procurement evaluator. Explain the supplied deterministic results "
            "using only the supplied evidence. You cannot change eligibility, scores, prices, "
            "specifications, or rejection reasons. Return one concise explanation per candidate."
        ),
        prompt=json.dumps({"requirements": requirements, "evaluations": evidence}),
        response_schema=EvaluationNarratives,
    )
    by_id = {item.product_candidate_id: item.explanation for item in narratives.candidates}
    expected_ids = {str(item.candidate.id) for item in evaluations}
    if set(by_id) != expected_ids:
        raise ValueError("Gemini evaluator did not return exactly one narrative per candidate")
    return [replace(item, explanation=by_id[str(item.candidate.id)]) for item in evaluations]
