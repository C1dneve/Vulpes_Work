# Development Analytics (Streamlit) — estado atual e regras


> Este documento descreve somente a baseline atual do módulo Development Analytics em Streamlit. A visão, decisões e roadmap do produto completo estão em [`DOCUMENTO_GERAL.md`](DOCUMENTO_GERAL.md); o plano de execução vigente está em [`plano/PLANO_IMPLEMENTACAO.md`](plano/PLANO_IMPLEMENTACAO.md).

O `docs/MVP_STATUS.md` do commit de referência `8412ce8` descreve a baseline após a correção dos P0 como “224 testes”. A comparação direta do código-fonte desse commit com `a812380` encontrou 332 funções `test_*` na baseline, todas com corpos AST idênticos no estado atual; não houve remoção nem alteração dos corpos dessas funções e foram adicionadas 40 funções de teste. Há 607 nós `assert` dentro das funções de teste da baseline (608 nós `assert` no total dos arquivos de teste). Como a contagem histórica “224” não coincide com o inventário estático do próprio snapshot e não existe manifesto que identifique quais seriam esses 224 itens, esta documentação não afirma “224/224”; registra a preservação integral das funções de teste efetivamente presentes no commit de referência e a discrepância da contagem histórica.

Este documento descreve o que o MVP faz hoje, suas regras, os resultados de validação disponíveis e o que ainda não está resolvido.

## Estado consolidado da Fase 0 — evidências reexecutadas em 28/11/2026

| Item | Situação atual |
|---|---|
| Identidade Git | Clone real; branch `chore/phase-0-stabilization`, HEAD `a812380`; `origin/main` atualizado em `40dddf4`; `git fetch --all --tags --prune` concluído. Remote `origin` identificado como `C1dneve/Vulpes_Work`. |
| Histórico | Repositório não raso; 6 commits alcançáveis nas refs locais, sendo 5 commits não-merge e 1 merge commit. |
| Python 3.12.16 | `uv sync --frozen --all-groups`, Ruff, mypy, pytest e `pip-audit` aprovados; 440 testes, 85% de cobertura. |
| Python 3.13.18 | `uv sync --frozen --all-groups`, Ruff, mypy, pytest e `pip-audit` aprovados; 440 testes, 85% de cobertura. |
| Dependências | `pip-audit`: nenhuma vulnerabilidade conhecida encontrada nas duas execuções. |
| Docker Compose | `docker compose config` e `docker compose up --build -d` aprovados; container `healthy`; UID/GID `10001:10001`; `/_stcore/health` HTTP 200; `docker compose down` executado. |
| Gitleaks | Versão 8.30.1; comando `git` e comando exato do workflow (`detect --source . --log-opts="--all" --redact --exit-code 1`) executados; 5 commits examinados, ~3,62 MB, sem achados. |
| Baseline de testes | Referência `8412ce8` identificada. Os 332 corpos AST de funções `test_*` da baseline estão preservados sem diferenças; 40 funções de teste foram adicionadas. O rótulo histórico “224 testes” não corresponde ao inventário estático do snapshot; ver seção de comparação abaixo. |
| CI remoto da branch | Pendente: `chore/phase-0-stabilization` existe apenas localmente; não há ref `origin/chore/phase-0-stabilization`. A execução #14 em `40dddf4` não valida o HEAD atual. |
| ADRs | ADRs 001–013 aceitas; ADR-014 pendente e não bloqueia a Fase 0; ADRs 015/017 propostas e ADR-016 pendente para a Fase 3. |
| `app.py` | 189 linhas no HEAD `a812380`, dentro do limite de 200 descrito no Prompt Mestre. |

Os testes, ferramentas, Docker e Gitleaks desta tabela foram reexecutados pelo mantenedor em 28/11/2026, conforme saídas fornecidas nesta conversa. A CI remota da branch atual ainda não foi executada. A Fase 0 permanece aberta até a confirmação da matriz remota e a revisão/commit final. Não houve push.

## Reexecução independente nesta sessão — 27/11/2026

Os itens da tabela anterior são resultados históricos reportados pelo mantenedor. A tabela abaixo registra somente o que foi repetido nesta sessão no clone recebido; resultados bloqueados não são tratados como aprovados.

| Verificação | Resultado nesta sessão |
|---|---|
| Clone e histórico | Clone Git válido; branch de trabalho `chore/phase-0-stabilization`, baseada no `origin/main` disponível no ZIP. O `git fetch --prune origin` falhou por DNS; as refs remotas não puderam ser atualizadas. |
| Ambiente | Python 3.13.5 e uv 0.10.0. Python 3.12 não estava instalado; o workflow fixa uv 0.13.9. |
| `uv sync --frozen --all-groups` | Bloqueado por falha de DNS ao acessar `files.pythonhosted.org`; o ambiente não foi reproduzido e nenhuma dependência foi atualizada. |
| `compileall` | Aprovado para os módulos da aplicação, testes e ferramentas incluídos no comando. |
| Suíte completa com cobertura | Bloqueada na coleta: cinco módulos de interface falharam por `ModuleNotFoundError: streamlit`, ausente no ambiente. |
| Suíte reduzida com cobertura | 413 testes passaram, com 85% de cobertura no subconjunto, excluindo `test_app_smoke.py`, `test_mvp_app.py`, `test_people_view.py`, `test_timeline_view.py` e `test_ui_components.py`. Não equivale à suíte completa nem ao resultado histórico de 440 testes. |
| Comparação histórica auxiliar | O commit raiz local `8412ce8` permitiu coletar 375 casos com as mesmas cinco exclusões; todos os 375 node IDs também aparecem na suíte atual, que coleta 413 (38 adicionais). Esse commit não foi identificado como a baseline original de 224 asserções, portanto a comparação exigida continua bloqueada. |
| Ruff, mypy e `pip-audit` | Não executados: os respectivos executáveis não estão instalados no ambiente; a sincronização de dependências foi bloqueada. |
| Docker Compose | Não executado: Docker/Compose não estão instalados/disponíveis. Não há evidência nova de build, healthcheck ou usuário não-root. |
| Gitleaks | Não executado localmente: binário ausente. A execução remota #14 terminou com código 1 no job de Gitleaks; a página pública não disponibilizou logs/annotations para classificar o achado. |
| CI Python 3.12/3.13 | Workflow configurado com matriz 3.12/3.13; a execução remota #14 falhou no conjunto. O resultado detalhado dos jobs da matriz não ficou acessível, portanto não foi considerado aprovado. |

A execução remota #14 está em [`GitHub Actions`](https://github.com/C1dneve/Vulpes_Work/actions/runs/46018835837). A Fase 0 permanece **aberta** até que os bloqueios obrigatórios sejam resolvidos e comprovados. Nenhuma credencial foi usada nem chamada às APIs Jira/GitHub foi feita; houve apenas consulta pública do status do Actions e tentativa de `git fetch`, bloqueada por DNS.

## Como executar
O ambiente oficial é reproduzido por `uv.lock` em Python 3.12. Na raiz do projeto:
```bash
uv sync --frozen --all-groups
uv run streamlit run app.py
uv run pytest -q                          # suíte completa (inclui o app inteiro com Jira/GitHub simulados)
uv run python tools/validate_real_apis.py # validação REAL read-only (usa seu .env local; ver "Validação real")
```

## Telas
| Tela | O que responde |
|---|---|
| **Dashboard** | KPIs de sempre + Story Points, Estimado × Registrado, Atrasadas, Inativas |
| **Sprint → Stories** | Por Story: Jira Key, US, título, responsável, status (Jira), Subtasks concluídas/total, **Story Points**, estimado (soma das subtasks), registrado, prazo/situação, nº de branches/PRs/commits e estado de revisão das PRs. Clique numa linha: *Story → Subtasks → Commits* (cada commit só na Subtask cuja chave ele cita) e, em paralelo, *Branches* e *PRs* da Story |
| **Sprint → Progresso** | Burndown (existente) + **Burnup** (escopo × concluído, em issues e em Story Points) |
| **Sprint → Tempo em status** | Matriz task × status (Pendente/Andamento/Análise/Teste/Bloqueada) + tempo no status atual; detalhe por task com nomes reais de status |
| **Agora** | Alertas de severidade alta/média agrupados por tipo; aba com todos os alertas e filtros |
| **Pessoas** | Visão geral **em ordem alfabética** + detalhe por pessoa (Tarefas, Stories, Horas, Commits, Branches, PRs, Alertas) |
| **Timeline** | Eventos: issue criada, status alterado, worklog, commit, PR aberta/revisada/mergeada, issue concluída; avisos de dados antigos/parciais e limitações ativas das fontes |

### Filtros globais (Sprint · User Stories · Desenvolvedor)
Valem para **todas** as telas acima. Regra de design: o filtro de **pessoa** vale para as *linhas* (tasks, alertas, eventos); a **evidência**
do GitHub de uma Story (branches/PRs/commits) vem sempre do time da Sprint, senão uma PR escrita por outra pessoa sumiria e geraria
falso "Done sem PR". Com "Todas" as Sprints não há Burnup (não existe escopo único). Há testes com duas Sprints provando que nada da
Sprint 4 aparece com a Sprint 5 selecionada (e vice-versa) em Sprint, Agora, Pessoas e Timeline.

## Dados novos coletados
**Jira** (`services/jira.py`): Story Points (campo descoberto por nome em `/rest/api/3/field`; desempate pela estimativa configurada no board;
fixável em `config.json → jira.story_points_field`); dados da **própria Story** (status, responsável, due date, prioridade, pontos, datas);
prioridade; bloqueadores (`issuelinks` "is blocked by" ainda não concluídos); campo `Flagged` + quando foi marcado; eventos do campo
`Sprint` no changelog; nomes originais de status no changelog. Nenhuma chamada nova por issue: tudo sai do changelog que já era buscado
(+1 chamada `/field` por carga; +1 de configuração do board **só** se houver mais de um campo de Story Points).
**GitHub** (`services/github.py`): `requested_reviewers`/`requested_teams` e **reviews reais** (`GET /pulls/{n}/reviews`) — 1 chamada por PR
**aberta ou mergeada** (não por commit, não para PR fechada sem merge). Falha ao ler = estado **"desconhecido"**, nunca "aguardando".

## Regras (todas em `domain/`, testadas)
**Limiares** (único lugar: `config.json → management`; valores padrão): `due_soon_days=2`, `inactive_business_days=2`,
`pr_review_wait_hours=24`, `pr_old_days=5`, `sprint_ending_days=2`, `recent_days=2`. Valor inválido cai no padrão e aparece em Configurações.

* **Prazo**: Sem due date · No prazo · Próximo do prazo (faltam ≤ N dias; o próprio dia conta) · Atrasado (hoje depois do prazo) · Concluído (nunca atrasada).
  A Story sem due date própria usa o prazo mais próximo entre as Subtasks **abertas**, rotulado "(das subtasks)".
* **Estimado × registrado**: estimado e registrado vêm do Jira. **Restante**: se o Jira informa, é "(jira)"; senão, havendo estimativa, é
  `estimado − registrado` (mín. 0) rotulado "(calculado)"; sem nenhum dos dois, **—**. Soma por Story = calculada, com cobertura ("2/3" tasks com estimativa); nunca trata ausente como 0.
* **Story Points**: ausente = **—**/"indisponível"; soma só das Stories que têm pontos, e `sp_missing` diz quantas ficaram de fora.
  "Concluídos" = Stories cujo **status da própria Story no Jira** é Concluída. Em Pessoas, "SP das Stories em que atua" é contexto (uma Story compartilhada conta para cada participante), **não** pontuação individual.
* **Bloqueio**: task aberta que (a) está no status Bloqueada, (b) está *flagged* (impedimento) ou (c) tem link "is blocked by" para issue ainda aberta.
  **Motivo**: só o que o Jira comprova (link); senão "motivo não informado no Jira". Tempo bloqueado: do changelog (status/flag); links não têm data → sem tempo.
* **Inativa**: task **em andamento/análise/teste** cuja última atividade é ≥ N **dias úteis** (seg–sex, sem feriados; sexta→segunda = 1).
  Atividade = atualização da issue no Jira, mudança de status, worklog ou commit que cita a chave **da task**. *Sem commit ≠ sem atividade.*
* **PR**: `rascunho` · `aguardando_revisao` (aberta, não-rascunho, **zero** reviews de outra pessoa que não seja bot) · `comentada` · `mudancas_solicitadas` ·
  `aprovada` · `mergeada` · `fechada` · `desconhecido`. Decisão vigente = último review de cada revisor; `DISMISSED` anula; comentário não desfaz aprovação.

### Alertas (severidade fixa por regra)
| Severidade | Regras |
|---|---|
| 🔴 alta | bloqueada · atrasada · sprint vencida com itens abertos |
| 🟠 média | inativa · PR sem revisão ≥ 24h · PR antiga (≥ 5d) · mudanças solicitadas · sprint terminando · *Done sem evidência GitHub* (task BE/FE) · *Done com commits mas sem PR* · *PR mergeada + subtasks do mesmo lado ainda em andamento* · *Em análise sem PR* · *commit sem Jira Key* |
| 🟡 baixa | PR aguardando revisão (< 24h) · PR só comentada · Done sem GitHub em task sem lado de código (ex.: UXDB) |
| 🔵 info | concluída/mergeada recentemente · PR aberta sem pendência (rascunho/aprovada/desconhecida) |

Anti-falso-positivo (deliberado): regras Jira↔GitHub **desligam** com aviso se o GitHub não carregou; task criada antes da janela de `lookback_days` não é verificável;
commit da *Story* não prova a *Subtask* (regra P0); PR é da Story e respeita o **lado** (`BE`/`FE` pelo código da subtask × `backend`/`frontend` da branch) — uma PR de backend
mergeada não torna "atrasadas" as subtasks de frontend; só entram no "PR mergeada + Jira aberto" subtasks **em andamento** (não as pendentes).

### Tempo em status
Fuso `America/Sao_Paulo`; duração = tempo **decorrido** absoluto (verificado por teste através de uma mudança de horário de verão); **tempo corrido**
(24h/dia, não horário comercial — o Jira não informa expediente). Início do 1º status = criação da issue. Status atual: `agora − entrada`.
Sem transições no histórico = no status atual desde a criação. Histórico incompleto (falha parcial) = **sem tempo** (não um número errado).
Tempo depois de concluída não entra na matriz.

### Burnup
Escopo reconstruído pelos **eventos do campo `Sprint`** do Jira (entrou/saiu em tal dia); task sem evento = presente desde a criação (ou do início da sprint) — a base
de cada task (`events`/`approx`) é mostrada. Saída no **fim** de sprint encerrada = carry-over (não reduz escopo). Concluído = em "Concluída" ao fim do dia (reabertura desconta) e ainda no escopo.
A série vai até hoje (não se projeta escopo futuro constante).

## Limitações conhecidas (não escondidas)
1. **Story Points**: depende de o campo existir no Jira e de a Story estar preenchida; o histórico do *valor* dos pontos não é carregado (Burnup em pontos só reflete entrada/saída de Stories). A "conclusão" em pontos segue o status da Story no Jira, que pode atrasar em relação às subtasks.
2. **Comentários do Jira** não são lidos; motivo de bloqueio só vem de issue links. *Flagged* (impedimento) não traz motivo.
3. **Revisão de PR**: só reviews formais (não comentários soltos da conversa); revisor e o momento "pronta para revisão" não são coletados (PR rascunho→aberta conta a idade desde a criação). Reviews de bots não contam.
4. **Tempo em status** só para Subtasks/tasks avulsas (changelog de Story não é carregado). Calendário corrido; sem feriados/expediente.
5. **Dias úteis** ignoram feriados.
6. Burnup não reflete mudança do valor de pontos nem estimativas ao longo do tempo; concluídas sem data no Jira ficam fora do "concluído" (listadas).
7. Reviews = N chamadas (1 por PR aberta/mergeada na janela); não há endpoint agregado simples. Cache existente (TTL GitHub 30 min) amortiza.
8. `lookback_days` (90) limita o que o GitHub carrega; tasks mais antigas que isso não têm "Done sem evidência" avaliado.
9. A página Pessoas mostra números de trabalho (horas/commits/SP) como **contexto**; não existe e não deve existir ranking, score ou comparação de produtividade.

## Validação real (APIs de verdade)
`tools/validate_real_apis.py` ganhou duas verificações **somente leitura**: **t9** (campos do MVP no Jira: catálogo de campos, Story Points em Stories/Subtasks, `Flagged`,
`issuelinks`, `duedate`, `priority`, eventos `Sprint`/`Flagged` no changelog, status reais) e **t10** (reviews de PR: chaves da listagem, estados e formato de `/pulls/{n}/reviews`).
O t8 (contagem de chamadas) já exercita o serviço real. Rode na sua máquina (as credenciais ficam no seu `.env`; nada é enviado):
```bash
uv run python tools/validate_real_apis.py --only t9,t10        # só os campos novos
uv run python tools/validate_real_apis.py --allow-jql-post     # tudo, incluindo o teste de chamadas (libera só POST /search/jql)
```
A saída (`tools/validation_output/results.json`) passa por um redator de segredos. Cada campo ausente vira "indisponível" na UI, nunca um valor inventado.

## Probe de critérios de aceite no Jira (US-03.4)

O script `tools/probe_acceptance_criteria.py` consulta até 20 issues usando somente requisições GET e grava um relatório sanitizado em `tools/validation_output/acceptance_criteria.json`. A chave original da issue, a descrição, os nomes de pessoas, os e-mails e os tokens não são gravados no relatório.

Execução utilizada:

```powershell
uv run python tools/probe_acceptance_criteria.py --jql "project = SCRUM ORDER BY created DESC" --max 20
```

Resultado informado em 27/11/2026: 20 issues analisadas; `sem_secao=20`, `secao_vazia=0`, `ok=0`, `ok_com_itens_invalidos=0` e `falha_api=0`. Nenhuma das 20 descrições continha a seção formal “Critérios de aceite”.

Esse resultado não demonstra falha do parser: não havia critérios estruturados para ele localizar e comparar. Também não permite calcular precisão ou cobertura. Orientações de implementação (“como fazer”) podem continuar na descrição, mas devem ficar separadas dos critérios que definem o resultado esperado.

Template recomendado para adoção no Jira:

```markdown
## Critérios de aceite
- Dado [contexto]
  Quando [ação]
  Então [resultado esperado]

## Orientações de implementação
- [Como fazer, restrições técnicas ou observações]
```

A medição deve ser repetida quando as issues passarem a usar esse formato.

## Regressões e comparação da baseline histórica

A referência Git identificada é `8412ce8` (`chore: Freeze the MVP baseline after functional, automated, and real API validation.`). Foi feita uma comparação AST dos arquivos `tests/**/*.py` desse commit com `a812380`:

- Baseline `8412ce8`: 332 funções `test_*`; 607 nós `assert` dentro das funções de teste (608 nós `assert` no total dos arquivos de teste).
- Estado `a812380`: 372 funções `test_*`; 712 nós `assert` dentro das funções de teste (713 no total).
- Os corpos AST de todas as 332 funções `test_*` da baseline são idênticos nos dois commits; nenhuma função original foi removida ou alterada. Foram acrescentadas 40 funções de teste e 105 nós `assert` dentro de funções de teste.

**Ressalva de rastreabilidade:** o `docs/MVP_STATUS.md` existente dentro do próprio commit `8412ce8` registra “224 testes”, mas a árvore de código desse mesmo commit contém 332 funções `test_*` e 607 nós `assert` dentro dessas funções. Não foi encontrado manifesto/lista que explique como o número 224 foi calculado. Assim, a preservação estrutural de toda a suíte presente em `8412ce8` está comprovada; não se afirma uma correspondência literal “224/224” porque a métrica histórica não é reproduzível a partir do snapshot.

A suíte atual passou com 440 testes e 85% de cobertura em Python 3.12.16 e 3.13.18. As regras P0 continuam cobertas, incluindo Commit → Subtask, Sprint própria da Subtask, Jira Key oficial, `on_main` × `delivered_via_pr`, cache (`clear()` ≠ `reset()`) e payload inesperado.

## Roadmap além da baseline atual

O módulo Streamlit permanece preservado. A evolução do produto completo segue as fases do [`Documento Geral`](DOCUMENTO_GERAL.md): Fase 1 (fundação e piloto de atribuições), Fase 2 (Analytics persistente, sincronização e produtividade pessoal), Fase 3 (Knowledge Hub e Canais), Fase 4 (automações e IA assistiva) e Fase 5 (SaaS/expansão). Não usar a terminologia antiga P1/P2 deste documento para reclassificar o roadmap vigente.


### Evidências complementares — 27/11/2026

- Python 3.12 e 3.13: instalação limpa, Ruff, mypy, pytest (440 aprovados, 85% de cobertura) e pip-audit aprovados.
- Docker Compose: imagem construída, container iniciado, usuário não-root 10001:10001 e healthcheck HTTP 200.
- Gitleaks: varredura histórica de 4 commits e aproximadamente 3,43 MB concluída sem achados, exit code 0.
- Dez fingerprints Sourcegraph registrados individualmente em `.gitleaksignore`, após confirmação do mantenedor de que são fictícios.
- `.env` permanece ignorado e não rastreado pelo Git.
- A comparação das 224 asserções originais continua pendente.
- A validação do GitHub Actions continua pendente de execução remota.

## Revalidação do workspace recebido nesta execução — 27/11/2026

Esta seção registra uma nova execução independente, posterior às evidências herdadas acima. O pacote chegou como ZIP, mas continha metadados `.git` funcionais; portanto, foi possível inspecionar o histórico e trabalhar sobre a branch existente, sem criar histórico artificial.

### Identificação Git e comparação histórica

- `git rev-parse --is-inside-work-tree`: `true`. Repositório não raso (`git rev-parse --is-shallow-repository`: `false`), com 6 commits alcançáveis nas refs locais e nenhum objeto inalcançável reportado por `git fsck --full --no-reflogs --unreachable`.
- Branch atual: `chore/phase-0-stabilization`, HEAD `a812380` (`chore(phase-0): record validation progress and update current documentation`), um commit à frente da `main`/`origin/main` local (`40dddf4`). `origin/HEAD` aponta para `origin/main`; remote `origin` configurado como `https://github.com/C1dneve/Vulpes_Work`.
- `git fetch --prune origin` foi tentado sem credenciais, mas não conseguiu resolver `github.com` (DNS). As refs locais não foram atualizadas e não se afirma que representam o estado remoto mais recente.
- Após a extração do ZIP, `git status` listou diversos arquivos como modificados por diferenças de metadados da árvore extraída. A comparação de conteúdo (`git diff`) mostrou somente `.gitleaksignore` com diferença de finais de linha CRLF/LF; os demais arquivos rastreados não apresentaram diferenças de conteúdo. Nenhuma alteração de código preexistente foi descartada ou incluída neste registro.
- O histórico alcançável não contém o commit de referência das 224 asserções originais. Comparação auxiliar reproduzida com `pytest --collect-only`: o commit raiz disponível `8412ce8` coleta 375 node IDs com as mesmas cinco exclusões de interface; a suíte atual coleta 413, preservando os 375 IDs e acrescentando 38. Essa comparação é útil, mas **não** identifica nem comprova a equivalência da baseline original de 224 asserções.

### Verificações reexecutadas

| Verificação | Resultado nesta execução |
|---|---|
| Ambiente | Python 3.13.5; uv 0.10.0. Python 3.12 não está instalado neste ambiente. O workflow fixa uv 0.13.9. |
| `uv sync --frozen --all-groups` | **Bloqueado** por timeout de rede ao baixar `protobuf==6.33.6` de `files.pythonhosted.org`. Nenhuma dependência ou lockfile foi alterado. |
| `python -m compileall -q .` | **Aprovado**, exit code 0. |
| `pytest -q --cov --cov-report=term-missing` | **Bloqueado na coleta**: os cinco módulos de interface (`test_app_smoke.py`, `test_mvp_app.py`, `test_people_view.py`, `test_timeline_view.py`, `test_ui_components.py`) não importam porque `streamlit` não está instalado. |
| Suíte reduzida com as mesmas cinco exclusões | **413 aprovados**, 85% de cobertura, em 4,00 s. Não equivale à suíte completa. |
| Comparação de node IDs `8412ce8` × HEAD | **375/375 IDs compartilhados**; 38 IDs adicionais na suíte atual. Comparação auxiliar, não substitui a referência de 224 asserções. |
| Ruff, mypy e `pip-audit` | **Não executados**: executáveis ausentes; sincronização de dependências bloqueada. |
| Docker/Compose | **Não executado**: Docker/Compose não estão instalados/disponíveis neste ambiente. |
| Gitleaks no histórico completo | **Não executado**: binário ausente. A varredura heurística local não substitui Gitleaks. A evidência herdada de execução local em 4 commits não comprova nova varredura dos 6 commits alcançáveis deste workspace. |
| GitHub Actions / matriz Python 3.12 e 3.13 | Workflow local configurado, mas **não revalidado remotamente**. A execução #14 anteriormente reportada falhou no job Gitleaks; os logs não foram consultados nesta execução. |
| Dockerfile/Compose, YAML e TOML | Sintaxe YAML dos workflows/Compose/Dependabot e TOML do `pyproject.toml` validada por parser local; isso não substitui build nem execução Docker. |
| Fronteira do domínio | Varredura AST local não encontrou imports proibidos de UI, aplicação, serviços ou persistência dentro de `domain/`. |

### Artefatos e dados sensíveis

- `.env` e `.streamlit/secrets.toml` não estão presentes; `.env.example` é o único arquivo de ambiente versionado.
- `.coverage`, `Vulpes_Hub-revisao.patch`, `tools/validation_output/results.json` e `tools/validation_output/console.log` estão ignorados pelo Git e não foram adicionados ao commit. O `.coverage` original foi restaurado após a execução de testes; os resultados/logs operacionais contêm identificadores de issues e endereços de e-mail e devem permanecer fora de pacotes compartilhados.
- A cópia local do patch é byte a byte igual ao blob histórico de `0bd09a9`; o commit `a812380` removeu o patch do conjunto rastreado. O patch altera 14 arquivos de documentação/configuração/assets e não contém alterações de testes ou código de runtime; não foi reaplicado.
- A inspeção heurística não exibiu valores de credenciais. Ela identificou padrões de token sintéticos usados pelo teste de redação em `tests/test_logging_config.py`; isso não é uma execução de Gitleaks nem prova de ausência de segredos no histórico.

### Estado após a revalidação

A reexecução confirma a compilação e a suíte reduzida, mas não fecha instalação limpa, suíte completa, Python 3.12, Ruff, mypy, `pip-audit`, Docker, CI remoto, Gitleaks no histórico completo ou comparação das 224 asserções originais. A Fase 0 permanece **aberta**. ADRs 001–013 continuam aceitas; ADR-014 permanece pendente e não bloqueia esta fase; ADRs 015/017 são propostas e ADR-016 permanece pendente para a Fase 3. Nenhuma API real de Jira/GitHub foi chamada.


## Revalidação complementar do mantenedor — 28/11/2026

### Ambiente e qualidade local

- Windows PowerShell; `uv` instalou CPython 3.12.16 e 3.13.18.
- Em cada versão: `uv sync --frozen --all-groups`, `uv run --frozen ruff check .`, `uv run --frozen mypy domain application contracts`, `uv run --frozen pytest -q --cov --cov-report=term-missing` e `uv run --frozen pip-audit`.
- Resultado em Python 3.12.16: Ruff aprovado; mypy sem problemas em 20 arquivos; 440 testes aprovados; cobertura total 85%; pip-audit sem vulnerabilidades conhecidas.
- Resultado em Python 3.13.18: Ruff aprovado; mypy sem problemas em 20 arquivos; 440 testes aprovados; cobertura total 85%; pip-audit sem vulnerabilidades conhecidas.

### Docker

- `docker compose config`: aprovado.
- `docker compose up --build -d`: imagem construída e container iniciado.
- `docker compose ps` / inspect: estado `healthy`.
- Processo dentro do container: UID 10001, GID 10001.
- `Invoke-WebRequest http://localhost:8501/_stcore/health`: HTTP 200.
- `docker compose down`: executado; container e rede removidos.

### Gitleaks e histórico

- Gitleaks 8.30.1. O comando `gitleaks git --log-opts="--all" --redact .` terminou sem achados.
- O comando exato configurado no workflow também foi executado: `gitleaks detect --source . --log-opts="--all" --redact --exit-code 1`; terminou sem achados, examinando 5 commits e aproximadamente 3.621.229 bytes.
- `git rev-parse --is-shallow-repository` retornou `false`; `git rev-list --all --count` retornou 6 commits alcançáveis, dos quais 5 não são merge commits. A saída de Gitleaks reporta 5 commits com alterações examináveis; o merge commit não acrescenta um patch próprio.

### CI remoto e publicação

- `git fetch --all --tags --prune` terminou sem erro. `origin/main` aponta para `40dddf4`.
- A branch `chore/phase-0-stabilization` permanece local; não existe `origin/chore/phase-0-stabilization`.
- O workflow `.github/workflows/ci.yml` executa qualidade para Python 3.12 e 3.13 e Gitleaks. A execução #14 conhecida pertence a `40dddf4` em `main`, não ao HEAD `a812380`.
- A CI remota do HEAD atual continua não verificada. Para executar o workflow nessa branch será necessário publicar a branch; isso exige autorização explícita. Não houve push nem PR.

### Working tree e arquivos para commit

- `core.autocrlf=true`. O `git status` lista vários arquivos como modificados e exibe avisos LF/CRLF; `git diff --ignore-space-at-eol --name-only` identifica apenas `README.md`, `CHANGELOG.md` e `docs/MVP_STATUS.md` como diferenças de conteúdo relevantes nesta atualização.
- Preparar somente esses três arquivos. Não usar `git add -A`; não alterar globalmente `core.autocrlf`; não executar `reset`, `restore`, `clean` ou renormalização em massa.
- A atualização documental desta seção não equivale ao commit final. Como a CI remota da branch ainda está pendente, qualquer commit antes dessa evidência deve ser explicitamente parcial, com mensagem diferente da mensagem de conclusão.
