"""Utilitários de apresentação compartilhados pelas telas de gestão."""
from __future__ import annotations

from urllib.parse import quote

import pandas as pd
import streamlit as st

from domain import work as W
from domain.fmt import NA, fmt_duration, fmt_hours, isna
from domain.people import nome_exibicao

SEV_ICON = {"alta": "🔴", "média": "🟠", "baixa": "🟡", "info": "🔵"}
DUE_ICON = {W.DUE_LATE: "🔴", W.DUE_SOON: "🟠", W.DUE_OK: "🟢", W.DUE_DONE: "✅", W.DUE_NONE: "⚪"}
REVIEW_LABEL = {"aguardando_revisao": "aguardando revisão", "comentada": "comentada", "mudancas_solicitadas": "mudanças solicitadas",
                "aprovada": "aprovada", "mergeada": "mergeada", "fechada": "fechada (sem merge)", "rascunho": "rascunho",
                "desconhecido": "desconhecido (reviews indisponíveis)"}


def jira_url(domain: str, key: object) -> str | None:
    return None if isna(key) else f"https://{domain}/browse/{quote(str(key))}"


def jira_col(label: str = "Jira"):
    """Coluna-link para o Jira: mostra só a chave (o final da URL)."""
    return st.column_config.LinkColumn(label, display_text=r"/browse/(.+)$")


def pessoa(slug: object) -> str:
    return NA if isna(slug) or slug == "nenhum" else nome_exibicao(slug)


def due_label(due: object, status: str, source: str | None = None) -> str:
    d = W.parse_due(due)
    day = "" if pd.isna(d) else d.strftime("%d/%m")
    extra = " (das subtasks)" if source == "subtasks" else ""
    return f"{DUE_ICON.get(status, '')} {status}" + (f" · {day}{extra}" if day else "")


def remaining_label(h: object, source: object) -> str:
    return NA if isna(h) else f"{fmt_hours(h)} ({source})"


def activity_label(row: pd.Series) -> str:
    if row.get("is_done"):
        return NA
    if isna(row.get("inactive_bdays")):
        return "sem sinal de atividade"
    src = {"jira_update": "Jira", "status": "status", "worklog": "worklog", "github": "GitHub"}.get(row["last_activity_source"], "")
    quando = "hoje" if row["inactive_bdays"] == 0 else f"há {row['inactive_bdays']}d útil(eis)"
    return f"{'🟠 ' if row['is_inactive'] else ''}{quando} ({src})"


def block_label(row: pd.Series) -> str:
    if not row.get("is_blocked") or row.get("is_done"):
        return NA
    why = row["block_reason"] or "motivo não informado no Jira"
    tempo = f" · há {fmt_duration(row['blocked_hours'])}" if not isna(row.get("blocked_hours")) else ""
    return f"🔴 {why}{tempo}"


def commit_lines(cm: pd.DataFrame, limit: int = 30) -> None:
    from domain.text import md_esc
    for _, r in cm.head(limit).iterrows():
        via = f" · PR {', '.join('#' + str(n) for n in r['pr_numbers'])}" if r.get("pr_numbers") else ""
        st.markdown(f"- {'✅' if r['delivered'] else '🌿'} {r['date']:%d/%m} · **{md_esc(pessoa(r['author']))}** · "
                    f"[{md_esc(str(r['title'])[:70])}]({r['url']}){via}")
    if len(cm) > limit:
        st.caption(f"… e mais {len(cm) - limit} commit(s).")


def tz_note() -> str:
    return "Horários em America/Sao_Paulo. Durações em tempo corrido (24h/dia), não horário comercial."
