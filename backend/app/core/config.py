from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "TaskForge AI"
    environment: str = "development"
    debug: bool = True

    # API
    api_prefix: str = "/api/v1"
    cors_origins: List[str] = ["http://localhost:5173"]

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/taskforge"

    # AI provider (generic placeholders, no real keys)
    ai_provider: str = "none"
    ai_api_key: Optional[str] = None
    ai_model: Optional[str] = None

    # Auth / JWT
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()