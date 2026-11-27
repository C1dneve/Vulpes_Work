"""Página Relatórios, renderizada a partir de um contexto explícito."""
from __future__ import annotations

from collections.abc import Callable

import plotly.express as px
import streamlit as st

import ui_components as ui
from domain import statuses as S
from domain.people import nome_exibicao
from ui_components import STATUS_COR, C
from views.context import PageContext

DevSelected = Callable[[object], None]


def render(context: PageContext, *, on_dev_selected: DevSelected) -> None:
    """Renderiza relatórios de trabalho usando os dados já filtrados pelo app."""
    a, b = st.columns(2)
    concl = context.scoped_items[context.scoped_items["status_group"] == S.CONCLUIDA]
    with a, st.container(border=True):
        st.markdown("#### ⏱️ Média de horas por tag (concluídas)")
        st.caption("Média de horas registradas em worklog por tag, só entre as tasks já concluídas.")
        if concl.empty:
            st.caption("Ainda não há tarefas concluídas.")
        else:
            pct_sem_tag = (concl["label"] == "Sem Tag").mean()
            if pct_sem_tag > 0.7:
                st.warning(f"⚠️ {pct_sem_tag:.0%} das tarefas concluídas estão sem tag no Jira — "
                           "esse gráfico fica pouco útil assim. Vale o time começar a rotular as issues.")
            m = concl.groupby("label")["time_spent_h"].mean().reset_index().sort_values("time_spent_h", ascending=False)
            fig = px.bar(m, x="label", y="time_spent_h", text_auto=".1f", color_discrete_sequence=[C["primary"]],
                         labels={"label": "Tag", "time_spent_h": "Horas (média)"})
            fig.update_traces(hovertemplate="Tag %{x}: %{y:.1f}h em média<extra></extra>")
            st.plotly_chart(ui.style_fig(fig, 280), use_container_width=True)
    with b, st.container(border=True):
        st.markdown("#### ✅ Entregas por desenvolvedor")
        st.caption("Quantas tasks do contexto cada pessoa tem, por status. Clique numa barra para ver os detalhes da pessoa.")
        e = context.scoped_items.assign(Dev=context.scoped_items["assignee"].map(nome_exibicao)).groupby(["Dev", "assignee", "status_group"]).size().reset_index(name="tasks")
        fig = px.bar(e, x="Dev", y="tasks", color="status_group", color_discrete_map=STATUS_COR,
                     category_orders={"status_group": list(STATUS_COR)}, custom_data=["assignee"],
                     labels={"Dev": "Desenvolvedor", "tasks": "Tasks", "status_group": "Status"})
        fig.update_traces(hovertemplate="%{x} — %{fullData.name}: %{y} task(s)<extra></extra>")
        evento = st.plotly_chart(ui.style_fig(fig, 280), use_container_width=True, on_select="rerun", key="chart_entregas_dev")
        on_dev_selected(evento)
    c, d = st.columns(2)
    with c, st.container(border=True):
        st.markdown("#### 🕓 Esforço diário (worklogs)")
        st.caption("Horas lançadas em worklog por dia (data local). Clique num ponto para ver os detalhes da pessoa.")
        w = context.scoped_worklogs   # já respeita sprint, histórias e desenvolvedor
        if w.empty:
            st.caption("Sem worklogs registrados neste contexto.")
        else:
            w = w.groupby(["date", "author"])["time_spent_h"].sum().reset_index()
            w["Dev"] = w["author"].map(nome_exibicao)
            fig = px.line(w, x="date", y="time_spent_h", color="Dev", markers=True, custom_data=["author"],
                          labels={"date": "Data", "time_spent_h": "Horas", "Dev": "Desenvolvedor"})
            fig.update_traces(hovertemplate="%{fullData.name}: %{y:.1f}h em %{x|%d/%m/%Y}<extra></extra>")
            evento = st.plotly_chart(ui.style_fig(fig, 280), use_container_width=True, on_select="rerun", key="chart_esforco_diario")
            on_dev_selected(evento)
    with d, st.container(border=True):
        st.markdown("#### ⌥ Commits por autor (entregues × em branch)")
        st.caption("Só commits humanos (bots e merges ficam de fora). Clique numa barra para ver os detalhes.")
        hum = context.scoped_commits[context.scoped_commits["kind"] == "human"] if not context.scoped_commits.empty else context.scoped_commits
        if hum.empty:
            st.caption("Sem commits humanos neste contexto.")
        else:
            g = (hum.assign(onde=hum["delivered"].map({True: "entregue", False: "branch"}), Dev=hum["author"].map(nome_exibicao))
                    .groupby(["Dev", "onde"]).agg(commits=("author", "size"), author=("author", "first")).reset_index())
            fig = px.bar(g, x="Dev", y="commits", color="onde", color_discrete_map={"entregue": C["green"], "branch": C["purple"]},
                         custom_data=["author"], labels={"Dev": "Desenvolvedor", "commits": "Commits", "onde": "Situação"})
            fig.update_traces(hovertemplate="%{x} — %{fullData.name}: %{y} commit(s)<extra></extra>")
            evento = st.plotly_chart(ui.style_fig(fig, 280), use_container_width=True, on_select="rerun", key="chart_commits_autor")
            on_dev_selected(evento)


