# Política de dependências

> Fonte normativa de produto e decisões: [`Documento Geral V1.2`](DOCUMENTO_GERAL.md).


- Revisar dependências diretas e transitivas mensalmente por meio do Dependabot.
- Executar a suíte de testes, Ruff, mypy e `pip-audit` antes de mesclar atualizações.
- Atualizações que corrigem vulnerabilidades de segurança têm prioridade sobre melhorias não relacionadas.
- Não atualizar versões fora de uma User Story que autorize essa mudança; registrar incompatibilidades e riscos no PR.
- `uv.lock` é o artefato de reprodução do ambiente. Alterações em `pyproject.toml` exigem regenerar e validar o lockfile localmente.
- `requirements.txt` e `requirements-dev.txt` permanecem como caminho de compatibilidade para ambientes que ainda usam pip; as dependências diretas também estão declaradas no `pyproject.toml`.

## Histórico de atualização — 26/11/2026

Com autorização do mantenedor, as dependências diretas Pillow e Requests foram atualizadas de `12.1.1` para `13.0.0` e de `2.32.5` para `2.33.0`, respectivamente, em `pyproject.toml` e `requirements.txt`. Para compatibilidade com essas versões, o Streamlit foi atualizado de `1.55.0` para `1.67.0`. Os metadados de Streamlit 1.67.0 aceitam Pillow `>=9.2.0,<14` e Requests `>=2.27,<3`.

Na preparação inicial dessas atualizações, o lockfile ainda continha o grafo anterior e aguardava regeneração local. Essa pendência foi encerrada: em 26/11/2026, o mantenedor confirmou `uv sync --frozen`, com 75 pacotes verificados. Portanto, a orientação antiga de não usar `--frozen` antes de regenerar o lockfile não se aplica ao estado atual do ZIP.

## Comandos de desenvolvimento

```bash
uv sync --frozen --all-groups
uv run ruff check .
uv run mypy domain application contracts
uv run pytest -q
uv run pip-audit
```

O CI executa qualidade, tipos, testes, cobertura e auditoria de dependências em Python 3.12 e 3.13. O job Gitleaks examina o histórico completo do Git; a análise de um ZIP, isoladamente, não substitui essa varredura.
