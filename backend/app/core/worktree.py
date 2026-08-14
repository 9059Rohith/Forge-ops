from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from git import Actor, Repo
from git.exc import GitCommandError, InvalidGitRepositoryError


def _ensure_repository(source: Path) -> Repo:
    try:
        return Repo(source)
    except InvalidGitRepositoryError:
        repo = Repo.init(source)
        repo.config_writer().set_value("user", "name", "ForgeGuard Demo").set_value(
            "user", "email", "demo@forgeguard.local"
        ).release()
        repo.git.add(A=True)
        actor = Actor("ForgeGuard Demo", "demo@forgeguard.local")
        repo.index.commit("chore: seed ForgeGuard demo repository", author=actor, committer=actor)
        return repo


@dataclass(slots=True)
class Worktree:
    repo: Repo
    path: Path

    def stage_and_diff(self) -> tuple[list[str], str]:
        self.repo.git.add(A=True)
        names = [
            line for line in self.repo.git.diff("--cached", "--name-only").splitlines() if line
        ]
        diff = self.repo.git.diff("--cached", "--no-ext-diff", "--unified=4")
        return names, diff


class WorktreeManager:
    def __init__(self, work_root: Path):
        self.work_root = work_root.resolve()
        self.work_root.mkdir(parents=True, exist_ok=True)

    def _resolve_source(self, repo_url: str, demo_repo_path: Path) -> Path:
        if repo_url == "demo":
            return demo_repo_path.resolve()
        local = Path(repo_url).expanduser()
        if local.exists():
            return local.resolve()
        if not repo_url.startswith("https://"):
            raise ValueError("unsupported repository locator")
        cache = self.work_root / "sources" / hashlib.sha256(repo_url.encode()).hexdigest()[:16]
        if cache.exists():
            Repo(cache).remotes.origin.fetch(prune=True)
        else:
            cache.parent.mkdir(parents=True, exist_ok=True)
            Repo.clone_from(repo_url, cache)
        return cache

    def create(
        self, task_id: str, repo_url: str, base_branch: str, demo_repo_path: Path
    ) -> Worktree:
        source = self._resolve_source(repo_url, demo_repo_path)
        source_repo = _ensure_repository(source)
        target = (self.work_root / task_id).resolve()
        if self.work_root not in target.parents:
            raise ValueError("invalid worktree target")
        branch = f"forgeguard/{task_id}"
        if target.exists():
            try:
                source_repo.git.worktree("remove", "--force", str(target))
            except GitCommandError:
                shutil.rmtree(target)
        if branch in [head.name for head in source_repo.heads]:
            source_repo.delete_head(branch, force=True)
        try:
            source_repo.git.worktree("add", "-b", branch, str(target), base_branch)
        except GitCommandError:
            source_repo.git.worktree("prune")
            if target.exists():
                shutil.rmtree(target)
            source_repo.git.worktree(
                "add", "-b", branch, str(target), source_repo.head.commit.hexsha
            )
        return Worktree(Repo(target), target)
