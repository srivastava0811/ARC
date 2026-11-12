from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.evaluator import evaluate_candidate
from app.agents.planner import plan_request
from app.api.routes import requests as request_routes
from app.core.config import Settings
from app.db.base import Base
from app.db.models import Evaluation, ProcurementRequest, ProductCandidate, Workspace
from app.main import create_app


def candidate(price: str, name: str = "Acme 27-inch Monitor") -> ProductCandidate:
    return ProductCandidate(
        id=uuid4(),
        external_product_id="test",
        name=name,
        provider="channel3",
        price=Decimal(price),
        currency="USD",
        specifications={"screen_size_inches": 27},
    )


@pytest.mark.parametrize(
    "price,eligible", [("5", False), ("6", False), ("69.99", True), ("72", False)]
)
def test_seven_monitor_request_checks_unit_price_and_actual_total(price, eligible):
    requirements = plan_request("I need 7 27-inch monitors under $500.")
    assert requirements["quantity"] == 7
    result = evaluate_candidate(candidate(price), requirements)
    assert result.eligible is eligible
    assert result.score_breakdown["budget_headroom"] == str(Decimal("500") - Decimal(price) * 7)


def test_privacy_filter_is_not_a_monitor():
    result = evaluate_candidate(
        candidate("63.99", "Privacy Filter for 27 in. Apple iMac"),
        plan_request("I need 7 27-inch monitors under $500."),
    )
    assert not result.eligible
    assert any("accessory" in reason for reason in result.rejection_reasons)


async def test_old_low_price_recommendation_is_flagged_and_cannot_be_checked_out(monkeypatch):
    settings = Settings(
        _env_file=None,
        database_url="sqlite+aiosqlite:///:memory:",
        paypal_client_id="test",
        paypal_client_secret="test",
    )
    monkeypatch.setattr(request_routes, "get_settings", lambda: settings)
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with app.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with app.state.session_factory() as session:
            workspace = Workspace(id=uuid4(), slug="test", name="Test")
            request = ProcurementRequest(
                id=uuid4(),
                workspace_id=workspace.id,
                status="AWAITING_APPROVAL",
                original_prompt="I need 7 27-inch monitors under $500.",
                structured_requirements=plan_request("I need 7 27-inch monitors under $500."),
            )
            product = candidate("5")
            product.procurement_request_id = request.id
            evaluation = Evaluation(
                procurement_request_id=request.id,
                product_candidate_id=product.id,
                eligible=True,
                score=Decimal("88.6"),
                rejection_reasons=[],
                explanation="Old result",
            )
            session.add_all([workspace, request, product, evaluation])
            await session.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            products = await client.get(f"/api/v1/requests/{request.id}/products")
            assert products.json()[0]["specifications"]["price_requires_verification"] is True
            evaluations = await client.get(f"/api/v1/requests/{request.id}/evaluations")
            assert evaluations.json()[0]["eligible"] is False
            assert evaluations.json()[0]["score"] is None
            checkout = await client.post(
                f"/api/v1/requests/{request.id}/checkout",
                json={"product_candidate_id": str(product.id)},
            )
            assert checkout.status_code == 409
            assert "verification" in checkout.json()["detail"]
