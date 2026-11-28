# Registro da auditoria inicial

> Fonte normativa de produto e decisões: [`Documento Geral V1.2`](DOCUMENTO_GERAL.md).


Este documento resume os principais problemas identificados antes da evolução do MVP. Ele serve como histórico; o comportamento atual, as regras e as limitações estão descritos em [`MVP_STATUS.md`](MVP_STATUS.md).

| Área | Problema identificado | Correção registrada |
|---|---|---|
| GitHub | Commits entregues por squash ou rebase não eram reconhecidos pela comparação direta de SHAs. | A entrega também considera Pull Requests integradas à branch padrão. |
| GitHub | Paginação limitada podia ocultar commits e branches. | Paginação ampliada e janela de consulta configurável. |
| GitHub | Bots e commits de merge podiam ser tratados como atividade de pessoas. | Classificação separada de pessoas, bots e merges. |
| Jira | Erros de API podiam parecer listas vazias e ser armazenados em cache. | Resultado da fonte diferencia falha de consulta de ausência de dados; falhas não são cacheadas. |
| Jira | Worklogs e changelog podiam ser lidos parcialmente. | Leitura paginada pelos endpoints específicos. |
| Jira | Status e hierarquia de issues eram interpretados de forma incompleta. | Classificação por categoria e leitura da hierarquia real. |
| Datas | Horários e fusos eram descartados em parte dos fluxos. | Datas completas, com apresentação em `America/Sao_Paulo`. |
| Vínculos | Textos como `status 1.2` podiam ser confundidos com identificadores de User Story. | Reconhecimento por token isolado e padrão configurável. |
| Interface | Filtros não eram aplicados de forma uniforme e havia risco de HTML não escapado. | Contexto global de filtros e escape de conteúdo dinâmico. |
| Configuração | A gravação do `.env` podia apagar valores existentes. | Atualização seletiva, preservando o conteúdo não alterado. |

O estado atual das correções e os limites conhecidos estão em [`MVP_STATUS.md`](MVP_STATUS.md). O histórico detalhado de arquitetura está em [`adr/ADR.md`](adr/ADR.md).
