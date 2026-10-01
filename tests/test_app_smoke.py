"""Executa o app.py inteiro (Streamlit AppTest) com Jira/GitHub simulados e navega por todas as páginas."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from domain.people import DevMapper
from services import sync
from services.github import GitHubService
from services.results import SourceResult
from settings import load_settings
from tests.conftest import ENV, MAPPING
from tests.test_github_service import BR_BACK, gh_commit, gh_pr, routes
from tests.test_jira_service import SPRINT, build, hist, issue

EVIL = '<img src=x onerror="alert(1)">'
PAGES = ["Dashboard", "Sprint", "Issues", "Commits", "Relatórios", "Configurações"]


def jira_result(settings, mapper, title=EVIL):
    story = issue("JH-100", f"US#2.1 Cadastro {title}", subtasks=["JH-101", "JH-102"], sprint=SPRINT)
    subs = [issue("JH-101", f"BE-09 Validar {title}", "Sub-task", ("Concluído", "done"), "JH-100", assignee="Samuel Martins",
                  spent=7200, est=10800),
            issue("JH-102", "FE-03 Formulário", "Sub-task", ("Em análise", "indeterminate"), "JH-100", assignee="Cid Daniel")]
    hs = {"JH-101": [hist("1", "2026-09-22T10:00:00.000-0300", "A fazer", "Em andamento"),
                     hist("2", "2026-09-24T10:00:00.000-0300", "Em análise", "Concluído")],
          "JH-102": [hist("3", "2026-09-23T10:00:00.000-0300", "Em andamento", "Em análise")]}
    svc, _ = build(settings, mapper, [story], search=subs, histories=hs)
    return svc.fetch()


def github_result(settings, mapper):
    c1 = gh_commit("c1", f"feat(JH-101): implementar validação do cadastro {EVIL}", days=3)
    c2 = gh_commit("c2", "feat(JH-102): criar formulário de cadastro de cliente", login=None, name="Pedro P.", days=2)
    bot = gh_commit("bot", "chore(deps): bump requests", login="dependabot[bot]", ctype="Bot", days=2)
    squash = gh_commit("s1", "[JH-100] US2.1 — Cadastro (#42)", days=1)
    pr = gh_pr(42, BR_BACK, "c2", state="closed", merged=True, merge_sha="s1", title=f"[JH-100] US2.1 — Cadastro {EVIL}")
    rts = routes([squash, bot], [("main", "s1")], prs_closed=[pr], pr_commits={42: [c1, c2]})
    from tests.fakes import FakeHttp
    return GitHubService(FakeHttp(rts), settings, mapper).fetch()


@pytest.fixture
def app(monkeypatch, tmp_path):
    import json

    import settings as settings_mod
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    (tmp_path / "config.json").write_text(json.dumps({"github": {"org": "Team", "repos": ["repo"]}, "dev_mapping": MAPPING}))
    monkeypatch.setattr(settings_mod, "ROOT", tmp_path)   # o app lê config/.env do diretório de teste
    s = load_settings(environ=ENV)
    mapper = DevMapper(MAPPING)
    sync.cache().reset()
    monkeypatch.setattr(sync, "_fetch_jira", lambda _s: jira_result(s, mapper))
    monkeypatch.setattr(sync, "_fetch_github", lambda _s: github_result(s, mapper))
    return AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=60)


def page(at, name):
    at.sidebar.radio[0].set_value(name)
    return at.run()


def test_every_page_renders_without_exception(app):
    at = app.run()
    assert not at.exception, at.exception
    for p in PAGES:
        at = page(at, p)
        assert not at.exception, (p, [e.value for e in at.exception])


def test_default_sprint_is_the_active_one(app):
    at = app.run()
    sel = next(s for s in at.sidebar.selectbox if s.label == "Sprint")
    assert sel.value == "Sprint 5"


def test_html_from_apis_is_escaped_everywhere(app):
    at = app.run()
    for p in ["Dashboard", "Sprint", "Issues", "Commits", "Configurações"]:
        at = page(at, p)
        html = " ".join(m.value for m in at.markdown)
        assert "<img src=x" not in html, p
    at = page(at, "Dashboard")
    assert "&lt;img" in " ".join(m.value for m in at.markdown)


def test_literal_search_does_not_crash_with_regex_chars(app):
    at = page(app.run(), "Issues")
    for term in ["(", "[", "*", "+", "\\", "?"]:
        at.text_input[0].set_value(term).run()
        assert not at.exception, term


def test_squash_merged_work_counts_as_delivered_in_ui(app):
    at = page(app.run(), "Commits")
    kpis = " ".join(m.value for m in at.markdown)
    assert "Entregues" in kpis and not at.exception


def test_unmapped_author_panel_shows_pedro(app):
    at = page(app.run(), "Configurações")
    text = " ".join(m.value for m in at.markdown)
    assert "Autores não mapeados" in text and "Pedro P." in text
    assert any(b.label == "Vincular" for b in at.button)


def test_dev_filter_is_global(app):
    at = app.run()
    dev = next(s for s in at.sidebar.selectbox if s.label == "Desenvolvedor")
    assert "Cid Daniel" in dev.options
    alvo = "cid-daniel"   # slug do colaborador (o rótulo exibido é "Cid Daniel")
    at = page(at, "Commits")
    antes = " ".join(m.value for m in at.markdown)
    next(s for s in at.sidebar.selectbox if s.label == "Desenvolvedor").set_value(alvo).run()
    at = at.run()
    depois = " ".join(m.value for m in at.markdown)
    assert not at.exception
    assert antes != depois   # o mesmo filtro muda a tela de Commits (antes só mudava a de Issues)
    at = page(at, "Issues")
    assert not at.exception


def test_jira_failure_shows_error_not_empty_state(monkeypatch, app):
    monkeypatch.setattr(sync, "_fetch_jira", lambda _s: SourceResult.failed("Jira", "Jira: falha de autenticação (HTTP 401) — confira e-mail/token no .env"))
    sync.cache().reset()
    at = app.run()
    assert not at.exception
    assert any("falha de autenticação" in e.value for e in at.error)


def test_stale_data_is_shown_when_refresh_fails(monkeypatch, app):
    at = app.run()
    assert not at.exception
    monkeypatch.setattr(sync, "_fetch_github", lambda _s: SourceResult.failed("GitHub", "GitHub: limite de requisições atingido (HTTP 429)"))
    sync.cache()._fresh.clear()   # expira o cache fresco; o último resultado bom permanece
    at = at.run()
    assert not at.exception
    assert any("429" in e.value and "dados de" in e.value for e in at.error)


def test_refresh_all_with_failing_source_keeps_showing_the_last_good_data(monkeypatch, app):
    at = app.run()
    assert not at.exception
    monkeypatch.setattr(sync, "_fetch_github", lambda _s: SourceResult.failed("GitHub", "GitHub: limite de requisições atingido (HTTP 429)"))
    next(b for b in at.sidebar.button if "Atualizar tudo" in b.label).click()   # o botão chama sync.clear()
    at = at.run()
    assert not at.exception
    assert any("429" in e.value and "dados de" in e.value for e in at.error)    # mostra o erro E os dados antigos
    at = page(at, "Commits")
    assert not at.exception


def test_unexpected_github_payload_does_not_crash_the_app(monkeypatch, app):
    at = app.run()
    monkeypatch.setattr(sync, "_fetch_github", lambda _s: SourceResult.unexpected("GitHub", KeyError("commit")))
    sync.cache().clear()
    at = at.run()
    assert not at.exception
    assert any("resposta inesperada" in e.value for e in at.error)


def test_subtask_in_the_active_sprint_shows_up_even_if_its_story_is_in_another_sprint(monkeypatch, app):
    from tests.test_jira_service import SPRINT4
    story = issue("JH-100", "US#2.1 Cadastro", subtasks=["JH-101"], sprint=SPRINT4)
    sub = issue("JH-101", "BE-09 Validar", "Sub-task", ("Em andamento", "indeterminate"), "JH-100", assignee="Samuel Martins",
                sprint=SPRINT)
    s = load_settings(environ=ENV)
    monkeypatch.setattr(sync, "_fetch_jira", lambda _s: build(s, DevMapper(MAPPING), [story, sub])[0].fetch())
    sync.cache().reset()
    at = app.run()
    assert not at.exception
    assert next(x for x in at.sidebar.selectbox if x.label == "Sprint").value == "Sprint 5"
    at = page(at, "Issues")
    assert not at.exception and len(at.dataframe[0].value) == 1     # JH-101 aparece na Sprint 5
    at = page(at, "Sprint")
    assert not at.exception
