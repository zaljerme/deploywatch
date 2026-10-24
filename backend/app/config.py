from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://deploywatch:deploywatch@localhost:5432/deploywatch"
    api_token: str = "local-development-token-change-me"
    environment: str = "development"
    allow_demo: bool = False
    demo_host: Literal["demo", "127.0.0.1"] = "demo"
    github_token: str = ""

    @model_validator(mode="after")
    def validate_environment(self):
        if self.environment not in {"development", "production"}:
            raise ValueError("environment must be development or production")
        if self.environment == "production":
            if self.allow_demo:
                raise ValueError("demo access is only allowed in development")
            if len(self.api_token) < 32 or self.api_token == "local-development-token-change-me":
                raise ValueError("production requires a unique API token of at least 32 characters")
        return self


@lru_cache
def settings():
    return Settings()
