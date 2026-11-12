from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://arc:arc@localhost:5432/arc"
    frontend_origin: str = "http://localhost:3000"
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    agent_mode: Literal["fixture", "gemini"] = "fixture"
    gemini_api_key: SecretStr | None = None
    gemini_planner_model: str = "gemini-3.5-flash-lite"
    gemini_evaluator_model: str = "gemini-3.5-flash"
    gemini_reporter_model: str = "gemini-3.5-flash-lite"
    catalog_provider: Literal["demo_catalog", "channel3"] = "demo_catalog"
    channel3_api_key: SecretStr | None = None
    channel3_base_url: str = "https://api.trychannel3.com"
    channel3_search_limit: int = Field(default=12, ge=1, le=30)
    channel3_minimum_monitor_price: Decimal = Field(default=Decimal("50.00"), ge=0)
    paypal_mode: Literal["sandbox"] = "sandbox"
    paypal_client_id: str | None = None
    paypal_client_secret: SecretStr | None = None
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"

    @model_validator(mode="after")
    def validate_agent_configuration(self) -> "Settings":
        if self.agent_mode == "gemini" and self.gemini_api_key is None:
            raise ValueError("GEMINI_API_KEY is required when AGENT_MODE=gemini")
        if self.catalog_provider == "channel3" and self.channel3_api_key is None:
            raise ValueError("CHANNEL3_API_KEY is required when CATALOG_PROVIDER=channel3")
        if (self.paypal_client_id is None) != (self.paypal_client_secret is None):
            raise ValueError(
                "PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be configured together"
            )
        return self

    def model_for_agent(self, agent_name: str) -> str:
        if agent_name == "research":
            return self.catalog_provider
        if self.agent_mode == "fixture":
            return "fixture:deterministic"
        models = {
            "planner": self.gemini_planner_model,
            "evaluator": self.gemini_evaluator_model,
            "reporter": self.gemini_reporter_model,
        }
        return models[agent_name]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
