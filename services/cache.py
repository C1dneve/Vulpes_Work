"""Cache por fonte com single-flight: buscas concorrentes da mesma fonte compartilham uma execução.

- sucesso completo -> TTL normal;
- sucesso parcial -> TTL curto;
- falha -> nunca é cacheada; o último resultado bom permanece disponível;
- clear() expira os resultados frescos, mas preserva last_good;
- reset() esquece ambos.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from services.results import SourceResult


@dataclass
class _Entry:
    result: SourceResult
    stored_at: float
    ttl: float


@dataclass
class _Flight:
    event: threading.Event = field(default_factory=threading.Event)
    result: SourceResult | None = None
    error: BaseException | None = None


class SourceCache:
    def __init__(self, clock: Callable[[], float] = time.time, wait_timeout: float = 60.0):
        if wait_timeout < 0:
            raise ValueError("wait_timeout deve ser maior ou igual a zero")
        self._clock = clock
        self._wait_timeout = wait_timeout
        self._lock = threading.Lock()
        self._fresh: dict[str, _Entry] = {}
        self._last_good: dict[str, _Entry] = {}
        self._inflight: dict[str, _Flight] = {}

    def get(self, source: str, fetch: Callable[[], SourceResult], ttl: float = 1800,
            partial_ttl: float = 120, force: bool = False, timeout: float | None = None) -> SourceResult:
        wait_timeout = self._wait_timeout if timeout is None else timeout
        if wait_timeout < 0:
            raise ValueError("timeout deve ser maior ou igual a zero")

        with self._lock:
            entry = self._fresh.get(source)
            if entry and not force and self._clock() - entry.stored_at < entry.ttl:
                return entry.result

            flight = self._inflight.get(source)
            leader = flight is None
            if leader:
                flight = _Flight()
                self._inflight[source] = flight

        # A thread que encontrou uma execução em andamento aguarda o mesmo resultado.
        if not leader:
            assert flight is not None
            if not flight.event.wait(wait_timeout):
                # Libera a fonte para uma nova tentativa caso a execução anterior esteja travada.
                # O líder antigo não poderá gravar no cache se outra execução assumir a fonte.
                with self._lock:
                    if self._inflight.get(source) is flight:
                        self._inflight.pop(source, None)
                raise TimeoutError(f"tempo de espera esgotado pela sincronização de {source}")
            if flight.error is not None:
                raise flight.error
            if flight.result is None:
                raise RuntimeError(f"sincronização de {source} terminou sem resultado")
            return flight.result

        assert flight is not None
        try:
            result = fetch()
        except BaseException as exc:
            with self._lock:
                flight.error = exc
                if self._inflight.get(source) is flight:
                    self._inflight.pop(source, None)
                flight.event.set()
            raise

        with self._lock:
            flight.result = result
            # Uma espera expirada pode ter liberado a fonte para um novo líder.
            if self._inflight.get(source) is flight:
                if result.ok:
                    entry = _Entry(result, self._clock(), partial_ttl if result.partial else ttl)
                    self._fresh[source] = entry
                    self._last_good[source] = entry
                else:
                    self._fresh.pop(source, None)
                self._inflight.pop(source, None)
            flight.event.set()
        return result

    def last_good(self, source: str) -> SourceResult | None:
        with self._lock:
            entry = self._last_good.get(source)
            return entry.result if entry else None

    def age_minutes(self, source: str) -> float | None:
        with self._lock:
            entry = self._last_good.get(source)
            return None if entry is None else (self._clock() - entry.stored_at) / 60

    def clear(self, source: str | None = None) -> None:
        """Expira o cache fresco e invalida o líder atual, preservando last_good."""
        with self._lock:
            if source is None:
                self._fresh.clear()
                self._inflight.clear()
            else:
                self._fresh.pop(source, None)
                self._inflight.pop(source, None)

    def reset(self) -> None:
        """Esquece tudo, inclusive last_good e execuções em andamento."""
        with self._lock:
            self._fresh.clear()
            self._last_good.clear()
            self._inflight.clear()
