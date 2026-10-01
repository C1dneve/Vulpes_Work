"""Sincronização: cria os clientes, aplica o cache por fonte e decide o que mostrar quando algo falha.

Regras: falha nunca é cacheada; se houver o último resultado bom, ele é exibido como "dados antigos"
com o motivo da falha; sem nenhum resultado bom, a tela mostra o erro (nunca um "Sem dados" mudo).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import streamlit as st
from requests.auth import HTTPBasicAuth

from domain.people import DevMapper
from services.cache import SourceCache
from services.github import GitHubData, GitHubService
from services.http import HttpClient
from services.jira import JiraData, JiraService
from services.results import SourceResult
from settings import Settings

JIRA_TTL, GITHUB_TTL = 3600, 1800


@st.cache_resource
def cache() -> SourceCache:
    return SourceCache()


def clear(source: str | None = None) -> None:
    cache().clear(source)


def _fetch_jira(s: Settings) -> SourceResult:
    http = HttpClient("Jira", headers={"Accept": "application/json"}, auth=HTTPBasicAuth(s.jira.email, s.jira.token))
    return JiraService(http, s, DevMapper(s.dev_mapping)).fetch()


def _fetch_github(s: Settings) -> SourceResult:
    http = HttpClient("GitHub", headers={"Authorization": f"Bearer {s.github.token}", "Accept": "application/vnd.github+json",
                                         "X-GitHub-Api-Version": "2022-11-28"})
    return GitHubService(http, s, DevMapper(s.dev_mapping)).fetch()


@dataclass
class SourceView:
    """O que a tela vai usar de uma fonte: dados (frescos ou antigos), estado e mensagens."""
    name: str
    result: SourceResult | None       # resultado efetivo (fresco ou último bom); None = nada para mostrar
    stale: bool = False               # True = a busca atual falhou e estes são dados antigos
    errors: list[str] = field(default_factory=list)
    age_min: float | None = None

    @property
    def state(self) -> str:
        if self.result is None:
            return "error"
        if self.stale:
            return "stale"
        return "partial" if self.result.partial else "ok"

    @property
    def data(self):
        return None if self.result is None else self.result.data

    @property
    def messages(self) -> list[str]:
        return self.errors + ([] if self.result is None else self.result.warnings)


@dataclass
class Loaded:
    jira: SourceView
    github: SourceView


def _view(name: str, fetch_result: SourceResult) -> SourceView:
    key = name.lower()
    if fetch_result.ok:
        return SourceView(name, fetch_result, False, [], cache().age_minutes(key))
    last = cache().last_good(key)
    return SourceView(name, last, last is not None, list(fetch_result.errors), cache().age_minutes(key))


def load_all(s: Settings) -> Loaded:
    jira = _view("Jira", cache().get("jira", lambda: _fetch_jira(s), ttl=JIRA_TTL))
    gh = _view("GitHub", cache().get("github", lambda: _fetch_github(s), ttl=GITHUB_TTL))
    return Loaded(jira, gh)


def jira_data(v: SourceView) -> JiraData:
    return v.data if v.data is not None else JiraData.empty()


def github_data(v: SourceView, known_slugs: set[str]) -> GitHubData:
    """Dados do GitHub; `author_mapped` também vale para quem já tem o mesmo slug de alguém do Jira."""
    d = v.data if v.data is not None else GitHubData.empty()
    if not d.commits.empty:
        d = GitHubData(d.commits.assign(author_mapped=d.commits["author_mapped"] | d.commits["author"].isin(known_slugs)),
                       d.branches, d.prs)
    return d
