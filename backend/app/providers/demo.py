from decimal import Decimal

from app.providers.base import NormalizedProduct
from app.services.demo_catalog import search_monitors


class DemoCatalogProvider:
    name = "demo_catalog"

    async def search(self, requirements: dict) -> list[NormalizedProduct]:
        category = requirements["category"]
        peripherals = {
            "computer_keyboard": [
                ("wireless-keys", "Northstar Wireless Keyboard", "29.00", ["wireless"]),
                ("wired-keys", "Northstar Wired Keyboard", "19.00", ["wired"]),
            ],
            "computer_mouse": [
                ("wireless-mouse", "Northstar Wireless Mouse", "18.00", ["wireless"]),
                ("wired-mouse", "Northstar Wired Mouse", "12.00", ["wired"]),
            ],
        }
        if category in peripherals:
            return [
                NormalizedProduct(
                    external_id=product_id,
                    name=name,
                    brand="Northstar",
                    merchant="ARC demo catalog",
                    price=Decimal(price),
                    currency="USD",
                    product_url=None,
                    image_url=None,
                    specifications={
                        "product_category": category,
                        "connections": connections,
                        "warranty": None,
                        "synthetic_data": True,
                    },
                    metadata={"data_label": "Synthetic demo data"},
                )
                for product_id, name, price, connections in peripherals[category]
            ]
        if requirements["category"] != "computer_monitor":
            return []
        return [
            NormalizedProduct(
                external_id=product.external_id,
                name=product.name,
                brand=product.brand,
                merchant="ARC demo catalog",
                price=product.price,
                currency="USD",
                product_url=None,
                image_url=None,
                specifications={
                    "screen_size_inches": product.screen_size,
                    "resolution": product.resolution,
                    "warranty": product.warranty,
                    "synthetic_data": True,
                },
                metadata={"data_label": "Synthetic demo data"},
            )
            for product in search_monitors()
        ]
