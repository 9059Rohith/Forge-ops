from __future__ import annotations

import re
from datetime import datetime
from pathlib import PureWindowsPath
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,119}$")
TERMINAL_STATUSES = {"verified", "failed", "manual_review_required"}


class TaskCreate(BaseModel):
    repo_url: str = Field(min_length=1, max_length=500)
    branch: str = Field(default="main", min_length=1, max_length=120)
    description: str = Field(min_length=3, max_length=10_000)
    user_id: str | None = None

    @field_validator("repo_url", "branch", "description", mode="before")
    @classmethod
    def strip_strings(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("repo_url")
    @classmethod
    def validate_repo(cls, value: str) -> str:
        if value == "demo":
            return value
        if not any(char in value for char in "\r\n\0") and PureWindowsPath(value).is_absolute():
            return value
        parsed = urlsplit(value)
        if (
            parsed.scheme == "https"
            and parsed.hostname == "github.com"
            and not parsed.username
            and not parsed.password
        ):
            return value.rstrip("/")
        # Local repository paths are allowed, but URI schemes and control characters are not.
        if not parsed.scheme and not any(char in value for char in "\r\n\0"):
            return value
        raise ValueError(
            "repository must be 'demo', a local path, or an HTTPS GitHub URL without credentials"
        )

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, value: str) -> str:
        if not BRANCH_PATTERN.fullmatch(value) or ".." in value or value.endswith(("/", ".lock")):
            raise ValueError("branch contains unsafe characters")
        return value


class TaskCreated(BaseModel):
    task_id: str


class ProjectView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    repo_url: str
    repo_full_name: str | None
    branch: str
    created_at: datetime


class EvaluationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    category: str
    score: int
    severity: str
    finding: str
    evidence: dict[str, Any]


class AgentRunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    agent_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    output: dict[str, Any]


class FlightLogView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    timestamp: datetime
    event: str


class TaskView(BaseModel):
    id: str
    description: str
    status: str
    risk_level: str | None
    confidence_score: float | None
    repair_cycles: int
    tests_passed: int
    tests_total: int
    changed_files: list[str]
    error_message: str | None
    repair_branch: str | None
    pr_url: str | None
    pr_number: int | None
    created_at: datetime
    updated_at: datetime
    project: ProjectView
    evaluations: list[EvaluationView]
    agent_runs: list[AgentRunView]


class DiffView(BaseModel):
    diff: str


class VerificationReceipt(BaseModel):
    schema_version: str
    receipt_id: str
    decision: Literal["VERIFIED", "BLOCKED"]
    task: dict[str, Any]
    verification: dict[str, Any]
    provenance: dict[str, Any]
    artifacts: dict[str, str]
    integrity: dict[str, str]


class ProofView(BaseModel):
    markdown: str
    receipt: VerificationReceipt | None = None


class RepairAccepted(BaseModel):
    task_id: str
    status: Literal["repairing"]


class ReviewResult(BaseModel):
    score: int = Field(ge=0, le=100)
    severity: Literal["none", "low", "medium", "high", "critical"]
    finding: str = Field(min_length=1, max_length=4_000)
    evidence: dict[str, Any] = Field(default_factory=dict)


class FileChange(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=1_000_000)


class EngineerResult(BaseModel):
    plan: str = Field(min_length=1, max_length=8_000)
    constraints_identified: list[str] = Field(default_factory=list, max_length=100)
    files: list[FileChange] = Field(min_length=1, max_length=100)


class RiskResult(BaseModel):
    overall_confidence: float
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    decision: Literal["VERIFIED", "BLOCKED"]
