from app.core.catalog import PRODUCT_CATEGORIES
from app.providers.base import NormalizedProduct, ProductProvider
from app.services.demo_catalog import DemoProduct, search_monitors


def research_demo_catalog(requirements: dict) -> tuple[DemoProduct, ...]:
    """Research through the configured synthetic provider; no silent live-provider fallback."""
    if requirements["category"] != "computer_monitor":
        return ()
    return search_monitors()


async def research_catalog(
    provider: ProductProvider, requirements: dict
) -> list[NormalizedProduct]:
    """Search only the explicitly configured provider; never fall back silently."""
    if requirements["category"] not in PRODUCT_CATEGORIES:
        return []
    return await provider.search(requirements)
