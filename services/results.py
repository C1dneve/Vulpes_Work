"""Resultado de uma fonte de dados (Jira/GitHub): dados + erros + avisos, nunca "vazio silencioso"."""
from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from domain import timeutil

log = logging.getLogger(__name__)


@dataclass
class SourceResult:
    source: str
    data: Any = None
    errors: list[str] = field(default_factory=list)  # falhas: os dados NÃO são confiáveis/completos
    warnings: list[str] = field(default_factory=list)  # parcial: dados úteis, mas com ressalvas
    stats: dict[str, Any] = field(default_factory=dict)
    fetched_at: pd.Timestamp = field(default_factory=timeutil.now)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def partial(self) -> bool:
        return bool(self.warnings)

    @property
    def status(self) -> str:
        return "error" if self.errors else ("partial" if self.warnings else "ok")

    @classmethod
    def failed(cls, source: str, *errors: str) -> SourceResult:
        return cls(source=source, errors=list(errors))

    @classmethod
    def unexpected(cls, source: str, exc: BaseException, secrets: Iterable[str] = ()) -> SourceResult:
        """Falha inesperada (ex.: payload da API sem um campo esperado) como resultado CONTROLADO.

        O traceback vai para o log (nada é engolido em silêncio) e a tela recebe uma mensagem curta com o tipo do erro.
        Valores de `secrets` (tokens) são removidos do texto.
        """
        log.error("%s: falha inesperada ao processar a resposta da API", source, exc_info=exc)
        detail = str(exc)[:200]
        for secret in secrets:
            if secret:
                detail = detail.replace(secret, "***")
        return cls.failed(source, f"{source}: resposta inesperada da API — {type(exc).__name__}: {detail}")
