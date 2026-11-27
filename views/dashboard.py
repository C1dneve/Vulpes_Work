"""Página Dashboard, renderizada a partir de contexto e callbacks explícitos."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_components as ui
from domain import statuses as S
from domain.linking import display_id
from domain.people import nome_exibicao
from domain.text import esc
from ui_components import STATUS_COR, C
from views.context import PageContext

SprintDates = Callable[[], tuple[pd.Timestamp | None, pd.Timestamp | None]]
DailyInterval = Callable[[], pd.DatetimeIndex]
StatusSeries = Callable[[pd.DatetimeIndex], pd.DataFrame]
TaskCode = Callable[[pd.Series], str]


def render(
    context: PageContext,
    management: Any,
    *,
    sprint: str,
    sprint_not_started: Callable[[], bool],
    sprint_dates: SprintDates,
    daily_interval: DailyInterval,
    status_series: StatusSeries,
    task_code: TaskCode,
) -> None:
    """Renderiza os KPIs e gráficos principais usando dados já preparados pelo app."""
    a, b = st.columns([1, 1.15])
    a.markdown(ui.HERO_LEFT, unsafe_allow_html=True)
    b.markdown(ui.HERO_RIGHT, unsafe_allow_html=True)
    total = len(context.scoped_items)
    n = lambda g: int((context.scoped_items["status_group"] == g).sum())
    pct = lambda x: f"{x / total:.0%} da meta" if total else "—"
    andamento = sum(n(g) for g in S.EM_PROGRESSO)
    ks = st.columns(4)
    ks[0].markdown(ui.kpi("Total de Issues", total, "no contexto selecionado", C["blue"], "◆"), unsafe_allow_html=True)
    ks[1].markdown(ui.kpi("Concluídas", n(S.CONCLUIDA), pct(n(S.CONCLUIDA)), C["green"], "✓"), unsafe_allow_html=True)
    ks[2].markdown(ui.kpi("Em Andamento", andamento, pct(andamento) + " (inclui Análise e Teste)", C["blue"], "◔"), unsafe_allow_html=True)
    ks[3].markdown(ui.kpi("Bloqueadas", n(S.BLOQUEADA), pct(n(S.BLOQUEADA)), C["red"], "!"), unsafe_allow_html=True)

    k = management.kpis
    ks2 = st.columns(4)
    _sp = "indisponível" if k["sp_planned"] is None else f"{k['sp_done']:g}/{k['sp_planned']:g}"
    _sp_sub = "Story Points concluídos/planejados" if k["sp_planned"] is not None else "campo ausente ou sem valores no Jira"
    ks2[0].markdown(ui.kpi("Story Points", _sp, _sp_sub + (f" · {k['sp_missing']} Story(ies) sem pontos" if k["sp_planned"] is not None and k["sp_missing"] else ""), C["purple"], "★"), unsafe_allow_html=True)
    _est = "—" if k["estimate_h"] is None else f"{k['estimate_h']:.0f}h"
    ks2[1].markdown(ui.kpi("Estimado × Registrado", f"{_est} / {k['logged_h']:.0f}h", f"estimativa em {k['estimate_items']} de {k['items']} tasks", C["blue"], "⏱"), unsafe_allow_html=True)
    ks2[2].markdown(ui.kpi("Atrasadas", k["late"], "due date vencido, não concluídas", C["red"], "⏰"), unsafe_allow_html=True)
    ks2[3].markdown(ui.kpi("Inativas", k["inactive"], f"em andamento sem atividade ≥ {context.settings.management.inactive_business_days} dias úteis", C["gray"], "💤"), unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2.1, 1.25, 1.05])
    with c1, st.container(border=True):
        st.markdown("#### 📈 Progresso da Sprint")
        st.caption("Quantas issues do contexto estavam em cada status a cada dia, reconstruído pelo histórico do Jira.")
        if sprint_not_started():
            ini, _ = sprint_dates()
            st.warning(f"⚠️ Segundo as datas do Jira, esta sprint só começa em {ini:%d/%m/%Y} — "
                       "confira se as datas da sprint no board estão corretas.")
        serie = status_series(daily_interval())
        fig = go.Figure()
        for col, cor in [(S.CONCLUIDA, C["green"]), ("Andamento (total)", C["blue"]), (S.BLOQUEADA, C["red"])]:
            fig.add_trace(go.Scatter(x=serie["data"], y=serie[col], name="Em Andamento" if col.startswith("Andamento") else col,
                                     mode="lines+markers", line=dict(color=cor, width=2.5),
                                     fill="tozeroy", fillcolor=ui.rgba(cor, .12)))
        fig.update_xaxes(title="Data")
        fig.update_yaxes(title="Nº de issues")
        fig.update_traces(hovertemplate="%{y} issue(s) em %{fullData.name} — %{x|%d/%m/%Y}<extra></extra>")
        st.plotly_chart(ui.style_fig(fig, 280), use_container_width=True)
    with c2, st.container(border=True):
        st.markdown("#### 🕒 Distribuição por Status")
        st.caption("Como as issues do contexto selecionado estão distribuídas entre os status.")
        ordem = list(STATUS_COR)
        fig = go.Figure(go.Pie(labels=ordem, values=[n(g) for g in ordem], hole=.72, sort=False, textinfo="none",
                               marker=dict(colors=[STATUS_COR[g] for g in ordem], line=dict(color=C["panel"], width=2))))
        fig.add_annotation(text=f"<b>{total}</b><br>issues", showarrow=False, font=dict(size=20, color=C["text"]))
        fig.update_traces(hovertemplate="%{label}: %{value} issue(s)<extra></extra>")
        fig = ui.style_fig(fig, 280)
        fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1, y=.5, xanchor="left"), margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with c3, st.container(border=True):
        st.markdown("#### 🗓️ Resumo da Sprint")
        ini, fim = sprint_dates()
        datas = f"{ini:%d/%m/%Y} → {fim:%d/%m/%Y}" if ini is not None and fim is not None else "sem datas no Jira"
        st.markdown(f"**{esc(sprint)}**<br><span class='mf-muted'>{esc(datas)}</span>", unsafe_allow_html=True)
        st.markdown(ui.bar("Concluídas", n(S.CONCLUIDA), total, C["green"]) + ui.bar("Em andamento", andamento, total, C["blue"])
                    + ui.bar("Bloqueadas", n(S.BLOQUEADA), total, C["red"]), unsafe_allow_html=True)

    d1, d2, d3 = st.columns([1.4, 1.5, .9])
    with d1, st.container(border=True):
        st.markdown("#### 🧾 Últimas Issues")
        ult = context.scoped_items.sort_values("updated", ascending=False).head(5)
        st.markdown("".join(ui.row((ui.chip(task_code(t)), ""), (t["subtask_summary"], "t"), (ui.badge(t["status_group"]), ""),
                                   (nome_exibicao(t["assignee"]), "m"), (ui.ago(t["updated"]), "m")) for _, t in ult.iterrows()) or "—",
                    unsafe_allow_html=True)
    with d2, st.container(border=True):
        st.markdown("#### ⌥ Últimos Commits (todas as branches)")
        hum = context.scoped_commits[context.scoped_commits["kind"] == "human"] if not context.scoped_commits.empty else context.scoped_commits
        st.markdown("".join(ui.row((ui.chip(display_id(t["jira_key"] or t["ref_jira_key"], t["us_id"]) or "sem ID"), ""), (t["title"], "t"),
                                   (ui.chip(("✅ " if t["delivered"] else "🌿 ") + t["branch_label"]), ""),
                                   (nome_exibicao(t["author"]), "m"), (f"{t['sha'][:7]} · {ui.ago(t['date'])}", "m"))
                            for _, t in hum.head(5).iterrows()) or "Nenhum commit no contexto atual.", unsafe_allow_html=True)
    with d3:
        with st.container(border=True):
            st.markdown("#### 🐙 Repositórios")
            org = context.settings.github.org
            st.markdown("".join(f'<a class="mf-link" href="https://github.com/{quote(org)}/{quote(r)}" target="_blank" rel="noopener">'
                                f'{esc(org)}/{esc(r)} ↗</a>' for r in context.settings.github.repos), unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("#### ⚡ Atalhos")
            st.markdown(f'<a class="mf-link" href="https://{quote(context.settings.jira.domain)}/secure/RapidBoard.jspa?rapidView={quote(context.settings.jira.board_id)}" target="_blank" rel="noopener">◆ Ver no Jira ↗</a>'
                        f'<a class="mf-link" href="https://github.com/{quote(org)}" target="_blank" rel="noopener">⌥ Ver no GitHub ↗</a>', unsafe_allow_html=True)


