"""Visão da Sprint: Stories (→ Subtasks → Commits; Branch; PR), Burnup e Tempo em status."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from domain import statuses as S
from domain import time_in_status as TIS
from domain.fmt import NA, fmt_duration, fmt_hours, fmt_points
from domain.linking import branches_for_story, commits_for_item, display_id, prs_for_story, story_level_commits
from domain.text import md_esc
from services.mgmt import Mgmt
from ui_components import C, style_fig
from views import common as V


def _kpis(m: Mgmt) -> None:
    k = m.kpis
    c = st.columns(6)
    c[0].metric("Stories", f"{k['stories_done']}/{k['stories']}", help="Concluídas / total, pelo status da própria Story no Jira.")
    if k["sp_planned"] is None:
        c[1].metric("Story Points", "indisponível", help="Nenhuma Story do recorte tem Story Points no Jira (ou o campo não foi encontrado).")
    else:
        c[1].metric("Story Points", f"{fmt_points(k['sp_done'])}/{fmt_points(k['sp_planned'])}",
                    help=f"Concluídos / planejados. {k['sp_missing']} Story(ies) sem pontos ficam FORA da soma (não contam como 0).")
    c[2].metric("Estimado", fmt_hours(k["estimate_h"]),
                help=f"Soma das subtasks que têm estimativa ({k['estimate_items']} de {k['items']}); as sem estimativa não entram como 0.")
    c[3].metric("Registrado", fmt_hours(k["logged_h"]), help="Tempo registrado no Jira (worklogs) nas tasks do recorte.")
    c[4].metric("Atrasadas", k["late"], help="Tasks abertas com due date vencido.")
    c[5].metric("Bloqueadas", k["blocked"], help=f"Inativas (sem atividade ≥ {m.th.inactive_business_days} dias úteis): {k['inactive']}")
    if k["sp_planned"] is not None and k["sp_missing"]:
        st.caption(f"⚠️ {k['sp_missing']} Story(ies) sem Story Points no Jira: indisponíveis, não contadas como 0.")


def _stories_frame(m: Mgmt, domain: str) -> pd.DataFrame:
    s = m.stories.sort_values(["us_id", "story_key"], na_position="last")
    return pd.DataFrame({
        "Jira": [V.jira_url(domain, k) for k in s["story_key"]],
        "US": s["us_id"].fillna(NA), "Título": s["story_summary"],
        "Responsável": s["responsavel"].map(V.pessoa),
        "Time": s["team"].map(lambda t: ", ".join(V.pessoa(x) for x in t) or NA),
        "Status (Jira)": s["status_name"].fillna(NA),
        "Subtasks": [f"{d}/{t}" for d, t in zip(s["subtasks_done"], s["subtasks_total"], strict=True)],
        "SP": s["story_points"].map(fmt_points),
        "Estimado": [NA if pd.isna(h) else f"{fmt_hours(h)} ({c})" for h, c in zip(s["estimate_h"], s["estimate_coverage"], strict=True)],
        "Registrado": s["logged_h"].map(fmt_hours),
        "Prazo / situação": [V.due_label(d, st_, src) for d, st_, src in zip(s["due_date"], s["due_status"], s["due_source"], strict=True)],
        "Bloq/Atras/Inat": [f"{b}/{a}/{i}" for b, a, i in zip(s["n_blocked"], s["n_late"], s["n_inactive"], strict=True)],
        "Branches": s["n_branches"], "PRs": s["n_prs"], "Commits": s["n_commits"], "Revisão das PRs": s["pr_states"].replace("", NA),
    }).reset_index(drop=True)


def _subtasks_frame(kids: pd.DataFrame, domain: str) -> pd.DataFrame:
    return pd.DataFrame({
        "Jira": [V.jira_url(domain, k) for k in kids["subtask_key"]], "Cód.": kids["subtask_code"].fillna(NA),
        "Resumo": kids["subtask_summary"], "Responsável": kids["assignee"].map(V.pessoa), "Status": kids["status_name"],
        "Estimado": kids["estimate_h"].map(fmt_hours), "Registrado": kids["logged_h"].map(fmt_hours),
        "Restante": [V.remaining_label(h, s) for h, s in zip(kids["remaining_eff_h"], kids["remaining_source"], strict=True)],
        "Prazo / situação": [V.due_label(d, s) for d, s in zip(kids["due_date"], kids["due_status"], strict=True)],
        "Atividade": kids.apply(V.activity_label, axis=1), "Bloqueio": kids.apply(V.block_label, axis=1),
        "Commits": kids["n_commits"]})


def _story_detail(m: Mgmt, sk: str, domain: str) -> None:
    s = m.stories[m.stories["story_key"] == sk].iloc[0]
    us = s["us_id"] if not pd.isna(s["us_id"]) else None
    all_kids = set(m.items_team.loc[m.items_team["story_key"] == sk, "subtask_key"])
    kids = m.items[m.items["story_key"] == sk]
    st.markdown(f"##### 📖 {md_esc(display_id(sk, us))} — {md_esc(s['story_summary'])}")
    st.caption(f"Epic: {md_esc(str(s['epic_summary'] or NA))} · Status no Jira: {s['status_name'] or NA} · Pontos: {fmt_points(s['story_points'])}"
               f" · Estimado: soma das subtasks (cobertura {s['estimate_coverage']}) · valor CALCULADO pelo Moonfoxes, não pelo Jira.")
    st.markdown("**├── Subtasks** (cada commit só aparece na Subtask cuja chave ele cita)")
    st.dataframe(_subtasks_frame(kids, domain), hide_index=True, use_container_width=True, column_config={"Jira": V.jira_col()})
    for _, t in kids.iterrows():
        cm = commits_for_item(m.team.commits, t, m.known_keys) if not m.team.commits.empty else m.team.commits
        cm = cm[cm["kind"] == "human"] if not cm.empty else cm
        if not cm.empty:
            with st.expander(f"└── Commits de {t['subtask_key']} · {md_esc(str(t['subtask_summary'])[:60])} ({len(cm)})"):
                V.commit_lines(cm)
    sl = story_level_commits(m.team.commits[m.team.commits["kind"] == "human"] if not m.team.commits.empty else m.team.commits,
                             sk, us, all_kids, m.known_keys)
    if not sl.empty:
        with st.expander(f"Commits só da Story, sem Subtask específica ({len(sl)})"):
            st.caption("Citam só a Story, a PR/branch ou o ID visual. Não provam a execução de nenhuma Subtask.")
            V.commit_lines(sl, 15)
    br = branches_for_story(m.team.branches, sk, us, all_kids, m.known_keys)
    st.markdown(f"**├── Branches** ({len(br)})")
    if br.empty:
        st.caption("Nenhuma branch ligada a esta Story (pela chave do Jira ou pelo ID visual).")
    else:
        st.dataframe(pd.DataFrame({"Branch": br["branch"], "Lado": br["kind"].fillna(NA), "Autor": br["last_author"].map(V.pessoa),
                                   "Último commit": br["last_commit"].dt.strftime("%d/%m %H:%M"),
                                   "Pendentes de merge": br["pending_commits"], "PR": br["pr_state"].fillna("sem PR")}),
                     hide_index=True, use_container_width=True)
    prs = prs_for_story(m.team.prs, sk, us, all_kids, m.known_keys)
    st.markdown(f"**└── Pull Requests** ({len(prs)})")
    if prs.empty:
        st.caption("Nenhuma PR ligada a esta Story.")
    else:
        now = m.now
        st.dataframe(pd.DataFrame({
            "PR": prs["url"], "Título": prs["title"], "Autor": prs["author"].map(V.pessoa), "Lado": prs["kind"].fillna(NA),
            "Estado": prs["state"], "Revisão": prs["review_state"].map(lambda r: V.REVIEW_LABEL.get(r, str(r))),
            "Aprov.": prs["approvals"], "Revisores pedidos": prs["requested_reviewers"].map(lambda r: ", ".join(r) or NA),
            "Aberta há": [fmt_duration((now - c).total_seconds() / 3600) for c in prs["created"]]}),
            hide_index=True, use_container_width=True,
            column_config={"PR": st.column_config.LinkColumn("PR", display_text=r"/pull/(\d+)$")})


def render_stories(m: Mgmt, domain: str) -> None:
    _kpis(m)
    if m.stories.empty:
        st.info("Nenhuma Story no recorte atual (Sprint / Stories / Desenvolvedor).")
        return
    st.caption("Clique numa linha para ver a hierarquia: Story → Subtasks → Commits, e Branches / PRs da Story. "
               "Estimado, Registrado e Restante vêm do Jira por task; a coluna da Story é a SOMA das subtasks (calculada aqui).")
    frame = _stories_frame(m, domain)
    ev = st.dataframe(frame, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row",
                      column_config={"Jira": V.jira_col()}, key="sprint_stories_table")
    if ev.selection.rows:
        _story_detail(m, m.stories.sort_values(["us_id", "story_key"], na_position="last").iloc[ev.selection.rows[0]]["story_key"], domain)


# ---------------------------------------------------------------- Burnup
def render_burnup(m: Mgmt) -> None:
    st.markdown("#### 📈 Burnup")
    if m.burnup is None:
        st.info("Selecione UMA Sprint no filtro lateral para ver o Burnup (com 'Todas' não existe escopo único).")
        return
    b = m.burnup
    if b.days.empty:
        for n in b.notes:
            st.warning(n)
        return
    st.caption("Escopo total (linha cinza) e trabalho concluído (linha verde), em nº de issues. O escopo PODE mudar: entradas/saídas de "
               "tasks na Sprint vêm do histórico do Jira. A série vai até hoje (não se projeta escopo futuro).")
    d = b.days
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["date"], y=d["scope_items"], name="Escopo total (issues)", line=dict(color=C["gray"], width=3, shape="hv"),
                             hovertemplate="Escopo: %{y} em %{x|%d/%m}<extra></extra>"))
    fig.add_trace(go.Scatter(x=d["date"], y=d["done_items"], name="Concluído (issues)", mode="lines+markers",
                             line=dict(color=C["green"], width=3), hovertemplate="Concluído: %{y} em %{x|%d/%m}<extra></extra>"))
    fig.update_yaxes(title="Issues", rangemode="tozero")
    st.plotly_chart(style_fig(fig, 300), use_container_width=True)
    if b.sp_available:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=d["date"], y=d["scope_sp"], name="Story Points planejados", line=dict(color=C["gray"], width=3, shape="hv")))
        fig2.add_trace(go.Scatter(x=d["date"], y=d["done_sp"], name="Story Points concluídos", mode="lines+markers", line=dict(color=C["green"], width=3)))
        fig2.update_yaxes(title="Story Points", rangemode="tozero")
        st.plotly_chart(style_fig(fig2, 280), use_container_width=True)
        if b.sp_missing:
            st.caption(f"⚠️ {b.sp_missing} Story(ies) sem Story Points: fora da soma (não contam como 0).")
    else:
        st.info("Story Points indisponíveis para este recorte (campo ausente ou sem valores no Jira): Burnup só em issues.")
    if not b.changes.empty:
        with st.expander(f"🔀 Mudanças de escopo depois do início da Sprint ({len(b.changes)})"):
            st.dataframe(b.changes.assign(date=b.changes["date"].dt.strftime("%d/%m/%Y"))
                         .rename(columns={"date": "Data", "key": "Issue", "change": "Mudança", "basis": "Base"}),
                         hide_index=True, use_container_width=True)
            st.caption("Base 'events' = evento de Sprint no histórico do Jira; 'approx' = deduzida da data de criação da issue.")
    with st.expander("ℹ️ Como o Burnup é calculado / limitações"):
        for n in b.notes:
            st.markdown(f"- {n}")
        st.markdown("- Concluído = task em 'Concluída' ao fim do dia (reabertura desconta) e ainda no escopo naquele dia.\n"
                    "- Item não concluído levado à próxima Sprint no fechamento é carry-over, não redução de escopo.")


# ---------------------------------------------------------------- Tempo em status
def render_time_in_status(m: Mgmt, domain: str) -> None:
    st.markdown("#### ⏱️ Tempo em status")
    st.caption(V.tz_note() + " O status atual conta de quando a issue entrou nele até agora. Tempo depois de concluída não entra na matriz.")
    seg = m.tis.segments
    if seg.empty:
        st.info("Sem histórico de status para as tasks do recorte.")
    else:
        matrix = TIS.by_group(seg)
        cur = TIS.current_status_hours(seg)
        items = m.scope.items.set_index("subtask_key")
        rows = []
        for k in matrix.index if not matrix.empty else []:
            r = {"Jira": V.jira_url(domain, k), "Resumo": items.loc[k, "subtask_summary"], "Responsável": V.pessoa(items.loc[k, "assignee"]),
                 "Status atual": items.loc[k, "status_name"], "No status atual": fmt_duration(cur.get(k))}
            r |= {g: fmt_duration(matrix.loc[k, g]) if g in matrix.columns else NA for g in S.FLUXO[:-1] + [S.BLOQUEADA]}
            rows.append(r)
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, column_config={"Jira": V.jira_col()})
        pick = st.selectbox("Detalhar uma task (por status do Jira)", [""] + sorted(seg["subtask_key"].unique()), key="tis_pick")
        if pick:
            p = TIS.per_status(seg[seg["subtask_key"] == pick])
            st.dataframe(pd.DataFrame({"Status": p["status"], "Tempo": p["hours"].map(fmt_duration), "Visitas": p["visits"],
                                       "Atual": p["current"].map({True: "◀ agora", False: ""})}), hide_index=True, use_container_width=True)
            if seg[(seg["subtask_key"] == pick) & seg["inconsistent"]].shape[0]:
                st.warning("O último destino do histórico difere do status atual do Jira: vale o status atual (histórico possivelmente incompleto).")
            if seg[(seg["subtask_key"] == pick) & (seg["basis"] == "sem_transicoes")].shape[0]:
                st.caption("Sem transições no histórico: a task está no status atual desde a criação.")
    if m.tis.unknown:
        st.warning(f"Sem tempo calculado (histórico incompleto ou sem data de criação): {', '.join(sorted(m.tis.unknown))}")
