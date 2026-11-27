# Vulpes Work — Registro de Decisões Arquiteturais (ADRs)

Versão 1.2 · 27/11/2026 · Acompanha o Documento Geral V1.2 e o Plano de Implementação vigente do Vulpes Work.

## Como usar

O Documento Geral V1.2 aprovado pelo usuário é a fonte de verdade de produto; estas ADRs registram decisões técnicas e não podem contrariar decisões posteriores do usuário.

Cada ADR registra uma decisão técnica que afeta mais de um épico. **Status:** *Proposta* = registrada, mas ainda não aprovada; *Pendente* = depende de um spike, parecer ou informação externa; *Aceita* = aprovada pelo mantenedor. As ADRs 001 a 013 foram aprovadas em 27/11/2026. A ADR-014 continua pendente. Cada decisão tem um **gatilho de revisão**; uma ADR aceita só muda por outra ADR que a substitua.

| ID | Decisão | Status | Fase |
| --- | --- | --- | --- |
| ADR-001 | Monólito modular com fronteiras verificadas | Aceita | 0 |
| ADR-002 | Backend em Python 3.12 + FastAPI, preservando `domain/` | Aceita | 0 |
| ADR-003 | PostgreSQL único; fila no próprio Postgres; Redis adiado | Aceita | 0–1 |
| ADR-004 | Multi-tenancy com `tenant_id` + Row-Level Security | Aceita | 1 |
| ADR-005 | Autorização: RBAC + ACL por recurso, função central | Aceita | 1–2 |
| ADR-006 | Frontend React + TypeScript + Vite; Streamlit como Development Analytics | Aceita | 1 |
| ADR-007 | Sincronização Jira/GitHub: polling → webhooks, propriedade de campos, outbox | Aceita | 1–2 |
| ADR-008 | Credenciais de integração por organização, criptografadas | Aceita | 1 |
| ADR-009 | Tempo real: SSE primeiro, WebSocket com o chat | Aceita | 1, 3 |
| ADR-010 | Armazenamento de arquivos atrás de uma interface | Aceita | 1, 3 |
| ADR-011 | Critérios de aceite: template Markdown e versionamento | Aceita | 1 |
| ADR-012 | Estados da atribuição e mapeamento para status do Jira | Aceita | 1 |
| ADR-013 | IA: gateway híbrido, desligado por padrão, registro determinístico | Aceita | 4 |
| ADR-014 | Licença e distribuição | Pendente; não bloqueia a Fase 0; decidir antes da Fase 5/publicação externa | Antes da Fase 5 |
| ADR-015 | Privacidade, retenção, exportação e exclusão | Proposta | 1 |
| ADR-016 | Chat: construir ou integrar | Pendente (spike/ADR antes do EP-32, Fase 3) | 3 |
| ADR-017 | Observabilidade mínima | Proposta | 1 |

## ADR-001 — Monólito modular com fronteiras verificadas

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** uma equipe de 5 a 9 pessoas, instalação self-hosted simples e um domínio já consolidado. Microsserviços aumentariam operação sem benefício medido.
- **Decisão:** uma única aplicação backend, organizada em módulos por contexto: Identidade e Acesso, Trabalho (atribuições, critérios, evidências, revisão), Integrações, Analytics, Conhecimento, Comunicação, IA e Automação. Dependências fluem para o domínio; o domínio não importa FastAPI, Streamlit, banco nem SDKs. As fronteiras são verificadas no CI (import-linter ou equivalente). Workers rodam o mesmo código em processos separados.
- **Alternativas:** microsserviços (rejeitado: custo operacional); monólito sem fronteiras (rejeitado: acopla tudo).
- **Consequências:** um único deploy e uma única base de código; disciplina de fronteiras exige regra automática.
- **Revisar quando:** um módulo precisar escalar ou ser implantado de forma independente, com medição que comprove.

## ADR-002 — Backend em Python 3.12 + FastAPI, preservando `domain/`

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** `domain/` e `services/` concentram o conhecimento acumulado e 224 testes. Reescrever em outra linguagem duplicaria regras e criaria risco de divergência.
- **Decisão:** manter Python (3.12, testando também 3.13) e expor o produto com FastAPI, com contratos Pydantic e OpenAPI. `domain/` continua puro. O Python 3.10 sai da matriz (fim do suporte de segurança em outubro de 2026; confirmar em python.org).
- **Alternativas:** Node.js, Go, Rust, Java, C# (rejeitadas: reescrita sem gargalo medido).
- **Consequências:** ecossistema analítico em Python segue disponível; exige tipagem e disciplina.
- **Revisar quando:** benchmark mostrar gargalo de CPU que não se resolva em Python, caso em que se avalia um serviço especializado.

## ADR-003 — PostgreSQL único; fila no próprio Postgres; Redis adiado

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** cada serviço extra pesa na instalação self-hosted. O volume inicial é baixo.
- **Decisão:** PostgreSQL como única dependência de estado. Fila de jobs com Procrastinate (ou equivalente baseado em `SKIP LOCKED`), com retry, backoff com jitter, idempotência e tabela de falhas. Busca textual, `LISTEN/NOTIFY` e, na Fase 4, `pgvector` também no Postgres. Perfil mínimo de instalação: aplicação + PostgreSQL.
- **Alternativas:** Redis + Celery (mais peças); Arq, Dramatiq ou RQ (exigem Redis).
- **Consequências:** menos serviços; throughput de fila limitado ao do Postgres.
- **Revisar quando:** a fila passar de cerca de milhares de jobs por minuto, a latência de jobs degradar nas medições, ou o tempo real exigir pub/sub entre várias instâncias.

## ADR-004 — Multi-tenancy com `tenant_id` + Row-Level Security

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** o produto será uma instalação por organização primeiro, mas a arquitetura precisa estar pronta para SaaS. Adicionar isolamento depois é muito mais caro.
- **Decisão:** todas as tabelas de negócio têm `tenant_id`, com política de RLS no PostgreSQL. A aplicação conecta com um papel que não é dono das tabelas (para não contornar RLS) e define o tenant por transação. Testes negativos cobrem toda entidade. Não há tela de administração de múltiplos tenants na v1. Um ERD por contexto cresce junto com as fases.
- **Alternativas:** schema por organização; banco por organização (mais isolamento, mais operação); sem isolamento até precisar.
- **Consequências:** custo pequeno e constante em toda consulta; migrações precisam incluir a política.
- **Revisar quando:** um cliente exigir isolamento físico ou residir em região diferente, ou o número de tenants tornar o banco único inviável.

## ADR-005 — Autorização: RBAC + ACL por recurso, função central

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** dois papéis padrão (Master, DEV TEAM), Master delegado, perfis personalizados, permissão por recurso e busca e IA que precisam respeitar tudo isso.
- **Decisão:** uma função única `can(usuário, ação, recurso)`, que nega por padrão, usada por todos os endpoints, pela busca e pela recuperação da IA. Na Fase 1: RBAC com escopo (organização, comunidade, time). Na Fase 2: perfis como conjuntos nomeados de um catálogo fixo de permissões e ACL por recurso, com herança Organização → Comunidade → Time → Recurso, onde «negar» vence «permitir». Testes parametrizados cobrem a matriz.
- **Alternativas:** motor externo (OpenFGA, Cerbos, Casbin); ReBAC próprio.
- **Consequências:** um único ponto para auditar e testar; precisa nascer antes das telas.
- **Revisar quando:** a regra de herança ou o número de tipos de recurso tornar a função difícil de manter; avaliar motor externo.

## ADR-006 — Frontend React + TypeScript + Vite; Streamlit como Development Analytics

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** o Streamlit reexecuta o script a cada interação e o `app.py` já é grande; por outro lado, o dashboard atual tem regras e testes valiosos.
- **Decisão:** os módulos novos (atribuições, revisão, administração, canais, conhecimento) usam React + TypeScript + Vite, com cliente TypeScript gerado do OpenAPI e checado no CI. O Streamlit permanece como módulo Development Analytics, com login OIDC via `st.login` e, a partir da Fase 2, lendo do novo banco. Telas do analytics migram para React uma a uma, só quando houver ganho e testes de equivalência.
- **Alternativas:** manter só Streamlit; reescrever tudo em React de uma vez; NiceGUI ou Reflex.
- **Consequências:** duas tecnologias de interface durante a transição; navegação entre elas por links e login compartilhado.
- **Revisar quando:** o analytics exigir interações que o Streamlit não suporta, ou a manutenção dupla pesar mais que a migração.

## ADR-007 — Sincronização Jira/GitHub: polling → webhooks, propriedade de campos, outbox

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** o produto lê dados do Jira e do GitHub e passa a escrever no Jira (transição após aprovação). Falhas e divergências não podem virar dado falso.
- **Decisão:**
  - **Leitura:** Fase 1 com polling incremental (checkpoints; JQL por `updated`; GitHub por `since` e ETag quando houver). Fase 2 com webhooks assinados, eventos brutos guardados e deduplicados, mais reconciliação periódica. Regras atuais preservadas: falha não é ausência, dado antigo é identificado, falha não é cacheada como sucesso.
  - **Propriedade de campos (tabela fixa):** Jira = chave, status oficial, Story Points, critério original; Vulpes = critérios complementares, evidências, responsáveis da atribuição, aprovação; GitHub = commits e PRs.
  - **Conflitos:** guarda-se o último valor sincronizado; mudança dos dois lados vira item na fila de conflitos do Master (Fase 2). Nunca há sobrescrita silenciosa.
  - **Escrita:** outbox transacional. A decisão e a intenção de transição são gravadas na mesma transação; um worker executa com chave de idempotência; estados: pendente, confirmado, falhou. A atribuição só vira «Concluída» depois de ler o status no Jira.
- **Alternativas:** só polling; escrita direta na requisição do usuário (perde consistência em falha).
- **Consequências:** mais complexidade no início, em troca de não declarar sucesso indevido.
- **Revisar quando:** a tabela fixa de propriedade não atender a um cliente (torná-la configurável por campo, como previsto em H-50), ou limites das APIs mudarem.

## ADR-008 — Credenciais de integração por organização, criptografadas

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** hoje os tokens ficam em `.env`, o que não serve para várias organizações nem para container.
- **Decisão:** tokens por organização ficam no banco, criptografados em repouso, com a chave fora do banco (variável de ambiente ou secret manager). A API nunca devolve o segredo completo; logs nunca o contêm; há teste de conexão e rotação. Na Fase 1, o armazenamento local em `.env` será substituído pelo cadastro de integrações por organização. Na Fase 5: OAuth 2.0 da Atlassian e GitHub App.
- **Alternativas:** `.env` por instância; OAuth desde o início (mais seguro, mais trabalho de configuração e de aprovação das integrações).
- **Consequências:** o escopo do token define o que o Vulpes enxerga; por isso o Master define quais projetos cada time vê (EP-12).
- **Revisar quando:** começar a oferta SaaS, ou houver exigência de permissão por usuário do Jira.

## ADR-009 — Tempo real: SSE primeiro, WebSocket com o chat

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** a Fase 1 só precisa de notificações do servidor para o cliente; o chat (Fase 3) precisa de comunicação nos dois sentidos.
- **Decisão:** SSE para notificações, com reconexão automática. WebSocket só quando o chat existir. Na v1 (uma instância), `LISTEN/NOTIFY` do Postgres propaga eventos entre processos.
- **Alternativas:** WebSocket desde já; polling do cliente.
- **Consequências:** simples e passa por proxies comuns; mais de uma instância da API exigirá outro mecanismo de pub/sub.
- **Revisar quando:** houver mais de uma instância da API ou o chat estiver em desenvolvimento.

## ADR-010 — Armazenamento de arquivos atrás de uma interface

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** evidências precisam de arquivos já na Fase 1; anexos avançados chegam na Fase 3.
- **Decisão:** interface de armazenamento com dois drivers: volume local (Fases 1 e 2) e S3-compatível (Fase 3). Validação de tipo por conteúdo, não só pela extensão; limites de tamanho; download com cabeçalhos seguros (`Content-Disposition` e `nosniff`); permissões herdadas do recurso; antimalware assíncrono a partir da Fase 2, com quarentena. Antes de escolher o servidor S3-compatível para self-hosted, conferir licença e estado atual do projeto.
- **Alternativas:** só banco de dados; só S3 desde o início.
- **Consequências:** troca de driver sem mexer no domínio; migração de arquivos existentes será necessária na Fase 3.
- **Revisar quando:** o volume de arquivos ou a necessidade de versionamento exigir o driver S3.

## ADR-011 — Critérios de aceite: template Markdown e versionamento

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** o Jira não tem um campo padrão de critérios de aceite. Eles costumam ficar na descrição.
- **Decisão:** os critérios vivem numa seção «Critérios de aceite» da descrição, como checklist em Markdown, num template definido pelo spike US-03.4. O importador valida o formato e avisa linhas inválidas. Cada critério tem origem (Jira ou Vulpes) e versão. Mudança no Jira cria nova versão pendente; o Master aceita ou rejeita; nada é sobrescrito; evidências da versão antiga ficam «precisa revalidar».
- **Alternativas:** campo customizado (exige administrador do Jira); subtasks como critérios; formato Gherkin.
- **Consequências:** depende da adesão do time ao template (PA-5); criação de issue pelo Vulpes (Fase 2) já usa o template.
- **Revisar quando:** a taxa de leitura correta ficar abaixo do aceitável, ou o administrador do Jira puder criar um campo dedicado.

## ADR-012 — Estados da atribuição e mapeamento para status do Jira

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** a atribuição é a unidade de trabalho do Vulpes e não é a issue; seus estados e os do Jira não coincidem.
- **Decisão:** estados fixos: Rascunho, Atribuída, Em andamento, Em revisão, Ajustes solicitados, Aprovada, Concluída e Cancelada, com transições permitidas explícitas. Cada projeto tem um mapeamento configurável entre estados do Vulpes e status do Jira. «Concluída» só após a confirmação no Jira (ADR-007). O vínculo com a issue é N:N no modelo, com regra de 1 issue por atribuição na v1.
- **Alternativas:** usar os status do Jira diretamente; estados configuráveis por comunidade.
- **Consequências:** o Vulpes tem seu próprio fluxo, mas depende do mapeamento para escrever no Jira.
- **Revisar quando:** uma comunidade precisar de um fluxo diferente do padrão, ou houver atribuições com várias issues.

## ADR-013 — IA: gateway híbrido, desligado por padrão, registro determinístico

- **Status:** Aceita (aprovada pelo mantenedor em 27/11/2026)
- **Contexto:** a IA lerá código, issues, documentos e, com opt-in, mensagens de canais. Texto de issue, PR e mensagem é conteúdo não confiável e pode conter instruções maliciosas.
- **Decisão:** uma camada de gateway por organização, que suporta modelos locais (por exemplo Ollama ou vLLM) e externos, desligada por padrão, com política de dados (o que pode sair), cotas e limite de custo. A recuperação de contexto usa `can()` (ADR-005) antes de enviar ao modelo; conversas privadas nunca entram; mensagens de canais só com opt-in da comunidade. Conteúdo externo é tratado como dado, nunca como instrução; ferramentas de escrita exigem aprovação humana até haver evidência de qualidade. O registro de cada execução guarda entradas, fontes, chamadas de ferramenta, saídas e aprovações; a «justificativa» do modelo é apenas texto auxiliar. Avaliações de qualidade e testes adversariais rodam no CI. O agente de desenvolvimento (Fase 5) exige ambiente isolado, identidade própria, nenhum segredo dentro dele e sem rede de saída por padrão.
- **Alternativas:** só provedor externo; só local; sem IA.
- **Consequências:** mais trabalho antes da primeira funcionalidade de IA, em troca de segurança e auditabilidade.
- **Revisar quando:** as avaliações mostrarem qualidade suficiente para ampliar autonomia, ou a política de dados de um provedor mudar.

## ADR-014 — Licença e distribuição

- **Status:** Pendente — decisão deliberadamente adiada; não bloqueia a Fase 0. Resolver antes do início da Fase 5 ou antes de publicação externa que exija definição jurídica.
- **Contexto:** o objetivo atual é desenvolver e implantar o Vulpes Work para uso próprio. O deploy pode preceder a definição de SaaS, licença ou monetização. A preferência histórica por source-available (BSL ou similar) não foi ratificada como licença definitiva; qualquer licença continua sujeita a parecer jurídico.
- **Diretriz provisória vigente:** manter todos os direitos reservados até a definição jurídica definitiva, sem conceder licença de uso a terceiros. Esta diretriz é temporária; não escolhe a licença final e não define titularidade formal. Não executar trabalho jurídico nem tratar esta decisão como bloqueio de Fase 0.
- **Decisão proposta:** após o parecer jurídico, escolher entre BSL 1.1 (com data de conversão e uma restrição de uso definida), FSL, Elastic License v2 ou outra equivalente. Definir também a política de contribuição (CLA ou DCO) e a possibilidade de licença comercial dupla.
- **Alternativas:** MIT ou Apache (permissivas); AGPL (copyleft forte). Nenhuma dessas alternativas foi adotada.
- **Consequências:** até a decisão definitiva, este repositório não concede licença de uso, cópia, modificação ou distribuição a terceiros. O uso próprio pode avançar; antes de distribuição/publicação externa, a licença, titularidade e política de contribuição precisam ser decididas.
- **Revisar quando:** antes do início da Fase 5 ou de publicação externa que exija decisão jurídica; considerar parecer sobre licença, titularidade e política de contribuição.

## ADR-015 — Privacidade, retenção, exportação e exclusão

- **Status:** Proposta
- **Contexto:** o produto guarda dados de pessoas, código, comentários e, depois, mensagens. A LGPD se aplica.
- **Decisão:** retenção configurável por organização e por tipo de dado, com padrões documentados (valores a validar com o jurídico, PA-7); rotina agendada de aplicação; exportação por usuário e por organização em JSON e CSV; exclusão ou anonimização que preserva o histórico de entregas e a auditoria sem dados pessoais identificáveis; registro de finalidades. Presença, leitura e «digitando» são opt-in. Nenhuma métrica individual de produtividade é derivada desses sinais.
- **Alternativas:** retenção indefinida; tratar depois.
- **Consequências:** modelo de dados precisa distinguir dado pessoal de dado de histórico desde a Fase 1.
- **Revisar quando:** houver mudança legal, novo tipo de dado (mensagens, gravações) ou oferta SaaS em outra jurisdição.

## ADR-016 — Chat: construir ou integrar

- **Status:** Pendente (spike/ADR antes do EP-32, Fase 3)
- **Contexto:** a decisão P29 foi um chat próprio simples na Fase 3, reavaliando Mattermost ou Matrix antes. O bloco F do Plano Mestre inclui muitos recursos de mensagens que são, juntos, um produto à parte.
- **Opções a comparar:** (a) chat próprio mínimo (canais por time, threads, menções, anexos); (b) embutir Mattermost; (c) embutir Matrix; (d) apenas integrar com o chat que o time já usa.
- **Critérios:** esforço, licença compatível com ADR-014, permissões unificadas com `can()`, busca, retenção e LGPD, instalação self-hosted, experiência do usuário.
- **Decisão:** a ser registrada ao fim do spike. Em qualquer opção, DMs, grupos, reações, enquetes, mensagens agendadas e vídeo ficam na Fase 5.
- **Revisar quando:** o esforço estimado para o chat ultrapassar a metade da capacidade da Fase 3.

## ADR-017 — Observabilidade mínima

- **Status:** Proposta
- **Contexto:** o self-hosted precisa ser operado por times pequenos; uma pilha completa de observabilidade pesa.
- **Decisão:** logs estruturados em JSON com `request_id` e `sync_id` e sem segredos; endpoints `/health/live` e `/health/ready`; Sentry ou GlitchTip (auto-hospedado) com mascaramento; métricas de sincronização e fila expostas a partir da Fase 2. OpenTelemetry e Grafana ficam opcionais e fora do perfil mínimo.
- **Alternativas:** pilha completa desde o início; só logs de texto.
- **Consequências:** diagnóstico suficiente com poucos serviços.
- **Revisar quando:** a operação SaaS ou o número de instâncias exigir tracing distribuído.
