# Decisões arquiteturais (ADRs)

Este índice acompanha [`ADR.md`](ADR.md), que contém o registro completo. As ADRs 001 a 013 foram aprovadas pelo mantenedor em 27/11/2026. A ADR-014 continua pendente de parecer jurídico; as ADRs 015 a 017 não foram aprovadas. Uma decisão aceita só deve ser alterada por meio de uma nova ADR que a substitua.

## Índice

| ADR | Decisão | Status | Fase |
|---|---|---|---|
| [ADR-001](ADR.md#adr-001--monólito-modular-com-fronteiras-verificadas) | Monólito modular com fronteiras verificadas | Aceita | 0 |
| [ADR-002](ADR.md#adr-002--backend-em-python-312--fastapi-preservando-domain) | Backend Python 3.12 + FastAPI, preservando `domain/` | Aceita | 0 |
| [ADR-003](ADR.md#adr-003--postgresql-único-fila-no-próprio-postgres-redis-adiado) | PostgreSQL único; fila no próprio Postgres; Redis adiado | Aceita | 0–1 |
| [ADR-004](ADR.md#adr-004--multi-tenancy-com-tenant_id--row-level-security) | Multi-tenancy com `tenant_id` + Row-Level Security | Aceita | 1 |
| [ADR-005](ADR.md#adr-005--autorização-rbac--acl-por-recurso-função-central) | RBAC + ACL por recurso, função central | Aceita | 1–2 |
| [ADR-006](ADR.md#adr-006--frontend-react--typescript--vite-streamlit-como-development-analytics) | React + TypeScript + Vite; Streamlit como Development Analytics | Aceita | 1 |
| [ADR-007](ADR.md#adr-007--sincronização-jiragithub-polling--webhooks-propriedade-de-campos-outbox) | Sincronização Jira/GitHub, propriedade de campos e outbox | Aceita | 1–2 |
| [ADR-008](ADR.md#adr-008--credenciais-de-integração-por-organização-criptografadas) | Credenciais por organização, criptografadas | Aceita | 1 |
| [ADR-009](ADR.md#adr-009--tempo-real-sse-primeiro-websocket-com-o-chat) | SSE primeiro; WebSocket com o chat | Aceita | 1, 3 |
| [ADR-010](ADR.md#adr-010--armazenamento-de-arquivos-atrás-de-uma-interface) | Armazenamento de arquivos atrás de uma interface | Aceita | 1, 3 |
| [ADR-011](ADR.md#adr-011--critérios-de-aceite-template-markdown-e-versionamento) | Critérios de aceite em Markdown e versionamento | Aceita | 1 |
| [ADR-012](ADR.md#adr-012--estados-da-atribuição-e-mapeamento-para-status-do-jira) | Estados da atribuição e mapeamento para Jira | Aceita | 1 |
| [ADR-013](ADR.md#adr-013--ia-gateway-híbrido-desligado-por-padrão-registro-determinístico) | IA: gateway híbrido e registro determinístico | Aceita | 4 |
| [ADR-014](ADR.md#adr-014--licença-source-available) | Licença source-available | Pendente (parecer jurídico; direitos reservados provisoriamente) | 0 |
| [ADR-015](ADR.md#adr-015--privacidade-retenção-exportação-e-exclusão) | Privacidade, retenção, exportação e exclusão | Proposta | 1 |
| [ADR-016](ADR.md#adr-016--chat-construir-ou-integrar) | Chat: construir ou integrar | Pendente (spike EP-40) | 3 |
| [ADR-017](ADR.md#adr-017--observabilidade-mínima) | Observabilidade mínima | Proposta | 1 |

## Significado dos status

- **Proposta:** decisão registrada, ainda sem aprovação.
- **Pendente:** depende de spike, parecer jurídico ou informação externa antes de ser decidida.
- **Aceita:** decisão aprovada; só muda por meio de uma nova ADR que a substitua.

## Template para novas ADRs

```markdown
## ADR-NNN — Título da decisão

- **Status:** Proposta | Pendente | Aceita
- **Contexto:** problema, restrições e evidências que motivam a decisão.
- **Decisão:** escolha adotada e limites de aplicação.
- **Alternativas:** opções consideradas e motivos para aceitar/rejeitar cada uma.
- **Consequências:** impactos positivos, custos, riscos e migrações necessárias.
- **Gatilho de revisão:** condição objetiva que obriga a reavaliar a decisão.
```
