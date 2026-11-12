"""Product catalog provider adapters."""

from app.core.config import Settings
from app.providers.base import ProductProvider
from app.providers.channel3 import Channel3Provider
from app.providers.demo import DemoCatalogProvider


def create_product_provider(settings: Settings) -> ProductProvider:
    if settings.catalog_provider == "channel3":
        if settings.channel3_api_key is None:
            raise ValueError("Channel3 API key is not configured")
        return Channel3Provider(
            api_key=settings.channel3_api_key.get_secret_value(),
            base_url=settings.channel3_base_url,
            limit=settings.channel3_search_limit,
            minimum_monitor_price=settings.channel3_minimum_monitor_price,
        )
    return DemoCatalogProvider()
