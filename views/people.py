"""Página Pessoas: acompanhar o TRABALHO. Sem ranking, sem score, sem ordenação por volume (ordem alfabética)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from domain import alerts as A
from domain import statuses as S
from domain.fmt import NA, fmt_duration, fmt_hours, fmt_points
from domain.linking import display_id
from domain.people import nome_exibicao
from services.mgmt import Mgmt
from ui_components import C, style_fig
from views import common as V
from views.now import alerts_frame

ALL = "(visão geral do time)"


def _overview(m: Mgmt) -> pd.DataFrame:
    p = m.people
    return pd.DataFrame({
        "Pessoa": p["name"], "Tarefas": p["tasks"], **{g: p[g] for g in (S.ANDAMENTO, S.ANALISE, S.TESTE, S.BLOQUEADA, S.CONCLUIDA)},
        "Estimado nas tasks": p["estimate_h"].map(fmt_hours), "Registrado nas tasks dela": p["logged_on_tasks_h"].map(fmt_hours),
        "Lançado por ela": p["logged_by_person_h"].map(fmt_hours), "Stories": p["stories"],
        "SP das Stories em que atua": p["story_points_related"].map(fmt_points),
        "Commits": p["commits"], "Branches": p["branches"], "PRs": p["prs"]})


def render(m: Mgmt, domain: str) -> None:
    st.caption("🧭 Esta página serve para **acompanhar o trabalho**, não para comparar pessoas. A tabela está em ordem alfabética e "
               "commits, horas e pontos **não medem valor individual**. Respeita os filtros de Sprint e Stories.")
    for note in [*m.notes, *m.alert_notes]:
        st.warning(note)
    if m.people.empty:
        st.info("Nenhuma pessoa com tasks ou worklogs no recorte atual.")
        return
    st.dataframe(_overview(m), hide_index=True, use_container_width=True)
    st.caption("Estimado/Registrado nas tasks dela = soma do Jira nas tasks atribuídas a ela (qualquer um pode ter lançado as horas). "
               "'Lançado por ela' = horas que ela registrou em qualquer task da Sprint. SP = pontos das Stories em que ela tem subtask "
               "(uma Story compartilhada conta para cada participante: é contexto, não pontuação individual).")
    fixed = m.ctx.dev
    options = list(m.people["person"])
    pick = st.selectbox("Pessoa", [ALL] + options, index=(options.index(fixed) + 1) if fixed in options else 0, disabled=bool(fixed),
                        format_func=lambda x: x if x == ALL else nome_exibicao(x), key=f"people_pick_{fixed}")
    if fixed:
        st.caption("Filtro global de Desenvolvedor ativo: a página já está no contexto dessa pessoa.")
    if pick == ALL:
        return
    _person(m, pick, domain)


def _person(m: Mgmt, who: str, domain: str) -> None:
    items = m.items_team[m.items_team["assignee"] == who]
    st.markdown(f"### 👤 {nome_exibicao(who)}")
    if m.ctx.sprint:
        st.caption(f"Contexto: {nome_exibicao(who)} · {m.ctx.sprint}. Nada de outras Sprints entra aqui.")
    wl = m.team.worklogs[m.team.worklogs["author"] == who] if not m.team.worklogs.empty else m.team.worklogs
    cm = m.team.commits[(m.team.commits["author"] == who) & (m.team.commits["kind"] == "human")] if not m.team.commits.empty else m.team.commits
    br = m.team.branches[(m.team.branches["last_author"] == who) & ~m.team.branches["is_default"]] if not m.team.branches.empty else m.team.branches
    prs = m.team.prs[m.team.prs["author"] == who] if not m.team.prs.empty else m.team.prs
    t_tasks, t_stories, t_hours, t_commits, t_branches, t_prs, t_alerts = st.tabs(
        ["Tarefas", "Stories", "Horas", "Commits", "Branches", "PRs", "Alertas"])
    with t_tasks:
        if items.empty:
            st.info("Sem tarefas atribuídas neste contexto.")
        else:
            sp = dict(zip(m.team.stories["story_key"], m.team.stories["story_points"], strict=True))
            st.dataframe(pd.DataFrame({
                "Jira": [V.jira_url(domain, k) for k in items["subtask_key"]], "Resumo": items["subtask_summary"],
                "Story": [display_id(k, u) for k, u in zip(items["story_key"], items["us_id"], strict=True)],
                "Status": items["status_name"], "Estimado": items["estimate_h"].map(fmt_hours), "Registrado": items["logged_h"].map(fmt_hours),
                "Restante": [V.remaining_label(h, s) for h, s in zip(items["remaining_eff_h"], items["remaining_source"], strict=True)],
                "SP da Story": [fmt_points(sp.get(k)) for k in items["story_key"]],
                "Prazo / situação": [V.due_label(d, s) for d, s in zip(items["due_date"], items["due_status"], strict=True)],
                "Atividade": items.apply(V.activity_label, axis=1), "Bloqueio": items.apply(V.block_label, axis=1),
                "Commits (chave da task)": items["n_commits"]}), hide_index=True, use_container_width=True, column_config={"Jira": V.jira_col()})
    with t_stories:
        keys = sorted(set(items["story_key"]))
        s = m.stories_team[m.stories_team["story_key"].isin(keys)]
        if s.empty:
            st.info("Sem Stories neste contexto.")
        else:
            mine = items.groupby("story_key").size().to_dict()
            st.dataframe(pd.DataFrame({
                "Jira": [V.jira_url(domain, k) for k in s["story_key"]], "US": s["us_id"].fillna(NA), "Título": s["story_summary"],
                "Status (Jira)": s["status_name"].fillna(NA), "SP": s["story_points"].map(fmt_points),
                "Subtasks dela / total": [f"{mine.get(k, 0)}/{t}" for k, t in zip(s["story_key"], s["subtasks_total"], strict=True)],
                "Prazo / situação": [V.due_label(d, st_, src) for d, st_, src in zip(s["due_date"], s["due_status"], s["due_source"], strict=True)]}),
                hide_index=True, use_container_width=True, column_config={"Jira": V.jira_col()})
    with t_hours:
        if wl.empty:
            st.info("Nenhuma hora registrada por esta pessoa no contexto.")
        else:
            titles = dict(zip(m.team.items["subtask_key"], m.team.items["subtask_summary"], strict=True))
            st.metric("Horas lançadas por ela", fmt_hours(wl["time_spent_h"].sum()))
            daily = wl.groupby("date")["time_spent_h"].sum().reset_index()
            fig = go.Figure(go.Bar(x=daily["date"], y=daily["time_spent_h"], marker_color=C["blue"], hovertemplate="%{y:.1f}h em %{x|%d/%m}<extra></extra>"))
            fig.update_yaxes(title="Horas")
            st.plotly_chart(style_fig(fig, 220), use_container_width=True)
            st.dataframe(pd.DataFrame({"Data": wl["date"].dt.strftime("%d/%m/%Y"), "Task": wl["subtask_key"].map(lambda k: f"{k} · {titles.get(k, '')}"),
                                       "Horas": wl["time_spent_h"].map(fmt_hours)}).iloc[::-1], hide_index=True, use_container_width=True)
    with t_commits:
        if cm.empty:
            st.info("Nenhum commit no contexto.")
        else:
            st.dataframe(pd.DataFrame({"Data": cm["date"].dt.strftime("%d/%m %H:%M"), "Repo": cm["repo"], "Branch": cm["branch_label"],
                                       "Task": cm["jira_key"].fillna("(sem chave)"), "Título": cm["title"], "Entregue": cm["delivered"].map({True: "✅", False: "🌿"}),
                                       "Link": cm["url"]}).iloc[::-1], hide_index=True, use_container_width=True,
                         column_config={"Link": st.column_config.LinkColumn("Link", display_text="abrir")})
    with t_branches:
        if br.empty:
            st.info("Nenhuma branch com último commit desta pessoa no contexto.")
        else:
            st.dataframe(pd.DataFrame({"Branch": br["branch"], "Lado": br["kind"].fillna(NA), "Story": br["jira_key"].fillna(NA),
                                       "Último commit": br["last_commit"].dt.strftime("%d/%m %H:%M"), "Pendentes de merge": br["pending_commits"],
                                       "PR": br["pr_state"].fillna("sem PR")}), hide_index=True, use_container_width=True)
    with t_prs:
        if prs.empty:
            st.info("Nenhuma PR desta pessoa no contexto.")
        else:
            st.dataframe(pd.DataFrame({"PR": prs["url"], "Título": prs["title"], "Estado": prs["state"],
                                       "Revisão": prs["review_state"].map(lambda r: V.REVIEW_LABEL.get(r, str(r))),
                                       "Aberta há": [fmt_duration((m.now - c).total_seconds() / 3600) for c in prs["created"]]}),
                         hide_index=True, use_container_width=True,
                         column_config={"PR": st.column_config.LinkColumn("PR", display_text=r"/pull/(\d+)$")})
    with t_alerts:
        a = A.for_person(m.alerts_team, who)
        if a.empty:
            st.success("Nenhum alerta ligado a esta pessoa.")
        else:
            st.dataframe(alerts_frame(a, domain), hide_index=True, use_container_width=True,
                         column_config={"Jira": V.jira_col(), "GitHub": st.column_config.LinkColumn("GitHub", display_text=r"github\.com/(.+)$")})
