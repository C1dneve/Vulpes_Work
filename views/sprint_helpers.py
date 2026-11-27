"""Cálculos compartilhados de datas e séries da Sprint para as telas de Analytics."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from domain import statuses as S
from domain import timeutil
from services.context import Context, sprint_window


@dataclass(frozen=True)
class SprintAnalytics:
    """Agrupa os dados necessários para reconstruir datas e evolução diária da Sprint."""

    stories: pd.DataFrame
    sprints: pd.DataFrame
    context: Context
    worklogs: pd.DataFrame
    changelog: pd.DataFrame
    scoped_items: pd.DataFrame

    def dates(self) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
        """Retorna o período da Sprint selecionada ou a união das Stories do contexto."""
        return sprint_window(self.stories, self.sprints, self.context.sprint, self.context.story_keys)

    def not_started(self) -> bool:
        """Indica se a data local de início da Sprint ainda está no futuro."""
        start, _ = self.dates()
        return start is not None and timeutil.today() < start

    def daily_interval(self, ate_hoje: bool = True) -> pd.DatetimeIndex:
        """Cria um intervalo diário válido, sempre incluindo hoje e respeitando as datas da Sprint."""
        start, end = self.dates()
        logs = [frame["date"] for frame in (self.worklogs, self.changelog) if not frame.empty]
        all_dates = pd.concat(logs) if logs else pd.Series(dtype="datetime64[ns]")
        today = timeutil.today()
        start = start if start is not None else (all_dates.min() if not all_dates.empty else today - pd.Timedelta(days=7))
        end = end if end is not None else today
        if ate_hoje:
            end = min(end, today)
        # Mantém pelo menos dois pontos e inclui hoje mesmo se a Sprint ainda não começou ou já terminou.
        return pd.date_range(min(start, end, today), max(start, end, today))

    def status_series(self, days: pd.DatetimeIndex) -> pd.DataFrame:
        """Reconstrói o total de tasks por grupo de status em cada dia usando o changelog do Jira."""
        changelog = (
            self.changelog[self.changelog["subtask_key"].isin(self.scoped_items["subtask_key"])].sort_values("ts")
            if not self.changelog.empty
            else self.changelog
        )
        history = (
            {
                key: list(zip(group["date"], group["to_group"], strict=True))
                for key, group in changelog.groupby("subtask_key")
            }
            if not changelog.empty
            else {}
        )
        rows = []
        for day in days:
            counts = {group: 0 for group in S.GRUPOS}
            for key in self.scoped_items["subtask_key"]:
                current = None
                for changed_at, group in history.get(key, []):
                    if changed_at <= day:
                        current = group
                    else:
                        break
                if current in counts:
                    counts[current] += 1
            rows.append({"data": day, **counts, "Andamento (total)": sum(counts[group] for group in S.EM_PROGRESSO)})
        return pd.DataFrame(rows)
