"""MVP / Fase 3-4 — tabelas de Sprint, Stories e Pessoas; filtro Pessoa + Sprint; sem ranking."""
import pandas as pd

from domain import statuses as S
from domain import work as W
from domain.sprint_view import enrich_items, enrich_stories, people_table, sprint_kpis
from domain.thresholds import Thresholds
from services.context import Bundle, Context, apply_context

TZ = "America/Sao_Paulo"
NOW = pd.Timestamp("2026-09-30 10:00", tz=TZ)
TH = Thresholds()
KNOWN = {"JH-100", "JH-200", "JH-101", "JH-102", "JH-103", "JH-201"}
CHANGELOG_COLS = ["subtask_key", "ts", "date", "to_group", "from_group"]


def ts(s):
    return pd.Timestamp(s, tz=TZ)


def story(key, us, sprint="Sprint 5", sp=None, group=S.ANDAMENTO, due=None, assignee="nenhum", **kw):
    return {"story_key": key, "story_summary": f"Story {us}", "us_id": us, "sprint": sprint, "story_points": sp, "status_name": group,
            "status_group": group, "assignee": assignee, "due_date": due, "epic_key": "JH-1", "epic_summary": "Epic", "kind": "story",
            "sprint_start": ts("2026-09-21"), "sprint_end": ts("2026-10-05"), "sprint_state": "active", **kw}


def task(key, sk, who, group=S.ANDAMENTO, est=None, spent=0.0, rem=None, due=None, code=None, sprint="Sprint 5",
         updated="2026-09-30 09:00", **kw):
    return {"subtask_key": key, "story_key": sk, "assignee": who, "status_group": group, "estimate_h": est, "time_spent_h": spent,
            "remaining_h": rem, "due_date": due, "subtask_code": code, "sprint": sprint, "updated": ts(updated), "flagged": False,
            "flagged_since": pd.NaT, "blocked_by": [], "us_id": "US2.1", "standalone": False, **kw}


def commit(sha, key=None, ref=None, us=None, author="ana", when="2026-09-29 10:00", delivered=False, kind="human"):
    return {"sha": sha, "jira_key": key, "ref_jira_key": ref, "us_id": us, "author": author, "date": ts(when), "delivered": delivered,
            "kind": kind, "branches": ["feature/x"], "repo": "r"}


def frames():
    stories = pd.DataFrame([story("JH-100", "US2.1", sp=5, assignee="cid", due="2026-10-02"),
                            story("JH-200", "US2.2", sp=None)])
    items = pd.DataFrame([
        task("JH-101", "JH-100", "ana", est=4, spent=1, code="BE-01", due="2026-09-29"),                    # atrasada
        task("JH-102", "JH-100", "zeca", group=S.CONCLUIDA, est=2, spent=3, code="FE-01"),
        task("JH-103", "JH-100", "ana", group=S.BLOQUEADA, code="BE-02", flagged=True, updated="2026-09-20 10:00"),
        task("JH-201", "JH-200", "zeca", est=None, spent=2, code="UXDB-01", us_id="US2.2"),
    ])
    commits = pd.DataFrame([commit("a", "JH-101"), commit("b", "JH-100"),                 # commit da STORY: não é evidência de JH-101
                            commit("c", None, ref="JH-100", us="US2.1", author="zeca", delivered=True),
                            commit("d", "JH-102", author="zeca", delivered=True), commit("m", None, kind="merge")])
    branches = pd.DataFrame([{"branch": "feature/backend/JH-100-US2.1-x", "is_default": False, "jira_key": "JH-100", "us_id": "US2.1",
                              "last_author": "ana", "pending_commits": 1, "last_commit": ts("2026-09-29")}])
    prs = pd.DataFrame([{"number": 42, "jira_key": "JH-100", "us_id": "US2.1", "author": "ana", "state": "open",
                         "review_state": "aguardando_revisao", "kind": "backend", "created": ts("2026-09-29")}])
    wl = pd.DataFrame([{"subtask_key": "JH-101", "author": "ana", "time_spent_h": 1.0}, {"subtask_key": "JH-102", "author": "zeca", "time_spent_h": 2.0},
                       {"subtask_key": "JH-102", "author": "ana", "time_spent_h": 1.0}])
    cl = pd.DataFrame(columns=CHANGELOG_COLS)
    return stories, items, wl, cl, commits, branches, prs


def enriched():
    stories, items, wl, cl, commits, branches, prs = frames()
    ie = enrich_items(items, cl, wl.assign(started=ts("2026-09-29")), commits, KNOWN, NOW, TH)
    se = enrich_stories(stories, ie, items, commits, branches, prs, KNOWN, NOW, TH)
    return stories, items, wl, commits, branches, prs, ie, se


# ---------------------------------------------------------------- tasks
def test_commit_evidence_of_a_task_is_only_commits_that_cite_its_key():
    *_, ie, _ = enriched()
    n = ie.set_index("subtask_key")["n_commits"].to_dict()
    assert n == {"JH-101": 1, "JH-102": 1, "JH-103": 0, "JH-201": 0}       # commit da Story ("b") e da PR ("c") NÃO entram na Subtask
    assert ie.set_index("subtask_key").loc["JH-102", "n_commits_delivered"] == 1


def test_tasks_are_classified_late_blocked_inactive_and_done():
    *_, ie, _ = enriched()
    t = ie.set_index("subtask_key")
    assert t.loc["JH-101", "due_status"] == W.DUE_LATE and t.loc["JH-101", "side"] == "backend"
    assert t.loc["JH-103", "is_blocked"] and t.loc["JH-103", "block_sources"] == ("status", "flag")
    assert not t.loc["JH-103", "is_inactive"]                                # bloqueada não é "inativa": é bloqueada
    assert t.loc["JH-102", "is_done"] and t.loc["JH-102", "due_status"] == W.DUE_DONE and not t.loc["JH-102", "is_inactive"]
    assert t.loc["JH-201", "due_status"] == W.DUE_NONE and t.loc["JH-201", "side"] is None


def test_estimate_versus_logged_is_kept_apart_and_labeled():
    *_, ie, _ = enriched()
    t = ie.set_index("subtask_key")
    assert (t.loc["JH-101", "estimate_h"], t.loc["JH-101", "logged_h"], t.loc["JH-101", "remaining_eff_h"],
            t.loc["JH-101", "remaining_source"]) == (4, 1, 3, "calculado")
    assert t.loc["JH-102", "diff_h"] == 1                                    # estourou 1h
    assert pd.isna(t.loc["JH-201", "remaining_eff_h"]) and t.loc["JH-201", "remaining_source"] is None   # sem estimativa: não se inventa


def test_empty_items_keep_the_expected_columns():
    stories, items, wl, cl, commits, *_ = frames()
    e = enrich_items(items.iloc[0:0], cl, wl, commits, KNOWN, NOW, TH)
    assert e.empty and {"is_blocked", "due_status", "is_inactive", "n_commits"} <= set(e.columns)


# ---------------------------------------------------------------- stories
def test_story_row_has_points_status_rollup_due_and_github_evidence():
    *_, se = enriched()
    s = se.set_index("story_key").loc["JH-100"]
    assert s["story_points"] == 5 and s["responsavel"] == "cid" and s["team"] == ["ana", "zeca"]
    assert (s["subtasks_total"], s["subtasks_done"], s["n_blocked"], s["n_late"]) == (3, 1, 1, 1)
    assert s["estimate_h"] == 6 and s["estimate_coverage"] == "2/3" and s["logged_h"] == 4
    assert s["due_date"] == "2026-10-02" and s["due_source"] == "story" and s["due_status"] == W.DUE_SOON
    assert (s["n_branches"], s["n_prs"]) == (1, 1) and s["pr_states"] == "#42 aguardando_revisao"
    assert s["n_commits"] == 4          # a, b (Story), c (ref da PR) e d — TODOS os commits da Story; os de Subtask vêm pela chave


def test_missing_story_points_and_responsible_stay_missing():
    *_, se = enriched()
    s = se.set_index("story_key").loc["JH-200"]
    assert pd.isna(s["story_points"]) and s["responsavel"] is None
    assert s["estimate_h"] is None or pd.isna(s["estimate_h"])
    assert s["due_date"] is None and s["due_status"] == W.DUE_NONE


def test_story_due_falls_back_to_earliest_open_subtask_due_date_and_says_so():
    stories = pd.DataFrame([story("JH-100", "US2.1")])
    items = pd.DataFrame([task("JH-101", "JH-100", "ana", due="2026-10-10"), task("JH-102", "JH-100", "ana", due="2026-10-01"),
                          task("JH-103", "JH-100", "ana", group=S.CONCLUIDA, due="2026-09-01")])   # concluída não conta
    empty_cl, empty_wl = pd.DataFrame(columns=CHANGELOG_COLS), pd.DataFrame(columns=["subtask_key", "started", "author", "time_spent_h"])
    ie = enrich_items(items, empty_cl, empty_wl, frames()[4].iloc[0:0], KNOWN, NOW, TH)
    s = enrich_stories(stories, ie, items, frames()[4].iloc[0:0], frames()[5].iloc[0:0], frames()[6].iloc[0:0], KNOWN, NOW, TH).iloc[0]
    assert s["due_date"] == "2026-10-01" and s["due_source"] == "subtasks" and s["due_status"] == W.DUE_SOON


def test_sprint_kpis_points_are_only_from_stories_that_have_them():
    *_, ie, se = enriched()
    k = sprint_kpis(se, ie)
    assert k["sp_planned"] == 5 and k["sp_missing"] == 1 and k["sp_done"] == 0          # JH-200 sem pontos: fora da soma, contada como ausente
    assert (k["items"], k["items_done"], k["blocked"], k["late"]) == (4, 1, 1, 1)
    assert k["estimate_h"] == 6 and k["estimate_items"] == 2
    none = sprint_kpis(se.assign(story_points=None), ie)
    assert none["sp_planned"] is None and none["sp_done"] is None and none["sp_missing"] == 2   # tudo ausente: indisponível, não 0


def test_sprint_kpis_on_empty_scope():
    stories, items, wl, cl, commits, branches, prs = frames()
    se = enrich_stories(stories.iloc[0:0], items.iloc[0:0], items, commits, branches, prs, KNOWN, NOW, TH)
    k = sprint_kpis(se, enrich_items(items.iloc[0:0], cl, wl, commits, KNOWN, NOW, TH))
    assert k["stories"] == 0 and k["sp_planned"] is None and k["logged_h"] == 0.0


# ---------------------------------------------------------------- pessoas
def test_people_table_is_alphabetical_not_a_ranking():
    stories, items, wl, commits, branches, prs, ie, _ = enriched()
    big = pd.concat([commits] + [pd.DataFrame([commit(f"z{i}", "JH-102", author="zeca")]) for i in range(20)])   # zeca com MUITO mais commits
    p = people_table(ie, stories, wl, big, branches, prs)
    assert p["person"].tolist() == ["ana", "zeca"]                               # ordem alfabética, não por volume
    banned = {"rank", "ranking", "score", "pontuacao", "produtividade", "position"}
    assert not banned & {c.lower() for c in p.columns}


def test_people_table_numbers_describe_the_work():
    stories, items, wl, commits, branches, prs, ie, _ = enriched()
    p = people_table(ie, stories, wl, commits, branches, prs).set_index("person")
    ana, zeca = p.loc["ana"], p.loc["zeca"]
    assert ana["tasks"] == 2 and ana[S.BLOQUEADA] == 1 and ana[S.ANDAMENTO] == 1 and ana["estimate_h"] == 4
    assert ana["logged_on_tasks_h"] == 1 and ana["logged_by_person_h"] == 2       # ela lançou 1h na task dela e 1h na do zeca
    assert zeca["logged_on_tasks_h"] == 5 and zeca["logged_by_person_h"] == 2
    assert ana["stories"] == 1 and ana["story_points_related"] == 5              # as 2 subtasks da Story contam UMA vez
    assert zeca["stories"] == 2 and zeca["story_points_related"] == 5            # JH-200 sem pontos: ausente, não 0
    assert (ana["commits"], ana["branches"], ana["prs"]) == (2, 1, 1) and zeca["commits"] == 2 and zeca["prs"] == 0


def test_person_without_any_points_shows_none_not_zero():
    stories, items, wl, commits, branches, prs, ie, _ = enriched()
    p = people_table(ie[ie["story_key"] == "JH-200"], stories, wl, commits, branches, prs).set_index("person")
    assert p.loc["zeca", "story_points_related"] is None or pd.isna(p.loc["zeca", "story_points_related"])


# ---------------------------------------------------------------- Pessoa + Sprint
def bundle():
    stories, items, wl, cl, commits, branches, prs = frames()
    stories2 = pd.DataFrame(stories.to_dict("records") + [story("JH-900", "US1.1", sprint="Sprint 4")])
    items2 = pd.DataFrame(items.to_dict("records") + [task("JH-901", "JH-900", "ana", sprint="Sprint 4")])
    sprints = pd.DataFrame([{"sprint_id": 4, "name": "Sprint 4", "state": "closed", "start": ts("2026-09-07"), "end": ts("2026-09-20"), "complete": pd.NaT},
                            {"sprint_id": 5, "name": "Sprint 5", "state": "active", "start": ts("2026-09-21"), "end": ts("2026-10-05"), "complete": pd.NaT}])
    wl2 = pd.DataFrame([{**r, "started": ts("2026-09-29"), "date": pd.Timestamp("2026-09-29")} for r in wl.to_dict("records")]
                       + [{"subtask_key": "JH-901", "author": "ana", "time_spent_h": 9.0, "started": ts("2026-09-10"), "date": pd.Timestamp("2026-09-10")}])
    return Bundle(stories2, items2, wl2, cl, sprints, commits, branches, prs)


def test_person_plus_sprint_limits_tasks_hours_and_never_shows_other_sprints():
    sc = apply_context(bundle(), Context(sprint="Sprint 5", dev="ana"))
    assert set(sc.items["subtask_key"]) == {"JH-101", "JH-103"}                    # JH-901 (Sprint 4) não aparece
    assert sc.worklogs["time_spent_h"].sum() == 1.0 and "JH-901" not in set(sc.worklogs["subtask_key"])
    assert set(sc.stories["story_key"]) == {"JH-100"}
    assert set(sc.commits["author"]) == {"ana"}


def test_person_filter_changes_github_rows_but_team_scope_keeps_story_facts():
    b = bundle()
    person, team = apply_context(b, Context(sprint="Sprint 5", dev="zeca")), apply_context(b, Context(sprint="Sprint 5"))
    assert person.prs.empty and len(team.prs) == 1           # a PR é da ana: só a visão de TIME a enxerga
    # por isso alertas/Stories usam o escopo de time e só filtram as LINHAS pela pessoa
    ie = enrich_items(person.items, person.changelog, person.worklogs, team.commits, KNOWN, NOW, TH)
    se = enrich_stories(person.stories, ie, b.items, team.commits, team.branches, team.prs, KNOWN, NOW, TH).set_index("story_key")
    assert se.loc["JH-100", "n_prs"] == 1
