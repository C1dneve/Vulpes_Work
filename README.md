# Vulpes Hub

Dashboard em Streamlit que reúne informações do Jira e do GitHub para acompanhar sprints, issues, branches, commits e Pull Requests.

## Funcionalidades

- **Dashboard:** indicadores da sprint, andamento diário, distribuição por status e atividade recente.
- **Sprint:** Stories, subtarefas, estimativas, horas registradas, Story Points, branches, PRs, burndown, burnup e tempo em status.
- **Agora:** alertas de bloqueio, atraso, inatividade e pendências de revisão.
- **Pessoas:** visão do trabalho por colaborador, sem ranking ou pontuação de produtividade.
- **Timeline:** eventos de Jira e GitHub em ordem cronológica.
- **Commits e relatórios:** rastreabilidade entre issues, commits, branches e Pull Requests.
- **Configurações:** validação das conexões, sincronização e mapeamento de autores.

As regras de negócio, os limites conhecidos e o estado funcional estão em [`docs/MVP_STATUS.md`](docs/MVP_STATUS.md).

## Arquitetura

O projeto é um monólito modular. As responsabilidades ficam separadas por camada:

| Diretório ou arquivo | Responsabilidade |
|---|---|
| `domain/` | Regras de negócio independentes de Streamlit, Jira, GitHub e banco de dados. |
| `services/` | Integrações com Jira e GitHub, HTTP, cache, sincronização e configuração de serviços. |
| `application/` | Casos de uso e coordenação dos serviços, sem dependência da interface. |
| `contracts/` | Modelos Pydantic usados como contratos de entrada e saída. |
| `views/` | Telas e componentes de apresentação organizados por área funcional. |
| `app.py` | Inicialização, composição do contexto e navegação entre telas. |
| `settings.py` | Leitura e validação das configurações e variáveis de ambiente. |
| `tests/` | Testes unitários, de integração simulada e de inicialização da aplicação. |
| `spikes/` | Provas de conceito isoladas, fora da aplicação principal. |

As regras de negócio ficam em `domain/`; chamadas externas ficam em `services/`; a interface não deve concentrar regras de negócio. O diretório `views/` não deve ser renomeado para `pages/`, pois isso altera o comportamento de navegação multipágina do Streamlit.

## Requisitos

- Python 3.12 ou superior.
- [uv](https://docs.astral.sh/uv/) para instalar o ambiente a partir do lockfile.
- Acesso a um projeto Jira Cloud e aos repositórios GitHub que serão consultados.

## Instalação e configuração

```powershell
git clone https://github.com/C1dneve/Vulpes_Hub.git
cd Vulpes_Hub
uv sync --frozen
uv run streamlit run app.py
```

Na primeira execução, a aplicação apresenta a configuração inicial quando faltam variáveis obrigatórias. Também é possível criar o arquivo local a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

Preencha as variáveis abaixo no `.env`:

| Variável | Uso |
|---|---|
| `EMAIL` | E-mail da conta Atlassian. |
| `TOKEN` | Token de API do Jira. |
| `JIRA_DOMAIN` | Domínio do Jira, por exemplo `empresa.atlassian.net`. |
| `BOARD_ID` | Identificador numérico do quadro. |
| `JIRA_PROJECT` | Chave do projeto, por exemplo `SCRUM`. |
| `GITHUB_TOKEN` | Token com acesso de leitura aos repositórios consultados. |
| `GITHUB_ORG` | Opcional; substitui a organização definida em `config.json`. |

Crie tokens nos painéis oficiais do [Jira](https://id.atlassian.com/manage-profile/security/api-tokens) e do [GitHub](https://github.com/settings/personal-access-tokens). Conceda somente as permissões de leitura necessárias. Os tokens devem permanecer no `.env` local e nunca devem ser incluídos no repositório.

O arquivo `config.json` define a organização, os repositórios, a janela de consulta do GitHub, os padrões de identificação de issues, os limites dos alertas e o mapeamento entre autores do GitHub e pessoas do Jira. Ajuste esses valores ao ambiente da equipe antes de usar o dashboard.

## Convenção Jira ↔ GitHub

O padrão de rastreabilidade é **Branch = User Story · Pull Request = User Story · Commit = Subtask**.

| Elemento | Padrão | Exemplo |
|---|---|---|
| Branch | `feature/{backend ou frontend}/{CHAVE}-{USx.y}-{slug}` | `feature/backend/JH-123-US2.1-cadastro` |
| Commit | `tipo(CHAVE-DA-SUBTASK): descrição` | `feat(JH-101): validar cadastro` |
| Pull Request | `[CHAVE-DA-STORY] USx.y — Título` | `[JH-123] US2.1 — Cadastro` |

A chave Jira é a referência principal quando aparece no nome ou na mensagem. As regras completas de vínculo e entrega estão descritas em `docs/MVP_STATUS.md`.

## Desenvolvimento e testes

Instale também as dependências de desenvolvimento:

```bash
uv sync --frozen --all-groups
uv run ruff check .
uv run mypy domain application contracts
uv run pytest -q --cov --cov-report=term-missing
uv run pip-audit
```

O workflow em `.github/workflows/ci.yml` executa essas verificações em Python 3.12 e 3.13 e faz uma varredura de segredos no histórico Git completo. A prova de conceito de Row-Level Security tem ambiente e testes próprios; veja [`spikes/rls/README.md`](spikes/rls/README.md).

## Docker

O Compose principal inicia somente o dashboard. O PostgreSQL não faz parte do runtime nesta fase.

No Windows PowerShell, crie um `.env` vazio antes de iniciar o container caso ainda não exista:

```powershell
New-Item .env -ItemType File -Force
docker compose up --build
```

No Linux/macOS, use `touch .env` antes do `docker compose up --build`. Abra `http://localhost:8501`. A imagem executa a aplicação com usuário não-root e possui healthcheck.

## Compartilhamento e segurança

O `.gitignore` exclui `.env`, ambientes virtuais, caches, logs e saídas reais de validação. Mesmo assim, revise qualquer arquivo compactado antes de compartilhar. Para gerar um ZIP somente com os arquivos versionados no commit atual:

```bash
git archive --format=zip -o vulpes-hub.zip HEAD
```

Depois de um push, o Gitleaks no GitHub Actions examina o histórico completo. A execução local anterior encontrou 2 commits e não encontrou vazamentos; isso não substitui a varredura do histórico completo no GitHub. Se um token real tiver sido exposto, revogue-o no provedor e gere outro.

## Próximas entregas

Autenticação OIDC, persistência em PostgreSQL, perfis de acesso, notificações, histórico persistente, busca global e relatórios adicionais estão planejados para fases futuras. O dashboard atual e suas limitações estão descritos em [`docs/MVP_STATUS.md`](docs/MVP_STATUS.md); o planejamento e as decisões técnicas ficam em `docs/plano/PLANO_IMPLEMENTACAO.md` e `docs/adr/ADR.md`.

## Licenciamento

A situação atual é provisória: todos os direitos reservados, sem concessão de licença de uso a terceiros, até decisão jurídica definitiva. A ADR-014 permanece pendente e não há arquivo `LICENSE`. A ausência de licença não deve ser interpretada como autorização para uso, cópia, modificação ou distribuição.
