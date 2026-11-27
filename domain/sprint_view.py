"""Tabelas de gestão da Sprint (funções puras): tasks enriquecidas, Stories e Pessoas.

Vínculo Jira <-> GitHub segue as regras P0 de `domain/linking.py` (Jira Key oficial; Commit = Subtask; Branch/PR = Story).
Os frames de GitHub recebidos devem ser os da SPRINT SEM filtro de pessoa (fato da Story, não de quem escreveu): o filtro de
pessoa é aplicado nas LINHAS (tasks/alertas), senão uma PR escrita por outra pessoa sumiria e geraria falso "Done sem PR".
"""
from __future__ import annotations

import pandas as pd

from domain import statuses as S
from domain import work as W
from domain.fmt import isna
from domain.linking import branches_for_story, commits_for_item, commits_for_story, prs_for_story
from domain.people import nome_exibicao
from domain.thresholds import Thresholds

_STATUS_ORDER = [S.CONCLUIDA, S.TESTE, S.ANALISE, S.ANDAMENTO, S.PENDENTE, S.BLOQUEADA]


def _human(commits: pd.DataFrame) -> pd.DataFrame:
    return commits[commits["kind"] == "human"] if not commits.empty and "kind" in commits else commits


def _by_key(df: pd.DataFrame, col: str = "subtask_key") -> dict[str, pd.DataFrame]:
    return {k: g for k, g in df.groupby(col)} if not df.empty else {}


ITEM_EXTRA = ["side", "logged_h", "diff_h", "remaining_eff_h", "remaining_source", "due_status", "days_to_due", "is_done",
              "is_blocked", "block_sources", "block_reason", "blocked_since", "blocked_hours", "last_activity",
              "last_activity_source", "inactive_bdays", "is_inactive", "n_commits", "n_commits_delivered", "last_commit"]


def enrich_items(items: pd.DataFrame, changelog: pd.DataFrame, worklogs: pd.DataFrame, commits: pd.DataFrame,
                 known_keys: set[str], now: pd.Timestamp, th: Thresholds) -> pd.DataFrame:
    """Uma linha por task com prazo, esforço, bloqueio, atividade e evidência de commits (só commits que citam a chave DELA)."""
    if items.empty:
        return pd.DataFrame(columns=[*items.columns, *ITEM_EXTRA])
    cl, wl, hc = _by_key(changelog), _by_key(worklogs), _human(commits)
    empty_cl, empty_wl = changelog.iloc[0:0], worklogs.iloc[0:0]
    today = now.tz_localize(None).normalize()
    rows = []
    for _, it in items.iterrows():
        k = it["subtask_key"]
        c_item, w_item = cl.get(k, empty_cl), wl.get(k, empty_wl)
        cm = commits_for_item(hc, it, known_keys) if not hc.empty else hc
        e = W.effort(it.get("estimate_h"), it.get("time_spent_h"), it.get("remaining_h"))
        blk = W.block_info(it, c_item, now)
        act = W.last_activity(it, c_item, w_item, cm, now, th)
        rows.append({
            "side": W.item_side(it.get("subtask_code")), "logged_h": e.logged_h, "diff_h": e.diff_h,
            "remaining_eff_h": e.remaining_h, "remaining_source": e.remaining_source,
            "due_status": W.due_status(it.get("due_date"), it["status_group"], today, th),
            "days_to_due": W.days_to_due(it.get("due_date"), today), "is_done": it["status_group"] == S.CONCLUIDA,
            "is_blocked": blk.is_blocked, "block_sources": blk.sources, "block_reason": blk.reason,
            "blocked_since": blk.since, "blocked_hours": blk.hours, "last_activity": act.last,
            "last_activity_source": act.source, "inactive_bdays": act.business_days, "is_inactive": act.inactive,
            "n_commits": len(cm), "n_commits_delivered": int(cm["delivered"].sum()) if len(cm) else 0,
            "last_commit": cm["date"].max() if len(cm) else pd.NaT})
    return pd.concat([items.reset_index(drop=True), pd.DataFrame(rows, columns=ITEM_EXTRA)], axis=1)


def _assignees(series: pd.Series) -> list[str]:
    return sorted({a for a in series.dropna() if a != "nenhum"}, key=nome_exibicao)


def _pr_summary(prs: pd.DataFrame) -> str:
    if prs.empty:
        return ""
    return ", ".join(f"#{r['number']} {r['review_state']}" if "review_state" in prs and not isna(r.get("review_state"))
                     else f"#{r['number']} {r['state']}" for _, r in prs.sort_values("number").iterrows())


def enrich_stories(stories: pd.DataFrame, items_e: pd.DataFrame, all_items: pd.DataFrame, commits: pd.DataFrame,
                   branches: pd.DataFrame, prs: pd.DataFrame, known_keys: set[str], now: pd.Timestamp,
                   th: Thresholds) -> pd.DataFrame:
    """Uma linha por Story com: responsável, status (do Jira), pontos, esforço (soma das Subtasks, CALCULADO), prazo e
    a evidência do GitHub ligada à Story (branches, PRs, commits). `all_items` = TODAS as tasks (para resolver as Subtasks da Story
    mesmo quando o filtro de pessoa esconde parte delas)."""
    cols = ["story_key", "us_id", "story_summary", "responsavel", "team", "status_name", "status_group", "story_points",
            "estimate_h", "estimate_coverage", "logged_h", "remaining_h", "remaining_partial", "due_date", "due_source",
            "due_status", "subtasks_total", "subtasks_done", "n_blocked", "n_inactive", "n_late", "n_branches", "n_prs",
            "n_commits", "pr_states", "epic_key", "epic_summary", "sprint", "kind"]
    if stories.empty:
        return pd.DataFrame(columns=cols)
    today = now.tz_localize(None).normalize()
    hc = _human(commits)
    rows = []
    for _, s in stories.iterrows():
        sk, us = s["story_key"], s["us_id"] if not isna(s.get("us_id")) else None
        mine = items_e[items_e["story_key"] == sk] if not items_e.empty else items_e
        children = set(all_items.loc[all_items["story_key"] == sk, "subtask_key"]) if not all_items.empty else set()
        roll = W.rollup_effort(mine) if len(mine) else {"estimate_h": None, "estimate_coverage": "0/0", "logged_h": 0.0,
                                                          "remaining_h": None, "remaining_partial": False}
        own_due = s.get("due_date")
        open_dues = [d for d in (mine.loc[~mine["is_done"], "due_date"] if len(mine) else []) if not isna(d) and d != ""]
        if not isna(own_due) and own_due != "":
            due, src = own_due, "story"
        elif open_dues:
            due, src = min(open_dues), "subtasks"     # prazo mais próximo entre as Subtasks ABERTAS (calculado, rotulado)
        else:
            due, src = None, None
        all_done = bool(len(mine) and mine["is_done"].all())
        group = s.get("status_group") if not isna(s.get("status_group")) else (S.CONCLUIDA if all_done else S.PENDENTE)
        b, p = branches_for_story(branches, sk, us, children, known_keys), prs_for_story(prs, sk, us, children, known_keys)
        cm = commits_for_story(hc, sk, us, children, known_keys) if not hc.empty else hc
        rows.append({
            "story_key": sk, "us_id": us, "story_summary": s["story_summary"],
            "responsavel": s.get("assignee") if not isna(s.get("assignee")) and s.get("assignee") != "nenhum" else None,
            "team": _assignees(mine["assignee"]) if len(mine) else [],
            "status_name": s.get("status_name"), "status_group": group,
            "story_points": None if isna(s.get("story_points")) else float(s["story_points"]),
            "estimate_h": roll["estimate_h"], "estimate_coverage": roll["estimate_coverage"], "logged_h": roll["logged_h"],
            "remaining_h": roll["remaining_h"], "remaining_partial": roll["remaining_partial"],
            "due_date": due, "due_source": src, "due_status": W.due_status(due, group, today, th),
            "subtasks_total": len(mine), "subtasks_done": int(mine["is_done"].sum()) if len(mine) else 0,
            "n_blocked": int(mine["is_blocked"].sum()) if len(mine) else 0,
            "n_inactive": int(mine["is_inactive"].sum()) if len(mine) else 0,
            "n_late": int((mine["due_status"] == W.DUE_LATE).sum()) if len(mine) else 0,
            "n_branches": len(b), "n_prs": len(p), "n_commits": len(cm), "pr_states": _pr_summary(p),
            "epic_key": s.get("epic_key"), "epic_summary": s.get("epic_summary"), "sprint": s.get("sprint"), "kind": s.get("kind")})
    return pd.DataFrame(rows, columns=cols)


def sprint_kpis(stories_e: pd.DataFrame, items_e: pd.DataFrame) -> dict[str, int | float | None]:
    """Números da Sprint. Story Points: só das Stories que TÊM pontos; `sp_missing` diz quantas não têm (nunca conta como 0)."""
    with_sp = stories_e["story_points"].dropna() if not stories_e.empty else pd.Series(dtype=float)
    done = stories_e[stories_e["status_group"] == S.CONCLUIDA] if not stories_e.empty else stories_e
    return {
        "stories": len(stories_e), "stories_done": len(done),
        "sp_planned": float(with_sp.sum()) if len(with_sp) else None,
        "sp_done": float(done["story_points"].dropna().sum()) if len(with_sp) else None,
        "sp_missing": int(stories_e["story_points"].isna().sum()) if not stories_e.empty else 0,
        "items": len(items_e), "items_done": int(items_e["is_done"].sum()) if len(items_e) else 0,
        "estimate_h": float(items_e["estimate_h"].dropna().sum()) if len(items_e) and items_e["estimate_h"].notna().any() else None,
        "estimate_items": int(items_e["estimate_h"].notna().sum()) if len(items_e) else 0,
        "logged_h": float(items_e["logged_h"].fillna(0).sum()) if len(items_e) else 0.0,
        "blocked": int(items_e["is_blocked"].sum()) if len(items_e) else 0,
        "late": int((items_e["due_status"] == W.DUE_LATE).sum()) if len(items_e) else 0,
        "inactive": int(items_e["is_inactive"].sum()) if len(items_e) else 0,
    }


def people_table(items_e: pd.DataFrame, stories: pd.DataFrame, worklogs: pd.DataFrame, commits: pd.DataFrame,
                 branches: pd.DataFrame, prs: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por pessoa, em ORDEM ALFABÉTICA (não é ranking). Horas e contagens descrevem o trabalho; não medem valor."""
    cols = ["person", "name", "tasks", *_STATUS_ORDER, "estimate_h", "logged_on_tasks_h", "logged_by_person_h",
            "stories", "story_points_related", "commits", "branches", "prs"]
    people = set(items_e["assignee"].dropna()) - {"nenhum"} if not items_e.empty else set()
    if not worklogs.empty:
        people |= set(worklogs["author"].dropna()) - {"nenhum"}
    hc = _human(commits)
    sp_by_story = dict(zip(stories["story_key"], stories["story_points"], strict=True)) if not stories.empty else {}
    rows = []
    for who in sorted(people, key=nome_exibicao):
        mine = items_e[items_e["assignee"] == who] if not items_e.empty else items_e
        keys = sorted(set(mine["story_key"])) if len(mine) else []
        sps = [sp_by_story[k] for k in keys if not isna(sp_by_story.get(k))]
        counts = mine["status_group"].value_counts().to_dict() if len(mine) else {}
        rows.append({
            "person": who, "name": nome_exibicao(who), "tasks": len(mine), **{g: int(counts.get(g, 0)) for g in _STATUS_ORDER},
            "estimate_h": float(mine["estimate_h"].dropna().sum()) if len(mine) and mine["estimate_h"].notna().any() else None,
            "logged_on_tasks_h": float(mine["logged_h"].fillna(0).sum()) if len(mine) else 0.0,
            "logged_by_person_h": float(worklogs.loc[worklogs["author"] == who, "time_spent_h"].sum()) if not worklogs.empty else 0.0,
            "stories": len(keys), "story_points_related": float(sum(sps)) if sps else None,
            "commits": int((hc["author"] == who).sum()) if not hc.empty else 0,
            "branches": int((branches["last_author"] == who).sum()) if not branches.empty and "last_author" in branches else 0,
            "prs": int((prs["author"] == who).sum()) if not prs.empty else 0})
    return pd.DataFrame(rows, columns=cols)
