"""Registro de ações das páginas do Development Analytics.

O app.py permanece responsável por selecionar e executar a página ativa. Este
módulo concentra apenas os adaptadores entre o contexto compartilhado e cada
função de renderização.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from views import commits as v_commits
from views import config as v_config
from views import dashboard as v_dashboard
from views import issues as v_issues
from views import now as v_now
from views import people as v_people
from views import reports as v_reports
from views import sprint as v_sprint
from views import timeline as v_timeline
from views.context import PageContext
from views.git_traceability import GitTraceability
from views.modals import ModalContext, dev_selected, modal_task
from views.sprint_helpers import SprintAnalytics

PageAction = Callable[[], None]


def build_page_actions(
    context: PageContext,
    *,
    sprint: str,
    sprint_stories: pd.DataFrame,
    git_traceability: GitTraceability,
    sprint_analytics: SprintAnalytics,
    modal_context: ModalContext,
    save_mapping: Callable[..., None],
    clear_sync: Callable[..., None],
    testar_jira: Callable[..., Any],
    testar_github: Callable[..., Any],
) -> dict[str, PageAction]:
    """Monta as ações das páginas sem executar renderizações antecipadamente."""

    def task_selected(key: str) -> None:
        task = context.subtasks[context.subtasks["subtask_key"] == key].iloc[0]
        modal_task(modal_context, task)

    return {
        "Dashboard": lambda: v_dashboard.render(
            context,
            context.management,
            sprint=sprint,
            sprint_not_started=sprint_analytics.not_started,
            sprint_dates=sprint_analytics.dates,
            daily_interval=sprint_analytics.daily_interval,
            status_series=sprint_analytics.status_series,
            task_code=git_traceability.task_code,
        ),
        "Sprint": lambda: v_sprint.render_page(
            context.management,
            context.settings.jira.domain,
            sprint_analytics.dates()[0],
            sprint_analytics.not_started(),
            sprint_analytics.daily_interval,
            sprint_analytics.status_series,
            sprint_stories,
            context.scoped_items,
            git_traceability.story_references,
            git_traceability.summarize_git,
        ),
        "Agora": lambda: v_now.render(context),
        "Pessoas": lambda: v_people.render(context.management, context.settings.jira.domain),
        "Timeline": lambda: v_timeline.render(context.management, context.settings.jira.domain),
        "Issues": lambda: v_issues.render(
            context.scoped_items,
            summarize=git_traceability.summarize_git,
            on_task_selected=task_selected,
        ),
        "Commits": lambda: v_commits.render(context, summarize_git=git_traceability.summarize_git),
        "Relatórios": lambda: v_reports.render(
            context,
            on_dev_selected=lambda event: dev_selected(modal_context, event),
        ),
        "Configurações": lambda: v_config.render(
            context,
            save_mapping=save_mapping,
            clear_sync=clear_sync,
            testar_jira=testar_jira,
            testar_github=testar_github,
        ),
    }
