"""Cache por fonte (jira / github / analytics) que NUNCA guarda falhas.

- resultado ok      -> guardado por `ttl`
- resultado parcial -> guardado por `partial_ttl` (curto: a ressalva pode ser passageira)
- resultado com erro -> NÃO guardado; se houver o último resultado bom, ele fica disponível como
  `last_good` para a tela mostrar dados antigos com um aviso, em vez de "Sem dados".
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from services.results import SourceResult


@dataclass
class _Entry:
    result: SourceResult
    stored_at: float
    ttl: float


class SourceCache:
    def __init__(self, clock: Callable[[], float] = time.time):
        self._clock = clock
        self._lock = threading.Lock()
        self._fresh: dict[str, _Entry] = {}
        self._last_good: dict[str, _Entry] = {}

    def get(self, source: str, fetch: Callable[[], SourceResult], ttl: float = 1800,
            partial_ttl: float = 120, force: bool = False) -> SourceResult:
        with self._lock:
            e = self._fresh.get(source)
            if e and not force and self._clock() - e.stored_at < e.ttl:
                return e.result
        result = fetch()
        if result.ok:
            entry = _Entry(result, self._clock(), partial_ttl if result.partial else ttl)
            with self._lock:
                self._fresh[source] = entry
                self._last_good[source] = entry
        else:
            with self._lock:
                self._fresh.pop(source, None)
        return result

    def last_good(self, source: str) -> SourceResult | None:
        e = self._last_good.get(source)
        return e.result if e else None

    def age_minutes(self, source: str) -> float | None:
        e = self._last_good.get(source)
        return None if e is None else (self._clock() - e.stored_at) / 60

    def clear(self, source: str | None = None) -> None:
        """Expira o cache FRESCO (uma fonte ou todas) para forçar nova busca. O último resultado bom é preservado:
        se a nova busca falhar, a tela ainda mostra os dados antigos com o aviso do erro."""
        with self._lock:
            if source is None:
                self._fresh.clear()
            else:
                self._fresh.pop(source, None)

    def reset(self) -> None:
        """Esquece TUDO (inclusive o último resultado bom). Uso: testes / troca de credenciais."""
        with self._lock:
            self._fresh.clear()
            self._last_good.clear()
