# Vulpes Work — Plano de Implementação

> **Versão:** 1.2 — alinhado ao Documento Geral aprovado
> **Data:** 27/11/2026
> **Status:** plano vigente; validações técnicas da Fase 0 aprovadas em 28/11/2026; fechamento formal pendente de revisão/aplicação das alterações documentais e commit final.
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

### Evidências consolidadas da Fase 0 — 28/11/2026

Os resultados abaixo foram executados pelo mantenedor no clone Git real ou apresentados por ele como evidência. A proveniência específica está detalhada em `docs/MVP_STATUS.md` e `CHANGELOG.md`.

- Python 3.12.16 e 3.13.18: `uv sync --frozen --all-groups`, Ruff, mypy, pytest e `pip-audit` aprovados em ambas as versões; 440 testes por versão e 85% de cobertura.
- Docker Compose: configuração/build aprovados; container `healthy`, UID/GID `10001:10001` e endpoint de healthcheck HTTP 200.
- Gitleaks 8.30.1: os comandos `git` e `detect` do workflow foram executados no clone não raso; 5 commits com alterações examinados, sem achados.
- GitHub Actions: captura fornecida pelo mantenedor mostra os três checks bem-sucedidos — Python 3.12, Python 3.13 e Gitleaks — após push na branch `chore/phase-0-stabilization`. O SHA e a URL da execução não aparecem na captura; a evidência é classificada como reportada pelo mantenedor.
- Baseline `8412ce8`: comparação AST reportada preserva os 332 corpos das funções `test_*` presentes no snapshot; 40 novas funções foram adicionadas em `a812380`. A anotação “224 testes” do status histórico não corresponde ao inventário do snapshot e não há manifesto que identifique esses 224 itens; não se afirma equivalência literal 224/224.
- O pacote de compartilhamento mais recente contém 126 arquivos e exclui `.git`, segredos, caches, resultados reais de validação e logs. O Prompt Mestre temporário da Fase 0 foi removido do repositório; a pasta de prompts internos e padrões de arquivos `PROMPT_*.md` são ignorados pelo Git.

## 3. Fase 0 — Baseline e estabilização

**Objetivo:** manter o dashboard atual reproduzível, testável e seguro enquanto prepara a evolução do Vulpes Work. A Fase 0 não entrega ainda a nova plataforma colaborativa.

**Estado:** validações técnicas aprovadas; fechamento formal pendente da atualização documental final, revisão do diff e commit previsto neste plano.

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
- **US-02.3 — Composição Streamlit:** manter `app.py` como composição, configuração e roteamento, evitando nova concentração de regras ou refatoração ampla sem necessidade. A baseline registra 189 linhas; o limite operacional desta estabilização é 200 linhas, salvo justificativa documentada.
- **US-02.4 — Configuração e segredos:** validar erros de configuração com mensagens claras; não imprimir tokens, cabeçalhos de autorização ou conteúdo sensível em logs.
- **US-02.5 — Concorrência e sincronização:** preservar idempotência/proteção contra sincronizações duplicadas e distinguir falha, parcial, vazio e dado desatualizado.
- **US-02.6 — Docker:** confirmar `docker compose up --build`, healthcheck e execução não-root; o Compose principal permanece apenas com o dashboard. PostgreSQL fica restrito ao Compose isolado do spike RLS.
- **US-02.7 — Regressão:** executar a suíte completa e comparar os casos/asserções presentes no commit de referência identificado. O status histórico registra “224 testes”, mas o snapshot `8412ce8` contém 332 funções `test_*` e 607 nós `assert` dentro dessas funções; não existe manifesto para mapear os 224 itens mencionados. A comparação AST dos corpos de todas as 332 funções originais foi concluída e preservada; não declarar uma contagem literal “224/224”. Não substituir testes antigos só para fazer a suíte passar.

**Aceite:** ambiente limpo reproduzível, verificações locais aprovadas, Docker saudável e comportamento do dashboard preservado por testes/evidências verificáveis.

### EP-03 — Decisões e provas técnicas

- **US-03.1 — ADRs:** manter ADRs 001–013 como aceitas conforme aprovação já registrada; nenhuma alteração nelas sem nova ADR ou substituição formal.
- **US-03.2 — Licença e distribuição:** FORA DA FASE 0. A diretriz provisória de direitos reservados permanece; licença, política de contribuição e modelo comercial só serão decididos antes da Fase 5 ou de publicação externa que exija decisão jurídica.
- **US-03.3 — RLS:** manter o spike isolado, sem integrar PostgreSQL ao runtime atual. Os 6 testes aprovados são evidência reportada; a integração por requisição pertence à Fase 1.
- **US-03.4 — Parser de critérios Jira:** registrar o resultado inconclusivo das 20 issues; repetir a medição quando o time adotar o template formal. Não bloquear a Fase 0 por ausência de dados de teste adequados.
- **US-03.5 — Login:** OIDC/Google não pertence à Fase 0; tratar na Fase 1, conforme Documento Geral.

### Critérios obrigatórios para encerrar a Fase 0

- [x] Fonte Git real, branch `chore/phase-0-stabilization` e referência histórica `8412ce8` identificadas; o mantenedor reportou HEAD `1b90b1b` sincronizado com `origin/chore/phase-0-stabilization`.
- [x] Documento Geral V1.2 aprovado; README, Plano, MVP Status, Changelog, Auditoria, Dependências e índice ADR alinhados nesta atualização.
- [x] Artefatos locais/sensíveis inspecionados; pacote compartilhado de 126 arquivos sem `.git`, `.env`, logs, caches, `.coverage` ou saídas reais de validação. Prompt operacional removido e ignorado.
- [x] Instalação limpa por `uv sync --frozen --all-groups` comprovada em Python 3.12.16 e 3.13.18.
- [x] Ruff, mypy, pytest/cobertura e `pip-audit` executados nas duas versões: 440 testes por versão, 85% de cobertura, sem problemas de lint/tipos e sem vulnerabilidades conhecidas reportadas.
- [x] Matriz Python 3.12/3.13 aprovada no GitHub Actions, conforme captura fornecida pelo mantenedor.
- [x] Gitleaks 8.30.1 executado no histórico Git não raso, com o comando do workflow e sem achados; o check remoto também aparece aprovado na captura do mantenedor.
- [x] Docker Compose validado; container saudável, usuário não-root UID/GID 10001:10001 e healthcheck HTTP 200.
- [x] Comparação AST da suíte presente em `8412ce8` concluída: 332 corpos de funções `test_*` preservados; a anotação histórica “224 testes” não é reproduzível a partir do snapshot e essa divergência está documentada, sem alegar “224/224”.
- [x] Status das ADRs coerente; ADR-014 permanece pendente e não bloqueia a Fase 0.
- [x] Nenhuma funcionalidade de produto da Fase 1 ou posterior foi adicionada nesta atualização.
- [ ] Commit local definitivo criado após aplicar este pacote e revisar o diff. Mensagem obrigatória: `chore(phase-0): stabilize baseline and align project docs`.

**Observação de evidência:** a captura dos checks comprova três resultados verdes, mas não exibe o SHA nem a URL da execução. O mantenedor informa que a execução ocorreu após o push da branch de estabilização; preserve o link/ID da execução no registro do projeto quando disponível.

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
- Instruções operacionais temporárias de agentes não são distribuídas no repositório; os critérios permanentes de fase ficam neste plano.
- Plano anterior mantido apenas como histórico: [`arquivo/PLANO_IMPLEMENTACAO_v1.0_SUPERADO.md`](arquivo/PLANO_IMPLEMENTACAO_v1.0_SUPERADO.md).
