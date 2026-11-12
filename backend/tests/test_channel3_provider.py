from decimal import Decimal

import httpx

from app.providers.channel3 import Channel3Provider


async def test_channel3_normalizes_the_best_live_offer() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"
        return httpx.Response(
            200,
            json={
                "products": [
                    {
                        "id": "channel-product-1",
                        "title": "Acme Vision 27-inch 4K Monitor",
                        "description": "Includes a 3 year warranty",
                        "brands": [{"id": "acme", "name": "Acme"}],
                        "images": [
                            {
                                "url": "https://images.example/monitor.jpg",
                                "cleaned_url": "https://images.example/monitor-clean.png",
                                "is_main_image": True,
                            }
                        ],
                        "offers": [
                            {
                                "url": "https://buy.example/monitor",
                                "domain": "merchant.example",
                                "price": {"price": 179.99, "currency": "USD"},
                                "availability": "InStock",
                                "condition": "new",
                            }
                        ],
                    }
                ]
            },
        )

    provider = Channel3Provider(
        api_key="test-key",
        base_url="https://api.trychannel3.com",
        transport=httpx.MockTransport(handler),
    )
    products = await provider.search(
        {
            "category": "computer_monitor",
            "quantity": 3,
            "maximum_total_budget": "600",
            "required_screen_size_inches": 27,
            "preferences": ["reliability"],
        }
    )

    assert len(products) == 1
    assert products[0].external_id == "channel-product-1"
    assert str(products[0].price) == "179.99"
    assert products[0].merchant == "merchant.example"
    assert products[0].specifications["screen_size_inches"] == 27
    assert products[0].specifications["resolution"] == "4K"
    assert products[0].specifications["warranty"] == "3 year"
    assert products[0].product_url == "https://buy.example/monitor"
    assert products[0].image_url == "https://images.example/monitor-clean.png"


async def test_channel3_excludes_accessories_and_prefers_a_reviewable_offer() -> None:
    def offer(price):
        return {
            "url": "https://merchant.example/monitor",
            "domain": "merchant.example",
            "price": {"price": price, "currency": "USD"},
            "availability": "InStock",
            "condition": "new",
        }

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        payload = json.loads(request.content)
        assert payload["filters"]["category_ids"] == ["computer-monitors"]
        return httpx.Response(
            200,
            json={
                "products": [
                    {
                        "id": "monitor",
                        "title": "Acme 27-inch Monitor",
                        "category": {"slug": "computer-monitors"},
                        "offers": [offer(5), offer(69.99)],
                    },
                    {
                        "id": "unverified",
                        "title": "Acme 27-inch Gaming Monitor",
                        "offers": [offer(6)],
                    },
                    {
                        "id": "accessory",
                        "title": "Privacy Filter for 27-inch Monitor",
                        "category": {"slug": "monitor-privacy-filters"},
                        "offers": [offer(63.99)],
                    },
                ]
            },
        )

    provider = Channel3Provider(
        api_key="test", base_url="https://api.example", transport=httpx.MockTransport(handler)
    )
    products = await provider.search(
        {"quantity": 7, "maximum_total_budget": "500", "required_screen_size_inches": 27}
    )
    assert [p.external_id for p in products] == ["monitor", "unverified"]
    assert products[0].price == Decimal("69.99")
    assert products[0].specifications["price_requires_verification"] is False
    assert products[1].specifications["price_requires_verification"] is True
