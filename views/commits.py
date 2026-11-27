"""Tela de rastreabilidade dos commits, branches e Pull Requests do GitHub."""
from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import plotly.express as px
import streamlit as st

import ui_components as ui
from domain import timeutil
from domain.people import nome_exibicao
from ui_components import C
from views.context import PageContext


def render(
    context: PageContext,
    *,
    summarize_git: Callable[[pd.DataFrame], pd.DataFrame],
) -> None:
    """Renderiza a visão Git usando somente o contexto explícito da página."""
    commits = context.scoped_commits
    branches = context.scoped_branches
    prs = context.scoped_prs
    items = context.scoped_items
    loaded = context.loaded
    settings = context.settings

    for message in loaded.github.messages:
        st.warning(message)
    if commits.empty and branches.empty and prs.empty:
        if loaded.github.result is None:
            st.info("Sem dados do GitHub — veja o erro acima.")
        else:
            st.info("Nenhum commit no contexto atual (sprint/histórias/desenvolvedor). Ajuste os filtros na barra lateral.")
        return
    st.caption(f"Janela do GitHub: últimos {settings.github.lookback_days} dias (config.json → github.lookback_days). "
               "'Entregue' = SHA na main, cópia equivalente na main (rebase) **ou** commit de PR merged (Squash and Merge).")
    f = st.columns(6)
    repos = f[0].multiselect("Repositório", sorted(commits["repo"].unique()))
    selected_branches = f[1].multiselect("Branch", sorted({branch for values in commits["branches"] for branch in values}))
    authors = f[2].multiselect("Autor", sorted(commits["author"].dropna().unique(), key=nome_exibicao),
                               format_func=nome_exibicao, key="commits_autor_filter")
    situation = f[3].selectbox("Situação", ["Todos", "Entregues (main ou PR merged)", "Em branch (não entregues)"])
    jira_link = f[4].selectbox("Vínculo Jira", ["Todos", "Com vínculo", "Sem vínculo"])
    kind = f[5].selectbox("Tipo", ["Humanos", "Todos", "Bots", "Merges"])
    filtered = commits
    if repos:
        filtered = filtered[filtered["repo"].isin(repos)]
    if selected_branches:
        filtered = filtered[filtered["branches"].map(lambda values: any(branch in values for branch in selected_branches))]
    if authors:
        filtered = filtered[filtered["author"].isin(authors)]
    if situation.startswith("Entregues"):
        filtered = filtered[filtered["delivered"]]
    if situation.startswith("Em branch"):
        filtered = filtered[~filtered["delivered"]]
    if jira_link == "Com vínculo":
        filtered = filtered[filtered["link_source"].notna()]
    if jira_link == "Sem vínculo":
        filtered = filtered[filtered["link_source"].isna()]
    filtered = filtered[{
        "Humanos": filtered["kind"] == "human",
        "Bots": filtered["kind"] == "bot",
        "Merges": filtered["kind"] == "merge",
    }.get(kind, filtered["kind"].notna())] if not filtered.empty else filtered

    kpis = st.columns(5)
    active_branches = branches[(~branches["is_default"]) & (branches["pending_commits"] > 0)] if not branches.empty else branches
    invalid_messages = int((filtered["valid_message"] == False).sum()) if not filtered.empty else 0  # noqa: E712
    for column, (title, value, color, icon) in zip(
        kpis,
        [
            ("Commits", len(filtered), C["blue"], "⌥"),
            ("Entregues", int(filtered["delivered"].sum()) if len(filtered) else 0, C["green"], "✅"),
            ("Em branches", int((~filtered["delivered"]).sum()) if len(filtered) else 0, C["purple"], "🌿"),
            ("Sem vínculo Jira", int(filtered["link_source"].isna().sum()) if len(filtered) else 0, C["red"], "?"),
            ("Branches com trabalho pendente", len(active_branches), C["blue"], "⑂"),
        ],
        strict=True,
    ):
        column.markdown(ui.kpi(title, value, "no filtro atual", color, icon), unsafe_allow_html=True)
    if invalid_messages:
        st.warning(f"{invalid_messages} commit(s) fora da regra da equipe (sem chave do Jira na mensagem). "
                   "Use `feat(JH-101): descrição real da alteração`.")

    commits_tab, branches_tab, prs_tab, tasks_tab = st.tabs(["Commits", "Branches", "Pull Requests", "Por task (Jira ↔ GitHub)"])
    with commits_tab:
        st.caption("Commits por dia (data local, America/Sao_Paulo), separando o que já foi entregue do que está só em branch.")
        if filtered.empty:
            st.caption("Nenhum commit com estes filtros.")
        else:
            grouped = (
                filtered.assign(dia=timeutil.local_dates(filtered["date"]),
                                Local=filtered["delivered"].map({True: "entregue", False: "branch"}))
                .groupby(["dia", "Local"]).size().reset_index(name="commits")
            )
            fig = px.bar(
                grouped,
                x="dia",
                y="commits",
                color="Local",
                color_discrete_map={"entregue": C["green"], "branch": C["purple"]},
                labels={"dia": "Data", "commits": "Commits", "Local": "Situação"},
            )
            fig.update_traces(hovertemplate="%{x|%d/%m/%Y} — %{fullData.name}: %{y} commit(s)<extra></extra>")
            st.plotly_chart(ui.style_fig(fig, 200), use_container_width=True)
            visible = filtered.assign(
                Branches=filtered["branches"].map(", ".join),
                Situação=filtered["delivered_via"].map({
                    "main": "✅ main",
                    "main_equivalente": "✅ main (SHA equivalente)",
                    "pr": "✅ PR merged",
                }).fillna("🌿 branch"),
                Autor=filtered["author"].map(nome_exibicao),
                PRs=filtered["pr_numbers"].map(lambda values: ", ".join(f"#{number}" for number in values)),
            )
            st.dataframe(
                visible[["date", "repo", "url", "title", "Autor", "jira_key", "ref_jira_key", "us_id", "link_source",
                         "Branches", "PRs", "Situação", "kind"]],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "date": st.column_config.DatetimeColumn("Data", format="DD/MM/YY HH:mm"),
                    "url": st.column_config.LinkColumn("Commit", display_text=r"commit/(.{7})"),
                    "title": "Mensagem",
                    "jira_key": "Chave Jira (mensagem)",
                    "ref_jira_key": "Chave da Story (PR/branch)",
                    "us_id": "User Story",
                    "link_source": "Vínculo via",
                    "repo": "Repo",
                    "kind": "Tipo",
                },
            )
    with branches_tab:
        st.caption("'Pendentes' = commits que só existem nessa branch e ainda não foram entregues (uma branch já mergeada via PR não conta).")
        visible_branches = branches[~branches["is_default"]] if not branches.empty else branches
        if repos and not visible_branches.empty:
            visible_branches = visible_branches[visible_branches["repo"].isin(repos)]
        if visible_branches.empty:
            st.caption("Nenhuma branch no contexto atual.")
        else:
            branch_table = visible_branches.assign(**{"Último autor": visible_branches["last_author"].map(nome_exibicao)})
            branch_table = branch_table.drop(columns=["last_author", "is_default", "head_sha", "pr_numbers"])
            branch_table = branch_table[["jira_key", "us_id"] + [
                column for column in branch_table.columns if column not in ("jira_key", "us_id")
            ]]  # chave oficial primeiro
            st.dataframe(
                branch_table.sort_values("pending_commits", ascending=False),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "last_commit": st.column_config.DatetimeColumn("Último commit", format="DD/MM/YY HH:mm"),
                    "pending_commits": "Commits pendentes",
                    "ahead_main": "À frente da main",
                    "behind_main": "Atrás da main",
                    "delivered": "Entregue",
                    "kind": "Lado",
                    "us_id": "User Story",
                    "jira_key": "Chave Jira",
                    "follows_convention": "Segue convenção",
                    "pr": "PR",
                    "pr_state": "Estado do PR",
                    "compare_status": "Compare",
                },
            )
    with prs_tab:
        if prs.empty:
            st.caption("Nenhuma PR no contexto atual.")
        else:
            pr_table = prs.assign(Autor=prs["author"].map(nome_exibicao))[[
                "number", "title", "Autor", "state", "kind", "head", "base", "created", "merged_at", "merge_method",
                "jira_key", "us_id", "follows_convention", "url",
            ]]
            st.dataframe(
                pr_table,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "url": st.column_config.LinkColumn("Link", display_text="abrir"),
                    "number": "PR",
                    "title": "Título",
                    "state": "Estado",
                    "kind": "Lado",
                    "head": "Branch",
                    "base": "Base",
                    "merge_method": "Merge",
                    "us_id": "User Story",
                    "jira_key": "Chave Jira",
                    "follows_convention": "Título segue convenção",
                    "created": st.column_config.DatetimeColumn("Criado", format="DD/MM/YY HH:mm"),
                    "merged_at": st.column_config.DatetimeColumn("Mergeado", format="DD/MM/YY HH:mm"),
                },
            )
    with tasks_tab:
        all_tasks = summarize_git(items).drop(columns="subtask_key")
        st.caption("Alertas mostram divergências entre o que o Jira diz e o que o GitHub tem. "
                   "'Possível inconsistência' = não há evidência suficiente para afirmar que algo está errado.")
        st.dataframe(all_tasks.sort_values("Alerta", ascending=False), hide_index=True, use_container_width=True)
