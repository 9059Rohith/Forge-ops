from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./forgeguard.db"
    allowed_origins: list[str] | str = Field(default_factory=lambda: ["http://localhost:3000"])
    demo_repo_path: Path = Path(__file__).resolve().parents[2] / "demo-repo"
    work_root: Path = Path(__file__).resolve().parents[2] / ".forgeguard-work"
    max_repair_cycles: int = Field(default=2, ge=0, le=5)
    demo_mode: bool = True
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    github_token: str | None = None
    github_webhook_secret: str | None = None
    openai_model: str = "gpt-4o"
    groq_model: str = "llama-3.3-70b-versatile"
    engineer_timeout_seconds: float = 60.0
    reviewer_timeout_seconds: float = 30.0
    command_timeout_seconds: float = 120.0

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
