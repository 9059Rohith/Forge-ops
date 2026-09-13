from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./forgeguard.db"
    allowed_origins: list[str] | str = Field(default_factory=lambda: ["http://localhost:3000"])
    allowed_origin_regex: str | None = None
    demo_repo_path: Path = Path(__file__).resolve().parents[2] / "demo-repo"
    work_root: Path = Field(
        default=Path(__file__).resolve().parents[2] / ".forgeguard-work",
        validation_alias=AliasChoices("WORKSPACE_ROOT", "WORK_ROOT"),
    )
    workspace_retention_hours: int = Field(default=0, ge=0, le=720)
    max_repair_cycles: int = Field(default=2, ge=0, le=5)
    demo_mode: bool = False
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    github_token: str | None = None
    github_webhook_secret: str | None = None
    github_app_id: str | None = None
    github_private_key: str | None = None
    dodo_api_key: str | None = None
    dodo_webhook_secret: str | None = None
    dodo_api_url: str = "https://live.dodopayments.com"
    dodo_product_developer: str | None = None
    dodo_product_pro: str | None = None
    dodo_product_team: str | None = None
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    session_secret: str | None = None
    allowed_repos: list[str] | str = Field(default_factory=list)
    log_level: str = "INFO"
    openai_model: str = "gpt-4o"
    groq_model: str = "openai/gpt-oss-120b"
    engineer_timeout_seconds: float = 60.0
    reviewer_timeout_seconds: float = 30.0
    command_timeout_seconds: float = 120.0

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allowed_repos", mode="before")
    @classmethod
    def parse_allowed_repos(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def product_id_for_plan(self, plan: str) -> str | None:
        return {
            "developer": self.dodo_product_developer,
            "pro": self.dodo_product_pro,
            "team": self.dodo_product_team,
        }.get(plan)

    def validate_runtime(self) -> None:
        if self.environment.lower() != "production" or self.demo_mode:
            return
        required = {
            "GITHUB_APP_ID": self.github_app_id,
            "GITHUB_PRIVATE_KEY": self.github_private_key,
            "GITHUB_WEBHOOK_SECRET": self.github_webhook_secret,
            "OPENAI_API_KEY": self.openai_api_key,
            "GROQ_API_KEY": self.groq_api_key,
            "DODO_API_KEY": self.dodo_api_key,
            "DODO_WEBHOOK_SECRET": self.dodo_webhook_secret,
            "DODO_PRODUCT_DEVELOPER": self.dodo_product_developer,
            "DODO_PRODUCT_PRO": self.dodo_product_pro,
            "DODO_PRODUCT_TEAM": self.dodo_product_team,
            "SESSION_SECRET": self.session_secret,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing required production settings: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
