# Changelog

Mudanças relevantes do Vulpes Work. A versão `0.1.0` em `pyproject.toml` identifica a baseline do projeto; não representa uma publicação ou release.

## Não lançado

### Documentação — revisão V1.2 (27/11/2026)
- Incorporado `docs/DOCUMENTO_GERAL.md`, cópia canônica do Documento Geral V1.2 aprovado pelo usuário.
- Reescrito o plano vigente para refletir fases, escopo e decisões V1.2; plano anterior preservado em `docs/plano/arquivo/` como histórico superado.
- Alinhados README, estado do Development Analytics e índice/registro de ADRs.
- As instruções operacionais específicas usadas para executar a Fase 0 são temporárias e não são distribuídas no repositório; os critérios permanentes permanecem no Plano de Implementação.
- Licença e monetização explicitamente adiadas para antes da Fase 5 ou publicação externa que exija definição jurídica; não bloqueiam o fechamento técnico da Fase 0.
- **Esta atualização altera documentação; não representa implementação de funcionalidades da Fase 0 nem execução nova da suíte.**


### Revalidação complementar da Fase 0 — 28/11/2026
- O mantenedor reexecutou `uv sync --frozen --all-groups`, Ruff, mypy, pytest com cobertura e `pip-audit` em Python 3.12.16 e 3.13.18: 440 testes aprovados em cada versão, cobertura total de 85%, Ruff/mypy aprovados e nenhuma vulnerabilidade conhecida reportada pelo `pip-audit`.
- Docker Compose: configuração e build aprovados; container `healthy`, UID/GID `10001:10001`, endpoint `/_stcore/health` HTTP 200; container encerrado após a verificação.
- Gitleaks 8.30.1 executado com os dois comandos (`gitleaks git` e o comando `detect` definido no workflow), ambos com `--log-opts="--all"`: 5 commits com alterações examinados, aproximadamente 3,62 MB, sem achados. O clone não é shallow e possui 6 commits alcançáveis, incluindo um merge commit.
- O commit de referência `8412ce8` foi localizado. Comparação AST entre `8412ce8` e `a812380`: os 332 corpos de funções `test_*` presentes na baseline são idênticos; 40 funções de teste foram adicionadas. O código de teste da baseline contém 607 nós `assert` dentro das funções de teste (608 nós `assert` no total dos arquivos de teste). A nota histórica de “224 testes” no `MVP_STATUS.md` de `8412ce8` não coincide com o inventário do snapshot; a documentação registra a discrepância sem alegar uma contagem 224/224.
- `app.py` permanece com 189 linhas na baseline de referência; a identidade visível da aplicação foi alinhada de Vulpes Hub para Vulpes Work sem alterar regras ou fluxos.
- Naquela revisão pré-publicação, a CI remota da branch ainda não estava disponível. Essa pendência foi posteriormente resolvida conforme a captura dos três checks bem-sucedidos registrada em 28/11/2026.

### Fechamento técnico da Fase 0 — 28/11/2026
- O mantenedor publicou a branch `chore/phase-0-stabilization`; o estado Git informado é HEAD `1b90b1b` sincronizado com `origin/chore/phase-0-stabilization`, com working tree e staging limpos antes desta atualização.
- A captura do GitHub Actions fornecida pelo mantenedor mostra 3 checks bem-sucedidos: qualidade/dependências em Python 3.12, qualidade/dependências em Python 3.13 e varredura de segredos no histórico Git. A captura não exibe SHA nem URL da execução; não se atribui um identificador de run que não foi fornecido.
- Validações locais executadas pelo mantenedor: `uv sync --frozen --all-groups`, Ruff, mypy, 440 testes com 85% de cobertura e `pip-audit`, em Python 3.12.16 e 3.13.18; ambas as matrizes passaram.
- Docker Compose foi validado; container `healthy`, UID/GID `10001:10001` e endpoint `/_stcore/health` HTTP 200.
- Gitleaks 8.30.1: tanto `gitleaks git --log-opts="--all" --redact .` quanto o comando `gitleaks detect --source . --log-opts="--all" --redact --exit-code 1` terminaram sem achados, examinando 5 commits com alterações (~3,62 MB) num histórico não raso.
- A comparação da baseline `8412ce8` com `a812380` preserva estruturalmente os 332 corpos de funções `test_*`; foram adicionadas 40 funções. O rótulo histórico “224 testes” não pode ser reproduzido por falta de manifesto correspondente e não é apresentado como “224/224”.
- Esta atualização remove o Prompt Mestre temporário de `docs/prompts/`, ignora essa pasta e padrões `PROMPT_*.md` no Git e no contexto Docker, e alinha textos ativos de interface/ferramentas à identidade Vulpes Work. O slug técnico `vulpes-hub` em metadados de pacote permanece deliberadamente inalterado, conforme permitido pelo Documento Geral V1.2.
- As verificações técnicas da Fase 0 estão aprovadas conforme as evidências acima. O fechamento formal depende da aplicação e revisão deste pacote e do commit com a mensagem `chore(phase-0): stabilize baseline and align project docs`.

### Reexecução da Fase 0 — 27/11/2026
- Revalidado o workspace ZIP com metadados Git funcionais na branch existente `chore/phase-0-stabilization`; a compilação e 413 testes do subconjunto sem Streamlit passaram (85% de cobertura). Instalação, suíte completa, ferramentas locais, Docker, CI remoto, Gitleaks no histórico completo e comparação da baseline de 224 asserções permanecem bloqueados/não comprovados; evidências detalhadas em `docs/MVP_STATUS.md`. A Fase 0 continua aberta.
- `compileall` aprovado e subconjunto de 413 testes aprovado com 85% de cobertura; a suíte completa não coletou por falta de Streamlit após bloqueio de rede no `uv sync`.
- Ruff, mypy, `pip-audit`, Docker e Gitleaks locais não foram executados por indisponibilidade das ferramentas. A execução remota #14 falhou no job Gitleaks; a causa ainda não pôde ser classificada.
- Naquela execução, a referência histórica ainda não havia sido identificada; a análise posterior localizou `8412ce8` e registrou a divergência entre a anotação “224 testes” e o inventário do snapshot.

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

Os resultados acima são validações locais reportadas pelo mantenedor. A execução remota #14, em 27/11/2026, ocorreu no commit `40dddf4` e falhou no job Gitleaks; o motivo ainda precisa ser investigado. Os logs não ficaram acessíveis nesta sessão.

### Decisões futuras que não bloqueiam a Fase 0
- Decisão jurídica sobre titularidade, licença definitiva e política de contribuição (ADR-014) antes da Fase 5 ou publicação externa que exija definição.
- Adoção de um padrão de critérios de aceite no Jira e nova medição quando houver issues preenchidas nesse formato (US-03.4); depende do processo da equipe.
- Configuração dos checks obrigatórios na proteção da branch principal é hardening operacional recomendado após a primeira execução válida; não substitui nem invalida os checks aprovados.

## [0.1.0] - 2026-11-26 — baseline do MVP, não publicada

- Dashboard Streamlit integrado ao Jira e ao GitHub.
- Visões de Dashboard, Sprint, Stories, Subtasks, Commits, PRs, Relatórios, Alertas, Pessoas e Timeline.
- Indicadores de Burndown, Burnup, tempo em status, Story Points, estimativas, horas registradas e bloqueios.
- Filtros globais e regras de rastreabilidade Jira ↔ GitHub.

A página Pessoas apresenta contexto de trabalho e não implementa ranking ou comparação de produtividade individual. As regras e limitações estão em `docs/MVP_STATUS.md`.
