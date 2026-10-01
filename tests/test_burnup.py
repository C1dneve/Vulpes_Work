"""MVP / Fase 7 — Burnup: escopo, concluído, alteração de escopo (quando suportada), ausência de Story Points."""
import pandas as pd

from domain import statuses as S
from domain.burnup import burnup

TZ = "America/Sao_Paulo"
NOW = pd.Timestamp("2026-09-30 12:00", tz=TZ)
SPRINT = {"name": "Sprint 5", "id": 5, "start": pd.Timestamp("2026-09-21 00:00", tz=TZ), "end": pd.Timestamp("2026-10-05 23:59", tz=TZ),
          "complete": pd.NaT, "state": "active"}


def ts(s):
    return pd.Timestamp(s, tz=TZ)


def it(key, created, group=S.ANDAMENTO, sprint="Sprint 5", story="JH-100", who="ana", resolved=None):
    return {"subtask_key": key, "story_key": story, "sprint": sprint, "assignee": who, "created": ts(created), "status_group": group,
            "resolved": ts(resolved) if resolved else pd.NaT}


def st(key, sp, group=S.ANDAMENTO, resolved=None):
    return {"story_key": key, "story_points": sp, "status_group": group, "resolved": ts(resolved) if resolved else pd.NaT}


def cl(*rows):   # (key, 'YYYY-MM-DD HH:MM', from_group, to_group)
    return pd.DataFrame([{"subtask_key": k, "ts": ts(w), "date": pd.Timestamp(w[:10]), "from_group": f, "to_group": t} for k, w, f, t in rows],
                        columns=["subtask_key", "ts", "date", "from_group", "to_group"])


def sev(*rows):  # (key, when, from_names, to_names)  ids = nomes "Sprint N" -> N
    def ids(names):
        return [n.split()[-1] for n in names]
    return pd.DataFrame([{"subtask_key": k, "ts": ts(w), "date": pd.Timestamp(w[:10]), "from_ids": ids(f), "to_ids": ids(t),
                          "from_names": f, "to_names": t} for k, w, f, t in rows],
                        columns=["subtask_key", "ts", "date", "from_ids", "to_ids", "from_names", "to_names"])


NO_EV = sev()
NO_CL = cl()


def scope_at(b, day):
    return b.days.set_index("date").loc[pd.Timestamp(day), "scope_items"]


def done_at(b, day):
    return b.days.set_index("date").loc[pd.Timestamp(day), "done_items"]


def base_items():
    return pd.DataFrame([
        it("JH-101", "2026-09-15"),                                     # criada antes da sprint, sem eventos: presente desde o início
        it("JH-102", "2026-09-23"),                                     # criada DEPOIS do início: escopo adicionado
        it("JH-103", "2026-09-10"),                                     # entra por evento em 25/09
        it("JH-104", "2026-09-10", sprint="Sprint 6")])                 # saiu da sprint em 26/09 (hoje está na 6)


def base_events():
    return sev(("JH-103", "2026-09-25 09:00", ["Sprint 4"], ["Sprint 4", "Sprint 5"]),
               ("JH-104", "2026-09-26 09:00", ["Sprint 5"], ["Sprint 6"]))


def test_scope_is_not_constant_it_follows_entries_and_exits():
    b = burnup(base_items(), pd.DataFrame(), NO_CL, base_events(), SPRINT, NOW)
    s = b.days.set_index("date")["scope_items"]
    assert s[pd.Timestamp("2026-09-21")] == 2          # JH-101 + JH-104 (estava na sprint desde o começo)
    assert s[pd.Timestamp("2026-09-23")] == 3          # + JH-102 criada
    assert s[pd.Timestamp("2026-09-25")] == 4          # + JH-103 entrou por evento
    assert s[pd.Timestamp("2026-09-26")] == 3          # − JH-104 saiu
    assert s.nunique() > 1 and b.days["date"].max() == pd.Timestamp("2026-09-30")     # série para em HOJE: sem escopo futuro


def test_scope_changes_after_start_are_listed_with_their_basis():
    ch = burnup(base_items(), pd.DataFrame(), NO_CL, base_events(), SPRINT, NOW).changes
    got = {(r["key"], r["change"], r["basis"]) for _, r in ch.iterrows()}
    assert got == {("JH-102", "entrou", "approx"), ("JH-103", "entrou", "events"), ("JH-104", "saiu", "events")}


def test_basis_counts_events_versus_approximation():
    b = burnup(base_items(), pd.DataFrame(), NO_CL, base_events(), SPRINT, NOW)
    assert b.basis == {"events": 2, "approx": 2} and any("sem evento de Sprint" in n for n in b.notes)


def test_done_work_uses_status_history_and_reopening_discounts():
    items = base_items().iloc[:2]
    c = cl(("JH-101", "2026-09-24 10:00", S.ANDAMENTO, S.CONCLUIDA), ("JH-101", "2026-09-28 10:00", S.CONCLUIDA, S.ANDAMENTO))
    b = burnup(items, pd.DataFrame(), c, NO_EV, SPRINT, NOW)
    assert done_at(b, "2026-09-23") == 0 and done_at(b, "2026-09-24") == 1 and done_at(b, "2026-09-27") == 1
    assert done_at(b, "2026-09-28") == 0                                              # reaberta: some do concluído


def test_done_item_without_history_uses_resolution_date_and_undated_is_reported_not_guessed():
    items = pd.DataFrame([it("JH-101", "2026-09-15", S.CONCLUIDA, resolved="2026-09-25 10:00"), it("JH-102", "2026-09-15", S.CONCLUIDA)])
    b = burnup(items, pd.DataFrame(), NO_CL, NO_EV, SPRINT, NOW)
    assert done_at(b, "2026-09-24") == 0 and done_at(b, "2026-09-25") == 1
    assert b.undated_done == ["JH-102"] and any("JH-102" in n for n in b.notes)      # sem data: fora do concluído, e dito


def test_completed_work_is_always_within_scope():
    b = burnup(base_items(), pd.DataFrame(), cl(("JH-104", "2026-09-22 10:00", S.ANDAMENTO, S.CONCLUIDA)), base_events(), SPRINT, NOW)
    d = b.days.set_index("date")
    assert d.loc[pd.Timestamp("2026-09-22"), "done_items"] == 1 and d.loc[pd.Timestamp("2026-09-27"), "done_items"] == 0   # saiu: não conta
    assert (d["done_items"] <= d["scope_items"]).all()


# ---------------------------------------------------------------- Story Points
def test_story_points_planned_and_done_follow_story_scope_and_story_status():
    items = pd.DataFrame([it("JH-101", "2026-09-15", story="JH-100"), it("JH-201", "2026-09-24", story="JH-200")])
    stories = pd.DataFrame([st("JH-100", 5, S.CONCLUIDA, resolved="2026-09-27 10:00"), st("JH-200", 3)])
    b = burnup(items, stories, NO_CL, NO_EV, SPRINT, NOW)
    assert b.sp_available and b.sp_missing == 0
    d = b.days.set_index("date")
    assert d.loc[pd.Timestamp("2026-09-21"), "scope_sp"] == 5 and d.loc[pd.Timestamp("2026-09-24"), "scope_sp"] == 8
    assert d.loc[pd.Timestamp("2026-09-26"), "done_sp"] == 0 and d.loc[pd.Timestamp("2026-09-27"), "done_sp"] == 5


def test_story_without_points_is_missing_never_zero_in_the_sum():
    items = pd.DataFrame([it("JH-101", "2026-09-15", story="JH-100"), it("JH-201", "2026-09-15", story="JH-200")])
    b = burnup(items, pd.DataFrame([st("JH-100", 5), st("JH-200", None)]), NO_CL, NO_EV, SPRINT, NOW)
    assert b.sp_available and b.sp_missing == 1 and b.days["scope_sp"].iloc[-1] == 5


def test_no_story_points_at_all_makes_sp_unavailable_and_keeps_item_burnup():
    items = pd.DataFrame([it("JH-101", "2026-09-15"), it("JH-102", "2026-09-15")])
    b = burnup(items, pd.DataFrame([st("JH-100", None)]), NO_CL, NO_EV, SPRINT, NOW)
    assert not b.sp_available and b.days["scope_sp"].isna().all() and b.days["done_sp"].isna().all()
    assert b.days["scope_items"].iloc[-1] == 2


# ---------------------------------------------------------------- sprint encerrada, filtros, bordas
def test_carry_over_at_the_end_of_a_closed_sprint_is_not_a_scope_reduction():
    closed = {**SPRINT, "state": "closed", "end": ts("2026-10-02 18:00"), "complete": ts("2026-10-02 18:30")}
    items = pd.DataFrame([it("JH-101", "2026-09-15", sprint="Sprint 6")])
    carry = sev(("JH-101", "2026-10-02 18:31", ["Sprint 5"], ["Sprint 6"]))
    b = burnup(items, pd.DataFrame(), NO_CL, carry, closed, ts("2026-10-20 10:00"))
    assert b.days["scope_items"].iloc[-1] == 1 and b.days["date"].max() == pd.Timestamp("2026-10-02")   # fecha na data de fim da sprint
    assert b.changes.empty


def test_mid_sprint_exit_of_a_closed_sprint_is_a_real_reduction():
    closed = {**SPRINT, "state": "closed", "end": ts("2026-10-02 18:00"), "complete": ts("2026-10-02 18:30")}
    items = pd.DataFrame([it("JH-101", "2026-09-15", sprint="Sprint 6")])
    b = burnup(items, pd.DataFrame(), NO_CL, sev(("JH-101", "2026-09-25 10:00", ["Sprint 5"], ["Sprint 6"])), closed, ts("2026-10-20 10:00"))
    assert b.days.set_index("date").loc[pd.Timestamp("2026-09-26"), "scope_items"] == 0 and not b.changes.empty


def test_assignee_and_story_filters_narrow_the_scope():
    items = pd.DataFrame([it("JH-101", "2026-09-15", who="ana"), it("JH-102", "2026-09-15", who="zeca"),
                          it("JH-201", "2026-09-15", story="JH-200", who="ana")])
    assert burnup(items, pd.DataFrame(), NO_CL, NO_EV, SPRINT, NOW, assignee="ana").days["scope_items"].iloc[-1] == 2
    assert burnup(items, pd.DataFrame(), NO_CL, NO_EV, SPRINT, NOW, story_keys={"JH-200"}).days["scope_items"].iloc[-1] == 1


def test_items_from_other_sprints_are_ignored():
    items = pd.DataFrame([it("JH-101", "2026-09-15"), it("JH-901", "2026-09-15", sprint="Sprint 4", story="JH-900")])
    assert burnup(items, pd.DataFrame(), NO_CL, NO_EV, SPRINT, NOW).days["scope_items"].iloc[-1] == 1


def test_sprint_not_started_or_without_start_date_returns_a_note_not_a_chart():
    future = {**SPRINT, "start": ts("2026-12-01"), "end": ts("2026-12-15")}
    assert burnup(base_items(), pd.DataFrame(), NO_CL, NO_EV, future, NOW).days.empty
    nostart = {**SPRINT, "start": pd.NaT}
    r = burnup(base_items(), pd.DataFrame(), NO_CL, NO_EV, nostart, NOW)
    assert r.days.empty and "início" in r.notes[0]


def test_no_items_gives_a_zero_series_not_an_error():
    b = burnup(base_items().iloc[0:0], pd.DataFrame(), NO_CL, NO_EV, SPRINT, NOW)
    assert (b.days["scope_items"] == 0).all() and not b.sp_available
