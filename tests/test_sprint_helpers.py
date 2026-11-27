"""Testes dos cálculos de período e evolução diária usados pelas telas de Sprint."""
import pandas as pd

from domain import statuses as S
from services.context import Context
from views.sprint_helpers import SprintAnalytics

TZ = "America/Sao_Paulo"


def ts(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz=TZ)


def analytics() -> SprintAnalytics:
    stories = pd.DataFrame([
        {"story_key": "JH-100", "sprint_start": ts("2026-09-21"), "sprint_end": ts("2026-10-05"), "sprint": "Sprint 5"}
    ])
    sprints = pd.DataFrame([
        {"name": "Sprint 5", "start": ts("2026-09-21"), "end": ts("2026-10-05")}
    ])
    changelog = pd.DataFrame([
        {"subtask_key": "JH-101", "ts": ts("2026-09-29 09:00"), "date": pd.Timestamp("2026-09-29"), "to_group": S.ANALISE},
        {"subtask_key": "JH-101", "ts": ts("2026-09-30 09:00"), "date": pd.Timestamp("2026-09-30"), "to_group": S.ANDAMENTO},
        {"subtask_key": "JH-102", "ts": ts("2026-09-29 10:00"), "date": pd.Timestamp("2026-09-29"), "to_group": S.CONCLUIDA},
        {"subtask_key": "JH-999", "ts": ts("2026-09-29 11:00"), "date": pd.Timestamp("2026-09-29"), "to_group": S.BLOQUEADA},
    ])
    return SprintAnalytics(
        stories=stories,
        sprints=sprints,
        context=Context(sprint="Sprint 5", story_keys=("JH-100",)),
        worklogs=pd.DataFrame(columns=["date"]),
        changelog=changelog,
        scoped_items=pd.DataFrame([{"subtask_key": "JH-101"}, {"subtask_key": "JH-102"}]),
    )


def test_sprint_dates_use_board_dates() -> None:
    assert analytics().dates() == (pd.Timestamp("2026-09-21"), pd.Timestamp("2026-10-05"))


def test_daily_interval_caps_at_today_and_can_include_full_sprint(monkeypatch) -> None:
    monkeypatch.setattr("views.sprint_helpers.timeutil.today", lambda: pd.Timestamp("2026-09-30"))
    helpers = analytics()

    current = helpers.daily_interval()
    full = helpers.daily_interval(ate_hoje=False)

    assert current[0] == pd.Timestamp("2026-09-21")
    assert current[-1] == pd.Timestamp("2026-09-30")
    assert full[-1] == pd.Timestamp("2026-10-05")


def test_sprint_not_started_uses_local_today(monkeypatch) -> None:
    monkeypatch.setattr("views.sprint_helpers.timeutil.today", lambda: pd.Timestamp("2026-09-20"))
    assert analytics().not_started()


def test_status_series_reconstructs_only_scoped_items() -> None:
    helpers = analytics()
    days = pd.date_range("2026-09-29", "2026-09-30")

    result = helpers.status_series(days).set_index("data")

    first = result.loc[pd.Timestamp("2026-09-29")]
    second = result.loc[pd.Timestamp("2026-09-30")]
    assert first[S.ANALISE] == 1 and first[S.CONCLUIDA] == 1
    assert second[S.ANDAMENTO] == 1 and second[S.CONCLUIDA] == 1
    assert first[S.BLOQUEADA] == 0  # a alteração de JH-999 não pertence ao contexto
    assert first["Andamento (total)"] == 1 and second["Andamento (total)"] == 1
