# Changelog

Mudanças relevantes do Vulpes Hub. A versão `0.1.0` em `pyproject.toml` identifica a baseline do projeto; não representa uma publicação ou release.

## Não lançado

### Adicionado
- Workflow de CI para Python 3.12 e 3.13 com Ruff, mypy, pytest com cobertura, `pip-audit` e Gitleaks.
- Container Docker com healthcheck e execução como usuário não-root.
- Camadas `application/` e `contracts/` para separar casos de uso e modelos da interface.
- Spike isolado de Row-Level Security, com PostgreSQL, SQLAlchemy e testes próprios.
- Ferramenta de diagnóstico, somente leitura, para verificar a estrutura dos critérios de aceite em issues do Jira.

### Alterado
- Interface organizada em módulos sob `views/`, mantendo `app.py` como ponto de composição e navegação.
- Configuração validada e mensagens de erro mais claras.
- Logs estruturados com redação de dados sensíveis e proteção contra sincronizações duplicadas.
- Documentação reorganizada para refletir a arquitetura atual, os resultados reais e as pendências da Fase 0.
- Removidos arquivos de instruções internas do processo de edição e imagens sem referência no código da aplicação.
- ADRs 001 a 013 aprovadas formalmente pelo mantenedor em 27/11/2026. A ADR-014 não faz parte dessa aprovação.
- Login OIDC transferido da Fase 0 para a Fase 1.

### Segurança e decisões pendentes
- `.env`, caches, ambientes virtuais, logs e saídas reais de validação são excluídos do Git e da imagem Docker.
- A decisão provisória de manter todos os direitos reservados permanece válida até parecer jurídico. A ADR-014 continua pendente e não foi criado arquivo `LICENSE`.

### Validação local registrada em 26/11/2026

| Verificação | Resultado informado pelo mantenedor |
|---|---|
| `uv sync --frozen` | Concluído; 75 pacotes verificados. |
| `uv run ruff check .` | Aprovado. |
| `uv run mypy domain application contracts` | Aprovado; 20 arquivos sem problemas. |
| `uv run pytest -q --cov --cov-report=term-missing` | 440 testes aprovados em 23,47 s; cobertura total de 85%. |
| `uv run pip-audit` | Nenhuma vulnerabilidade conhecida encontrada. |
| Gitleaks local | Nenhum vazamento encontrado nos 2 commits examinados. |
| Docker Compose | Build e inicialização concluídos; container saudável, app acessível e processo com `uid=10001`. |
| Configuração | `load_settings()` retornou `ready=True`, sem variáveis obrigatórias ausentes. |
| Spike RLS (27/11/2026) | 6 testes aprovados; ambiente descartável removido após a execução. |
| Probe Jira (27/11/2026) | 20 issues lidas, 20 sem seção formal de critérios de aceite e nenhuma falha de API. Resultado inconclusivo para medir a precisão do parser. |

Os resultados acima são validações locais reportadas pelo mantenedor. O workflow do GitHub Actions ainda precisa ser executado após o commit e o push.

### Pendente antes de encerrar a Fase 0
- Primeiro resultado verde do GitHub Actions, incluindo Python 3.12 e 3.13 e a varredura do histórico completo.
- Comparação com a baseline original para comprovar que as 224 asserções existentes foram preservadas. A suíte atual passou com 440 testes, mas isso, isoladamente, não comprova a comparação histórica.
- Decisão jurídica sobre titularidade, licença definitiva e política de contribuição (US-03.2 / ADR-014).
- Adoção de um padrão de critérios de aceite no Jira e nova medição quando houver issues preenchidas nesse formato (US-03.4).
- Configuração dos checks obrigatórios na proteção da branch `main`, depois da primeira execução válida.

## [0.1.0] - 2026-11-26 — baseline do MVP, não publicada

- Dashboard Streamlit integrado ao Jira e ao GitHub.
- Visões de Dashboard, Sprint, Stories, Subtasks, Commits, PRs, Relatórios, Alertas, Pessoas e Timeline.
- Indicadores de Burndown, Burnup, tempo em status, Story Points, estimativas, horas registradas e bloqueios.
- Filtros globais e regras de rastreabilidade Jira ↔ GitHub.

A página Pessoas apresenta contexto de trabalho e não implementa ranking ou comparação de produtividade individual. As regras e limitações estão em `docs/MVP_STATUS.md`.
