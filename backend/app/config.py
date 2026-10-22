from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DinnerBell Product Manager"
    database_url: str = "postgresql+psycopg://workflow:workflow@localhost:5432/workflow"
    frontend_origin: str = "http://localhost:5173"
    app_timezone: str = "America/Denver"
    session_cookie_secure: bool = False
    session_days: int = 14
    seed_demo_data: bool = False

    # Sprint analysis goes through the class LiteLLM proxy (AI-7).
    analysis_llm_base_url: str | None = None
    analysis_llm_api_key: str | None = None
    analysis_llm_model: str | None = None

    # Sprint review uses a Codex model; an empty base URL means OpenAI directly (AI-7).
    review_llm_base_url: str | None = None
    review_llm_api_key: str | None = None
    review_llm_model: str | None = None

    github_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
