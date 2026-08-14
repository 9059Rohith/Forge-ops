from pathlib import Path

import pytest

from app.core.repository import apply_file_changes, resolve_safe_path


def test_resolve_safe_path_accepts_nested_relative_path(tmp_path: Path):
    assert resolve_safe_path(tmp_path, "src/checkout.py") == tmp_path / "src" / "checkout.py"


@pytest.mark.parametrize("path", ["../secrets.txt", "/etc/passwd", ".git/config", "src/../../x"])
def test_resolve_safe_path_rejects_escape_or_git_metadata(tmp_path: Path, path: str):
    with pytest.raises(ValueError):
        resolve_safe_path(tmp_path, path)


def test_apply_file_changes_writes_only_inside_repository(tmp_path: Path):
    changed = apply_file_changes(
        tmp_path,
        [{"path": "src/checkout.py", "content": "def checkout():\n    return True\n"}],
    )

    assert changed == ["src/checkout.py"]
    assert (tmp_path / "src" / "checkout.py").read_text(encoding="utf-8").startswith("def checkout")
