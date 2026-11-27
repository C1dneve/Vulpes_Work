# Development Analytics (Streamlit) — estado atual e regras


> Este documento descreve somente a baseline atual do módulo Development Analytics em Streamlit. A visão, decisões e roadmap do produto completo estão em [`DOCUMENTO_GERAL.md`](DOCUMENTO_GERAL.md); o plano de execução vigente está em [`plano/PLANO_IMPLEMENTACAO.md`](plano/PLANO_IMPLEMENTACAO.md).

A baseline anterior à evolução do MVP tinha 224 testes. A suíte atual passou com 440 testes e cobertura reportada de 85%. A comparação individual das asserções originais com a baseline ainda precisa ser documentada; a contagem maior de testes, por si só, não comprova essa equivalência.

Este documento descreve o que o MVP faz hoje, suas regras, os resultados de validação disponíveis e o que ainda não está resolvido.

## Estado da Fase 0 — evidências registradas em 27/11/2026

| Item | Situação |
|---|---|
| ADRs 001–013 | Aprovadas formalmente pelo mantenedor. ADR-014 permanece pendente. |
| Qualidade local | Ruff aprovado; mypy aprovado em 20 arquivos; 440 testes aprovados; cobertura reportada de 85%. |
| Dependências | `pip-audit` não encontrou vulnerabilidades conhecidas. |
| Docker | Build e inicialização concluídos; container saudável; processo executado como `uid=10001`. |
| Configuração | `load_settings()` retornou `ready=True`, sem variáveis obrigatórias ausentes. |
| Spike RLS | 6 testes aprovados em ambiente PostgreSQL descartável. |
| Probe de critérios de aceite | 20 issues consultadas, nenhuma falha de API e nenhuma seção formal de critérios de aceite encontrada. Resultado inconclusivo para medir a precisão do parser. |
| GitHub Actions | Execução remota #14, no commit `40dddf4` (27/11/2026), falhou no job Gitleaks (código 1). Os logs/annotations não ficaram acessíveis nesta sessão; o resultado individual da matriz de qualidade não foi confirmado. |
| Baseline de testes | O commit de referência que contém as 224 asserções não foi localizado no histórico disponível. A comparação exata continua bloqueada; não declarar equivalência pela contagem. |
| Higiene do pacote | `.coverage`, patch antigo e saídas reais foram inspecionados e retirados do índice Git na branch local; os arquivos físicos foram preservados e estão ignorados. `results.example.json` permanece como exemplo versionável. |
| Licença e distribuição | ADR-014 permanece pendente; decisão antes da Fase 5/publicação externa e não bloqueia a Fase 0. |

Os resultados locais foram executados pelo mantenedor. Eles não substituem a execução do workflow no GitHub, que também examinará o histórico completo do repositório.

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

## Regressões
A suíte atual cobre as regras de vínculo Commit → Subtask, Sprint própria da Subtask, Jira Key oficial, `on_main` × `delivered_via_pr`, cache (`clear()` ≠ `reset()`) e payload inesperado. A execução mais recente passou com 440 testes. Para declarar formalmente que as 224 asserções da baseline original foram preservadas, ainda falta comparar a suíte e os arquivos de teste com o commit de referência anterior à evolução do MVP.

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