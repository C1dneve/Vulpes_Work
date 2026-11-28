"""Vulpes Work • Dashboard Jira + GitHub."""
import pandas as pd
import streamlit as st
from PIL import Image

import setup_wizard
import ui_components as ui
from application.use_cases import BuildManagement, BuildScope
from domain import statuses as S
from domain import timeutil
from domain.people import nome_exibicao
from services import sync
from services.context import Bundle, Context, default_sprint, sprint_options, stories_in_sprint
from services.logging_config import configure_logging
from settings import load_settings, save_dev_mapping
from views.context import PageContext
from views.git_traceability import GitTraceability
from views.modals import ModalContext
from views.navigation import build_page_actions
from views.sprint_helpers import SprintAnalytics

configure_logging()

_icone = ui.ASSETS / "favicon.png"
st.set_page_config(page_title="Vulpes Work • Jira + GitHub", page_icon=Image.open(_icone) if _icone.exists() else "🦊",
                   layout="wide", initial_sidebar_state="expanded")
ui.apply_theme()

settings = load_settings()
# Tela de onboarding: se faltar alguma variável obrigatória, pede os tokens numa tela amigável.
if not settings.ready:
    setup_wizard.tela_onboarding()
    st.stop()



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
scope = BuildScope().execute(raw, ctx)
df_meta, df_com, df_br, df_pr, df_wl, df_cl = scope.items, scope.commits, scope.branches, scope.prs, scope.worklogs, scope.changelog
known_issue_keys = set(df_sub["subtask_key"]) | set(df_stories["story_key"])

# Regras de gestão do MVP (prazo, esforço, bloqueio, inatividade, alertas, tempo em status, Timeline, Burnup) sobre o MESMO contexto.
_jira_stats = loaded.jira.result.stats if loaded.jira.result is not None else {}
_agora = timeutil.now().floor("min")
# Memo: só recalcula quando muda a carga (fetched_at), o filtro, os limiares ou o minuto — cliques de UI não repagam o cálculo.
_mkey = (loaded.jira.result.fetched_at if loaded.jira.result is not None else None,
         loaded.github.result.fetched_at if loaded.github.result is not None else None, loaded.github.state, ctx, settings.management, _agora)
if st.session_state.get("_mgmt_key") != _mkey:
    st.session_state["_mgmt"] = BuildManagement(clock=timeutil.now).execute(
        raw,
        ctx,
        settings.management,
        now=_agora,
        github_ok=loaded.github.result is not None,
        github_since=_agora - pd.Timedelta(days=settings.github.lookback_days),
        history_unknown=set(_jira_stats.get("changelog_partial") or []),
        github_partial=loaded.github.state == "partial",
        github_stale=loaded.github.stale,
    )
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

# Contexto explícito compartilhado pelas páginas já extraídas. O contrato será
# ampliado conforme as próximas telas forem migradas na US-02.2.
page_context = PageContext(
    settings=settings,
    loaded=loaded,
    management=m,
    github_commits=gd.commits,
    jira_slugs=_slugs_jira,
    subtasks=df_sub,
    stories=df_stories,
    raw_commits=raw.commits,
    scoped_items=df_meta,
    scoped_commits=df_com,
    scoped_branches=df_br,
    scoped_prs=df_pr,
    scoped_worklogs=df_wl,
)


git_traceability = GitTraceability(
    stories=df_stories,
    subtasks=df_sub,
    commits=raw.commits,
    branches=raw.branches,
    prs=raw.prs,
    known_keys=known_issue_keys,
)


sprint_analytics = SprintAnalytics(
    stories=df_stories,
    sprints=df_sprints,
    context=ctx,
    worklogs=df_wl,
    changelog=df_cl,
    scoped_items=df_meta,
)
modal_context = ModalContext(
    page=page_context,
    return_counts=retornos,
    slug_by_display_name=NOME_PARA_SLUG,
    task_commits=git_traceability.commits_for_task,
    story_references=git_traceability.story_references,
    task_code=git_traceability.task_code,
)


# ---------------------------------------------------------------- navegação
page_actions = build_page_actions(
    page_context,
    sprint=sprint,
    sprint_stories=scope.stories,
    git_traceability=git_traceability,
    sprint_analytics=sprint_analytics,
    modal_context=modal_context,
    save_mapping=save_dev_mapping,
    clear_sync=sync.clear,
    testar_jira=setup_wizard.testar_jira,
    testar_github=setup_wizard.testar_github,
)
page_actions[pagina]()
