"""Contratos tipados dos registros normalizados consumidos pela aplicação."""

from contracts.models import (
    BranchContract,
    CommitContract,
    IssueContract,
    PullRequestContract,
    StoryContract,
    SubtaskContract,
    SyncResultContract,
)

__all__ = [
    "BranchContract",
    "CommitContract",
    "IssueContract",
    "PullRequestContract",
    "StoryContract",
    "SubtaskContract",
    "SyncResultContract",
]
