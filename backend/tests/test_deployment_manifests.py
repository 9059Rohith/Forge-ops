import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_vercel_manifest_uses_the_frontend_as_a_nextjs_project():
    manifest_path = REPOSITORY_ROOT / "frontend" / "vercel.json"

    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["framework"] == "nextjs"
    assert manifest["installCommand"] == "npm ci"
    assert manifest["buildCommand"] == "npm run build"


def test_render_blueprint_deploys_only_the_api_for_vercel_pairing():
    blueprint = (REPOSITORY_ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "name: forgeguard-api" in blueprint
    assert "name: forgeguard-dashboard" not in blueprint
    assert "- key: FRONTEND_URL" in blueprint
    assert "- key: ALLOWED_ORIGINS" in blueprint
    assert "numInstances: 1" in blueprint


def test_ci_builds_both_release_images_before_publish():
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "docker build -f backend/Dockerfile" in workflow
    assert "docker build -f frontend/Dockerfile" in workflow


def test_compose_ports_and_public_urls_are_overridable():
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert '${BACKEND_PORT:-8000}:8000' in compose
    assert '${FRONTEND_PORT:-3000}:3000' in compose
    assert '${PUBLIC_BACKEND_URL:-http://localhost:8000}' in compose
    assert '${PUBLIC_FRONTEND_URL:-http://localhost:3000}' in compose
