# Vulpes Work

Plataforma em evolução para gestão colaborativa de entregas, Development Analytics e rastreabilidade entre Jira e GitHub. A baseline técnica deste pacote é o dashboard em Streamlit; os novos módulos da plataforma serão desenvolvidos de forma incremental, conforme as fases aprovadas.

> **Estado do pacote:** a aplicação Streamlit existente é a parte observada/implementada. FastAPI, React, PostgreSQL/RLS integrado, autenticação, central de atribuições, Knowledge Hub, canais, automações e IA são itens planejados para fases posteriores — não devem ser tratados como disponíveis nesta baseline.

## Documentação oficial

- [Documento Geral V1.2 — decisões de produto aprovadas](docs/DOCUMENTO_GERAL.md)
- [Plano de Implementação vigente](docs/plano/PLANO_IMPLEMENTACAO.md)
- [Estado e regras do Development Analytics atual](docs/MVP_STATUS.md)
- [Registro de decisões arquiteturais](docs/adr/README.md)
- [Prompt Mestre de execução da Fase 0](docs/prompts/PROMPT_MESTRE_FASE_0.md)
- [Auditoria histórica](docs/AUDITORIA.md)
- [Política de dependências](docs/DEPENDENCIAS.md)

O Documento Geral V1.2 é a fonte normativa para visão, escopo, decisões e roadmap. O plano detalha execução; ADRs registram decisões técnicas. O plano anterior à V1.2 foi arquivado como histórico e não é fonte vigente.

## Baseline atual — Development Analytics

O dashboard Streamlit reúne informações de Jira e GitHub para acompanhar sprints, issues, branches, commits e Pull Requests:

- **Dashboard:** indicadores da sprint, andamento diário, distribuição por status e atividade recente.
- **Sprint:** Stories, subtarefas, estimativas, horas registradas, Story Points, branches, PRs, burndown, burnup e tempo em status.
- **Agora:** alertas de bloqueio, atraso, inatividade e pendências de revisão.
- **Pessoas:** contexto do trabalho por colaborador, sem ranking ou pontuação de produtividade.
- **Timeline:** eventos de Jira e GitHub em ordem cronológica.
- **Commits e relatórios:** rastreabilidade entre issues, commits, branches e Pull Requests.
- **Configurações:** validação das conexões, sincronização e mapeamento de autores.

As regras, limitações e evidências da baseline estão em [`docs/MVP_STATUS.md`](docs/MVP_STATUS.md).

## Arquitetura observada

O código atual é um monólito modular Python/Streamlit:

| Diretório ou arquivo | Responsabilidade observada |
|---|---|
| `domain/` | Regras de negócio e cálculos, independentes da interface e dos SDKs externos. |
| `services/` | Integrações Jira/GitHub, HTTP, cache, sincronização e configuração de serviços. |
| `application/` | Casos de uso e coordenação dos serviços. |
| `contracts/` | Modelos Pydantic usados como contratos de entrada e saída. |
| `views/` | Telas e componentes de apresentação. Não renomear para `pages/`: isso altera o comportamento multipágina do Streamlit. |
| `app.py` | Inicialização, composição do contexto e navegação. |
| `settings.py` | Leitura e validação das configurações e variáveis de ambiente. |
| `tests/` | Testes unitários, integração simulada e inicialização da aplicação. |
| `spikes/` | Provas de conceito isoladas, fora do runtime principal. |

A arquitetura-alvo futura (FastAPI, PostgreSQL/RLS e React) está especificada no Documento Geral e não deve ser implementada durante a Fase 0.

## Requisitos

- Python 3.12 como ambiente principal; CI também valida Python 3.13.
- [uv](https://docs.astral.sh/uv/) para reproduzir o ambiente a partir de `uv.lock`.
- Acesso a um projeto Jira Cloud e aos repositórios GitHub consultados pelo dashboard.

## Instalação e configuração

Clone o repositório oficial usando o URL remoto confirmado pelo mantenedor. Pacotes ZIP exportados podem não conter metadados Git; para trabalhar com histórico, branches e remotes, use um clone Git real.

```powershell
git clone <URL_DO_REPOSITORIO_OFICIAL>
cd <DIRETORIO_DO_REPOSITORIO>
uv sync --frozen --all-groups
uv run streamlit run app.py
```

Na primeira execução, a aplicação apresenta a configuração inicial quando faltam variáveis obrigatórias. Também é possível criar o arquivo local a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

Preencha as variáveis no `.env` local. Nunca versione esse arquivo:

| Variável | Uso |
|---|---|
| `EMAIL` | E-mail da conta Atlassian. |
| `TOKEN` | Token de API do Jira. |
| `JIRA_DOMAIN` | Domínio do Jira, por exemplo `empresa.atlassian.net`. |
| `BOARD_ID` | Identificador numérico do quadro. |
| `JIRA_PROJECT` | Chave do projeto, por exemplo `SCRUM`. |
| `GITHUB_TOKEN` | Token com acesso de leitura aos repositórios consultados. |
| `GITHUB_ORG` | Opcional; substitui a organização definida em `config.json`. |

Crie tokens nos painéis oficiais do [Jira](https://id.atlassian.com/manage-profile/security/api-tokens) e do [GitHub](https://github.com/settings/personal-access-tokens). Conceda somente as permissões necessárias. Nunca inclua tokens em código, logs, patches ou ZIPs compartilhados.

O arquivo `config.json` define organização, repositórios, janela de consulta do GitHub, padrões de identificação de issues, limites dos alertas e mapeamento entre autores do GitHub e pessoas do Jira.

## Convenção Jira ↔ GitHub

A convenção existente é **Branch = User Story · Pull Request = User Story · Commit = Subtask**. Confirme as regras exatas em [`docs/MVP_STATUS.md`](docs/MVP_STATUS.md) antes de alterar o padrão.

## Desenvolvimento e testes

```bash
uv sync --frozen --all-groups
uv run ruff check .
uv run mypy domain application contracts
uv run pytest -q --cov --cov-report=term-missing
uv run pip-audit
```

O workflow em `.github/workflows/ci.yml` executa as verificações em Python 3.12 e 3.13. O job Gitleaks examina o histórico completo do Git; análise de ZIP não substitui essa verificação. A prova de conceito de Row-Level Security tem ambiente e testes próprios; veja [`spikes/rls/README.md`](spikes/rls/README.md).

## Docker

O Compose principal inicia somente o dashboard Streamlit. PostgreSQL não faz parte do runtime desta baseline.

```powershell
New-Item .env -ItemType File -Force
docker compose up --build
```

No Linux/macOS, use `touch .env` antes de `docker compose up --build`. Abra `http://localhost:8501`. A imagem deve executar como usuário não-root e possuir healthcheck; valide esses requisitos no ambiente de destino.

## Segurança, compartilhamento e estado da Fase 0

- `.env`, caches, ambientes virtuais, logs e saídas reais de validação não devem ser compartilhados nem versionados.
- Antes de gerar um ZIP, revise os arquivos incluídos; prefira `git archive --format=zip -o vulpes-work.zip HEAD` a compactar a pasta de trabalho inteira.
- Gitleaks precisa ser aprovado no histórico Git completo. A execução remota mais recente registrada em 27/11/2026 falhou nesse job; consulte `docs/MVP_STATUS.md` antes de considerar a fase encerrada.
- A Fase 0 permanece aberta: a comparação das 224 asserções originais, a investigação do achado de Gitleaks e as validações completas ainda precisam de evidência. Veja o Plano e o Documento Geral.

## Roadmap

- **Fase 0:** baseline e estabilização — fechamento em andamento.
- **Fase 1:** fundação da plataforma e piloto vertical de atribuições.
- **Fase 2:** persistência analítica, sincronização robusta e produtividade pessoal.
- **Fase 3:** Knowledge Hub e comunicação por Times.
- **Fase 4:** automações e IA assistiva com fontes e aprovação humana.
- **Fase 5:** SaaS e expansão comercial, somente após decisões jurídicas/comerciais.

## Licença e distribuição

O objetivo atual é desenvolver e implantar o Vulpes Work para uso próprio. A decisão de licença, SaaS e monetização foi deliberadamente adiada para antes do início da Fase 5 ou antes de publicação externa que exija definição jurídica. A diretriz provisória é manter todos os direitos reservados; não há concessão de licença a terceiros neste momento. A ausência de `LICENSE` não deve ser interpretada como autorização de uso, cópia, modificação ou distribuição.
