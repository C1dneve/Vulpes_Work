"""Página Configurações e seus painéis auxiliares.

A página recebe dados e ações por parâmetros, sem ler variáveis globais de app.py.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import streamlit as st

from domain.people import nome_exibicao, suggest_matches, unmapped_authors
from domain.text import md_esc
from settings import Settings
from views.context import PageContext

SaveMapping = Callable[[Path, str, str], None]
ClearSync = Callable[[str | None], None]
TestJira = Callable[[str, str, str], tuple[bool, str]]
TestGitHub = Callable[[str], tuple[bool, str]]


def _txt(value: object) -> str:
    """Converte uma célula para texto sem exibir None/NaN."""
    return "" if value is None or (not isinstance(value, (list, tuple)) and pd.isna(value)) else str(value)


def _painel_autores_nao_mapeados(
    context: PageContext,
    save_mapping: SaveMapping,
    clear_sync: ClearSync,
) -> None:
    st.markdown("#### 👤 Autores não mapeados")
    st.caption("Autores de commits (humanos) cujo login/e-mail do GitHub não está ligado a ninguém do Jira. Nada é "
               "vinculado automaticamente: confirme a sugestão e clique em Vincular (grava em `dev_mapping` no config.json).")
    unm = unmapped_authors(context.github_commits)
    if unm.empty:
        st.success("Todos os autores humanos estão mapeados.")
        return
    slugs = sorted(context.jira_slugs, key=nome_exibicao)
    for i, row in unm.iterrows():
        login, nome = _txt(row["author_login"]), _txt(row["author_name"])
        suggestions = suggest_matches(login or None, nome or None, slugs)
        c1, c2, c3 = st.columns([2, 2.2, .8])
        c1.markdown(f"**GitHub:** {md_esc(nome or login)}  \n`{md_esc(login or 'sem login')}` · {md_esc(_txt(row['author_email']))} · {row['commits']} commit(s)")
        options = [slug for slug, _ in suggestions] + [slug for slug in slugs if slug not in [item for item, _ in suggestions]]
        choice = c2.selectbox(
            "Colaborador do Jira",
            options,
            key=f"unm_sel_{i}",
            format_func=lambda value, _suggestions=tuple(item for item, _ in suggestions): (
                nome_exibicao(value) + (" (sugestão)" if value in _suggestions else "")
            ),
        )
        if c3.button("Vincular", key=f"unm_btn_{i}", disabled=not options):
            save_mapping(context.settings.config_path, login or nome, choice)
            clear_sync("github")
            st.rerun()


def _painel_sincronizacao(context: PageContext) -> None:
    st.markdown("#### 🔄 Sincronização")
    icon = {"ok": "🟢", "partial": "🟡", "stale": "🟠", "error": "🔴"}
    for source in (context.loaded.jira, context.loaded.github):
        result = source.result
        st.markdown(
            f"**{icon[source.state]} {source.name}** — "
            f"{'sem dados' if result is None else ('dados antigos (última busca falhou)' if source.stale else result.status)}"
            + (f" · atualizado há {source.age_min:.0f} min" if source.age_min is not None else "")
        )
        if result is not None:
            st.caption(" · ".join(f"{key}: {value}" for key, value in result.stats.items() if not isinstance(value, list)))
        for message in source.messages:
            st.caption(f"• {md_esc(message)}")


def render(
    context: PageContext,
    *,
    save_mapping: SaveMapping,
    clear_sync: ClearSync,
    testar_jira: TestJira,
    testar_github: TestGitHub,
) -> None:
    """Renderiza Configurações preservando textos, widgets e chaves existentes."""
    settings: Settings = context.settings
    for problem in settings.problems:
        st.warning(problem)
    _painel_sincronizacao(context)
    st.markdown("#### 🔑 Variáveis do .env")
    variables = [
        ("EMAIL", "sim", "E-mail da conta Atlassian"),
        ("TOKEN", "sim", "id.atlassian.com/manage-profile/security/api-tokens"),
        ("JIRA_DOMAIN", "sim", "ex.: meuprojeto.atlassian.net"),
        ("BOARD_ID", "sim", "número em .../boards/34 ou rapidView=34"),
        ("JIRA_PROJECT", "sim", "sigla das issues (JH em JH-12)"),
        ("GITHUB_TOKEN", "sim", "github.com/settings/personal-access-tokens"),
        ("GITHUB_ORG", "não", "sobrescreve o 'org' do config.json"),
    ]
    missing = set(settings.missing_env)
    st.dataframe(
        pd.DataFrame([
            {
                "Variável": key,
                "Status": "❌ ausente" if key in missing else ("✅ definida" if key != "GITHUB_ORG" or settings.github.org else "—"),
                "Obrigatória": required,
                "Onde obter": help_text,
            }
            for key, required, help_text in variables
        ]),
        hide_index=True,
        use_container_width=True,
    )
    if st.button("🧪 Testar conexões"):
        ok_jira, msg_jira = testar_jira(settings.jira.email, settings.jira.token, settings.jira.domain)
        (st.success if ok_jira else st.error)(f"Jira: {msg_jira}")
        ok_github, msg_github = testar_github(settings.github.token)
        (st.success if ok_github else st.error)(f"GitHub: {msg_github}")
    _painel_autores_nao_mapeados(context, save_mapping, clear_sync)
    st.markdown("#### ⚙️ config.json")
    st.json({
        "github": {"org": settings.github.org, "repos": list(settings.github.repos), "lookback_days": settings.github.lookback_days},
        "regex": {
            "jira_key_pattern": settings.linking.jira_key_pattern,
            "subtask_summary_pattern": settings.linking.subtask_pattern,
            "use_jira_key_as_canonical": settings.linking.use_jira_key_as_canonical,
        },
        "jira": {"story_points_field": settings.jira.story_points_field or "(descoberto automaticamente)"},
        "management": vars(settings.management),
        "dev_mapping": settings.dev_mapping,
    })
    with st.expander("🧪 Debug de mapeamento (User Story ↔ GitHub) — sem filtros"):
        st.markdown("**Tasks com vínculo de User Story (ID visual)**")
        debug = context.subtasks[["subtask_key", "subtask_code", "subtask_summary", "us_id", "canonical_id", "assignee"]].dropna(
            subset=["us_id"]
        ).copy()
        debug["assignee"] = debug["assignee"].map(nome_exibicao)
        st.dataframe(debug.rename(columns={"assignee": "Dev"}), hide_index=True, use_container_width=True)
        st.markdown("**Commits sem vínculo com o Jira** (sem chave/User Story na mensagem, na PR nem na branch)")
        if context.raw_commits.empty:
            st.caption("Sem commits carregados.")
        else:
            unlinked = context.raw_commits[
                context.raw_commits["link_source"].isna() & (context.raw_commits["kind"] == "human")
            ][["date", "repo", "author", "title", "branch_label"]].copy()
            unlinked["author"] = unlinked["author"].map(nome_exibicao)
            st.dataframe(unlinked.rename(columns={"author": "Autor"}), hide_index=True, use_container_width=True)
