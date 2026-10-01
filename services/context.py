"""Contexto global de filtros (sprint / colaborador / user stories) aplicado a TODOS os dados.

Antes, o filtro de sprint só mudava a lista de User Stories: commits, branches, PRs e worklogs continuavam
globais, e cada tela mostrava um recorte diferente. Agora existe UM `Context` e UM `apply_context`.

Regras de pertencimento ao escopo (commits, branches e PRs seguem as mesmas):
  * vinculado (chave Jira, chave herdada da PR/branch ou ID visual): entra se o vínculo aponta para algo do escopo.
    A chave oficial vence: se o commit cita a chave de OUTRA issue conhecida, nem a referência da PR/branch
    nem o ID visual o trazem para cá;
  * sprint: uma Subtask pertence à sprint DELA (ou à da Story, se não tiver a própria). A Story entra no escopo se
    está na sprint OU se tem Subtasks nela (`stories_in_sprint`), sem duplicar;
  * sem vínculo nenhum: entra se a atividade caiu dentro da janela da sprint (ou se não há janela);
    se a pessoa recortou manualmente as User Stories, atividade sem vínculo fica de fora;
  * colaborador: commits/PRs/branches pelo autor; worklogs pelo autor; tasks pelo responsável.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from domain import timeutil


@dataclass
class Bundle:
    stories: pd.DataFrame
    items: pd.DataFrame
    worklogs: pd.DataFrame
    changelog: pd.DataFrame
    sprints: pd.DataFrame
    commits: pd.DataFrame
    branches: pd.DataFrame
    prs: pd.DataFrame
    # Mudanças do campo Sprint no histórico do Jira (base para reconstruir o escopo do Burnup). Opcional: frames antigos não têm.
    sprint_events: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(
        columns=["subtask_key", "ts", "date", "from_ids", "to_ids", "from_names", "to_names"]))


@dataclass(frozen=True)
class Context:
    sprint: str | None = None          # None = todas as sprints
    dev: str | None = None             # None = todos
    story_keys: tuple[str, ...] | None = None  # None = todas as stories da sprint


@dataclass
class Scope(Bundle):
    window: tuple[pd.Timestamp | None, pd.Timestamp | None] = (None, None)
    narrowed: bool = False


def sprint_options(stories: pd.DataFrame, sprints: pd.DataFrame) -> list[str]:
    """Nomes de sprint, da mais recente para a mais antiga (usa o board; cai para as stories)."""
    names: list[str] = []
    if not sprints.empty:
        names += sprints.sort_values("start", ascending=False, na_position="last")["name"].dropna().tolist()
    for n in stories["sprint"].dropna().unique() if not stories.empty else []:
        if n not in names and n != "Sem Sprint":
            names.append(n)
    if not stories.empty and "Sem Sprint" in set(stories["sprint"]):
        names.append("Sem Sprint")
    return names


def stories_in_sprint(stories: pd.DataFrame, items: pd.DataFrame, sprint: str) -> pd.DataFrame:
    """Stories na sprint OU com pelo menos uma Subtask nela (a sprint da Subtask pode diferir da da Story)."""
    if stories.empty:
        return stories
    with_items = set(items.loc[items["sprint"] == sprint, "story_key"]) if not items.empty else set()
    return stories[(stories["sprint"] == sprint) | stories["story_key"].isin(with_items)]


def default_sprint(stories: pd.DataFrame, sprints: pd.DataFrame) -> str | None:
    """Sprint ativa (a mais recente, se houver mais de uma); senão a mais recente com datas; senão a primeira."""
    if not sprints.empty:
        active = sprints[sprints["state"] == "active"].sort_values("start", ascending=False)
        if not active.empty:
            return active.iloc[0]["name"]
    if not stories.empty and "sprint_state" in stories and (stories["sprint_state"] == "active").any():
        return stories[stories["sprint_state"] == "active"].iloc[0]["sprint"]
    opts = sprint_options(stories, sprints)
    return opts[0] if opts else None


def sprint_window(stories: pd.DataFrame, sprints: pd.DataFrame, sprint: str | None,
                  story_keys: tuple[str, ...] | None = None) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """(início, fim) como datas locais naive. Sprint escolhida -> datas dela; 'Todas' -> união das stories."""
    def bound(series: pd.Series, agg: str):
        v = series.dropna()
        return None if v.empty else timeutil.local_date(getattr(v, agg)())

    if sprint and not sprints.empty and (sprints["name"] == sprint).any():
        row = sprints[sprints["name"] == sprint].iloc[0]
        return bound(pd.Series([row["start"]]), "min"), bound(pd.Series([row["end"]]), "max")
    sel = stories if story_keys is None else stories[stories["story_key"].isin(story_keys)]
    if sprint:
        sel = sel[sel["sprint"] == sprint]
    if sel.empty:
        return None, None
    return bound(sel["sprint_start"], "min"), bound(sel["sprint_end"], "max")


def apply_context(b: Bundle, ctx: Context) -> Scope:
    stories, items = b.stories, b.items
    if ctx.sprint:
        stories, items = stories_in_sprint(stories, items, ctx.sprint), items[items["sprint"] == ctx.sprint]
    sprint_story_keys = set(stories["story_key"])
    narrowed = ctx.story_keys is not None and set(ctx.story_keys) != sprint_story_keys
    if ctx.story_keys is not None:
        keep = set(ctx.story_keys)
        stories, items = stories[stories["story_key"].isin(keep)], items[items["story_key"].isin(keep)]
    if ctx.dev:
        items = items[items["assignee"] == ctx.dev]
        stories = stories[stories["story_key"].isin(items["story_key"])]

    window = sprint_window(b.stories, b.sprints, ctx.sprint, ctx.story_keys)
    known_keys = set(b.items["subtask_key"]) | set(b.stories["story_key"])
    scope_keys = set(items["subtask_key"]) | set(items["story_key"])
    scope_us = set(stories["us_id"].dropna())
    # A janela de datas só restringe atividade SEM vínculo quando uma sprint específica está selecionada.
    start, end = window if ctx.sprint else (None, None)

    def select(df: pd.DataFrame, date_col: str, author_col: str) -> pd.DataFrame:
        if df.empty:
            return df
        own = df["jira_key"]
        ref = df["ref_jira_key"] if "ref_jira_key" in df else pd.Series(None, index=df.index, dtype="object")  # da PR/branch
        linked = own.notna() | ref.notna() | df["us_id"].notna()
        unknown_own = ~own.isin(known_keys)   # a chave própria de OUTRA issue conhecida vence referência e ID visual
        in_scope = own.isin(scope_keys) | (ref.isin(scope_keys) & unknown_own) | (df["us_id"].isin(scope_us) & unknown_own)
        if narrowed:
            unlinked_ok = pd.Series(False, index=df.index)
        elif start is None or end is None:
            unlinked_ok = pd.Series(True, index=df.index)
        else:
            d = timeutil.local_dates(df[date_col]) if df[date_col].dt.tz is not None else df[date_col]
            unlinked_ok = d.isna() | ((d >= start) & (d <= end))
        out = df[(linked & in_scope) | (~linked & unlinked_ok)]
        return out[out[author_col] == ctx.dev] if ctx.dev else out

    commits = select(b.commits, "date", "author")
    prs = select(b.prs, "created", "author")
    branches = b.branches
    if not branches.empty:
        branches = branches[~branches["is_default"]] if (ctx.sprint or ctx.dev or narrowed) else branches
        default_rows = branches[branches["is_default"]]
        branches = pd.concat([select(branches[~branches["is_default"]], "last_commit", "last_author"), default_rows])

    worklogs = b.worklogs[b.worklogs["subtask_key"].isin(items["subtask_key"])] if not b.worklogs.empty else b.worklogs
    if ctx.dev and not worklogs.empty:
        worklogs = worklogs[worklogs["author"] == ctx.dev]
    changelog = b.changelog[b.changelog["subtask_key"].isin(items["subtask_key"])] if not b.changelog.empty else b.changelog
    events = b.sprint_events
    if not events.empty:
        events = events[events["subtask_key"].isin(items["subtask_key"])]
    return Scope(stories, items, worklogs, changelog, b.sprints, commits, branches, prs, sprint_events=events,
                 window=window, narrowed=narrowed)
