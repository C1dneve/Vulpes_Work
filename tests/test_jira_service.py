"""Jira: paginação real, worklog/changelog completos, hierarquia Story/Sub-task/Bug, erros explícitos."""
import re

import pandas as pd

from services.http import AuthError, NotFound
from services.jira import JiraService
from tests.fakes import FakeHttp, offset_pages

SPRINT = {"id": 5, "name": "Sprint 5", "state": "active", "startDate": "2026-09-21T09:00:00.000Z",
          "endDate": "2026-10-05T09:00:00.000Z"}


def issue(key, summary, itype="Story", status=("A fazer", "new"), parent=None, subtasks=(), assignee=None,
          sprint=None, closed=None, wl=None, spent=None, est=None, **extra):
    f = {"summary": summary, "issuetype": {"name": itype, "subtask": itype in ("Sub-task", "Subtarefa")},
         "status": {"name": status[0], "statusCategory": {"key": status[1]}},
         "assignee": {"displayName": assignee, "accountId": "acc-" + assignee} if assignee else None,
         "subtasks": [{"key": k} for k in subtasks], "labels": [], "timespent": spent, "timeoriginalestimate": est,
         "created": "2026-09-21T10:00:00.000-0300", "updated": "2026-09-24T15:04:05.000-0300"}
    if parent:
        f["parent"] = {"key": parent}
    if sprint:
        f["sprint"] = sprint
    if closed:
        f["closedSprints"] = closed
    if wl is not None:
        f["worklog"] = wl
    f.update(extra)
    return {"id": key.split("-")[1], "key": key, "fields": f}


def cl(history):
    return lambda url, params: offset_pages("values", history, with_total=True)(url, params) | {"isLast": True}


def build(settings, mapper, board_issues, search=None, worklogs=None, histories=None, extra=(), page_size=50,
          fields_catalog=None, **kw):
    worklogs, histories = worklogs or {}, histories or {}

    def wl_route(url, params):
        key = re.search(r"issue/([A-Z]+-\d+)/worklog", url).group(1)
        r = worklogs.get(key, [])
        return r if isinstance(r, Exception) else offset_pages("worklogs", r)(url, params)

    def cl_route(url, params):
        key = re.search(r"issue/([A-Z]+-\d+)/changelog", url).group(1)
        r = histories.get(key, [])
        return r if isinstance(r, Exception) else offset_pages("values", r)(url, params)

    rts = list(extra) + [
        (r"/rest/api/3/field$", fields_catalog if fields_catalog is not None else []),   # sem campos custom por padrão
        (r"/board/7/configuration$", {}),
        (r"/board/7/sprint$", offset_pages("values", [SPRINT])),
        (r"/board/7/issue$", board_issues if callable(board_issues) or isinstance(board_issues, Exception)
         else offset_pages("issues", board_issues, **kw)),
        (r"/rest/api/3/search/jql$", lambda u, body: {"issues": [i for i in (search or []) if i["key"] in body["jql"]]}),
        (r"/worklog$", wl_route), (r"/changelog$", cl_route)]
    http = FakeHttp(rts)
    return JiraService(http, settings, mapper, page_size=page_size), http


def hist(hid, when, frm, to, who="Samuel Martins"):
    return {"id": hid, "created": when, "author": {"displayName": who, "accountId": "a"},
            "items": [{"field": "status", "fromString": frm, "toString": to}]}


STORY = issue("JH-100", "US#1.1 Cadastro de cliente", subtasks=["JH-101", "JH-102"], sprint=SPRINT)
SUBS = [issue("JH-101", "BE-09 Validar cadastro", "Sub-task", ("Em andamento", "indeterminate"), "JH-100", assignee="Samuel Martins"),
        issue("JH-102", "FE-03 Formulário", "Sub-task", ("Em análise", "indeterminate"), "JH-100", assignee="Cid Daniel")]


# ---------------------------------------------------------------- paginação
def test_paginates_all_issues_without_total(settings, mapper):
    stories = [issue(f"JH-{i}", f"US#{i}.1 Story {i}", sprint=SPRINT) for i in range(1, 8)]
    svc, http = build(settings, mapper, stories, page_size=3)   # 3 por página, sem "total"
    res = svc.fetch()
    assert res.ok and len(res.data.stories) == 7 and res.stats["issues"] == 7


def test_server_capping_page_size_still_returns_everything(settings, mapper):
    stories = [issue(f"JH-{i}", f"US#{i}.1 Story {i}", sprint=SPRINT) for i in range(1, 121)]
    svc, _ = build(settings, mapper, stories, page_size=50, cap=20)   # pedimos 50, servidor entrega 20
    assert len(svc.fetch().data.stories) == 120     # antes: maxResults=1000 e torcer para dar certo


def test_server_ignoring_startat_does_not_loop_forever(settings, mapper):
    page = [issue("JH-1", "US#1.1 A", sprint=SPRINT)]
    svc, http = build(settings, mapper, lambda u, p: {"issues": page})
    res = svc.fetch()
    assert http.calls < 30 and any("repetiu a página" in w for w in res.warnings)


def test_token_pagination_is_supported(settings, mapper):
    pages = {None: {"issues": [issue("JH-1", "US#1.1 A", sprint=SPRINT)], "nextPageToken": "t2"},
             "t2": {"issues": [issue("JH-2", "US#1.2 B", sprint=SPRINT)]}}
    svc, _ = build(settings, mapper, lambda u, p: pages[p.get("nextPageToken")])
    assert len(svc.fetch().data.stories) == 2


# ---------------------------------------------------------------- worklog / changelog
def test_worklogs_beyond_embedded_20_are_fetched_from_own_endpoint(settings, mapper):
    logs = [{"id": str(i), "author": {"displayName": "Samuel Martins", "accountId": "a"},
             "started": "2026-09-22T10:00:00.000-0300", "timeSpentSeconds": 3600} for i in range(45)]
    sub = issue("JH-101", "BE-09 Validar", "Sub-task", parent="JH-100", assignee="Samuel Martins", spent=45 * 3600,
                wl={"worklogs": logs[:20], "total": 45, "maxResults": 20})
    svc, http = build(settings, mapper, [STORY, sub], worklogs={"JH-101": logs}, page_size=20)
    res = svc.fetch()
    assert len(res.data.worklogs) == 45
    assert res.data.items.iloc[0]["worklog_sum_h"] == 45
    assert http.urls("/issue/JH-101/worklog")


def test_complete_embedded_worklog_needs_no_extra_call(settings, mapper):
    logs = [{"id": "1", "author": {"displayName": "Samuel Martins"}, "started": "2026-09-22T10:00:00.000-0300", "timeSpentSeconds": 7200}]
    sub = issue("JH-101", "BE-09 Validar", "Sub-task", parent="JH-100", wl={"worklogs": logs, "total": 1})
    svc, http = build(settings, mapper, [STORY, sub])
    assert len(svc.fetch().data.worklogs) == 1 and not http.urls("/worklog")


def test_changelog_beyond_100_is_paginated_and_grouped(settings, mapper):
    hs = []
    for i in range(130):   # 130 transições (ex.: vai-e-volta): o embutido truncaria em 100
        frm, to = ("Em andamento", "Em análise") if i % 2 == 0 else ("Em análise", "Em andamento")
        hs.append(hist(str(i), f"2026-09-22T{(i % 20) + 1:02d}:00:00.000-0300", frm, to))
    sub = issue("JH-101", "BE-09 Validar", "Sub-task", ("Em análise", "indeterminate"), "JH-100")
    svc, _ = build(settings, mapper, [STORY, sub], histories={"JH-101": hs}, page_size=50)
    c = svc.fetch().data.changelog
    assert len(c) == 130
    assert set(c["to_group"]) == {"Em Análise", "Em Andamento"}     # "em análise" = Code Review, não "Pendente"
    assert str(c["ts"].dt.tz) == "America/Sao_Paulo"


def test_worklog_dates_use_local_day_and_keep_time(settings, mapper):
    logs = [{"id": "1", "author": {"displayName": "Samuel Martins"}, "started": "2026-09-25T01:00:00.000+0000", "timeSpentSeconds": 3600},
            {"id": "2", "author": {"displayName": "Samuel Martins"}, "started": "2026-09-24T23:30:00.000-0300", "timeSpentSeconds": 3600}]
    sub = issue("JH-101", "BE-09 Validar", "Sub-task", parent="JH-100", wl={"worklogs": logs, "total": 2})
    w = build(settings, mapper, [STORY, sub])[0].fetch().data.worklogs
    assert w["date"].tolist() == [pd.Timestamp("2026-09-24")] * 2
    assert w["started"].iloc[0].hour == 22


# ---------------------------------------------------------------- hierarquia
def test_subtasks_missing_from_board_are_fetched_by_key(settings, mapper):
    svc, http = build(settings, mapper, [STORY], search=SUBS)   # board devolve só a story
    res = svc.fetch()
    assert sorted(res.data.items["subtask_key"]) == ["JH-101", "JH-102"]
    assert set(res.data.items["story_key"]) == {"JH-100"}
    assert http.urls("/search/jql") and not http.urls("/rest/api/3/search?")   # endpoint novo, não o removido


def test_status_groups_reflect_team_workflow(settings, mapper):
    items = build(settings, mapper, [STORY] + SUBS)[0].fetch().data.items.set_index("subtask_key")
    assert items.loc["JH-101", "status_group"] == "Em Andamento"
    assert items.loc["JH-102", "status_group"] == "Em Análise"


def test_bug_under_story_story_without_children_and_standalone_bug(settings, mapper):
    bug = issue("JH-110", "Bug no login", "Bug", ("Em teste", "indeterminate"), parent="JH-100", assignee="Cid Daniel")
    lonely = issue("JH-200", "US#2.1 Story sem subtasks", sprint=SPRINT)
    orphan = issue("JH-300", "Bug solto", "Bug", ("A fazer", "new"))
    res = build(settings, mapper, [STORY, SUBS[0], bug, lonely, orphan])[0].fetch()
    it, st = res.data.items.set_index("subtask_key"), res.data.stories.set_index("story_key")
    assert it.loc["JH-110", "story_key"] == "JH-100" and it.loc["JH-110", "status_group"] == "Em Teste"
    assert it.loc["JH-200", "standalone"] and it.loc["JH-200", "story_key"] == "JH-200"
    assert it.loc["JH-300", "standalone"] and st.loc["JH-300", "kind"] == "standalone"
    assert st.loc["JH-100", "kind"] == "story"


def test_us_1_1_and_1_2_are_different_stories(settings, mapper):
    a = issue("JH-1", "US#1.1 Cadastro", sprint=SPRINT, subtasks=["JH-11"])
    b = issue("JH-2", "US#1.2 Listagem", sprint=SPRINT, subtasks=["JH-21"])
    subs = [issue("JH-11", "BE-01 x", "Sub-task", parent="JH-1"), issue("JH-21", "BE-02 y", "Sub-task", parent="JH-2")]
    st = build(settings, mapper, [a, b] + subs)[0].fetch().data
    assert st.stories.set_index("story_key")["us_id"].to_dict() == {"JH-1": "US1.1", "JH-2": "US1.2"}
    assert st.items.set_index("subtask_key")["us_id"].to_dict() == {"JH-11": "US1.1", "JH-21": "US1.2"}


def test_jira_key_as_canonical_switch(tmp_path, mapper):
    import json

    from settings import load_settings
    from tests.conftest import ENV
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"github": {"org": "T", "repos": ["r"]}, "regex": {"use_jira_key_as_canonical": True}}))
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    d = build(s, mapper, [STORY] + SUBS)[0].fetch().data
    assert set(d.items["canonical_id"]) == {"JH-100"} and set(d.items["us_id"]) == {"US1.1"}   # os dois coexistem


def test_estimates_hours_and_subtask_code(settings, mapper):
    sub = issue("JH-101", "BE-09 Validar", "Sub-task", parent="JH-100", spent=5400, est=7200, timeestimate=1800)
    r = build(settings, mapper, [STORY, sub])[0].fetch().data.items.iloc[0]
    assert (r["estimate_h"], r["time_spent_h"], r["subtask_code"]) == (2.0, 1.5, "BE-09")


def test_epic_is_captured_from_parent(settings, mapper):
    st = issue("JH-100", "US#1.1 Cadastro", sprint=SPRINT, subtasks=["JH-101"])
    st["fields"]["parent"] = {"key": "JH-50", "fields": {"summary": "Clientes", "issuetype": {"name": "Epic"}}}
    d = build(settings, mapper, [st, issue("JH-101", "BE-1 x", "Sub-task", parent="JH-100")])[0].fetch().data
    assert d.stories.iloc[0]["epic_key"] == "JH-50" and d.stories.iloc[0]["epic_summary"] == "Clientes"


# ---------------------------------------------------------------- sprint
def test_sprint_dates_active_state_and_closed_fallback(settings, mapper):
    closed = {"id": 3, "name": "Sprint 3", "state": "closed", "endDate": "2026-09-10T09:00:00.000Z"}
    old = issue("JH-9", "US#9.1 Antiga", closed=[closed])
    d = build(settings, mapper, [STORY, SUBS[0], old])[0].fetch().data
    st = d.stories.set_index("story_key")
    assert st.loc["JH-100", "sprint_state"] == "active" and st.loc["JH-100", "sprint"] == "Sprint 5"
    assert st.loc["JH-9", "sprint"] == "Sprint 3"    # antes: história só em sprint fechada virava "Sem Sprint"
    assert d.sprints.iloc[0]["state"] == "active" and str(d.sprints.iloc[0]["start"].tz) == "America/Sao_Paulo"


def test_kanban_board_without_sprints_is_a_warning_not_failure(settings, mapper):
    from services.http import ApiError
    svc, _ = build(settings, mapper, [STORY, SUBS[0]],
                   extra=[(r"/board/7/sprint$", ApiError("Jira", "board não suporta sprints", 400))])
    res = svc.fetch()
    assert res.ok and res.partial and res.data.sprints.empty


# ---------------------------------------------------------------- erros
def test_auth_failure_is_an_error_with_no_data(settings, mapper):
    svc, _ = build(settings, mapper, AuthError("Jira", "bad", 401),
                   extra=[(r"/board/7/sprint$", AuthError("Jira", "bad", 401))])
    res = svc.fetch()
    assert not res.ok and res.data is None and "falha de autenticação" in res.errors[0]


def test_board_not_found_is_explicit(settings, mapper):
    svc, _ = build(settings, mapper, NotFound("Jira", "board 7", 404), extra=[(r"/board/7/sprint$", NotFound("Jira", "x", 404))])
    res = svc.fetch()
    assert not res.ok and "404" in res.errors[0]


def test_partial_changelog_is_reported_not_hidden(settings, mapper):
    subs = [issue(f"JH-1{i}", f"BE-0{i} x", "Sub-task", parent="JH-100") for i in range(1, 4)]
    svc, _ = build(settings, mapper, [STORY] + subs, histories={"JH-12": NotFound("Jira", "x", 404)})
    res = svc.fetch()
    assert res.ok and res.partial and res.stats["changelog_partial"] == ["JH-12"]
    assert any("Changelog: 1 issue" in w for w in res.warnings)


def test_all_changelogs_failing_is_an_error(settings, mapper):
    svc, _ = build(settings, mapper, [STORY, SUBS[0]], histories={"JH-101": NotFound("Jira", "x", 404)})
    assert not svc.fetch().ok


def test_empty_board_is_flagged(settings, mapper):
    res = build(settings, mapper, [])[0].fetch()
    assert res.ok and res.partial and any("nenhuma issue" in w for w in res.warnings) and res.data.items.empty


def test_assignee_none_and_display_name_slug(settings, mapper):
    sub = issue("JH-101", "BE-09 x", "Sub-task", parent="JH-100")
    sub2 = issue("JH-102", "BE-10 y", "Sub-task", parent="JH-100", assignee="Samuel Martins")
    it = build(settings, mapper, [STORY, sub, sub2])[0].fetch().data.items.set_index("subtask_key")
    assert it.loc["JH-101", "assignee"] == "nenhum" and it.loc["JH-102", "assignee"] == "samuel-martins"


# ---------------------------------------------------------------- P0.2: Sprint própria da Subtask
SPRINT4 = {"id": 4, "name": "Sprint 4", "state": "closed", "startDate": "2026-09-07T09:00:00.000Z",
           "endDate": "2026-09-20T09:00:00.000Z"}
SPRINT6 = {"id": 6, "name": "Sprint 6", "state": "future", "startDate": "2026-10-06T09:00:00.000Z",
           "endDate": "2026-10-20T09:00:00.000Z"}


def sprints_of(settings, mapper, story_sprint, sub_sprint, sub_closed=None):
    st = issue("JH-100", "US#1.1 Cadastro", sprint=story_sprint, subtasks=["JH-101"])
    sb = issue("JH-101", "BE-01 x", "Sub-task", parent="JH-100", sprint=sub_sprint, closed=sub_closed)
    d = build(settings, mapper, [st, sb])[0].fetch().data
    return d.stories.iloc[0]["sprint"], d.items.iloc[0]["sprint"], d.items.iloc[0]["sprint_id"]


def test_story_and_subtask_in_the_same_sprint(settings, mapper):
    assert sprints_of(settings, mapper, SPRINT, SPRINT) == ("Sprint 5", "Sprint 5", 5)


def test_subtask_keeps_its_own_sprint_when_story_is_in_another(settings, mapper):
    story, sub, sub_id = sprints_of(settings, mapper, SPRINT, SPRINT6)
    assert (story, sub, sub_id) == ("Sprint 5", "Sprint 6", 6)   # nunca sobrescrita pela Sprint da Story


def test_subtask_sprint_is_used_when_story_has_none(settings, mapper):
    assert sprints_of(settings, mapper, None, SPRINT) == ("Sem Sprint", "Sprint 5", 5)


def test_subtask_falls_back_to_the_story_sprint_when_it_has_none(settings, mapper):
    assert sprints_of(settings, mapper, SPRINT, None) == ("Sprint 5", "Sprint 5", 5)


def test_subtask_uses_its_own_closed_sprint_when_story_has_none(settings, mapper):
    assert sprints_of(settings, mapper, None, None, sub_closed=[SPRINT4]) == ("Sem Sprint", "Sprint 4", 4)


def test_subtask_without_any_sprint_and_story_without_sprint_is_sem_sprint(settings, mapper):
    assert sprints_of(settings, mapper, None, None)[:2] == ("Sem Sprint", "Sem Sprint")


# ---------------------------------------------------------------- P0.5: payload inesperado não derruba o app
def test_unexpected_board_payload_is_a_controlled_failure(settings, mapper):
    broken = {"id": "1", "key": "JH-1"}   # issue sem "fields"
    res = build(settings, mapper, [broken])[0].fetch()
    assert res.status == "error" and res.data is None
    assert "KeyError" in res.errors[0] and settings.jira.token not in res.errors[0]
