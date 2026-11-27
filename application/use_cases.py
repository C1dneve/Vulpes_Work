"""Casos de uso puros para construir o escopo e as visões de gestão."""
from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from domain import timeutil
from domain.thresholds import Thresholds
from services import mgmt
from services.context import Bundle, Context, Scope, apply_context
from services.mgmt import Mgmt


class BuildScope:
    """Aplica o mesmo Context aos dados Jira e GitHub, sem depender da interface."""

    def __init__(self, builder: Callable[[Bundle, Context], Scope] = apply_context) -> None:
        self._builder = builder

    def execute(self, bundle: Bundle, context: Context) -> Scope:
        return self._builder(bundle, context)


class BuildManagement:
    """Calcula KPIs, alertas e visões com relógio e construtor injetáveis."""

    def __init__(
        self,
        *,
        builder: Callable[..., Mgmt] | None = None,
        clock: Callable[[], pd.Timestamp] = timeutil.now,
    ) -> None:
        self._builder = builder
        self._clock = clock

    def execute(
        self,
        bundle: Bundle,
        context: Context,
        thresholds: Thresholds,
        *,
        now: pd.Timestamp | None = None,
        github_ok: bool = True,
        github_since: pd.Timestamp | None = None,
        history_unknown: set[str] | frozenset[str] = frozenset(),
        github_partial: bool = False,
        github_stale: bool = False,
    ) -> Mgmt:
        effective_now = self._clock() if now is None else now
        # Resolve o adaptador no momento da execução para preservar a substituição
        # de services.mgmt.build_mgmt usada pelos testes de integração com fakes.
        builder = self._builder if self._builder is not None else mgmt.build_mgmt
        return builder(
            bundle,
            context,
            thresholds,
            now=effective_now,
            github_ok=github_ok,
            github_since=github_since,
            history_unknown=history_unknown,
            github_partial=github_partial,
            github_stale=github_stale,
        )
