from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_backend_image_prepares_writable_render_paths():
    dockerfile = (REPOSITORY_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

    assert "mkdir -p /data /workspace" in dockerfile
    assert "chown -R forgeguard:forgeguard /app /data /workspace /tmp" in dockerfile
