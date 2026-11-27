from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from contracts import (
    BranchContract,
    CommitContract,
    IssueContract,
    PullRequestContract,
    StoryContract,
    SubtaskContract,
    SyncResultContract,
)


def test_normalized_jira_contracts_accept_service_fields_and_extra_columns() -> None:
    issue = IssueContract.model_validate({"key": "JH-1", "summary": "Resumo", "issue_type": "Story"})
    story = StoryContract.model_validate({"story_key": "JH-1", "story_summary": "US2.1", "story_points": 3})
    subtask = SubtaskContract.model_validate({"subtask_key": "JH-11", "story_key": "JH-1", "subtask_code": "BE-01"})

    assert issue.key == "JH-1"
    assert story.story_points == 3
    assert subtask.subtask_code == "BE-01"


def test_github_contracts_validate_commit_branch_and_pull_request_identity() -> None:
    commit = CommitContract.model_validate({"sha": "abc123", "repo": "org/repo", "author": "cid", "delivered": True})
    branch = BranchContract.model_validate({"repo": "org/repo", "branch": "feature/backend/JH-1-US2.1-demo"})
    pull_request = PullRequestContract.model_validate({"repo": "org/repo", "number": 12, "state": "open"})

    assert commit.sha == "abc123" and commit.delivered is True
    assert branch.branch.startswith("feature/")
    assert pull_request.number == 12


def test_contracts_reject_missing_identifiers_and_invalid_pull_request_numbers() -> None:
    with pytest.raises(ValidationError):
        StoryContract.model_validate({"story_summary": "sem chave"})
    with pytest.raises(ValidationError):
        CommitContract.model_validate({"sha": "", "repo": "org/repo"})
    with pytest.raises(ValidationError):
        PullRequestContract.model_validate({"repo": "org/repo", "number": 0})


def test_sync_result_contract_preserves_partial_and_error_information() -> None:
    result = SyncResultContract.model_validate({
        "source": "GitHub",
        "status": "partial",
        "fetched_at": datetime(2026, 11, 26, tzinfo=timezone.utc),
        "warnings": ["3 PRs indisponíveis"],
        "stats": {"pages": 2},
        "data": {"commits": []},
    })

    assert result.status == "partial"
    assert result.warnings == ["3 PRs indisponíveis"]
    assert result.stats["pages"] == 2
