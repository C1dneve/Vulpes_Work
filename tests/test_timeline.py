"""MVP / Fase 6 — Timeline: um evento por fato, em ordem cronológica, sem inventar o que não foi coletado."""
import pandas as pd

from domain import statuses as S
from domain import timeline as T

TZ = "America/Sao_Paulo"


def ts(s):
    return pd.Timestamp(s, tz=TZ)


ITEMS = pd.DataFrame([{"subtask_key": "JH-101", "subtask_summary": "BE-01 Validar", "assignee": "ana", "created": ts("2026-09-22 08:00"),
                       "issue_type": "Sub-task", "status_group": S.CONCLUIDA, "status_name": "Concluído", "resolved": ts("2026-09-29 18:00")}])
CL = pd.DataFrame([{"subtask_key": "JH-101", "ts": ts("2026-09-23 09:00"), "author": "ana", "from_name": "A fazer", "to_name": "Em andamento",
                    "from_group": S.PENDENTE, "to_group": S.ANDAMENTO},
                   {"subtask_key": "JH-101", "ts": ts("2026-09-29 17:30"), "author": "ana", "from_name": "Em teste", "to_name": "Concluído",
                    "from_group": S.TESTE, "to_group": S.CONCLUIDA}])
WL = pd.DataFrame([{"subtask_key": "JH-101", "author": "ana", "started": ts("2026-09-23 10:00"), "time_spent_h": 2.0}])
CM = pd.DataFrame([{"sha": "abcdef1234", "jira_key": "JH-101", "title": "feat(JH-101): validar", "author": "ana", "date": ts("2026-09-24 11:00"),
                    "url": "u", "kind": "human"},
                   {"sha": "bot1111", "jira_key": None, "title": "chore", "author": "dependabot", "date": ts("2026-09-24 12:00"), "url": "u", "kind": "bot"},
                   {"sha": "nokey22", "jira_key": None, "title": "wip", "author": "zeca", "date": ts("2026-09-24 13:00"), "url": "u", "kind": "human"}])
PRS = pd.DataFrame([{"number": 7, "title": "[JH-100] US2.1", "author": "ana", "created": ts("2026-09-25 09:00"), "draft": False, "url": "pu",
                     "first_review_at": ts("2026-09-26 09:00"), "last_review_at": ts("2026-09-27 09:00"), "last_review_state": "approved",
                     "merged_at": ts("2026-09-28 09:00"), "base": "main"},
                    {"number": 8, "title": "[JH-100] outra", "author": "zeca", "created": ts("2026-09-29 09:00"), "draft": True, "url": "pu2",
                     "first_review_at": pd.NaT, "last_review_at": pd.NaT, "last_review_state": None, "merged_at": pd.NaT, "base": "main"}])


def tl():
    return T.build_timeline(ITEMS, CL, WL, CM, PRS)


def test_every_event_type_in_the_prompt_is_produced():
    assert set(tl()["type"]) == set(T.EVENT_TYPES)


def test_events_are_chronological_with_local_dates():
    t = tl()
    assert t["ts"].is_monotonic_increasing and list(t.columns) == T.TL_COLS
    assert t.iloc[0]["type"] == T.EV_CREATED and t.iloc[-1]["ts"] == ts("2026-09-29 17:30")        # a conclusão vem depois da PR #8 (09:00)
    pos = {r["key"]: i for i, r in t.iterrows() if r["type"] == T.EV_PR_OPEN}
    assert pos["PR #7"] < pos["PR #8"] < t.index[t["type"] == T.EV_DONE][0]
    assert t["date"].iloc[0] == pd.Timestamp("2026-09-22")


def test_completion_event_uses_the_status_change_not_the_resolution_field():
    d = tl().query("type == @T.EV_DONE").iloc[0]
    assert d["ts"] == ts("2026-09-29 17:30") and d["key"] == "JH-101"
    no_hist = T.build_timeline(ITEMS, CL.iloc[0:0], WL.iloc[0:0], CM.iloc[0:0], PRS.iloc[0:0])
    assert no_hist.query("type == @T.EV_DONE").iloc[0]["ts"] == ts("2026-09-29 18:00")        # fallback: resolução do Jira


def test_only_human_commits_and_missing_key_is_explicit():
    c = tl().query("type == @T.EV_COMMIT")
    assert set(c["key"]) == {"JH-101", "(sem chave)"} and "dependabot" not in set(c["person"])


def test_pr_review_events_exist_only_when_reviews_exist():
    t = tl()
    rev = t.query("type == @T.EV_PR_REVIEW")
    assert rev["key"].tolist() == ["PR #7", "PR #7"] and "última revisão (approved)" in rev["detail"].iloc[1]
    assert t.query("type == @T.EV_PR_MERGE")["key"].tolist() == ["PR #7"]
    assert t.query("type == @T.EV_PR_OPEN").set_index("key").loc["PR #8", "detail"] == "rascunho"


def test_worklog_and_status_change_events_carry_who_and_what():
    t = tl()
    assert t.query("type == @T.EV_WORKLOG").iloc[0]["detail"] == "2h registradas"
    assert "A fazer → Em andamento" in set(t.query("type == @T.EV_STATUS")["detail"])


def test_empty_inputs_give_an_empty_timeline_with_columns():
    e = T.build_timeline(ITEMS.iloc[0:0], CL.iloc[0:0], WL.iloc[0:0], CM.iloc[0:0], PRS.iloc[0:0])
    assert e.empty and list(e.columns) == T.TL_COLS
