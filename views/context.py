"""Contextos explícitos entregues por app.py às páginas extraídas.

O contrato é ampliado incrementalmente à medida que cada tela é movida para
views/, evitando que as páginas dependam de variáveis globais do app.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from settings import Settings

if TYPE_CHECKING:
    from application.sync import Loaded
    from services.mgmt import Mgmt


@dataclass(frozen=True)
class PageContext:
    """Dados compartilhados entregues por app.py às páginas extraídas."""

    settings: Settings
    loaded: Loaded
    management: Mgmt
    github_commits: pd.DataFrame
    jira_slugs: set[str]
    subtasks: pd.DataFrame
    stories: pd.DataFrame
    raw_commits: pd.DataFrame
    scoped_items: pd.DataFrame
    scoped_commits: pd.DataFrame
    scoped_branches: pd.DataFrame
    scoped_prs: pd.DataFrame
    scoped_worklogs: pd.DataFrame
