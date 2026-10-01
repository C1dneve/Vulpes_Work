"""MVP / Fase 6 — tempo em status: múltiplos status, status atual, histórico vazio, fuso."""
import pandas as pd
import pytest

from domain import statuses as S
from domain.time_in_status import by_group, current_status_hours, per_status, time_in_status

TZ = "America/Sao_Paulo"
NOW = pd.Timestamp("2026-09-30 12:00", tz=TZ)


def ts(s):
    return pd.Timestamp(s, tz=TZ)


def item(key="JH-101", status="Em teste", group=S.TESTE, created="2026-09-28 08:00"):
    return {"subtask_key": key, "status_name": status, "status_group": group, "created": ts(created) if created else pd.NaT}


def ev(key, when, frm, to, fg, tg):
    return {"subtask_key": key, "ts": ts(when), "from_name": frm, "to_name": to, "from_group": fg, "to_group": tg}


def cl(*events):
    return pd.DataFrame(list(events), columns=["subtask_key", "ts", "from_name", "to_name", "from_group", "to_group"])


EMPTY = cl()


def seg_hours(res, key="JH-101"):
    return res.segments[res.segments["subtask_key"] == key].set_index("status")["hours"].to_dict()


def test_multiple_statuses_sum_to_elapsed_time_from_creation_to_now():
    items = pd.DataFrame([item()])
    c = cl(ev("JH-101", "2026-09-28 12:00", "A fazer", "Em andamento", S.PENDENTE, S.ANDAMENTO),
           ev("JH-101", "2026-09-29 18:00", "Em andamento", "Em análise", S.ANDAMENTO, S.ANALISE),
           ev("JH-101", "2026-09-30 04:00", "Em análise", "Em teste", S.ANALISE, S.TESTE))
    r = time_in_status(items, c, NOW)
    assert seg_hours(r) == {"A fazer": 4.0, "Em andamento": 30.0, "Em análise": 10.0, "Em teste": 8.0}
    assert r.segments["hours"].sum() == (NOW - ts("2026-09-28 08:00")).total_seconds() / 3600       # sem buracos nem sobreposição
    assert r.unknown == []


def test_current_status_runs_until_now():
    r = time_in_status(pd.DataFrame([item()]), cl(ev("JH-101", "2026-09-30 04:00", "Em análise", "Em teste", S.ANALISE, S.TESTE)), NOW)
    cur = r.segments[r.segments["current"]].iloc[0]
    assert cur["status"] == "Em teste" and cur["end"] == NOW and cur["hours"] == 8.0
    assert current_status_hours(r.segments) == {"JH-101": 8.0}


def test_empty_history_means_current_status_since_creation():
    r = time_in_status(pd.DataFrame([item(status="A fazer", group=S.PENDENTE)]), EMPTY, NOW)
    s = r.segments.iloc[0]
    assert s["status"] == "A fazer" and s["current"] and s["basis"] == "sem_transicoes" and s["hours"] == 52.0


def test_history_that_failed_to_load_is_unknown_not_a_wrong_number():
    r = time_in_status(pd.DataFrame([item()]), EMPTY, NOW, history_unknown={"JH-101"})
    assert r.segments.empty and r.unknown == ["JH-101"]


def test_no_history_and_no_creation_date_is_unknown():
    r = time_in_status(pd.DataFrame([item(created=None)]), EMPTY, NOW)
    assert r.segments.empty and r.unknown == ["JH-101"]


def test_back_and_forth_sums_visits_and_keeps_original_status_names():
    items = pd.DataFrame([item(status="Em andamento", group=S.ANDAMENTO)])
    c = cl(ev("JH-101", "2026-09-28 10:00", "A fazer", "Em andamento", S.PENDENTE, S.ANDAMENTO),
           ev("JH-101", "2026-09-28 14:00", "Em andamento", "Em análise", S.ANDAMENTO, S.ANALISE),
           ev("JH-101", "2026-09-29 14:00", "Em análise", "Em andamento", S.ANALISE, S.ANDAMENTO))
    p = per_status(time_in_status(items, c, NOW).segments).set_index("status")
    assert p.loc["Em andamento", "visits"] == 2 and p.loc["Em andamento", "hours"] == 4 + 22
    assert p.loc["Em análise", "hours"] == 24 and list(p.index)[0] == "A fazer"        # ordem do fluxo, nomes com a caixa original
    assert bool(p.loc["Em andamento", "current"]) and not bool(p.loc["Em análise", "current"])


def test_creation_after_first_transition_does_not_create_negative_time():
    items = pd.DataFrame([item(created="2026-09-29 12:00")])                          # issue movida de outro projeto
    c = cl(ev("JH-101", "2026-09-28 12:00", "A fazer", "Em andamento", S.PENDENTE, S.ANDAMENTO))
    r = time_in_status(items, c, NOW)
    assert (r.segments["hours"] >= 0).all() and r.segments.iloc[0]["start"] == ts("2026-09-28 12:00")


def test_current_jira_status_wins_over_an_incomplete_history():
    items = pd.DataFrame([item(status="Concluído", group=S.CONCLUIDA)])
    c = cl(ev("JH-101", "2026-09-29 12:00", "A fazer", "Em andamento", S.PENDENTE, S.ANDAMENTO))
    last = time_in_status(items, c, NOW).segments.iloc[-1]
    assert last["status"] == "Concluído" and last["inconsistent"] and last["current"]


def test_duration_is_absolute_elapsed_time_across_a_dst_change():
    # Em 04/11/2018 São Paulo entrou em horário de verão à 00:00: o "dia" teve 23h. A duração não pode ser 24h de relógio.
    items = pd.DataFrame([{"subtask_key": "K-1", "status_name": "Em andamento", "status_group": S.ANDAMENTO,
                           "created": ts("2018-11-03 12:00")}])
    c = cl(ev("K-1", "2018-11-04 12:00", "A fazer", "Em andamento", S.PENDENTE, S.ANDAMENTO))
    first = time_in_status(items, c, ts("2018-11-04 12:00")).segments.iloc[0]
    assert first["hours"] == 23.0


def test_utc_and_local_inputs_give_the_same_duration():
    items = pd.DataFrame([{"subtask_key": "K-1", "status_name": "Em andamento", "status_group": S.ANDAMENTO,
                           "created": pd.Timestamp("2026-09-28 11:00", tz="UTC").tz_convert(TZ)}])      # 08:00 local
    c = cl({"subtask_key": "K-1", "ts": pd.Timestamp("2026-09-28 15:00", tz="UTC").tz_convert(TZ), "from_name": "A fazer",
            "to_name": "Em andamento", "from_group": S.PENDENTE, "to_group": S.ANDAMENTO})
    assert time_in_status(items, c, NOW).segments.iloc[0]["hours"] == 4.0
    assert str(time_in_status(items, c, NOW).segments["start"].dt.tz) == TZ


def test_by_group_ignores_time_after_done_and_keeps_flow_order():
    items = pd.DataFrame([item(status="Concluído", group=S.CONCLUIDA)])
    c = cl(ev("JH-101", "2026-09-28 12:00", "A fazer", "Em andamento", S.PENDENTE, S.ANDAMENTO),
           ev("JH-101", "2026-09-29 12:00", "Em andamento", "Concluído", S.ANDAMENTO, S.CONCLUIDA))
    seg = time_in_status(items, c, NOW).segments
    m = by_group(seg)
    assert list(m.columns) == [S.PENDENTE, S.ANDAMENTO] and m.loc["JH-101", S.ANDAMENTO] == 24     # as 24h em "Concluído" ficam de fora
    assert S.CONCLUIDA in by_group(seg, include_done=True).columns


@pytest.mark.parametrize("fn", [per_status, by_group, current_status_hours])
def test_empty_segments_are_handled(fn):
    empty = time_in_status(pd.DataFrame([item()]).iloc[0:0], EMPTY, NOW).segments
    assert len(fn(empty)) == 0
