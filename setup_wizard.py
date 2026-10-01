"""Tela de onboarding: cria o .env quando ele não existe ou está incompleto.

Pensada pra colega sem conhecimento técnico conseguir configurar o dashboard sozinho(a),
sem precisar editar nenhum arquivo na mão — só preencher um formulário e clicar em um botão.
"""

import requests
import streamlit as st
from requests.auth import HTTPBasicAuth

import ui_components as ui
from settings import ROOT, load_settings, merge_env_file, read_env

# (variável, rótulo, é_senha, texto de ajuda)
CAMPOS = [
    ("EMAIL", "E-mail da conta Atlassian", False, "O e-mail que você usa para logar no Jira."),
    ("TOKEN", "Token do Jira", True,
     "Gere em id.atlassian.com/manage-profile/security/api-tokens → Create API token (sem escopos)."),
    ("JIRA_DOMAIN", "Domínio do Jira", False, "Ex.: meuprojeto.atlassian.net (sem 'https://' na frente)."),
    ("BOARD_ID", "ID do board", False, "O número que aparece na URL do quadro no Jira, ex.: .../boards/34."),
    ("JIRA_PROJECT", "Sigla do projeto no Jira", False, "A sigla que aparece nas issues, ex.: SCRUM em SCRUM-12."),
    ("GITHUB_TOKEN", "Token do GitHub", True,
     "Classic: github.com/settings/tokens (escopo 'repo'). Fine-grained: github.com/settings/personal-access-tokens."),
]


def env_completo():
    """True se todas as variáveis obrigatórias existem (ambiente real ou .env). Não altera os.environ."""
    return load_settings().ready


def testar_jira(email, token, dominio):
    if not (email and token and dominio):
        return False, "Preencha e-mail, token e domínio primeiro."
    try:
        r = requests.get(f"https://{dominio}/rest/api/3/myself", auth=HTTPBasicAuth(email, token), timeout=15)
        if r.ok:
            return True, f"OK — conectado como {r.json().get('displayName', email)}"
        return False, f"HTTP {r.status_code} — confira e-mail, token e domínio."
    except Exception as e:
        return False, str(e)


def testar_github(token):
    if not token:
        return False, "Preencha o token do GitHub primeiro."
    try:
        r = requests.get("https://api.github.com/user", headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if r.ok:
            return True, f"OK — conectado como {r.json().get('login')}"
        return False, f"HTTP {r.status_code} — confira o token e as permissões dele na organização."
    except Exception as e:
        return False, str(e)


def _salvar_env(valores):
    """Grava só as chaves do formulário no .env, preservando o resto (comentários e outras variáveis)."""
    merge_env_file(ROOT / ".env", valores)


def tela_onboarding():
    st.markdown(
        f'<div class="mf-top"><div class="mf-brand"><img src="data:image/png;base64,{ui.logo_b64()}"/>'
        f'<h1>Moonfoxes</h1><p>Configuração inicial</p></div></div>', unsafe_allow_html=True)
    st.markdown("#### 👋 Bem-vindo! Vamos configurar o acesso ao Jira e ao GitHub")
    st.caption("Isso só precisa ser feito uma vez, nesta máquina. Os valores ficam salvos **apenas aqui**, "
               "num arquivo `.env` dentro da pasta do projeto (que já é ignorado pelo git) — nunca são "
               "enviados a mais ninguém além do Jira e do GitHub, pra confirmar que funcionam.")

    with st.form("onboarding"):
        valores = {}
        for var, rotulo, senha, ajuda in CAMPOS:
            valores[var] = st.text_input(rotulo, value=read_env(ROOT / ".env").get(var, ""),
                                         type="password" if senha else "default", help=ajuda)
        org = st.text_input("Organização do GitHub (opcional)", value=read_env(ROOT / ".env").get("GITHUB_ORG", ""),
                            help="Só preencha se quiser usar uma organização diferente da definida em config.json. "
                                 "Se deixar em branco, o app usa a organização do config.json normalmente.")
        enviado = st.form_submit_button("🧪 Testar e salvar", use_container_width=True)

    if enviado:
        faltando = [rotulo for var, rotulo, _, _ in CAMPOS if not valores[var].strip()]
        if faltando:
            st.error("Preencha os campos: " + ", ".join(faltando))
            return
        with st.spinner("Testando as conexões com o Jira e o GitHub..."):
            ok_jira, msg_jira = testar_jira(valores["EMAIL"], valores["TOKEN"], valores["JIRA_DOMAIN"])
            ok_gh, msg_gh = testar_github(valores["GITHUB_TOKEN"])
        (st.success if ok_jira else st.error)(f"Jira: {msg_jira}")
        (st.success if ok_gh else st.error)(f"GitHub: {msg_gh}")
        if ok_jira and ok_gh:
            if org.strip():
                valores["GITHUB_ORG"] = org.strip()
            _salvar_env(valores)
            st.success("Configuração salva! Carregando o dashboard...")
            st.rerun()
        else:
            st.info("Corrija os campos indicados acima e tente de novo. Nada foi salvo ainda.")

    st.markdown(ui.sidebar_footer(), unsafe_allow_html=True)
