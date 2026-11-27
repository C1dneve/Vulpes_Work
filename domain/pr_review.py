"""Estado de revisão de uma Pull Request, derivado dos REVIEWS reais do GitHub (funções puras).

Regras (nada é assumido):
  * só conta review SUBMETIDO (`PENDING` é rascunho do revisor) de alguém que não é o autor nem um bot;
  * o estado decisivo de cada revisor é o do seu ÚLTIMO review APROVADO / MUDANÇAS_SOLICITADAS; um review `DISMISSED`
    anula a decisão; comentário posterior não desfaz aprovação nem pedido de mudança;
  * PR aberta sem nenhum review válido = `aguardando_revisao`; se os reviews NÃO puderam ser lidos = `desconhecido`;
  * rascunho (draft) não espera revisão.
Comentários soltos da conversa da PR (issue comments) não são lidos: só reviews.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from domain import timeutil
from domain.people import is_bot

AGUARDANDO, COMENTADA, MUDANCAS, APROVADA = "aguardando_revisao", "comentada", "mudancas_solicitadas", "aprovada"
RASCUNHO, MERGEADA, FECHADA, DESCONHECIDO = "rascunho", "mergeada", "fechada", "desconhecido"
REVISADA = (COMENTADA, MUDANCAS, APROVADA)   # "PR revisada" = teve ao menos um review humano de outra pessoa
_DECISIVE = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
_SUBMITTED = _DECISIVE | {"COMMENTED"}


@dataclass(frozen=True)
class ReviewSummary:
    known: bool
    review_count: int = 0
    approvals: int = 0
    changes_requested: int = 0
    commented: int = 0            # revisores que só comentaram (sem decisão vigente)
    first_review_at: pd.Timestamp = pd.NaT
    last_review_at: pd.Timestamp = pd.NaT
    last_review_state: str | None = None


def summarize_reviews(reviews: list[dict[str, Any]] | None, author_login: str | None, bot_extra: tuple[str, ...] = ()) -> ReviewSummary:
    """`reviews=None` = não foi possível ler (falha da API) → `known=False`; `[]` = lido e sem reviews."""
    if reviews is None:
        return ReviewSummary(known=False)
    rows = []
    for r in reviews:
        state = (r.get("state") or "").upper()
        user = r.get("user") or {}
        login = user.get("login")
        if state not in _SUBMITTED or not r.get("submitted_at"):
            continue
        if login and author_login and login.lower() == author_login.lower():
            continue
        if is_bot(login, None, user.get("type"), bot_extra):
            continue
        rows.append((timeutil.parse_ts(r["submitted_at"]), login or "(usuário removido)", state))
    rows.sort(key=lambda x: x[0])
    decisive: dict[str, str | None] = {}
    commenters: set[str] = set()
    for _, who, state in rows:
        if state == "COMMENTED":
            commenters.add(who)
        else:
            decisive[who] = None if state == "DISMISSED" else state
    live = {w: s for w, s in decisive.items() if s}
    return ReviewSummary(
        known=True, review_count=len(rows),
        approvals=sum(1 for s in live.values() if s == "APPROVED"),
        changes_requested=sum(1 for s in live.values() if s == "CHANGES_REQUESTED"),
        commented=len(commenters - set(live)),
        first_review_at=rows[0][0] if rows else pd.NaT, last_review_at=rows[-1][0] if rows else pd.NaT,
        last_review_state=rows[-1][2].lower() if rows else None)


def review_state(pr_state: str, draft: bool, s: ReviewSummary) -> str:
    """`pr_state`: 'open' | 'merged' | 'closed'."""
    if pr_state == "merged":
        return MERGEADA
    if pr_state == "closed":
        return FECHADA
    if draft:
        return RASCUNHO
    if not s.known:
        return DESCONHECIDO
    if s.changes_requested:
        return MUDANCAS
    if s.approvals:
        return APROVADA
    if s.commented:
        return COMENTADA
    return AGUARDANDO
