"""Tempo em cada status, a partir do changelog do Jira (funções puras).

Definições (para não inventar precisão que o Jira não dá):
  * FUSO: todos os instantes são tz-aware em America/Sao_Paulo; a duração é o tempo DECORRIDO absoluto (não a diferença de
    relógio de parede), então mudança de horário de verão não distorce.
  * TEMPO CORRIDO (24h/dia, fins de semana incluídos): o Jira não informa horário comercial.
  * INÍCIO do 1º status = criação da issue (ou a 1ª transição, se a issue foi movida e a data de criação for posterior a ela).
  * FIM do status atual = agora. Se a issue ainda está no status, o tempo atual é `agora − entrada` (segmento `current`).
  * Issue SEM transições no histórico = ficou no status atual desde a criação. Issue cujo histórico NÃO foi carregado por inteiro
    (falha parcial) = DESCONHECIDA: não recebe tempo nenhum (em vez de um número errado).
  * Vai-e-volta: os tempos de cada visita somam; `visits` conta as entradas no status.
  * Se o último destino do histórico difere do status atual do Jira, vale o status atual do Jira e a issue é marcada `inconsistent`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from domain import statuses as S
from domain.fmt import isna

SEG_COLS = ["subtask_key", "status", "group", "start", "end", "hours", "current", "basis", "inconsistent"]


@dataclass
class TimeInStatus:
    segments: pd.DataFrame
    unknown: list[str] = field(default_factory=list)      # issues sem histórico confiável: sem tempo calculado


def _hours(a: pd.Timestamp, b: pd.Timestamp) -> float:
    seconds = float((b - a).total_seconds())
    return max(seconds / 3600.0, 0.0)


def time_in_status(items: pd.DataFrame, changelog: pd.DataFrame, now: pd.Timestamp,
                   history_unknown: set[str] | frozenset[str] = frozenset()) -> TimeInStatus:
    rows: list[dict[str, object]] = []
    unknown: list[str] = []
    by_key = {k: g.sort_values("ts") for k, g in changelog.groupby("subtask_key")} if not changelog.empty else {}
    for _, it in items.iterrows():
        k = it["subtask_key"]
        if k in history_unknown:
            unknown.append(k)
            continue
        created, evs = it.get("created"), by_key.get(k)
        cur_name = it["status_name"] or "(sem status)"

        def seg(name: str, group: str, start: pd.Timestamp, end: pd.Timestamp, current: bool = False,
                basis: str = "historico", bad: bool = False, _k: str = str(k)) -> None:
            rows.append({"subtask_key": _k, "status": name, "group": group, "start": start, "end": end,
                         "hours": _hours(start, end), "current": current, "basis": basis, "inconsistent": bad})

        if evs is None or evs.empty:
            if isna(created):
                unknown.append(k)
                continue
            seg(cur_name, it["status_group"], created, now, True, "sem_transicoes")
            continue
        first = evs.iloc[0]
        start0 = first["ts"] if isna(created) else min(created, first["ts"])
        seg(first["from_name"], first["from_group"], start0, first["ts"])
        for i in range(len(evs)):
            e = evs.iloc[i]
            last = i == len(evs) - 1
            end = now if last else evs.iloc[i + 1]["ts"]
            name, group = e["to_name"], e["to_group"]
            bad = last and (name or "").strip().lower() != (cur_name or "").strip().lower()
            if bad:     # o status atual do Jira é a verdade sobre "onde está agora"
                name, group = cur_name, it["status_group"]
            seg(name, group, e["ts"], end, current=last, bad=bad)
    return TimeInStatus(pd.DataFrame(rows, columns=SEG_COLS), unknown)


def per_status(seg: pd.DataFrame) -> pd.DataFrame:
    """Por issue e status: horas somadas, nº de visitas e se é o status atual. Ordem do fluxo (Pendente → … → Concluída)."""
    cols = ["subtask_key", "status", "group", "hours", "visits", "current"]
    if seg.empty:
        return pd.DataFrame(columns=cols)
    g = (seg.groupby(["subtask_key", "status", "group"], sort=False)
            .agg(hours=("hours", "sum"), visits=("start", "size"), current=("current", "max"), first=("start", "min")).reset_index())
    g["_o"] = g["group"].map({x: i for i, x in enumerate(S.FLUXO + [S.BLOQUEADA])}).fillna(99)
    return g.sort_values(["subtask_key", "_o", "first"]).drop(columns=["_o", "first"])[cols].reset_index(drop=True)


def by_group(seg: pd.DataFrame, include_done: bool = False) -> pd.DataFrame:
    """Matriz issue × grupo de status (horas). Por padrão ignora o tempo DEPOIS de concluída (não é trabalho)."""
    if seg.empty:
        return pd.DataFrame()
    s = seg if include_done else seg[seg["group"] != S.CONCLUIDA]
    if s.empty:
        return pd.DataFrame()
    m = s.pivot_table(index="subtask_key", columns="group", values="hours", aggfunc="sum", fill_value=0.0)
    return m[[g for g in S.FLUXO + [S.BLOQUEADA] if g in m.columns]]


def current_status_hours(seg: pd.DataFrame) -> dict[str, float]:
    """Tempo no status ATUAL (agora − entrada) por issue."""
    return seg[seg["current"]].groupby("subtask_key")["hours"].sum().to_dict() if not seg.empty else {}
