from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DemoProduct:
    external_id: str
    name: str
    brand: str
    price: Decimal
    screen_size: int
    resolution: str
    warranty: str | None


CATALOG = (
    DemoProduct(
        "studio-27", "StudioView 27 4K", "Northstar", Decimal("189.00"), 27, "4K UHD", None
    ),
    DemoProduct("viewpro-27", "ViewPro Q27", "Aster", Decimal("229.00"), 27, "QHD", "2 years"),
    DemoProduct(
        "essential-24", "Essential Display 24", "Meridian", Decimal("119.00"), 24, "FHD", "1 year"
    ),
    DemoProduct(
        "clarity-27", "ClarityPanel 27", "Lumen", Decimal("265.00"), 27, "4K UHD", "3 years"
    ),
)


def search_monitors() -> tuple[DemoProduct, ...]:
    """Explicit synthetic catalog; it is never substituted for a failed live provider."""
    return CATALOG
