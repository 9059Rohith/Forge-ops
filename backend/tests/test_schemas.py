import pytest
from pydantic import ValidationError

from app.schemas import TaskCreate


def test_task_create_strips_values_and_accepts_https_or_local_demo_repo():
    value = TaskCreate(
        repo_url="  https://github.com/example/repo  ",
        branch=" main ",
        description=" Add retry handling. ",
    )

    assert value.repo_url == "https://github.com/example/repo"
    assert value.branch == "main"
    assert value.description == "Add retry handling."


def test_task_create_accepts_an_absolute_windows_repository_path():
    value = TaskCreate(
        repo_url=r"C:\Users\Builder\source\checkout",
        branch="main",
        description="Add retry handling.",
    )

    assert value.repo_url == r"C:\Users\Builder\source\checkout"


@pytest.mark.parametrize(
    "repo_url",
    [
        "http://github.com/example/repo",
        "https://internal.example/repo",
        "https://user:secret@github.com/example/repo",
        "file:///etc",
    ],
)
def test_task_create_rejects_unsafe_repository_locators(repo_url: str):
    with pytest.raises(ValidationError):
        TaskCreate(repo_url=repo_url, branch="main", description="A valid task")


def test_task_create_rejects_command_like_branch_names():
    with pytest.raises(ValidationError):
        TaskCreate(repo_url="demo", branch="main; rm -rf", description="A valid task")
