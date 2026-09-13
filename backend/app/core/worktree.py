from __future__ import annotations

import base64
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from git import Actor, Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

PROTECTED_BRANCHES = {"main", "master", "production"}


def assert_safe_push_branch(branch: str) -> str:
    normalized = branch.removeprefix("refs/heads/").strip("/").lower()
    if normalized in PROTECTED_BRANCHES:
        raise ValueError(f"refusing write operation targeting protected branch: {branch}")
    if not normalized.startswith("forgeguard/repair-"):
        raise ValueError("repair writes must target forgeguard/repair-{job_id}")
    return branch


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
    owner_repo: Repo

    def stage_and_diff(self) -> tuple[list[str], str]:
        self.repo.git.add(A=True)
        names = [
            line for line in self.repo.git.diff("--cached", "--name-only").splitlines() if line
        ]
        diff = self.repo.git.diff("--cached", "--no-ext-diff", "--unified=4")
        return names, diff

    def commit_and_push(self, branch: str, access_token: str) -> None:
        """Commit the reviewed index and push only the task's dedicated branch."""
        safe_branch = assert_safe_push_branch(branch)
        self.repo.git.add(A=True)
        actor = Actor("ForgeGuard", "bot@forgeguard.local")
        if self.repo.is_dirty(index=True, working_tree=True, untracked_files=True):
            self.repo.index.commit(
                "fix: apply verified ForgeGuard repair", author=actor, committer=actor
            )
        credentials = base64.b64encode(f"x-access-token:{access_token}".encode()).decode()
        with self.repo.git.custom_environment(
            GIT_HTTP_EXTRAHEADER=f"Authorization: Basic {credentials}"
        ):
            self.repo.git.push("origin", f"HEAD:refs/heads/{safe_branch}")


class WorktreeManager:
    def __init__(self, work_root: Path):
        self.work_root = work_root.resolve()
        self.work_root.mkdir(parents=True, exist_ok=True)

    def _resolve_source(
        self, repo_url: str, demo_repo_path: Path, access_token: str | None = None
    ) -> Path:
        if repo_url == "demo":
            return demo_repo_path.resolve()
        local = Path(repo_url).expanduser()
        if local.exists():
            return local.resolve()
        if not repo_url.startswith("https://"):
            raise ValueError("unsupported repository locator")
        cache = self.work_root / "sources" / hashlib.sha256(repo_url.encode()).hexdigest()[:16]
        git_env: dict[str, str] = {}
        if access_token:
            credentials = base64.b64encode(f"x-access-token:{access_token}".encode()).decode()
            git_env["GIT_HTTP_EXTRAHEADER"] = f"Authorization: Basic {credentials}"
        if cache.exists():
            cache_repo = Repo(cache)
            with cache_repo.git.custom_environment(**git_env):
                cache_repo.remotes.origin.fetch(prune=True)
        else:
            cache.parent.mkdir(parents=True, exist_ok=True)
            Repo.clone_from(repo_url, cache, env=git_env)
        return cache

    def create(
        self,
        task_id: str,
        repo_url: str,
        base_branch: str,
        demo_repo_path: Path,
        access_token: str | None = None,
    ) -> Worktree:
        source = self._resolve_source(repo_url, demo_repo_path, access_token)
        source_repo = _ensure_repository(source)
        target = (self.work_root / task_id).resolve()
        if self.work_root not in target.parents:
            raise ValueError("invalid worktree target")
        branch = assert_safe_push_branch(f"forgeguard/repair-{task_id}")
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
        return Worktree(Repo(target), target, source_repo)

    def remove(self, worktree: Worktree) -> None:
        worktree.repo.close()
        try:
            try:
                worktree.owner_repo.git.worktree("remove", "--force", str(worktree.path))
            except GitCommandError:
                if worktree.path.exists():
                    shutil.rmtree(worktree.path)
                worktree.owner_repo.git.worktree("prune")
        finally:
            worktree.owner_repo.close()
