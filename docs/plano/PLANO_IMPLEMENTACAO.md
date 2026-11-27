# Vulpes Hub — Plano de Implementação: Fases, Épicos e User Stories

Versão 1.0 · 25/11/2026 · Consolida o Plano Mestre v2.0 e as respostas às 38 perguntas de alinhamento. As decisões técnicas estão no documento separado «Vulpes Hub — Registro de Decisões Arquiteturais (ADRs)».

## 1. Como ler este documento

Este documento passa a ser o **guia de execução**. O Plano Mestre v2.0 continua como catálogo de referência, mas onde houver conflito, vale o que está aqui.

**Estrutura:** Fase → Épico → User Story (US) → tarefas técnicas.

**IDs estáveis:** FASE n · EP-nn (épico) · US-nn.m (user story) · ADR-nnn (decisão técnica) · PA-n (premissa a confirmar) · R-n (risco). Nenhum ID carrega prioridade; a prioridade é um campo.

**Prioridade (MoSCoW):** **Must** = a fase não termina sem isso · **Should** = entra se a capacidade permitir · **Could** = primeiro a sair.

**Tamanho (esforço de uma pessoa):** **P** ≈ até 2 dias · **M** ≈ 3 a 5 dias · **G** ≈ 1 a 2 semanas. Uma US maior que G deve ser quebrada antes de entrar em sprint.

**Critérios de aceite:** formato Dado / Quando / Então. Quando uma US tem vários cenários, cada um aparece em uma linha.

**Planejamento em ondas:** as Fases 0, 1 e 2 estão detalhadas até o nível de tarefa. A Fase 3 está em nível de US. As Fases 4 e 5 estão em nível de épico e de US-chave, e devem ser refinadas ao final da fase anterior, com o que se aprendeu.

## 2. Decisões consolidadas

Resumo das respostas às perguntas de alinhamento (P1 a P38). A coluna «Origem» indica a pergunta.

| Tema | Decisão | Origem |
| --- | --- | --- |
| Núcleo do produto | Plataforma de gestão de entregas: atribuição → critérios → evidência → revisão → Jira. O dashboard atual vira o módulo Development Analytics | P1 |
| Público da v1 | Vários times da mesma empresa ou instituição; arquitetura preparada para várias organizações | P2 |
| Equipe | 5 a 9 pessoas; fases de 6 a 8 semanas, ajustadas à capacidade | P3, P38 |
| Distribuição | Uma instalação por organização via Docker Compose primeiro; SaaS multi-tenant depois | P4 |
| Hierarquia | Organização → Comunidade (contém Projetos e Times) → Time → Canal. Projeto = 1 board Jira + N repositórios | P5 |
| Canais | Fase 1: thread de comentários na atribuição. Fase 3: canais por time, criados pelo Master. DMs e grupos: só depois | P6 |
| Acesso entre times | Só aos recursos dos times de que é membro explícito | P7 |
| Master delegado | Tudo na comunidade, exceto integrações da organização e gestão de outros Masters | P8 |
| Perfis | Fase 1: só Master e DEV TEAM. Fase 2: perfis = conjuntos nomeados de permissões de um catálogo fixo | P9 |
| Autorização | RBAC + ACL por recurso, em uma função central, negando por padrão | P10 |
| Dados do Jira por time | O Master define quais projetos Jira cada time vê dentro do Vulpes. OAuth por usuário fica como opção futura | P11 |
| Aprovação | Qualquer Master da comunidade (central ou delegado) aprova, com fila visível e prazo (SLA) | P12 |
| Estados da atribuição | Rascunho → Atribuída → Em andamento → Em revisão → Ajustes solicitados → Aprovada → Concluída (confirmada no Jira); mais Cancelada. Mapeamento configurável para os status do Jira | P13 |
| Issue obrigatória | Fase 1: sempre exige issue existente. Fase 2: o Vulpes cria a issue. Atribuição sem issue só se houver demanda. Vínculo N:N com regra de 1 por atribuição | P14 |
| Critérios de aceite | Seção da descrição da issue, com checklist em Markdown seguindo um template | P15 |
| Mudança de critério | Cria nova versão; o Master aceita ou rejeita; nada é sobrescrito | P16 |
| Evidências | Manuais + automáticas (PR mergeada, checks, commits). Vínculo critério → teste automatizado fica para fase futura | P17 |
| Hierarquia e dependências | Fase 2, com detecção de ciclos | P18 |
| Fonte da verdade | Tabela fixa na v1; conflitos vão para uma fila do Master | P19 |
| Escrita no Jira | Fase 1: só a transição de status após aprovação. Fase 2: criar issue e comentar | P20 |
| Credenciais | Tokens por organização, criptografados. OAuth Atlassian e GitHub App quando houver SaaS | P21 |
| Atualização de dados | Fase 1: polling incremental. Fase 2: webhooks + reconciliação | P22 |
| Infraestrutura mínima | Aplicação + PostgreSQL; fila no próprio Postgres. Redis adiado | P23 |
| Interface | React + TypeScript + Vite nos módulos novos. Streamlit permanece como Development Analytics, lendo do novo banco, até migrar | P24 |
| Multi-tenancy | tenant\_id + Row-Level Security desde o início; sem tela de administração multi-organização | P25 |
| Tempo real | SSE; WebSocket só quando o chat existir | P26 |
| Python | 3.12 (testar também 3.13) | P27 |
| Notificações | Fase 1: in-app + e-mail. Fase 2: o canal que o time já usa | P28 |
| Chat | Simples, na Fase 3. Reavaliar Mattermost ou Matrix antes de começar | P29 |
| Presença, leitura, «digitando» | Opt-in, e só quando houver chat | P30 |
| Áudio e vídeo | Última fase, embutindo Jitsi ou LiveKit | P31 |
| Conhecimento | Markdown + Mermaid + anexos com permissões. ADRs com aprovação do Master. Diagramas: Mermaid → Excalidraw → diagrams.net | P32 |
| IA, ordem de entrega | Assistente somente leitura → sugestões com aprovação → agente isolado só depois de avaliações de qualidade e segurança | P33 |
| IA, provedores e dados | Híbrido configurável, desligado por padrão, com política de dados por organização. Mensagens de canais só com opt-in; privadas nunca. Auditoria guarda entradas, chamadas de ferramenta e saídas | P34 |
| Dados pessoais | Retenção configurável por organização, com padrões documentados. Exportação e exclusão desde a Fase 1 | P35 |
| Licença | Source-available (BSL ou similar). Licença específica a definir (PA-2) | P36 |
| Formato do plano | Fases → épicos → user stories (Dado/Quando/Então) → tarefas técnicas. ADRs separados | P37 |

## 3. Premissas e pendências a confirmar

O que não foi respondido ou que depende de fora do código foi registrado como premissa. Cada uma tem prazo para confirmação.

| ID | Premissa | Confirmar até |
| --- | --- | --- |
| PA-1 | O canal de notificação da Fase 2 não foi informado. Assume-se **Microsoft Teams** (o README já o lista como planejado). Slack entra depois pelo mesmo contrato de notificação | Fim da Fase 1 |
| PA-2 | «Source-available» exige uma licença concreta (por exemplo BSL 1.1 com data de conversão, ou ELv2). Ela não é «open source» pela definição da OSI e deve passar por parecer jurídico antes de publicar o código | Fim da Fase 0 |
| PA-3 | Provedor de login (OIDC) da Fase 1: Microsoft Entra ID e/ou Google, configurável | Semana 1 da Fase 1 |
| PA-4 | Equipe de 5 a 9 pessoas. Esperado: pelo menos 1 pessoa forte em backend Python, 1 em frontend e 1 cuidando de produto e qualidade | Antes da Fase 0 |
| PA-5 | O time vai **adotar o template de critérios de aceite** nas issues do Jira (ação de processo, não de código). Responsável: Master | Semana 4 da Fase 1 |
| PA-6 | Jira Cloud (atlassian.net). Jira Server e Data Center estão fora do escopo | Fase 0 |
| PA-7 | Prazos padrão de retenção de dados (usuários desativados, mensagens, logs) precisam de validação jurídica e de LGPD | Fim da Fase 1 |
| PA-8 | Ambiente de self-hosted: Linux com Docker Compose. Requisitos mínimos de CPU e memória serão medidos na Fase 1 | Fim da Fase 1 |

## 4. Contradições do Plano Mestre e como foram resolvidas

| # | Contradição | Resolução |
| --- | --- | --- |
| 1 | A seção P1-SEC-03 lista papéis futuros (Owner, PM, Viewer, Auditor), mas a decisão E-27 define só dois papéis | Só Master e DEV TEAM. Perfis personalizados são conjuntos de permissões (Fase 2). Os papéis extras foram removidos |
| 2 | «Workspace», «Comunidade», «Projeto» e «Time» usados sem mapeamento | Hierarquia única (seção 5.3). O termo «Workspace» deixa de existir |
| 3 | Seções 1–17 descrevem um dashboard; a seção 20 descreve uma plataforma de colaboração | O núcleo é a gestão de entregas. O analytics é um módulo (decisão I-59) |
| 4 | Chat completo (bloco F) × princípio de evitar complexidade prematura | Chat em camadas: comentários na atribuição (Fase 1), canais por time (Fase 3), DMs e extras (Fase 5). Vídeo por último |
| 5 | Presença e leitura (F-40) × «pessoa não é ranking» | Opt-in, só com chat, e nenhuma métrica derivada de presença |
| 6 | Só o Master aprova (B-10) × risco de gargalo | Qualquer Master da comunidade aprova, com fila e SLA. O SLA é indicador de processo, não de pessoa |
| 7 | O schema da P1-12 não tem comunidades, mensagens, atribuições, critérios nem evidências | O modelo de dados cresce por fase, com um ERD por contexto (ADR-004) |
| 8 | Atribuição não é issue, mas B-06 trata como 1:1 | Vínculo N:N no modelo, com regra de 1 issue por atribuição na v1 |
| 9 | H-50 pede fonte da verdade configurável por campo | Tabela fixa na v1, configurável depois, mais fila de conflitos (ADR-007) |
| 10 | C-12 atualiza critérios automaticamente × H-51 proíbe sobrescrever | Critério ganha nova versão; o Master aceita ou rejeita (US-14.3) |
| 11 | Redis e Celery no plano × self-hosted simples | Só PostgreSQL. Redis e Celery entram por gatilho medido (ADR-003) |
| 12 | Tokens no .env × várias organizações | Tokens por organização, criptografados; o assistente de .env é aposentado (US-12.1) |
| 13 | IDs com prioridade embutida; itens duplicados | IDs estáveis; duplicados fundidos em épicos |
| 14 | A seção 22 (pendências) ficava no fim | Virou ADRs e premissas (PA-n) |
| 15 | PWA × aplicativo nativo | PWA na Fase 3. Nativo só se houver demanda |
| 16 | LGPD tratada como «depois» | Retenção, exportação e exclusão entram na Fase 1 (EP-21) |

## 5. Visão e escopo

### 5.1 Problema e proposta de valor

Hoje o trabalho se espalha entre Jira (o que fazer), GitHub (o que foi feito) e conversas (o que foi combinado). Quem aprova uma entrega precisa juntar tudo à mão e confiar na memória. O Vulpes Hub conecta essas pontas em um fluxo único: cada atribuição tem critérios de aceite, cada critério tem evidências ligadas ao código real, e a aprovação do Master é registrada e refletida no Jira de forma confirmada.

### 5.2 Usuários

- **Master central:** administra a organização, integrações e delegações.
- **Master delegado:** administra uma comunidade (membros, times, atribuições, revisão), sem tocar nas integrações da organização.
- **DEV TEAM:** executa atribuições, anexa evidências, responde a ajustes.

### 5.3 Hierarquia e glossário

| Termo | Significado |
| --- | --- |
| Organização | Entidade que contrata ou instala o produto. Dona das integrações e da política de dados |
| Comunidade | Agrupamento dentro da organização (ex.: uma área ou disciplina). Contém Projetos e Times |
| Projeto | 1 board Jira + N repositórios GitHub + convenções. Fica dentro de uma comunidade |
| Time | Grupo de pessoas dentro da comunidade. Uma pessoa pode estar em vários |
| Canal | Espaço de conversa de um time (Fase 3). Criado só pelo Master |
| Atribuição | Unidade de trabalho gerenciada pelo Vulpes. Relacionada a uma issue Jira, mas não é a issue |
| Critério | Condição de aceite da atribuição. Tem origem (Jira ou Vulpes) e versão |
| Evidência | Prova ligada a um critério (manual ou automática) |
| Revisão | Rodada de avaliação do Master sobre uma entrega |

### 5.4 Fluxo central (o que a Fase 1 entrega)

1. O Master cria a atribuição a partir de uma issue Jira existente.
2. Os critérios são importados da descrição da issue; o Master pode acrescentar os seus.
3. O DEV TEAM trabalha; commits e PRs do GitHub aparecem como evidência sugerida.
4. O DEV anexa as demais evidências, critério por critério, e envia para revisão.
5. Um Master da comunidade avalia cada critério e aprova ou devolve com comentários.
6. Se devolveu, o DEV ajusta e reenvia (nova rodada, histórico preservado).
7. Se aprovou, o Vulpes pede a transição no Jira e só marca «Concluída» depois de confirmá-la.
8. Tudo fica na auditoria, com notificações por e-mail e dentro do produto.

### 5.5 Fora do escopo da v1

Chat completo, vídeo, wiki colaborativa em tempo real, agente de código, multi-organização ativa, colaboradores externos, aplicativo nativo, outros provedores (GitLab, Bitbucket), WhatsApp.

## 6. Papéis e permissões da v1

Somente **Master** e **DEV TEAM** são papéis padrão. O Master delegado é o papel Master com escopo limitado a uma comunidade. Toda checagem é feita no backend pela função central de autorização (ADR-005).

| Ação | DEV TEAM | Master delegado | Master central |
| --- | --- | --- | --- |
| Ver atribuições e dashboards dos seus times | Sim | Sim (comunidade) | Sim |
| Comentar, anexar evidência, enviar para revisão | Sim | Sim | Sim |
| Criar e editar atribuições e critérios complementares | Não | Sim (comunidade) | Sim |
| Aprovar ou devolver entregas | Não | Sim (comunidade) | Sim |
| Gerenciar membros e times | Não | Sim (comunidade) | Sim |
| Definir quais projetos Jira cada time vê | Não | Sim (comunidade) | Sim |
| Configurar convenções e limiares da comunidade | Não | Sim | Sim |
| Ver a auditoria | Não | Sim (comunidade) | Sim |
| Delegar ou remover Masters | Não | Não | Sim |
| Configurar integrações da organização | Não | Não | Sim |
| Exportar ou excluir dados da organização | Não | Não | Sim |

A criação de canais (Fase 3) é exclusiva do Master. Perfis personalizados (Fase 2) combinam permissões de um catálogo fixo e nunca ultrapassam o que o Master que os cria possui.

## 7. Roadmap

| Fase | Nome | Duração | Objetivo | Critério de saída |
| --- | --- | --- | --- | --- |
| 0 | Fundação | 4 semanas | Base reproduzível, segura e testável, sem mudar o comportamento do dashboard atual | Dashboard rodando em Docker; CI com tipagem e segurança; `app.py` reduzido; ADRs aceitos; licença definida |
| 1 | Núcleo vertical | 8 semanas (10 a 12 com 5 pessoas) | Um time-piloto executa o ciclo completo | Demonstração de ponta a ponta do fluxo da seção 5.4, com login, auditoria e e-mail |
| 2 | Histórico e fluxo | 8 semanas | Histórico persistente, sincronização robusta, atribuições avançadas, acesso completo | **Release 1.0:** vários times usando; analytics lendo do banco; webhooks; perfis e convites |
| 3 | Conhecimento e comunicação | 8 semanas | Contexto e conversa perto do trabalho; busca com permissões; PWA | Canais, documentos, ADRs e busca em uso; app instalável |
| 4 | IA e automações | 6 a 8 semanas | IA assistiva, auditável e controlada | Assistente somente leitura e automações aprovadas em uso, com avaliações no CI |
| 5 | Expansão | Em ondas | Multi-organização, externos, chat avançado, diagramas, vídeo, agente | Definido ao final da Fase 4 |

**Prazo total até o fim da Fase 4:** cerca de 8 a 10 meses, conforme a capacidade real (9 pessoas ficam no início da faixa, 5 pessoas no fim).

**Marcos:** fim da Fase 1 = piloto interno (alfa) · fim da Fase 2 = Release 1.0 (vários times) · fim da Fase 3 = Release 1.5 · fim da Fase 4 = Release 2.0.

**Regra de ajuste de capacidade:** com 5 pessoas, trabalhe no teto de duração e corte os itens Could e Should de cada fase antes de estender o prazo. Com 9 pessoas, é possível paralelizar frentes (backend, frontend e analytics) e ficar perto de 6 semanas nas Fases 1 e 2.

## 8. FASE 0 — Fundação (4 semanas)

**Objetivo:** transformar o projeto atual em uma base estável, reproduzível e segura, sem alterar o comportamento do dashboard.

**Critério de saída:** o dashboard atual roda via `docker compose up`; o CI roda lint, tipagem, testes e varredura de segredos; os 224 testes da baseline original são preservados com as mesmas asserções; `app.py` é só composição; ADR-001 a ADR-013 estão aceitos ou ajustados; a licença definitiva está escolhida (ADR-014).

**Registro de situação em 26/11/2026:** o mantenedor autorizou manter temporariamente todos os direitos reservados, sem conceder licença de uso a terceiros. Essa decisão provisória não substitui a escolha da licença definitiva nem conclui a US-03.2; o critério de licença permanece pendente até parecer jurídico.

**Registro de aprovação em 27/11/2026:** o mantenedor aprovou formalmente as ADRs-001 a ADR-013. A ADR-014 permanece expressamente excluída dessa aprovação e continua pendente; não realizar trabalho jurídico nesta fase.

**Estado da validação:** em 26/11/2026, a suíte principal passou com 440 testes e cobertura reportada de 85%; Ruff, mypy e `pip-audit` também passaram. O container foi iniciado, ficou saudável e executou como usuário não-root (`uid=10001`). Em 27/11/2026, o spike isolado de RLS passou em 6 testes e o probe de critérios de aceite leu 20 issues do Jira sem falhas de API, mas nenhuma tinha a seção formal esperada; portanto, a precisão do parser ainda não pôde ser medida. O GitHub Actions só poderá ser confirmado após o push.

**Pendências de encerramento:** ainda falta comparar as 224 asserções da baseline original com a suíte atual, confirmar o workflow no GitHub Actions (Python 3.12 e 3.13 e histórico completo) e resolver a ADR-014 antes de qualquer distribuição do projeto. A aprovação das ADRs 001–013 e a aprovação técnica dos testes não encerram essas pendências.

### EP-01 — Higiene do repositório e do runtime (Must · G)

- **US-01.1** Como mantenedor, quero README e documentação com nome e links corretos, para que alguém novo instale sem confusão. **P**
  - Aceite: Dado o README, quando alguém segue o passo a passo, então instala e abre o app sem nenhuma menção ao nome antigo nem à URL antiga.
  - Aceite: Dado o `docs/AUDITORIA.md`, então os itens já corrigidos aparecem marcados como histórico.
- **US-01.2** Como mantenedor, quero que artefatos operacionais sejam sanitizados e ignorados (saídas de validação, `.env`, caches), para não vazar dados ao compartilhar. **P**
  - Aceite: Dado o repositório, quando o Gitleaks roda no CI, então passa sem achados.
  - Aceite: Dado um zip gerado pelo procedimento documentado, então ele não contém `.env` nem saídas reais de validação.
- **US-01.3** Como mantenedor, quero Python 3.12 (com 3.13 na matriz), lockfile e política de atualização de dependências. **M**
  - Aceite: Dado o CI, quando roda, então testa 3.12 e 3.13 com as versões do lockfile; uma instalação limpa reproduz o mesmo ambiente.
- **US-01.4** Como mantenedor, quero um CHANGELOG com versionamento semântico. **P**
  - Aceite: Dado um release, então existe uma entrada com mudanças, correções e quebras de compatibilidade.
- **US-01.5** Como mantenedor, quero análises de qualidade e segurança no CI (ruff, checagem de tipos, cobertura, pip-audit, Gitleaks, Dependabot). **M**
  - Aceite: Dado um PR com erro de tipo ou vulnerabilidade crítica, então o CI falha e o merge é bloqueado.

### EP-02 — Containerização e modularização do código atual (Must · G)

- **US-02.1** Como mantenedor, quero rodar o dashboard em Docker, para ter ambientes idênticos. **M**
  - Aceite: Dado `docker compose up`, quando abro o endereço local, então vejo o dashboard igual ao atual, com segredos vindos de variáveis de ambiente.
  - Aceite: Dado a imagem, então roda sem privilégios de root e tem healthcheck.
  - Tarefas: Dockerfile enxuto, `.dockerignore` e Compose principal com somente o serviço `app`. PostgreSQL não integra o runtime do dashboard na Fase 0; aparece apenas no Compose isolado do spike US-03.3.
- **US-02.2** Como desenvolvedor, quero o `app.py` reduzido a composição e navegação, para facilitar manutenção. **G**
  - Aceite: Dado a suíte atual, quando roda após a extração para `views/`, então os 224 testes passam sem alterar asserções.
  - Aceite: Dado o `app.py`, então é um módulo de composição e navegação, com alvo aproximado de 150 linhas e limite de até 200 linhas quando a justificativa estiver documentada.
  - Registro estático de 26/11/2026: `app.py` possui 189 linhas. O total se justifica por manter no ponto de entrada apenas a configuração da página/tema, onboarding, sincronização, sidebar/filtros, construção do contexto e roteamento; as telas estão extraídas para `views/`.
  - Nota: `views/` não deve ser renomeado para `pages/` (o Streamlit trataria como multipágina).
- **US-02.3** Como desenvolvedor, quero uma camada de aplicação com casos de uso e injeção de dependências, para testar sem Streamlit. **G**
  - Aceite: Dado um caso de uso (por exemplo, sincronizar fontes), quando executado em teste com Jira e GitHub simulados, então não importa Streamlit nem faz chamadas reais.
  - Tarefas: contratos de entrada e saída (Pydantic) para issue, story, subtask, commit, branch, PR e resultado de sincronização; relógio e cache injetáveis.
- **US-02.4** Como Master, quero configuração validada, para que erro de configuração apareça claro. **M**
  - Aceite: Dado um `config.json` ou `.env` inválido, quando o app inicia, então falha com mensagem que indica o campo e o motivo.
- **US-02.5** Como operador, quero logs estruturados sem segredos e proteção contra sincronização duplicada. **M**
  - Aceite: Dado dois pedidos simultâneos de sincronização da mesma fonte, então apenas uma execução ocorre e a outra aguarda ou reaproveita o resultado.
  - Aceite: Dado qualquer log, então não contém token nem cabeçalho de autorização.

### EP-03 — Decisões e provas de conceito (Must · M)

- **US-03.1** Como equipe, quero registrar e aceitar as ADRs 001 a 013 (ou ajustá-las), para começar com decisões explícitas. **P**
  - Aceite: Dado cada ADR, então tem status, alternativas e gatilho de revisão.
  - **Resultado em 27/11/2026:** ADRs 001 a 013 aprovadas formalmente pelo mantenedor. A ADR-014 não está incluída nessa aprovação.
- **US-03.2** Como organização, quero escolher a licença source-available específica, com parecer jurídico (ADR-014). **M**
  - Aceite: Dado a decisão, então `LICENSE`, cabeçalhos e política de contribuição estão publicados e o texto sobre uso self-hosted e SaaS está claro.
- **US-03.3** Como equipe, quero provar o isolamento por Row-Level Security com PostgreSQL e SQLAlchemy antes de adotá-lo (spike isolado de 3 dias); a integração por requisição com FastAPI fica para a Fase 1. **P**
  - Aceite: Dado dois tenants, quando consulto como o tenant A, então nunca recebo dados do B, nem via ORM nem via SQL direto.
  - **Resultado em 27/11/2026:** spike executado localmente; 6 testes passaram. O ambiente descartável foi encerrado após a execução. A integração com o aplicativo principal continua prevista para a Fase 1.
- **US-03.4** Como equipe, quero medir se o template de critérios de aceite é lido corretamente em 20 issues reais do Jira (spike). **P**
  - Aceite: Dado o conjunto de issues, então há um relatório com a taxa de leitura correta, as falhas e o template final proposto.
  - **Resultado em 27/11/2026:** leitura de 20 issues concluída, sem falhas de API. As 20 issues não tinham a seção formal “Critérios de aceite”; algumas podem conter orientações de implementação na descrição, mas isso não equivale a critérios estruturados. O resultado confirma o estado atual dos dados, mas não permite calcular a precisão do parser. Repetir a medição depois que o time adotar um template.
- **US-03.5** Login OIDC no Streamlit (`st.login`): **retirada da Fase 0 e transferida para a semana 1 da Fase 1**, após a escolha do provedor. Não é critério de encerramento da Fase 0.

## 9. FASE 1 — Núcleo vertical (8 semanas; 10 a 12 com 5 pessoas)

**Objetivo:** um time-piloto executa o ciclo completo da seção 5.4, com login, permissões, auditoria e notificações.

**Critério de saída (demonstração ao vivo):** o Master cria uma atribuição a partir de uma issue; o DEV anexa evidências; o Master devolve com comentários por critério; o DEV ajusta; o Master aprova; o Jira recebe a transição e o Vulpes mostra «Concluída» somente após a confirmação. Tudo aparece na auditoria. Um usuário de outro time não enxerga nada disso.

**Organização interna da fase:**

- **Etapa 1A (semanas 1 a 4):** EP-10 plataforma base, EP-11 identidade e acesso, EP-12 integrações, EP-20 analytics com login, início do EP-21.
- **Etapa 1B (semanas 5 a 8):** EP-13 atribuições, EP-14 critérios, EP-15 evidências, EP-16 revisão, EP-17 saída para o Jira, EP-18 colaboração, EP-19 experiência inicial.

**Linha de corte com 5 pessoas:** adiar para a Fase 2 as US marcadas Should e Could (US-18.4, US-19.3, US-20.2) e as preferências de e-mail além do opt-out.

### EP-10 — Plataforma base (Must · G)

**Dependências:** Fase 0 concluída.

- **US-10.1** Como desenvolvedor, quero um monorepo com `apps/backend` (FastAPI), `apps/frontend` (React + TypeScript + Vite) e `apps/analytics` (Streamlit), para evoluir cada módulo de forma independente. **M**
  - Aceite: Dado `docker compose up`, então sobem API, web, analytics e PostgreSQL, todos com healthcheck verde.
- **US-10.2** Como desenvolvedor, quero PostgreSQL com migrações versionadas e isolamento por organização, para que nenhum dado vaze entre tenants. **G**
  - Aceite: Dado qualquer tabela de negócio, então tem `tenant_id` e política de Row-Level Security.
  - Aceite: Dado dois tenants, quando um teste consulta como o tenant A, então nunca recebe linhas do B (testes negativos em todas as entidades).
  - Aceite: Dado o CI, então aplica as migrações do zero e faz rollback da última.
  - Tarefas: SQLAlchemy, Alembic, sessão com contexto de tenant, ERD do núcleo (organização, comunidade, time, projeto, usuário, membro, atribuição, critério, evidência, revisão, integração, auditoria).
- **US-10.3** Como operador, quero fila e worker no próprio PostgreSQL, para executar sincronizações e envios fora da requisição. **G**
  - Aceite: Dado um job que falha, então tenta de novo com backoff e jitter e, ao esgotar as tentativas, vai para a lista de falhas com motivo e ação de reprocessar.
  - Aceite: Dado o mesmo job entregue duas vezes, então o efeito ocorre uma vez (chave de idempotência).
- **US-10.4** Como desenvolvedor de frontend, quero contratos de API versionados e um cliente TypeScript gerado, para não haver divergência entre backend e frontend. **M**
  - Aceite: Dado uma mudança de contrato, quando o CI gera o cliente, então falha se o resultado difere do que está versionado.
  - Aceite: Dado qualquer resposta, então o envelope distingue sucesso, ausente, parcial, dados antigos, erro externo e erro interno.
- **US-10.5** Como operador, quero observabilidade mínima, para diagnosticar falhas sem expor segredos. **M**
  - Aceite: Dado uma requisição, então os logs em JSON trazem `request_id` e, em jobs, `sync_id`.
  - Aceite: Dado `/health/live` e `/health/ready`, então refletem API, banco e worker sem expor credenciais.
  - Aceite: Dado uma exceção no Sentry (ou GlitchTip), então tokens e dados pessoais estão mascarados.
- **US-10.6** Como usuário, quero uma interface consistente, para entender o estado do sistema sem ambiguidade. **G**
  - Aceite: Dado qualquer tela de dados, então existem estados padronizados: carregando, parcial, dados antigos, erro, sem dados e sem permissão; erro nunca é exibido como vazio.
  - Aceite: Dado o tema claro e escuro, então todos os componentes mantêm contraste adequado.
  - Tarefas: tokens de design, componentes base (botão, formulário, tabela, painel lateral, cartão), strings centralizadas (PT-BR primeiro), checklist de acessibilidade.

### EP-11 — Identidade, organizações e acesso (Must · G)

**Dependências:** US-10.2.

- **US-11.1** Como usuário, quero entrar com minha conta corporativa (OIDC), para não ter outra senha. **G**
  - Aceite: Dado um usuário sem sessão, quando acessa qualquer rota, então é levado ao login.
  - Aceite: Dado um token inválido ou expirado, então o backend responde 401, sem nenhum dado.
  - Aceite: Dado o logout, então a sessão é encerrada no servidor.
- **US-11.2** Como Master central, quero criar comunidades e times dentro da organização. **M**
  - Aceite: Dado a hierarquia Organização → Comunidade → Time, então cada nível pertence a exatamente um nível acima.
- **US-11.3** Como Master, quero convidar pessoas por e-mail e colocá-las em vários times, para refletir a realidade do trabalho. **M**
  - Aceite: Dado um usuário nos times A e B, quando acessa uma atribuição do time C, então recebe 403 sem revelação de que ela existe.
  - Aceite: Dado um convite aceito, então o usuário entra com o papel DEV TEAM nos times indicados.
- **US-11.4** Como Master, quero que as permissões sejam aplicadas de forma uniforme, para não depender de cada tela. **G**
  - Aceite: Dado qualquer endpoint, então chama a função central `can(usuário, ação, recurso)`, que nega por padrão.
  - Aceite: Dado a matriz da seção 6, então existe um teste parametrizado (papel × ação × escopo) cobrindo todas as combinações.
- **US-11.5** Como Master central, quero delegar um Master para uma comunidade. **M**
  - Aceite: Dado um Master delegado, quando tenta configurar integrações da organização ou gerenciar outros Masters, então é negado.
  - Aceite: Dado um Master delegado, quando age dentro da comunidade delegada, então tem os poderes do Master naquele escopo; em outra comunidade, nenhum.
- **US-11.6** Como Master, quero uma trilha de auditoria, para saber quem fez o quê. **M**
  - Aceite: Dado login, mudança de membros ou papéis, configuração e decisões de aprovação, então cada evento grava autor, ação, entidade, data e valores antes e depois (sem segredos).
  - Aceite: Dado o registro de auditoria, então só aceita inserção; ninguém edita ou apaga pela aplicação.

### EP-12 — Integrações Jira e GitHub (Must · G)

**Dependências:** EP-10, EP-11. Reaproveita `services/` e `domain/` existentes.

- **US-12.1** Como Master central, quero cadastrar e testar as conexões Jira e GitHub da organização, com tokens criptografados, para aposentar o `.env`. **M**
  - Aceite: Dado um token salvo, quando consulto a API ou a tela, então o segredo nunca volta completo.
  - Aceite: Dado o banco, então o token está criptografado em repouso e a chave fica fora do banco.
  - Aceite: Dado «testar conexão», então mostra sucesso ou o motivo da falha (autenticação, permissão, rede).
- **US-12.2** Como Master, quero cadastrar Projetos (board Jira + repositórios + convenções de chave) em uma comunidade. **M**
  - Aceite: Dado um Projeto, então a chave do Jira e o padrão de branch usam as regras existentes de vínculo.
- **US-12.3** Como Master, quero definir quais projetos Jira cada time vê. **M**
  - Aceite: Dado um time sem acesso ao projeto X, quando busca issues ou atribuições, então não encontra nada de X, nem pela busca.
- **US-12.4** Como sistema, quero sincronizar Jira e GitHub de forma incremental, para ter dados atualizados sem recarregar tudo. **G**
  - Aceite: Dado um checkpoint, quando a sincronização roda, então busca só o que mudou (JQL por `updated`; GitHub por `since`, com ETag quando houver).
  - Aceite: Dado falha da API, então o último dado bom é mantido e marcado como antigo, e a falha nunca vira «sem dados».
  - Aceite: Dado limite de requisições atingido, então a execução espera ou reagenda e registra o motivo.
  - Aceite: Dado um campo ausente na API, então fica como indisponível, nunca como zero.
- **US-12.5** Como Master, quero ver o estado das sincronizações e disparar uma manual. **M**
  - Aceite: Dado a tela, então mostra última execução, duração, erros e avisos por fonte, e o botão «sincronizar agora» é exclusivo do Master.

### EP-13 — Atribuições (Must · G)

**Dependências:** EP-11, EP-12.

- **US-13.1** Como Master, quero criar uma atribuição a partir de uma issue Jira existente, com responsável principal, participantes e time. **M**
  - Aceite: Dado uma issue dos projetos visíveis, quando crio a atribuição, então fica ligada a ela (modelo N:N, com regra de 1 issue por atribuição).
  - Aceite: Dado uma issue que já tem atribuição ativa, então o sistema avisa e impede duplicar.
  - Aceite: Dado qualquer tipo de issue disponível no projeto, então pode receber atribuição.
- **US-13.2** Como usuário, quero que a atribuição siga estados claros. **M**
  - Aceite: Dado os estados Rascunho → Atribuída → Em andamento → Em revisão → Ajustes solicitados → Aprovada → Concluída (e Cancelada), então só as transições previstas são aceitas, cada uma registrando autor, data e motivo quando exigido.
  - Aceite: Dado o estado «Concluída», então só é atingido após a confirmação da transição no Jira (US-17.2).
- **US-13.3** Como Master, quero mapear estados do Vulpes para status do Jira por projeto. **M**
  - Aceite: Dado o mapeamento, então a transição de saída usa o status configurado; sem mapeamento, o sistema avisa antes de permitir aprovação.
- **US-13.4** Como usuário, quero listar e abrir atribuições com filtros (time, pessoa, estado, sprint) e painel lateral. **M**
  - Aceite: Dado a lista, então só mostra atribuições dos meus times; o painel lateral abre sem perder o filtro.
- **US-13.5** Como Master, quero cancelar uma atribuição com motivo. **P**
  - Aceite: Dado o cancelamento, então o motivo é obrigatório e o histórico é preservado.

### EP-14 — Critérios de aceite (Must · G)

**Dependências:** EP-13, resultado do spike US-03.4, PA-5.

- **US-14.1** Como Master, quero que os critérios sejam importados da seção «Critérios de aceite» da descrição da issue (checklist em Markdown), para não redigitar. **M**
  - Aceite: Dado uma issue com a seção no template, então cada item vira um critério com origem «Jira».
  - Aceite: Dado uma issue sem a seção, então a atribuição fica com o aviso «sem critérios» e não vai para revisão enquanto o Master não adicionar critérios ou registrar uma justificativa.
  - Aceite: Dado um item mal formatado, então o sistema indica a linha e não o descarta em silêncio.
- **US-14.2** Como Master, quero adicionar critérios complementares só no Vulpes. **P**
  - Aceite: Dado um critério complementar, então fica marcado com origem «Vulpes» e nunca é sobrescrito pela importação.
- **US-14.3** Como responsável, quero que mudanças de critério no Jira criem uma nova versão para decisão, para nada mudar sem ninguém ver. **G**
  - Aceite: Dado uma atribuição em andamento, quando o critério C1 muda no Jira, então surge a versão v2 pendente e os responsáveis são notificados com o que mudou.
  - Aceite: Dado a v2 pendente, quando o Master aceita, então a v2 passa a vigorar e as evidências ligadas à v1 ficam marcadas «precisa revalidar».
  - Aceite: Dado a v2 pendente, quando o Master rejeita, então a v1 permanece e a divergência fica registrada.
  - Aceite: Dado uma atribuição em revisão, quando o critério muda, então a revisão em curso não é invalidada até o Master decidir sobre a nova versão.
- **US-14.4** Como Master, quero definir os requisitos de evidência de cada critério (tipo e obrigatoriedade). **M**
  - Aceite: Dado os tipos captura de tela, teste, PR, documento e outro, então cada critério pode exigir um ou mais deles.

### EP-15 — Evidências (Must · G)

**Dependências:** EP-14, EP-12.

- **US-15.1** Como DEV, quero anexar evidência manual (link, texto ou arquivo) a um critério. **M**
  - Aceite: Dado um arquivo fora dos tipos ou tamanho permitidos, então é rejeitado com motivo.
  - Aceite: Dado o download, então usa cabeçalhos seguros e só é permitido a quem vê a atribuição.
  - Tarefas: armazenamento atrás de uma interface (volume local na v1, S3-compatível depois).
- **US-15.2** Como DEV, quero que commits, PRs e checks do GitHub apareçam como evidência sugerida. **M**
  - Aceite: Dado uma PR vinculada à atribuição, então aparece com número, estado (aberta, aprovada, mergeada) e data, e o DEV confirma a qual critério ela se liga.
  - Aceite: Dado que o GitHub falhou, então o estado aparece como «desconhecido», nunca como «sem PR».
- **US-15.3** Como DEV e Master, quero ver a completude das evidências. **P**
  - Aceite: Dado a atribuição, então mostra, por critério, se as evidências exigidas estão completas.

### EP-16 — Revisão e aprovação (Must · G)

**Dependências:** EP-14, EP-15.

- **US-16.1** Como DEV, quero enviar a entrega para revisão. **M**
  - Aceite: Dado critérios sem evidência obrigatória, quando tento enviar, então o sistema lista o que falta e não envia.
- **US-16.2** Como Master, quero uma fila de revisão da comunidade, com prazo (SLA). **M**
  - Aceite: Dado dois Masters, quando A assume uma revisão, então B vê «em análise por A» e pode reassumir com registro.
  - Aceite: Dado o SLA configurável excedido, então aparece um alerta de processo na fila (não ligado a pessoas).
- **US-16.3** Como Master, quero aprovar ou devolver por critério, com comentários. **M**
  - Aceite: Dado uma devolução, então a atribuição vai para «Ajustes solicitados» com justificativa obrigatória e comentário por critério.
  - Aceite: Dado várias rodadas, então o histórico preserva cada uma (r1, r2, ...) com decisões e comentários.
- **US-16.4** Como DEV, quero reenviar após os ajustes vendo o que mudou. **M**
  - Aceite: Dado uma nova rodada, então destaca evidências novas ou alteradas e os comentários ainda não resolvidos.

### EP-17 — Saída confiável para o Jira (Must · G)

**Dependências:** EP-12, EP-13, EP-16. Ver ADR-007.

- **US-17.1** Como Master, quero uma tabela clara de quem manda em cada campo. **P**
  - Aceite: Dado a tela de referência, então mostra: Jira = chave, status oficial, Story Points e critério original; Vulpes = critérios complementares, evidências, responsáveis da atribuição e aprovação; GitHub = commits e PRs.
- **US-17.2** Como Master, quero que a aprovação gere a transição no Jira de forma confirmada. **G**
  - Aceite: Dado o Jira indisponível, quando o Master aprova, então a atribuição fica «Aprovada (transição Jira pendente)» e nunca «Concluída».
  - Aceite: Dado o Jira de volta, então a transição ocorre uma única vez e a atribuição passa a «Concluída» após ler o status no Jira.
  - Aceite: Dado um workflow que exige campo ou condição, então a falha é mostrada com a ação manual indicada, e o estado fica «falhou».
  - Tarefas: outbox transacional (decisão e intenção na mesma transação), chave de idempotência, worker, reconciliação por leitura do status.
- **US-17.3** Como Master, quero ser avisado quando o Jira mudou por fora durante a revisão. **M**
  - Aceite: Dado que o status mudou no Jira fora do Vulpes, então aparece um alerta na atribuição e nada é sobrescrito. A fila geral de conflitos chega na Fase 2.

### EP-18 — Colaboração e notificações (Must e Should · G)

- **US-18.1** (Must) Como usuário, quero uma thread de comentários na atribuição, com menções e anexos. **M**
  - Aceite: Dado um comentário com @usuário, então a pessoa recebe notificação, e só se tiver acesso à atribuição.
  - Aceite: Dado edição ou exclusão, então o histórico e a auditoria preservam a versão anterior.
- **US-18.2** (Must) Como usuário, quero notificações dentro do produto, quase em tempo real (SSE). **M**
  - Aceite: Dado eventos de atribuído a mim, menção, revisão pendente, devolvida e aprovada, então aparecem em segundos, com marca de lida ou não lida.
- **US-18.3** (Must) Como usuário, quero e-mails transacionais com opt-out por tipo. **M**
  - Aceite: Dado um e-mail enviado, então fica registrado (entrega ou falha) e respeita o opt-out.
- **US-18.4** (Should) Como usuário, quero ver os alertas atuais (bloqueada, atrasada, PR sem revisão) dentro da atribuição, reaproveitando as regras de alertas existentes. **M**

### EP-19 — Experiência inicial (Must e Should · M)

- **US-19.1** (Must) Como DEV, quero uma tela «Meu trabalho» com minhas atribuições por estado, ajustes pendentes e prazos. **M**
  - Aceite: Dado que entro no sistema, então vejo primeiro o que exige a minha ação agora.
- **US-19.2** (Must) Como Master, quero uma «Fila do Master» com revisões pendentes, aprovações com transição pendente e divergências. **M**
  - Aceite: Dado que sou Master, então vejo a fila ordenada por idade, com o SLA visível.
- **US-19.3** (Should) Como usuário, quero navegação com seletor de comunidade, breadcrumbs e layout responsivo. **M**

### EP-20 — Development Analytics integrado (Must e Could · M)

**Dependências:** US-03.5, EP-11, EP-12.

- **US-20.1** (Must) Como usuário, quero acessar o Development Analytics com o mesmo login e as conexões da organização, sem `.env`. **G**
  - Aceite: Dado um usuário sem permissão na comunidade, quando abre o analytics, então não vê dados dela.
  - Aceite: Dado a suite de testes atual, então continua passando com as mesmas asserções, e as regras de vinculação, entrega, cache e dados antigos permanecem iguais.
- **US-20.2** (Could) Como usuário, quero links entre a atribuição e a Story correspondente no analytics, e vice-versa. **P**

### EP-21 — Privacidade e dados (Must · M)

- **US-21.1** Como Master central, quero retenção configurável por tipo de dado, com padrões documentados. **M**
  - Aceite: Dado cada tipo (logs, auditoria, comentários, anexos, usuários desativados), então há um prazo padrão documentado (validação em PA-7) e a retenção é aplicada por rotina agendada.
- **US-21.2** Como Master central, quero exportar os dados da organização e de um usuário. **M**
  - Aceite: Dado o pedido, então gera arquivo em formato aberto (JSON e CSV) com o que a pessoa ou a organização tem no sistema, sem segredos.
- **US-21.3** Como Master central, quero excluir ou anonimizar um usuário desativado ou os dados de uma organização. **M**
  - Aceite: Dado a anonimização, então o histórico de entregas e a auditoria são preservados sem dados pessoais identificáveis, e a ação é auditada.
- **US-21.4** Como organização, quero o registro das finalidades de tratamento de dados e um aviso de privacidade no produto. **P**

## 10. FASE 2 — Histórico e fluxo (8 semanas) → Release 1.0

**Objetivo:** guardar histórico, tornar a sincronização robusta, completar o fluxo de atribuições e a administração de acesso, para que vários times usem o produto.

**Critério de saída (Release 1.0):** vários times de uma organização usam o produto; o Development Analytics lê do banco, com histórico, e dá os mesmos resultados de antes nos testes de equivalência; webhooks funcionam com reconciliação; o Master cria issues pelo Vulpes; há perfis personalizados, convites completos e notificações no canal do time; backup e restauração foram testados.

**Pré-requisito:** PA-1 confirmada (canal de notificação). No fim da fase, executar o spike do chat (EP-40) para destravar a Fase 3.

**Linha de corte:** se a capacidade for menor, mover EP-36 (alertas e convenções) e US-30.4 e US-30.5 (métricas de fluxo e comparação de sprints) para o início da Fase 3.

### EP-30 — Histórico persistente (Must · G)

- **US-30.1** Como sistema, quero persistir snapshots diários e eventos de domínio, para reconstruir o passado. **G**
  - Aceite: Dado o mesmo evento recebido em duas sincronizações, então há um único registro, com origem e hora de coleta.
  - Aceite: Dado um campo não obtido, então o snapshot grava «indisponível», nunca zero.
  - Eventos cobertos: mudança de status, entrada e saída de sprint, mudança de estimativa e pontos, PR aberta, revisada e mergeada, commit detectado.
- **US-30.2** Como usuário do analytics, quero que as telas leiam do banco, para abrir rápido e ter histórico, sem mudar o resultado. **G**
  - Aceite: Dado dados gravados de uma sprint real, quando comparo a saída antiga (API direta) com a nova (banco), então são iguais ou cada diferença está explicada e aprovada.
  - Aceite: Dado a suíte de testes existente, então continua passando.
- **US-30.3** Como Master, quero histórico de Story Points e estimativas e changelog de Stories, para fechar limitações conhecidas do MVP. **M**
  - Aceite: Dado um histórico incompleto, então a lacuna é sinalizada e não vira duração falsa.
- **US-30.4** (Should) Como Master, quero métricas de fluxo: cycle time, lead time, throughput, aging WIP e CFD. **G**
  - Aceite: Dado cada métrica, então mostra a definição de início e fim usada, o período, a fonte e as limitações.
  - Aceite: Dado qualquer gráfico, então nenhum ranking ou comparação individual de produtividade é exibido.
- **US-30.5** (Should) Como Master, quero comparar sprints (escopo adicionado, carry-over, throughput). **M**

### EP-31 — Sincronização robusta (Must · G)

- **US-31.1** Como sistema, quero receber webhooks do Jira e do GitHub, para reagir a eventos sem esperar o polling. **G**
  - Aceite: Dado um webhook sem assinatura válida, então é rejeitado.
  - Aceite: Dado um webhook válido, então o evento bruto é guardado, deduplicado e processado de forma assíncrona.
- **US-31.2** Como sistema, quero reconciliação periódica, para corrigir eventos perdidos, duplicados ou fora de ordem. **M**
  - Aceite: Dado um evento perdido, quando a reconciliação roda, então o estado local converge com a origem sem duplicar eventos.
- **US-31.3** Como operador, quero controle de limite de requisições e de concorrência por provedor e organização. **M**
  - Aceite: Dado o limite restante informado pela API, então a concorrência e a próxima execução se ajustam.
- **US-31.4** Como Master, quero uma fila de conflitos entre Jira e Vulpes, para resolver divergências sem sobrescrita silenciosa. **G**
  - Aceite: Dado um campo alterado nos dois lados desde o último valor sincronizado, então aparece na fila com os três valores (base, Vulpes, Jira).
  - Aceite: Dado a resolução, então fica registrada com autor e motivo, e os responsáveis são notificados.
- **US-31.5** Como Master, quero uma central de sincronização completa. **M**
  - Aceite: Dado a tela, então mostra execuções, falhas e a lista de jobs mortos, e permite reprocessar uma fonte, um repositório ou um job.

### EP-32 — Atribuições avançadas (Must e Should · G)

- **US-32.1** (Must) Como Master, quero dividir uma atribuição em subatribuições por equipe, com progresso agregado. **G**
  - Aceite: Dado subatribuições, então o progresso da principal reflete as filhas e a aprovação final continua sendo da principal.
- **US-32.2** (Must) Como Master, quero dependências entre atribuições, com detecção de ciclos. **G**
  - Aceite: Dado A depende de B e B depende de C, quando tento fazer C depender de A, então é rejeitado mostrando o caminho do ciclo.
  - Aceite: Dado uma dependência concluída, então o time dependente é notificado.
- **US-32.3** (Should) Como Master, quero regras de reabertura após aprovação e de replanejamento. **M**
  - Aceite: Dado a reabertura, então exige motivo, registra quem reabriu e define o efeito no Jira (transição de volta, com confirmação).

### EP-33 — Escrita ampliada no Jira (Must · G)

- **US-33.1** Como Master, quero criar uma issue pelo Vulpes, com formulário dinâmico por tipo e projeto, e criar a atribuição em seguida. **G**
  - Aceite: Dado campos obrigatórios do Jira (lidos do metadata do projeto), quando faltam, então o formulário não permite enviar.
  - Aceite: Dado um template com a seção de critérios, então a issue já nasce no padrão exigido.
  - Aceite: Dado falha do Jira, então o rascunho é preservado e o estado fica «pendente» até confirmar.
- **US-33.2** (Should) Como Master, quero comentar no Jira a partir de eventos do Vulpes (aprovada, devolvida), por comunidade. **M**
  - Aceite: Dado o mesmo evento processado duas vezes, então há um único comentário no Jira.

### EP-34 — Acesso completo (Must e Should · G)

- **US-34.1** (Must) Como Master, quero perfis personalizados como conjuntos nomeados de permissões de um catálogo fixo. **G**
  - Aceite: Dado um perfil, então pode ser criado, clonado, versionado e atribuído, e nunca concede mais do que o Master que o criou possui.
- **US-34.2** (Must) Como Master, quero ACL por recurso com herança Organização → Comunidade → Time → Recurso. **G**
  - Aceite: Dado permissões em conflito, então «negar» vence «permitir», e a regra está documentada e testada.
- **US-34.3** (Must) Como Master, quero convites com link, validade, escopo e aprovação configurável. **M**
  - Aceite: Dado um convite expirado ou revogado, então não concede acesso.
- **US-34.4** (Must) Como Master, quero tratar a saída de um membro: desativar, transferir atribuições, revisar permissões. **M**
  - Aceite: Dado um membro desativado, então suas atribuições abertas ficam sem responsável e aparecem para o Master reatribuir, e as sessões são encerradas.
- **US-34.5** (Should) Como usuário, quero revogar sessões e dispositivos e usar o MFA do provedor. **M**

### EP-35 — Notificações no canal do time e resumos (Should · M)

- **US-35.1** Como Master, quero enviar notificações ao Microsoft Teams (PA-1), por um contrato de provedor que aceite outros canais. **M**
  - Aceite: Dado cada envio, então fica registrado (entregue, falhou) e as credenciais são segregadas por comunidade.
- **US-35.2** Como Master, quero resumos diários e semanais programados (fuso configurável). **M**
  - Aceite: Dado o resumo, então traz bloqueios, PRs paradas e a fila de revisão, sem duplicar envios.
- **US-35.3** Como usuário, quero preferências por evento e time e horário de silêncio. **M**

### EP-36 — Alertas e convenções (Should · G)

- **US-36.1** Como Master, quero alertas com ciclo de vida (novo, reconhecido, em tratamento, resolvido, reaberto), atribuição, comentário, soneca e deduplicação. **G**
  - Aceite: Dado o mesmo problema reaparecendo, então reabre o alerta anterior em vez de criar outro.
- **US-36.2** Como Master, quero convenções de branch, commit e PR por comunidade, projeto e repositório, com severidade de aviso e exceções autorizadas. **G**
  - Aceite: Dado uma exceção, então exige autor, motivo e validade, e entra na auditoria.
- **US-36.3** Como Master, quero calendário de expediente e feriados por comunidade. **M**
  - Aceite: Dado o calendário, então dias úteis, inatividade e prazos o usam; sem calendário, a tela diz que o cálculo é só de segunda a sexta.

### EP-37 — Segurança e operação (Must · G)

- **US-37.1** Como organização, quero antimalware nos uploads. **M**
  - Aceite: Dado um arquivo infectado, então vai para quarentena e o usuário recebe aviso.
- **US-37.2** Como operador, quero backup e restauração testados e um procedimento de atualização self-hosted com rollback. **G**
  - Aceite: Dado um backup, quando restauro em ambiente limpo, então o sistema sobe com os dados e arquivos; o teste é repetido periodicamente.
- **US-37.3** Como operador, quero endurecimento da aplicação: limite de taxa, CORS restrito, CSP e cabeçalhos de segurança, varredura básica (ZAP). **M**
- **US-37.4** Como equipe, quero testes E2E do fluxo central (Playwright), testes de contrato com Jira e GitHub (fixtures sanitizadas) e testes de carga básicos. **G**
  - Aceite: Dado o CI, então roda o fluxo «criar, evidenciar, devolver, aprovar, confirmar no Jira» com APIs simuladas.

## 11. FASE 3 — Conhecimento e comunicação (8 semanas)

**Objetivo:** colocar contexto e conversa perto do trabalho, com busca que respeita permissões e um app instalável.

**Critério de saída (Release 1.5):** os times usam canais, documentos e ADRs; a busca global encontra tudo o que a pessoa pode ver e nada além; o app é instalável como PWA; há uma auditoria de acessibilidade dos fluxos principais.

**Pré-requisito:** ADR-016 decidida pelo spike EP-40.

**Linha de corte:** primeiro sai EP-47 (bloqueio por status check), depois partes de EP-46 (dashboards modulares e abas internas), depois EP-42.

### EP-40 — Decisão sobre o chat (Must · P)

- **US-40.1** Como equipe, quero comparar construir o chat com embutir Mattermost ou Matrix, antes de começar a Fase 3 (spike de 1 semana, no fim da Fase 2). **P**
  - Aceite: Dado o comparativo, então cobre esforço, licença, permissões unificadas com o Vulpes, busca, retenção, instalação self-hosted e experiência do usuário, e termina com a ADR-016 e as US de EP-41 ajustadas.

### EP-41 — Canais por time (Must · G)

- **US-41.1** Como Master, quero criar canais por time com níveis de visibilidade (geral, de time, privado, administrativo). **M**
  - Aceite: Dado um DEV TEAM, quando tenta criar um canal, então é negado.
  - Aceite: Dado um canal privado, então só membros o veem, inclusive na busca.
- **US-41.2** Como usuário, quero mensagens com threads, menções a usuários e times, citações, trechos de código, edição e exclusão com histórico. **G**
  - Aceite: Dado queda de conexão, então o cliente reconecta e recebe o que perdeu (WebSocket com retomada).
  - Aceite: Dado edição ou exclusão, então a versão anterior fica guardada e auditada conforme a política de retenção.
- **US-41.3** Como usuário, quero compartilhar uma atribuição ou documento no canal. **M**
  - Aceite: Dado um cartão compartilhado, então só exibe o conteúdo para quem tem acesso ao recurso.
- **US-41.4** Como usuário, quero controlar presença, última atividade, confirmação de leitura e «digitando», tudo desligado por padrão. **M**
  - Aceite: Dado um usuário que não ativou, então nenhum desses sinais é coletado nem exibido a outras pessoas.
- **US-41.5** Como usuário, quero notificações por canal, time e evento, push (PWA) e horário de silêncio. **M**
- **US-41.6** Como Master, quero moderação básica (ocultar e excluir com motivo) e retenção de mensagens configurável. **M**
  - Aceite: Dado uma ação de moderação, então entra na auditoria com autor e motivo.

### EP-42 — Anexos avançados (Should · G)

- **US-42.1** Como organização, quero armazenamento S3-compatível, versionamento, categorias, limites por usuário, comunidade e organização, e prévias. **G**
  - Aceite: Dado um arquivo, então herda as permissões do recurso onde foi anexado e vale na busca, na prévia e no download.

### EP-43 — Knowledge Hub (Must · G)

- **US-43.1** Como usuário, quero documentos em Markdown com pastas, anexos e diagramas Mermaid, com histórico de versões e restauração. **G**
  - Aceite: Dado uma edição, então cria uma versão e permite restaurar a anterior.
- **US-43.2** Como Master, quero permissões por documento, pasta e comunidade. **M**
  - Aceite: Dado um documento restrito, então nem o título aparece na busca, na prévia ou nos anexos para quem não tem acesso.
- **US-43.3** Como usuário, quero vincular um documento a um canal, time ou atribuição. **P**

### EP-44 — ADRs (Must · M)

- **US-44.1** Como time, quero um módulo de ADRs com contexto, decisão, consequências e status, aprovação do Master, histórico e substituição. **M**
  - Aceite: Dado uma ADR que substitui outra, então a antiga passa a «substituída» com vínculo para a nova.
  - Aceite: Dado uma ADR aprovada, então pode ser exportada em Markdown e vinculada a atribuições, issues e repositórios.

### EP-45 — Busca global com permissões (Must · G)

- **US-45.1** Como usuário, quero buscar em atribuições, issues, PRs, commits, documentos, ADRs, mensagens, arquivos, usuários e canais. **G**
  - Aceite: Dado dois usuários com permissões diferentes, quando fazem a mesma busca, então cada um recebe só o que pode ver, e contagens e sugestões não revelam o que está oculto.
  - Tarefas: busca textual do PostgreSQL; filtro de ACL aplicado dentro da consulta, não depois.

### EP-46 — Navegação e personalização (Should · G)

- **US-46.1** Como usuário, quero instalar o app (PWA), com política de cache explícita e sem promessa de uso offline completo. **M**
- **US-46.2** Como usuário, quero paleta de comandos (Ctrl+K), favoritos, filtros salvos, histórico de navegação e atalhos configuráveis. **M**
  - Aceite: Dado a paleta, então só oferece ações e itens que a pessoa pode usar, e funciona só com teclado.
- **US-46.3** Como usuário, quero personalizar tema, cor de destaque, idioma (PT-BR e EN), fuso, formato de data, densidade e página inicial. **M**
- **US-46.4** Como usuário, quero uma auditoria de acessibilidade (teclado, contraste, foco, leitor de tela) nas jornadas principais. **M**
  - Aceite: Dado o checklist (nível WCAG 2.2 AA), então os fluxos principais passam ou têm correções planejadas.
- **US-46.5** (Could) Como usuário, quero dashboards modulares com widgets arrastáveis e salvos por pessoa. **G**

### EP-47 — Políticas com bloqueio (Could · M)

- **US-47.1** Como Master, quero que uma GitHub Action consulte o Vulpes e falhe o check de PR quando uma convenção com severidade de bloqueio for violada, com exceções autorizadas e auditadas. **M**
  - Aceite: Dado uma regra em modo bloqueio, então o check explica qual regra falhou; sem exceção válida, o merge fica bloqueado.

## 12. FASE 4 — IA e automações (6 a 8 semanas) → Release 2.0

**Objetivo:** adicionar IA assistiva, auditável e controlada, sem dar autonomia de escrita antes de haver avaliação.

**Critério de saída (Release 2.0):** o assistente somente leitura responde com fontes e respeita as permissões de quem pergunta; sugestões com aprovação estão em uso; o catálogo de automações roda com aprovação por tipo de ação; as avaliações de qualidade e de segurança rodam no CI.

**Pré-requisitos:** busca com ACL e documentos (Fase 3), política de dados da organização e parecer de LGPD sobre envio de dados a provedores externos.

**Princípios da fase:** IA desligada por padrão; todo conteúdo externo (texto de issue, PR, mensagem) é dado não confiável e nunca instrução; a IA só lê o que o solicitante pode ler; ações de escrita exigem aprovação humana até haver evidência de qualidade; mensagens de canais só entram como contexto com opt-in da comunidade; conversas privadas nunca.

### EP-50 — Fundação de IA (Must · G)

- **US-50.1** Como Master central, quero configurar provedores de IA por organização (locais e externos), com política do que pode sair (código, mensagens, documentos), cotas e limite de custo. **G**
  - Aceite: Dado a IA desligada, então nenhum dado é enviado a nenhum provedor.
  - Aceite: Dado uma política que proíbe código em provedor externo, então nenhum trecho de código é enviado a ele.
  - Aceite: Dado o limite de custo atingido, então as chamadas são bloqueadas com aviso.
- **US-50.2** Como Master, quero um registro determinístico de cada execução, em visão resumida e detalhada. **M**
  - Aceite: Dado uma execução, então o registro guarda entradas, fontes consultadas, chamadas de ferramenta, saídas, alterações propostas e aprovações.
  - Nota: a «justificativa» escrita pelo modelo é mostrada como texto auxiliar; o registro confiável é o das entradas e ações.
- **US-50.3** Como equipe, quero uma suíte de avaliações e testes adversariais no CI. **G**
  - Aceite: Dado um texto malicioso em issue, PR ou mensagem pedindo uma ação de escrita, então nenhuma ferramenta de escrita é chamada sem aprovação.
  - Aceite: Dado um conjunto de perguntas de referência, então a taxa de respostas corretas e com fonte é medida e não pode regredir entre versões.

### EP-51 — Assistente somente leitura (Must · G)

- **US-51.1** Como sistema, quero um índice vetorial (pgvector) com ACL por documento e atribuição. **G**
  - Aceite: Dado dois usuários com permissões diferentes, quando fazem a mesma pergunta, então a recuperação filtra por permissão antes de chegar ao modelo.
- **US-51.2** Como usuário, quero perguntas e respostas com citação de fontes e período, separando fato de inferência. **M**
  - Aceite: Dado uma pergunta sem fonte suficiente, então o assistente diz que não encontrou, em vez de inventar.
- **US-51.3** Como Master, quero resumos de atribuição e de sprint, somente leitura. **M**
  - Aceite: Dado um resumo, então cada afirmação aponta para a fonte; dados ausentes são declarados como ausentes.

### EP-52 — Sugestões com aprovação (Should · G)

- **US-52.1** Como usuário, quero sugestões de checklist, título e descrição de PR, resumo para a revisão e critérios que faltam. **M**
  - Aceite: Dado uma sugestão, então só vira ação depois de a pessoa aceitar, e a aceitação é registrada.
- **US-52.2** Como Master, quero que a IA compare evidências com critérios e recomende, deixando a decisão comigo. **G**
  - Aceite: Dado uma recomendação, então aponta as evidências usadas e nunca aprova nem devolve sozinha.
- **US-52.3** (Could) Como DEV, quero análise de falhas de testes com hipóteses separadas de fatos. **M**

### EP-53 — Catálogo de automações (Should · G)

- **US-53.1** Como Master, quero ligar e desligar automações pré-definidas por comunidade, com política por tipo de ação (automática ou com aprovação). **G**
  - Catálogo inicial: preparar checklist ao criar atribuição; validar mensagens de commit; preparar PR; avisar quando uma dependência conclui; avisar mudanças de critério no Jira.
  - Aceite: Dado uma ação marcada «com aprovação», então fica pendente até um Master aprovar.
- **US-53.2** Como operador, quero execução segura de automações. **G**
  - Aceite: Dado uma automação, então tem simulação (dry-run), idempotência, limites de taxa, proteção contra laço (uma automação disparando outra) e um botão de desligar tudo, global e por comunidade.
- **US-53.3** (Could) Como Master, quero definir automações em formato declarativo versionado (gatilho, condição, ação), só quando o catálogo estiver estável. **G**

### EP-54 — Preparação para o agente (Could · M)

- **US-54.1** Como equipe, quero desenhar o ambiente isolado do agente e os critérios de segurança para libertá-lo, como ADR. **M**
  - Aceite: Dado o desenho, então define identidade própria do agente, nenhum segredo dentro do ambiente, sem rede de saída por padrão, limites de CPU, memória, tempo e custo, e permissões por ferramenta (ler, criar branch, commit, PR).

## 13. FASE 5 — Expansão (em ondas)

Esta fase é um backlog ordenado, refinado ao final da Fase 4 com base no que foi aprendido (uso real, custo, demanda dos times). Não há data fixa.

| Épico | Conteúdo | Pré-requisitos |
| --- | --- | --- |
| EP-60 Multi-organização e SaaS | Contas em várias organizações, troca de organização, isolamento de sessão e recursos, administração de tenants, cobrança, backup e recuperação por tenant, página de status | Isolamento por RLS provado (EP-10), ADR de operação SaaS |
| EP-61 Colaboradores externos | Acesso limitado por organização, projeto, time e recurso, com validade | ACL (EP-34) |
| EP-62 Integrações por OAuth | OAuth 2.0 da Atlassian e GitHub App; opção de OAuth por usuário respeitando permissões do Jira | EP-12 |
| EP-63 Chat avançado | Conversas individuais, grupos privados e vinculados a times, reações, enquetes, mensagens agendadas, encaminhamento, fixadas, anúncios do Master | EP-41 |
| EP-64 Diagramas | Excalidraw e depois diagrams.net: editáveis, versionados, compartilháveis e vinculados a atribuições, canais, comunidades e issues | EP-43 |
| EP-65 Áudio e vídeo | Jitsi ou LiveKit embutido: salas por canal, compartilhamento de tela, agendamento, gravação opcional com consentimento | EP-41 |
| EP-66 Agente de desenvolvimento | Ambiente isolado que executa, testa e prepara branch e PR, com permissões por ferramenta e aprovação humana | EP-54 e avaliações de segurança aprovadas |
| EP-67 Análises avançadas | Critério → teste automatizado, atribuição com várias issues, DORA, previsão por Monte Carlo, roadmap e capacidade | EP-30 |
| EP-68 Dashboards modulares | Widgets arrastáveis e redimensionáveis, múltiplos dashboards, templates e compartilhamento | EP-46 |
| EP-69 Aplicativo nativo | Avaliar a partir do uso do PWA | EP-46 |

## 14. Requisitos não funcionais transversais

| Área | Requisito |
| --- | --- |
| Segurança | Autorização no backend em todo endpoint (nega por padrão); isolamento por tenant com RLS; segredos criptografados e nunca em logs; varredura de segredos e dependências no CI; endurecimento HTTP |
| Privacidade e LGPD | Finalidade e base legal documentadas; retenção configurável; exportação e exclusão; envio a provedores de IA sob política da organização; recursos de presença e leitura opt-in |
| Transparência dos dados | Falha não é ausência; dado antigo é identificado; parcial é identificado; campo ausente não vira zero; métricas mostram definição, período, fonte e limitações |
| Pessoas | Sem ranking nem score de produtividade individual; indicadores individuais são contexto de trabalho; presença não gera métricas |
| Desempenho | Metas iniciais a validar na Fase 1 com volume de teste: telas de lista abrindo em até 1 segundo no p95 com 10 mil atribuições; sincronização incremental sem bloquear a interface |
| Confiabilidade | Jobs idempotentes com retry e lista de falhas; ações externas (Jira) com estado pendente, confirmado e falhou; backup e restauração testados |
| Observabilidade | Logs estruturados com `request_id` e `sync_id`; healthchecks; erros com mascaramento; métricas de sincronização e fila a partir da Fase 2 |
| Acessibilidade | WCAG 2.2 AA nas jornadas principais; navegação por teclado; informação nunca só por cor; auditoria periódica |
| Internacionalização | PT-BR primeiro; textos centralizados; EN na Fase 3; fuso padrão America/Sao\_Paulo, configurável por usuário |
| Portabilidade | Linux com Docker Compose; perfil mínimo (aplicação + PostgreSQL); serviços extras só por gatilho medido |

## 15. Riscos e mitigações

| ID | Risco | Prob. | Impacto | Mitigação |
| --- | --- | --- | --- | --- |
| R-1 | Escopo maior que a capacidade (5 pessoas) | Alta | Alto | MoSCoW, linha de corte por fase, revisão a cada sprint, entregas verticais |
| R-2 | Critérios de aceite fora do padrão no Jira | Média | Alto | Spike US-03.4, template adotado (PA-5), validação na importação, criação de issue pelo Vulpes na Fase 2 |
| R-3 | Limites das APIs do Jira e do GitHub | Média | Médio | Sincronização incremental, controle de taxa, ETags, webhooks |
| R-4 | Vazamento de dados entre tenants ou times | Baixa | Crítico | RLS com testes negativos, função central de autorização, revisão de segurança por fase |
| R-5 | Divergência entre Vulpes e Jira na transição de estado | Média | Alto | Outbox, reconciliação, estados pendente e falhou, fila de conflitos |
| R-6 | Injeção de prompt e vazamento de dados pela IA | Média | Alto | IA desligada por padrão, ACL na recuperação, sem escrita automática, avaliações adversariais no CI |
| R-7 | O chat consumir a Fase 3 inteira | Alta | Médio | Spike EP-40, escopo mínimo, opção de embutir uma solução pronta |
| R-8 | Fila de revisão virar gargalo | Média | Médio | Qualquer Master aprova, SLA visível, delegação de Masters |
| R-9 | Licença e jurídico (source-available, LGPD) | Média | Alto | ADR-014 com parecer, revisão de LGPD antes da Fase 1 e da Fase 4 |
| R-10 | Regressão no analytics ao migrar para o banco | Média | Alto | Testes de equivalência, manter `domain/` e a suíte atual |
| R-11 | Dependência de tokens de uma pessoa | Média | Médio | Tokens por organização com rotação; OAuth e GitHub App na Fase 5 |
| R-12 | Limites do Streamlit (autenticação e UX) | Média | Médio | Módulo isolado, `st.login`, migração tela a tela para React se necessário |
| R-13 | O time não adotar o preenchimento de critérios e evidências | Média | Alto | Piloto com um time, importação automática, evidência automática do GitHub, UX simples, retrospectiva ao fim da Fase 1 |

## 16. Definições de pronto e processo

**Definition of Ready (para uma US entrar em sprint):**

- Tem critérios de aceite no formato Dado / Quando / Então.
- Dependências identificadas e resolvidas ou planejadas.
- Tamanho P, M ou G (se maior, foi quebrada).
- Impacto em permissões, dados pessoais e auditoria avaliado.
- Design de interface definido, quando houver tela.

**Definition of Done (para uma US ser considerada concluída):**

- Código revisado por outra pessoa.
- Testes unitários e de integração; testes de autorização e isolamento quando aplicável.
- Estados de erro, parcial e dados antigos tratados; nenhum erro exibido como vazio.
- Logs sem segredos; ações relevantes na auditoria.
- Textos centralizados; checklist de acessibilidade aplicado nas telas.
- Migração com rollback quando houver banco; documentação e CHANGELOG atualizados.
- Demonstrada ao time ou ao Master.

**Cerimônias sugeridas:** sprints de 2 semanas; revisão e retrospectiva ao fim de cada sprint; refinamento da próxima fase na última sprint da fase atual; revisão de riscos a cada fase.

**Processo de ADR:** proposta → discussão (até 1 semana) → decisão registrada → revisão quando o gatilho definido na própria ADR ocorrer. Uma decisão técnica que afeta mais de um épico não entra em sprint sem ADR.

## 17. Rastreabilidade: decisões do Plano Mestre → épicos

| Bloco do Plano Mestre | Decisões | Épicos |
| --- | --- | --- |
| A — Estrutura da comunidade | A-01 a A-05 | EP-11, EP-41, EP-63 |
| B — Central de atribuições e Jira | B-06 a B-10 | EP-13, EP-16, EP-32, EP-33 |
| C — Critérios, evidências, documentação, diagramas | C-11 a C-19 | EP-14, EP-15, EP-43, EP-44, EP-64 |
| D — IA e automações | D-20 a D-25 | EP-50 a EP-54, EP-66 |
| E — Administração e permissões | E-26 a E-32 | EP-11, EP-34, EP-60, EP-61 |
| F — Comunicação | F-33 a F-41 | EP-18, EP-41, EP-42, EP-45, EP-63, EP-65 |
| G — UI e UX | G-42 a G-49 | EP-10, EP-19, EP-46, EP-68, EP-69 |
| H — Integrações e fluxo de desenvolvimento | H-50 a H-56 | EP-12, EP-17, EP-31, EP-33, EP-36, EP-47 |
| I — Infraestrutura e estratégia | I-57 a I-60 | EP-02, EP-10, EP-20, EP-30, EP-37, EP-60 |
| Plano Mestre — P0 (estabilização) | P0-01 a P0-20 | EP-01, EP-02, EP-03 |
| Plano Mestre — P1 (arquitetura e sincronização) | P1-01 a P1-SYNC-12 | EP-10, EP-12, EP-17, EP-30, EP-31 |
| Plano Mestre — P2 (produto e análises) | P2-TRACE, P2-ALERT, P2-AN, P2-PR | EP-30, EP-36, EP-45, EP-67 |

## 18. Fora do escopo (por enquanto)

Kubernetes, Kafka, microsserviços, Elasticsearch, banco NoSQL adicional, WhatsApp, outros provedores de código (GitLab e Bitbucket), aplicativo nativo, ranking ou score de produtividade individual. Cada item só volta ao plano com um gatilho medido ou uma demanda concreta, registrada em ADR.

## 19. Próximos passos

1. Confirmar as premissas PA-1 a PA-8 (especialmente PA-2, PA-4 e PA-5).
2. Revisar e aceitar as ADRs 001 a 013 (documento separado).
3. Montar o time e o quadro de sprints da Fase 0 a partir dos épicos EP-01 a EP-03.
4. Escolher o time-piloto da Fase 1 e combinar com ele o template de critérios no Jira.
5. Agendar o parecer jurídico sobre licença e LGPD.
