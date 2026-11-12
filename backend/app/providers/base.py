from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class NormalizedProduct:
    external_id: str
    name: str
    brand: str | None
    merchant: str | None
    price: Decimal
    currency: str
    product_url: str | None
    image_url: str | None
    specifications: dict
    metadata: dict = field(default_factory=dict)


class ProductProvider(Protocol):
    name: str

    async def search(self, requirements: dict) -> list[NormalizedProduct]: ...
