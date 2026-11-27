from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pandas as pd

from application.sync import SyncSources
from application.use_cases import BuildManagement, BuildScope
from domain.thresholds import Thresholds
from services import mgmt as mgmt_module
from services.cache import SourceCache
from services.context import Context
from services.mgmt import Mgmt
from services.results import SourceResult
from settings import GitHubSettings, JiraSettings, LinkSettings, Settings
from tests.test_context import bundle


def _settings() -> Settings:
    return Settings(
        jira=JiraSettings(email="dev@example.test", token="jira-token", domain="jira.example.test", board_id="1", project="JH"),
        github=GitHubSettings(token="github-token", org="org", repos=("repo",)),
        linking=LinkSettings(jira_key_pattern=r"JH-\d+"),
        dev_mapping={},
        config_path=Path("config.json"),
        env_path=Path(".env"),
    )


class _FakeService:
    def __init__(self, result: SourceResult) -> None:
        self._result = result

    def fetch(self) -> SourceResult:
        return self._result


def test_application_imports_without_loading_streamlit() -> None:
    source = (
        "import sys; "
        "import application.sync; "
        "import application.use_cases; "
        "import contracts.models; "
        "assert 'streamlit' not in sys.modules"
    )
    result = subprocess.run([sys.executable, "-c", source], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_sync_sources_uses_injected_http_service_factories_cache_and_clock() -> None:
    clock_value = 123.0
    observed: list[tuple[str, Any, Any]] = []
    jira_result = SourceResult("Jira", data="jira-data")
    github_result = SourceResult("GitHub", data="github-data")

    def http_factory(source: str, *, headers: dict[str, str], auth: Any = None, clock: Any) -> object:
        observed.append((source, headers, clock))
        return object()

    def jira_factory(http: Any, settings: Settings, mapper: Any) -> _FakeService:
        return _FakeService(jira_result)

    def github_factory(http: Any, settings: Settings, mapper: Any) -> _FakeService:
        return _FakeService(github_result)

    service = SyncSources(
        SourceCache(clock=lambda: clock_value),
        http_client_factory=http_factory,
        clock=lambda: clock_value,
        jira_service_factory=jira_factory,
        github_service_factory=github_factory,
    )
    loaded = service.execute(_settings())

    assert loaded.jira.result is jira_result and loaded.github.result is github_result
    assert loaded.jira.state == "ok" and loaded.github.state == "ok"
    assert [entry[0] for entry in observed] == ["Jira", "GitHub"]
    assert all(entry[2]() == clock_value for entry in observed)
    assert observed[0][1] == {"Accept": "application/json"}
    assert observed[1][1]["Authorization"] == "Bearer github-token"


def test_sync_sources_preserves_last_good_when_a_refresh_fails() -> None:
    cache = SourceCache(clock=lambda: 100.0)
    previous = SourceResult("Jira", data="last-good")
    cache.get("jira", lambda: previous)
    cache.clear("jira")

    service = SyncSources(
        cache,
        http_client_factory=lambda *args, **kwargs: object(),
        jira_service_factory=lambda *args, **kwargs: _FakeService(SourceResult.failed("Jira", "falha simulada")),
        github_service_factory=lambda *args, **kwargs: _FakeService(SourceResult("GitHub", data="github")),
    )
    loaded = service.execute(_settings())

    assert loaded.jira.result is previous
    assert loaded.jira.stale and loaded.jira.errors == ["falha simulada"]


def test_build_scope_uses_the_existing_global_context_rules() -> None:
    scope = BuildScope().execute(bundle(), Context(sprint="Sprint 5", dev="cid"))
    assert set(scope.items["subtask_key"]) == {"JH-11", "JH-21"}
    assert set(scope.commits["author"]) == {"cid"}


def test_build_management_uses_the_injected_clock_when_now_is_not_supplied() -> None:
    expected = pd.Timestamp("2026-11-26T12:00:00")
    received: dict[str, Any] = {}

    def builder(*args: Any, **kwargs: Any) -> Mgmt:
        received.update(kwargs)
        return cast(Mgmt, object())

    use_case = BuildManagement(builder=builder, clock=lambda: expected)
    use_case.execute(bundle(), Context(), Thresholds())

    assert received["now"] == expected


def test_build_management_resolves_default_builder_at_execution(monkeypatch: Any) -> None:
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def replacement_builder(*args: Any, **kwargs: Any) -> Mgmt:
        calls.append((args, kwargs))
        return cast(Mgmt, object())

    monkeypatch.setattr(mgmt_module, "build_mgmt", replacement_builder)
    use_case = BuildManagement(clock=lambda: pd.Timestamp("2026-11-26T12:00:00"))

    use_case.execute(bundle(), Context(), Thresholds())

    assert len(calls) == 1
