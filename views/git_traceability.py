"""Resolução e resumo da rastreabilidade entre Jira e GitHub nas telas de Analytics."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from domain import statuses as S
from domain.linking import (
    branches_for_story,
    prs_for_story,
    story_level_commits,
)
from domain.linking import (
    commits_for_item as domain_commits_for_item,
)
from domain.people import nome_exibicao

StoryReferences = tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]


@dataclass(frozen=True)
class GitTraceability:
    """Agrupa os dados brutos e as regras de vínculo consumidas pelas páginas."""

    stories: pd.DataFrame
    subtasks: pd.DataFrame
    commits: pd.DataFrame
    branches: pd.DataFrame
    prs: pd.DataFrame
    known_keys: set[str]

    def commits_for_task(self, task: pd.Series) -> pd.DataFrame:
        """Commits humanos que citam a chave da própria task na mensagem."""
        if self.commits.empty:
            return self.commits
        commits = domain_commits_for_item(self.commits, task, self.known_keys)
        return commits[commits["kind"] == "human"]

    def _child_keys(self, story_key: str) -> set[str]:
        return set(self.subtasks.loc[self.subtasks["story_key"] == story_key, "subtask_key"])

    def _story_us_id(self, story_key: str) -> str | None:
        values = self.stories.loc[self.stories["story_key"] == story_key, "us_id"]
        return values.iloc[0] if len(values) and pd.notna(values.iloc[0]) else None

    def story_references(self, story_key: str) -> StoryReferences:
        """Retorna branches, PRs e commits humanos da Story sem Subtask específica."""
        children = self._child_keys(story_key)
        us_id = self._story_us_id(story_key)
        branches = branches_for_story(self.branches, story_key, us_id, children, self.known_keys)
        prs = prs_for_story(self.prs, story_key, us_id, children, self.known_keys)
        commits = story_level_commits(self.commits, story_key, us_id, children, self.known_keys)
        human_commits = commits[commits["kind"] == "human"] if not commits.empty else commits
        return branches, prs, human_commits

    @staticmethod
    def task_code(task: pd.Series) -> str:
        """Código curto da task, usando a chave Jira quando não há código visual."""
        return task["subtask_code"] if pd.notna(task.get("subtask_code")) else task["subtask_key"]

    def summarize_git(self, tasks: pd.DataFrame) -> pd.DataFrame:
        """Resume commits e possíveis divergências para as tabelas de Issues e Git."""
        rows = []
        for _, task in tasks.iterrows():
            commits = self.commits_for_task(task)
            count, delivered = len(commits), int(commits["delivered"].sum()) if len(commits) else 0
            alert = ""
            if task["status_group"] == S.CONCLUIDA and count == 0:
                alert = "⚠️ Possível inconsistência: concluída sem commits vinculados"
            elif task["status_group"] == S.CONCLUIDA and delivered == 0:
                alert = "⚠️ Possível inconsistência: concluída, mas sem entrega (main ou PR merged)"
            elif task["status_group"] == S.PENDENTE and count > 0:
                alert = "ℹ️ Tem commits, mas está Pendente"
            rows.append({
                "Task": self.task_code(task),
                "User Story": task["us_id"] if pd.notna(task["us_id"]) else "—",
                "Resumo": task["subtask_summary"],
                "Dev": nome_exibicao(task["assignee"]),
                "Status": task["status_group"],
                "Horas": round(task["time_spent_h"], 1),
                "Estimado (h)": task["estimate_h"],
                "Commits": count,
                "Entregues": delivered,
                "Em branch": count - delivered,
                "Branches": ", ".join(sorted({branch for values in commits["branches"] for branch in values})) if count else "",
                "Alerta": alert,
                "subtask_key": task["subtask_key"],
            })
        return pd.DataFrame(rows, columns=[
            "Task", "User Story", "Resumo", "Dev", "Status", "Horas", "Estimado (h)", "Commits",
            "Entregues", "Em branch", "Branches", "Alerta", "subtask_key",
        ])
