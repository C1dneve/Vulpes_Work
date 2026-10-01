"""Linha do tempo de eventos da Sprint (funções puras). Primeira visão cronológica útil — NÃO é reconstrução histórica perfeita.

Fontes: criação/resolução da issue e changelog de status (Jira), worklogs (Jira), commits humanos, abertura/revisão/merge de PR
(GitHub). Não há evento onde o dado não existe: p.ex. revisor e data de "pronta para revisão" da PR não são coletados.
"""
from __future__ import annotations

import pandas as pd

from domain import statuses as S
from domain import timeutil
from domain.fmt import fmt_hours, isna

EV_CREATED, EV_STATUS, EV_WORKLOG, EV_COMMIT = "Issue criada", "Status alterado", "Worklog", "Commit"
EV_PR_OPEN, EV_PR_REVIEW, EV_PR_MERGE, EV_DONE = "PR aberta", "PR revisada", "PR mergeada", "Issue concluída"
EVENT_TYPES = [EV_CREATED, EV_STATUS, EV_WORKLOG, EV_COMMIT, EV_PR_OPEN, EV_PR_REVIEW, EV_PR_MERGE, EV_DONE]
TL_COLS = ["ts", "date", "type", "key", "title", "person", "detail", "url"]


def _ev(ts: object, typ: str, key: str, title: object, person: object, detail: str, url: object = None) -> dict | None:
    if isna(ts):
        return None
    return {"ts": ts, "type": typ, "key": key, "title": "" if isna(title) else str(title), "person": None if isna(person) else person,
            "detail": detail, "url": None if isna(url) else url}


def build_timeline(items: pd.DataFrame, changelog: pd.DataFrame, worklogs: pd.DataFrame, commits: pd.DataFrame,
                   prs: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict | None] = []
    title_of = dict(zip(items["subtask_key"], items["subtask_summary"], strict=True)) if not items.empty else {}
    for _, it in items.iterrows():
        k = it["subtask_key"]
        rows.append(_ev(it["created"], EV_CREATED, k, it["subtask_summary"], it["assignee"], str(it.get("issue_type") or "")))
        if it["status_group"] == S.CONCLUIDA:     # concluída = última entrada em "Concluída"; sem changelog, a resolução do Jira
            mine = changelog[(changelog["subtask_key"] == k) & (changelog["to_group"] == S.CONCLUIDA)] if not changelog.empty else changelog
            entered = mine["ts"] if not mine.empty else []
            done_at = max(entered) if len(entered) else it.get("resolved")
            rows.append(_ev(done_at, EV_DONE, k, it["subtask_summary"], it["assignee"], f"status: {it['status_name']}"))
    for _, c in changelog.iterrows():
        rows.append(_ev(c["ts"], EV_STATUS, c["subtask_key"], title_of.get(c["subtask_key"]), c["author"],
                        f"{c['from_name']} → {c['to_name']}"))
    for _, w in worklogs.iterrows():
        rows.append(_ev(w["started"], EV_WORKLOG, w["subtask_key"], title_of.get(w["subtask_key"]), w["author"],
                        f"{fmt_hours(w['time_spent_h'])} registradas"))
    hc = commits[commits["kind"] == "human"] if not commits.empty and "kind" in commits else commits
    for _, c in hc.iterrows():
        key = c["jira_key"] if not isna(c["jira_key"]) else "(sem chave)"
        rows.append(_ev(c["date"], EV_COMMIT, key, c["title"], c["author"], str(c["sha"])[:7], c.get("url")))
    for _, p in prs.iterrows():
        k, who = f"PR #{p['number']}", p["author"]
        rows.append(_ev(p["created"], EV_PR_OPEN, k, p["title"], who, "rascunho" if p.get("draft") else "aberta", p.get("url")))
        if not isna(p.get("first_review_at")):
            rows.append(_ev(p["first_review_at"], EV_PR_REVIEW, k, p["title"], None, "primeira revisão", p.get("url")))
            if p["last_review_at"] != p["first_review_at"]:
                rows.append(_ev(p["last_review_at"], EV_PR_REVIEW, k, p["title"], None,
                                f"última revisão ({p.get('last_review_state')})", p.get("url")))
        rows.append(_ev(p.get("merged_at"), EV_PR_MERGE, k, p["title"], who, f"→ {p.get('base')}", p.get("url")))
    df = pd.DataFrame([r for r in rows if r], columns=[c for c in TL_COLS if c != "date"])
    if df.empty:
        return pd.DataFrame(columns=TL_COLS)
    df["date"] = timeutil.local_dates(df["ts"])
    return df.sort_values("ts", kind="stable").reset_index(drop=True)[TL_COLS]
