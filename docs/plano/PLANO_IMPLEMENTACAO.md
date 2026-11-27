# Vulpes Work — Plano de Implementação

> **Versão:** 1.2 — alinhado ao Documento Geral aprovado
> **Data:** 27/11/2026
> **Status:** plano vigente; Fase 0 em fechamento, ainda não declarada concluída
> **Fonte normativa:** [`DOCUMENTO_GERAL.md`](../DOCUMENTO_GERAL.md)

Este documento organiza a execução por fases, épicos, histórias, dependências e critérios de saída. O Documento Geral define produto, decisões e limites; este plano não pode alterá-los silenciosamente. Detalhes técnicos específicos devem ser registrados em ADRs e especificações de épicos/US.

## 1. Precedência e regras de execução

1. Decisões explícitas mais recentes do usuário.
2. [`DOCUMENTO_GERAL.md`](../DOCUMENTO_GERAL.md), aprovado em 27/11/2026.
3. ADRs aceitas, desde que não contrariem decisão posterior.
4. Este plano e especificações de épicos/US.
5. Código, testes e ZIPs como evidência do estado implementado — não como autoridade de produto.

Regras obrigatórias:

- Não ampliar escopo sem registrar a proposta e obter aprovação do usuário.
- Não tratar funcionalidade planejada como implementada.
- Não declarar teste aprovado sem executá-lo; identificar resultados reportados por terceiros.
- Não reescrever o dashboard Streamlit na Fase 0; preservar comportamento e regras existentes.
- Não introduzir Redis, Kubernetes, microsserviços ou nova infraestrutura sem necessidade medida e ADR quando aplicável.
- Não iniciar login OIDC, FastAPI, React, banco do produto, automações ou IA durante a Fase 0.
- Não decidir licença, SaaS ou monetização na Fase 0. Resolver antes da Fase 5 ou de publicação externa que exija definição jurídica/comercial.
- Executar mudanças em branch de trabalho; criar commit local após verificações. Não fazer push sem autorização explícita.

## 2. Baseline de trabalho recebida

O pacote de referência enviado em 27/11/2026 tem SHA-256 `ced071848f4e2fca79a6d2ed9a34c7117773f735703f56ef9a2ba0fb1192aafe`, 146 entradas ZIP (126 arquivos) e não contém `.git`. Portanto, o ZIP não permite identificar branch, commit, remote nem verificar o histórico Git. A implementação e o commit devem ocorrer em um clone real do repositório, depois de confirmar a origem correta.

O pacote contém o dashboard Python/Streamlit, camadas `domain/`, `services/`, `application/` e `contracts/`, testes, Docker, CI e o spike isolado de RLS. Não foi identificado runtime principal com FastAPI, React, PostgreSQL/RLS integrado ou fluxo de atribuições — esses itens são planejados para fases posteriores.

### Evidências já registradas — não equivalem a uma nova execução

- `docs/MVP_STATUS.md` e `CHANGELOG.md` reportam 440 testes aprovados, 85% de cobertura, Ruff, mypy, `pip-audit` e Docker aprovados pelo mantenedor.
- O spike isolado de RLS reporta 6 testes aprovados.
- O probe do Jira consultou 20 issues sem falhas de API, mas nenhuma tinha a seção formal de critérios esperada; não foi possível medir a precisão do parser.
- A comparação das 224 asserções da baseline original com a suíte atual continua pendente.
- O primeiro resultado verde do GitHub Actions, inclusive matriz Python 3.12/3.13 e Gitleaks no histórico completo, continua pendente.
- O ZIP contém `.coverage`, `Vulpes_Hub-revisao.patch` e saídas reais em `tools/validation_output/`; precisam ser inspecionados/classificados antes de compartilhar outro pacote.

## 3. Fase 0 — Baseline e estabilização

**Objetivo:** manter o dashboard atual reproduzível, testável e seguro enquanto prepara a evolução do Vulpes Work. A Fase 0 não entrega ainda a nova plataforma colaborativa.

**Estado:** em fechamento. Há atividades e resultados importantes reportados, mas os critérios de saída abaixo não estão todos comprovados.

### EP-01 — Higiene do pacote, identidade e documentação

**Objetivo:** garantir que identidade, instruções, documentos e artefatos representem a baseline real e as decisões aprovadas.

- **US-01.1 — Documentação canônica:** adicionar o Documento Geral V1.2 aprovado; alinhar README, plano, status, changelog e índices às decisões vigentes.
- **US-01.2 — Identidade do produto:** usar Vulpes Work em documentação e interface nova. Nomes de diretório, pacote ou slug histórico podem permanecer até uma migração técnica segura; não inventar novo URL remoto.
- **US-01.3 — Higiene de artefatos:** verificar `.env`, logs, caches, `.coverage`, resultados reais de validação e patches. Não apagar patch potencialmente útil antes de examinar se contém trabalho ainda não incorporado. Remover do versionamento artefatos locais/sensíveis sem eliminar evidência necessária; manter apenas exemplos sanitizados.
- **US-01.4 — Instruções reproduzíveis:** documentar instalação limpa, execução local, Docker, testes e compartilhamento de pacote sem segredos.
- **US-01.5 — Changelog e auditoria:** manter histórico factual, com datas, proveniência e distinção entre reportado e executado.

**Aceite:** uma pessoa consegue identificar a fonte normativa, instalar e executar conforme instruções verificadas; documentos vigentes não apresentam decisões antigas como atuais; nenhum segredo, saída de validação real ou artefato local desnecessário é incluído no commit/pacote final.

### EP-02 — Qualidade, modularização e runtime

**Objetivo:** preservar o dashboard e comprovar que o ambiente e as fronteiras atuais continuam reproduzíveis.

- **US-02.1 — Ambiente Python:** validar Python 3.12 como ambiente principal, matriz CI com 3.12 e 3.13, `uv.lock` reproduzível e `uv sync --frozen`.
- **US-02.2 — Fronteiras de módulos:** preservar regras de negócio em `domain/`, integrações em `services/`, casos de uso em `application/`, contratos em `contracts/` e apresentação em `views/`. Não renomear `views/` para `pages/`.
- **US-02.3 — Composição Streamlit:** manter `app.py` como composição, configuração e roteamento, evitando nova concentração de regras ou refatoração ampla sem necessidade. A baseline anterior registrou 189 linhas; confirmar no clone atual e documentar qualquer desvio relevante.
- **US-02.4 — Configuração e segredos:** validar erros de configuração com mensagens claras; não imprimir tokens, cabeçalhos de autorização ou conteúdo sensível em logs.
- **US-02.5 — Concorrência e sincronização:** preservar idempotência/proteção contra sincronizações duplicadas e distinguir falha, parcial, vazio e dado desatualizado.
- **US-02.6 — Docker:** confirmar `docker compose up --build`, healthcheck e execução não-root; o Compose principal permanece apenas com o dashboard. PostgreSQL fica restrito ao Compose isolado do spike RLS.
- **US-02.7 — Regressão:** executar a suíte completa e comparar, quando houver a referência histórica disponível, as 224 asserções originais. Não substituir asserções antigas só para fazer os testes passarem.

**Aceite:** ambiente limpo reproduzível, verificações locais aprovadas, Docker saudável e comportamento do dashboard preservado por testes/evidências verificáveis.

### EP-03 — Decisões e provas técnicas

- **US-03.1 — ADRs:** manter ADRs 001–013 como aceitas conforme aprovação já registrada; nenhuma alteração nelas sem nova ADR ou substituição formal.
- **US-03.2 — Licença e distribuição:** FORA DA FASE 0. A diretriz provisória de direitos reservados permanece; licença, política de contribuição e modelo comercial só serão decididos antes da Fase 5 ou de publicação externa que exija decisão jurídica.
- **US-03.3 — RLS:** manter o spike isolado, sem integrar PostgreSQL ao runtime atual. Os 6 testes aprovados são evidência reportada; a integração por requisição pertence à Fase 1.
- **US-03.4 — Parser de critérios Jira:** registrar o resultado inconclusivo das 20 issues; repetir a medição quando o time adotar o template formal. Não bloquear a Fase 0 por ausência de dados de teste adequados.
- **US-03.5 — Login:** OIDC/Google não pertence à Fase 0; tratar na Fase 1, conforme Documento Geral.

### Critérios obrigatórios para encerrar a Fase 0

- [ ] Fonte Git real, branch de trabalho e baseline/commit de referência identificados; o ZIP por si só não satisfaz esse item.
- [ ] Documento Geral V1.2 aprovado e documentos operacionais sincronizados.
- [ ] Artefatos locais/sensíveis inspecionados e removidos/sanitizados do conjunto versionado quando aplicável.
- [ ] Instalação limpa por `uv sync --frozen --all-groups` comprovada.
- [ ] Ruff, mypy, pytest/cobertura e `pip-audit` executados e registrados.
- [ ] Matriz Python 3.12/3.13 aprovada no GitHub Actions.
- [ ] Gitleaks executado sobre o histórico Git completo, sem achados não resolvidos.
- [ ] Docker Compose validado, container saudável e usuário não-root confirmado.
- [ ] Comparação das 224 asserções originais concluída, ou bloqueio documentado com a referência histórica ausente; não declarar equivalência sem prova.
- [ ] Status das ADRs coerente; ADR-014 não tratada como bloqueio da Fase 0.
- [ ] Nenhuma mudança de produto da Fase 1 ou posterior introduzida incidentalmente.
- [ ] Commit local criado somente após os critérios técnicos exigidos e revisão do diff.

## 4. Fase 1 — Fundação da plataforma e piloto vertical de atribuições

**Objetivo:** um Time piloto executa atribuição → critérios → evidências → revisão → confirmação Jira. Analytics permanece em Streamlit.

| Épico | Escopo principal |
|---|---|
| EP-10 | Backend FastAPI, PostgreSQL, SQLAlchemy/Alembic, RLS, fila/workers, contratos e healthchecks. |
| EP-11 | Google/OIDC, Organização, membros, Owner/Admin/Master/DEV TEAM, convites e autorização central. |
| EP-12 | Integrações Jira/GitHub, sincronização, busca interna + Jira e saúde básica das integrações. |
| EP-13 | Comunidades, Projetos e Times, relações N:N e escopo de acesso. |
| EP-14 | Atribuições ligadas a issue Jira, participantes, estados, comentários e templates simples. |
| EP-15 | Critérios, evidências, anexos e sugestões GitHub sempre sujeitas à confirmação explícita. |
| EP-16 | Review Inbox, rodadas de revisão, aprovação e solicitação de ajustes por critério. |
| EP-17 | Transição Jira idempotente; concluir somente após confirmação da API. |
| EP-18 | Notificações in-app/e-mail, auditoria, privacidade, preferências básicas e agrupamento. |
| EP-19 | React + TypeScript + Vite; Meu Trabalho, widgets personalizáveis, densidade Padrão, views salvas, lista + painel + detalhe, setup guiado, autosave, ações destrutivas confirmadas e jornadas móveis essenciais. |

**Critério de saída:** demonstração ponta a ponta de atribuição, evidências, revisão, ajustes/aprovação e transição Jira confirmada, com auditoria, notificações e isolamento de permissões.

## 5. Fase 2 — Persistência analítica, sincronização robusta e produtividade pessoal

| Épico | Escopo principal |
|---|---|
| EP-20 | Analytics persistente com snapshots, eventos, histórico e consultas PostgreSQL; migração gradual do Streamlit para dados persistidos. |
| EP-21 | Sincronização avançada, reconciliação, limites de API, jobs e reprocessamento. |
| EP-22 | Dependências entre atribuições, subatribuições e replanejamento somente com necessidade validada. |
| EP-23 | ACL/permissões ampliadas sem papéis globais arbitrários. |
| EP-24 | Backup/restore, observabilidade, métricas de fila e testes de carga direcionados. |
| EP-25 | Command Palette Ctrl+K, busca GitHub, novidades desde a última visita, timeline privada, modo foco, seletor de densidade, caixa pessoal de captura e resumos programados de notificações. |

## 6. Fase 3 — Knowledge Hub e comunicação por Times

- **EP-30:** Knowledge Hub com Markdown, pastas, anexos, busca, histórico e vínculos.
- **EP-31:** ADRs com ciclo de revisão/aprovação/substituição.
- **EP-32:** Canais de Times, mensagens, threads, menções, anexos e notificações.
- **EP-33:** permissões e retenção de conteúdo.
- **EP-34:** pesquisa contextual em documentos, atribuições, issues, PRs e mensagens, sempre respeitando ACL.
- **EP-35:** PWA e experiência ampliada quando justificadas.

A decisão de chat próprio versus integração permanece dependente de spike e ADR antes da implementação.

## 7. Fase 4 — Automações e IA assistiva

- **EP-40:** automações por gatilho → condição → ação, com simulação, idempotência, limites e desligamento.
- **EP-41:** gateway de IA configurável, desligado por padrão, com política de dados e limites de custo.
- **EP-42:** assistente somente leitura com fontes, período, permissões e distinção entre fato e inferência; resumos de issue/PR e alterações.
- **EP-43:** sugestões de critérios, evidências e sínteses de revisão, sempre com fonte e aprovação humana; a IA não aprova atribuições.
- **EP-44:** avaliações de qualidade, testes adversariais e proteção contra prompt injection.

## 8. Fase 5 — SaaS e expansão comercial

- **EP-50:** multi-organização SaaS e isolamento de tenants.
- **EP-51:** billing, planos e limites.
- **EP-52:** operação SaaS, provisionamento, backups, suporte e recuperação.
- **EP-53:** distribuição self-hosted, empacotamento, configuração, atualização e suporte.
- **EP-54:** expansões futuras aprovadas (OAuth individual, colaboradores externos, chat avançado, integrações, app nativo ou agente).

Decisões de licença, monetização e distribuição devem estar resolvidas antes do início desta fase ou de publicação externa que exija definição jurídica.

## 9. Definition of Ready / Done

Aplicam-se as regras do Documento Geral V1.2, seções 7.1 e 7.2. Cada US deve ter ator, objetivo, critérios Dado/Quando/Então, dependências, tamanho P/M/G, impacto de segurança/permissões/dados pessoais e evidência de validação. Mudanças em banco devem ter migração reproduzível e rollback documentado. O DoD exige testes apropriados, revisão, documentação e evidência verificável.

## 10. Documentos auxiliares

- Documento de produto e decisões: [`../DOCUMENTO_GERAL.md`](../DOCUMENTO_GERAL.md).
- ADRs: [`../adr/ADR.md`](../adr/ADR.md) e [`../adr/README.md`](../adr/README.md).
- Estado do Development Analytics atual: [`../MVP_STATUS.md`](../MVP_STATUS.md).
- Prompt Mestre para executar a Fase 0: [`../prompts/PROMPT_MESTRE_FASE_0.md`](../prompts/PROMPT_MESTRE_FASE_0.md).
- Plano anterior mantido apenas como histórico: [`arquivo/PLANO_IMPLEMENTACAO_v1.0_SUPERADO.md`](arquivo/PLANO_IMPLEMENTACAO_v1.0_SUPERADO.md).
