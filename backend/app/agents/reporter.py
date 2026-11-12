import json

from pydantic import BaseModel, Field

from app.agents.evaluator import EvaluationResult
from app.agents.gemini import generate_structured


class ReportNarrative(BaseModel):
    summary: str
    limitations: list[str] = Field(min_length=1)


def create_initial_report(
    evaluations: list[EvaluationResult], catalog_provider: str = "demo_catalog"
) -> dict:
    ranked = sorted(
        (item for item in evaluations if item.eligible),
        key=lambda item: item.score or 0,
        reverse=True,
    )
    is_live = catalog_provider == "channel3"
    return {
        "mode": "demo" if not is_live else "channel3",
        "catalog_provider": catalog_provider,
        "summary": (
            "Recommendations were generated from live Channel3 catalog offers."
            if is_live
            else "Recommendations were generated from synthetic demo catalog data."
        ),
        "recommended_product_id": str(ranked[0].candidate.id) if ranked else None,
        "eligible_count": len(ranked),
        "no_eligible_products": not bool(ranked),
        "limitations": (
            [
                "Prices and availability can change at the merchant.",
                "Warranty details are only considered when present in catalog evidence.",
            ]
            if is_live
            else [
                "Prices and warranty data are synthetic demo data.",
                "No merchant purchase offer is implied.",
            ]
        ),
    }


async def create_report_with_gemini(
    evaluations: list[EvaluationResult], api_key: str, model: str, catalog_provider: str
) -> dict:
    report = create_initial_report(evaluations, catalog_provider)
    evidence = [
        {
            "name": item.candidate.name,
            "eligible": item.eligible,
            "score": str(item.score) if item.score is not None else None,
            "explanation": item.explanation,
        }
        for item in evaluations
    ]
    narrative = await generate_structured(
        api_key=api_key,
        model=model,
        system_instruction=(
            "You are ARC's procurement reporter. Summarize the supplied evaluated options for "
            "a business user. Do not invent product facts or alter the recommendation. "
            f"The catalog provider is {catalog_provider}. "
            "Channel3 data is live merchant-offer data; demo_catalog data is synthetic."
        ),
        prompt=json.dumps(
            {
                "recommended_product_id": report["recommended_product_id"],
                "eligible_count": report["eligible_count"],
                "evaluations": evidence,
            }
        ),
        response_schema=ReportNarrative,
    )
    report["mode"] = "gemini"
    report["summary"] = narrative.summary
    report["limitations"] = list(
        dict.fromkeys([*narrative.limitations, *report["limitations"]])
    )
    return report
