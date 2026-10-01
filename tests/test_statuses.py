import pytest

from domain import statuses as S


@pytest.mark.parametrize("name,category,expected", [
    ("A fazer", "new", S.PENDENTE),
    ("Em andamento", "indeterminate", S.ANDAMENTO),
    ("Em análise", "indeterminate", S.ANALISE),      # Code Review — antes virava "Pendente"
    ("Em teste", "indeterminate", S.TESTE),          # antes virava "Pendente"
    ("Concluído", "done", S.CONCLUIDA),
    ("Bloqueado", "indeterminate", S.BLOQUEADA),
    ("Aguardando deploy", "indeterminate", S.ANDAMENTO),  # status novo: categoria decide
    ("Qualquer coisa", "done", S.CONCLUIDA),
    ("Code Review", "indeterminate", S.ANALISE),
    ("Blocked", "new", S.BLOQUEADA),                 # bloqueio vence a categoria
])
def test_with_category(name, category, expected):
    assert S.classify_status(name, category) == expected


@pytest.mark.parametrize("name,expected", [   # changelog traz só o nome
    ("em análise", S.ANALISE), ("em teste", S.TESTE), ("concluído", S.CONCLUIDA), ("em andamento", S.ANDAMENTO),
    ("a fazer", S.PENDENTE), ("EM ANALISE", S.ANALISE), ("Done", S.CONCLUIDA), ("In Progress", S.ANDAMENTO),
])
def test_name_only(name, expected):
    assert S.classify_status(name) == expected


def test_none_is_pending():
    assert S.classify_status(None) == S.PENDENTE


def test_flow_order_matches_team_workflow():
    assert S.FLUXO == [S.PENDENTE, S.ANDAMENTO, S.ANALISE, S.TESTE, S.CONCLUIDA]
