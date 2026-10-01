"""MVP / Fase 2 — regras de gestão: prazo, estimativa x realizado, bloqueio, inatividade, lado BE/FE, formatação."""
import pandas as pd
import pytest

from domain import fmt
from domain import statuses as S
from domain import work as W
from domain.thresholds import Thresholds, parse_thresholds

TZ = "America/Sao_Paulo"
NOW = pd.Timestamp("2026-09-30 10:00", tz=TZ)          # quarta-feira
TODAY = pd.Timestamp("2026-09-30")
TH = Thresholds()


def ts(s):
    return pd.Timestamp(s, tz=TZ)


# ---------------------------------------------------------------- due date
@pytest.mark.parametrize("due,group,expected", [
    (None, S.ANDAMENTO, W.DUE_NONE), ("", S.ANDAMENTO, W.DUE_NONE), (float("nan"), S.PENDENTE, W.DUE_NONE),
    ("2026-09-29", S.ANDAMENTO, W.DUE_LATE),          # ontem
    ("2026-09-30", S.ANDAMENTO, W.DUE_SOON),          # hoje ainda NÃO é atraso
    ("2026-10-02", S.PENDENTE, W.DUE_SOON),           # faltam 2 dias (limiar padrão = 2)
    ("2026-10-03", S.PENDENTE, W.DUE_OK),             # faltam 3
    ("2026-09-01", S.CONCLUIDA, W.DUE_DONE),          # concluída nunca é atrasada
    ("2026-10-10T00:00:00.000-0300", S.TESTE, W.DUE_OK),
])
def test_due_status(due, group, expected):
    assert W.due_status(due, group, TODAY, TH) == expected


def test_due_soon_threshold_is_configurable_and_centralized():
    assert W.due_status("2026-10-03", S.ANDAMENTO, TODAY, Thresholds(due_soon_days=3)) == W.DUE_SOON
    assert W.days_to_due("2026-10-03", TODAY) == 3 and W.days_to_due(None, TODAY) is None


def test_thresholds_come_from_config_and_bad_values_fall_back_with_a_warning():
    problems: list[str] = []
    th = parse_thresholds({"due_soon_days": 4, "inactive_business_days": 0, "pr_old_days": "x", "zzz": 1}, problems)
    assert th.due_soon_days == 4 and th.inactive_business_days == 2 and th.pr_old_days == 5
    assert len(problems) == 3 and any("zzz" in p for p in problems)
    assert parse_thresholds(None, problems) == Thresholds()


def test_settings_load_management_section(tmp_path):
    import json

    from settings import load_settings
    from tests.conftest import ENV
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"github": {"org": "T", "repos": ["r"]}, "management": {"inactive_business_days": 3},
                               "jira": {"story_points_field": "customfield_10016"}}))
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    assert s.management.inactive_business_days == 3 and s.jira.story_points_field == "customfield_10016"
    cfg.write_text(json.dumps({"github": {"org": "T", "repos": ["r"]}, "jira": {"story_points_field": "sp; drop"}}))
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    assert s.jira.story_points_field == "" and any("story_points_field" in p for p in s.problems)


# ---------------------------------------------------------------- estimativa x realizado
def test_remaining_from_jira_wins_and_is_labeled():
    e = W.effort(8, 5, 2.5)
    assert (e.estimate_h, e.logged_h, e.remaining_h, e.remaining_source, e.diff_h) == (8, 5, 2.5, "jira", -3)


def test_remaining_is_calculated_only_when_jira_does_not_provide_it():
    e = W.effort(8, 5, None)
    assert e.remaining_h == 3 and e.remaining_source == "calculado"


def test_remaining_is_not_invented_without_estimate_nor_jira_remaining():
    e = W.effort(None, 5, None)
    assert e.remaining_h is None and e.remaining_source is None and e.diff_h is None and e.logged_h == 5


def test_overrun_is_positive_diff_and_calculated_remaining_never_negative():
    e = W.effort(4, 6, None)
    assert e.diff_h == 2 and e.remaining_h == 0


def test_jira_zero_remaining_is_respected_as_zero_from_jira():
    e = W.effort(8, 8, 0.0)
    assert e.remaining_h == 0.0 and e.remaining_source == "jira"


def test_rollup_reports_coverage_and_never_turns_missing_into_zero():
    items = pd.DataFrame([{"estimate_h": 4.0, "time_spent_h": 1.0, "remaining_h": 3.0},
                          {"estimate_h": None, "time_spent_h": 2.0, "remaining_h": None},
                          {"estimate_h": 2.0, "time_spent_h": 0.0, "remaining_h": None}])
    r = W.rollup_effort(items)
    assert r["estimate_h"] == 6.0 and r["estimate_coverage"] == "2/3" and r["logged_h"] == 3.0
    assert r["remaining_h"] == 5.0 and r["remaining_partial"]          # 3 (jira) + 2 (calculado); a sem estimativa fica de fora
    none = W.rollup_effort(pd.DataFrame([{"estimate_h": None, "time_spent_h": 1.0, "remaining_h": None}]))
    assert none["estimate_h"] is None and none["remaining_h"] is None and none["estimate_coverage"] == "0/1"


@pytest.mark.parametrize("code,side", [("BE-09", "backend"), ("FE-03", "frontend"), ("UXDB-01", None), (None, None), (float("nan"), None)])
def test_item_side(code, side):
    assert W.item_side(code) == side


# ---------------------------------------------------------------- bloqueio
def item(**kw):
    base = {"status_group": S.ANDAMENTO, "flagged": False, "flagged_since": pd.NaT, "blocked_by": [], "updated": ts("2026-09-30 09:00")}
    return pd.Series({**base, **kw})


NO_CL = pd.DataFrame(columns=["ts", "to_group"])


def test_not_blocked_by_default():
    b = W.block_info(item(), NO_CL, NOW)
    assert not b.is_blocked and b.sources == () and b.reason is None and pd.isna(b.since) and b.hours is None


def test_blocked_by_status_uses_changelog_for_since():
    cl = pd.DataFrame([{"ts": ts("2026-09-28 10:00"), "to_group": S.BLOQUEADA}, {"ts": ts("2026-09-26 10:00"), "to_group": S.ANDAMENTO}])
    b = W.block_info(item(status_group=S.BLOQUEADA), cl, NOW)
    assert b.is_blocked and b.sources == ("status",) and b.hours == 48 and b.reason is None       # motivo NÃO é inventado


def test_blocked_by_flag_and_unknown_since_is_not_invented():
    b = W.block_info(item(flagged=True), NO_CL, NOW)
    assert b.is_blocked and b.sources == ("flag",) and pd.isna(b.since) and b.hours is None and b.reason is None


def test_blocked_by_link_gives_provable_reason():
    b = W.block_info(item(blocked_by=["JH-55 — Liberar ambiente"]), NO_CL, NOW)
    assert b.is_blocked and b.reason == "Bloqueada por JH-55 — Liberar ambiente" and pd.isna(b.since)


def test_multiple_sources_use_earliest_known_since():
    b = W.block_info(item(flagged=True, flagged_since=ts("2026-09-29 10:00"), blocked_by=["JH-1"], status_group=S.BLOQUEADA),
                     pd.DataFrame([{"ts": ts("2026-09-28 10:00"), "to_group": S.BLOQUEADA}]), NOW)
    assert set(b.sources) == {"status", "flag", "link"} and b.hours == 48


# ---------------------------------------------------------------- dias úteis / inatividade
@pytest.mark.parametrize("a,b,n", [("2026-09-25", "2026-09-28", 1),      # sexta -> segunda
                                   ("2026-09-24", "2026-09-28", 2), ("2026-09-28", "2026-09-28", 0),
                                   ("2026-09-26", "2026-09-28", 0),      # sábado -> segunda
                                   ("2026-09-30", "2026-09-28", 0)])
def test_business_days(a, b, n):
    assert W.business_days_between(ts(a), ts(b)) == n


EMPTY_W = pd.DataFrame(columns=["started"])
EMPTY_C = pd.DataFrame(columns=["date"])


def test_activity_in_jira_without_commit_is_not_inactivity():
    a = W.last_activity(item(updated=ts("2026-09-30 08:00")), NO_CL, EMPTY_W, EMPTY_C, NOW, TH)
    assert not a.inactive and a.source == "jira_update" and a.business_days == 0


def test_in_progress_task_without_recent_activity_is_inactive():
    a = W.last_activity(item(updated=ts("2026-09-25 09:00")), NO_CL, EMPTY_W, EMPTY_C, NOW, TH)     # sexta -> quarta = 3 úteis
    assert a.inactive and a.business_days == 3


def test_weekend_does_not_make_monday_morning_inactive():
    monday = pd.Timestamp("2026-09-28 09:00", tz=TZ)
    a = W.last_activity(item(updated=ts("2026-09-25 17:00")), NO_CL, EMPTY_W, EMPTY_C, monday, TH)
    assert a.business_days == 1 and not a.inactive


@pytest.mark.parametrize("group", [S.PENDENTE, S.CONCLUIDA, S.BLOQUEADA])
def test_only_in_progress_tasks_can_be_inactive(group):
    assert not W.last_activity(item(status_group=group, updated=ts("2026-09-01")), NO_CL, EMPTY_W, EMPTY_C, NOW, TH).inactive


def test_newest_signal_wins_and_is_named():
    cl = pd.DataFrame([{"ts": ts("2026-09-27 10:00"), "to_group": S.ANDAMENTO}])
    wl = pd.DataFrame([{"started": ts("2026-09-29 10:00")}])
    cm = pd.DataFrame([{"date": ts("2026-09-30 09:30")}])
    i = item(updated=ts("2026-09-26 10:00"))
    assert W.last_activity(i, cl, EMPTY_W, EMPTY_C, NOW, TH).source == "status"
    assert W.last_activity(i, cl, wl, EMPTY_C, NOW, TH).source == "worklog"
    a = W.last_activity(i, cl, wl, cm, NOW, TH)
    assert a.source == "github" and not a.inactive


def test_threshold_for_inactivity_is_configurable():
    i = item(updated=ts("2026-09-28 09:00"))                       # 2 dias úteis
    assert W.last_activity(i, NO_CL, EMPTY_W, EMPTY_C, NOW, TH).inactive
    assert not W.last_activity(i, NO_CL, EMPTY_W, EMPTY_C, NOW, Thresholds(inactive_business_days=3)).inactive


def test_no_signal_at_all_is_unknown_not_inactive():
    a = W.last_activity(item(updated=pd.NaT), NO_CL, EMPTY_W, EMPTY_C, NOW, TH)
    assert a.business_days is None and not a.inactive and a.source is None


# ---------------------------------------------------------------- formatação
def test_formatting_never_turns_missing_into_zero():
    assert fmt.fmt_hours(None) == "—" and fmt.fmt_hours(float("nan")) == "—" and fmt.fmt_hours(0) == "0h"
    assert fmt.fmt_hours(8) == "8h" and fmt.fmt_hours(1.5) == "1.5h"
    assert fmt.fmt_points(None) == "—" and fmt.fmt_points(5.0) == "5" and fmt.fmt_points(0.5) == "0.5" and fmt.fmt_points(0) == "0"


@pytest.mark.parametrize("h,txt", [(28, "1d 4h"), (48, "2d"), (5, "5h"), (5.5, "5h 30min"), (0.2, "12min"), (0, "<1min"), (None, "—")])
def test_fmt_duration(h, txt):
    assert fmt.fmt_duration(h) == txt
