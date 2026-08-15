from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.integrations import github_app


def test_exchanges_scoped_github_app_installation_token(monkeypatch):
    captured: dict[str, object] = {}
    expected_token = "-".join(("installation", "token"))

    class FakeIntegration:
        def __init__(self, app_id: str, private_key: str):
            captured.update(app_id=app_id, private_key=private_key)

        def get_access_token(self, installation_id: int, permissions: dict[str, str]):
            captured.update(installation_id=installation_id, permissions=permissions)
            return SimpleNamespace(token=expected_token)

    monkeypatch.setattr(github_app, "GithubIntegration", FakeIntegration)

    token = github_app.get_installation_token("123", "line1\\nline2", 456)

    assert token == expected_token
    assert captured == {
        "app_id": "123",
        "private_key": "line1\nline2",
        "installation_id": 456,
        "permissions": {"contents": "write", "pull_requests": "write", "metadata": "read"},
    }


def test_creates_evidence_backed_pull_request(monkeypatch):
    captured: dict[str, object] = {}
    access_token = "".join(("test", "-credential"))

    class FakeRepository:
        def create_pull(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(html_url="https://github.com/acme/widget/pull/7", number=7)

    class FakeGithub:
        def __init__(self, *, auth):
            captured["auth"] = auth

        def get_repo(self, full_name: str):
            captured["repo"] = full_name
            return FakeRepository()

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr(github_app, "Github", FakeGithub)

    result = github_app.create_pull_request(
        token=access_token,
        repo_full_name="acme/widget",
        base_branch="main",
        repair_branch="forgeguard/repair-job-1",
        title="ForgeGuard repair: Escape SQL parameters",
        body="Evidence",
    )

    assert result.url == "https://github.com/acme/widget/pull/7"
    assert result.number == 7
    assert captured["repo"] == "acme/widget"
    assert captured["base"] == "main"
    assert captured["head"] == "forgeguard/repair-job-1"
    assert captured["body"] == "Evidence"
    assert captured["closed"] is True


def test_pull_request_rejects_protected_write_branch():
    access_token = "".join(("test", "-credential"))
    with pytest.raises(ValueError, match="protected branch"):
        github_app.create_pull_request(
            token=access_token,
            repo_full_name="acme/widget",
            base_branch="develop",
            repair_branch="main",
            title="unsafe",
            body="unsafe",
        )
