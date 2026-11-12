import asyncio
import sys

from app.agents.planner import plan_request_with_gemini
from app.core.config import Settings


async def main() -> None:
    settings = Settings()
    if settings.gemini_api_key is None:
        raise SystemExit("GEMINI_API_KEY is not configured")
    model = sys.argv[1] if len(sys.argv) > 1 else settings.gemini_planner_model
    try:
        result = await plan_request_with_gemini(
            "Find three 27-inch monitors under $600 total",
            settings.gemini_api_key.get_secret_value(),
            model,
        )
    except Exception as exc:
        print(f"Gemini verification failed: {type(exc).__name__}: {exc}")
        raise SystemExit(1) from None
    print(
        "Gemini verification succeeded: "
        f"quantity={result['quantity']}, "
        f"budget={result['maximum_total_budget']}, "
        f"screen_size={result['required_screen_size_inches']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
