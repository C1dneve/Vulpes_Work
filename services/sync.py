"""Adaptador Streamlit da sincronização; conserva o singleton do cache da sessão da aplicação."""
from __future__ import annotations

import time

import streamlit as st

from application.sync import (
    GITHUB_TTL,
    JIRA_TTL,
    Loaded,
    SourceView,
    SyncSources,
    github_data,
    jira_data,
)
from services.cache import SourceCache
from services.results import SourceResult
from settings import Settings


@st.cache_resource
def cache() -> SourceCache:
    return SourceCache()


def clear(source: str | None = None) -> None:
    cache().clear(source)


def _fetch_jira(settings: Settings) -> SourceResult:
    """Ponto de substituição mantido para os testes de integração existentes."""
    return SyncSources(cache(), clock=time.time)._fetch_jira(settings)


def _fetch_github(settings: Settings) -> SourceResult:
    """Ponto de substituição mantido para os testes de integração existentes."""
    return SyncSources(cache(), clock=time.time)._fetch_github(settings)


def load_all(settings: Settings) -> Loaded:
    """Mantém a API usada pelo dashboard e delega a sincronização ao caso de uso."""
    return SyncSources(
        cache(),
        clock=time.time,
        jira_fetcher=_fetch_jira,
        github_fetcher=_fetch_github,
    ).execute(settings)


__all__ = [
    "GITHUB_TTL",
    "JIRA_TTL",
    "Loaded",
    "SourceView",
    "cache",
    "clear",
    "github_data",
    "jira_data",
    "load_all",
]
