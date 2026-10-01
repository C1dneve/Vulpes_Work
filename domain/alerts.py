"""Alertas operacionais derivados dos dados já carregados (funções puras).

Severidade é FIXA por regra (nada de score mágico); só há escalonamento onde existe um limiar explícito em `Thresholds`.

  alta   = exige ação hoje:   bloqueada · atrasada · sprint vencida com itens abertos
  média  = precisa de atenção: inativa · PR sem revisão além do SLA · PR antiga · mudanças solicitadas · sprint terminando ·
                               inconsistências Jira↔GitHub · commit sem chave do Jira
  baixa  = acompanhar:          PR aguardando revisão dentro do SLA · PR só comentada · Done sem GitHub em task sem lado de código
  info   = registro:            concluída/mergeada recentemente · PR aberta sem pendência

Regras Jira↔GitHub só rodam com o GitHub carregado (`github_ok`): sem ele, "sem evidência" seria falso para tudo.
Evidência de uma SUBTASK = commit que cita a chave DELA (regra P0). PR/branch são da STORY e respeitam o lado BE/FE.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from domain import pr_review as R
from domain import statuses as S
from domain import timeutil
from domain import work as W
from domain.fmt import fmt_duration, isna
from domain.linking import prs_for_story
from domain.thresholds import Thresholds

ALTA, MEDIA, BAIXA, INFO = "alta", "média", "baixa", "info"
SEV_ORDER = {ALTA: 3, MEDIA: 2, BAIXA: 1, INFO: 0}
ALERT_COLS = ["rule", "severity", "source", "entity", "key", "story_key", "title", "owners", "detail", "since", "url"]

# regra -> (rótulo, fonte)
RULES = {
    "bloqueada": ("Tarefa bloqueada", "Jira"), "atrasada": ("Tarefa atrasada", "Jira"), "inativa": ("Tarefa inativa", "Jira"),
    "concluida": ("Tarefa concluída", "Jira"), "sprint_fim": ("Sprint próxima do fim", "Jira"),
    "pr_aguardando_revisao": ("PR aguardando revisão", "GitHub"), "pr_comentada": ("PR comentada", "GitHub"),
    "pr_mudancas": ("PR com mudanças solicitadas", "GitHub"), "pr_antiga": ("PR antiga", "GitHub"),
    "pr_aberta": ("PR aberta", "GitHub"), "pr_mergeada": ("PR mergeada", "GitHub"),
    "done_sem_github": ("Done sem evidência no GitHub", "Jira↔GitHub"), "done_sem_pr": ("Done sem PR", "Jira↔GitHub"),
    "pr_mergeada_jira_aberto": ("PR mergeada, Jira ainda em andamento", "Jira↔GitHub"),
    "analise_sem_pr": ("Em análise sem PR", "Jira↔GitHub"), "commit_sem_jira_key": ("Commit sem Jira Key", "Jira↔GitHub"),
}
GH_RULES = {r for r, (_, src) in RULES.items() if src == "Jira↔GitHub"}


@dataclass
class AlertReport:
    alerts: pd.DataFrame
    notes: list[str] = field(default_factory=list)   # o que NÃO pôde ser avaliado, e por quê (nunca silencioso)


def _alert(rule: str, severity: str, entity: str, key: str, title: object, owners: list[str], detail: str,
           since: object = pd.NaT, story_key: str | None = None, url: str | None = None) -> dict:
    return {"rule": rule, "severity": severity, "source": RULES[rule][1], "entity": entity, "key": key, "story_key": story_key,
            "title": "" if isna(title) else str(title), "owners": sorted({o for o in owners if o and o != "nenhum"}),
            "detail": detail, "since": since, "url": url}


def _owner(v: object) -> list[str]:
    return [] if isna(v) else [str(v)]


def _fmt_day(ts: object) -> str:
    return "—" if isna(ts) else pd.Timestamp(ts).strftime("%d/%m")


def _due_ts(due: object) -> pd.Timestamp:
    """Due date (data, sem fuso) como Timestamp tz-aware local à meia-noite: a coluna `since` nunca mistura naive com aware."""
    d = W.parse_due(due)
    return d if pd.isna(d) else d.tz_localize(timeutil.TZ)


def _hours_since(ts: object, now: pd.Timestamp) -> float | None:
    return None if isna(ts) else max((now - ts).total_seconds() / 3600, 0)


def _story_prs(prs: pd.DataFrame, story: pd.Series | None, sk: str, children: set[str], known: set[str], side: str | None) -> pd.DataFrame:
    """PRs da Story, restritas ao lado (BE/FE) da task quando a PR declara o lado (kind). PR sem lado vale para qualquer task."""
    us = story["us_id"] if story is not None and not isna(story.get("us_id")) else None
    found = prs_for_story(prs, sk, us, children, known)
    if found.empty or side is None or "kind" not in found:
        return found
    return found[found["kind"].isna() | (found["kind"] == side)]


def build_alerts(items_e: pd.DataFrame, stories: pd.DataFrame, all_items: pd.DataFrame, commits: pd.DataFrame, prs: pd.DataFrame, *,
                 known_keys: set[str], now: pd.Timestamp, th: Thresholds, github_ok: bool = True,
                 github_since: pd.Timestamp | None = None, sprint: dict | None = None) -> AlertReport:
    """`items_e` = tasks enriquecidas (`sprint_view.enrich_items`); `commits`/`prs` = SPRINT inteira, sem filtro de pessoa.
    `sprint` = {'name','end','state'} quando UMA sprint está selecionada (senão a regra de fim de sprint não se aplica)."""
    rows: list[dict] = []
    notes: list[str] = []
    today = now.tz_localize(None).normalize()
    sby = {r["story_key"]: r for _, r in stories.iterrows()} if not stories.empty else {}
    children_of = all_items.groupby("story_key")["subtask_key"].apply(set).to_dict() if not all_items.empty else {}
    recent = now - pd.Timedelta(days=th.recent_days)

    # ------------------------------------------------ Jira
    for _, t in items_e.iterrows():
        k, who = t["subtask_key"], _owner(t["assignee"])
        common = dict(entity="subtask", key=k, title=t["subtask_summary"], owners=who, story_key=t["story_key"])
        if t["is_done"]:
            done_at = t.get("resolved")
            if not isna(done_at) and done_at >= recent:
                rows.append(_alert("concluida", INFO, detail=f"concluída em {_fmt_day(done_at)}", since=done_at, **common))
            continue
        if t["is_blocked"]:
            why = t["block_reason"] or "motivo não informado no Jira"
            tempo = f" há {fmt_duration(t['blocked_hours'])}" if not isna(t["blocked_hours"]) else ""
            src = ", ".join(t["block_sources"])
            rows.append(_alert("bloqueada", ALTA, detail=f"{why}{tempo} (fonte: {src})", since=t["blocked_since"], **common))
        if t["due_status"] == W.DUE_LATE:
            late = -t["days_to_due"] if not isna(t["days_to_due"]) else 0
            rows.append(_alert("atrasada", ALTA, detail=f"venceu em {_fmt_day(W.parse_due(t['due_date']))} ({late}d de atraso)",
                               since=_due_ts(t["due_date"]), **common))
        if t["is_inactive"]:
            rows.append(_alert("inativa", MEDIA, detail=f"sem atividade há {t['inactive_bdays']} dia(s) útil(eis); última: "
                               f"{t['last_activity_source']} em {_fmt_day(t['last_activity'])}", since=t["last_activity"], **common))

    if sprint and not isna(sprint.get("end")):
        open_n = int((~items_e["is_done"]).sum()) if len(items_e) else 0
        left = (sprint["end"].tz_convert(now.tz).normalize().tz_localize(None) - today).days
        if open_n and sprint.get("state") == "active" and left < 0:
            rows.append(_alert("sprint_fim", ALTA, "sprint", sprint["name"], sprint["name"],
                               [], f"a sprint venceu há {-left}d e ainda tem {open_n} task(s) aberta(s)", since=sprint["end"]))
        elif open_n and sprint.get("state") == "active" and left <= th.sprint_ending_days:
            rows.append(_alert("sprint_fim", MEDIA, "sprint", sprint["name"], sprint["name"],
                               [], f"termina em {left}d com {open_n} task(s) aberta(s)", since=sprint["end"]))

    # ------------------------------------------------ GitHub (PRs)
    if github_ok and not prs.empty:
        for _, p in prs.iterrows():
            who, base = _owner(p["author"]), dict(entity="pr", key=f"PR #{p['number']}", title=p["title"], url=p.get("url"))
            skey = p["jira_key"] if not isna(p.get("jira_key")) else None
            state, rs = p["state"], p.get("review_state")
            age_h = _hours_since(p["created"], now)
            if state == "merged":
                if not isna(p["merged_at"]) and p["merged_at"] >= recent:
                    rows.append(_alert("pr_mergeada", INFO, owners=who, story_key=skey, detail=f"mergeada em {_fmt_day(p['merged_at'])}"
                                       + (" sem nenhum review" if p.get("reviews_known") and p.get("review_count") == 0 else ""),
                                       since=p["merged_at"], **base))
                continue
            if state != "open":
                continue
            specific = False
            if rs == R.AGUARDANDO:
                late = age_h is not None and age_h >= th.pr_review_wait_hours
                extra = " (acima do prazo de revisão)" if late else ""
                rows.append(_alert("pr_aguardando_revisao", MEDIA if late else BAIXA, owners=who, story_key=skey, since=p["created"],
                                   detail=f"aberta há {fmt_duration(age_h)}, sem nenhum review{extra}", **base))
                specific = True
            elif rs == R.MUDANCAS:
                rows.append(_alert("pr_mudancas", MEDIA, owners=who, story_key=skey, since=p.get("last_review_at"),
                                   detail="há mudanças solicitadas pendentes", **base))
                specific = True
            elif rs == R.COMENTADA:
                rows.append(_alert("pr_comentada", BAIXA, owners=who, story_key=skey, since=p.get("last_review_at"),
                                   detail="recebeu comentários, sem aprovação nem pedido de mudança", **base))
                specific = True
            if age_h is not None and age_h >= th.pr_old_days * 24:
                rows.append(_alert("pr_antiga", MEDIA, owners=who, story_key=skey, since=p["created"],
                                   detail=f"aberta há {fmt_duration(age_h)} (limiar: {th.pr_old_days}d)", **base))
                specific = True
            if not specific:
                labels = {R.RASCUNHO: "rascunho", R.APROVADA: "aprovada, aguardando merge",
                          R.DESCONHECIDO: "estado de revisão desconhecido"}
                why = labels.get(rs, str(rs))
                rows.append(_alert("pr_aberta", INFO, owners=who, story_key=skey, since=p["created"], detail=why, **base))
    elif not github_ok:
        notes.append("Alertas de PR e regras Jira↔GitHub desativados: GitHub indisponível (sem dados não dá para afirmar 'sem evidência').")

    # ------------------------------------------------ Jira <-> GitHub
    if github_ok:
        hc = commits[commits["kind"] == "human"] if not commits.empty and "kind" in commits else commits
        prs_cache: dict[tuple[str, str | None], pd.DataFrame] = {}
        for _, t in items_e.iterrows():
            sk = t["story_key"]
            story = sby.get(sk)
            side = t["side"]
            common = dict(entity="subtask", key=t["subtask_key"], title=t["subtask_summary"], owners=_owner(t["assignee"]), story_key=sk)
            verifiable = github_since is None or isna(t.get("created")) or t["created"] >= github_since
            if (sk, side) not in prs_cache:     # uma busca por (Story, lado), não uma por task
                prs_cache[(sk, side)] = _story_prs(prs, story, sk, children_of.get(sk, set()), known_keys, side) if not prs.empty else prs
            my_prs = prs_cache[(sk, side)]
            de = f" de {side}" if side else ""
            if t["is_done"] and verifiable:
                if t["n_commits"] == 0:
                    nota = "" if side else " (task sem lado de código: pode não gerar commit)"
                    rows.append(_alert("done_sem_github", MEDIA if side else BAIXA, since=t.get("resolved"), **common,
                                       detail=f"concluída, mas nenhum commit cita a chave dela{nota}"))
                elif my_prs.empty:
                    rows.append(_alert("done_sem_pr", MEDIA, since=t.get("resolved"), **common,
                                       detail=f"concluída com commits, mas a Story não tem PR{de}"))
            if t["status_group"] == S.ANALISE and (side or t["n_commits"]) and my_prs.empty:
                rows.append(_alert("analise_sem_pr", MEDIA, since=t.get("updated"), **common,
                                   detail=f"em análise (code review), mas a Story não tem PR{de}"))
        if not prs.empty:
            rows += _merged_but_open(items_e, prs, stories, known_keys, now)
        if not hc.empty:
            for _, c in hc[hc["jira_key"].isna()].iterrows():
                title = c["title"] if "title" in c else c["sha"]
                rows.append(_alert("commit_sem_jira_key", MEDIA, "commit", str(c["sha"])[:7], title, _owner(c["author"]),
                                   "a mensagem não cita nenhuma chave do Jira", since=c["date"], url=c.get("url")))
    df = pd.DataFrame(rows, columns=ALERT_COLS)
    if not df.empty:
        ordered = df.assign(_s=df["severity"].map(SEV_ORDER)).sort_values(["_s", "since"], ascending=[False, True], na_position="last")
        df = ordered.drop(columns="_s").reset_index(drop=True)
    return AlertReport(df, notes)


def _merged_but_open(items_e: pd.DataFrame, prs: pd.DataFrame, stories: pd.DataFrame, known: set[str], now: pd.Timestamp) -> list[dict]:
    """PR mergeada na branch padrão + Subtasks do MESMO lado ainda em andamento no Jira (e sem outra PR aberta do lado)."""
    if items_e.empty:
        return []
    story_of: dict[str, str] = dict(zip(items_e["subtask_key"], items_e["story_key"], strict=True))
    story_keys = set(stories["story_key"]) if not stories.empty else set()
    us_map = stories.dropna(subset=["us_id"]).groupby("us_id")["story_key"].apply(list).to_dict() if not stories.empty else {}
    out = []
    merged = prs[(prs["state"] == "merged") & (prs["base_is_default"] if "base_is_default" in prs else True)]
    for _, p in merged.iterrows():
        jk, us = p.get("jira_key"), p.get("us_id")
        sk = jk if jk in story_keys else story_of.get(jk) if not isna(jk) else None
        if sk is None and isna(jk) and not isna(us) and len(us_map.get(us, [])) == 1:
            sk = us_map[us][0]
        if sk is None:
            continue
        kind = p.get("kind") if not isna(p.get("kind")) else None
        mine = items_e[(items_e["story_key"] == sk) & (items_e["status_group"].isin(S.EM_PROGRESSO))]
        if kind:
            mine = mine[mine["side"] == kind]      # PR backend não diz nada sobre subtasks de frontend (nem sobre as sem lado)
        if mine.empty:
            continue
        same_side = (prs["kind"] == kind) if kind and "kind" in prs else pd.Series(True, index=prs.index)
        if not prs[(prs["state"] == "open") & (prs["jira_key"] == sk) & same_side].empty:
            continue                                # há uma PR nova do mesmo lado: o trabalho continua
        keys = ", ".join(mine["subtask_key"])
        out.append(_alert("pr_mergeada_jira_aberto", MEDIA, "story", f"PR #{p['number']}", p["title"], list(mine["assignee"]),
                          f"mergeada em {_fmt_day(p['merged_at'])}; no Jira seguem em andamento: {keys}",
                          since=p["merged_at"], story_key=sk, url=p.get("url")))
    return out


def for_person(alerts: pd.DataFrame, slug: str | None) -> pd.DataFrame:
    """Alertas de uma pessoa (responsável da task / autora da PR ou do commit). `None` = todos. A regra é avaliada no time todo e
    só as LINHAS são filtradas (assim a PR escrita por outra pessoa continua contando como evidência)."""
    if not slug or alerts.empty:
        return alerts
    return alerts[alerts["owners"].map(lambda o: slug in o)]
