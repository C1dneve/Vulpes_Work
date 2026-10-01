"""MVP / Fase 1 — dados do Jira: Story Points, campos da Story, prioridade, bloqueios, eventos de Sprint."""
from dataclasses import replace

import pandas as pd

from tests.test_jira_service import SPRINT, build, hist, issue

SP_CATALOG = [{"id": "customfield_10016", "name": "Story point estimate", "custom": True},
              {"id": "customfield_10021", "name": "Flagged", "custom": True},
              {"id": "summary", "name": "Summary", "custom": False}]


def story(**extra):
    return issue("JH-100", "US#1.1 Cadastro", subtasks=["JH-101", "JH-102"], sprint=SPRINT, **extra)


def sub(key="JH-101", **extra):
    return issue(key, "BE-09 Validar", "Sub-task", ("Em andamento", "indeterminate"), "JH-100", assignee="Samuel Martins", **extra)


# ---------------------------------------------------------------- Story Points
def test_story_points_are_discovered_by_field_name_and_requested(settings, mapper):
    svc, http = build(settings, mapper, [story(customfield_10016=5), sub(), sub("JH-102")], fields_catalog=SP_CATALOG)
    res = svc.fetch()
    assert res.ok
    st = res.data.stories.set_index("story_key").loc["JH-100"]
    assert st["story_points"] == 5.0
    board_call = next(p for _, u, p in http.log if u.endswith("/board/7/issue"))
    assert "customfield_10016" in board_call["fields"] and "customfield_10021" in board_call["fields"]


def test_missing_story_points_stay_none_never_zero(settings, mapper):
    svc, _ = build(settings, mapper, [story(customfield_10016=None), sub(), sub("JH-102")], fields_catalog=SP_CATALOG)
    d = svc.fetch().data
    assert d.stories["story_points"].isna().all() and d.items["story_points"].isna().all()


def test_story_points_value_must_be_a_number(settings, mapper):
    svc, _ = build(settings, mapper, [story(customfield_10016="5"), sub(customfield_10016=True), sub("JH-102", customfield_10016=3)],
                   fields_catalog=SP_CATALOG)
    d = svc.fetch().data
    assert pd.isna(d.stories.iloc[0]["story_points"])                 # texto não é número: ausente
    assert d.items.set_index("subtask_key").loc["JH-102", "story_points"] == 3.0
    assert pd.isna(d.items.set_index("subtask_key").loc["JH-101", "story_points"])   # bool não vira 1


def test_no_story_points_field_is_a_permanent_limitation_not_a_partial_result(settings, mapper):
    res = build(settings, mapper, [story(), sub(), sub("JH-102")], fields_catalog=[])[0].fetch()
    assert res.ok and not res.partial                                   # não encurta o TTL do cache
    assert "indisponível" in res.stats["story_points_field"]
    assert res.data.stories["story_points"].isna().all()


def test_explicit_config_beats_discovery(settings, mapper):
    cfg = replace(settings, jira=replace(settings.jira, story_points_field="customfield_10026"))
    svc, _ = build(cfg, mapper, [story(customfield_10026=8, customfield_10016=5), sub(), sub("JH-102")], fields_catalog=SP_CATALOG)
    assert svc.fetch().data.stories.iloc[0]["story_points"] == 8.0


def test_ambiguous_story_points_fields_are_resolved_by_the_board_estimation(settings, mapper):
    catalog = SP_CATALOG + [{"id": "customfield_10026", "name": "Story Points", "custom": True}]
    board_cfg = (r"/board/7/configuration$", {"estimation": {"type": "field", "field": {"fieldId": "customfield_10026"}}})
    svc, http = build(settings, mapper, [story(customfield_10016=5, customfield_10026=13), sub(), sub("JH-102")],
                      fields_catalog=catalog, extra=[board_cfg])
    res = svc.fetch()
    assert res.data.stories.iloc[0]["story_points"] == 13.0 and res.ok


# ---------------------------------------------------------------- campos da Story
def test_story_rows_carry_their_own_status_assignee_due_date_and_priority(settings, mapper):
    s = issue("JH-100", "US#1.1 Cadastro", subtasks=["JH-101"], sprint=SPRINT, status=("Em análise", "indeterminate"),
              assignee="Cid Daniel", duedate="2026-10-02", priority={"name": "High"})
    st = build(settings, mapper, [s, sub()])[0].fetch().data.stories.iloc[0]
    assert (st["status_name"], st["status_group"], st["assignee"]) == ("Em análise", "Em Análise", "cid-daniel")
    assert st["due_date"] == "2026-10-02" and st["priority"] == "High"


def test_estimate_and_time_spent_of_story_are_none_when_jira_has_none(settings, mapper):
    st = build(settings, mapper, [story(), sub(), sub("JH-102")])[0].fetch().data.stories.iloc[0]
    assert pd.isna(st["estimate_h"]) and pd.isna(st["time_spent_h"])


# ---------------------------------------------------------------- bloqueios
def link(key, status_cat, kind="Blocks", inward="is blocked by", summary="Liberar ambiente"):
    return {"type": {"name": kind, "inward": inward, "outward": "blocks"},
            "inwardIssue": {"key": key, "fields": {"summary": summary, "status": {"name": "x", "statusCategory": {"key": status_cat}}}}}


def test_unresolved_blockers_are_listed_with_their_summary(settings, mapper):
    s = sub(issuelinks=[link("JH-55", "indeterminate"), link("JH-56", "done"), link("JH-57", "new", kind="Relates", inward="relates to")])
    it = build(settings, mapper, [story(), s, sub("JH-102")])[0].fetch().data.items.set_index("subtask_key")
    assert it.loc["JH-101", "blocked_by"] == ["JH-55 — Liberar ambiente"]     # concluído e "relates to" não bloqueiam
    assert it.loc["JH-102", "blocked_by"] == []


def test_flagged_since_comes_from_the_last_flag_event_and_only_while_flagged(settings, mapper):
    def flag(hid, when, on):
        return {"id": hid, "created": when, "author": {"displayName": "Samuel Martins", "accountId": "a"},
                "items": [{"field": "Flagged", "fromString": None if on else "Impediment", "toString": "Impediment" if on else None}]}
    hs = {"JH-101": [flag("1", "2026-09-22T10:00:00.000-0300", True), flag("2", "2026-09-23T10:00:00.000-0300", False),
                     flag("3", "2026-09-24T09:00:00.000-0300", True)],
          "JH-102": [flag("4", "2026-09-22T10:00:00.000-0300", True), flag("5", "2026-09-23T10:00:00.000-0300", False)]}
    subs = [sub(customfield_10021=[{"value": "Impediment"}]), sub("JH-102", customfield_10021=None)]
    it = build(settings, mapper, [story(), *subs], histories=hs, fields_catalog=SP_CATALOG)[0].fetch().data.items.set_index("subtask_key")
    assert it.loc["JH-101", "flagged"] and it.loc["JH-101", "flagged_since"] == pd.Timestamp("2026-09-24 09:00", tz="America/Sao_Paulo")
    assert not it.loc["JH-102", "flagged"] and pd.isna(it.loc["JH-102", "flagged_since"])


def test_flagged_without_history_has_unknown_since(settings, mapper):
    it = build(settings, mapper, [story(), sub(flagged=True), sub("JH-102")])[0].fetch().data.items.set_index("subtask_key")
    assert it.loc["JH-101", "flagged"] and pd.isna(it.loc["JH-101", "flagged_since"])   # não inventa uma data


# ---------------------------------------------------------------- changelog: nomes originais e eventos de Sprint
def test_changelog_keeps_original_status_names_and_sprint_events_are_parsed(settings, mapper):
    sprint_change = {"id": "9", "created": "2026-09-23T08:00:00.000-0300", "author": {"displayName": "Samuel Martins", "accountId": "a"},
                     "items": [{"field": "Sprint", "from": "4", "to": "4, 5", "fromString": "Sprint 4", "toString": "Sprint 4, Sprint 5"}]}
    hs = {"JH-101": [hist("1", "2026-09-22T10:00:00.000-0300", "A fazer", "Em andamento"), sprint_change]}
    d = build(settings, mapper, [story(), sub(), sub("JH-102")], histories=hs)[0].fetch().data
    c = d.changelog.iloc[0]
    assert (c["from_name"], c["to_name"]) == ("A fazer", "Em andamento") and c["to_status"] == "em andamento"
    ev = d.sprint_events.iloc[0]
    assert ev["subtask_key"] == "JH-101" and ev["to_ids"] == ["4", "5"] and ev["to_names"] == ["Sprint 4", "Sprint 5"]
    assert ev["from_names"] == ["Sprint 4"] and ev["date"] == pd.Timestamp("2026-09-23")


def test_worklogs_are_never_attributed_to_another_subtask(settings, mapper):
    def w(i, h):
        return {"id": i, "author": {"displayName": "Samuel Martins", "accountId": "a"}, "started": "2026-09-22T10:00:00.000-0300",
                "timeSpentSeconds": h * 3600}
    d = build(settings, mapper, [story(), sub(), sub("JH-102")], worklogs={"JH-101": [w("1", 2)], "JH-102": [w("2", 5), w("3", 1)]})[0].fetch().data
    assert d.worklogs.groupby("subtask_key")["time_spent_h"].sum().to_dict() == {"JH-101": 2.0, "JH-102": 6.0}
    assert d.items.set_index("subtask_key")["worklog_sum_h"].to_dict() == {"JH-101": 2.0, "JH-102": 6.0}


# ---------------------------------------------------------------- sem N+1 extra
def test_field_discovery_costs_one_call_per_fetch_and_no_board_config_unless_ambiguous(settings, mapper):
    _, http = (lambda b: (b[0].fetch(), b[1]))(build(settings, mapper, [story(), sub(), sub("JH-102")], fields_catalog=SP_CATALOG))
    assert len(http.urls("/rest/api/3/field")) == 1 and not http.urls("/configuration")
    sp2 = SP_CATALOG + [{"id": "customfield_10026", "name": "Story Points", "custom": True}]
    _, http = (lambda b: (b[0].fetch(), b[1]))(build(settings, mapper, [story(), sub(), sub("JH-102")], fields_catalog=sp2))
    assert len(http.urls("/rest/api/3/field")) == 1 and len(http.urls("/configuration")) == 1


def test_no_extra_changelog_or_issue_calls_for_the_new_fields(settings, mapper):
    """Eventos de Sprint e Flagged saem do MESMO changelog já buscado (1 chamada por task), sem chamadas novas."""
    _, http = (lambda b: (b[0].fetch(), b[1]))(build(settings, mapper, [story(), sub(), sub("JH-102")], fields_catalog=SP_CATALOG))
    assert len(http.urls("/JH-101/changelog")) == 1 and len(http.urls("/JH-102/changelog")) == 1
