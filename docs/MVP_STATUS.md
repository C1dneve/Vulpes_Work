# MVP de acompanhamento de Sprint — estado e regras

Baseline: Moonfoxes **após a correção dos P0** (224 testes). Os P0 foram preservados (ver "Regressões" no final).
Este documento descreve o que o MVP faz **hoje**, as regras exatas e o que **não** está resolvido.

## Como executar
```bash
pip install -r requirements.txt           # versões fixadas (pandas 2.3.3, streamlit 1.55, plotly 6.6, requests 2.32)
streamlit run app.py
pytest -q                                  # suíte completa (inclui o app inteiro com Jira/GitHub simulados)
python tools/validate_real_apis.py         # validação REAL read-only (usa seu .env local; ver "Validação real")
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
| **Timeline** | Eventos: issue criada, status alterado, worklog, commit, PR aberta/revisada/mergeada, issue concluída |

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
python tools/validate_real_apis.py --only t9,t10        # só os campos novos
python tools/validate_real_apis.py --allow-jql-post     # tudo, incluindo o teste de chamadas (libera só POST /search/jql)
```
A saída (`tools/validation_output/results.json`) passa por um redator de segredos. Cada campo ausente vira "indisponível" na UI, nunca um valor inventado.

## Regressões
Os P0 continuam cobertos pelos testes originais, **sem alteração de asserções**: Commit → Subtask, Sprint própria da Subtask, Jira Key oficial, `on_main` × `delivered_via_pr`,
cache (`clear()` ≠ `reset()`) e payload inesperado. Nos arquivos de teste existentes só foram acrescentados *helpers* (rota padrão de `/field` e de `/reviews` nos fakes).

## Fora do MVP (P1/P2 restantes)
P1: página Jira ↔ GitHub dedicada; leitura de comentários (motivo de bloqueio); histórico de pontos/estimativas; changelog de Stories; feriados/expediente.
P2: autenticação/OIDC, PostgreSQL e histórico persistente/snapshots, notificações (Teams/WhatsApp/e-mail), PDFs, scheduler, CFD/gargalos, busca global.
