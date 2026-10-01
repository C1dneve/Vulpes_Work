# Auditoria e status de implementação

## Problemas encontrados (todos reproduzidos antes de corrigir)

| Arquivo (original) | Problema | Risco | Situação |
|---|---|---|---|
| `git_tracker.py` | `on_main = sha in main_shas` falha com Squash/Rebase | Entrega nunca reconhecida | ✅ corrigido (entrega via PR merged) |
| `git_tracker.py` | `max_pages` 5/3/3 truncando sem avisar | Dados incompletos apresentados como completos | ✅ paginação total + janela por data |
| `git_tracker.py` | 1 listagem de commits por branch; `ahead_main` inflado após squash | Rate limit; branches "abertas" já entregues | ✅ `compare` só quando necessário |
| `git_tracker.py` | `dependabot[bot]` → `dependabotbot`; sem tratamento de bots/merges | Bots viram desenvolvedores | ✅ `kind` = human/bot/merge |
| `jira_client.py` | `maxResults=1000` sem paginação; erro → `[]` cacheado por 1h | "Sem dados" no lugar de "falha de autenticação" | ✅ paginação real + `SourceResult` + cache que não guarda falhas |
| `jira_client.py` | worklog/changelog via `expand` (máx. 20 / 100) | Horas e histórico subestimados | ✅ endpoints próprios paginados |
| `jira_client.py` | "Em análise" e "Em teste" classificados como "Pendente" | Code Review invisível; alertas falsos | ✅ `statusCategory` + refinamento por nome |
| `jira_client.py` | só Story → Sub-task | Bugs e stories sem filhos fora das métricas | ✅ hierarquia por estrutura |
| `jira_client.py` | datas cortadas em `[:10]` / `[:16]` | Sem hora nem fuso | ✅ timestamps completos em America/Sao_Paulo |
| `jira_client.py` | story só em sprint fechada virava "Sem Sprint" | Histórico de sprint perdido | ✅ usa `closedSprints` |
| `config.json` regex | `status 1.2`, `bonus 2.5`, `virus 1.1` viravam User Story | Vínculos falsos | ✅ regex com fronteira + testes |
| `config.json` regex | `US1.1`/`US1.2`/`US1.3` → `US1` | Commits vazando entre stories | ✅ ID `US{epic}.{story}` |
| `app.py` | filtros só afetavam a lista de stories; padrão "Todas" e apenas 5 stories | Telas incoerentes entre si | ✅ `Context` global; padrão = sprint ativa |
| `app.py` / `ui_components.py` | HTML dinâmico sem escape | Injeção de HTML | ✅ `esc()` por padrão, `Safe` explícito |
| `app.py` | `str.contains` interpretando regex | Erro com `(`, `[`, `*` | ✅ busca literal |
| `setup_wizard.py` | reescrevia o `.env` inteiro; `load_dotenv(override=True)` | Perda/sobrescrita de segredos | ✅ merge; ambiente real vence |
| `requirements.txt` | 45 pacotes (quase todos transitivos), `pytz` sem uso, sem `tzdata` | Instalação frágil no Windows | ✅ 7 dependências diretas |

## Status por prioridade do prompt-mestre

- **P0 (correção e confiabilidade):** implementado e testado (itens 1–14).
- **P1 (produto):** não iniciado, exceto o que o P0 exigiu (contexto global de filtros; "Autores não mapeados").
- **P2 (comunicação e análise):** não iniciado, exceto um painel básico de sincronização.
- **P3 (automação, autenticação, perfis, banco):** não iniciado.

## Limites conhecidos das correções

- Nenhuma chamada foi feita contra o Jira/GitHub reais (sem credenciais neste ambiente): tudo foi validado com respostas simuladas
  construídas a partir da documentação oficial. A primeira execução com credenciais reais é o teste que falta.
- `compare/{base}...{head}` com branches que contêm `/` no nome não foi verificado contra a API real; há tratamento de 404
  (a branch é marcada como "sem pendências verificáveis" e um aviso aparece em Sincronização).
- A detecção de commits "equivalentes" (rebase-and-merge) é heurística (mesmo autor, data e título), não `patch-id`.
- O endpoint agile `/board/{id}/issue` pode ter uma variante com paginação por token na Jira Cloud; o paginador aceita as
  duas formas (`startAt` e `nextPageToken`), mas isso só será confirmado com um board real.
