import re
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.gemini import generate_structured


class PlannedRequirements(BaseModel):
    category: Literal["computer_monitor", "computer_keyboard", "computer_mouse"] | None = (
        "computer_monitor"
    )
    quantity: int | None = Field(default=None, ge=1, le=100)
    maximum_total_budget: Decimal | None = None
    currency: str = "USD"
    required_screen_size_inches: int | None = Field(default=None, ge=10, le=100)
    preferences: list[str] = Field(default_factory=list)
    required_connection: Literal["wired", "wireless", "bluetooth"] | None = None


def missing_requirements(values: dict) -> list[str]:
    fields = [
        ("one supported product category (monitors, keyboards, or mice)", values.get("category")),
        ("quantity", values.get("quantity")),
        ("maximum total budget", values.get("maximum_total_budget")),
    ]
    if values.get("category") == "computer_monitor":
        fields.append(("screen size", values.get("required_screen_size_inches")))
    return [label for label, value in fields if value is None]


def plan_request(message: str) -> dict:
    """Extract deterministic baseline requirements; Gemini enhancement comes later."""
    categories = {
        "computer_monitor": r"\bmonitors?\b",
        "computer_keyboard": r"\bkeyboards?\b",
        "computer_mouse": r"\b(?:mouse|mice)\b",
    }
    # A clarification can select one category after an ambiguous original request.
    detected = []
    for line in reversed(message.splitlines()):
        detected = [key for key, pattern in categories.items() if re.search(pattern, line, re.I)]
        if detected:
            break
    category = detected[0] if len(detected) == 1 else None
    noun = categories[category] if category else r"\b(?:monitors?|keyboards?|mouse|mice)\b"
    quantity_match = re.search(
        r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
        r"(?:[\w-]+\s+){0,3}" + noun,
        message,
        re.I,
    )
    budget_match = re.search(
        r"(?:under|budget(?:\s+of)?|maximum of?|up to)\s*\$?([\d,]+(?:\.\d{1,2})?)",
        message,
        re.I,
    )
    size_match = re.search(r"\b(\d{2})[- ]?(?:inch|in|\")", message, re.I)
    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    token = quantity_match.group(1).lower() if quantity_match else None
    quantity = int(token) if token and token.isdigit() else number_words.get(token)
    budget = budget_match.group(1).replace(",", "") if budget_match else None
    size = int(size_match.group(1)) if size_match and category == "computer_monitor" else None
    if quantity is not None and not 1 <= quantity <= 100:
        quantity = None
    if budget is not None and Decimal(budget) <= 0:
        budget = None
    connection = re.search(r"\b(wireless|bluetooth|wired)\b", message, re.I)
    required_connection = (
        connection.group(1).lower() if connection and category != "computer_monitor" else None
    )
    values = {
        "category": category,
        "quantity": quantity,
        "maximum_total_budget": budget,
        "currency": "USD",
        "required_screen_size_inches": size,
        "preferences": ["reliability", "warranty coverage"]
        + (["display quality"] if category == "computer_monitor" else []),
        "required_connection": required_connection,
    }
    missing = missing_requirements(values)
    return {**values, "missing_information": missing, "requires_clarification": bool(missing)}


async def plan_request_with_gemini(message: str, api_key: str, model: str) -> dict:
    plan = await generate_structured(
        api_key=api_key,
        model=model,
        system_instruction=(
            "You are ARC's procurement planner. Extract only requirements explicitly stated "
            "by the user. Do not invent quantities, budgets, dimensions, or preferences. "
            "ARC supports computer monitors, computer keyboards, computer mice, and USD budgets. "
            "Screen size is required only for monitors. If the category is unsupported or "
            "multiple categories are requested, set category to null."
        ),
        prompt=f"Procurement request:\n{message}",
        response_schema=PlannedRequirements,
    )
    values = plan.model_dump(mode="json")
    if plan.maximum_total_budget is not None and plan.maximum_total_budget <= 0:
        values["maximum_total_budget"] = None
    missing = missing_requirements(values)
    values["missing_information"] = missing
    values["requires_clarification"] = bool(missing)
    return values
