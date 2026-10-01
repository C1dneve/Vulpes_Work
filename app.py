"""Moonfoxes • Dashboard Jira + GitHub."""
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

import setup_wizard
import ui_components as ui
from domain import statuses as S
from domain import timeutil
from domain.linking import branches_for_story, commits_for_item, display_id, prs_for_story, story_level_commits
from domain.people import nome_exibicao, suggest_matches, unmapped_authors
from domain.text import esc, literal_contains, md_esc
from services import sync
from services.context import Bundle, Context, apply_context, default_sprint, sprint_options, sprint_window, stories_in_sprint
from services.mgmt import build_mgmt
from settings import load_settings, save_dev_mapping
from ui_components import STATUS_COR, C
from views import now as v_now
from views import people as v_people
from views import sprint as v_sprint
from views import timeline as v_timeline
from views.common import due_label, remaining_label

_icone = ui.ASSETS / "favicon.png"
st.set_page_config(page_title="Moonfoxes • Jira + GitHub", page_icon=Image.open(_icone) if _icone.exists() else "🦊",
                   layout="wide", initial_sidebar_state="expanded")
ui.apply_theme()

settings = load_settings()
# Tela de onboarding: se faltar alguma variável obrigatória, pede os tokens numa tela amigável.
if not settings.ready:
    setup_wizard.tela_onboarding()
    st.stop()


def _txt(v):
    """Texto de uma célula que pode ser None/NaN."""
    return "" if v is None or (not isinstance(v, (list, tuple)) and pd.isna(v)) else str(v)


# ---------------------------------------------------------------- dados
with st.spinner("Sincronizando Jira e GitHub..."):
    loaded = sync.load_all(settings)

_ultima = max((v.result.fetched_at for v in (loaded.jira, loaded.github) if v.result is not None), default=None)
ui.header(timeutil.fmt(_ultima) if _ultima is not None else "—", loaded.jira.state, loaded.github.state)

# Falhas aparecem como falha (com o motivo), nunca como "sem dados".
for v in (loaded.jira, loaded.github):
    for e in v.errors:
        idade = f" — exibindo dados de {v.age_min:.0f} min atrás" if v.stale and v.age_min is not None else ""
        st.error(f"🔴 {e}{idade}")
if loaded.jira.data is None:
    st.info("Sem nenhum dado do Jira para exibir. Corrija o problema acima (veja também Configurações) e clique em Atualizar.")
    with st.sidebar:
        st.button("🔄 Atualizar Jira", use_container_width=True, on_click=sync.clear, args=("jira",))
    st.stop()

jd = sync.jira_data(loaded.jira)
df_stories, df_sub, df_sprints = jd.stories, jd.items, jd.sprints
_slugs_jira = set(df_sub["assignee"].dropna()) - {"nenhum"}
gd = sync.github_data(loaded.github, _slugs_jira)
raw = Bundle(jd.stories, jd.items, jd.worklogs, jd.changelog, jd.sprints, gd.commits, gd.branches, gd.prs, jd.sprint_events)
if df_sub.empty:
    st.warning("O Jira respondeu, mas não há issues no board. Confira BOARD_ID e as permissões (Configurações → Sincronização).")
    st.stop()

PAGINAS = {"Dashboard": ":material/home:", "Sprint": ":material/event_note:", "Agora": ":material/notifications_active:",
           "Pessoas": ":material/groups:", "Timeline": ":material/timeline:", "Issues": ":material/list_alt:",
           "Commits": ":material/account_tree:", "Relatórios": ":material/bar_chart:", "Configurações": ":material/settings:"}

with st.sidebar:
    pagina = st.radio("Navegação", list(PAGINAS), format_func=lambda p: f"{PAGINAS[p]} {p}",
                      label_visibility="collapsed", key="nav_page")
    c_j, c_g = st.columns(2)
    c_j.button("🔄 Jira", use_container_width=True, on_click=sync.clear, args=("jira",), help="Atualizar só o Jira")
    c_g.button("🔄 GitHub", use_container_width=True, on_click=sync.clear, args=("github",), help="Atualizar só o GitHub")
    st.button("🔄 Atualizar tudo", use_container_width=True, on_click=sync.clear)
    _idade = [f"{v.name}: há {v.age_min:.0f} min" for v in (loaded.jira, loaded.github) if v.age_min is not None]
    if _idade:
        st.caption(" · ".join(_idade))
    with st.expander("🎛️ Filtros (valem para todas as telas)", expanded=True):
        opcoes_sprint = sprint_options(df_stories, df_sprints)
        padrao = default_sprint(df_stories, df_sprints)   # sprint ativa selecionada automaticamente
        sprint = st.selectbox("Sprint", ["Todas"] + opcoes_sprint, key="flt_sprint",
                              index=(opcoes_sprint.index(padrao) + 1) if padrao in opcoes_sprint else 0)
        df_st = stories_in_sprint(df_stories, df_sub, sprint) if sprint != "Todas" else df_stories
        titulos_por_chave = dict(zip(df_st["story_key"], df_st["story_summary"], strict=True))
        chaves = st.multiselect("User Stories", list(titulos_por_chave), default=list(titulos_por_chave),
                                format_func=lambda k: f"{k} · {titulos_por_chave[k]}", key=f"flt_stories_{sprint}")
        devs_disponiveis = sorted(df_sub["assignee"].dropna().unique(), key=nome_exibicao)
        dev = st.selectbox("Desenvolvedor", ["Todos"] + devs_disponiveis,
                           format_func=lambda x: x if x == "Todos" else nome_exibicao(x), key="flt_dev")
    st.markdown(ui.sidebar_footer(), unsafe_allow_html=True)

# Contexto global: UM recorte aplicado a Jira, commits, branches, PRs, worklogs e changelog.
ctx = Context(sprint=None if sprint == "Todas" else sprint, dev=None if dev == "Todos" else dev, story_keys=tuple(chaves))
scope = apply_context(raw, ctx)
df_meta, df_com, df_br, df_pr, df_wl, df_cl = scope.items, scope.commits, scope.branches, scope.prs, scope.worklogs, scope.changelog
gh_msgs = loaded.github.messages
KNOWN_KEYS = set(df_sub["subtask_key"]) | set(df_stories["story_key"])

# Regras de gestão do MVP (prazo, esforço, bloqueio, inatividade, alertas, tempo em status, Timeline, Burnup) sobre o MESMO contexto.
_jira_stats = loaded.jira.result.stats if loaded.jira.result is not None else {}
_agora = timeutil.now().floor("min")
# Memo: só recalcula quando muda a carga (fetched_at), o filtro, os limiares ou o minuto — cliques de UI não repagam o cálculo.
_mkey = (loaded.jira.result.fetched_at if loaded.jira.result is not None else None,
         loaded.github.result.fetched_at if loaded.github.result is not None else None, loaded.github.state, ctx, settings.management, _agora)
if st.session_state.get("_mgmt_key") != _mkey:
    st.session_state["_mgmt"] = build_mgmt(raw, ctx, settings.management, now=_agora, github_ok=loaded.github.result is not None,
                                           github_since=_agora - pd.Timedelta(days=settings.github.lookback_days),
                                           history_unknown=set(_jira_stats.get("changelog_partial") or []),
                                           github_partial=loaded.github.state == "partial", github_stale=loaded.github.stale)
    st.session_state["_mgmt_key"] = _mkey
m = st.session_state["_mgmt"]

retornos = {}
if not df_cl.empty:
    voltas = df_cl[df_cl["from_group"].isin([S.ANALISE, S.TESTE]) & (df_cl["to_group"] == S.ANDAMENTO)]
    retornos = voltas.groupby("subtask_key").size().to_dict()

# Mapa nome-bonito -> slug, usado pra "destravar" o slug original quando a pessoa clica num
# nome de dev num gráfico (o gráfico mostra o nome bonito, mas tudo é filtrado pelo slug).
_slugs_conhecidos = set(df_sub["assignee"].dropna()) | (set(gd.commits["author"].dropna()) if not gd.commits.empty else set())
NOME_PARA_SLUG = {nome_exibicao(s_): s_ for s_ in _slugs_conhecidos}


# ---------------------------------------------------------------- helpers
def commits_da_task(t):
    """Commits (humanos) de uma task. Usa TODOS os commits carregados, não só o recorte de autor/janela.
    Commit = Subtask: só entram commits que citam a chave DESTA task na mensagem (nem a chave da Story, nem o ID
    visual US2.1, nem a referência da PR/branch atribuem um commit a todas as Subtasks)."""
    if raw.commits.empty:
        return raw.commits
    cm = commits_for_item(raw.commits, t, KNOWN_KEYS)
    return cm[cm["kind"] == "human"]


def _filhas(story_key):
    return set(df_sub.loc[df_sub["story_key"] == story_key, "subtask_key"])


def _us_da_story(story_key):
    v = df_stories.loc[df_stories["story_key"] == story_key, "us_id"]
    return v.iloc[0] if len(v) and pd.notna(v.iloc[0]) else None


def refs_da_story(story_key):
    """(branches, PRs, commits sem Subtask) da User Story — Jira Key vence; US visual só sem chave conhecida."""
    filhas, us = _filhas(story_key), _us_da_story(story_key)
    br = branches_for_story(raw.branches, story_key, us, filhas, KNOWN_KEYS)
    pr = prs_for_story(raw.prs, story_key, us, filhas, KNOWN_KEYS)
    cm = story_level_commits(raw.commits, story_key, us, filhas, KNOWN_KEYS)
    return br, pr, (cm[cm["kind"] == "human"] if not cm.empty else cm)


def _codigo(t):
    return t["subtask_code"] if pd.notna(t.get("subtask_code")) else t["subtask_key"]


def resumo_git(tasks):
    rows = []
    for _, t in tasks.iterrows():
        cm = commits_da_task(t)
        n, n_ent = len(cm), int(cm["delivered"].sum()) if len(cm) else 0
        alerta = ""
        if t["status_group"] == S.CONCLUIDA and n == 0: alerta = "⚠️ Possível inconsistência: concluída sem commits vinculados"
        elif t["status_group"] == S.CONCLUIDA and n_ent == 0: alerta = "⚠️ Possível inconsistência: concluída, mas sem entrega (main ou PR merged)"
        elif t["status_group"] == S.PENDENTE and n > 0: alerta = "ℹ️ Tem commits, mas está Pendente"
        rows.append({"Task": _codigo(t), "User Story": t["us_id"] if pd.notna(t["us_id"]) else "—",
                     "Resumo": t["subtask_summary"], "Dev": nome_exibicao(t["assignee"]), "Status": t["status_group"],
                     "Horas": round(t["time_spent_h"], 1), "Estimado (h)": t["estimate_h"], "Commits": n,
                     "Entregues": n_ent, "Em branch": n - n_ent,
                     "Branches": ", ".join(sorted({b for l in cm["branches"] for b in l})) if n else "",
                     "Alerta": alerta, "subtask_key": t["subtask_key"]})
    return pd.DataFrame(rows, columns=["Task", "User Story", "Resumo", "Dev", "Status", "Horas", "Estimado (h)", "Commits",
                                       "Entregues", "Em branch", "Branches", "Alerta", "subtask_key"])


@st.dialog("🔍 Detalhes da task", width="large")
def modal_task(sub):
    st.subheader(f"{md_esc(_codigo(sub))}: {md_esc(sub['subtask_summary'])}")
    st.caption(f"Jira: `{md_esc(sub['subtask_key'])}` · User Story: {md_esc(sub['story_summary'])} "
               f"(`{md_esc(display_id(sub['story_key'], sub['us_id']))}`)")
    story_br, story_pr, story_cm = refs_da_story(sub["story_key"])
    if story_br.empty and story_pr.empty:
        st.caption("Sem branch nem PR ligada a esta User Story (pela chave do Jira ou pelo ID visual).")
    else:
        brs = ", ".join("`" + b.replace("`", "") + "`" for b in story_br["branch"]) or "—"
        prs = ", ".join(f"#{n}" for n in story_pr["number"]) or "—"
        st.caption(f"Branches da Story: {brs} · PRs da Story: {prs}")
    if retornos.get(sub["subtask_key"], 0):
        st.warning(f"Esta task já voltou {retornos[sub['subtask_key']]}x da Análise/Teste para Em Andamento.")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(ui.badge(sub["status_group"]), unsafe_allow_html=True)
        st.write(f"**Dev:** {nome_exibicao(sub['assignee'])}")
        est = f" (estimado {sub['estimate_h']:.1f}h)" if pd.notna(sub["estimate_h"]) else ""
        st.write(f"**Esforço:** {sub['time_spent_h']:.1f}h{est}")
        _e = m.items_team[m.items_team["subtask_key"] == sub["subtask_key"]]
        if not _e.empty:
            _e = _e.iloc[0]
            st.write(f"**Restante:** {remaining_label(_e['remaining_eff_h'], _e['remaining_source'])}")
            st.write(f"**Prazo:** {due_label(_e['due_date'], _e['due_status'])}")
            _sp = m.stories_team[m.stories_team["story_key"] == sub["story_key"]]
            st.write(f"**Story Points da Story:** {'—' if _sp.empty or pd.isna(_sp.iloc[0]['story_points']) else format(_sp.iloc[0]['story_points'], 'g')}")
            if _e["is_blocked"] and not _e["is_done"]:
                st.error(f"Bloqueada: {_e['block_reason'] or 'motivo não informado no Jira'}")
        st.write(f"**Tag:** `{sub['label']}`")
        st.markdown(f"[Abrir no Jira](https://{settings.jira.domain}/browse/{quote(sub['subtask_key'])})")
    with c2:
        cm = commits_da_task(sub)
        if cm.empty:
            st.caption(f"👻 Nenhum commit cita a chave {md_esc(sub['subtask_key'])} na mensagem.")
        else:
            branches = sorted({b for l in cm["branches"] for b in l})
            st.markdown(f"**{len(cm)} commits** · {int(cm['delivered'].sum())} entregues · branches: "
                        f"{', '.join('`' + b.replace('`', '') + '`' for b in branches)}")
            for _, r in cm.iterrows():
                via = f" · PR {', '.join('#' + str(n) for n in r['pr_numbers'])}" if r["pr_numbers"] else ""
                st.markdown(f"- {'✅' if r['delivered'] else '🌿'} `{r['branch_label'].replace('`', '')}` · {r['date']:%d/%m} · "
                            f"**{md_esc(nome_exibicao(r['author']))}** · [{md_esc(r['title'][:60])}]({r['url']}) "
                            f"_(via {r['link_source']}{via})_")
        if not story_cm.empty:
            with st.expander(f"Commits da User Story sem Subtask específica ({len(story_cm)})"):
                st.caption("Citam só a Story, a PR/branch ou o ID visual. Não provam execução de nenhuma Subtask.")
                for _, r in story_cm.head(15).iterrows():
                    st.markdown(f"- {'✅' if r['delivered'] else '🌿'} {r['date']:%d/%m} · **{md_esc(nome_exibicao(r['author']))}** · "
                                f"[{md_esc(r['title'][:60])}]({r['url']})")


@st.dialog("👤 Detalhes do desenvolvedor", width="large")
def modal_dev(slug):
    tarefas = df_meta[df_meta["assignee"] == slug]   # respeita o contexto global (sprint/histórias)
    contagem = tarefas["status_group"].value_counts()
    horas = tarefas["time_spent_h"].sum()
    hum = df_com[df_com["kind"] == "human"] if not df_com.empty else df_com
    commits_pessoa = hum[hum["author"] == slug].sort_values("date", ascending=False) if not hum.empty else hum
    branches_pessoa = df_br[df_br["last_author"] == slug] if not df_br.empty else df_br

    st.subheader(nome_exibicao(slug))
    st.caption("Números dentro do contexto atual dos filtros (sprint e User Stories).")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.write(f"**Total de tasks:** {len(tarefas)}")
        for status in STATUS_COR:
            if contagem.get(status, 0):
                st.markdown(ui.badge(status) + f" &nbsp;{contagem[status]}", unsafe_allow_html=True)
        st.write(f"**Horas somadas (worklog das subtasks):** {horas:.1f}h")
        if len(branches_pessoa):
            ativas = branches_pessoa[branches_pessoa["pending_commits"] > 0]
            st.write(f"**Branches com trabalho pendente:** {len(ativas)}" if len(ativas) else "**Sem branches com trabalho pendente no momento.**")
            for _, b in ativas.iterrows():
                st.markdown(f"- 🌿 `{b['branch'].replace('`', '')}` ({md_esc(b['repo'])})")
        if st.button("🔎 Ver tasks e commits desta pessoa em Commits", use_container_width=True):
            st.session_state["flt_dev"] = slug
            st.session_state["commits_autor_filter"] = [slug]
            st.session_state["nav_page"] = "Commits"
            st.rerun()
    with c2:
        if commits_pessoa.empty:
            st.caption("👻 Nenhum commit humano encontrado para esta pessoa no contexto atual.")
        else:
            n_ent = int(commits_pessoa["delivered"].sum())
            st.markdown(f"**{len(commits_pessoa)} commits** · {n_ent} entregues · {len(commits_pessoa) - n_ent} em branch")
            for _, r in commits_pessoa.head(15).iterrows():
                st.markdown(f"- {'✅' if r['delivered'] else '🌿'} `{r['branch_label'].replace('`', '')}` · {r['date']:%d/%m} · "
                            f"[{md_esc(r['title'][:60])}]({r['url']})")
            if len(commits_pessoa) > 15:
                st.caption(f"... e mais {len(commits_pessoa) - 15} commits.")


def _dev_clicado(evento):
    """Extrai o slug do dev a partir do ponto clicado num gráfico (via customdata) e abre o modal."""
    if not evento or not getattr(evento, "selection", None) or not evento.selection.points:
        return
    ponto = evento.selection.points[0]
    slug = None
    cd = ponto.get("customdata")
    if cd:
        slug = cd[0] if isinstance(cd, (list, tuple)) else cd
    if not slug:
        slug = NOME_PARA_SLUG.get(ponto.get("x"))
    if slug:
        modal_dev(slug)


def datas_sprint():
    """(início, fim) da sprint selecionada — datas do board; com 'Todas', a união das stories no contexto."""
    return sprint_window(df_stories, df_sprints, ctx.sprint, ctx.story_keys)


def sprint_ainda_nao_comecou():
    ini, _ = datas_sprint()
    return ini is not None and timeutil.today() < ini


def intervalo_dias(ate_hoje=True):
    ini, fim = datas_sprint()
    logs = [d["date"] for d in (df_wl, df_cl) if not d.empty]
    todas = pd.concat(logs) if logs else pd.Series(dtype="datetime64[ns]")
    hoje = timeutil.today()
    ini = ini if ini is not None else (todas.min() if not todas.empty else hoje - pd.Timedelta(days=7))
    fim = fim if fim is not None else hoje
    if ate_hoje:
        fim = min(fim, hoje)
    # Garante um intervalo válido (>= 2 pontos, sempre incluindo hoje) mesmo quando a sprint ainda não
    # começou ou já terminou segundo as datas do Jira (ini > fim).
    return pd.date_range(min(ini, fim, hoje), max(ini, fim, hoje))


def serie_status_diaria(dias):
    """Quantas tasks estavam em cada grupo de status em cada dia, reconstruído pelo changelog COMPLETO do Jira."""
    cl = df_cl[df_cl["subtask_key"].isin(df_meta["subtask_key"])].sort_values("ts") if not df_cl.empty else df_cl
    hist = {k: list(zip(g["date"], g["to_group"], strict=True)) for k, g in cl.groupby("subtask_key")} if not cl.empty else {}
    rows = []
    for d in dias:
        cont = {g: 0 for g in S.GRUPOS}
        for k in df_meta["subtask_key"]:
            atual = None
            for quando, grupo in hist.get(k, []):
                if quando <= d: atual = grupo
                else: break
            if atual in cont: cont[atual] += 1
        rows.append({"data": d, **cont, "Andamento (total)": sum(cont[g] for g in S.EM_PROGRESSO)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- páginas
def pg_dashboard():
    a, b = st.columns([1, 1.15])
    a.markdown(ui.HERO_LEFT, unsafe_allow_html=True)
    b.markdown(ui.HERO_RIGHT, unsafe_allow_html=True)
    total = len(df_meta)
    n = lambda g: int((df_meta["status_group"] == g).sum())
    pct = lambda x: f"{x / total:.0%} da meta" if total else "—"
    andamento = sum(n(g) for g in S.EM_PROGRESSO)
    ks = st.columns(4)
    ks[0].markdown(ui.kpi("Total de Issues", total, "no contexto selecionado", C["blue"], "◆"), unsafe_allow_html=True)
    ks[1].markdown(ui.kpi("Concluídas", n(S.CONCLUIDA), pct(n(S.CONCLUIDA)), C["green"], "✓"), unsafe_allow_html=True)
    ks[2].markdown(ui.kpi("Em Andamento", andamento, pct(andamento) + " (inclui Análise e Teste)", C["blue"], "◔"), unsafe_allow_html=True)
    ks[3].markdown(ui.kpi("Bloqueadas", n(S.BLOQUEADA), pct(n(S.BLOQUEADA)), C["red"], "!"), unsafe_allow_html=True)

    k = m.kpis
    ks2 = st.columns(4)
    _sp = "indisponível" if k["sp_planned"] is None else f"{k['sp_done']:g}/{k['sp_planned']:g}"
    _sp_sub = "Story Points concluídos/planejados" if k["sp_planned"] is not None else "campo ausente ou sem valores no Jira"
    ks2[0].markdown(ui.kpi("Story Points", _sp, _sp_sub + (f" · {k['sp_missing']} Story(ies) sem pontos" if k["sp_planned"] is not None and k["sp_missing"] else ""), C["purple"], "★"), unsafe_allow_html=True)
    _est = "—" if k["estimate_h"] is None else f"{k['estimate_h']:.0f}h"
    ks2[1].markdown(ui.kpi("Estimado × Registrado", f"{_est} / {k['logged_h']:.0f}h", f"estimativa em {k['estimate_items']} de {k['items']} tasks", C["blue"], "⏱"), unsafe_allow_html=True)
    ks2[2].markdown(ui.kpi("Atrasadas", k["late"], "due date vencido, não concluídas", C["red"], "⏰"), unsafe_allow_html=True)
    ks2[3].markdown(ui.kpi("Inativas", k["inactive"], f"em andamento sem atividade ≥ {settings.management.inactive_business_days} dias úteis", C["gray"], "💤"), unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2.1, 1.25, 1.05])
    with c1, st.container(border=True):
        st.markdown("#### 📈 Progresso da Sprint")
        st.caption("Quantas issues do contexto estavam em cada status a cada dia, reconstruído pelo histórico do Jira.")
        if sprint_ainda_nao_comecou():
            ini, _ = datas_sprint()
            st.warning(f"⚠️ Segundo as datas do Jira, esta sprint só começa em {ini:%d/%m/%Y} — "
                       "confira se as datas da sprint no board estão corretas.")
        serie = serie_status_diaria(intervalo_dias())
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
        ini, fim = datas_sprint()
        datas = f"{ini:%d/%m/%Y} → {fim:%d/%m/%Y}" if ini is not None and fim is not None else "sem datas no Jira"
        st.markdown(f"**{esc(sprint)}**<br><span class='mf-muted'>{esc(datas)}</span>", unsafe_allow_html=True)
        st.markdown(ui.bar("Concluídas", n(S.CONCLUIDA), total, C["green"]) + ui.bar("Em andamento", andamento, total, C["blue"])
                    + ui.bar("Bloqueadas", n(S.BLOQUEADA), total, C["red"]), unsafe_allow_html=True)

    d1, d2, d3 = st.columns([1.4, 1.5, .9])
    with d1, st.container(border=True):
        st.markdown("#### 🧾 Últimas Issues")
        ult = df_meta.sort_values("updated", ascending=False).head(5)
        st.markdown("".join(ui.row((ui.chip(_codigo(t)), ""), (t["subtask_summary"], "t"), (ui.badge(t["status_group"]), ""),
                                   (nome_exibicao(t["assignee"]), "m"), (ui.ago(t["updated"]), "m")) for _, t in ult.iterrows()) or "—",
                    unsafe_allow_html=True)
    with d2, st.container(border=True):
        st.markdown("#### ⌥ Últimos Commits (todas as branches)")
        hum = df_com[df_com["kind"] == "human"] if not df_com.empty else df_com
        st.markdown("".join(ui.row((ui.chip(display_id(t["jira_key"] or t["ref_jira_key"], t["us_id"]) or "sem ID"), ""), (t["title"], "t"),
                                   (ui.chip(("✅ " if t["delivered"] else "🌿 ") + t["branch_label"]), ""),
                                   (nome_exibicao(t["author"]), "m"), (f"{t['sha'][:7]} · {ui.ago(t['date'])}", "m"))
                            for _, t in hum.head(5).iterrows()) or "Nenhum commit no contexto atual.", unsafe_allow_html=True)
    with d3:
        with st.container(border=True):
            st.markdown("#### 🐙 Repositórios")
            org = settings.github.org
            st.markdown("".join(f'<a class="mf-link" href="https://github.com/{quote(org)}/{quote(r)}" target="_blank" rel="noopener">'
                                f'{esc(org)}/{esc(r)} ↗</a>' for r in settings.github.repos), unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("#### ⚡ Atalhos")
            st.markdown(f'<a class="mf-link" href="https://{quote(settings.jira.domain)}/secure/RapidBoard.jspa?rapidView={quote(settings.jira.board_id)}" target="_blank" rel="noopener">◆ Ver no Jira ↗</a>'
                        f'<a class="mf-link" href="https://github.com/{quote(org)}" target="_blank" rel="noopener">⌥ Ver no GitHub ↗</a>', unsafe_allow_html=True)


def pg_sprint():
    t_stories, t_progress, t_status = st.tabs(["📖 Stories", "📉 Progresso (Burndown e Burnup)", "⏱️ Tempo em status"])
    with t_stories:
        v_sprint.render_stories(m, settings.jira.domain)
        with st.expander("📋 Resumo Git por Story (visão anterior)"):
            _resumo_git_por_story()
    with t_progress:
        _burndown()
        v_sprint.render_burnup(m)
    with t_status:
        v_sprint.render_time_in_status(m, settings.jira.domain)


def _burndown():
    with st.container(border=True):
        st.markdown("#### 📉 Burndown da meta")
        st.caption("Linha tracejada = ritmo ideal para zerar a meta até o fim da sprint; "
                   "linha vermelha = quantas issues realmente faltam, dia a dia.")
        if sprint_ainda_nao_comecou():
            ini, _ = datas_sprint()
            st.warning(f"⚠️ Segundo as datas do Jira, esta sprint só começa em {ini:%d/%m/%Y} — "
                       "confira se as datas da sprint no board estão corretas.")
        dias = intervalo_dias(ate_hoje=False)
        serie = serie_status_diaria(dias)
        total = len(df_meta)
        passo = total / (len(dias) - 1) if len(dias) > 1 else 0
        hoje = timeutil.today()
        real = serie[serie["data"] <= hoje]
        if real.empty:
            st.info("Nenhum dado real ainda dentro do período da sprint — confira as datas da sprint no Jira.")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dias, y=[max(0, total - i * passo) for i in range(len(dias))], name="Linha ideal",
                                 line=dict(dash="dash", color=C["gray"]),
                                 hovertemplate="Ideal: %{y:.1f} restantes em %{x|%d/%m/%Y}<extra></extra>"))
        fig.add_trace(go.Scatter(x=real["data"], y=total - real[S.CONCLUIDA], name="Restantes", mode="lines+markers",
                                 line=dict(color=C["red"], width=3),
                                 hovertemplate="Restantes: %{y} em %{x|%d/%m/%Y}<extra></extra>"))
        fig.update_xaxes(title="Data")
        fig.update_yaxes(title="Issues restantes")
        st.plotly_chart(ui.style_fig(fig, 300), use_container_width=True)


def _resumo_git_por_story():
    for _, story in scope.stories.sort_values("story_summary").iterrows():
        subs = df_meta[df_meta["story_key"] == story["story_key"]].sort_values("subtask_summary")
        if subs.empty:
            continue
        with st.expander(f"📖 {md_esc(story['story_summary'])} — {len(subs)} subtasks"):
            s_br, s_pr, _ = refs_da_story(story["story_key"])
            st.caption(f"{display_id(story['story_key'], story['us_id'])} · branches: {len(s_br)} · PRs: {len(s_pr)}")
            st.dataframe(resumo_git(subs).drop(columns="subtask_key"), hide_index=True, use_container_width=True)


def pg_issues():
    f1, f2 = st.columns([2, 1])
    status = f1.multiselect("Status", list(STATUS_COR), default=list(STATUS_COR))
    busca = f2.text_input("Buscar", placeholder="ID ou texto")
    view = resumo_git(df_meta[df_meta["status_group"].isin(status)])
    if busca:   # busca LITERAL: "(", "[", "*", "+" não quebram nem viram regex
        view = view[literal_contains(view["Task"], busca) | literal_contains(view["Resumo"], busca)
                    | literal_contains(view["User Story"], busca)]
    st.caption("Clique em uma linha para ver os detalhes e os commits (com as branches) da task.")
    ev = st.dataframe(view.drop(columns="subtask_key"), hide_index=True, use_container_width=True,
                      on_select="rerun", selection_mode="single-row")
    if ev.selection.rows:
        chave = view.iloc[ev.selection.rows[0]]["subtask_key"]
        modal_task(df_sub[df_sub["subtask_key"] == chave].iloc[0])


def pg_commits():
    for e in gh_msgs:
        st.warning(e)
    if df_com.empty and df_br.empty and df_pr.empty:
        if loaded.github.result is None:
            st.info("Sem dados do GitHub — veja o erro acima.")
        else:
            st.info("Nenhum commit no contexto atual (sprint/histórias/desenvolvedor). Ajuste os filtros na barra lateral.")
        return
    st.caption(f"Janela do GitHub: últimos {settings.github.lookback_days} dias (config.json → github.lookback_days). "
               "'Entregue' = SHA na main, cópia equivalente na main (rebase) **ou** commit de PR merged (Squash and Merge).")
    f = st.columns(6)
    repos = f[0].multiselect("Repositório", sorted(df_com["repo"].unique()))
    branches = f[1].multiselect("Branch", sorted({b for l in df_com["branches"] for b in l}))
    autores = f[2].multiselect("Autor", sorted(df_com["author"].dropna().unique(), key=nome_exibicao),
                               format_func=nome_exibicao, key="commits_autor_filter")
    onde = f[3].selectbox("Situação", ["Todos", "Entregues (main ou PR merged)", "Em branch (não entregues)"])
    vinc = f[4].selectbox("Vínculo Jira", ["Todos", "Com vínculo", "Sem vínculo"])
    tipo = f[5].selectbox("Tipo", ["Humanos", "Todos", "Bots", "Merges"])
    df = df_com
    if repos: df = df[df["repo"].isin(repos)]
    if branches: df = df[df["branches"].map(lambda l: any(b in l for b in branches))]
    if autores: df = df[df["author"].isin(autores)]
    if onde.startswith("Entregues"): df = df[df["delivered"]]
    if onde.startswith("Em branch"): df = df[~df["delivered"]]
    if vinc == "Com vínculo": df = df[df["link_source"].notna()]
    if vinc == "Sem vínculo": df = df[df["link_source"].isna()]
    df = df[{"Humanos": df["kind"] == "human", "Bots": df["kind"] == "bot", "Merges": df["kind"] == "merge"}.get(tipo, df["kind"].notna())] if not df.empty else df

    k = st.columns(5)
    ativas = df_br[(~df_br["is_default"]) & (df_br["pending_commits"] > 0)] if not df_br.empty else df_br
    invalidos = int((df["valid_message"] == False).sum()) if not df.empty else 0  # noqa: E712
    for col, (t, v, cor, ic) in zip(k, [("Commits", len(df), C["blue"], "⌥"), ("Entregues", int(df["delivered"].sum()) if len(df) else 0, C["green"], "✅"),
                                       ("Em branches", int((~df["delivered"]).sum()) if len(df) else 0, C["purple"], "🌿"),
                                       ("Sem vínculo Jira", int(df["link_source"].isna().sum()) if len(df) else 0, C["red"], "?"),
                                       ("Branches com trabalho pendente", len(ativas), C["blue"], "⑂")], strict=True):
        col.markdown(ui.kpi(t, v, "no filtro atual", cor, ic), unsafe_allow_html=True)
    if invalidos:
        st.warning(f"{invalidos} commit(s) fora da regra da equipe (sem chave do Jira na mensagem). "
                   "Use `feat(JH-101): descrição real da alteração`.")

    t1, t2, t3, t4 = st.tabs(["Commits", "Branches", "Pull Requests", "Por task (Jira ↔ GitHub)"])
    with t1:
        st.caption("Commits por dia (data local, America/Sao_Paulo), separando o que já foi entregue do que está só em branch.")
        if df.empty:
            st.caption("Nenhum commit com estes filtros.")
        else:
            g = (df.assign(dia=timeutil.local_dates(df["date"]), Local=df["delivered"].map({True: "entregue", False: "branch"}))
                   .groupby(["dia", "Local"]).size().reset_index(name="commits"))
            fig = px.bar(g, x="dia", y="commits", color="Local", color_discrete_map={"entregue": C["green"], "branch": C["purple"]},
                         labels={"dia": "Data", "commits": "Commits", "Local": "Situação"})
            fig.update_traces(hovertemplate="%{x|%d/%m/%Y} — %{fullData.name}: %{y} commit(s)<extra></extra>")
            st.plotly_chart(ui.style_fig(fig, 200), use_container_width=True)
            vis = df.assign(Branches=df["branches"].map(", ".join), Situação=df["delivered_via"].map({"main": "✅ main", "main_equivalente": "✅ main (SHA equivalente)",
                                                                              "pr": "✅ PR merged"}).fillna("🌿 branch"),
                            Autor=df["author"].map(nome_exibicao), PRs=df["pr_numbers"].map(lambda l: ", ".join(f"#{n}" for n in l)))
            st.dataframe(vis[["date", "repo", "url", "title", "Autor", "jira_key", "ref_jira_key", "us_id", "link_source", "Branches", "PRs", "Situação", "kind"]],
                         hide_index=True, use_container_width=True,
                         column_config={"date": st.column_config.DatetimeColumn("Data", format="DD/MM/YY HH:mm"),
                                        "url": st.column_config.LinkColumn("Commit", display_text=r"commit/(.{7})"), "title": "Mensagem",
                                        "jira_key": "Chave Jira (mensagem)", "ref_jira_key": "Chave da Story (PR/branch)", "us_id": "User Story",
                                        "link_source": "Vínculo via", "repo": "Repo", "kind": "Tipo"})
    with t2:
        st.caption("'Pendentes' = commits que só existem nessa branch e ainda não foram entregues (uma branch já mergeada via PR não conta).")
        b = df_br[~df_br["is_default"]] if not df_br.empty else df_br
        if repos and not b.empty:
            b = b[b["repo"].isin(repos)]
        if b.empty:
            st.caption("Nenhuma branch no contexto atual.")
        else:
            b_vis = b.assign(**{"Último autor": b["last_author"].map(nome_exibicao)}).drop(columns=["last_author", "is_default", "head_sha", "pr_numbers"])
            b_vis = b_vis[["jira_key", "us_id"] + [c for c in b_vis.columns if c not in ("jira_key", "us_id")]]   # chave oficial primeiro
            st.dataframe(b_vis.sort_values("pending_commits", ascending=False), hide_index=True, use_container_width=True,
                         column_config={"last_commit": st.column_config.DatetimeColumn("Último commit", format="DD/MM/YY HH:mm"),
                                        "pending_commits": "Commits pendentes", "ahead_main": "À frente da main", "behind_main": "Atrás da main",
                                        "delivered": "Entregue", "kind": "Lado", "us_id": "User Story", "jira_key": "Chave Jira",
                                        "follows_convention": "Segue convenção", "pr": "PR", "pr_state": "Estado do PR",
                                        "compare_status": "Compare"})
    with t3:
        if df_pr.empty:
            st.caption("Nenhuma PR no contexto atual.")
        else:
            pr_vis = df_pr.assign(Autor=df_pr["author"].map(nome_exibicao))[["number", "title", "Autor", "state", "kind", "head", "base", "created", "merged_at",
                                                                             "merge_method", "jira_key", "us_id", "follows_convention", "url"]]
            st.dataframe(pr_vis, hide_index=True, use_container_width=True,
                         column_config={"url": st.column_config.LinkColumn("Link", display_text="abrir"), "number": "PR", "title": "Título",
                                        "state": "Estado", "kind": "Lado", "head": "Branch", "base": "Base", "merge_method": "Merge",
                                        "us_id": "User Story", "jira_key": "Chave Jira", "follows_convention": "Título segue convenção",
                                        "created": st.column_config.DatetimeColumn("Criado", format="DD/MM/YY HH:mm"),
                                        "merged_at": st.column_config.DatetimeColumn("Mergeado", format="DD/MM/YY HH:mm")})
    with t4:
        todas = resumo_git(df_meta).drop(columns="subtask_key")
        st.caption("Alertas mostram divergências entre o que o Jira diz e o que o GitHub tem. "
                   "'Possível inconsistência' = não há evidência suficiente para afirmar que algo está errado.")
        st.dataframe(todas.sort_values("Alerta", ascending=False), hide_index=True, use_container_width=True)


def pg_relatorios():
    a, b = st.columns(2)
    concl = df_meta[df_meta["status_group"] == S.CONCLUIDA]
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
        e = df_meta.assign(Dev=df_meta["assignee"].map(nome_exibicao)).groupby(["Dev", "assignee", "status_group"]).size().reset_index(name="tasks")
        fig = px.bar(e, x="Dev", y="tasks", color="status_group", color_discrete_map=STATUS_COR,
                     category_orders={"status_group": list(STATUS_COR)}, custom_data=["assignee"],
                     labels={"Dev": "Desenvolvedor", "tasks": "Tasks", "status_group": "Status"})
        fig.update_traces(hovertemplate="%{x} — %{fullData.name}: %{y} task(s)<extra></extra>")
        evento = st.plotly_chart(ui.style_fig(fig, 280), use_container_width=True, on_select="rerun", key="chart_entregas_dev")
        _dev_clicado(evento)
    c, d = st.columns(2)
    with c, st.container(border=True):
        st.markdown("#### 🕓 Esforço diário (worklogs)")
        st.caption("Horas lançadas em worklog por dia (data local). Clique num ponto para ver os detalhes da pessoa.")
        w = df_wl   # já respeita sprint, histórias e desenvolvedor
        if w.empty:
            st.caption("Sem worklogs registrados neste contexto.")
        else:
            w = w.groupby(["date", "author"])["time_spent_h"].sum().reset_index()
            w["Dev"] = w["author"].map(nome_exibicao)
            fig = px.line(w, x="date", y="time_spent_h", color="Dev", markers=True, custom_data=["author"],
                          labels={"date": "Data", "time_spent_h": "Horas", "Dev": "Desenvolvedor"})
            fig.update_traces(hovertemplate="%{fullData.name}: %{y:.1f}h em %{x|%d/%m/%Y}<extra></extra>")
            evento = st.plotly_chart(ui.style_fig(fig, 280), use_container_width=True, on_select="rerun", key="chart_esforco_diario")
            _dev_clicado(evento)
    with d, st.container(border=True):
        st.markdown("#### ⌥ Commits por autor (entregues × em branch)")
        st.caption("Só commits humanos (bots e merges ficam de fora). Clique numa barra para ver os detalhes.")
        hum = df_com[df_com["kind"] == "human"] if not df_com.empty else df_com
        if hum.empty:
            st.caption("Sem commits humanos neste contexto.")
        else:
            g = (hum.assign(onde=hum["delivered"].map({True: "entregue", False: "branch"}), Dev=hum["author"].map(nome_exibicao))
                    .groupby(["Dev", "onde"]).agg(commits=("author", "size"), author=("author", "first")).reset_index())
            fig = px.bar(g, x="Dev", y="commits", color="onde", color_discrete_map={"entregue": C["green"], "branch": C["purple"]},
                         custom_data=["author"], labels={"Dev": "Desenvolvedor", "commits": "Commits", "onde": "Situação"})
            fig.update_traces(hovertemplate="%{x} — %{fullData.name}: %{y} commit(s)<extra></extra>")
            evento = st.plotly_chart(ui.style_fig(fig, 280), use_container_width=True, on_select="rerun", key="chart_commits_autor")
            _dev_clicado(evento)


def _painel_autores_nao_mapeados():
    st.markdown("#### 👤 Autores não mapeados")
    st.caption("Autores de commits (humanos) cujo login/e-mail do GitHub não está ligado a ninguém do Jira. Nada é "
               "vinculado automaticamente: confirme a sugestão e clique em Vincular (grava em `dev_mapping` no config.json).")
    unm = unmapped_authors(gd.commits)
    if unm.empty:
        st.success("Todos os autores humanos estão mapeados.")
        return
    slugs = sorted(_slugs_jira, key=nome_exibicao)
    for i, r in unm.iterrows():
        login, nome = _txt(r["author_login"]), _txt(r["author_name"])
        sug = suggest_matches(login or None, nome or None, slugs)
        c1, c2, c3 = st.columns([2, 2.2, .8])
        c1.markdown(f"**GitHub:** {md_esc(nome or login)}  \n`{md_esc(login or 'sem login')}` · {md_esc(_txt(r['author_email']))} · {r['commits']} commit(s)")
        opcoes = [s_ for s_, _ in sug] + [s_ for s_ in slugs if s_ not in [x for x, _ in sug]]
        escolha = c2.selectbox("Colaborador do Jira", opcoes, key=f"unm_sel_{i}", format_func=lambda x, _sug=tuple(y for y, _ in sug): nome_exibicao(x) + (" (sugestão)" if x in _sug else ""))
        if c3.button("Vincular", key=f"unm_btn_{i}", disabled=not opcoes):
            save_dev_mapping(settings.config_path, login or nome, escolha)
            sync.clear("github")
            st.rerun()


def _painel_sincronizacao():
    st.markdown("#### 🔄 Sincronização")
    icon = {"ok": "🟢", "partial": "🟡", "stale": "🟠", "error": "🔴"}
    for v in (loaded.jira, loaded.github):
        r = v.result
        st.markdown(f"**{icon[v.state]} {v.name}** — {'sem dados' if r is None else ('dados antigos (última busca falhou)' if v.stale else r.status)}"
                    + (f" · atualizado há {v.age_min:.0f} min" if v.age_min is not None else ""))
        if r is not None:
            st.caption(" · ".join(f"{k}: {val}" for k, val in r.stats.items() if not isinstance(val, list)))
        for m in v.messages:
            st.caption(f"• {md_esc(m)}")


def pg_config():
    for p in settings.problems:
        st.warning(p)
    _painel_sincronizacao()
    st.markdown("#### 🔑 Variáveis do .env")
    vars_ = [("EMAIL", "sim", "E-mail da conta Atlassian"), ("TOKEN", "sim", "id.atlassian.com/manage-profile/security/api-tokens"),
             ("JIRA_DOMAIN", "sim", "ex.: meuprojeto.atlassian.net"), ("BOARD_ID", "sim", "número em .../boards/34 ou rapidView=34"),
             ("JIRA_PROJECT", "sim", "sigla das issues (JH em JH-12)"), ("GITHUB_TOKEN", "sim", "github.com/settings/personal-access-tokens"),
             ("GITHUB_ORG", "não", "sobrescreve o 'org' do config.json")]
    faltando = set(settings.missing_env)
    st.dataframe(pd.DataFrame([{"Variável": k, "Status": "❌ ausente" if k in faltando else ("✅ definida" if k != "GITHUB_ORG" or settings.github.org else "—"),
                                "Obrigatória": o, "Onde obter": d} for k, o, d in vars_]),
                 hide_index=True, use_container_width=True)
    if st.button("🧪 Testar conexões"):
        ok_jira, msg_jira = setup_wizard.testar_jira(settings.jira.email, settings.jira.token, settings.jira.domain)
        (st.success if ok_jira else st.error)(f"Jira: {msg_jira}")
        ok_gh, msg_gh = setup_wizard.testar_github(settings.github.token)
        (st.success if ok_gh else st.error)(f"GitHub: {msg_gh}")
    _painel_autores_nao_mapeados()
    st.markdown("#### ⚙️ config.json")
    st.json({"github": {"org": settings.github.org, "repos": list(settings.github.repos), "lookback_days": settings.github.lookback_days},
             "regex": {"jira_key_pattern": settings.linking.jira_key_pattern, "subtask_summary_pattern": settings.linking.subtask_pattern,
                       "use_jira_key_as_canonical": settings.linking.use_jira_key_as_canonical},
             "jira": {"story_points_field": settings.jira.story_points_field or "(descoberto automaticamente)"},
             "management": vars(settings.management), "dev_mapping": settings.dev_mapping})
    with st.expander("🧪 Debug de mapeamento (User Story ↔ GitHub) — sem filtros"):
        st.markdown("**Tasks com vínculo de User Story (ID visual)**")
        deb = df_sub[["subtask_key", "subtask_code", "subtask_summary", "us_id", "canonical_id", "assignee"]].dropna(subset=["us_id"]).copy()
        deb["assignee"] = deb["assignee"].map(nome_exibicao)
        st.dataframe(deb.rename(columns={"assignee": "Dev"}), hide_index=True, use_container_width=True)
        st.markdown("**Commits sem vínculo com o Jira** (sem chave/User Story na mensagem, na PR nem na branch)")
        if raw.commits.empty:
            st.caption("Sem commits carregados.")
        else:
            sv = raw.commits[raw.commits["link_source"].isna() & (raw.commits["kind"] == "human")][["date", "repo", "author", "title", "branch_label"]].copy()
            sv["author"] = sv["author"].map(nome_exibicao)
            st.dataframe(sv.rename(columns={"author": "Autor"}), hide_index=True, use_container_width=True)


def pg_agora():
    v_now.render(m, settings.jira.domain)


def pg_pessoas():
    v_people.render(m, settings.jira.domain)


def pg_timeline():
    v_timeline.render(m, settings.jira.domain)


{"Dashboard": pg_dashboard, "Sprint": pg_sprint, "Agora": pg_agora, "Pessoas": pg_pessoas, "Timeline": pg_timeline,
 "Issues": pg_issues, "Commits": pg_commits, "Relatórios": pg_relatorios, "Configurações": pg_config}[pagina]()
