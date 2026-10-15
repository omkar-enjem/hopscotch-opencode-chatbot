from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_models: str = "openai/gpt-4o-mini,anthropic/claude-3.5-haiku"

    app_name: str = "Kids Fashion Assistant"
    app_url: str = "http://localhost:8501"

    database_url: str = "sqlite:///./data/kidsfashion.db"

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    backend_url: str = "http://127.0.0.1:8000"

    brand_name: str = "Kids Fashion Assistant"
    bot_name: str = "Guddi"

    @property
    def model_list(self) -> list[str]:
        return [m.strip() for m in self.llm_models.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
