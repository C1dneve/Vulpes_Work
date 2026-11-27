"""Contratos Pydantic dos dados normalizados já produzidos pelos serviços."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NormalizedRecord(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


class IssueContract(NormalizedRecord):
    """Representação mínima de uma issue normalizada do Jira."""

    key: str = Field(min_length=1)
    summary: str | None = None
    issue_type: str | None = None
    status_name: str | None = None
    status_group: str | None = None


class StoryContract(NormalizedRecord):
    story_key: str = Field(min_length=1)
    story_summary: str | None = None
    issue_type: str | None = None
    status_name: str | None = None
    status_group: str | None = None
    assignee: str | None = None
    sprint: str | None = None
    us_id: str | None = None
    canonical_id: str | None = None
    story_points: float | None = None


class SubtaskContract(NormalizedRecord):
    subtask_key: str = Field(min_length=1)
    subtask_summary: str | None = None
    story_key: str | None = None
    assignee: str | None = None
    issue_type: str | None = None
    status_name: str | None = None
    status_group: str | None = None
    sprint: str | None = None
    us_id: str | None = None
    canonical_id: str | None = None
    subtask_code: str | None = None


class CommitContract(NormalizedRecord):
    sha: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    author: str | None = None
    date: datetime | None = None
    message: str | None = None
    jira_key: str | None = None
    us_id: str | None = None
    delivered: bool | None = None


class BranchContract(NormalizedRecord):
    repo: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    is_default: bool | None = None
    head_sha: str | None = None
    jira_key: str | None = None
    us_id: str | None = None
    delivered: bool | None = None


class PullRequestContract(NormalizedRecord):
    repo: str = Field(min_length=1)
    number: int = Field(gt=0)
    title: str | None = None
    state: str | None = None
    author: str | None = None
    head: str | None = None
    base: str | None = None
    jira_key: str | None = None
    us_id: str | None = None


class SyncResultContract(BaseModel):
    """Resultado de sincronização sem impor formato novo aos dados internos dos serviços."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    source: str = Field(min_length=1)
    status: Literal["ok", "partial", "error"]
    fetched_at: datetime
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    data: Any | None = None
