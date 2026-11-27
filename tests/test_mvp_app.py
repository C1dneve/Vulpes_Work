"""MVP — integração de ponta a ponta: o app inteiro (AppTest) com um cenário rico de Sprint."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from domain.people import DevMapper
from services import sync
from services.github import GitHubService
from services.results import SourceResult
from settings import load_settings
from tests.conftest import ENV, MAPPING
from tests.fakes import FakeHttp
from tests.test_github_service import BR_BACK, gh_commit, gh_pr, routes
from tests.test_jira_service import SPRINT, SPRINT4, build, hist, issue

EVIL = '<img src=x onerror="alert(1)">'
NEW_PAGES = ["Agora", "Pessoas", "Timeline"]
CATALOG = [{"id": "customfield_10016", "name": "Story point estimate", "custom": True}]
BLOCKER = {"type": {"name": "Blocks", "inward": "is blocked by", "outward": "blocks"},
           "inwardIssue": {"key": "JH-55", "fields": {"summary": "Liberar ambiente", "status": {"name": "Em andamento",
                                                                                                "statusCategory": {"key": "indeterminate"}}}}}


def jira_result(settings, mapper):
    s1 = issue("JH-100", f"US#2.1 Cadastro {EVIL}", subtasks=["JH-101", "JH-102", "JH-103"], sprint=SPRINT,
               status=("Em andamento", "indeterminate"), customfield_10016=5)
    s2 = issue("JH-200", "US#2.2 Relatório", subtasks=["JH-201"], sprint=SPRINT, status=("A fazer", "new"))
    subs = [
        issue("JH-101", f"BE-09 Validar {EVIL}", "Sub-task", ("Concluído", "done"), "JH-100", assignee="Samuel Martins", spent=7200, est=10800,
              resolutiondate="2026-09-24T10:00:00.000-0300"),
        issue("JH-102", "FE-03 Formulário", "Sub-task", ("Em análise", "indeterminate"), "JH-100", assignee="Cid Daniel",
              duedate="2020-01-01", issuelinks=[BLOCKER]),
        issue("JH-103", "BE-10 Endpoint", "Sub-task", ("Em andamento", "indeterminate"), "JH-100", assignee="Samuel Martins", est=7200),
        issue("JH-201", "UXDB-01 Protótipo", "Sub-task", ("A fazer", "new"), "JH-200", assignee="Cid Daniel")]
    hs = {"JH-101": [hist("1", "2026-09-22T10:00:00.000-0300", "A fazer", "Em andamento"),
                     hist("2", "2026-09-24T10:00:00.000-0300", "Em análise", "Concluído")],
          "JH-102": [hist("3", "2026-09-23T10:00:00.000-0300", "Em andamento", "Em análise")]}
    svc, _ = build(settings, mapper, [s1, s2], search=subs, histories=hs, fields_catalog=CATALOG)
    return svc.fetch()


def github_result(settings, mapper):
    c1 = gh_commit("c1", "feat(JH-101): implementar validação do cadastro")
    wip = gh_commit("w1", f"wip sem chave {EVIL}", days=1)
    # Sprint 5 termina em 05/10/2026; use uma data fixa dentro da Sprint, não "ontem".
    wip["commit"]["author"]["date"] = "2026-10-01T12:00:00Z"
    pr = gh_pr(42, BR_BACK, "c1", title=f"[JH-100] US2.1 — Cadastro {EVIL}")      # PR aberta, sem reviews
    rts = routes([wip], [("main", "w1"), (BR_BACK, "c1")], prs_open=[pr], pr_commits={42: [c1]},
                 compares={f"main...{BR_BACK}": {"ahead_by": 1, "behind_by": 0, "status": "ahead", "commits": [c1]}})
    return GitHubService(FakeHttp(rts), settings, mapper).fetch()


@pytest.fixture
def app(monkeypatch, tmp_path):
    import settings as settings_mod
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    (tmp_path / "config.json").write_text(json.dumps({"github": {"org": "Team", "repos": ["repo"]}, "dev_mapping": MAPPING}))
    monkeypatch.setattr(settings_mod, "ROOT", tmp_path)
    s, mapper = load_settings(environ=ENV), DevMapper(MAPPING)
    sync.cache().reset()
    monkeypatch.setattr(sync, "_fetch_jira", lambda _s: jira_result(s, mapper))
    monkeypatch.setattr(sync, "_fetch_github", lambda _s: github_result(s, mapper))
    return AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=90)


def page(at, name):
    at.sidebar.radio[0].set_value(name)
    return at.run()


def frames(at):
    return [d.value for d in at.dataframe]


def cells(at) -> str:
    return " | ".join(str(v) for df in frames(at) for v in df.to_numpy().ravel())


def md(at) -> str:
    return " ".join(m.value for m in at.markdown)


def captions(at) -> str:
    return " ".join(c.value for c in at.caption)


def test_new_pages_and_sprint_render_without_exception(app):
    at = app.run()
    assert not at.exception, at.exception
    for p in ["Dashboard", "Sprint", *NEW_PAGES]:
        at = page(at, p)
        assert not at.exception, (p, [e.value for e in at.exception])


def test_sprint_stories_table_shows_points_hours_status_and_never_invents(app):
    at = page(app.run(), "Sprint")
    stories = next(f for f in frames(at) if "Subtasks" in f.columns and "SP" in f.columns)
    s = stories.set_index("US")
    assert s.loc["US2.1", "SP"] == "5" and s.loc["US2.1", "Subtasks"] == "1/3"
    assert s.loc["US2.2", "SP"] == "—"                                      # sem pontos no Jira: indisponível, não 0
    assert s.loc["US2.1", "Estimado"].startswith("5h") and "(2/3)" in s.loc["US2.1", "Estimado"]   # só 2 de 3 subtasks têm estimativa
    assert "Atrasado" in s.loc["US2.1", "Prazo / situação"] and "(das subtasks)" in s.loc["US2.1", "Prazo / situação"]
    assert s.loc["US2.1", "PRs"] == 1 and s.loc["US2.1", "Branches"] == 1 and s.loc["US2.1", "Commits"] >= 1
    assert "aguardando_revisao" in s.loc["US2.1", "Revisão das PRs"]
    k = " ".join(f"{m.label}={m.value}" for m in at.metric)
    assert "Story Points=0/5" in k and "Atrasadas=1" in k and "Bloqueadas=1" in k


def test_agora_lists_blocked_overdue_and_pr_without_review_with_provable_reasons(app):
    at = page(app.run(), "Agora")
    text = cells(at)
    assert "Bloqueada por JH-55 — Liberar ambiente" in text                 # motivo comprovado pelo link do Jira
    assert "Tarefa atrasada" in text and "PR aguardando revisão" in text
    assert "Commit sem Jira Key" in text and "wip sem chave" in text         # o commit 'wip' não cita nenhuma chave
    sev = {m.label: m.value for m in at.metric}
    assert int(sev["🔴 Alta"]) >= 2 and int(sev["🟠 Média"]) >= 1


def test_pessoas_is_alphabetical_has_no_ranking_and_scopes_the_person(app):
    at = page(app.run(), "Pessoas")
    overview = frames(at)[0]
    assert list(overview["Pessoa"]) == sorted(overview["Pessoa"])               # ordem alfabética
    banned = ("rank", "score", "produtiv", "melhor", "pior", "posição")
    assert not any(b in str(c).lower() for f in frames(at) for c in f.columns for b in banned)
    assert "não para comparar pessoas" in captions(at)
    sel = next(s for s in at.selectbox if s.label == "Pessoa")
    sel.set_value("samuel-martins").run()
    assert not at.exception
    tasks = next(f for f in frames(at) if "Commits (chave da task)" in f.columns)
    assert set(tasks["Resumo"]) == {f"BE-09 Validar {EVIL}", "BE-10 Endpoint"}   # só as tasks dele


def test_global_dev_filter_reaches_every_new_page(app):
    at = app.run()
    next(s for s in at.sidebar.selectbox if s.label == "Desenvolvedor").set_value("cid-daniel").run()
    at = page(at, "Sprint")
    stories = next(f for f in frames(at) if "Subtasks" in f.columns)
    assert "Samuel" not in " ".join(stories["Time"])                         # o time da Story só tem a pessoa filtrada
    at = page(at, "Agora")
    assert "BE-10" not in cells(at) and "JH-103" not in cells(at)            # alerta de task do Samuel não aparece para a Cid
    assert "JH-102" in cells(at)
    at = page(at, "Pessoas")
    assert not at.exception and next(s for s in at.selectbox if s.label == "Pessoa").disabled
    at = page(at, "Timeline")
    assert not at.exception


def two_sprints(monkeypatch):
    """Sprint 5 (a do cenário) + Sprint 4 com a Story JH-900 / Subtask JH-901 / worklog / commit / PR próprios."""
    s, mapper = load_settings(environ=ENV), DevMapper(MAPPING)

    def jira(_s):
        s4 = issue("JH-900", "US#1.1 Login", subtasks=["JH-901"], sprint=SPRINT4, status=("Em andamento", "indeterminate"))
        sub4 = issue("JH-901", "BE-01 Autenticar", "Sub-task", ("Em andamento", "indeterminate"), "JH-900", assignee="Cid Daniel",
                     sprint=SPRINT4, est=3600)
        base = jira_result(s, mapper)
        story5 = issue("JH-100", "US#2.1 Cadastro", subtasks=["JH-102"], sprint=SPRINT, status=("Em andamento", "indeterminate"))
        sub5 = issue("JH-102", "FE-03 Formulário", "Sub-task", ("Em andamento", "indeterminate"), "JH-100", assignee="Cid Daniel", sprint=SPRINT)
        assert base.ok
        return build(s, mapper, [story5, s4], search=[sub5, sub4])[0].fetch()

    def github(_s):
        c5 = gh_commit("c5", "feat(JH-102): formulário de cadastro", days=1)
        c4 = gh_commit("c4", "feat(JH-901): autenticar usuário", days=5)
        pr4 = gh_pr(40, "feature/backend/JH-900-US1.1-login", "c4", title="[JH-900] US1.1 — Login")
        pr5 = gh_pr(50, "feature/frontend/JH-100-US2.1-cadastro", "c5", title="[JH-100] US2.1 — Cadastro")
        rts = routes([], [("main", "m"), ("feature/backend/JH-900-US1.1-login", "c4"), ("feature/frontend/JH-100-US2.1-cadastro", "c5")],
                     prs_open=[pr4, pr5], pr_commits={40: [c4], 50: [c5]},
                     compares={"main...feature/backend/JH-900-US1.1-login": {"ahead_by": 1, "behind_by": 0, "status": "ahead", "commits": [c4]},
                               "main...feature/frontend/JH-100-US2.1-cadastro": {"ahead_by": 1, "behind_by": 0, "status": "ahead", "commits": [c5]}})
        return GitHubService(FakeHttp(rts), s, mapper).fetch()
    monkeypatch.setattr(sync, "_fetch_jira", jira)
    monkeypatch.setattr(sync, "_fetch_github", github)
    sync.cache().reset()


def test_sprint_filter_reaches_every_secondary_table(app, monkeypatch):
    two_sprints(monkeypatch)
    at = app.run()
    sel = next(s for s in at.sidebar.selectbox if s.label == "Sprint")
    assert sel.value == "Sprint 5" and "Sprint 4" in sel.options
    for p in ["Sprint", "Agora", "Pessoas", "Timeline"]:                   # Sprint 5: nada da Sprint 4
        at = page(at, p)
        t = cells(at)
        assert not at.exception and "JH-900" not in t and "JH-901" not in t and "PR #40" not in t and "/pull/40" not in t, p
    next(s for s in at.sidebar.selectbox if s.label == "Sprint").set_value("Sprint 4").run()
    for p in ["Sprint", "Agora", "Pessoas", "Timeline"]:                   # Sprint 4: nada da Sprint 5
        at = page(at, p)
        t = cells(at)
        assert not at.exception and "JH-102" not in t and "PR #50" not in t and "/pull/50" not in t and "FE-03" not in t, p
    at = page(at, "Sprint")
    stories = next(f for f in frames(at) if "Subtasks" in f.columns)
    assert list(stories["US"]) == ["US1.1"] and stories["PRs"].tolist() == [1]
    at = page(at, "Timeline")
    ev = next(f for f in frames(at) if "Tipo" in f.columns and "Quando" in f.columns)
    assert set(ev["Item"]) <= {"JH-901", "PR #40"}


def test_html_from_apis_is_escaped_in_new_pages(app):
    at = app.run()
    for p in ["Sprint", *NEW_PAGES]:
        at = page(at, p)
        assert "<img src=x" not in md(at), p


def test_burnup_and_time_in_status_render_in_sprint_tabs(app):
    at = page(app.run(), "Sprint")
    assert not at.exception
    text = md(at)
    assert "Burnup" in text and "Tempo em status" in text
    tis = next(f for f in frames(at) if "No status atual" in f.columns)
    assert {"JH-101", "JH-102"} <= {str(v).split("/")[-1] for v in tis["Jira"]}


def test_timeline_has_events_of_the_sprint(app):
    at = page(app.run(), "Timeline")
    assert not at.exception
    ev = next(f for f in frames(at) if "Tipo" in f.columns and "Quando" in f.columns)
    assert {"Status alterado", "PR aberta", "Commit"} <= set(ev["Tipo"])


def test_github_unavailable_disables_github_rules_and_says_so(monkeypatch, app):
    monkeypatch.setattr(sync, "_fetch_github", lambda _s: SourceResult.failed("GitHub", "GitHub: limite de requisições atingido (HTTP 429)"))
    sync.cache().reset()
    at = page(app.run(), "Agora")
    assert not at.exception
    assert any("GitHub indisponível" in w.value for w in at.warning)
    text = cells(at)
    assert "Done sem" not in text and "PR aguardando revisão" not in text and "Bloqueada por JH-55" in text   # Jira segue funcionando


def test_story_points_missing_everywhere_is_reported_as_unavailable(monkeypatch, app):
    s, mapper = load_settings(environ=ENV), DevMapper(MAPPING)

    def no_sp(_s):
        story = issue("JH-100", "US#2.1 Cadastro", subtasks=["JH-101"], sprint=SPRINT)
        sub = issue("JH-101", "BE-09 Validar", "Sub-task", ("Em andamento", "indeterminate"), "JH-100", assignee="Samuel Martins")
        return build(s, mapper, [story], search=[sub], fields_catalog=[])[0].fetch()
    monkeypatch.setattr(sync, "_fetch_jira", no_sp)
    sync.cache().reset()
    at = page(app.run(), "Sprint")
    assert not at.exception
    assert any(m.label == "Story Points" and m.value == "indisponível" for m in at.metric)


def test_management_is_recomputed_only_when_data_or_filter_changes(app, monkeypatch):
    import pandas as pd

    import services.mgmt as mg
    from domain import timeutil
    fixed = pd.Timestamp.now(tz="America/Sao_Paulo").floor("min")
    monkeypatch.setattr(timeutil, "now", lambda: fixed)
    calls, real = [], mg.build_mgmt
    monkeypatch.setattr(mg, "build_mgmt", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    at = app.run()
    for p in ["Agora", "Pessoas", "Timeline", "Sprint"]:       # navegar não pode repagar o cálculo
        at = page(at, p)
    assert not at.exception and len(calls) == 1
    next(s for s in at.sidebar.selectbox if s.label == "Desenvolvedor").set_value("cid-daniel").run()
    assert len(calls) == 2                                      # o filtro mudou: recalcula
