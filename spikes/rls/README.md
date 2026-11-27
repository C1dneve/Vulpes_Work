# Spike: PostgreSQL Row-Level Security

Esta prova é isolada do aplicativo principal. Ela não altera o `compose.yaml` da raiz nem as dependências principais. Use apenas a instância descartável e os dados sintéticos deste diretório.

## Executar localmente

```bash
docker compose -f spikes/rls/compose.yaml up -d
python -m pip install -r spikes/rls/requirements-spike.txt
```

Configure as URLs de conexão de teste (senhas fixas e exclusivas deste ambiente descartável):

```bash
export RLS_ADMIN_DATABASE_URL='postgresql+psycopg://rls_admin:spike_admin_password@localhost:55432/rls_demo'
export RLS_APP_DATABASE_URL='postgresql+psycopg://rls_app:rls_spike_only_password@localhost:55432/rls_demo'
pytest -m spike spikes/rls/tests -q
```

No PowerShell, use `$env:RLS_ADMIN_DATABASE_URL=...` e `$env:RLS_APP_DATABASE_URL=...`.

## Conclusões esperadas

- A política aplica `USING` e `WITH CHECK` com `current_setting('app.tenant_id', true)`.
- O tenant é definido com `set_config(..., true)`, portanto vale apenas na transação atual.
- O papel `rls_app` não é dono da tabela, não é superusuário e não possui `BYPASSRLS`.
- `FORCE ROW LEVEL SECURITY` também sujeita o dono da tabela à política, mas não protege contra superusuários nem papéis com `BYPASSRLS`.
- Sem tenant definido, a expressão de política resulta em ausência de linhas para leitura e negação para escrita.
- O teste com pool de uma conexão verifica que o tenant não vaza para a transação seguinte.

## Riscos e limites

- A aplicação precisa definir o tenant em toda transação e impedir SQL fora do contexto transacional.
- Conexões administrativas, superusuários e papéis `BYPASSRLS` podem contornar a política; não devem ser usadas pela aplicação.
- A demonstração não prova que toda tabela futura estará protegida; cada entidade de negócio deverá ter política e testes negativos.
- A senha do Compose é pública e deliberadamente fraca: não reutilize em qualquer ambiente real.

## Recomendação para EP-10

Adotar papel de aplicação sem propriedade das tabelas e sem `BYPASSRLS`, aplicar `ENABLE` + `FORCE ROW LEVEL SECURITY`, definir tenant por transação e adicionar testes de isolamento para cada tabela. A integração FastAPI que injeta o tenant por requisição fica para a Fase 1, conforme o plano.
