from pathlib import Path

import pytest
from git import Actor, Repo

from app.core.repository import apply_file_changes, resolve_safe_path
from app.core.worktree import Worktree, assert_safe_push_branch


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


@pytest.mark.parametrize("branch", ["main", "master", "production", "refs/heads/main"])
def test_protected_branches_are_never_write_targets(branch: str):
    with pytest.raises(ValueError, match="protected branch"):
        assert_safe_push_branch(branch)


def test_repair_branch_is_a_safe_write_target():
    assert assert_safe_push_branch("forgeguard/repair-task-123") == "forgeguard/repair-task-123"


def test_verified_worktree_pushes_only_dedicated_branch(tmp_path: Path):
    remote_path = tmp_path / "remote.git"
    Repo.init(remote_path, bare=True)
    checkout_path = tmp_path / "checkout"
    repo = Repo.init(checkout_path)
    actor = Actor("Test", "test@example.com")
    tracked = checkout_path / "app.py"
    tracked.write_text("safe = False\n", encoding="utf-8")
    repo.index.add(["app.py"])
    repo.index.commit("initial", author=actor, committer=actor)
    repo.create_remote("origin", str(remote_path))

    tracked.write_text("safe = True\n", encoding="utf-8")
    worktree = Worktree(repo=repo, path=checkout_path, owner_repo=repo)
    access_token = "".join(("test", "-credential"))
    branch = "forgeguard/repair-job-123"
    worktree.commit_and_push(branch, access_token)

    remote = Repo(remote_path)
    assert remote.commit(f"refs/heads/{branch}").message == "fix: apply verified ForgeGuard repair"
