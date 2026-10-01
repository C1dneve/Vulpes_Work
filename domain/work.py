"""Regras de gestão de uma task/story (funções puras): prazo, esforço, bloqueio, inatividade, lado BE/FE.

Princípios: ausente continua ausente (`None`), nunca vira 0; valor calculado pelo Moonfoxes é sempre rotulado como tal;
`now`/`today` são parâmetros (testável e sem depender do relógio).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from domain import statuses as S
from domain.fmt import isna
from domain.thresholds import Thresholds

# ---------------------------------------------------------------- prazo
DUE_NONE, DUE_OK, DUE_SOON, DUE_LATE, DUE_DONE = "Sem due date", "No prazo", "Próximo do prazo", "Atrasado", "Concluído"


def parse_due(value: object) -> pd.Timestamp:
    """`duedate` do Jira é uma DATA ('2026-10-02'), sem hora nem fuso -> meia-noite naive (comparável com `timeutil.today()`)."""
    if isna(value) or value == "":
        return pd.NaT
    ts = pd.to_datetime(str(value)[:10], format="%Y-%m-%d", errors="coerce")
    return ts.normalize() if not pd.isna(ts) else pd.NaT


def due_status(due: object, status_group: str, today: pd.Timestamp, th: Thresholds) -> str:
    """Concluído > Sem due date > Atrasado (hoje DEPOIS do prazo) > Próximo (faltam ≤ N dias; o próprio dia conta) > No prazo."""
    if status_group == S.CONCLUIDA:
        return DUE_DONE
    d = parse_due(due)
    if pd.isna(d):
        return DUE_NONE
    left = (d - today.normalize()).days
    if left < 0:
        return DUE_LATE
    return DUE_SOON if left <= th.due_soon_days else DUE_OK


def days_to_due(due: object, today: pd.Timestamp) -> int | None:
    d = parse_due(due)
    return None if pd.isna(d) else int((d - today.normalize()).days)


# ---------------------------------------------------------------- estimativa x realizado
@dataclass(frozen=True)
class Effort:
    estimate_h: float | None        # do Jira (timeoriginalestimate)
    logged_h: float | None          # do Jira (timespent = soma dos worklogs)
    diff_h: float | None            # CALCULADO: registrado − estimado (positivo = estourou); None sem estimativa
    remaining_h: float | None
    remaining_source: str | None    # "jira" (timeestimate) | "calculado" (estimado − registrado, mín. 0) | None (sem base)


def effort(estimate_h: object, logged_h: object, remaining_h: object) -> Effort:
    est = None if isna(estimate_h) else float(estimate_h)
    log = None if isna(logged_h) else float(logged_h)
    if not isna(remaining_h):
        rem, src = float(remaining_h), "jira"
    elif est is not None:
        rem, src = max(est - (log or 0.0), 0.0), "calculado"
    else:
        rem, src = None, None       # sem estimativa e sem restante do Jira: NÃO se inventa
    return Effort(est, log, None if est is None or log is None else log - est, rem, src)


def rollup_effort(items: pd.DataFrame) -> dict:
    """Soma das Subtasks de uma Story (valor CALCULADO pelo Moonfoxes). Subtask sem estimativa não entra como 0:
    `estimate_coverage` diz quantas têm estimativa ('3/5') e a soma é None se nenhuma tiver."""
    n = len(items)
    est = items["estimate_h"].dropna() if n else pd.Series(dtype=float)
    efforts = [effort(r["estimate_h"], r["time_spent_h"], r.get("remaining_h")) for _, r in items.iterrows()]
    rem = [e.remaining_h for e in efforts if e.remaining_h is not None]
    return {"estimate_h": float(est.sum()) if len(est) else None, "estimate_coverage": f"{len(est)}/{n}",
            "logged_h": float(items["time_spent_h"].fillna(0).sum()) if n else 0.0,
            "remaining_h": float(sum(rem)) if rem else None,
            "remaining_partial": bool(rem) and len(rem) < n}


# ---------------------------------------------------------------- lado (BE/FE)
def item_side(code: object) -> str | None:
    """'BE-09' -> backend; 'FE-03' -> frontend; qualquer outro (UXDB, sem código) -> None. Usa o prefixo do `subtask_code`."""
    c = "" if isna(code) else str(code).upper()
    return "backend" if c.startswith("BE") else "frontend" if c.startswith("FE") else None


# ---------------------------------------------------------------- bloqueio
@dataclass(frozen=True)
class Block:
    is_blocked: bool
    sources: tuple[str, ...]        # "status" | "flag" | "link"
    reason: str | None              # SÓ o que o Jira comprova (issue bloqueadora aberta); senão None
    since: pd.Timestamp             # NaT quando não dá para saber
    hours: float | None             # agora − since


def block_info(item: pd.Series, changelog: pd.DataFrame, now: pd.Timestamp) -> Block:
    sources: list[str] = []
    since: list[pd.Timestamp] = []
    if item["status_group"] == S.BLOQUEADA:
        sources.append("status")
        if not changelog.empty:
            entered = changelog[changelog["to_group"] == S.BLOQUEADA]["ts"].dropna()
            if len(entered):
                since.append(entered.max())
    if bool(item.get("flagged")):
        sources.append("flag")
        if not isna(item.get("flagged_since")):
            since.append(item["flagged_since"])
    links = item.get("blocked_by")
    links = links if isinstance(links, (list, tuple)) else []
    if links:
        sources.append("link")      # o Jira não informa quando o link foi criado: sem `since` por esta fonte
    reason = "Bloqueada por " + "; ".join(links) if links else None
    t = min(since) if since else pd.NaT
    return Block(bool(sources), tuple(sources), reason, t, None if pd.isna(t) else max((now - t).total_seconds() / 3600, 0))


# ---------------------------------------------------------------- atividade / inatividade
def business_days_between(a: pd.Timestamp, b: pd.Timestamp) -> int:
    """Dias ÚTEIS (seg–sex, sem feriados) decorridos de `a` até `b` (datas locais). Sexta->segunda = 1."""
    if pd.isna(a) or pd.isna(b):
        return 0
    return max(int(np.busday_count(a.date(), b.date())), 0)


@dataclass(frozen=True)
class Activity:
    last: pd.Timestamp
    source: str | None              # "jira_update" | "status" | "worklog" | "github"
    business_days: int | None       # None = sem nenhum sinal (não dá para afirmar inatividade)
    inactive: bool


def last_activity(item: pd.Series, changelog: pd.DataFrame, worklogs: pd.DataFrame, commits: pd.DataFrame,
                  now: pd.Timestamp, th: Thresholds) -> Activity:
    """Última atividade = o sinal mais recente entre: atualização da issue, mudança de status, worklog e commit que cita a chave
    DESTA task. Sem commit NÃO significa sem atividade: a atividade do Jira conta. Só task EM ANDAMENTO pode ficar inativa."""
    cands: list[tuple[pd.Timestamp, str]] = []
    if not isna(item.get("updated")):
        cands.append((item["updated"], "jira_update"))
    if not changelog.empty and changelog["ts"].notna().any():
        cands.append((changelog["ts"].max(), "status"))
    if not worklogs.empty and worklogs["started"].notna().any():
        cands.append((worklogs["started"].max(), "worklog"))
    if not commits.empty and commits["date"].notna().any():
        cands.append((commits["date"].max(), "github"))
    if not cands:
        return Activity(pd.NaT, None, None, False)
    last, src = max(cands, key=lambda c: c[0])
    bd = business_days_between(last, now)
    return Activity(last, src, bd, item["status_group"] in S.EM_PROGRESSO and bd >= th.inactive_business_days)
