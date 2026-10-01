# 🦊 Moonfoxes — Dashboard Jira + GitHub

Dashboard em Streamlit que cruza as **issues do Jira** com os **commits do GitHub** — em todas as branches e na main.

## O que ele faz
- **Dashboard**: KPIs da sprint, progresso diário, distribuição por status, últimas issues e últimos commits.
- **Commits**: todos os commits de todas as branches, com *em quais branches estão*, se **já estão na main** ou só em branch, PRs e commits sem vínculo com o Jira.
- **Por task**: cruza Jira × GitHub e alerta divergências (ex.: task *Concluída* sem commit na main).
- **Sprint / Issues / Relatórios**: burndown, hierarquia US → subtasks, horas por tag, esforço por dev. Nos gráficos de
  Relatórios, clique numa barra/ponto de uma pessoa para abrir os detalhes dela (tasks, horas, commits, branches).
- **Configurações**: confere o `.env`, testa as conexões e mostra o debug de mapeamento.

### MVP de acompanhamento de Sprint (novo)
- **Sprint → Stories**: por Story, responsável, status do Jira, Story Points, estimado × registrado, prazo, branches, PRs e commits, com a hierarquia
  *Story → Subtasks → Commits* e, em paralelo, *Story → Branch → PR*. Abas de **Burndown/Burnup** e **Tempo em status**.
- **Agora**: o que exige atenção neste momento (bloqueadas, atrasadas, inativas, PRs aguardando revisão, inconsistências Jira ↔ GitHub) + todos os alertas.
- **Pessoas**: o trabalho de cada pessoa (tarefas, Stories, horas, commits, branches, PRs). **Sem ranking.**
- **Timeline**: eventos cronológicos da Sprint (criação, status, worklog, commit, PR aberta/revisada/mergeada, conclusão).

Detalhes, regras, limiares e limitações conhecidas: **[`docs/MVP_STATUS.md`](docs/MVP_STATUS.md)**.

## Convenções do time (Jira ↔ GitHub)

Modelo oficial: **Branch = User Story · PR = User Story · Commit = Subtask**.

| Item | Convenção | Exemplo |
|---|---|---|
| Branch (uma por lado) | `feature/{backend ou frontend}/{CHAVE}-{USx.y}-{slug}` | `feature/backend/JH-123-US2.1-cadastro` |
| Commit | `tipo(CHAVE-DA-SUBTASK): descrição real da alteração` | `feat(JH-101): implementar validação do cadastro de cliente` |
| Pull Request | `[CHAVE-DA-STORY] USx.y — Título` | `[JH-123] US2.1 — Cadastro de cliente` |

- **Commit sem chave do Jira é inválido** (aparece como alerta em *Commits*). A descrição deve dizer o que mudou
  (`ajustes`, `fix`, `wip` são sinalizados). Merges e reverts automáticos são isentos.
- A chave do Jira é **configurável** (`regex.jira_key_pattern` no `config.json`; por padrão `{JIRA_PROJECT}-\d+`).
- **`US2.1` é o identificador visual; `JH-123` é o oficial.** Quando os dois aparecem, a chave do Jira vence. `US1.1`,
  `US1.2` e `US1.3` são User Stories **diferentes** (antes eram todas fundidas em `US1`).
- O ID visual só é reconhecido como token isolado: `status 1.2`, `bonus 2.5` e `virus 1.1` **não** viram User Story.

### O que conta como "entregue"
Um commit está **entregue** se está na branch padrão **ou** pertence a uma PR *merged* nela. Isso cobre **Squash and Merge**
(padrão do time), em que o SHA original nunca chega à `main`, e continua valendo se a branch foi apagada. Uma branch
está entregue quando existe PR merged cujo `head` é o topo atual da branch; commits empurrados depois do merge seguem
pendentes. Bots (`dependabot`, `github-actions`, `[bot]`…) e merge commits são classificados à parte e não contam como
atividade de uma pessoa.

### Filtros e sincronização
- A **sprint ativa** é selecionada automaticamente; dá para trocar. Sprint, User Stories e desenvolvedor valem para
  **todas** as telas (Jira, commits, branches, PRs, worklogs, changelog).
- Se o Jira/GitHub falhar, a tela mostra **o motivo** (ex.: falha de autenticação, limite de requisições) e, se houver,
  os últimos dados bons marcados como antigos. Falhas nunca são cacheadas. *Configurações → Sincronização* mostra o estado.
- Janela do GitHub: `github.lookback_days` (padrão 90). PRs **abertas** são sempre carregadas, por mais antigas que sejam.
- Todos os horários usam `America/Sao_Paulo`.
- *Configurações → Autores não mapeados*: vincula autores de commit sem correspondência ao colaborador do Jira.

## Setup
Não precisa mais editar arquivo nenhum na mão: ao abrir o app pela primeira vez (ou sempre que faltar alguma
variável obrigatória), uma **tela de configuração** aparece pedindo o e-mail e os tokens, testa a conexão com o
Jira e o GitHub, e já salva o `.env` sozinha.

```bash
git clone https://github.com/kakashinho/dashboard-jira-github.git && cd dashboard-jira-github
python -m venv venv && venv\Scripts\activate      # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py                               # abre a tela de configuração na primeira vez
```

Se preferir preencher o `.env` você mesmo (ex. rodando em CI), copie `.env.example` para `.env` e preencha —
o app detecta que já está tudo preenchido e não mostra a tela de configuração.

Depois de configurado, rode `python setup_config.py` de vez em quando pra atualizar a lista de autores do Jira
usada no `dev_mapping` (ver `config.json`), caso o time mude.

## De onde vem cada valor pedido na tela de configuração
| Variável | Como obter |
|---|---|
| `EMAIL` | E-mail da sua conta Atlassian |
| `TOKEN` | https://id.atlassian.com/manage-profile/security/api-tokens → **Create API token** (sem escopos) |
| `JIRA_DOMAIN` | O endereço do seu Jira, ex.: `meuprojeto.atlassian.net` |
| `BOARD_ID` | Abra o quadro no Jira: o número na URL (`.../boards/34`) |
| `JIRA_PROJECT` | A sigla das issues (`SCRUM` em `SCRUM-12`) |
| `GITHUB_TOKEN` | Veja abaixo |
| `GITHUB_ORG` *(opcional, campo extra na tela)* | Sobrescreve o `org` do `config.json` |

### Token do GitHub
- **Classic** (mais simples para repositório de organização): https://github.com/settings/tokens → escopo `repo`. Se a org usa SSO, clique em **Configure SSO → Authorize**.
- **Fine-grained**: https://github.com/settings/personal-access-tokens → *Resource owner* = a organização, selecione os repositórios e dê **Read-only** em *Contents*, *Pull requests* e *Metadata*. A org pode exigir aprovação de um administrador.

Os valores digitados na tela de configuração ficam salvos **apenas na máquina de quem está rodando o app**
(arquivo `.env` local, já listado no `.gitignore`) e nunca são enviados a mais ninguém.

## `config.json`
Define `org`, `repos`, `lookback_days`, `bot_logins` (bots extras), `regex.jira_key_pattern`,
`regex.use_jira_key_as_canonical`, `jira.story_points_field` (opcional), `management` (limiares de gestão: prazo, inatividade, PR sem revisão, etc.) e o `dev_mapping` (`"login_github": "slug-no-jira"`; a comparação ignora maiúsculas e separadores) — precisa ser atualizado manualmente sempre que
alguém entra ou sai do time. Se uma pessoa sair do grupo, os commits antigos dela no GitHub continuam existindo
no histórico normalmente — não precisa (nem dá pra) removê-la do mapeamento retroativamente.

## ⚠️ Antes de compartilhar este projeto com o time
Um `.env` com tokens reais ou a pasta `venv/` **nunca** devem sair da sua máquina. O `.gitignore` já cobre os
dois quando se usa `git`, mas um `.zip`/pasta compartilhada manualmente (Drive, WhatsApp, etc.) **não respeita o
`.gitignore` sozinho** — confira à mão antes de enviar:

- [ ] O `.zip`/pasta compartilhada **não contém** `.env` nem `venv/` (nem `__pycache__/`).
- [ ] Se algum `.env` com token real chegou a sair da sua máquina (por zip, e-mail, Drive etc.), **revogue e gere
      um novo token** — tanto no Jira (`id.atlassian.com/manage-profile/security/api-tokens`) quanto no GitHub
      (`github.com/settings/tokens` ou `.../personal-access-tokens`) — antes de continuar usando o projeto.
- [ ] Cada pessoa do time cria o próprio `.env` (pela tela de configuração) e o próprio `venv`
      (`python -m venv venv && pip install -r requirements.txt`) na máquina dela.

## Desenvolvimento e testes
```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```
Estrutura: `domain/` (regras puras: vínculo, status, fuso, texto, pessoas, prazo/esforço/bloqueio, alertas, tempo em status,
Burnup, Timeline), `services/` (Jira, GitHub, HTTP, cache, contexto de filtros, sincronização, `mgmt.py` = orquestrador das regras
de gestão), `settings.py` (`load_settings()`), `app.py` + `ui_components.py` + `views/` (interface; **não** renomear `views/` para `pages/`,
o Streamlit trataria como multipage) e
`tests/` (inclui um teste que executa o app inteiro com Jira/GitHub simulados). O CI (`.github/workflows/ci.yml`)
roda lint e testes a cada push.

## Ainda não implementado (planejado)
Página Jira ↔ GitHub dedicada, Auditoria, busca global, notificações (e-mail/Teams/WhatsApp), relatórios PDF, CFD/gargalos,
snapshots/histórico persistente (PostgreSQL), autenticação (Microsoft/Google/OIDC) e perfis DEV TEAM/MASTER. Alertas, página Pessoas,
Timeline e Burnup **já existem** (MVP; ver `docs/MVP_STATUS.md`). O diagnóstico original está em `docs/AUDITORIA.md`
(histórico: parte dele descreve o estado anterior ao MVP).
