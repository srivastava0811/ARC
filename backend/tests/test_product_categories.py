from decimal import Decimal

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.evaluator import evaluate_candidate
from app.agents.planner import plan_request
from app.api.routes import requests as request_routes
from app.core.config import Settings
from app.db.base import Base
from app.db.models import ProductCandidate
from app.main import create_app
from app.providers.channel3 import Channel3Provider
from app.services import workflow


@pytest.mark.parametrize(
    "message,category,quantity",
    [
        ("I need 4 wireless keyboards under $200", "computer_keyboard", 4),
        ("Five computer mice under $100", "computer_mouse", 5),
        ("I need one wired mouse under $20", "computer_mouse", 1),
    ],
)
def test_peripherals_do_not_require_a_screen_size(message, category, quantity):
    requirements = plan_request(message)
    assert requirements["category"] == category
    assert requirements["quantity"] == quantity
    assert not requirements["requires_clarification"]
    assert requirements["required_screen_size_inches"] is None


@pytest.mark.parametrize(
    "message", ["I need 3 printers under $600", "I need 3 keyboards and mice under $100"]
)
def test_unsupported_or_mixed_categories_require_clarification(message):
    requirements = plan_request(message)
    assert requirements["category"] is None
    assert requirements["requires_clarification"]


def test_peripheral_connection_must_be_verified_without_monitor_price_floor():
    requirements = plan_request("I need 4 wireless keyboards under $100")
    candidate = ProductCandidate(
        provider="channel3",
        name="Keyboard",
        price=Decimal("15"),
        specifications={"product_category": "computer_keyboard", "connections": ["wired"]},
    )
    result = evaluate_candidate(candidate, requirements)
    assert not result.eligible
    assert all("low catalog price" not in reason for reason in result.rejection_reasons)
    candidate.specifications = {**candidate.specifications, "connections": ["wireless"]}
    assert evaluate_candidate(candidate, requirements).eligible


def test_bluetooth_request_is_not_satisfied_by_generic_wireless_evidence():
    requirements = plan_request("I need 2 Bluetooth mice under $100")
    candidate = ProductCandidate(
        provider="channel3",
        name="Mouse",
        price=Decimal("20"),
        specifications={"product_category": "computer_mouse", "connections": ["wireless"]},
    )
    assert not evaluate_candidate(candidate, requirements).eligible
    candidate.specifications = {
        **candidate.specifications,
        "connections": ["wireless", "bluetooth"],
    }
    assert evaluate_candidate(candidate, requirements).eligible


@pytest.mark.parametrize(
    "category,slug,noun",
    [
        ("computer_keyboard", "keyboards", "Keyboard"),
        ("computer_mouse", "mice-trackballs", "Mouse"),
    ],
)
async def test_channel3_uses_peripheral_category_and_preserves_connection_evidence(
    category, slug, noun
):
    def handler(request):
        import json

        payload = json.loads(request.content)
        assert payload["filters"]["category_ids"] == [slug]
        assert "-inch" not in payload["query"]
        return httpx.Response(
            200,
            json={
                "products": [
                    {
                        "id": "correct",
                        "title": f"Wireless {noun}",
                        "category": {"slug": slug},
                        "offers": [
                            {
                                "url": "https://merchant.example/device",
                                "domain": "merchant.example",
                                "price": {"price": 15, "currency": "USD"},
                                "availability": "InStock",
                                "condition": "new",
                            }
                        ],
                    },
                    {
                        "id": "wrong",
                        "title": "27-inch Monitor",
                        "category": {"slug": "computer-monitors"},
                        "offers": [],
                    },
                ]
            },
        )

    provider = Channel3Provider(
        api_key="test", base_url="https://api.example", transport=httpx.MockTransport(handler)
    )
    products = await provider.search(
        {
            "category": category,
            "quantity": 4,
            "maximum_total_budget": "100",
            "required_connection": "wireless",
        }
    )
    assert len(products) == 1
    assert products[0].specifications["product_category"] == category
    assert products[0].specifications["connections"] == ["wireless"]
    assert products[0].specifications["price_requires_verification"] is False


@pytest.mark.parametrize(
    "message,category",
    [
        ("I need 3 27-inch monitors under $600", "computer_monitor"),
        ("I need 4 wireless keyboards under $200", "computer_keyboard"),
        ("I need 5 wired mice under $100", "computer_mouse"),
    ],
)
async def test_category_workflow_checkout_and_receipt_with_mock_paypal(
    monkeypatch, message, category
):
    settings = Settings(_env_file=None, database_url="sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(workflow, "get_settings", lambda: settings)
    monkeypatch.setattr(request_routes, "get_settings", lambda: settings)

    class FakePayPal:
        async def create_order(self, **kwargs):
            return "TEST-ORDER", "https://sandbox.example/approve"

        async def capture_order(self, **kwargs):
            return "TEST-CAPTURE", "COMPLETED"

    monkeypatch.setattr(request_routes, "paypal_client", lambda: FakePayPal())
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with app.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/v1/requests", json={"message": message})
            assert created.status_code == 202
            path = f"/api/v1/requests/{created.json()['id']}"
            request = (await client.get(path)).json()
            assert request["status"] == "AWAITING_APPROVAL"
            assert request["structured_requirements"]["category"] == category
            quantity = request["structured_requirements"]["quantity"]
            products = (await client.get(path + "/products")).json()
            product = next(
                p for p in products if p["id"] == request["report"]["recommended_product_id"]
            )
            order = await client.post(
                path + "/checkout", json={"product_candidate_id": product["id"]}
            )
            assert order.status_code == 200
            assert Decimal(order.json()["amount"]) == Decimal(product["price"]) * quantity
            captured = await client.post(path + "/checkout/TEST-ORDER/capture")
            assert captured.status_code == 200
            receipt = (await client.get(path + "/receipt")).json()
            assert receipt["quantity"] == quantity
            assert receipt["product_name"] == product["name"]
            assert receipt["payment_status"] == "COMPLETED"
