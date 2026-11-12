import asyncio

from app.core.config import Settings
from app.providers import create_product_provider


async def main() -> None:
    settings = Settings()
    if settings.catalog_provider != "channel3":
        raise SystemExit("Set CATALOG_PROVIDER=channel3 before running this verification")
    provider = create_product_provider(settings)
    try:
        products = await provider.search(
            {
                "category": "computer_monitor",
                "quantity": 3,
                "maximum_total_budget": "600",
                "required_screen_size_inches": 27,
                "preferences": ["reliability", "warranty coverage", "display quality"],
            }
        )
    except Exception as exc:
        print(f"Channel3 verification failed: {type(exc).__name__}: {exc}")
        raise SystemExit(1) from None
    print(f"Channel3 verification succeeded: {len(products)} normalized product(s)")
    for product in products[:3]:
        print(
            f"- {product.name} | {product.merchant} | "
            f"{product.currency} {product.price} | "
            f"screen={product.specifications['screen_size_inches']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
