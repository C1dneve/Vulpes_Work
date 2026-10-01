"""Extração de dados do Jira: issues, sprints, worklogs e changelog — com paginação REAL.

Fatos da API usados aqui (conferidos na documentação oficial):
- `/rest/api/3/search` foi removido; o substituto `/rest/api/3/search/jql` pagina por `nextPageToken`.
- o campo `worklog` embutido na issue traz no máximo 20 registros; o completo vem de
  `/rest/api/3/issue/{key}/worklog` (startAt/maxResults).
- o `changelog` embutido é truncado; o completo vem de `/rest/api/3/issue/{key}/changelog`.
- `total` pode faltar ou mudar durante a paginação: o paginador não depende dele.

Modelo (por ESTRUTURA, não só por nome de tipo): Epic -> Story -> {Sub-task, Bug, ...}. Toda issue que
não é Epic nem Story é um "item de trabalho"; uma Story sem filhos (e issues sem Story pai) também
viram item, para não sumirem das métricas.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from domain import timeutil
from domain.linking import extract_us_ids
from domain.people import DevMapper
from domain.statuses import classify_status
from services.http import ApiError, AuthError, HttpClient, friendly
from services.results import SourceResult
from settings import Settings

STORY_TYPES = {"story", "história", "historia", "user story"}
EPIC_TYPES = {"epic", "épico", "epico"}
_KEY_OK = re.compile(r"^[A-Z][A-Z0-9_]*-\d+$")

ISSUE_FIELDS = ("summary,status,assignee,issuetype,parent,subtasks,labels,timespent,timeoriginalestimate,"
                "timeestimate,duedate,created,updated,resolutiondate,worklog,sprint,closedSprints,flagged,epic,priority,issuelinks")
SEARCH_FIELDS = [f for f in ISSUE_FIELDS.split(",") if f not in ("sprint", "closedSprints", "flagged", "epic")]

STORY_COLS = ["story_key", "story_summary", "sprint", "sprint_id", "sprint_state", "sprint_start", "sprint_end",
              "us_id", "canonical_id", "kind", "issue_type", "epic_key", "epic_summary",
              # campos da PRÓPRIA Story (status/responsável/prazo/pontos dela, não agregados das Subtasks)
              "status_name", "status_category", "status_group", "assignee", "due_date", "priority", "story_points",
              "estimate_h", "time_spent_h", "created", "updated", "resolved", "flagged"]
ITEM_COLS = ["subtask_key", "subtask_summary", "story_key", "story_summary", "assignee", "assignee_account_id",
             "label", "status_name", "status_category", "status_group", "time_spent_h", "worklog_sum_h",
             "estimate_h", "remaining_h", "due_date", "sprint", "sprint_id", "us_id", "canonical_id",
             "subtask_code", "issue_type", "parent_key", "epic_key", "created", "updated", "resolved",
             "flagged", "standalone", "priority", "story_points", "blocked_by", "flagged_since"]
WORKLOG_COLS = ["subtask_key", "story_key", "author", "author_account_id", "worklog_id", "started", "date", "time_spent_h"]
CHANGELOG_COLS = ["subtask_key", "author", "author_account_id", "history_id", "ts", "date",
                  "from_status", "to_status", "from_group", "to_group", "from_name", "to_name"]
SPRINT_EVENT_COLS = ["subtask_key", "ts", "date", "from_ids", "to_ids", "from_names", "to_names"]
SPRINT_COLS = ["sprint_id", "name", "state", "start", "end", "complete"]


@dataclass
class JiraData:
    stories: pd.DataFrame
    items: pd.DataFrame
    worklogs: pd.DataFrame
    changelog: pd.DataFrame
    sprints: pd.DataFrame
    sprint_events: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=SPRINT_EVENT_COLS))

    @classmethod
    def empty(cls) -> JiraData:
        return cls(*(pd.DataFrame(columns=c) for c in (STORY_COLS, ITEM_COLS, WORKLOG_COLS, CHANGELOG_COLS, SPRINT_COLS,
                                                       SPRINT_EVENT_COLS)))


SP_FIELD_NAMES = ("story points", "story point estimate")
_TIME_FIELDS = {"timeoriginalestimate", "timeestimate", "aggregatetimeoriginalestimate", "timespent"}


def _num(v: Any) -> float | None:
    """Número não-negativo vindo do Jira; qualquer outra coisa (None, texto, bool) é AUSENTE, nunca 0."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v < 0:
        return None
    return float(v)


def _blockers(fields: dict) -> list[str]:
    """Issues que bloqueiam esta (link \"is blocked by\") e AINDA não estão concluídas. Fonte comprovável do bloqueio."""
    out: list[str] = []
    for link in fields.get("issuelinks") or []:
        other = link.get("inwardIssue")
        t = link.get("type") or {}
        if not other or not ((t.get("name") or "").lower() == "blocks" or "blocked by" in (t.get("inward") or "").lower()):
            continue
        of = other.get("fields") or {}
        if ((of.get("status") or {}).get("statusCategory") or {}).get("key") == "done":
            continue
        out.append(f"{other.get('key')} — {of['summary']}" if of.get("summary") else str(other.get("key")))
    return out


@dataclass
class _Run:
    warnings: list[str] = field(default_factory=list)
    worklog_partial: list[str] = field(default_factory=list)
    changelog_partial: list[str] = field(default_factory=list)


class JiraService:
    def __init__(self, http: HttpClient, settings: Settings, mapper: DevMapper,
                 page_size: int = 50, max_pages: int = 400, max_workers: int = 6):
        self.http, self.cfg, self.mapper = http, settings, mapper
        self.base = f"https://{settings.jira.domain}"
        self.page_size, self.max_pages, self.max_workers = page_size, max_pages, max_workers
        self._run = _Run()
        self._sp_field: str | None = None
        self._flag_field: str | None = None
        self._sp_note: str | None = None

    # ------------------------------------------------------------ campos customizados
    def _discover_fields(self) -> None:
        """Descobre o id do campo de Story Points e do `Flagged` (impedimento). Nada é inventado:
        configuração explícita > `/field` (por nome) > desempate pelo campo de estimativa do board.
        Sem campo, Story Points ficam AUSENTES (None) e um aviso é registrado."""
        self._sp_field = self.cfg.jira.story_points_field or None
        self._flag_field = None
        self._sp_note = None
        try:
            catalog = self.http.get_json(f"{self.base}/rest/api/3/field")
        except AuthError:
            raise
        except ApiError as e:
            self._run.warnings.append(f"Campos do Jira indisponíveis ({friendly(e)}): Story Points e Flagged podem faltar")
            return
        catalog = [f for f in catalog if isinstance(f, dict)] if isinstance(catalog, list) else []
        flagged = [f["id"] for f in catalog if f.get("custom") and (f.get("name") or "").strip().lower() == "flagged"]
        self._flag_field = flagged[0] if flagged else None
        if self._sp_field:
            return
        cands = [f["id"] for f in catalog if f.get("custom") and (f.get("name") or "").strip().lower() in SP_FIELD_NAMES]
        if len(cands) > 1:
            cands = self._pick_board_estimation(cands)
        if cands:
            self._sp_field = cands[0]
        else:   # limitação permanente (não é falha transitória): vai para stats, não para warnings (senão o cache encurta)
            self._sp_note = "indisponível (campo 'Story Points' não encontrado no Jira)"

    def _pick_board_estimation(self, cands: list[str]) -> list[str]:
        """Mais de um campo 'Story Points': usa o que o board configurou como estimativa."""
        try:
            cfg = self.http.get_json(f"{self.base}/rest/agile/1.0/board/{self.cfg.jira.board_id}/configuration")
            fid = (((cfg or {}).get("estimation") or {}).get("field") or {}).get("fieldId")
        except AuthError:
            raise
        except ApiError:
            fid = None
        if fid in cands:
            return [fid]
        self._sp_note = f"{cands[0]} (ambíguo entre {', '.join(cands)}; fixe em config.json → jira.story_points_field)"
        return cands

    def _extra_fields(self) -> list[str]:
        return [f for f in (self._sp_field, self._flag_field) if f]

    def _is_flagged(self, fields: dict) -> bool:
        return bool(fields.get("flagged")) or bool(self._flag_field and fields.get(self._flag_field))

    # ------------------------------------------------------------ paginação
    def _paged(self, url: str, params: dict[str, Any], items_key: str, what: str) -> list[dict]:
        """Pagina por `startAt` OU por `nextPageToken` (o que a API devolver), sem depender de `total`."""
        out: list[dict] = []
        seen: set[str] = set()
        start, token = 0, None
        for _ in range(self.max_pages):
            q = dict(params, maxResults=self.page_size)
            q.update({"nextPageToken": token} if token else {"startAt": start})
            data = self.http.get_json(url, q)
            items = data.get(items_key) or []
            new = [i for i in items if str(i.get("id", i.get("key", id(i)))) not in seen]
            seen.update(str(i.get("id", i.get("key", id(i)))) for i in new)
            out += new
            nxt = data.get("nextPageToken")
            if nxt:
                if nxt == token or not new:
                    self._run.warnings.append(f"{what}: paginação por token não avançou; lista pode estar incompleta")
                    break
                token = nxt
                continue
            token = None
            if not items:
                break
            if not new:
                self._run.warnings.append(f"{what}: o servidor repetiu a página (ignorou startAt); lista pode estar incompleta")
                break
            start += len(items)
            if data.get("isLast") is True or (data.get("total") is not None and start >= data["total"]):
                break
        else:
            self._run.warnings.append(f"{what}: atingiu o limite de segurança de {self.max_pages} páginas; lista pode estar incompleta")
        return out

    def _search_keys(self, keys: list[str]) -> list[dict]:
        """Busca issues por chave via `search/jql` (paginação por nextPageToken), em lotes."""
        out: list[dict] = []
        keys = [k for k in dict.fromkeys(keys) if _KEY_OK.match(k)]
        for i in range(0, len(keys), 40):
            body: dict[str, Any] = {"jql": f"key in ({','.join(keys[i:i + 40])})", "fields": SEARCH_FIELDS + self._extra_fields(), "maxResults": 100}
            token = None
            for _ in range(self.max_pages):
                data = self.http.post_json(f"{self.base}/rest/api/3/search/jql", {**body, **({"nextPageToken": token} if token else {})})
                out += data.get("issues") or []
                nxt = data.get("nextPageToken")
                if not nxt or nxt == token:
                    break
                token = nxt
        return out

    # ------------------------------------------------------------ sprints
    def list_sprints(self) -> pd.DataFrame:
        try:
            raw = self._paged(f"{self.base}/rest/agile/1.0/board/{self.cfg.jira.board_id}/sprint", {}, "values", "Sprints")
        except AuthError:
            raise
        except ApiError as e:  # quadro Kanban não tem sprints; não é falha do restante
            self._run.warnings.append(f"Sprints indisponíveis: {friendly(e)}")
            return pd.DataFrame(columns=SPRINT_COLS)
        rows = [{"sprint_id": s.get("id"), "name": s.get("name"), "state": (s.get("state") or "").lower(),
                 "start": timeutil.parse_ts(s.get("startDate")), "end": timeutil.parse_ts(s.get("endDate")),
                 "complete": timeutil.parse_ts(s.get("completeDate"))} for s in raw]
        return pd.DataFrame(rows, columns=SPRINT_COLS)

    # ------------------------------------------------------------ worklog / changelog por issue
    def _worklogs(self, key: str, embedded: dict | None) -> list[dict]:
        wl = embedded or {}
        listed = wl.get("worklogs") or []
        if embedded is not None and wl.get("total", len(listed)) <= len(listed):
            return listed  # o embutido está completo
        return self._paged(f"{self.base}/rest/api/3/issue/{key}/worklog", {}, "worklogs", f"Worklog {key}")

    def _changelog(self, key: str) -> list[dict]:
        return self._paged(f"{self.base}/rest/api/3/issue/{key}/changelog", {}, "values", f"Changelog {key}")

    def _load_issue_details(self, key: str, embedded_wl: dict | None) -> tuple[str, list[dict] | None, list[dict] | None]:
        wl = hist = None
        try:
            wl = self._worklogs(key, embedded_wl)
        except AuthError:
            raise
        except ApiError:
            self._run.worklog_partial.append(key)
        try:
            hist = self._changelog(key)
        except AuthError:
            raise
        except ApiError:
            self._run.changelog_partial.append(key)
        return key, wl, hist

    # ------------------------------------------------------------ montagem
    @staticmethod
    def _sprint_of(fields: dict) -> dict | None:
        sp = fields.get("sprint")
        if isinstance(sp, dict):
            return sp
        closed = [s for s in (fields.get("closedSprints") or []) if isinstance(s, dict)]
        return max(closed, key=lambda s: s.get("endDate") or s.get("completeDate") or "") if closed else None

    def fetch(self) -> SourceResult:
        self._run = _Run()
        try:
            return self._fetch()
        except ApiError as e:
            return SourceResult.failed("Jira", friendly(e))
        except Exception as e:  # payload inesperado nunca derruba o app: vira falha controlada (com log)
            return SourceResult.unexpected("Jira", e, (self.cfg.jira.token,))

    def _fetch(self) -> SourceResult:
        j, link = self.cfg.jira, self.cfg.linking
        sprints = self.list_sprints()
        self._discover_fields()
        fields_param = ",".join([ISSUE_FIELDS, *self._extra_fields()])
        raw = self._paged(f"{self.base}/rest/agile/1.0/board/{j.board_id}/issue", {"fields": fields_param}, "issues", "Issues")
        issues: dict[str, dict] = {i["key"]: i for i in raw}
        if not issues:
            self._run.warnings.append("O board não retornou nenhuma issue (board vazio ou sem permissão de leitura).")

        def itype(i: dict) -> str:
            return ((i["fields"].get("issuetype") or {}).get("name") or "").lower()

        stories = {k: i for k, i in issues.items() if itype(i) in STORY_TYPES}
        missing = [c["key"] for s in stories.values() for c in (s["fields"].get("subtasks") or []) if c["key"] not in issues]
        for extra in self._search_keys(missing):  # filhos que o board não devolveu
            issues.setdefault(extra["key"], extra)
        if missing and not all(k in issues for k in missing):
            gone = [k for k in missing if k not in issues]
            self._run.warnings.append(f"{len(gone)} subtask(s) listadas nas stories não puderam ser carregadas: {', '.join(gone[:5])}")

        children: dict[str, list[str]] = {k: [] for k in stories}
        candidates: dict[str, str] = {}  # item -> container (story_key)
        for k, i in issues.items():
            t = itype(i)
            if t in STORY_TYPES or t in EPIC_TYPES:
                continue
            parent = (i["fields"].get("parent") or {}).get("key")
            container = parent if parent in stories else k
            candidates[k] = container
            if container in children:
                children[container].append(k)
        for s in stories:  # story sem filhos vira o próprio item de trabalho
            if not children[s]:
                candidates[s] = s

        status_cat: dict[str, str] = {}
        for i in issues.values():
            st = i["fields"].get("status") or {}
            status_cat.setdefault((st.get("name") or "").lower(), ((st.get("statusCategory") or {}).get("key") or ""))

        story_rows, item_rows = [], []
        containers = {c for c in candidates.values()}
        for ckey in sorted(containers):
            i = issues[ckey]
            f = i["fields"]
            sp = self._sprint_of(f) or {}
            summary = f.get("summary") or f"Issue ({ckey})"
            us = (extract_us_ids(summary) or [None])[0]
            epic = f.get("epic") or {}
            par = f.get("parent") or {}
            par_is_epic = ((par.get("fields") or {}).get("issuetype") or {}).get("name", "").lower() in EPIC_TYPES
            sst = f.get("status") or {}
            scat = (sst.get("statusCategory") or {}).get("key") or ""
            sassignee = f.get("assignee") or {}
            s_est, s_spent = f.get("timeoriginalestimate"), f.get("timespent")
            story_rows.append({
                "story_key": ckey, "story_summary": summary, "sprint": sp.get("name") or "Sem Sprint",
                "sprint_id": sp.get("id"), "sprint_state": (sp.get("state") or "").lower(),
                "sprint_start": timeutil.parse_ts(sp.get("startDate")), "sprint_end": timeutil.parse_ts(sp.get("endDate")),
                "us_id": us, "canonical_id": ckey if link.use_jira_key_as_canonical else us,
                "kind": "story" if ckey in stories else "standalone", "issue_type": (f.get("issuetype") or {}).get("name"),
                "epic_key": epic.get("key") or (par.get("key") if par_is_epic else None),
                "epic_summary": epic.get("name") or ((par.get("fields") or {}).get("summary") if par_is_epic else None),
                "status_name": sst.get("name") or "", "status_category": scat, "status_group": classify_status(sst.get("name"), scat),
                "assignee": self.mapper.jira(sassignee.get("displayName")) if sassignee else "nenhum",
                "due_date": f.get("duedate"), "priority": (f.get("priority") or {}).get("name"),
                "story_points": _num(f.get(self._sp_field)) if self._sp_field else None,
                "estimate_h": s_est / 3600 if s_est is not None else None,
                "time_spent_h": s_spent / 3600 if s_spent is not None else None,
                "created": timeutil.parse_ts(f.get("created")), "updated": timeutil.parse_ts(f.get("updated")),
                "resolved": timeutil.parse_ts(f.get("resolutiondate")), "flagged": self._is_flagged(f),
            })
        story_df = pd.DataFrame(story_rows, columns=STORY_COLS)
        sinfo = story_df.set_index("story_key").to_dict("index") if not story_df.empty else {}

        # worklog + changelog por item (endpoints próprios, paginados, em paralelo)
        keys = sorted(candidates)
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            details = {k: (wl, hist) for k, wl, hist in
                       pool.map(lambda k: self._load_issue_details(k, issues[k]["fields"].get("worklog")), keys)}

        wl_rows, cl_rows, sp_rows = [], [], []
        subtask_re = re.compile(link.subtask_pattern, re.IGNORECASE)
        for k in keys:
            i, ckey = issues[k], candidates[k]
            f, ci = i["fields"], sinfo[candidates[k]]
            wl, hist = details[k]
            wsum = 0.0
            for w in wl or []:
                h = (w.get("timeSpentSeconds") or 0) / 3600
                wsum += h
                started = timeutil.parse_ts(w.get("started"))
                au = w.get("author") or {}
                wl_rows.append({"subtask_key": k, "story_key": ckey, "author": self.mapper.jira(au.get("displayName")),
                                "author_account_id": au.get("accountId"), "worklog_id": w.get("id"), "started": started,
                                "date": timeutil.local_date(started), "time_spent_h": h})
            flag_events: list[tuple[pd.Timestamp, bool]] = []
            for h in hist or []:
                ts = timeutil.parse_ts(h.get("created"))
                au = h.get("author") or {}
                for it in h.get("items") or []:
                    fld = it.get("field")
                    if fld == "Sprint":   # pertencimento à sprint ao longo do tempo (base do escopo do Burnup)
                        split = lambda v: [x.strip() for x in (v or "").split(",") if x.strip()]  # noqa: E731
                        sp_rows.append({"subtask_key": k, "ts": ts, "date": timeutil.local_date(ts),
                                        "from_ids": split(it.get("from")), "to_ids": split(it.get("to")),
                                        "from_names": split(it.get("fromString")), "to_names": split(it.get("toString"))})
                        continue
                    if fld == "Flagged":
                        flag_events.append((ts, bool(it.get("toString"))))
                        continue
                    if fld != "status":
                        continue
                    fr, to = (it.get("fromString") or ""), (it.get("toString") or "")
                    cl_rows.append({"subtask_key": k, "author": self.mapper.jira(au.get("displayName")),
                                    "author_account_id": au.get("accountId"), "history_id": h.get("id"), "ts": ts,
                                    "date": timeutil.local_date(ts), "from_status": fr.lower(), "to_status": to.lower(),
                                    "from_group": classify_status(fr, status_cat.get(fr.lower())),
                                    "to_group": classify_status(to, status_cat.get(to.lower())),
                                    "from_name": fr, "to_name": to})
            st = f.get("status") or {}
            cat = (st.get("statusCategory") or {}).get("key") or ""
            summary = f.get("summary") or f"Issue ({k})"
            mc = subtask_re.search(summary)
            code = f"{mc.group(1).upper()}-{int(mc.group(2)):02d}" if mc and mc.lastindex and mc.lastindex >= 2 else None
            assignee = f.get("assignee") or {}
            labels = f.get("labels") or []
            spent, est, rem = f.get("timespent"), f.get("timeoriginalestimate"), f.get("timeestimate")
            us = ci["us_id"]  # o ID visual é sempre o do container (story ou item standalone)
            # Sprint: a PRÓPRIA do item (atual ou última fechada) > a da Story > "Sem Sprint". Nunca sobrescreve a do item.
            flagged_now = self._is_flagged(f)
            sets = [t for t, on in sorted(flag_events, key=lambda e: e[0]) if on]
            last_event_on = bool(flag_events) and sorted(flag_events, key=lambda e: e[0])[-1][1]
            flagged_since = sets[-1] if flagged_now and sets and last_event_on else pd.NaT
            own_sp = self._sprint_of(f) if ckey != k else None
            sprint_name = own_sp.get("name") if own_sp and own_sp.get("name") else ci["sprint"]
            sprint_id = own_sp.get("id") if own_sp and own_sp.get("name") else ci["sprint_id"]
            item_rows.append({
                "subtask_key": k, "subtask_summary": summary, "story_key": ckey, "story_summary": ci["story_summary"],
                "assignee": self.mapper.jira(assignee.get("displayName")) if assignee else "nenhum",
                "assignee_account_id": assignee.get("accountId"), "label": labels[0] if labels else "Sem Tag",
                "status_name": st.get("name") or "", "status_category": cat,
                "status_group": classify_status(st.get("name"), cat), "time_spent_h": (spent or 0) / 3600,
                "worklog_sum_h": wsum, "estimate_h": est / 3600 if est is not None else None,
                "remaining_h": rem / 3600 if rem is not None else None, "due_date": f.get("duedate"),
                "sprint": sprint_name, "sprint_id": sprint_id, "us_id": us,
                "canonical_id": ci["canonical_id"],
                "subtask_code": code, "issue_type": (f.get("issuetype") or {}).get("name"),
                "parent_key": (f.get("parent") or {}).get("key"), "epic_key": ci["epic_key"],
                "created": timeutil.parse_ts(f.get("created")), "updated": timeutil.parse_ts(f.get("updated")),
                "resolved": timeutil.parse_ts(f.get("resolutiondate")), "flagged": flagged_now,
                "standalone": ckey == k, "priority": (f.get("priority") or {}).get("name"),
                "story_points": _num(f.get(self._sp_field)) if self._sp_field else None,
                "blocked_by": _blockers(f), "flagged_since": flagged_since,
            })

        data = JiraData(story_df, pd.DataFrame(item_rows, columns=ITEM_COLS).drop_duplicates("subtask_key"),
                        pd.DataFrame(wl_rows, columns=WORKLOG_COLS), pd.DataFrame(cl_rows, columns=CHANGELOG_COLS), sprints,
                        pd.DataFrame(sp_rows, columns=SPRINT_EVENT_COLS))
        run = self._run
        if keys and len(run.changelog_partial) == len(keys):
            return SourceResult.failed("Jira", "Changelog: nenhuma issue teve o histórico carregado (verifique permissões).")
        warnings = list(dict.fromkeys(run.warnings))
        if run.worklog_partial:
            warnings.append(f"Worklogs: {len(run.worklog_partial)} issue(s) sem worklog completo ({', '.join(sorted(run.worklog_partial)[:5])})")
        if run.changelog_partial:
            warnings.append(f"Changelog: {len(run.changelog_partial)} issue(s) parcialmente carregadas ({', '.join(sorted(run.changelog_partial)[:5])})")
        stats = {"issues": len(issues), "stories": int((story_df["kind"] == "story").sum()) if not story_df.empty else 0,
                 "items": len(data.items), "worklogs": len(data.worklogs), "changelog": len(data.changelog),
                 "sprints": len(sprints), "worklog_partial": sorted(run.worklog_partial),
                 "changelog_partial": sorted(run.changelog_partial), "story_points_field": self._sp_note or self._sp_field or "indisponível",
                 "api_calls": self.http.calls}
        return SourceResult("Jira", data, warnings=warnings, stats=stats)
