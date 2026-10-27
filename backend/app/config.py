from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DinnerBell Product Manager"
    database_url: str = "postgresql+psycopg://workflow:workflow@localhost:5432/workflow"
    frontend_origin: str = "http://localhost:5173"
    app_timezone: str = "America/Denver"
    session_cookie_secure: bool = False
    session_days: int = 14
    seed_demo_data: bool = False

    # Providers and models are configured explicitly per feature (AI-7)
    analysis_llm_base_url: str | None = None
    analysis_llm_api_key: str | None = None
    analysis_llm_model: str | None = None
    analysis_llm_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] | None = "medium"
    analysis_llm_max_output_tokens: int = Field(default=4096, ge=256, le=128000)

    # Sprint review uses Responses with read-only GitHub tools
    review_llm_base_url: str | None = None
    review_llm_api_key: str | None = None
    review_llm_model: str | None = None
    review_llm_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] | None = "high"
    review_llm_max_output_tokens: int = Field(default=6000, ge=256, le=128000)

    github_token: str | None = None

    # Blank Compose values use the same defaults as a directly launched backend
    # Ignore retired dotenv settings, including the old shared OPENAI_API_KEY
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True, extra="ignore")


settings = Settings()
