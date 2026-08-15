from __future__ import annotations

from dataclasses import dataclass

from github import Auth, Github, GithubIntegration

from app.core.worktree import assert_safe_push_branch


@dataclass(frozen=True, slots=True)
class PublishedPullRequest:
    url: str
    number: int


def get_installation_token(app_id: str, private_key: str, installation_id: int) -> str:
    """Exchange GitHub App credentials for a short-lived, least-privilege token."""
    normalized_key = private_key.replace("\\n", "\n")
    integration = GithubIntegration(app_id, normalized_key)
    authorization = integration.get_access_token(
        installation_id,
        permissions={"contents": "write", "pull_requests": "write", "metadata": "read"},
    )
    return authorization.token


def create_pull_request(
    *,
    token: str,
    repo_full_name: str,
    base_branch: str,
    repair_branch: str,
    title: str,
    body: str,
) -> PublishedPullRequest:
    """Open the human-merge-only PR after the verified branch has been pushed."""
    assert_safe_push_branch(repair_branch)
    client = Github(auth=Auth.Token(token))
    try:
        pull = client.get_repo(repo_full_name).create_pull(
            title=title,
            body=body,
            base=base_branch,
            head=repair_branch,
            draft=False,
        )
        return PublishedPullRequest(url=pull.html_url, number=pull.number)
    finally:
        client.close()
