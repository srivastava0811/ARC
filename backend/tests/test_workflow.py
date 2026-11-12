from decimal import Decimal

from app.agents.planner import PlannedRequirements, plan_request, plan_request_with_gemini
from app.services.demo_catalog import search_monitors


def test_planner_extracts_the_demo_request_requirements() -> None:
    result = plan_request("Find three 27-inch monitors for our office under $600 total.")

    assert result["quantity"] == 3
    assert result["maximum_total_budget"] == "600"
    assert result["category"] == "computer_monitor"
    assert result["required_screen_size_inches"] == 27
    assert result["requires_clarification"] is False


def test_demo_catalog_contains_ineligible_candidates_for_real_evaluation() -> None:
    products = search_monitors()

    assert any(product.screen_size != 27 for product in products)
    assert any(product.price * 3 > 600 for product in products)


async def test_gemini_planner_derives_clarification_from_validated_fields(monkeypatch) -> None:
    async def fake_generate_structured(**kwargs):
        return PlannedRequirements(
            quantity=3,
            maximum_total_budget=Decimal("600"),
            required_screen_size_inches=None,
            preferences=["reliability"],
        )

    monkeypatch.setattr("app.agents.planner.generate_structured", fake_generate_structured)

    result = await plan_request_with_gemini("Three monitors under $600", "key", "model")

    assert result["maximum_total_budget"] == "600"
    assert result["missing_information"] == ["screen size"]
    assert result["requires_clarification"] is True
