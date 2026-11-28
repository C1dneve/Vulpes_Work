# Vulpes Work --- Documento Geral do Projeto

> **Versão:** 1.2 --- decisões consolidadas e experiência do usuário\
> **Data:** 27/11/2026\
> **Status:** APROVADO PELO USUÁRIO em 27/11/2026; Q1--Q90 incorporadas\
> **Base:** documento 1.1, respostas do usuário Q1--Q90 e baseline do ZIP `Vulpes_Work-main.zip`\
> **Objetivo:** contexto geral de produto e desenvolvimento, AI-ready,
> para trabalho baseado em ZIPs sem presumir acesso ao repositório
> remoto, CLI ou ambiente local.

------------------------------------------------------------------------

## 0. Como interpretar este documento

Este documento separa quatro tipos de informação:

-   **DECIDIDO:** escolha expressamente confirmada pelo usuário, com
    referência à resposta/decisão correspondente.
-   **OBSERVADO NO ZIP:** arquivo, código ou configuração efetivamente
    presente no ZIP analisado.
-   **PLANEJADO:** funcionalidade ou arquitetura desejada, ainda não
    comprovada como implementada.
-   **EM ABERTO:** decisão que ainda precisa de resposta ou validação.

Não considerar uma funcionalidade implementada apenas porque aparece
neste documento, em um plano antigo, em uma ADR ou em um teste isolado.

### 0.1 Regra de precedência

Em caso de conflito, aplicar esta ordem:

1.  Respostas explícitas mais recentes do usuário (decisões
    explicitamente respondidas e esclarecimentos posteriores).
2.  Este Documento Geral V1.2, aprovado pelo usuário em 27/11/2026.
3.  ADRs vigentes, desde que não contrariem decisões mais recentes do
    usuário.
4.  Planos de implementação e plano mestre anteriores.
5.  Código e testes do ZIP como evidência do estado implementado --- não
    como autoridade para alterar requisitos do produto.

O código é a fonte para saber o que existe; as decisões do usuário são a
fonte para saber o que o produto deve ser.

### 0.2 Regra para trabalho baseado somente em ZIP

A IA deve: - analisar apenas os arquivos efetivamente recebidos; -
listar o conteúdo do ZIP antes de afirmar que algo existe; - identificar
a versão/commit/data do pacote quando houver essa informação; - não
presumir acesso ao GitHub, histórico de commits, branches, CI remoto,
banco, credenciais ou ambiente de execução; - não executar chamadas
reais a Jira/GitHub nem solicitar ou reproduzir segredos; - não inventar
resultados de testes: distinguir testes descritos em relatórios, testes
executados durante a análise e testes que não puderam ser executados; -
registrar caminhos exatos dos arquivos que sustentam cada afirmação; -
apontar arquivos ausentes, incompletos ou contraditórios; - propor
alterações em arquivos e código como patches ou arquivos revisados, sem
afirmar que alterou o repositório; - ao receber um ZIP novo, compará-lo
com a baseline anterior somente se ambos estiverem disponíveis; - nunca
tratar arquivos temporários, logs, `.coverage`, relatórios de validação
ou patches antigos como código-fonte canônico sem verificar sua
finalidade.

------------------------------------------------------------------------

# 1. Identidade e visão do produto

## 1.1 Nome

**Nome oficial: Vulpes Work.**\
"Vulpes Hub" é nome histórico e não deve ser usado como identidade atual
do produto. Referências antigas podem permanecer em nomes de
repositório, diretórios, pacotes ou histórico até serem migradas de
forma segura, mas a documentação nova, interface, textos e identidade
devem usar Vulpes Work.

## 1.2 Visão

Vulpes Work é uma plataforma colaborativa para equipes de
desenvolvimento que reúne:

1.  **Development Analytics:** acompanhamento de sprints, fluxo de
    trabalho, métricas, alertas e rastreabilidade Jira ↔ GitHub.
2.  **Central de Atribuições:** trabalho organizado em atribuições
    ligadas a issues Jira, com critérios de aceite, evidências, revisão,
    aprovação e auditoria.
3.  **Organização colaborativa:** Organizações, Comunidades, Projetos,
    Times e Canais.
4.  **Knowledge Hub:** documentação, ADRs, arquivos, pesquisa e vínculos
    com o trabalho.
5.  **Automações e IA assistiva:** automações configuráveis e IA com
    acesso restrito, fontes identificáveis e aprovação humana para
    ações.

A plataforma deve reduzir a fragmentação entre Jira (planejamento e
registro externo), GitHub (execução e evidências técnicas) e
comunicação/documentação (contexto e decisões).

**Objetivo de distribuição atual (decisão V1.1):** o projeto será inicialmente desenvolvido e implantado para uso próprio, para apoiar o fluxo de trabalho do usuário. O deploy pode preceder a definição de SaaS, licença ou monetização. Essas decisões ficam para antes do início da Fase 5 ou antes de publicação externa que exija definição jurídica/comercial.

**Posicionamento decidido (Q25--Q26):** no longo prazo, Vulpes Work é
uma plataforma completa (Q25-D); o foco inicial é a gestão colaborativa
de entregas e rastreabilidade (Q25-C), atacando a fragmentação entre
ferramentas (Q26-A). O MVP é voltado tanto a gestores/Masters quanto a
desenvolvedores (Q27-C).

## 1.3 Princípios de produto

-   Entregas verticais e incrementais; cada fase deve produzir um fluxo
    utilizável.
-   Preservar o dashboard atual enquanto se constrói o novo fluxo de
    gestão.
-   Não reescrever funcionalidades existentes sem necessidade e sem
    testes de equivalência.
-   Jira e GitHub continuam sendo fontes externas importantes; Vulpes
    mantém o estado e o histórico do fluxo interno.
-   Falha de integração não pode ser apresentada como ausência de dados.
-   Dados antigos, parciais, ausentes e erro precisam ser estados
    diferentes e visíveis.
-   Não criar rankings ou scores simplistas de produtividade individual.
-   Auditoria e privacidade são requisitos desde a primeira fase do novo
    fluxo.
-   Não adotar microsserviços, Redis, Kubernetes ou infraestrutura
    complexa sem necessidade medida.
-   A IA nunca deve inventar dados ausentes nem ultrapassar as
    permissões do usuário.
-   A experiência deve equilibrar clareza, produtividade e personalização:
    padrões simples por default, com ajustes úteis sem transformar a
    interface em um construtor complexo.
-   A página inicial deve priorizar o trabalho que exige atenção do
    usuário, sem rankings ou métricas de produtividade individual.
-   A interface deve permitir acesso rápido aos detalhes sem obrigar o
    usuário a perder o contexto da lista ou do fluxo atual.
-   Recursos de busca, histórico, notificações e IA devem respeitar as
    permissões e a visibilidade de cada recurso em todas as superfícies.

### 1.4 Direção de experiência do usuário (V1.2)

**Filosofia:** equilíbrio entre produtividade e clareza, com personalização
por usuário (Q90-C). O Vulpes Work não deve ser excessivamente minimalista
a ponto de esconder contexto, nem tão configurável que exija manutenção
constante do layout.

- **Ponto de entrada:** após o login, abrir **Meu Trabalho**, uma central
  pessoal de pendências e atividades relevantes (Q69-A).
- **Personalização:** permitir mover, ocultar e reordenar widgets (Q70-A).
  A personalização deve ser simples e preservar layouts padrão úteis.
- **Densidade:** iniciar com densidade **Padrão** (Q71-B). Em evolução
  posterior, oferecer os modos Confortável, Padrão e Compacto (Q71-futuro-D).
- **Atribuições:** combinar lista, painel lateral de consulta rápida e
  página completa de detalhes (Q72-C).
- **Views:** permitir filtros e visualizações salvas pelo usuário (Q73-A).
- **Mobile:** oferecer consulta, comentários, revisão e ações básicas;
  edição avançada continua prioritariamente no desktop (Q86-A).
- **Customização:** priorizar densidade, widgets e views salvas; cores de
  destaque ficam para depois. Tema claro/escuro por usuário permanece
  conforme V1.1 (Q87-A).
- **Acessibilidade e estados:** manter WCAG 2.2 AA como alvo das jornadas
  principais e distinguir carregamento, vazio, parcial, desatualizado,
  falha, falta de permissão e salvamento pendente.

------------------------------------------------------------------------

# 2. Decisões consolidadas do usuário

Esta seção reúne decisões consolidadas no documento 0.1 e as respostas
posteriores do usuário. Q1--Q24 estão registradas na seção 9; Q25--Q53 na
seção 11; Q54--Q68 na seção 15; Q69--Q90 na seção 16. Decisões comerciais
foram adiadas intencionalmente, conforme descrito na seção 9.

## 2.1 Produto e escopo

  ---------------------------------------------------------------------
  Tema                               Decisão consolidada
  ---------------------------------- ----------------------------------
  Nome                               Vulpes Work; Vulpes Hub é
                                     histórico.

  Prioridade inicial                 Estratégia híbrida: preservar o
                                     dashboard atual e desenvolver o
                                     fluxo de gestão de entregas sem
                                     exigir migração integral do
                                     dashboard.

  Analytics                          Streamlit continua como módulo
                                     Development Analytics; novas áreas
                                     serão desenvolvidas em React +
                                     TypeScript.

  Hierarquia                         Organização → Comunidades →
                                     Projetos e Times; Times contêm
                                     Canais.

  Projeto e Times                    Um Projeto pertence a uma
                                     Comunidade e pode ser associado a
                                     vários Times daquela Comunidade;
                                     associação Projeto--Time é N:N.

  Jira                               Na primeira entrega, a atribuição
                                     exige uma issue Jira existente.
                                     Criar issues pelo Vulpes fica para
                                     fase posterior.

  Comunicação                        Comentários nas atribuições na
                                     Fase 1; Canais de Times na Fase 3;
                                     DMs e grupos privados em fase
                                     futura.

  Multi-tenancy                      Preparar `tenant_id` e RLS desde a
                                     fundação; inicialmente uma
                                     Organização por instalação, sem
                                     SaaS multi-organização ativo.

  Distribuição                       Estratégia futura híbrida:
                                     self-hosted e SaaS.

  Time de referência                 Planejamento considera uma equipe
                                     de 5--9 desenvolvedores; não é
                                     garantia de capacidade.
  ---------------------------------------------------------------------

## 2.2 Fluxo de atribuições

  ---------------------------------------------------------------------------------------------------------------------
  Tema               Decisão consolidada
  ------------------ --------------------------------------------------------------------------------------------------
  Issue por          Uma issue por atribuição na primeira versão; uma issue não pode ter duas atribuições ativas
  atribuição         simultâneas.

  Histórico          Ao concluir/cancelar, a issue poderá receber outra atribuição posteriormente, mantendo o
                     histórico.

  Responsabilidade   Uma atribuição tem um Time responsável, uma pessoa responsável principal e participantes
                     adicionais.

  Aprovação          Qualquer Master da Comunidade pode revisar/aprovar, central ou delegado.

  Estados            `Rascunho → Atribuída → Em andamento → Em revisão → Ajustes solicitados → Aprovada → Concluída`;
                     `Cancelada` como alternativa.

  Cancelamento       Atribuição cancelada permanece no histórico; Master pode reabri-la mediante justificativa.

  Revisões           Rodadas ilimitadas, com histórico preservado.

  Critérios ausentes Política por Projeto; padrão é exigir critérios. Exceção depende de Master, justificativa e
                     auditoria.

  Formato            Markdown em Given/When/Then (Dado/Quando/Então).

  Critérios          Criar nova versão pendente; Master aceita/rejeita; preservar versão anterior e marcar evidências
  alterados no Jira  para revalidação quando aplicável.

  Evidências         Links, texto, arquivos e evidências sugeridas automaticamente pelo GitHub; cada evidência ligada a
                     um critério.

  Não aplicável      Critério pode ser marcado como não aplicável com justificativa e aprovação de Master.

  Envio para revisão DEV solicita revisão quando todos os critérios obrigatórios têm evidência e estão marcados como
                     atendidos.

  Aprovação no Jira  Vulpes solicita a transição Jira e só marca Concluída após confirmação da API.
  ---------------------------------------------------------------------------------------------------------------------

Modelo do critério:

``` markdown
## Critérios de aceite
- Dado que o usuário está autenticado
  Quando realizar o cadastro
  Então o sistema deve salvar os dados
```

## 2.3 Papéis e acesso

-   Papéis globais definidos: **Owner, Admin, Master e DEV TEAM**.
-   Master delegado tem escopo restrito à Comunidade delegada.
-   Owner e Admin criam/gerenciam Comunidades (conforme resposta 39A:
    Owner/Admin).
-   Convites por e-mail enviados por Owner/Admin, com aceite do
    convidado.
-   Usuário pode exercer papéis diferentes em Comunidades diferentes.
-   Uma conta pode participar de múltiplas Organizações, com membros e
    permissões independentes por Organização.
-   Associação de Time a Projeto concede acesso ao
    Projeto/issues/repositórios conforme permissões específicas; não
    concede automaticamente acesso a Canais privados ou documentos
    restritos.
-   A matriz exata de poderes de Owner, Admin, Master central, Master
    delegado e DEV TEAM ainda precisa ser fechada (ver perguntas
    abertas).

## 2.4 Integrações e dados

  ---------------------------------------------------------------------
  Tema                               Decisão consolidada
  ---------------------------------- ----------------------------------
  Credenciais Jira/GitHub            Por Organização, criptografadas em
                                     repouso; Master configura e
                                     controla quais Projetos/Times
                                     podem usar.

  OAuth individual                   Apenas em fase muito futura.

  Sincronização                      Webhooks + sincronização periódica
                                     de segurança/reconciliação.

  Frequência periódica               5 minutos como intervalo inicial
                                     desejado, sujeito a limites de API
                                     e configuração operacional.

  Fonte de verdade                   Jira para issues, status externo e
                                     metadados externos; Vulpes para
                                     atribuições, critérios internos,
                                     evidências e revisões.

  GitHub inicial                     Repositórios, branches, commits,
                                     PRs e checks.

  Associação de PR                   Referência de issue em
                                     branch/PR/commit, com associação
                                     manual quando necessário.

  Indisponibilidade externa          Preservar último dado válido,
                                     marcar como antigo e tentar
                                     novamente em background.

  Analytics Fase 1                   Preservar integrações atuais com
                                     Jira/GitHub via API.

  Analytics Fase 2                   Começar a consumir dados
                                     persistidos no PostgreSQL.
  ---------------------------------------------------------------------

## 2.5 Plataforma, experiência e roadmap

-   Backend-alvo: Python + FastAPI, monólito modular e contratos
    Pydantic.
-   Banco: PostgreSQL com `tenant_id` e Row-Level Security.
-   Fila: PostgreSQL e workers separados; Redis não será introduzido até
    existir justificativa.
-   Frontend dos novos módulos: React + TypeScript + Vite.
-   Deploy inicial: Docker Compose; Kubernetes apenas se houver
    necessidade comprovada.
-   Testes: unitários, integração, contrato de API, banco/RLS e E2E dos
    fluxos principais.
-   Ambientes: desenvolvimento, homologação e produção isolados.
-   Visual: referências de Linear, GitHub e ferramentas modernas de
    gestão, sem copiar; interface limpa, produtiva e com baixa poluição
    visual.
-   Temas: claro/escuro por preferência do usuário; personalização
    ampliada futuramente.
-   Idioma inicial: PT-BR, arquitetura preparada para
    internacionalização.
-   Responsividade: desktop-first, com funcionalidades essenciais
    utilizáveis em celular.
-   Knowledge Hub: documentos, ADRs, arquivos, pesquisa, histórico e
    vínculos com Projetos/atribuições.
-   Automação: modelo configurável de gatilho → condição → ação.
-   IA: Fase 4, inicialmente somente leitura, com fontes, permissões e
    aprovação humana antes de ações.
-   Canais: Fase 3; canais de Time, mensagens, threads, anexos e
    notificações.
-   Fase 5: SaaS, administração multi-organização, billing, planos e
    expansão comercial.
-   Licença, modelo de distribuição self-hosted e detalhes comerciais
    continuam em aberto.
-   Estimativas: P/M/G por US, dependências e marcos; sem datas firmes
    antes de conhecer a velocidade real.

## 2.6 Experiência, navegação e produtividade pessoal (V1.2)

As escolhas abaixo foram confirmadas nas respostas Q69--Q90 e detalhadas
na seção 16. A classificação de fase é deliberada: itens essenciais ao
fluxo entram na Fase 1; recursos que dependem de histórico mais rico ou
representam expansão de produtividade são escalonados para a Fase 2.

| Tema | Decisão consolidada |
|---|---|
| Página inicial | Meu Trabalho após login, com widgets pessoais (Q69-A). |
| Widgets | Usuário pode mover, ocultar e reordenar (Q70-A). |
| Densidade | Padrão inicialmente; seletor Confortável/Padrão/Compacto em fase posterior (Q71-B; futuro-D). |
| Detalhe da atribuição | Lista + painel lateral + página completa (Q72-C). |
| Views salvas | Views criadas pelo usuário (Q73-A). |
| Busca inicial | Busca Vulpes + Jira na Fase 1; GitHub e Knowledge Hub entram conforme suas fases (Q74-A). |
| Command Palette | Ctrl+K na Fase 2, após estabilizar a navegação (Q75-B). |
| Novidades desde a última visita | Fase 2, apoiada em histórico de eventos mais completo (Q76-B). |
| Review Inbox | Caixa dedicada é parte do fluxo central da Fase 1 (Q77-A). |
| Templates | Templates reutilizáveis com critérios/checklist (Q78-A). |
| Captura pessoal | Caixa pessoal para ideias/tarefas a organizar depois; não equivale a uma atribuição Jira (Q79-A). |
| Notificações | Preferências por evento, agrupamento e resumos diários/semanais, entregues em etapas (Q80-A). |
| Vínculos GitHub–Jira | Sugestões dentro da atribuição; toda associação exige confirmação explícita (Q81-A). |
| Saúde das integrações | Página com conexão, última sincronização, falhas e nova tentativa autorizada (Q82-A). |
| Linha do tempo pessoal | Sim, privada e sem ranking ou score de produtividade (Q83-A). |
| Setup guiado | Assistente para configurar Organização, Jira, GitHub, Projetos e Times na instalação própria (Q84-A). |
| Salvamento | Autosave de rascunhos, recuperação e confirmação de ações destrutivas (Q85-A). |
| Mobile | Consulta, comentários, revisão e ações básicas; edição avançada no desktop (Q86-A). |
| Personalização | Densidade/widgets/views; cor de destaque depois (Q87-A). |
| IA futura | Resumos e sugestões de issue/PR, mudanças, critérios e evidências, sempre com fontes e aprovação humana (Q88-E). |
| Modo foco | Simples, na Fase 2 (Q89-A). |
| Filosofia | Equilíbrio entre clareza, produtividade e personalização por usuário (Q90-C). |

**Regra de escopo:** sugestões de associação GitHub–Jira nunca criam vínculo
silenciosamente. Capturas pessoais não criam atribuições sem issue Jira
válida. Templates complementam o contexto da atribuição e não sobrescrevem
critério ou descrição de origem Jira sem ação explícita.

------------------------------------------------------------------------

# 3. Baseline atual do ZIP analisado

## 3.1 Identificação

-   **Arquivo:** `Vulpes_Work-main.zip`
-   **Tamanho do ZIP:** 2,148,214 bytes (aprox. 2,15 MB)
-   **SHA-256:**
    `ced071848f4e2fca79a6d2ed9a34c7117773f735703f56ef9a2ba0fb1192aafe`
-   **Entradas ZIP:** 146 (incluindo diretórios)
-   **Arquivos:** 126
-   **Raiz interna:** `Vulpes_Work-main/`
-   **Git metadata:** não encontrado (`.git`/commit não disponível no
    ZIP)
-   **Análise:** inspeção estática de arquivos, documentação e código;
    compilação Python e tentativa de coleta de testes registradas
    abaixo.

## 3.2 Estrutura e implementação observadas

O pacote contém `.github/`, `.streamlit/`, `application/`, `contracts/`,
`docs/`, `domain/`, `services/`, `spikes/rls/`, `tests/`, `tools/`,
`views/`, `app.py`, `settings.py`, `ui_components.py`, Dockerfile,
Compose, `pyproject.toml`, `uv.lock` e documentação.

-   Aplicação atual: Python + Streamlit, com `app.py` como entrada.
-   `domain/`: regras e cálculos; `services/`: integrações Jira/GitHub,
    HTTP, cache e sincronização.
-   `application/` e `contracts/` existem em estágio inicial.
-   O dashboard oferece visões de sprint, stories/subtasks,
    burnup/burndown, alertas, pessoas, timeline e rastreabilidade
    Jira--GitHub, conforme README e `docs/MVP_STATUS.md`.
-   Há 32 arquivos `test_*.py` e 56 arquivos Python de produção, com
    aproximadamente 7,334 linhas físicas (contagem estática; inclui
    código de UI/configuração).
-   Dockerfile e Compose estão presentes; o Compose principal inicia o
    dashboard Streamlit.
-   CI está configurado para Python 3.12/3.13, Ruff, mypy,
    pytest/cobertura, `pip-audit` e Gitleaks; o documento do projeto
    informa que o workflow remoto ainda aguarda commit/push.

## 3.3 O que não foi identificado integrado ao runtime principal

-   API FastAPI funcional e frontend React/TypeScript/Vite.
-   PostgreSQL, SQLAlchemy/Alembic e RLS no produto principal.
-   Login OIDC/Google e RBAC/ACL completos.
-   Entidades de Organização/Comunidade/Projeto/Time e fluxo completo de
    atribuições.
-   Critérios, evidências, revisão/aprovação e confirmação de transição
    Jira como fluxo integrado.
-   Workers/fila de jobs, webhooks do produto, notificações
    transacionais e auditoria completa.
-   Knowledge Hub, Canais, automações, IA e SaaS.

`spikes/rls/` é uma prova de conceito isolada; não comprova isolamento
de todas as tabelas do produto.

## 3.4 Verificações desta análise

-   `python -m compileall -q .`: **concluído sem erro**.
-   `python -m pytest -q`: **não coletou a suíte**; cinco módulos
    falharam na coleta por
    `ModuleNotFoundError: No module named 'streamlit'`. Isso é uma
    limitação do ambiente desta análise, não evidência de falha
    funcional nos testes do projeto.
-   `docs/MVP_STATUS.md` relata 440 testes aprovados e cobertura de 85%;
    esse resultado é reportado pelo mantenedor, não reexecutado aqui. O
    próprio documento ainda registra pendência de equivalência das 224
    asserções anteriores.

## 3.5 Artefatos que merecem revisão no próximo ZIP

O ZIP contém `.coverage` (69,632 bytes), `Vulpes_Hub-revisao.patch`
(2,138,680 bytes), `tools/validation_output/results.json` (20,110 bytes)
e `tools/validation_output/console.log` (22,948 bytes). Confirmar se são
necessários e se podem conter dados reais; remover/sanitizar artefatos
desnecessários antes de compartilhar.

A documentação visível ainda contém identidade histórica `Vulpes Hub` e
o README referencia um URL antigo de repositório. `pyproject.toml`
mantém o nome de pacote `vulpes-hub`. Isso pode ser uma migração técnica
pendente, mas não altera o nome oficial de produto **Vulpes Work**.

------------------------------------------------------------------------

# 4. Decisões antigas que devem ser substituídas

  ------------------------------------------------------------------------
  Tema antigo            Situação antiga         Decisão atual que
                                                 prevalece
  ---------------------- ----------------------- -------------------------
  Nome                   Vulpes Hub              Vulpes Work; nome antigo
                                                 apenas histórico.

  Foco da Fase 1         Migrar dashboard para   Abordagem híbrida: manter
                         React e persistência    Analytics em Streamlit e
                         antes do fluxo          construir o fluxo de
                         colaborativo            atribuições como
                                                 prioridade vertical.

  Papéis                 Apenas Master e DEV     Owner, Admin, Master e
                         TEAM como papéis padrão DEV TEAM; Master delegado
                                                 é limitado à Comunidade.

  Criação de Comunidades Master central também   Owner/Admin são
                         podia criar conforme    responsáveis pela
                         matriz antiga           criação/gestão de
                                                 Comunidades.

  Login                  Microsoft/Google/OIDC   Google como provedor
                         configurável            primário; OIDC genérico
                                                 se adequado.

  Critérios/evidências   Critérios e evidências  Recursos básicos de
                         avançadas planejados    critérios e evidências
                         para fases posteriores  entram na Fase 1;
                                                 versionamento/Knowledge
                                                 Hub avançado na Fase 3.

  Sincronização          Polling na Fase 1;      Webhooks + sincronização
                         webhooks na Fase 2      periódica de segurança;
                                                 frequência inicial de 5
                                                 minutos.

  Analytics              Migrar dashboard para   Streamlit preservado;
                         React na Fase 1         Fase 1 mantém APIs
                                                 existentes; Fase 2 começa
                                                 a consumir PostgreSQL.

  Licença                MIT aprovada em ADR-014 Reabrir a decisão.
                         e plano antigo          Nenhuma licença está
                                                 aprovada.

  Distribuição           Self-hosted e SaaS com  Estratégia híbrida;
                         detalhes não fechados   condições comerciais e
                                                 limites ainda em aberto.

  Multi-organização      Sem multi-organização   Mantém-se uma Organização
                         ativa até fase futura   por instalação no início;
                                                 multi-organização SaaS na
                                                 Fase 5.

  IDs e prioridade       Mistura de P0--P3,      IDs estáveis
                         MoSCoW e IDs de estilos EP-xx/US-xx.y; prioridade
                         diferentes              MoSCoW; tamanho P/M/G.

  Planejamento           Durações fixas e        Estimativas P/M/G,
                         cronograma por semanas  dependências e marcos;
                                                 datas só após
                                                 capacidade/velocidade
                                                 observadas.
  ------------------------------------------------------------------------

### 4.1 Documentos e trechos que não devem mais ser tratados como verdade vigente

-   Afirmação de que a camada `application/` ainda não existe.
-   Caminhos antigos de configuração/logging, como `core/config.py` e
    `core/logging.py`; no ZIP atual estão `settings.py` e
    `services/logging_config.py`.
-   Stack e versões antigas (Python 3.10, Streamlit 1.55, requests
    2.32.x) quando contradisserem `pyproject.toml` e `uv.lock` atuais.
-   Papéis limitados a Master/DEV TEAM.
-   Login corporativo Microsoft como escolha primária.
-   Migração total do dashboard para React como pré-condição da Fase 1.
-   Licença MIT como decisão final.
-   Redis/Celery como requisito inicial; a decisão atual mantém
    PostgreSQL como fila e Redis adiado.
-   "Workspace" como entidade de produto sem definição; usar
    Organização, Comunidade, Projeto, Time e Canal.

------------------------------------------------------------------------

# 5. Arquitetura-alvo

## 5.1 Direção

Monólito modular em Python, com API e workers separados por processo
quando necessário. O backend não deve ser fragmentado em microsserviços
prematuramente.

``` text
Vulpes Work
├── Development Analytics
│   └── Streamlit (preservado; lê APIs existentes na Fase 1)
├── Novos módulos
│   └── React + TypeScript + Vite
├── Backend
│   └── FastAPI + Pydantic
├── Domínio e aplicação
│   ├── domain/
│   ├── application/
│   └── contracts/
├── Integrações
│   ├── Jira Cloud
│   └── GitHub
├── Persistência (Fase 1)
│   └── PostgreSQL + SQLAlchemy + Alembic
└── Processamento
    └── Workers + fila PostgreSQL
```

O desenho acima é arquitetura-alvo; somente Streamlit, domínio,
serviços, Application inicial, contratos, testes, Docker e CI foram
observados como existentes no ZIP.

## 5.2 Regras arquiteturais

-   Domínio não importa Streamlit, FastAPI, ORM ou SDK externo.
-   UI Streamlit e frontend React consomem casos de uso/API, sem
    duplicar regras.
-   Contratos Pydantic explícitos entre fronteiras.
-   Repositórios encapsulam persistência.
-   Jobs são idempotentes, com retry, backoff, rastreabilidade e fila de
    falhas.
-   Credenciais criptografadas em repouso; nunca em logs ou ZIPs
    compartilhados.
-   RLS deve ser aplicado por transação e testado negativamente para
    cada entidade com dados de Organização.
-   Autorização central no backend, deny-by-default.
-   Eventos externos e comandos para Jira devem ser reconciliáveis; não
    declarar conclusão antes da confirmação externa.
-   SSE pode atender atualizações em tempo real simples; WebSocket fica
    para chat quando necessário.
-   Redis, Kubernetes e microsserviços dependem de gatilho medido.

## 5.3 Entidades centrais previstas

-   Organization
-   User
-   OrganizationMembership
-   Community
-   CommunityMembership
-   Project
-   Team
-   TeamMembership
-   ProjectTeam
-   Channel
-   Assignment
-   AssignmentParticipant
-   JiraIssueReference
-   AcceptanceCriterion
-   CriterionVersion
-   Evidence
-   Review
-   ReviewRound
-   IntegrationCredential
-   Repository
-   SyncRun / Job
-   AuditEvent
-   Notification
-   UserPreference / DashboardWidgetPreference
-   SavedView
-   PersonalActivityEvent
-   PersonalCapture (Fase 2)
-   KnowledgeDocument / DocumentVersion

O modelo é conceitual e precisa de ERD e validação antes das migrações
definitivas.

------------------------------------------------------------------------

# 6. Roadmap reconciliado

As fases abaixo substituem a sequência antiga que colocava a migração
integral do dashboard na Fase 1. Os IDs são estáveis e não devem mudar
quando o escopo for reordenado.

## Fase 0 --- Baseline e estabilização

**Status:** concluída em grande parte segundo os documentos e relatórios
do ZIP; ainda há validações pendentes.

Objetivo: manter o dashboard atual reproduzível, testável e seguro
enquanto prepara evolução.

Épicos: - **EP-01 --- Higiene do pacote e documentação:** identidade
Vulpes Work, remoção/sanitização de artefatos, README e instruções
reproduzíveis. - **EP-02 --- Qualidade e modularização:** preservar
domínio, casos de uso, contratos, tipagem e testes. - **EP-03 ---
Decisões e provas técnicas:** revisar ADRs, validar RLS, critérios Jira,
autenticação e licença.

Critérios de saída: - instalação limpa reproduzível a partir do ZIP; -
documentação de estado atual coerente com o código; - testes e
verificações registrados com data, comando e resultado; - baseline das
224 asserções comparada/documentada contra a suíte atual; - artefatos
sensíveis e de validação tratados; - ADRs em estado coerente com as
decisões mais recentes.

## Fase 1 --- Fundação da plataforma e piloto vertical de atribuições

**Prioridade:** maior prioridade de produto.\
**Analytics:** permanece em Streamlit, consumindo as integrações
existentes.\
**Objetivo:** um Time piloto realiza o ciclo completo de atribuição,
critérios, evidências, revisão e confirmação no Jira.

### EP-10 --- Fundação backend, banco e contratos

-   US-10.1 --- Criar API FastAPI versionada e contratos
    OpenAPI/Pydantic.
-   US-10.2 --- Criar PostgreSQL, SQLAlchemy, Alembic e entidades
    iniciais com `tenant_id` e RLS.
-   US-10.3 --- Implementar fila PostgreSQL e workers separados, com
    idempotência e retry.
-   US-10.4 --- Definir contratos de resposta que distingam sucesso,
    parcial, stale, vazio, erro externo e erro interno.
-   US-10.5 --- Healthchecks, logs estruturados, request IDs e
    mascaramento de segredos.

Dependências: nenhuma para desenho; banco/RLS precedem funcionalidades
multi-tenant; contratos precedem frontend.

### EP-11 --- Identidade, organização e permissões

-   US-11.1 --- Login Google como provedor primário e suporte OIDC
    genérico quando adequado.
-   US-11.2 --- Criar Organização, usuário e associação de membros.
-   US-11.3 --- Implementar papéis Owner, Admin, Master e DEV TEAM.
-   US-11.4 --- Implementar Master delegado limitado à Comunidade.
-   US-11.5 --- Convites por e-mail com aceite, expiração e revogação.
-   US-11.6 --- Aplicar autorização central no backend, deny-by-default.
-   US-11.7 --- Permitir participação do mesmo usuário em múltiplas
    Organizações, com permissões independentes.

Dependências: EP-10; matriz de permissões precisa ser fechada.

### EP-12 --- Integrações Jira e GitHub

-   US-12.1 --- Configurar credenciais por Organização, criptografadas
    em repouso.
-   US-12.2 --- Configurar Projetos Jira e repositórios GitHub
    disponíveis para Projetos/Times.
-   US-12.3 --- Sincronizar issues e metadados necessários à criação de
    atribuições.
-   US-12.4 --- Receber webhooks e executar sincronização periódica de
    segurança (alvo inicial: 5 minutos).
-   US-12.5 --- Preservar dados anteriores e sinalizar
    stale/parcial/erro.
-   US-12.6 --- Registrar execuções, falhas, tentativas e reconciliação.
-   US-12.7 --- Expor uma página de Saúde das Integrações com estado da
    conexão, última sincronização, falhas recentes e ação de nova tentativa
    para usuários autorizados; não expor credenciais.
-   US-12.8 --- Disponibilizar busca inicial de issues Jira Cloud no Vulpes,
    combinada à busca de entidades internas, respeitando permissões e
    sinalizando dados desatualizados ou indisponibilidade externa.

Dependências: EP-10 e EP-11. A página inicial pode ser simples na Fase 1;
observabilidade detalhada, reprocessamento e visão ampla de jobs evoluem
na Fase 2.

### EP-13 --- Estrutura de Comunidades, Projetos e Times

-   US-13.1 --- Owner/Admin criam Comunidades.
-   US-13.2 --- Criar Projetos dentro de uma Comunidade.
-   US-13.3 --- Criar Times dentro de Comunidades.
-   US-13.4 --- Associar múltiplos Times a um Projeto e um Time a
    múltiplos Projetos da mesma Comunidade.
-   US-13.5 --- Aplicar herança de acesso e restrições específicas sem
    conceder acesso automático a canais/documentos privados.

Dependências: EP-11.

### EP-14 --- Central de atribuições

-   US-14.1 --- Criar atribuição a partir de issue Jira existente.
-   US-14.2 --- Impedir mais de uma atribuição ativa para a mesma issue.
-   US-14.3 --- Definir Time responsável, responsável principal e
    participantes.
-   US-14.4 --- Implementar estados fixos da atribuição e histórico.
-   US-14.5 --- Cancelar com histórico e permitir reabertura por Master
    com justificativa.
-   US-14.6 --- Comentários na atribuição.
-   US-14.7 --- Preservar histórico para permitir nova atribuição à
    issue depois de concluída/cancelada.
-   US-14.8 --- Permitir templates reutilizáveis de atribuição com
    checklists e critérios sugeridos, preservando a origem dos critérios
    Jira e exigindo confirmação do usuário antes de aplicar um template.

Dependências: EP-11, EP-12, EP-13. Templates iniciais devem ser simples;
construtor avançado ou biblioteca compartilhada não fazem parte deste
escopo sem decisão posterior.

### EP-15 --- Critérios de aceite e evidências

-   US-15.1 --- Importar critérios da descrição Jira e permitir
    critérios complementares do Vulpes.
-   US-15.2 --- Validar/editar critérios em Markdown Given/When/Then.
-   US-15.3 --- Política por Projeto para exigir critérios; exceções de
    Master com justificativa/auditoria.
-   US-15.4 --- Anexar evidências de texto, link e arquivo por critério.
-   US-15.5 --- Sugerir evidências GitHub (branches, commits, PRs,
    checks) dentro da atribuição; toda associação precisa de confirmação
    explícita e nunca pode ser criada silenciosamente.
-   US-15.6 --- Marcar critério como não aplicável com justificativa e
    aprovação Master.
-   US-15.7 --- Bloquear envio à revisão enquanto critérios obrigatórios
    não estiverem evidenciados/atendidos.

Dependências: EP-12 e EP-14. Limites de arquivos e política de
armazenamento precisam de definição.

### EP-16 --- Revisão e aprovação

-   US-16.1 --- Enviar atribuição para fila de revisão.
-   US-16.2 --- Qualquer Master da Comunidade pode assumir uma revisão.
-   US-16.3 --- Exibir quem assumiu a revisão e evitar duas revisões
    concorrentes.
-   US-16.4 --- Aprovar ou solicitar ajustes por critério, com
    comentários.
-   US-16.5 --- Permitir rodadas ilimitadas, mantendo histórico e SLA de
    processo.
-   US-16.6 --- Registrar decisões, autores, datas e justificativas na
    auditoria.
-   US-16.7 --- Implementar Review Inbox dedicada para Masters, com fila
    de atribuições aguardando revisão, filtros úteis, indicação de quem
    assumiu cada revisão e acesso direto ao contexto completo; manter a
    regra de uma revisão concorrente por atribuição.

Dependências: EP-14 e EP-15. A Review Inbox é parte do fluxo essencial da
Fase 1 (Q77-A), não um painel analítico opcional.

### EP-17 --- Confirmação no Jira

-   US-17.1 --- Após aprovação, solicitar transição Jira configurada.
-   US-17.2 --- Marcar atribuição como Concluída somente após
    confirmação da API.
-   US-17.3 --- Tratar falha como pendente/reconciliável, sem declarar
    sucesso.
-   US-17.4 --- Garantir idempotência para evitar transições/efeitos
    duplicados.

Dependências: EP-12 e EP-16.

### EP-18 --- Notificações, privacidade e auditoria

-   US-18.1 --- Notificações in-app.
-   US-18.2 --- E-mails transacionais.
-   US-18.3 --- Auditoria de ações relevantes desde a Fase 1.
-   US-18.4 --- Exportação, exclusão e retenção documentada desde a
    Fase 1.
-   US-18.5 --- Preferências de notificação por tipo de evento e proteção
    de dados pessoais.
-   US-18.6 --- Agrupar notificações relacionadas para reduzir ruído;
    oferecer resumos diários/semanais na evolução da Fase 2, respeitando
    preferências e permissões de cada usuário.

Dependências: EP-10 e EP-11. Fornecedor SMTP/e-mail e política de
retenção padrão ainda precisam ser decididos. Preferências básicas e
agrupamento entram na Fase 1; resumos programados amadurecem na Fase 2.

### EP-19 --- Interface dos novos módulos

-   US-19.1 --- Criar frontend React + TypeScript + Vite para novos
    módulos.
-   US-19.2 --- Implementar design system limpo, acessível, claro/escuro
    e PT-BR.
-   US-19.3 --- Estados de carregamento, sem dados, parcial, stale, erro
    e sem permissão.
-   US-19.4 --- Desktop-first com jornadas essenciais utilizáveis em
    celular.
-   US-19.5 --- Integração com API e cliente tipado.
-   US-19.6 --- Definir Meu Trabalho como página inicial após login, com
    widgets pessoais orientados a atribuições, revisões, atualizações e
    bloqueios relevantes.
-   US-19.7 --- Permitir mover, ocultar e reordenar widgets, salvando a
    configuração por usuário e preservando um layout padrão recuperável.
-   US-19.8 --- Oferecer lista de atribuições com painel lateral de
    consulta rápida e página completa de detalhes.
-   US-19.9 --- Permitir criar, editar e remover views/filtros salvos por
    usuário, respeitando permissões no momento de cada consulta.
-   US-19.10 --- Iniciar com densidade visual Padrão; suportar layout
    responsivo para desktop e jornadas móveis essenciais.
-   US-19.11 --- Criar assistente guiado de configuração pós-instalação
    para Organização, Jira Cloud, GitHub, Projetos e Times, com testes de
    conexão, progresso recuperável e controle de acesso Owner/Admin.
-   US-19.12 --- Implementar autosave de rascunhos com indicação de
    salvamento, recuperação após falhas e confirmação para ações
    destrutivas.
-   US-19.13 --- Implementar jornadas móveis para consulta, comentários,
    revisão e ações básicas; manter edição avançada prioritariamente no
    desktop.
-   US-19.14 --- Integrar busca global inicial de dados internos do
    Vulpes e issues Jira Cloud, com resultados separados por origem,
    autorização no backend e indicação de dados antigos/indisponíveis.

Dependências: EP-10 e contratos estáveis. O assistente configura a
aplicação após o deploy Docker Compose; não substitui o procedimento
operacional de instalação/atualização nem concede permissões adicionais.

**Critério de saída da Fase 1:** demonstração com usuário autenticado:
Owner/Admin organiza acesso; Master cria atribuição de issue Jira; DEV
adiciona evidências critério a critério; Master assume revisão; devolve
ou aprova; Vulpes confirma transição Jira; atribuição só então fica
Concluída. Auditoria e notificações registram o fluxo. Usuário sem
permissão não acessa os dados. A navegação inicial leva a Meu Trabalho;
Masters dispõem da Review Inbox; atribuições podem ser abertas em painel
lateral ou página completa; busca Vulpes/Jira, views salvas e configuração
guiada estão disponíveis conforme as permissões. O layout inicia em
densidade Padrão e as jornadas móveis essenciais permitem consulta,
comentários e revisão.

## Fase 2 --- Persistência analítica, sincronização robusta e expansão do fluxo

Objetivo: tornar histórico e operação confiáveis para múltiplos Times
dentro da Organização.

Épicos: - **EP-20 --- Analytics persistente:** snapshots, eventos,
histórico e consultas no PostgreSQL; Streamlit passa gradualmente a
consumir dados persistidos. - **EP-21 --- Sincronização avançada:**
reconciliação, limites de API, central de jobs, conflitos e
reprocessamento. - **EP-22 --- Atribuições avançadas:** dependências
entre atribuições, subatribuições e replanejamento, somente após validar
necessidade. - **EP-23 --- Permissões ampliadas:** perfis de permissão e
ACL por recurso se necessário, sem papéis globais arbitrários. - **EP-24
--- Operação e confiabilidade:** backup/restore, métricas de fila,
observabilidade e testes de carga direcionados.

### EP-25 --- Produtividade pessoal e navegação avançada

-   US-25.1 --- Adicionar Command Palette acionada por Ctrl+K, com ações
    e destinos disponíveis conforme papel e permissões; incluir atalhos
    de teclado documentados sem tornar a navegação dependente deles.
-   US-25.2 --- Expandir a busca global para artefatos GitHub (branches,
    commits e PRs) conforme sincronização e permissões disponíveis.
-   US-25.3 --- Disponibilizar visão "O que mudou desde minha última
    visita?", apoiada em eventos persistidos e filtrada pelo acesso do
    usuário.
-   US-25.4 --- Criar linha do tempo pessoal privada, reunindo atividades
    que o próprio usuário pode visualizar; não gerar ranking ou score de
    produtividade.
-   US-25.5 --- Adicionar modo foco simples para reduzir elementos
    secundários durante o trabalho em uma atribuição, sem alterar estados
    ou permissões.
-   US-25.6 --- Oferecer seletor de densidade Confortável, Padrão e
    Compacto, preservando a preferência por usuário.
-   US-25.7 --- Criar caixa pessoal de captura rápida para ideias e tarefas
    ainda não organizadas; itens capturados não são atribuições nem
    alteram Jira até que o usuário os organize e vincule a uma issue
    elegível.
-   US-25.8 --- Implementar resumos de notificações diários/semanais,
    configuráveis por usuário e sem duplicar eventos já agrupados.

Dependências: EP-10, EP-14, EP-18 e EP-20/EP-21 para histórico e eventos
confiáveis. Busca GitHub exige dados disponíveis e ACL; busca do Knowledge
Hub continua na Fase 3.

Critério de saída: Analytics usa dados persistidos com equivalência
funcional documentada; sincronização é idempotente e recuperável;
múltiplos Times usam atribuições sem vazamento de dados. A experiência
pessoal tem histórico, views e preferências consistentes, sem expor
atividades privadas de outros usuários.

## Fase 3 --- Knowledge Hub e comunicação por Times

Objetivo: aproximar documentação e comunicação do trabalho.

Épicos:

- **EP-30 --- Knowledge Hub:** documentos Markdown, pastas, anexos,
  busca, histórico e vínculos com Projetos/atribuições.
- **EP-31 --- ADRs:** criar, revisar, aprovar, substituir e vincular
  decisões.
- **EP-32 --- Canais de Times:** canais, mensagens, threads, menções,
  anexos e notificações.
- **EP-33 --- Permissões e retenção de conteúdo:** aplicar acesso em
  busca, prévia, download e histórico.
- **EP-34 --- Pesquisa contextual:** busca em documentos, atribuições,
  issues, PRs e mensagens, respeitando ACL; completar a busca global com
  o Knowledge Hub.
- **EP-35 --- Experiência ampliada:** PWA e preferências avançadas quando
  justificadas.

A decisão "construir chat ou integrar solução existente" permanece
pendente e deve ser resolvida por spike/ADR antes do desenvolvimento dos
canais.

Critério de saída: documentos e canais são utilizáveis, pesquisáveis e
respeitam permissões e retenção.

## Fase 4 --- Automações e IA assistiva

Objetivo: automatizar tarefas repetitivas com segurança e oferecer
análise contextual sem autonomia indevida.

Épicos:

- **EP-40 --- Catálogo de automações:** gatilho → condição → ação;
  presets iniciais; simulação, idempotência, limites e desligamento.
- **EP-41 --- Gateway de IA:** provedor configurável, desligado por
  padrão, política de dados e limites de custo.
- **EP-42 --- Assistente somente leitura:** perguntas e resumos com
  fontes, período, permissões e distinção entre fato/inferência. Incluir
  resumos de issue + PR e alterações associadas, bem como resumo do que
  mudou desde a última revisão.
- **EP-43 --- Sugestões com aprovação:** sugerir critérios de aceite,
  evidências e sínteses de revisão; cada sugestão deve apontar as fontes
  utilizadas e exigir aprovação humana antes de alterar conteúdo ou
  vincular artefatos. A IA nunca aprova atribuições sozinha.
- **EP-44 --- Avaliações e segurança:** testes adversariais, avaliação de
  qualidade e proteção contra prompt injection.

Critério de saída: respostas citam fontes; recuperação respeita
permissões; IA não executa ações de escrita sem aprovação humana;
automações têm trilha de auditoria e mecanismos de parada.

## Fase 5 --- SaaS e expansão comercial

Objetivo: transformar a solução híbrida em oferta SaaS operacional e
comercial.

Épicos: - **EP-50 --- Multi-organização SaaS:** administração de
tenants, isolamento, sessão e recursos entre Organizações. - **EP-51 ---
Billing e planos:** planos, limites por
usuários/projetos/funcionalidades e cobrança. - **EP-52 --- Operação
SaaS:** provisionamento, backups por tenant, observabilidade, suporte,
status e recuperação. - **EP-53 --- Distribuição self-hosted:**
empacotamento, configuração, atualização, suporte e política de
funcionalidades. - **EP-54 --- Expansões futuras:** OAuth individual,
colaboradores externos, chat avançado, integrações adicionais,
aplicativo nativo ou agente de desenvolvimento, conforme demanda e
aprovação.

Critério de saída: operação multi-organização comprovada, cobrança e
limites funcionais, isolamento testado, suporte e recuperação
documentados.

------------------------------------------------------------------------

# 7. Critérios transversais de qualidade

## 7.1 Definition of Ready

Uma US só entra em implementação quando: - tem objetivo e ator claros; -
tem critérios de aceite verificáveis em Dado/Quando/Então; - tem
dependências identificadas; - tem tamanho P/M/G; - tem impacto em
permissões, dados pessoais, auditoria e integrações avaliado; - tem
desenho de interface quando necessário; - não depende de decisão crítica
ainda aberta.

## 7.2 Definition of Done

Uma US só é concluída quando: - implementação revisada; - testes
unitários e de integração adequados; - testes de autorização/RLS quando
aplicável; - estados de erro, parcial, stale, vazio e sem permissão
tratados; - nenhum segredo em logs, código ou pacote; - auditoria de
ações relevantes; - migrações reproduzíveis e rollback documentado
quando houver banco; - documentação e changelog atualizados; -
demonstração ou evidência verificável anexada.

## 7.3 Requisitos não funcionais

-   **Segurança:** autorização no backend; deny-by-default; segredos
    criptografados; RLS; varredura de dependências e segredos.
-   **Privacidade:** finalidade, retenção, exportação e exclusão; dados
    externos enviados à IA somente conforme política explícita.
-   **Confiabilidade:** jobs idempotentes, retry, reconciliação, backup
    e restore testados.
-   **Transparência:** falha não é vazio; stale/parcial identificados;
    campos ausentes não viram zero.
-   **Acessibilidade:** WCAG 2.2 AA como alvo para jornadas principais.
-   **Idioma:** PT-BR primeiro; textos centralizados e arquitetura
    i18n-ready.
-   **Pessoas:** sem ranking ou score individual de produtividade.
-   **Portabilidade:** Docker Compose como instalação inicial
    self-hosted.

## 7.4 Requisitos transversais de UX (V1.2)

-   **Contexto preservado:** abrir o painel lateral não deve retirar o
    usuário da lista, dos filtros ou da posição em que estava; a página
    completa deve permitir aprofundamento e retorno previsível.
-   **Meu Trabalho:** os widgets devem ser relevantes ao papel e às
    permissões; estados vazios devem orientar o próximo passo sem criar
    tarefas fictícias.
-   **Personalização segura:** preferências, widgets e views são por
    usuário; alterar a apresentação não pode alterar permissões ou dados
    compartilhados.
-   **Busca permission-aware:** aplicar autorização no backend, inclusive
    em contagens, sugestões, previews e resultados externos; não revelar
    títulos ou snippets de recursos sem acesso.
-   **Integrações transparentes:** exibir última sincronização e estado
    real; oferecer retry somente a papéis autorizados; nunca confundir
    falha de sincronização com ausência de dados.
-   **Autosave:** indicar salvando/salvo/falha; recuperar rascunhos sem
    duplicar submissões e resolver conflitos sem sobrescrever conteúdo
    silenciosamente.
-   **Ações destrutivas:** explicar consequência e pedir confirmação;
    ações de revisão/aprovação também devem deixar claro o efeito sobre
    atribuição e Jira.
-   **Mobile:** priorizar leitura, comentários, acompanhamento e revisão;
    formulários extensos e edição avançada podem direcionar ao desktop.
-   **Consistência:** manter mesmos nomes, estados, filtros e regras entre
    widgets, lista, painel, página completa e notificações.
-   **Atividade pessoal:** timeline e novidades devem mostrar apenas
    eventos acessíveis ao usuário; não podem ser transformadas em ranking
    individual ou mecanismo de vigilância.
-   **Ajuda contextual:** o setup guiado e os estados de erro devem
    explicar o que falta, por que importa e qual é a próxima ação segura.

------------------------------------------------------------------------

# 8. Conflitos, riscos e decisões de reconciliação

1. **Fase 1 ampla:** o piloto tem linha de corte definida em Q24-A: fluxo completo de atribuição, permissões mínimas, evidências básicas e confirmação Jira; refinamentos visuais e relatórios podem ser adiados.
2. **Permissões:** Q1, Q3, Q4, Q54 e Q55 definem os principais limites. A matriz detalhada por ação deve ser mantida como artefato de implementação, sem introduzir papéis customizados na Fase 1.
3. **Atribuições:** Q34/Q35 foram consolidadas: Master escolhe reabrir atribuição existente ou criar nova para a mesma issue, com justificativa e histórico.
4. **Q52:** a resposta válida é Q52-B: testes E2E para fluxos críticos, além de testes unitários/de integração apropriados. A referência anterior a “F” foi esclarecida como intenção de dar cobertura E2E aos fluxos importantes.
5. **Retenção:** Q10-D e Q64-A exigem políticas separadas por tipo de dado (auditoria, arquivos, mensagens, logs e demais conteúdos), definidas por Organização. Não assumir retenção ilimitada nem expiração única.
6. **Arquivos:** Q8-A define 20 MB por arquivo e 100 MB por atribuição. Q9-A define volume persistente local com interface de storage e caminho para S3. Q62-A define allowlist; Q63-A exige interface preparada para scanner e bloqueio de arquivos não verificados conforme configuração.
7. **Licença e monetização:** não definidas agora. Q18 estabelece decisão somente antes do início da Fase 5 ou antes de publicação externa que exija licença definida. Q19/Q20 ficam adiadas até a Fase 5/validação comercial. O deploy inicial para uso próprio não depende de SaaS ou monetização.
8. **Jira:** Cloud apenas na primeira versão (Q23-A). Issues inacessíveis permanecem vinculadas à atribuição, com integração indisponível e resolução pelo Master (Q7-A).
9. **Critérios Jira:** se o parser não identificar critérios, emitir aviso e permitir que Master adicione/ajuste manualmente (Q59-A). Alterações no Jira colocam critérios afetados/dependentes em revalidação e exigem revisão do Master (Q60-A).
10. **Estado de integração:** estado interno da atribuição e estado de sincronização são máquinas separadas (Q61-A). Falha de sync não deve ser confundida com estado do trabalho.
11. **RLS:** o spike reporta seis testes aprovados, mas o runtime principal não integra banco/RLS.
12. **Chat:** decisão de construir ou integrar continua dependente do spike e ADR-016 (Q16-A).
13. **Identidade técnica:** README, package name, ADRs e patches antigos ainda podem usar “Hub”; migração deve ser planejada e não realizada automaticamente.
14. **ZIP atual sem Git metadata:** não é possível determinar commit/branch ou comparar com histórico remoto a partir deste pacote.
15. **Relatórios de teste:** distinguir resultados reportados em `MVP_STATUS.md` de testes executados nesta sessão; a coleta da suíte foi bloqueada por dependência ausente.

------------------------------------------------------------------------

# 9. Decisões Q1--Q24 consolidadas

## Bloco A --- Papéis e administração

- **Q1-A:** Owner é o proprietário máximo. Admin administra usuários, Comunidades e configurações comuns, mas não transfere propriedade nem altera billing/segurança crítica.
- **Q2-A:** somente Owner/Admin configuram integrações e credenciais da Organização.
- **Q3-A:** Master central não cria nem administra Comunidades; essa responsabilidade é de Owner/Admin.
- **Q4-A:** DEV TEAM pode participar de várias Comunidades e Times por associações explícitas, com permissões independentes.

## Bloco B --- Atribuições e Jira

- **Q5-A:** Master configura a transição/status Jira de destino por Projeto; Vulpes valida sua disponibilidade.
- **Q6-A:** Master pode reabrir atribuição concluída com justificativa e auditoria; executar transição Jira correspondente quando configurada.
- **Q7-A:** issue removida, arquivada ou inacessível não cancela a atribuição; integração fica indisponível e exige resolução do Master.

## Bloco C --- Arquivos e privacidade

- **Q8-A:** limite inicial de 20 MB por arquivo e 100 MB por atribuição.
- **Q9-A:** volume local persistente na Fase 1, com interface de armazenamento e caminho de migração para S3.
- **Q10-D:** retenção configurável por Organização e diferenciada por tipo de dado.
- **Q11-A:** ao remover usuário, revogar acesso, preservar auditoria e anonimizar referências pessoais quando necessário/permitido.

## Bloco D --- Sincronização e notificações

- **Q12-A:** idempotência por ID externo/evento e reconciliação pelo estado atual.
- **Q13-A:** SMTP configurável para self-hosted; SaaS poderá usar provedor gerenciado.
- **Q14-A:** falhas de e-mail são retentadas em background, com histórico/status, sem bloquear o fluxo principal.

## Bloco E --- Conhecimento, canais e experiência

- **Q15-A:** Mermaid em Markdown na Fase 3; ferramentas visuais externas podem ser avaliadas posteriormente.
- **Q16-A:** realizar spike comparando chat próprio e integração Mattermost/Matrix; decidir por ADR antes de implementar.
- **Q17-A:** tema claro/escuro por usuário na Fase 1; cores de destaque e personalização ampliada depois.

## Bloco F --- Comercial, licença e distribuição

- **Q18:** licença será decidida somente antes do início da Fase 5 ou antes de publicação externa que exija essa decisão. Não escolher agora MIT/Apache, AGPL, source-available ou dual license.
- **Q19-E e Q20-E:** modelo self-hosted, SaaS, planos, limites e preços ficam adiados até a Fase 5/validação comercial. Não são requisitos para o deploy inicial de uso próprio.

## Bloco G --- Operação e entrega

- **Q21-A:** documentar backup/restauração de PostgreSQL e arquivos; teste de restore obrigatório.
- **Q22-A:** imagens versionadas, migrações controladas, backup pré-upgrade e rollback documentado.
- **Q23-A:** Jira Cloud apenas na primeira versão.
- **Q24-A:** piloto de cinco pessoas prioriza fluxo completo de atribuição, permissões mínimas, evidências básicas e Jira confirmado; refinamentos visuais/relatórios podem ficar para depois.

------------------------------------------------------------------------

# 10. Próxima revisão documental

A V1.2 consolida as respostas Q1--Q90. Antes de iniciar implementação de cada épico:

1. atualizar ADRs e plano de implementação quando houver decisão que os contradiga;
2. detalhar a matriz de permissões por ação, mantendo os papéis fixos;
3. definir políticas concretas de retenção por tipo de dado e Organização, respeitando requisitos legais aplicáveis;
4. especificar configuração do scanner, allowlist e comportamento de arquivos não verificados;
5. realizar spike e ADR para chat antes de qualquer implementação;
6. reestimar US com P/M/G, dependências e capacidade real; não transformar durações do plano em compromissos;
7. detalhar as especificações das novas jornadas de Meu Trabalho, Review Inbox, busca, setup guiado, views salvas, templates e mobile antes das respectivas US;
8. definir eventos e regras de privacidade para timeline pessoal, resumos e "mudanças desde a última visita";
9. manter esta V1.2 como referência aprovada; revisões futuras devem registrar versão, data, decisões alteradas e aprovação do usuário quando afetarem o escopo do produto.

A V1.2 é uma consolidação de decisões de produto e **não autoriza automaticamente a implementação de todas as US**. O deploy inicial para uso próprio pode ocorrer antes de qualquer decisão de SaaS/licença, desde que respeite as decisões técnicas, de segurança e privacidade já estabelecidas.

------------------------------------------------------------------------

# 11. Registro das respostas Q25--Q53

As respostas abaixo são decisões do usuário. As letras preservam a opção selecionada; a interpretação textual segue o conteúdo da pergunta recuperado.

# 12. AI-ready: protocolo de trabalho baseado em ZIP

## 12.1 Antes de analisar

1.  Confirmar nome e identidade do projeto; Vulpes Work é o nome de
    produto vigente.
2.  Listar arquivos do ZIP e registrar tamanho, hash e metadados
    disponíveis.
3.  Procurar versão/commit/data no próprio pacote; não presumir Git
    metadata.
4.  Separar código canônico de `.coverage`, logs, resultados, patches,
    arquivos temporários e exemplos.
5.  Não presumir acesso a GitHub, branches, CI remoto, banco, APIs reais
    ou ambiente do usuário.

## 12.2 Ao responder ou implementar

-   Separar **DECIDIDO**, **OBSERVADO**, **PLANEJADO**, **INFERIDO** e
    **EM ABERTO**.
-   Usar decisão mais recente do usuário como autoridade; código
    demonstra estado, não altera requisito.
-   Citar caminhos de arquivo exatos para evidências.
-   Distinguir testes reportados no ZIP, testes executados nesta sessão
    e testes não executados.
-   Não executar chamadas reais a Jira/GitHub nem expor segredos.
-   Não implementar sugestões de IA como requisitos sem aprovação
    explícita.
-   Se houver conflito crítico, interromper a decisão afetada e
    perguntar.
-   Propor patch/arquivo revisado; não afirmar que alterou repositório
    remoto ou local.
-   Comparar ZIPs apenas se os dois pacotes estiverem disponíveis.

## 12.3 Relatório padrão de ZIP (Q45-C)

Resumo curto contendo: identidade/hash; arquitetura atual; módulos
presentes; implementação comprovada; lacunas contra o Documento Geral;
conflitos; status de testes com proveniência; riscos e próximos passos.
Relatório completo de arquivos, classes, testes e recomendações somente
sob demanda.

## 12.4 Precedência de fontes (Q44-B)

1.  Instrução/decisão explícita mais recente do usuário.
2.  Documento Geral aprovado.
3.  ADR aceita e vigente, sem conflito com decisão posterior.
4.  Plano de implementação e documentos auxiliares.
5.  Código/testes/ZIP como evidência do estado implementado.

Registrar conflitos. Não resolver silenciosamente questões críticas de
produto, segurança ou arquitetura.

------------------------------------------------------------------------

# 13. Mapa documental recomendado

-   **Documento Geral (este):** visão, escopo, decisões de produto,
    módulos, fluxos, roadmap, AI-ready e pendências.
-   **Plano de Implementação:** épicos, US, dependências, estimativas,
    DoR/DoD e corte de MVP.
-   **ADRs:** decisões técnicas com contexto, alternativas,
    consequências e gatilho de revisão.
-   **Baseline/Relatório de ZIP:** inventário, hash, estado observado e
    verificações de cada pacote analisado.
-   **Guia de Desenvolvimento:** convenções de código, testes por tipo
    de mudança, comandos e revisão.
-   **Guia de Operação:** instalação, backup/restore, upgrade,
    configuração e troubleshooting.
-   **Guia de IA:** protocolo detalhado de trabalho, segurança,
    avaliação e limites de autonomia; este Documento Geral mantém o
    resumo.

------------------------------------------------------------------------

# 14. Atualização de baseline --- ZIP recebido em 27/11/2026

Esta revisão substitui a descrição anterior da baseline pelo pacote
atual:

-   ZIP: `Vulpes_Work-main.zip`
-   SHA-256:
    `ced071848f4e2fca79a6d2ed9a34c7117773f735703f56ef9a2ba0fb1192aafe`
-   126 arquivos; 32 arquivos de teste; 7.334 linhas físicas aproximadas
    em arquivos Python fora de `tests/`.
-   `compileall`: aprovado nesta sessão.
-   `pytest -q`: coleta bloqueada por falta de `streamlit` no ambiente
    de análise; não declarar resultado de suíte.
-   `docs/MVP_STATUS.md`: relata 440 testes/85% cobertura; equivalência
    com 224 asserções antigas e CI remoto ainda pendentes.
-   ZIP sem `.git`; commit/branch não verificáveis.
-   Artefatos de revisão/validação identificados para limpeza ou
    sanitização.


------------------------------------------------------------------------

# 15. Registro de decisões complementares Q54--Q68

- **Q54-A + D:** Owner/Admin administram membros; Master administra atribuições e revisões; DEV TEAM executa o trabalho. Além dessa regra-base, manter matriz detalhada de permissões por ação e escopo.
- **Q55-A:** Master pode alterar/remover outro Master dentro da Comunidade; Owner/Admin também podem fazê-lo, respeitando auditoria.
- **Q56-A:** entrada na Organização por convite de e-mail, aceite e associação explícita.
- **Q57-A:** conta global pode participar de várias Organizações; cada instalação self-hosted inicial hospeda uma Organização.
- **Q58-A:** Google como autenticação primária; suporte genérico a OIDC se viável na fundação.
- **Q59-A:** se o parser de critérios falhar, avisar e permitir ao Master adicionar/ajustar critérios manualmente.
- **Q60-A:** critérios alterados/dependentes ficam pendentes de revalidação e revisão do Master.
- **Q61-A:** estados da atribuição e da sincronização são separados; sync usa estados próprios (pendente, sincronizando, atualizado, falha, desatualizado ou equivalentes).
- **Q62-A:** aceitar arquivos por allowlist de tipos comuns e seguros; bloquear executáveis e formatos perigosos.
- **Q63-A:** preparar interface para scanner configurável; arquivos não verificados devem ser bloqueados conforme política/configuração, não tratados como seguros.
- **Q64-A:** retenção separada para auditoria, logs técnicos e conteúdo do usuário, além das categorias definidas em Q10-D.
- **Q65-B:** E2E nos fluxos críticos, complementado por testes unitários e de integração apropriados.
- **Q66-A:** consolidar Q34/Q35: Master escolhe reabrir atribuição anterior ou criar nova para a mesma issue; registrar escolha, justificativa e histórico.
- **Q67-A:** Documento Geral define módulos e regras; cada épico/US possui especificação própria.
- **Q68-D:** quando uma decisão técnica entrar em conflito com uma decisão de produto aprovada, a IA deve pedir confirmação antes de qualquer alteração relacionada.

------------------------------------------------------------------------

# 16. Registro das respostas Q69--Q90 --- experiência do usuário

As escolhas abaixo foram fornecidas pelo usuário em 27/11/2026. As letras
referem-se às alternativas apresentadas na rodada de perguntas de UX; a
interpretação operacional e a distribuição por fase estão consolidadas
nesta seção e no roadmap.

## Bloco A --- Experiência central

- **Q69-A:** Meu Trabalho é a página inicial após login.
- **Q70-A:** o usuário pode mover, ocultar e reordenar widgets.
- **Q71-B, futuramente D:** iniciar com densidade Padrão; em fase futura,
  permitir escolha entre Confortável, Padrão e Compacto.
- **Q72-C:** oferecer lista com painel lateral de consulta rápida e página
  completa da atribuição.
- **Q73-A:** permitir que usuários criem e salvem suas próprias views.

## Bloco B --- Navegação e descoberta

- **Q74-A:** busca global da plataforma e Jira na Fase 1; GitHub e
  Knowledge Hub entram nas fases em que seus dados estiverem integrados.
- **Q75-B:** Command Palette com Ctrl+K na Fase 2, depois de estabilizar
  o fluxo de navegação.
- **Q76-B:** visão do que mudou desde a última visita na Fase 2, baseada
  em histórico mais robusto.

## Bloco C --- Atribuições e revisão

- **Q77-A:** Review Inbox dedicada faz parte do fluxo essencial da Fase 1.
- **Q78-A:** templates reutilizáveis com critérios e checklist.
- **Q79-A:** caixa pessoal de captura para ideias/tarefas a organizar
  posteriormente; não é uma atribuição Jira e fica escalonada para a
  Fase 2 para não ampliar o corte crítico do piloto.

## Bloco D --- Notificações e integrações

- **Q80-A:** preferências por evento, agrupamento e resumos diários ou
  semanais; preferências e agrupamento básicos na Fase 1, resumos
  programados na Fase 2.
- **Q81-A:** sugestões de associação GitHub–Jira dentro da atribuição,
  sempre sujeitas à confirmação explícita do usuário; sem associação
  automática silenciosa. Reafirma Q36-B.
- **Q82-A:** página de saúde das integrações com conexão, última
  sincronização, falhas e nova tentativa por usuário autorizado.

## Bloco E --- Personalização e acessibilidade operacional

- **Q83-A:** linha do tempo pessoal privada, sem ranking ou score de
  produtividade; Fase 2, quando o histórico estiver persistido de forma
  consistente.
- **Q84-A:** assistente guiado para configurar a instalação própria:
  Organização, Jira, GitHub, Projetos e Times. Atua após o deploy e não
  substitui Docker Compose nem o procedimento operacional.
- **Q85-A:** autosave de rascunhos, recuperação e confirmação de ações
  destrutivas.
- **Q86-A:** experiência móvel para consulta, comentários, revisão e
  ações básicas; edição avançada permanece prioritariamente no desktop.
- **Q87-A:** priorizar densidade, widgets e views salvas; cores de destaque
  são adiadas.

## Bloco F --- IA e direção de UX

- **Q88-E:** na Fase 4, IA poderá resumir issue + PR e alterações, resumir
  o que mudou desde a última revisão e sugerir critérios de aceite e
  evidências. Toda saída deve indicar fontes e respeitar permissões; toda
  alteração ou vínculo exige aprovação humana.
- **Q89-A:** modo foco simples na Fase 2.
- **Q90-C:** filosofia de UX equilibrada entre velocidade, clareza e
  personalização por usuário.

## 16.1 Decisões de fase e limites de escopo

1. **Fase 1:** Meu Trabalho, widgets básicos personalizáveis, densidade
   Padrão, lista + painel + página completa, views salvas, busca Vulpes +
   Jira, Review Inbox, templates simples, sugestões GitHub sempre
   confirmadas, saúde básica das integrações, setup guiado, autosave,
   confirmações destrutivas e jornadas móveis essenciais.
2. **Fase 2:** Command Palette, expansão da busca para GitHub, "mudanças
   desde a última visita", timeline pessoal, modo foco, seletor de três
   densidades, caixa pessoal de captura e resumos programados de
   notificações.
3. **Fase 3:** busca do Knowledge Hub, respeitando as ACLs de documentos,
   ADRs, arquivos e Canais.
4. **Fase 4:** IA contextual com resumos e sugestões baseadas em fontes,
   sempre com aprovação humana antes de escrita ou associação.

A classificação acima resolve apenas o sequenciamento necessário ao
roadmap. Não cria autorização para expandir o piloto além dos critérios
prioritários definidos em Q24-A; itens de Fase 2/3/4 não devem bloquear a
entrega vertical essencial da Fase 1.
