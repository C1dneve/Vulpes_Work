"""Diálogos compartilhados para detalhes de tasks e desenvolvedores."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import pandas as pd
import streamlit as st

import ui_components as ui
from domain.linking import display_id
from domain.people import nome_exibicao
from domain.text import md_esc
from services.mgmt import Mgmt
from ui_components import STATUS_COR
from views.common import due_label, remaining_label
from views.context import PageContext

StoryReferences = tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]


@dataclass(frozen=True)
class ModalContext:
    """Dependências explícitas utilizadas pelos diálogos."""

    page: PageContext
    return_counts: Mapping[str, int]
    slug_by_display_name: Mapping[str, str]
    task_commits: Callable[[pd.Series], pd.DataFrame]
    story_references: Callable[[str], StoryReferences]
    task_code: Callable[[pd.Series], str]


@st.dialog("🔍 Detalhes da task", width="large")
def modal_task(context: ModalContext, sub: pd.Series) -> None:
    page = context.page
    management: Mgmt = page.management
    task_key = sub["subtask_key"]

    st.subheader(f"{md_esc(context.task_code(sub))}: {md_esc(sub['subtask_summary'])}")
    st.caption(
        f"Jira: `{md_esc(task_key)}` · User Story: {md_esc(sub['story_summary'])} "
        f"(`{md_esc(display_id(sub['story_key'], sub['us_id']))}`)"
    )
    story_branches, story_prs, story_commits = context.story_references(sub["story_key"])
    if story_branches.empty and story_prs.empty:
        st.caption("Sem branch nem PR ligada a esta User Story (pela chave do Jira ou pelo ID visual).")
    else:
        branches = ", ".join("`" + branch.replace("`", "") + "`" for branch in story_branches["branch"]) or "—"
        prs = ", ".join(f"#{number}" for number in story_prs["number"]) or "—"
        st.caption(f"Branches da Story: {branches} · PRs da Story: {prs}")
    if context.return_counts.get(task_key, 0):
        st.warning(f"Esta task já voltou {context.return_counts[task_key]}x da Análise/Teste para Em Andamento.")

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(ui.badge(sub["status_group"]), unsafe_allow_html=True)
        st.write(f"**Dev:** {nome_exibicao(sub['assignee'])}")
        estimate = f" (estimado {sub['estimate_h']:.1f}h)" if pd.notna(sub["estimate_h"]) else ""
        st.write(f"**Esforço:** {sub['time_spent_h']:.1f}h{estimate}")
        effort = management.items_team[management.items_team["subtask_key"] == task_key]
        if not effort.empty:
            effort = effort.iloc[0]
            st.write(f"**Restante:** {remaining_label(effort['remaining_eff_h'], effort['remaining_source'])}")
            st.write(f"**Prazo:** {due_label(effort['due_date'], effort['due_status'])}")
            story = management.stories_team[management.stories_team["story_key"] == sub["story_key"]]
            points = "—" if story.empty or pd.isna(story.iloc[0]["story_points"]) else format(story.iloc[0]["story_points"], "g")
            st.write(f"**Story Points da Story:** {points}")
            if effort["is_blocked"] and not effort["is_done"]:
                st.error(f"Bloqueada: {effort['block_reason'] or 'motivo não informado no Jira'}")
        st.write(f"**Tag:** `{sub['label']}`")
        st.markdown(f"[Abrir no Jira](https://{page.settings.jira.domain}/browse/{quote(task_key)})")

    with c2:
        commits = context.task_commits(sub)
        if commits.empty:
            st.caption(f"👻 Nenhum commit cita a chave {md_esc(task_key)} na mensagem.")
        else:
            branches = sorted({branch for branch_list in commits["branches"] for branch in branch_list})
            delivered = int(commits["delivered"].sum())
            branch_labels = ", ".join("`" + branch.replace("`", "") + "`" for branch in branches)
            st.markdown(f"**{len(commits)} commits** · {delivered} entregues · branches: {branch_labels}")
            for _, commit in commits.iterrows():
                via_pr = f" · PR {', '.join('#' + str(number) for number in commit['pr_numbers'])}" if commit["pr_numbers"] else ""
                st.markdown(
                    f"- {'✅' if commit['delivered'] else '🌿'} `{commit['branch_label'].replace('`', '')}` · "
                    f"{commit['date']:%d/%m} · **{md_esc(nome_exibicao(commit['author']))}** · "
                    f"[{md_esc(commit['title'][:60])}]({commit['url']}) "
                    f"_(via {commit['link_source']}{via_pr})_"
                )
        if not story_commits.empty:
            with st.expander(f"Commits da User Story sem Subtask específica ({len(story_commits)})"):
                st.caption("Citam só a Story, a PR/branch ou o ID visual. Não provam execução de nenhuma Subtask.")
                for _, commit in story_commits.head(15).iterrows():
                    st.markdown(
                        f"- {'✅' if commit['delivered'] else '🌿'} {commit['date']:%d/%m} · "
                        f"**{md_esc(nome_exibicao(commit['author']))}** · "
                        f"[{md_esc(commit['title'][:60])}]({commit['url']})"
                    )


@st.dialog("👤 Detalhes do desenvolvedor", width="large")
def modal_dev(context: ModalContext, slug: str) -> None:
    page = context.page
    tasks = page.scoped_items[page.scoped_items["assignee"] == slug]
    counts = tasks["status_group"].value_counts()
    hours = tasks["time_spent_h"].sum()
    commits = page.scoped_commits
    human_commits = commits[commits["kind"] == "human"] if not commits.empty else commits
    person_commits = human_commits[human_commits["author"] == slug].sort_values("date", ascending=False) if not human_commits.empty else human_commits
    branches = page.scoped_branches[page.scoped_branches["last_author"] == slug] if not page.scoped_branches.empty else page.scoped_branches

    st.subheader(nome_exibicao(slug))
    st.caption("Números dentro do contexto atual dos filtros (sprint e User Stories).")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.write(f"**Total de tasks:** {len(tasks)}")
        for status in STATUS_COR:
            if counts.get(status, 0):
                st.markdown(ui.badge(status) + f" &nbsp;{counts[status]}", unsafe_allow_html=True)
        st.write(f"**Horas somadas (worklog das subtasks):** {hours:.1f}h")
        if len(branches):
            active = branches[branches["pending_commits"] > 0]
            st.write(
                f"**Branches com trabalho pendente:** {len(active)}"
                if len(active)
                else "**Sem branches com trabalho pendente no momento.**"
            )
            for _, branch in active.iterrows():
                st.markdown(f"- 🌿 `{branch['branch'].replace('`', '')}` ({md_esc(branch['repo'])})")
        if st.button("🔎 Ver tasks e commits desta pessoa em Commits", use_container_width=True):
            st.session_state["flt_dev"] = slug
            st.session_state["commits_autor_filter"] = [slug]
            st.session_state["nav_page"] = "Commits"
            st.rerun()
    with c2:
        if person_commits.empty:
            st.caption("👻 Nenhum commit humano encontrado para esta pessoa no contexto atual.")
        else:
            delivered = int(person_commits["delivered"].sum())
            st.markdown(f"**{len(person_commits)} commits** · {delivered} entregues · {len(person_commits) - delivered} em branch")
            for _, commit in person_commits.head(15).iterrows():
                st.markdown(
                    f"- {'✅' if commit['delivered'] else '🌿'} `{commit['branch_label'].replace('`', '')}` · "
                    f"{commit['date']:%d/%m} · [{md_esc(commit['title'][:60])}]({commit['url']})"
                )
            if len(person_commits) > 15:
                st.caption(f"... e mais {len(person_commits) - 15} commits.")


def dev_selected(context: ModalContext, event: Any) -> None:
    """Abre o diálogo do desenvolvedor selecionado em um gráfico."""
    if not event or not getattr(event, "selection", None) or not event.selection.points:
        return
    point = event.selection.points[0]
    slug = None
    custom_data = point.get("customdata")
    if custom_data:
        slug = custom_data[0] if isinstance(custom_data, (list, tuple)) else custom_data
    if not slug:
        slug = context.slug_by_display_name.get(point.get("x"))
    if slug:
        modal_dev(context, slug)
