"""Status do Jira -> grupos do Vulpes Hub.

Fluxo do time: A fazer -> Em andamento -> Em análise (Code Review) -> Em teste -> Concluído.
A classificação usa primeiro a CATEGORIA oficial do Jira (`new` / `indeterminate` / `done`) e só
depois o NOME do status, para refinar o que é "indeterminate". Assim um status novo criado no Jira
continua sendo classificado de forma razoável sem mudar código.
"""
from __future__ import annotations

import re

from domain.text import strip_accents

PENDENTE = "Pendente"
ANDAMENTO = "Em Andamento"
ANALISE = "Em Análise"  # Code Review: testar, ver se cumpre a subtask, se o commit atende
TESTE = "Em Teste"
BLOQUEADA = "Bloqueada"
CONCLUIDA = "Concluída"

# Ordem de exibição (do mais avançado ao menos) e ordem do fluxo (para CFD/gargalos).
GRUPOS = [CONCLUIDA, TESTE, ANALISE, ANDAMENTO, PENDENTE, BLOQUEADA]
FLUXO = [PENDENTE, ANDAMENTO, ANALISE, TESTE, CONCLUIDA]
EM_PROGRESSO = (ANDAMENTO, ANALISE, TESTE)

_BLOQUEIO = re.compile(r"bloque|block|impedi|imped")
_ANALISE = re.compile(r"analis|review|revis")
_TESTE = re.compile(r"\bteste|\btest\b|\btesting\b|\bqa\b|homolog")
_CONCLUIDO = re.compile(r"conclu|\bdone\b|finaliz|fechad|\bclosed\b|resolvid")
_A_FAZER = re.compile(r"a fazer|to do|\btodo\b|backlog|aberto|\bopen\b|\bnovo\b|\bnew\b")
_ANDAMENTO = re.compile(r"andamento|progress|\bdoing\b|desenvolv")


def classify_status(name: str | None, category: str | None = None) -> str:
    """Grupo do Vulpes Hub para um status do Jira. `category` = `statusCategory.key` quando disponível."""
    n = strip_accents(name).lower().strip()
    if _BLOQUEIO.search(n):
        return BLOQUEADA
    cat = (category or "").lower()
    if cat == "done":
        return CONCLUIDA
    if cat == "new":
        return PENDENTE
    if cat == "indeterminate":
        if _ANALISE.search(n):
            return ANALISE
        if _TESTE.search(n):
            return TESTE
        return ANDAMENTO
    # Sem categoria (ex.: histórico do changelog traz só o nome): decide pelo nome.
    if _CONCLUIDO.search(n):
        return CONCLUIDA
    if _ANALISE.search(n):
        return ANALISE
    if _TESTE.search(n):
        return TESTE
    if _ANDAMENTO.search(n):
        return ANDAMENTO
    if _A_FAZER.search(n):
        return PENDENTE
    return PENDENTE
