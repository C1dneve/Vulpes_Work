"""Testes das regras de rastreabilidade consumidas pelas páginas do Analytics."""
import pandas as pd

from domain import statuses as S
from views.git_traceability import GitTraceability


def build_traceability(
    *,
    commits: pd.DataFrame | None = None,
    branches: pd.DataFrame | None = None,
    prs: pd.DataFrame | None = None,
) -> GitTraceability:
    return GitTraceability(
        stories=pd.DataFrame([{"story_key": "JH-100", "us_id": "US2.1"}]),
        subtasks=pd.DataFrame([{"subtask_key": "JH-101", "story_key": "JH-100"}]),
        commits=commits if commits is not None else pd.DataFrame(),
        branches=branches if branches is not None else pd.DataFrame(),
        prs=prs if prs is not None else pd.DataFrame(),
        known_keys={"JH-100", "JH-101"},
    )


def test_task_commits_keep_only_human_commits_that_name_the_subtask() -> None:
    commits = pd.DataFrame([
        {"sha": "human-task", "jira_key": "JH-101", "kind": "human", "date": pd.Timestamp("2026-09-01")},
        {"sha": "bot-task", "jira_key": "JH-101", "kind": "bot", "date": pd.Timestamp("2026-09-02")},
        {"sha": "story-only", "jira_key": "JH-100", "kind": "human", "date": pd.Timestamp("2026-09-03")},
    ])
    task = pd.Series({"subtask_key": "JH-101", "story_key": "JH-100", "us_id": "US2.1"})

    result = build_traceability(commits=commits).commits_for_task(task)

    assert list(result["sha"]) == ["human-task"]


def test_story_references_exclude_subtask_commits_and_bots() -> None:
    commits = pd.DataFrame([
        {"sha": "story-human", "jira_key": "JH-100", "ref_jira_key": None, "us_id": "US2.1", "kind": "human",
         "date": pd.Timestamp("2026-09-01")},
        {"sha": "subtask-human", "jira_key": "JH-101", "ref_jira_key": "JH-100", "us_id": "US2.1", "kind": "human",
         "date": pd.Timestamp("2026-09-02")},
        {"sha": "story-bot", "jira_key": "JH-100", "ref_jira_key": None, "us_id": "US2.1", "kind": "bot",
         "date": pd.Timestamp("2026-09-03")},
    ])
    branches = pd.DataFrame([
        {"branch": "main", "is_default": True, "jira_key": None, "us_id": None},
        {"branch": "feature/backend/JH-100-US2.1-example", "is_default": False, "jira_key": "JH-100", "us_id": "US2.1"},
    ])
    prs = pd.DataFrame([
        {"number": 7, "jira_key": "JH-100", "ref_jira_key": None, "us_id": "US2.1"},
    ])

    story_branches, story_prs, story_commits = build_traceability(
        commits=commits,
        branches=branches,
        prs=prs,
    ).story_references("JH-100")

    assert list(story_branches["branch"]) == ["feature/backend/JH-100-US2.1-example"]
    assert list(story_prs["number"]) == [7]
    assert list(story_commits["sha"]) == ["story-human"]


def test_git_summary_preserves_delivery_alerts_and_task_code_fallback() -> None:
    commits = pd.DataFrame([
        {"jira_key": "JH-101", "kind": "human", "date": pd.Timestamp("2026-09-01"), "delivered": False,
         "branches": ["feature/backend/JH-101"]},
        {"jira_key": "JH-101", "kind": "bot", "date": pd.Timestamp("2026-09-02"), "delivered": True,
         "branches": ["feature/backend/JH-101"]},
    ])
    tasks = pd.DataFrame([
        {"subtask_key": "JH-101", "subtask_code": None, "story_key": "JH-100", "us_id": "US2.1",
         "subtask_summary": "Implementar teste", "assignee": "ana", "status_group": S.CONCLUIDA,
         "time_spent_h": 2.5, "estimate_h": 3.0},
    ])

    result = build_traceability(commits=commits).summarize_git(tasks)
    row = result.iloc[0]

    assert row["Task"] == "JH-101"
    assert row["Commits"] == 1
    assert row["Entregues"] == 0
    assert row["Em branch"] == 1
    assert row["Branches"] == "feature/backend/JH-101"
    assert "sem entrega" in row["Alerta"]


def test_git_summary_on_empty_scope_keeps_expected_columns() -> None:
    result = build_traceability().summarize_git(pd.DataFrame())

    assert result.empty
    assert list(result.columns) == [
        "Task", "User Story", "Resumo", "Dev", "Status", "Horas", "Estimado (h)", "Commits",
        "Entregues", "Em branch", "Branches", "Alerta", "subtask_key",
    ]
