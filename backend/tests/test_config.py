import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_fixture_mode_does_not_require_gemini_key() -> None:
    settings = Settings(agent_mode="fixture", gemini_api_key=None)

    assert settings.model_for_agent("planner") == "fixture:deterministic"


def test_gemini_mode_requires_api_key() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY is required"):
        Settings(agent_mode="gemini", gemini_api_key=None)


def test_gemini_mode_selects_configured_models() -> None:
    settings = Settings(agent_mode="gemini", gemini_api_key="test-key")

    assert settings.model_for_agent("planner") == "gemini-3.5-flash-lite"
    assert settings.model_for_agent("evaluator") == "gemini-3.5-flash"
    assert settings.model_for_agent("reporter") == "gemini-3.5-flash-lite"


def test_channel3_mode_requires_api_key() -> None:
    with pytest.raises(ValidationError, match="CHANNEL3_API_KEY is required"):
        Settings(catalog_provider="channel3", channel3_api_key=None)


def test_channel3_is_recorded_as_the_research_provider() -> None:
    settings = Settings(catalog_provider="channel3", channel3_api_key="test-key")

    assert settings.model_for_agent("research") == "channel3"
