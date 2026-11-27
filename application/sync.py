"""Casos de uso para sincronizar Jira e GitHub sem dependência de Streamlit."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from requests.auth import HTTPBasicAuth

from domain.people import DevMapper
from services.cache import SourceCache
from services.github import GitHubData, GitHubService
from services.http import HttpClient
from services.jira import JiraData, JiraService
from services.results import SourceResult
from settings import Settings

JIRA_TTL, GITHUB_TTL = 3600, 1800
HttpClientFactory = Callable[..., Any]
ServiceFactory = Callable[..., Any]
SourceFetcher = Callable[[Settings], SourceResult]


@dataclass
class SourceView:
    """Dados efetivos de uma fonte, incluindo estado e mensagens de qualidade."""

    name: str
    result: SourceResult | None
    stale: bool = False
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
    def data(self) -> Any | None:
        return None if self.result is None else self.result.data

    @property
    def messages(self) -> list[str]:
        return self.errors + ([] if self.result is None else self.result.warnings)


@dataclass
class Loaded:
    jira: SourceView
    github: SourceView


class SyncSources:
    """Sincroniza as fontes com cache e dependências explícitas e substituíveis em testes."""

    def __init__(
        self,
        source_cache: SourceCache,
        *,
        http_client_factory: HttpClientFactory = HttpClient,
        clock: Callable[[], float] = time.time,
        jira_service_factory: ServiceFactory = JiraService,
        github_service_factory: ServiceFactory = GitHubService,
        jira_fetcher: SourceFetcher | None = None,
        github_fetcher: SourceFetcher | None = None,
    ) -> None:
        self._cache = source_cache
        self._http_client_factory = http_client_factory
        self._clock = clock
        self._jira_service_factory = jira_service_factory
        self._github_service_factory = github_service_factory
        self._jira_fetcher = jira_fetcher
        self._github_fetcher = github_fetcher

    def _fetch_jira(self, settings: Settings) -> SourceResult:
        http = self._http_client_factory(
            "Jira",
            headers={"Accept": "application/json"},
            auth=HTTPBasicAuth(settings.jira.email, settings.jira.token),
            clock=self._clock,
        )
        service = self._jira_service_factory(http, settings, DevMapper(settings.dev_mapping))
        return cast(SourceResult, service.fetch())

    def _fetch_github(self, settings: Settings) -> SourceResult:
        http = self._http_client_factory(
            "GitHub",
            headers={
                "Authorization": f"Bearer {settings.github.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            clock=self._clock,
        )
        service = self._github_service_factory(http, settings, DevMapper(settings.dev_mapping))
        return cast(SourceResult, service.fetch())

    def _source_view(self, name: str, fetch_result: SourceResult) -> SourceView:
        key = name.lower()
        age = self._cache.age_minutes(key)
        if fetch_result.ok:
            return SourceView(name, fetch_result, False, [], age)
        last = self._cache.last_good(key)
        return SourceView(name, last, last is not None, list(fetch_result.errors), age)

    def execute(self, settings: Settings) -> Loaded:
        """Carrega Jira e GitHub, mantendo a independência de cache e o último resultado bom."""
        fetch_jira = self._jira_fetcher or self._fetch_jira
        fetch_github = self._github_fetcher or self._fetch_github
        jira_result = self._cache.get("jira", lambda: fetch_jira(settings), ttl=JIRA_TTL)
        github_result = self._cache.get("github", lambda: fetch_github(settings), ttl=GITHUB_TTL)
        return Loaded(
            jira=self._source_view("Jira", jira_result),
            github=self._source_view("GitHub", github_result),
        )


def jira_data(view: SourceView) -> JiraData:
    return cast(JiraData, view.data) if view.data is not None else JiraData.empty()


def github_data(view: SourceView, known_slugs: set[str]) -> GitHubData:
    """Marca como mapeados autores cujo slug já corresponde a alguém do Jira."""
    data = cast(GitHubData, view.data) if view.data is not None else GitHubData.empty()
    if not data.commits.empty:
        commits = data.commits.assign(
            author_mapped=data.commits["author_mapped"] | data.commits["author"].isin(known_slugs)
        )
        data = GitHubData(commits, data.branches, data.prs)
    return data
