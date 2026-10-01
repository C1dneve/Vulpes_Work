"""Cliente HTTP com timeout, retry com backoff e erros tipados (401/403/404/429/5xx/timeout).

Nada aqui devolve "lista vazia" para esconder uma falha: ou volta JSON válido, ou levanta `ApiError`.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

import requests


class ApiError(Exception):
    """Falha ao falar com uma API externa."""

    def __init__(self, source: str, message: str, status: int | None = None, url: str | None = None):
        super().__init__(message)
        self.source, self.message, self.status, self.url = source, message, status, url

    def __str__(self) -> str:
        return self.message


class AuthError(ApiError):
    """401 — credencial inválida/expirada."""


class PermissionDenied(ApiError):
    """403 (sem ser limite de taxa) — a credencial não tem acesso ao recurso."""


class NotFound(ApiError):
    """404."""


class RateLimited(ApiError):
    """429, ou 403 com limite de taxa esgotado."""

    def __init__(self, source: str, message: str, retry_after: float | None = None, **kw: Any):
        super().__init__(source, message, **kw)
        self.retry_after = retry_after


class ServerError(ApiError):
    """5xx mesmo após as tentativas."""


class NetworkError(ApiError):
    """Timeout ou falha de conexão mesmo após as tentativas."""


def friendly(err: ApiError) -> str:
    """Mensagem curta e acionável para mostrar ao usuário (nunca inclui token)."""
    s = err.source
    if isinstance(err, AuthError):
        return f"{s}: falha de autenticação (HTTP 401) — confira e-mail/token no .env"
    if isinstance(err, PermissionDenied):
        return f"{s}: acesso negado (HTTP 403) — o token não tem permissão para este recurso ({err.message})"
    if isinstance(err, NotFound):
        return f"{s}: recurso não encontrado (HTTP 404) — confira board/repositório/organização ({err.message})"
    if isinstance(err, RateLimited):
        espera = f", tente de novo em ~{int(err.retry_after)}s" if err.retry_after else ""
        return f"{s}: limite de requisições atingido (HTTP 429){espera}"
    if isinstance(err, NetworkError):
        return f"{s}: sem resposta ({err.message})"
    if isinstance(err, ServerError):
        return f"{s}: erro no servidor (HTTP {err.status})"
    return f"{s}: {err.message}"


class HttpClient:
    def __init__(self, source: str, headers: Mapping[str, str] | None = None, auth: Any = None,
                 timeout: tuple[float, float] = (5, 30), max_retries: int = 3, backoff: float = 1.0,
                 max_wait: float = 30.0, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.time,
                 session_factory: Callable[[], requests.Session] = requests.Session):
        self.source, self.headers, self.auth = source, dict(headers or {}), auth
        self.timeout, self.max_retries, self.backoff, self.max_wait = timeout, max_retries, backoff, max_wait
        self._sleep, self._clock, self._session_factory = sleep, clock, session_factory
        self._local = threading.local()
        self.rate: dict[str, float | None] = {"limit": None, "remaining": None, "reset": None}
        self.calls = 0

    def _session(self) -> requests.Session:
        if not hasattr(self._local, "s"):
            s = self._session_factory()
            s.headers.update(self.headers)
            s.auth = self.auth
            self._local.s = s
        return self._local.s

    def _note_rate(self, h: Mapping[str, str]) -> None:
        for k, hk in (("limit", "X-RateLimit-Limit"), ("remaining", "X-RateLimit-Remaining"), ("reset", "X-RateLimit-Reset")):
            v = h.get(hk)
            if v is not None:
                try:
                    self.rate[k] = float(v)
                except ValueError:
                    pass

    def _rate_wait(self, resp: requests.Response) -> float | None:
        """Quanto esperar (s) se a resposta indica limite de taxa; None se não indica."""
        h = resp.headers
        if h.get("Retry-After"):
            try:
                return max(float(h["Retry-After"]), 0.0)
            except ValueError:
                return 1.0
        if h.get("X-RateLimit-Remaining") == "0" and h.get("X-RateLimit-Reset"):
            return max(float(h["X-RateLimit-Reset"]) - self._clock(), 0.0)
        return None

    @staticmethod
    def _detail(resp: requests.Response) -> str:
        try:
            body = resp.json()
        except ValueError:
            return (resp.text or "")[:200]
        if isinstance(body, dict):
            msgs = body.get("errorMessages")
            if msgs:
                return "; ".join(map(str, msgs))[:200]
            if body.get("message"):
                return str(body["message"])[:200]
        return ""

    def request_json(self, method: str, url: str, params: Mapping[str, Any] | None = None,
                     json: Any = None) -> Any:
        last: ApiError | None = None
        for attempt in range(self.max_retries + 1):
            self.calls += 1
            try:
                resp = self._session().request(method, url, params=params, json=json, timeout=self.timeout)
            except requests.Timeout:
                last = NetworkError(self.source, "tempo esgotado", url=url)
            except requests.ConnectionError as e:
                last = NetworkError(self.source, f"falha de conexão ({type(e).__name__})", url=url)
            else:
                self._note_rate(resp.headers)
                s = resp.status_code
                if 200 <= s < 300:
                    if s == 204 or not resp.content:
                        return {}
                    try:
                        return resp.json()
                    except ValueError as e:
                        raise ApiError(self.source, "resposta não é JSON válido", s, url) from e
                detail = self._detail(resp)
                if s == 401:
                    raise AuthError(self.source, detail or "não autenticado", s, url)
                if s == 404:
                    raise NotFound(self.source, detail or url, s, url)
                wait = self._rate_wait(resp) if s in (403, 429) else None
                if s == 429 or wait is not None:
                    if wait is None:
                        wait = self.backoff * 2 ** attempt
                    last = RateLimited(self.source, detail or "limite de taxa", wait, status=s, url=url)
                    if wait > self.max_wait or attempt == self.max_retries:
                        raise last
                    self._sleep(wait)
                    continue
                if s == 403:
                    raise PermissionDenied(self.source, detail or url, s, url)
                if s >= 500:
                    last = ServerError(self.source, detail or f"HTTP {s}", s, url)
                else:
                    raise ApiError(self.source, detail or f"HTTP {s}", s, url)
            if attempt < self.max_retries:
                self._sleep(self.backoff * 2 ** attempt)
        assert last is not None
        raise last

    def get_json(self, url: str, params: Mapping[str, Any] | None = None) -> Any:
        return self.request_json("GET", url, params=params)

    def post_json(self, url: str, json: Any) -> Any:
        return self.request_json("POST", url, json=json)
