"""Limiares de gestão do Vulpes Hub — UM lugar só (nada de números mágicos espalhados pela UI).

Configuráveis em `config.json` → `management`. Valor inválido cai no padrão e vira aviso em Configurações.
"""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Thresholds:
    due_soon_days: int = 2             # due date a até N dias (corridos) de hoje = "Próximo do prazo"
    inactive_business_days: int = 2    # task em andamento sem atividade há N dias ÚTEIS = inativa
    pr_review_wait_hours: int = 24     # PR aberta (não-rascunho) sem revisão há N horas = atenção
    pr_old_days: int = 5               # PR aberta há N dias = antiga
    sprint_ending_days: int = 2        # sprint termina em até N dias com itens abertos = atenção
    recent_days: int = 2               # concluídas/mergeadas nos últimos N dias aparecem como alerta INFORMATIVO


def parse_thresholds(cfg: object, problems: list[str]) -> Thresholds:
    """`config.json → management`. Inteiros > 0; o resto vira o padrão com um aviso."""
    if cfg is None:
        return Thresholds()
    if not isinstance(cfg, dict):
        problems.append("management deve ser um objeto {limiar: número}; usando padrões.")
        return Thresholds()
    known = {f.name: f.default for f in fields(Thresholds)}
    values: dict[str, int] = {}
    for k, v in cfg.items():
        if k not in known:
            problems.append(f"management.{k} é desconhecido e foi ignorado.")
        elif isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            problems.append(f"management.{k} deve ser um inteiro > 0; usando {known[k]}.")
        else:
            values[k] = v
    return Thresholds(**values)
