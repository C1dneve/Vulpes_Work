"""Fakes de teste: HTTP simulado (sem rede) e helpers para montar respostas do Jira/GitHub."""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

import pandas as pd
import requests


class FakeHttp:
    """Substitui `HttpClient`: roteia por regex na URL; handler pode ser dado, callable ou Exception."""

    def __init__(self, routes: list[tuple[str, Any]]):
        self.routes = routes
        self.calls = 0
        self.log: list[tuple[str, str, dict]] = []
        self.rate: dict[str, float | None] = {"limit": None, "remaining": None, "reset": None}

    def _dispatch(self, method: str, url: str, params: dict | None) -> Any:
        self.calls += 1
        self.log.append((method, url, dict(params or {})))
        for pattern, handler in self.routes:
            if re.search(pattern, url):
                out = handler(url, params or {}) if callable(handler) else handler
                if isinstance(out, Exception):
                    raise out
                return out
        raise AssertionError(f"rota não mockada: {method} {url}")

    def get_json(self, url: str, params: dict | None = None) -> Any:
        return self._dispatch("GET", url, params)

    def post_json(self, url: str, json: Any) -> Any:  # noqa: A002
        return self._dispatch("POST", url, json)

    def urls(self, needle: str) -> list[str]:
        return [u for _, u, _ in self.log if needle in u]


def paged_list(items: list) -> Callable[[str, dict], list]:
    """GitHub: lista paginada por page/per_page."""
    def handler(url: str, params: dict) -> list:
        n, page = params.get("per_page", 100), params.get("page", 1)
        return items[(page - 1) * n: page * n]
    return handler


def offset_pages(key: str, items: list, cap: int | None = None, with_total: bool = False) -> Callable[[str, dict], dict]:
    """Jira: paginação startAt/maxResults; `cap` simula o servidor limitando o tamanho da página."""
    def handler(url: str, params: dict) -> dict:
        start, size = params.get("startAt", 0), params.get("maxResults", 50)
        size = min(size, cap) if cap else size
        page = items[start:start + size]
        out = {"startAt": start, "maxResults": size, key: page}
        if with_total:
            out["total"] = len(items)
        return out
    return handler


def make_response(status: int, body: Any = None, headers: dict | None = None) -> requests.Response:
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(body).encode() if body is not None else b""
    r.headers.update(headers or {})
    return r


class FakeSession:
    """requests.Session falso: devolve respostas/exceções roteirizadas, em ordem."""

    def __init__(self, script: list):
        self.script = list(script)
        self.headers: dict = {}
        self.auth = None
        self.requests: list[tuple[str, str]] = []

    def request(self, method, url, params=None, json=None, timeout=None):  # noqa: A002
        self.requests.append((method, url))
        out = self.script.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def iso(days_ago: float = 0, hours: float = 0) -> str:
    """Timestamp UTC no formato do GitHub, relativo a agora."""
    t = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_ago, hours=hours)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")
