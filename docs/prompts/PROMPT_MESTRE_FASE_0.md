# PROMPT MESTRE — Fechamento e implementação da Fase 0 do Vulpes Work

> **Versão:** 1.0
> **Data-base:** 27/11/2026
> **Uso:** entregar a um agente de programação com acesso ao clone Git real do Vulpes Work.
> **Não usar apenas sobre um ZIP sem `.git` para tentar criar o commit.**

---

## 1. Papel e missão

Atue como engenheiro de software sênior, responsável por estabilização, higiene de repositório, qualidade, documentação e segurança operacional do Vulpes Work.

Sua missão é **inspecionar o repositório real, concluir somente o trabalho ainda pendente da Fase 0, validar a baseline sem alterar o comportamento do dashboard e criar um commit local rastreável**. Não avance para funcionalidades da Fase 1 ou posteriores.

O usuário aprovou o Documento Geral V1.2 em 27/11/2026. Essa versão está em `docs/DOCUMENTO_GERAL.md` e é a fonte normativa do produto.

## 2. Fontes e precedência obrigatórias

Leia integralmente, nesta ordem operacional:

1. `docs/DOCUMENTO_GERAL.md` — visão, decisões aprovadas, roadmap e regras para trabalho baseado em ZIP.
2. `docs/plano/PLANO_IMPLEMENTACAO.md` — escopo, tarefas e critérios de saída da Fase 0.
3. `docs/adr/README.md` e `docs/adr/ADR.md` — decisões técnicas e status.
4. `README.md`, `CHANGELOG.md`, `docs/MVP_STATUS.md`, `docs/AUDITORIA.md`, `docs/DEPENDENCIAS.md`.
5. Código, testes, workflow, configuração, Docker e histórico Git — evidências do que está realmente implementado.

Precedência: decisão explícita mais recente do usuário → Documento Geral V1.2 → ADR aceita sem conflito → Plano vigente/especificação → código/testes/ZIP como evidência. Registre conflitos; não os resolva silenciosamente.

Se o repositório ainda não contiver estes documentos, use o pacote documental V1.2 aprovado fornecido pelo mantenedor. Não recupere instruções de planos arquivados como se fossem atuais.

## 3. Preparação obrigatória: não inventar Git

1. Confirme que está em um clone real e que `git rev-parse --is-inside-work-tree` funciona. **Não execute `git init` sobre o ZIP e não crie histórico artificial.**
2. Registre `git remote -v`, branch atual, `git status --short --branch`, HEAD e árvore de trabalho. Não publique credenciais do remote.
3. Confirme com a configuração real do projeto qual branch é a principal. Não assuma `main` se a configuração indicar outro nome.
4. Preserve alterações locais preexistentes: não sobrescreva, descarte, limpe ou faça reset de trabalho do usuário. Se houver alterações não relacionadas, pare antes de misturá-las e apresente o inventário.
5. Atualize refs remotas sem reescrever histórico. Crie uma branch de trabalho a partir da branch principal atualizada, por exemplo `chore/phase-0-stabilization`. Se já existir, escolha um sufixo claro sem apagar a existente.
6. Identifique o commit de referência que continha os 224 testes/assertions originais. Se a história ou o commit não estiver disponível, marque a comparação como bloqueada por evidência ausente; não afirme equivalência.
7. Não faça push. O pedido é criar o commit local; qualquer push precisa de autorização separada.

## 4. Escopo permitido — Fase 0

### EP-01 — Higiene, identidade e documentação

- Alinhe o README à identidade oficial **Vulpes Work**. O slug antigo de repositório/pacote pode permanecer até uma migração segura, mas não use “Vulpes Hub” como identidade nova.
- Use `docs/DOCUMENTO_GERAL.md` como cópia canônica aprovada da V1.2.
- Garanta que plano, MVP status, changelog, auditoria, dependências e índice ADR não contradigam o Documento Geral.
- Não invente URL para remote: use o remote confirmado. Se não puder confirmá-lo, deixe placeholder identificado e registre a pendência.
- Separe evidências executadas pelo agente de resultados históricos reportados pelo mantenedor.
- Inspecione `.coverage`, `Vulpes_Hub-revisao.patch`, `tools/validation_output/results.json` e `tools/validation_output/console.log`. Classifique cada artefato como fonte necessária, evidência sanitizada, temporário ou dado sensível. Não apague um patch antes de verificar se contém alterações únicas ainda não incorporadas. Remova do commit/pacote finais caches, logs e resultados reais que não devam ser compartilhados; mantenha exemplos sanitizados e atualize `.gitignore`/`.dockerignore` quando necessário.
- Verifique `.env`, `.env.*`, tokens, cabeçalhos, URLs privadas, payloads reais e outros dados sensíveis em arquivos e histórico. Não exiba segredos no relatório.

### EP-02 — Qualidade, modularização e runtime

- Preserve o dashboard Streamlit, suas regras de negócio e suas jornadas existentes.
- Mantenha as fronteiras: `domain/` sem dependência de UI/SDK; integrações em `services/`; casos de uso em `application/`; contratos em `contracts/`; UI em `views/`.
- Não renomeie `views/` para `pages/`.
- Confirme que `app.py` é composição/configuração/navegação, sem nova concentração de regra de negócio. A baseline anterior registrou 189 linhas e o plano aceita até 200 com justificativa; não faça refatoração cosmética apenas para reduzir linhas.
- Reproduza o ambiente com `uv.lock` e `uv sync --frozen --all-groups`. Não atualize dependências por conveniência. Qualquer atualização necessária deve ter justificativa, compatibilidade e lock regenerado/testado.
- Valide o runtime Docker: Compose principal somente com o dashboard; healthcheck; usuário não-root; sem PostgreSQL integrado ao runtime atual.
- Revise logs para garantir que tokens e cabeçalhos de autorização nunca apareçam. Preserve idempotência e proteção contra execuções duplicadas.

### EP-03 — Decisões e provas técnicas

- Preserve como aceitas as ADRs 001–013. Não modifique uma decisão aceita sem registrar ADR substituta e apontar o impacto.
- ADR-014 (licença/distribuição) permanece pendente por decisão do usuário: **não é bloqueio da Fase 0**. A decisão final ocorre antes da Fase 5 ou publicação externa que exija definição jurídica. A diretriz provisória de direitos reservados continua; não criar `LICENSE` por inferência.
- RLS permanece spike isolado em `spikes/rls/`; não adicionar PostgreSQL ao Compose principal nem integrar RLS ao dashboard nessa fase. Verifique os resultados sem alegar que a aplicação principal já possui isolamento multi-tenant.
- O probe de critérios Jira feito em 20 issues foi inconclusivo porque nenhuma tinha a seção formal. Registre isso corretamente; não invente uma taxa de precisão. Repetir apenas quando o template estiver sendo usado em issues reais e houver autorização de acesso.
- OIDC/Google saiu da Fase 0 e pertence à Fase 1. Não implementar `st.login` agora.

## 5. Itens explicitamente proibidos nesta execução

Não implementar, antecipar ou adicionar dependências para:

- FastAPI, React/TypeScript/Vite ou migração de telas do Streamlit;
- PostgreSQL no runtime principal, entidades multi-tenant do produto ou RLS por request;
- autenticação Google/OIDC, RBAC/ACL de produto, Organização/Comunidade/Projeto/Time;
- atribuições, critérios/evidências/review inbox, notificações transacionais;
- Knowledge Hub, canais/chat, busca global de produto;
- Command Palette, Meu Trabalho ou outros módulos novos da Fase 1/2 (documentação dos requisitos pode estar presente; implementação não);
- automações, IA, SaaS, billing, novo modelo de licença ou monetização.

Não alterar a lógica Jira/GitHub do dashboard sem defeito reproduzível que impeça a baseline. Não mudar API externa, formato de configuração ou resultado de regra sem teste de regressão e justificativa explícita.

## 6. Procedimento de execução

### Passo A — Inventário e diff da baseline

- Inventarie os arquivos e verifique os documentos vigentes.
- Compare a árvore recebida com a branch principal do repositório real.
- Examine o patch legado e valide se há mudanças únicas, aplicadas, obsoletas ou conflitantes.
- Registre estado de dependências, workflows e Docker antes de modificar.

### Passo B — Lista de pendências verificáveis

Monte checklist por EP/US com quatro estados: concluído com evidência, pendente, bloqueado por evidência/acesso, não aplicável. Não confunda “já existe no código” com “foi revalidado”.

Priorize apenas pendências que impedem os critérios de saída. Faça mudanças pequenas e reversíveis. Se um item já atende, não o reimplemente.

### Passo C — Alterações

- Faça as alterações mínimas necessárias nos arquivos de documentação, ignore rules, configuração, testes, Docker ou código de suporte da Fase 0.
- Atualize documentação após cada mudança real: comando, data, resultado, ambiente e proveniência.
- Se uma exigência estiver fora de Fase 0, registre-a na fase correta; não a implemente.
- Se encontrar conflito entre requisito aprovado e uma decisão técnica, pare a alteração relacionada e apresente a pergunta objetiva ao usuário.

### Passo D — Validação local

Execute os comandos aplicáveis e registre saída/resumo sem segredos:

```bash
uv sync --frozen --all-groups
uv run ruff check .
uv run mypy domain application contracts
uv run pytest -q --cov --cov-report=term-missing
uv run pip-audit
docker compose config
docker compose up --build
```

Verifique adicionalmente que o container está saudável e executa como usuário não-root. Se não houver Docker disponível, declare como não executado, não como aprovado. Execute o fluxo de inicialização do Streamlit quando possível.

- Teste em Python 3.12 localmente e verifique Python 3.13 no CI, ou execute ambos localmente se o ambiente suportar.
- Compare as 224 asserções antigas com a referência Git identificada. Verifique os próprios casos/asserções, não apenas a contagem total de testes. Se não encontrar a baseline, registre exatamente quais evidências faltam e mantenha a equivalência como não comprovada.
- Não chame Jira/GitHub real nem use credenciais do usuário nesta etapa sem autorização explícita. Testes devem usar fakes/mocks; a prova real de APIs já registrada pode ser citada como evidência histórica.

### Passo E — CI e segurança do histórico

- Confirme no GitHub Actions os jobs e a matriz Python 3.12/3.13.
- Execute Gitleaks em clone com histórico completo, usando a configuração do workflow, e corrija achados antes do commit. Não imprima valores detectados.
- Um ZIP, diff isolado ou varredura apenas do working tree não prova ausência de segredos no histórico.
- Não desabilite checks, não crie allowlist ampla e não esconda achado legítimo para obter build verde.

### Passo F — Revisão e commit

Antes de commitar:

1. Revise `git diff --check` e `git diff` integralmente.
2. Confirme que só há arquivos relacionados à Fase 0; nenhum segredo, `.env`, log, `.coverage`, output real ou artefato não aprovado será commitado.
3. Confira changelog, Plano, MVP status, Documento Geral e ADRs por coerência.
4. Confirme que todos os testes aplicáveis foram realmente executados e que falhas/limitações estão registradas.
5. Se os critérios obrigatórios foram atendidos, crie **um commit local** com mensagem:

```text
chore(phase-0): stabilize baseline and align project docs
```

6. Caso algum critério obrigatório siga bloqueado (por exemplo, CI remoto, Gitleaks no histórico completo ou baseline original de 224 assertions), não declare Fase 0 concluída. Você pode criar um commit de progresso documental/técnico apenas se ele for seguro e autocontido, deixando explícito que é um commit parcial e que a Fase 0 continua aberta. Não use a mensagem de conclusão acima para um trabalho parcial.
7. Não faça push e não abra PR sem autorização.

## 7. Relatório obrigatório ao final

Entregue um relatório com:

1. branch e commit base; remote apenas mascarado/identificado sem credenciais;
2. branch criada e hash/mensagem do commit, se criado;
3. arquivos modificados e motivo;
4. decisões/ADRs não alteradas e itens deliberadamente adiados;
5. validações executadas, comandos, ambiente e resultados;
6. resultados herdados do mantenedor identificados como reportados, não reexecutados;
7. itens pendentes/bloqueados e a evidência necessária para fechar cada um;
8. confirmação explícita se a Fase 0 foi concluída ou permanece aberta;
9. confirmação de que não houve push.

## 8. Regra final

**Não sacrifique a veracidade para produzir um commit ou marcar a fase como concluída.** Se o ZIP, histórico, ambiente ou acesso não fornecer a evidência necessária, registre o limite e conclua apenas o trabalho que puder ser validado com segurança.
