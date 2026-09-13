from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


def test_live_mode_is_the_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    from app.config import Settings

    assert Settings(_env_file=None).demo_mode is False


def test_vercel_preview_origin_regex_is_configurable(monkeypatch: pytest.MonkeyPatch):
    pattern = r"^https://forge-ops(?:-[a-z0-9-]+)?\.vercel\.app$"
    monkeypatch.setenv("ALLOWED_ORIGIN_REGEX", pattern)
    from app.config import Settings

    assert Settings().allowed_origin_regex == pattern


def test_production_validation_names_every_missing_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEMO_MODE", "false")
    for name in (
        "GITHUB_APP_ID",
        "GITHUB_PRIVATE_KEY",
        "GITHUB_WEBHOOK_SECRET",
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
        "DODO_API_KEY",
        "DODO_WEBHOOK_SECRET",
        "SESSION_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    from app.config import Settings

    with pytest.raises(RuntimeError) as error:
        Settings().validate_runtime()

    assert "GITHUB_APP_ID" in str(error.value)
    assert "DODO_WEBHOOK_SECRET" in str(error.value)
    assert "SESSION_SECRET" in str(error.value)


@pytest.mark.asyncio
async def test_root_health_and_readiness_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'health.db'}")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.db import reset_engine_for_tests

    await reset_engine_for_tests()
    from app.main import app

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/healthz")).json() == {"status": "ok"}
            ready = await client.get("/readyz")
            assert ready.status_code == 200
            assert ready.json() == {"status": "ready"}
