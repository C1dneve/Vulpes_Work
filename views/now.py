"""Agora: o que exige atenção neste momento (situação atual, não histórico) + todos os alertas."""
from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from domain import alerts as A
from domain.fmt import NA
from views import common as V
from views.context import PageContext

JIRA_KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
ACTIONABLE = (A.ALTA, A.MEDIA)
SECTIONS = [
    ("🔴 Bloqueadas", ["bloqueada"]), ("⏰ Atrasadas", ["atrasada"]), ("💤 Inativas", ["inativa"]),
    ("🔍 PRs que pedem ação", ["pr_aguardando_revisao", "pr_mudancas", "pr_antiga"]),
    ("🔗 Jira ↔ GitHub inconsistente", ["done_sem_github", "done_sem_pr", "pr_mergeada_jira_aberto", "analise_sem_pr", "commit_sem_jira_key"]),
    ("🏁 Sprint", ["sprint_fim"])]


def alerts_frame(a: pd.DataFrame, domain: str) -> pd.DataFrame:
    def jira(r: pd.Series) -> str | None:
        if r["entity"] in ("subtask", "story") and JIRA_KEY.match(str(r["key"])):
            return V.jira_url(domain, r["key"])
        return V.jira_url(domain, r["story_key"]) if not pd.isna(r["story_key"]) and r["entity"] != "subtask" else None
    return pd.DataFrame({
        "Sev.": [f"{V.SEV_ICON[s]} {s}" for s in a["severity"]], "Regra": a["rule"].map(lambda r: A.RULES[r][0]), "Fonte": a["source"],
        "Item": a["key"], "Título": a["title"], "Responsável(is)": a["owners"].map(lambda o: ", ".join(V.pessoa(x) for x in o) or NA),
        "Detalhe": a["detail"], "Desde": a["since"].map(lambda t: NA if pd.isna(t) else t.strftime("%d/%m %H:%M")),
        "Jira": a.apply(jira, axis=1), "GitHub": a["url"]}).reset_index(drop=True)


def _table(a: pd.DataFrame, domain: str) -> None:
    cols = {"Jira": V.jira_col(), "GitHub": st.column_config.LinkColumn("GitHub", display_text=r"github\.com/(.+)$")}
    st.dataframe(alerts_frame(a, domain), hide_index=True, use_container_width=True, column_config=cols)


def render(context: PageContext) -> None:
    management = context.management
    domain = context.settings.jira.domain

    for n in [*management.notes, *management.alert_notes]:
        st.warning(n)
    a = management.alerts
    sev = a["severity"].value_counts().to_dict() if not a.empty else {}
    c = st.columns(4)
    c[0].metric("🔴 Alta", sev.get("alta", 0), help="Exige ação hoje: bloqueada, atrasada, sprint vencida com itens abertos.")
    c[1].metric("🟠 Média", sev.get("média", 0), help="Precisa de atenção: inativa, PR sem revisão no prazo / antiga, inconsistência Jira↔GitHub.")
    c[2].metric("🟡 Baixa", sev.get("baixa", 0), help="Acompanhar.")
    c[3].metric("🔵 Info", sev.get("info", 0), help="Registro: concluída/mergeada recentemente, PR aberta sem pendência.")
    t_now, t_all = st.tabs(["⚡ Agora", "📋 Todos os alertas"])
    with t_now:
        st.caption(f"Itens de severidade alta e média, em ordem de urgência. Limiares: inatividade ≥ {management.th.inactive_business_days} dias úteis · "
                   f"PR sem revisão ≥ {management.th.pr_review_wait_hours}h · PR antiga ≥ {management.th.pr_old_days}d · prazo 'próximo' ≤ {management.th.due_soon_days}d "
                   "(configuráveis em config.json → management).")
        now = a[a["severity"].isin(ACTIONABLE)] if not a.empty else a
        if now.empty:
            st.success("✅ Nada exige atenção agora neste recorte.")
        for title, rules in SECTIONS:
            part = now[now["rule"].isin(rules)] if not now.empty else now
            if part.empty:
                continue
            with st.container(border=True):
                st.markdown(f"**{title}** · {len(part)}")
                _table(part, domain)
    with t_all:
        if a.empty:
            st.info("Nenhum alerta neste recorte.")
            return
        f1, f2, f3 = st.columns(3)
        sev_sel = f1.multiselect("Severidade", list(A.SEV_ORDER), default=list(A.SEV_ORDER), key="al_sev")
        src_sel = f2.multiselect("Fonte", ["Jira", "GitHub", "Jira↔GitHub"], default=["Jira", "GitHub", "Jira↔GitHub"], key="al_src")
        rule_sel = f3.multiselect("Regra", list(A.RULES), format_func=lambda r: A.RULES[r][0], key="al_rule")
        sel = a[a["severity"].isin(sev_sel) & a["source"].isin(src_sel)]
        if rule_sel:
            sel = sel[sel["rule"].isin(rule_sel)]
        _table(sel, domain)
