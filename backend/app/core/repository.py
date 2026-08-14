from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any


def resolve_safe_path(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    posix_path = PurePosixPath(relative_path.replace("\\", "/"))
    if posix_path.is_absolute() or ".." in posix_path.parts or ".git" in posix_path.parts:
        raise ValueError(f"unsafe repository path: {relative_path}")
    candidate = root.joinpath(*posix_path.parts)
    resolved_parent = candidate.parent.resolve(strict=False)
    if root != resolved_parent and root not in resolved_parent.parents:
        raise ValueError(f"path escapes repository: {relative_path}")
    cursor = candidate.parent
    while cursor != root and root in cursor.parents:
        if cursor.exists() and cursor.is_symlink():
            raise ValueError(f"symlinked repository path is not writable: {relative_path}")
        cursor = cursor.parent
    return candidate


def apply_file_changes(root: Path, changes: Iterable[Mapping[str, Any]]) -> list[str]:
    written: list[str] = []
    for change in changes:
        relative_path = str(change["path"])
        destination = resolve_safe_path(root, relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.is_symlink():
            raise ValueError(f"refusing to overwrite symlink: {relative_path}")
        content = str(change["content"])
        destination.write_text(content, encoding="utf-8", newline="\n")
        try:
            os.chmod(destination, 0o644)
        except OSError:
            pass
        written.append(PurePosixPath(relative_path).as_posix())
    return written


def build_repository_context(root: Path, *, max_files: int = 80, max_chars: int = 120_000) -> str:
    ignored = {".git", "node_modules", ".next", ".venv", "venv", "dist", "build", "__pycache__"}
    sections: list[str] = []
    size = 0
    files = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts):
            continue
        if path.stat().st_size > 200_000 or files >= max_files or size >= max_chars:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative = path.relative_to(root).as_posix()
        section = f"\n--- {relative} ---\n{content[:20_000]}"
        sections.append(section)
        size += len(section)
        files += 1
    return "".join(sections)[:max_chars]
