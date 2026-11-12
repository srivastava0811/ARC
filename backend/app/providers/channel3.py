import re
from decimal import Decimal

import httpx
from pydantic import AliasChoices, BaseModel, Field

from app.core.catalog import PRODUCT_CATEGORIES
from app.providers.base import NormalizedProduct


class Channel3ProviderError(RuntimeError):
    """Safe, user-displayable Channel3 provider failure."""


class Channel3Price(BaseModel):
    amount: Decimal = Field(validation_alias=AliasChoices("price", "amount"))
    currency: str


class Channel3Category(BaseModel):
    slug: str
    path: list[dict[str, str]] = Field(default_factory=list)


class Channel3Offer(BaseModel):
    url: str
    domain: str
    price: Channel3Price
    availability: str
    condition: str | None = None
    max_commission_rate: float = 0


class Channel3Image(BaseModel):
    url: str
    cleaned_url: str | None = None
    is_main_image: bool = False


class Channel3Brand(BaseModel):
    id: str | None = None
    name: str


class Channel3Product(BaseModel):
    id: str
    title: str
    description: str | None = None
    brands: list[Channel3Brand] = Field(default_factory=list)
    images: list[Channel3Image] = Field(default_factory=list)
    key_features: list[str] | None = None
    structured_attributes: dict[str, list[str]] = Field(default_factory=dict)
    offers: list[Channel3Offer] = Field(default_factory=list)
    category: Channel3Category | None = None


class Channel3SearchResponse(BaseModel):
    products: list[Channel3Product]


def _evidence_text(product: Channel3Product) -> str:
    attributes = [value for values in product.structured_attributes.values() for value in values]
    return " ".join(
        [product.title, product.description or "", *(product.key_features or []), *attributes]
    )


def _screen_size(product: Channel3Product) -> int | None:
    match = re.search(
        r"\b(\d{2})(?:\.0)?\s*(?:-| )?(?:inch(?:es)?\b|in\.?\b|\")",
        _evidence_text(product),
        re.I,
    )
    return int(match.group(1)) if match else None


def _resolution(product: Channel3Product) -> str | None:
    match = re.search(
        r"\b(8K|5K|4K(?:\s+UHD)?|UHD|WQHD|QHD|FHD|1080P|1440P|2160P)\b",
        _evidence_text(product),
        re.I,
    )
    return match.group(1).upper() if match else None


def _warranty(product: Channel3Product) -> str | None:
    match = re.search(
        r"\b(\d+\s*[- ]?years?)\s+(?:limited\s+)?warranty\b",
        _evidence_text(product),
        re.I,
    )
    return match.group(1) if match else None


class Channel3Provider:
    name = "channel3"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        limit: int = 12,
        minimum_monitor_price: Decimal = Decimal("50.00"),
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.limit = limit
        self.transport = transport
        self.minimum_monitor_price = minimum_monitor_price

    async def search(self, requirements: dict) -> list[NormalizedProduct]:
        quantity = int(requirements["quantity"])
        maximum_unit_price = Decimal(requirements["maximum_total_budget"]) / quantity
        category = requirements.get("category", "computer_monitor")
        if category not in PRODUCT_CATEGORIES:
            return []
        definition = PRODUCT_CATEGORIES[category]
        minimum_price = (
            self.minimum_monitor_price if category == "computer_monitor" else Decimal("0")
        )
        size = requirements.get("required_screen_size_inches")
        preferences = " ".join(requirements.get("preferences", []))
        size_query = f"{size}-inch " if category == "computer_monitor" and size else ""
        connection = requirements.get("required_connection") or ""
        query = f"{size_query}{connection} {definition['query']} {preferences}".strip()
        payload = {
            "query": query,
            "limit": self.limit,
            "filters": {
                "category_ids": [definition["catalog_slug"]],
                "conditions": ["new"],
                "availability": ["InStock"],
                "price": {"max_price": float(maximum_unit_price)},
            },
            "config": {"country": "US", "currency": "USD", "mode": "default"},
        }
        try:
            async with httpx.AsyncClient(timeout=25, transport=self.transport) as client:
                response = await client.post(
                    f"{self.base_url}/v1/search",
                    headers={"x-api-key": self.api_key, "content-type": "application/json"},
                    json=payload,
                )
            response.raise_for_status()
            search_response = Channel3SearchResponse.model_validate(response.json())
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise Channel3ProviderError(f"Channel3 search failed with status {status}") from None
        except (httpx.HTTPError, ValueError) as exc:
            raise Channel3ProviderError(
                f"Channel3 search could not be completed ({type(exc).__name__})"
            ) from None

        normalized: list[NormalizedProduct] = []
        for product in search_response.products:
            if product.category is not None:
                categories = {
                    product.category.slug,
                    *(item["slug"] for item in product.category.path),
                }
                if definition["catalog_slug"] not in categories:
                    continue
            elif category != "computer_monitor":
                # Without category evidence, do not guess that an accessory is a device.
                continue
            if re.search(
                r"\b(privacy filter|screen protector|monitor (?:arm|stand|mount)"
                r"|replacement screen|keycaps?|keyboard kit|mouse pad|mousepad|wrist rest)\b",
                product.title,
                re.I,
            ):
                continue
            offers = [
                offer
                for offer in product.offers
                if offer.availability == "InStock"
                and offer.condition in {None, "new"}
                and offer.price.currency == "USD"
                and offer.price.amount > 0
            ]
            if not offers:
                continue
            # Prefer offers above the review threshold. A low catalog price is not
            # proof of a deal, and must not outrank an otherwise usable offer.
            reviewable_offers = [offer for offer in offers if offer.price.amount >= minimum_price]
            offer = min(reviewable_offers or offers, key=lambda item: item.price.amount)
            price_requires_verification = offer.price.amount < minimum_price
            evidence = _evidence_text(product)
            connections = []
            if re.search(r"\b(wireless|bluetooth|2\.4\s*g(?:hz)?)\b", evidence, re.I):
                connections.append("wireless")
            if re.search(r"\bbluetooth\b", evidence, re.I):
                connections.append("bluetooth")
            if re.search(r"\bwired\b", evidence, re.I):
                connections.append("wired")
            images = sorted(product.images, key=lambda item: item.is_main_image, reverse=True)
            image_url = (images[0].cleaned_url or images[0].url) if images else None
            normalized.append(
                NormalizedProduct(
                    external_id=product.id,
                    name=product.title,
                    brand=product.brands[0].name if product.brands else None,
                    merchant=offer.domain,
                    price=offer.price.amount,
                    currency=offer.price.currency,
                    product_url=offer.url,
                    image_url=image_url,
                    specifications={
                        "product_category": category,
                        "connections": connections,
                        "screen_size_inches": _screen_size(product),
                        "resolution": _resolution(product),
                        "warranty": _warranty(product),
                        "key_features": product.key_features or [],
                        "structured_attributes": product.structured_attributes,
                        "synthetic_data": False,
                        "price_requires_verification": price_requires_verification,
                        "price_review_threshold": str(minimum_price),
                    },
                    metadata={
                        "data_label": "Live Channel3 catalog data",
                        "offer_count": len(product.offers),
                        "selected_offer_domain": offer.domain,
                        "max_commission_rate": offer.max_commission_rate,
                        "category": product.category.slug if product.category else None,
                    },
                )
            )
        return normalized
