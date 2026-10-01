"""Orquestra as regras de gestão do MVP sobre um `Bundle` + `Context` (sem Streamlit: testável).

Dois escopos, de propósito:
  * `team`  = Sprint/Stories do filtro, SEM filtro de pessoa → evidência GitHub e alertas (a PR da Ana cobre a task do Zeca);
  * `scope` = escopo completo (com a pessoa) → o que as tabelas mostram.
O filtro de pessoa vale para as LINHAS (tasks, alertas, eventos), nunca para a evidência.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

from domain import alerts as A
from domain import timeline as T
from domain import timeutil
from domain.burnup import Burnup, burnup
from domain.sprint_view import enrich_items, enrich_stories, people_table, sprint_kpis
from domain.thresholds import Thresholds
from domain.time_in_status import TimeInStatus, time_in_status
from services.context import Bundle, Context, Scope, apply_context


@dataclass
class Mgmt:
    ctx: Context
    now: pd.Timestamp
    th: Thresholds
    scope: Scope                       # com pessoa
    team: Scope                        # sem pessoa
    known_keys: set[str]
    items: pd.DataFrame                # tasks enriquecidas (com pessoa)
    items_team: pd.DataFrame
    stories: pd.DataFrame              # Stories enriquecidas (rollup só das tasks do escopo com pessoa)
    stories_team: pd.DataFrame
    kpis: dict
    people: pd.DataFrame               # alfabética; sempre do time (a página filtra por pessoa depois)
    alerts: pd.DataFrame               # já filtrados pela pessoa, se houver
    alerts_team: pd.DataFrame
    alert_notes: list[str]
    tis: TimeInStatus
    timeline: pd.DataFrame
    burnup: Burnup | None
    sprint_info: dict | None
    notes: list[str] = field(default_factory=list)   # limitações ativas nesta tela (fonte parcial/antiga etc.)


def sprint_dict(sprints: pd.DataFrame, name: str | None) -> dict | None:
    if not name or sprints.empty or not (sprints["name"] == name).any():
        return None
    r = sprints[sprints["name"] == name].iloc[0]
    return {"name": r["name"], "id": r["sprint_id"], "start": r["start"], "end": r["end"], "complete": r["complete"], "state": r["state"]}


def build_mgmt(raw: Bundle, ctx: Context, th: Thresholds, *, now: pd.Timestamp | None = None, github_ok: bool = True,
               github_since: pd.Timestamp | None = None, history_unknown: set[str] | frozenset[str] = frozenset(),
               github_partial: bool = False, github_stale: bool = False) -> Mgmt:
    now = now if now is not None else timeutil.now()
    team = apply_context(raw, replace(ctx, dev=None))
    scope = team if not ctx.dev else apply_context(raw, ctx)
    known = set(raw.items["subtask_key"]) | set(raw.stories["story_key"])

    items_team = enrich_items(team.items, team.changelog, team.worklogs, team.commits, known, now, th)
    stories_team = enrich_stories(team.stories, items_team, raw.items, team.commits, team.branches, team.prs, known, now, th)
    if ctx.dev:
        items = items_team[items_team["subtask_key"].isin(scope.items["subtask_key"])].reset_index(drop=True)
        stories = enrich_stories(scope.stories, items, raw.items, team.commits, team.branches, team.prs, known, now, th)
    else:
        items, stories = items_team, stories_team

    sprint = sprint_dict(raw.sprints, ctx.sprint)
    rep = A.build_alerts(items_team, team.stories, raw.items, team.commits, team.prs, known_keys=known, now=now, th=th,
                         github_ok=github_ok, github_since=github_since, sprint=sprint)
    narrowed = scope.narrowed
    bu = None
    if sprint is not None:
        bu = burnup(raw.items, raw.stories, raw.changelog, raw.sprint_events, sprint, now,
                    story_keys=set(ctx.story_keys) if narrowed and ctx.story_keys is not None else None, assignee=ctx.dev)

    notes: list[str] = []
    if github_stale:
        notes.append("GitHub: exibindo dados antigos (a busca atual falhou); alertas Jira↔GitHub podem estar defasados.")
    elif github_partial:
        notes.append("GitHub: carga parcial; alertas de 'sem evidência' podem ter falso positivo (veja Configurações → Sincronização).")
    if history_unknown:
        notes.append(f"Histórico de status incompleto para {len(history_unknown)} task(s): sem tempo em status para elas.")
    return Mgmt(
        ctx=ctx, now=now, th=th, scope=scope, team=team, known_keys=known, items=items, items_team=items_team, stories=stories,
        stories_team=stories_team, kpis=sprint_kpis(stories, items),
        people=people_table(items_team, team.stories, team.worklogs, team.commits, team.branches, team.prs),
        alerts=A.for_person(rep.alerts, ctx.dev), alerts_team=rep.alerts, alert_notes=rep.notes,
        tis=time_in_status(scope.items, scope.changelog, now, history_unknown),
        timeline=T.build_timeline(scope.items, scope.changelog, scope.worklogs, scope.commits, scope.prs),
        burnup=bu, sprint_info=sprint, notes=notes)
