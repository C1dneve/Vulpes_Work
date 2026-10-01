"""Burnup da Sprint (funções puras): ESCOPO total e TRABALHO concluído, separados — e o escopo pode mudar.

Como o escopo é reconstruído (e o que NÃO é possível):
  * Pertencimento de cada task à Sprint vem dos eventos do campo `Sprint` do histórico do Jira (entrou/saiu em data X).
    Task sem nenhum evento citando esta sprint = presente desde a criação (ou desde o início da sprint, se foi criada antes);
    a base de cada task fica registrada (`events` vs `approx`) e é resumida em `basis`.
  * Saída que acontece NO FIM de uma sprint encerrada (item não concluído levado à próxima) é carry-over, não redução de escopo.
  * Concluído em cada dia = task em "Concluída" ao FIM do dia (reabertura desconta), só se ainda estava no escopo naquele dia.
  * Story Points: soma dos pontos das Stories que têm Subtask no escopo; Story conta como concluída quando o status DA STORY no Jira é
    Concluída (data de resolução). O histórico do VALOR dos pontos e da Story no Jira não é carregado: mudança do valor de pontos NÃO
    é reconstruída (só a entrada/saída de Stories). Story sem pontos nunca vira 0: fica fora da soma e é contada em `sp_missing`.
  * A série vai até hoje (ou o fim da sprint, se encerrada): NÃO se desenha escopo futuro constante.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field

import pandas as pd

from domain import statuses as S
from domain import timeutil
from domain.fmt import isna

DAY_COLS = ["date", "scope_items", "done_items", "scope_sp", "done_sp"]
CHANGE_COLS = ["date", "key", "change", "basis"]


@dataclass
class Burnup:
    days: pd.DataFrame
    changes: pd.DataFrame                  # entradas/saídas de escopo APÓS o início da sprint
    sp_available: bool = False
    sp_missing: int = 0                    # Stories no escopo sem Story Points (fora da soma)
    basis: dict = field(default_factory=dict)       # {"events": n, "approx": n}
    undated_done: list[str] = field(default_factory=list)   # concluídas sem data confiável (não entram no 'concluído')
    notes: list[str] = field(default_factory=list)


def _matches(ids: list, names: list, sprint: dict) -> bool:
    return (sprint.get("id") is not None and str(sprint["id"]) in [str(i) for i in ids]) or sprint["name"] in names


def _mentions(e: pd.Series, sprint: dict) -> bool:
    return _matches(e["from_ids"], e["from_names"], sprint) or _matches(e["to_ids"], e["to_names"], sprint)


def _membership(item: pd.Series, events: pd.DataFrame, sprint: dict, start: pd.Timestamp, end_carry: pd.Timestamp | None,
                ) -> tuple[list[tuple[pd.Timestamp, pd.Timestamp | None]], str]:
    """Intervalos [entrada, saída) de pertencimento à sprint (datas locais) e a base ('events' | 'approx')."""
    created = timeutil.local_date(item.get("created"))
    base_start = start if isna(created) else max(created, start)
    mentions = [e for _, e in events.iterrows() if _mentions(e, sprint)]
    if not mentions:
        return [(base_start, None)], "approx"
    intervals: list[list] = []
    cur = _matches(events.iloc[0]["from_ids"], events.iloc[0]["from_names"], sprint)
    if cur:
        intervals.append([base_start, None])
    for _, e in events.sort_values("ts").iterrows():
        after = _matches(e["to_ids"], e["to_names"], sprint)
        d = max(e["date"], start) if not isna(e["date"]) else start
        if after and not cur:
            intervals.append([d, None])
        elif cur and not after:
            if end_carry is not None and e["date"] >= end_carry:
                pass                                   # carry-over de fim de sprint: continua contando como escopo
            elif intervals:
                intervals[-1][1] = d
        cur = after
    return [(a, b) for a, b in intervals], "events"


def _group_timeline(evs: pd.DataFrame, item: pd.Series) -> tuple[str | None, list, list]:
    """(grupo inicial, datas das transições, grupos de destino) — calculado UMA vez por task (None = desconhecido)."""
    if evs.empty:
        if item["status_group"] != S.CONCLUIDA:
            return item["status_group"], [], []
        d = timeutil.local_date(item.get("resolved"))
        return (None, [], []) if isna(d) else (S.PENDENTE, [d], [S.CONCLUIDA])
    return evs.iloc[0]["from_group"], list(evs["date"]), list(evs["to_group"])


def _group_on(day: pd.Timestamp, tl: tuple[str | None, list, list]) -> str | None:
    """Grupo de status da task ao FIM de `day`."""
    initial, dates, groups = tl
    i = bisect_right(dates, day)
    return initial if i == 0 else groups[i - 1]


def burnup(items: pd.DataFrame, stories: pd.DataFrame, changelog: pd.DataFrame, sprint_events: pd.DataFrame, sprint: dict,
           now: pd.Timestamp, *, story_keys: set[str] | None = None, assignee: str | None = None) -> Burnup:
    """`items`/`stories`/`changelog`/`sprint_events` = frames BRUTOS (não filtrados pela sprint: quem saiu dela continua visível)."""
    empty = Burnup(pd.DataFrame(columns=DAY_COLS), pd.DataFrame(columns=CHANGE_COLS))
    start, end = timeutil.local_date(sprint.get("start")), timeutil.local_date(sprint.get("end"))
    if isna(start):
        empty.notes.append("A sprint não tem data de início: não há como montar o Burnup.")
        return empty
    today = timeutil.local_date(now)
    closed = sprint.get("state") == "closed"
    last = min(end, today) if not isna(end) else today
    if closed and not isna(end):
        last = end
    if last < start:
        empty.notes.append("A sprint ainda não começou.")
        return empty
    complete = timeutil.local_date(sprint.get("complete")) if closed else pd.NaT
    carry_from = complete if not isna(complete) else (end if closed else None)

    ev_by = {k: g.sort_values("ts") for k, g in sprint_events.groupby("subtask_key")} if not sprint_events.empty else {}
    cl_by = {k: g.sort_values("ts") for k, g in changelog.groupby("subtask_key")} if not changelog.empty else {}
    mentioned = {k for k, g in ev_by.items() if any(_mentions(r, sprint) for _, r in g.iterrows())}
    cand = items[(items["sprint"] == sprint["name"]) | items["subtask_key"].isin(mentioned)]
    if story_keys is not None:
        cand = cand[cand["story_key"].isin(story_keys)]
    if assignee:
        cand = cand[cand["assignee"] == assignee]

    days = pd.date_range(start, last, freq="D")
    mem: dict[str, list] = {}
    basis = {"events": 0, "approx": 0}
    changes: list[dict] = []
    for _, it in cand.iterrows():
        k = it["subtask_key"]
        iv, how = _membership(it, ev_by.get(k, sprint_events.iloc[0:0]), sprint, start, carry_from)
        mem[k] = iv
        basis[how] += 1
        for a, b in iv:
            if a > start:
                changes.append({"date": a, "key": k, "change": "entrou", "basis": how})
            if b is not None:
                changes.append({"date": b, "key": k, "change": "saiu", "basis": how})

    def member(k: str, d: pd.Timestamp) -> bool:
        return any(a <= d and (b is None or d < b) for a, b in mem[k])

    undated: set[str] = set()
    cand_rows = [(it["subtask_key"], it) for _, it in cand.iterrows()]
    tls = {k: _group_timeline(cl_by.get(k, changelog.iloc[0:0]), it) for k, it in cand_rows}
    st_by = stories.set_index("story_key") if not stories.empty else pd.DataFrame()
    cand_story: dict[str, list[str]] = {}
    for _, it in cand.iterrows():
        cand_story.setdefault(it["story_key"], []).append(it["subtask_key"])
    sp_stories = {sk: st_by.loc[sk] for sk in cand_story if sk in st_by.index}
    sp_has = {sk: not isna(s["story_points"]) for sk, s in sp_stories.items()}
    sp_available = any(sp_has.values())
    rows = []
    for d in days:
        scope = done = 0
        for k, _it in cand_rows:
            if not member(k, d):
                continue
            scope += 1
            g = _group_on(d, tls[k])
            if g is None:
                undated.add(k)
            elif g == S.CONCLUIDA:
                done += 1
        sp_scope = sp_done = 0.0
        for sk, kids in cand_story.items():
            if sk not in sp_stories or not sp_has[sk] or not any(member(k, d) for k in kids):
                continue
            s = sp_stories[sk]
            sp_scope += float(s["story_points"])
            resolved = timeutil.local_date(s.get("resolved")) if s["status_group"] == S.CONCLUIDA else pd.NaT
            if s["status_group"] == S.CONCLUIDA and (isna(resolved) or resolved <= d):
                sp_done += float(s["story_points"])
        rows.append({"date": d, "scope_items": scope, "done_items": done,
                     "scope_sp": sp_scope if sp_available else None, "done_sp": sp_done if sp_available else None})
    notes = []
    if undated:
        notes.append(f"{len(undated)} task(s) concluída(s) sem data de conclusão no Jira não entram no 'concluído': "
                     f"{', '.join(sorted(undated))}.")
    if basis["approx"]:
        notes.append(f"{basis['approx']} de {len(cand)} task(s) sem evento de Sprint no histórico: "
                     "presentes desde a criação (ou desde o início da sprint).")
    notes.append("Pontos: o histórico do valor dos pontos não é carregado; só entrada/saída de Stories é refletida.")
    chg = pd.DataFrame(changes, columns=CHANGE_COLS)
    chg = chg.sort_values("date").reset_index(drop=True) if changes else chg
    return Burnup(pd.DataFrame(rows, columns=DAY_COLS), chg, sp_available, sum(1 for v in sp_has.values() if not v), basis,
                  sorted(undated), notes)
