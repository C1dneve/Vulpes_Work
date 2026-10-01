#!/usr/bin/env python3
"""FERRAMENTA DE DIAGNÓSTICO — validação REAL (100% read-only) das APIs Jira e GitHub do Moonfoxes.

Não altera o projeto. Só emite GET/HEAD (exceção opt-in: --allow-jql-post, ver abaixo).
Credenciais: as MESMAS do Moonfoxes (.env / ambiente): EMAIL, TOKEN, JIRA_DOMAIN, BOARD_ID, JIRA_PROJECT,
GITHUB_TOKEN. Nenhum segredo é impresso nem gravado (toda saída passa por um redator).

Uso (na raiz do projeto, no Windows/PowerShell ou bash):
    python tools/validate_real_apis.py
    python tools/validate_real_apis.py --only t5,t6,t7            # só GitHub
    python tools/validate_real_apis.py --skip-run                 # sem a atualização completa (teste 8)
    python tools/validate_real_apis.py --branch feature/backend/JH-123-US2.1-cadastro --pr 42 --issue JH-10

Parâmetros NÃO secretos: --jira-domain --board-id --org --repo --branch --issue --pr --since-hours ...

Sobre POST: o JiraService do Moonfoxes usa POST /rest/api/3/search/jql (consulta JQL, semanticamente leitura)
para buscar subtasks que o board não devolveu. Por regra, POST é BLOQUEADO. Se o teste 8 precisar dele, ele
aborta e diz isso; reexecute com --allow-jql-post para liberar SOMENTE esse endpoint (não altera nada no Jira).

Testes:  t1 paginação Jira | t2 epic/closedSprints | t3 worklog | t4 changelog
         t5 compare com '/' | t6 semântica de `since` | t7 PR merged/rebase | t8 contagem de chamadas
         t9 campos do MVP no Jira (Story Points, Flagged, links de bloqueio, due date, Sprint no histórico)
         t10 reviews de PR no GitHub (requested_reviewers, /pulls/{n}/reviews)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
import threading
import time
import traceback
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

import requests
from requests.auth import HTTPBasicAuth

GH_API = "https://api.github.com"
GH_VERSION = "2022-11-28"
OK, PART, UNK, DIV = "✅", "⚠️", "❓", "❌"
LABEL = {OK: "Confirmado na API real", PART: "Confirmado parcialmente", UNK: "Não foi possível confirmar",
         DIV: "Divergência real encontrada"}
SUMMARY_MIN_GAP_S = 60  # diferença mínima author/committer para servir de prova no teste `since`


# ============================================================================ segurança / saída
class Redactor:
    """Remove segredos de QUALQUER texto que sai do script (terminal e arquivos)."""

    def __init__(self) -> None:
        self.secrets: list[str] = []

    def add(self, *values: str | None) -> None:
        for v in values:
            if v and len(v) >= 6 and v not in self.secrets:
                self.secrets.append(v)

    def __call__(self, text: str) -> str:
        for s in sorted(self.secrets, key=len, reverse=True):
            text = text.replace(s, "***")
        text = re.sub(r"(gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|ATATT[A-Za-z0-9_=\-]{16,})", "***", text)
        text = re.sub(r"(?i)(access_token|token|password|secret)=[^&\s]+", r"\1=***", text)
        text = re.sub(r"(?i)(authorization\s*[:=]\s*)(bearer|basic)\s+\S+", r"\1\2 ***", text)
        return text


REDACT = Redactor()
LOG: list[str] = []


def say(*parts: object, indent: int = 0) -> None:
    line = REDACT(" ".join(str(p) for p in parts))
    line = "\n".join((" " * indent + ln) if ln else ln for ln in line.split("\n"))
    print(line)
    LOG.append(line)


def shape(v: object) -> str:
    """Tipo/estrutura (nunca valores): dict{chaves}, list[n] de ..., tipo escalar."""
    if v is None:
        return "null"
    if isinstance(v, dict):
        ks = sorted(v)
        return "dict{" + ",".join(ks[:14]) + ("…" if len(ks) > 14 else "") + "}"
    if isinstance(v, list):
        return "list(vazia)" if not v else f"list[{len(v)}] de {shape(v[0])}"
    return type(v).__name__


# ============================================================================ HTTP read-only + instrumentação
class ReadOnlyViolation(Exception):
    pass


class RequestCapExceeded(Exception):
    pass


class Ledger:
    """Registro thread-safe de cada requisição enviada."""

    def __init__(self, cap: int | None = None) -> None:
        self.rows: list[dict] = []
        self.blocked: list[str] = []
        self.cap = cap
        self.lock = threading.Lock()

    def check_cap(self) -> None:
        with self.lock:
            if self.cap is not None and len(self.rows) >= self.cap:
                raise RequestCapExceeded(f"teto de segurança de {self.cap} requisições atingido")

    def add(self, row: dict) -> None:
        with self.lock:
            self.rows.append(row)


_NORM = (
    (r"^/repos/[^/]+/[^/]+", "/repos/{org}/{repo}"),
    (r"/rest/agile/1\.0/board/\d+", "/rest/agile/1.0/board/{board}"),
    (r"/rest/api/3/issue/[A-Za-z][A-Za-z0-9_]*-\d+", "/rest/api/3/issue/{key}"),
    (r"/pulls/\d+", "/pulls/{n}"),
    (r"/compare/.+$", "/compare/{basehead}"),
    (r"/commits/[0-9a-fA-F]{40}", "/commits/{sha}"),
)


def norm_path(path: str) -> str:
    for pat, rep in _NORM:
        path = re.sub(pat, rep, path)
    return path


class GuardedSession(requests.Session):
    """Sessão que RECUSA qualquer método que não seja GET/HEAD e registra tudo que envia."""

    ledger: Ledger
    allow_jql_post: bool = False

    def request(self, method, url, **kw):  # type: ignore[override]
        m = str(method).upper()
        path = urlsplit(str(url)).path
        allowed = m in ("GET", "HEAD") or (m == "POST" and self.allow_jql_post and path == "/rest/api/3/search/jql")
        if not allowed:
            self.ledger.blocked.append(f"{m} {norm_path(path)}")
            raise ReadOnlyViolation(f"{m} {norm_path(path)} bloqueado pelo guard read-only")
        self.ledger.check_cap()
        host = urlsplit(str(url)).netloc.lower()
        source = "GitHub" if host == "api.github.com" else "Jira"
        t0 = time.perf_counter()
        try:
            resp = super().request(method, url, **kw)
        except Exception as e:
            self.ledger.add({"source": source, "method": m, "endpoint": norm_path(path), "status": type(e).__name__,
                             "secs": time.perf_counter() - t0, "remaining": None})
            raise
        rem = resp.headers.get("X-RateLimit-Remaining")
        self.ledger.add({"source": source, "method": m, "endpoint": norm_path(path), "status": resp.status_code,
                         "secs": time.perf_counter() - t0, "remaining": int(rem) if rem and rem.isdigit() else None})
        return resp


def session_factory(ledger: Ledger, allow_jql_post: bool):
    def factory() -> GuardedSession:
        s = GuardedSession()
        s.ledger, s.allow_jql_post = ledger, allow_jql_post
        return s
    return factory


class Resp:
    def __init__(self, status: int, data: object, headers: dict, url: str, secs: float, error: str | None = None):
        self.status, self.data, self.headers, self.url, self.secs, self.error = status, data, headers, url, secs, error

    @property
    def ok(self) -> bool:
        return self.status == 200 and self.error is None


class Api:
    """GET simples para os testes de diagnóstico (sem retry; falhas viram Resp com status/erro)."""

    def __init__(self, session: GuardedSession) -> None:
        self.s = session

    def get(self, url: str, params: dict | None = None) -> Resp:
        t0 = time.perf_counter()
        try:
            r = self.s.get(url, params=params, timeout=(5, 30))
        except ReadOnlyViolation:
            raise
        except requests.RequestException as e:
            return Resp(0, None, {}, url, time.perf_counter() - t0, type(e).__name__)
        try:
            data = r.json()
        except ValueError:
            data = None
        return Resp(r.status_code, data, dict(r.headers), r.request.url or url, time.perf_counter() - t0)

    def paginate(self, url: str, params: dict | None = None, per_page: int = 100, max_pages: int = 5) -> list[dict]:
        out: list[dict] = []
        for page in range(1, max_pages + 1):
            r = self.get(url, {**(params or {}), "per_page": per_page, "page": page})
            if not r.ok or not isinstance(r.data, list):
                break
            out += r.data
            if len(r.data) < per_page:
                break
        return out


def pdt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def verdict(status: str, evidence: str, **extra: object) -> dict:
    return {"status": status, "evidence": evidence, **extra}


# ============================================================================ JIRA
def jira_preflight(J: Api, base: str) -> dict:
    r = J.get(f"{base}/rest/api/3/serverInfo")
    info: dict = {"http": r.status, "error": r.error}
    deny = r.headers.get("x-deny-reason")
    if deny:
        info["blocked"] = f"egress bloqueado pelo ambiente de execução (x-deny-reason: {deny})"
    elif r.status == 401:
        info["blocked"] = "HTTP 401 — credencial Jira inválida/expirada"
    elif r.error:
        info["blocked"] = f"sem conexão ({r.error})"
    elif r.ok and isinstance(r.data, dict):
        info["deployment"], info["version"] = r.data.get("deploymentType"), r.data.get("version")
    elif r.status != 200:
        info["blocked"] = f"HTTP {r.status}"
    me = J.get(f"{base}/rest/api/3/myself") if not info.get("blocked") else None
    info["auth"] = "autenticado" if me is not None and me.ok else "não autenticado / não verificado"
    return info


def sample_board(J: Api, base: str, board: str, fields: str, limit: int) -> tuple[list[dict], dict]:
    url, out, start, meta = f"{base}/rest/agile/1.0/board/{board}/issue", [], 0, {}
    for _ in range(40):
        r = J.get(url, {"fields": fields, "maxResults": 50, "startAt": start})
        if not r.ok or not isinstance(r.data, dict):
            meta["error"] = f"HTTP {r.status} {r.error or ''}".strip()
            break
        items = r.data.get("issues") or []
        meta.update({"total": r.data.get("total"), "isLast": r.data.get("isLast")})
        out += items
        if not items or len(out) >= limit or (r.data.get("total") is not None and start + len(items) >= r.data["total"]):
            break
        start += len(items)
    return out[:limit], meta


def t1_pagination(J: Api, base: str, board: str, issue_fields: str) -> dict:
    url = f"{base}/rest/agile/1.0/board/{board}/issue"
    say("JIRA — PAGINAÇÃO")
    say("Endpoint: GET /rest/agile/1.0/board/{board}/issue  (o mesmo de services/jira.py::_fetch)", indent=1)
    p1 = J.get(url, {"fields": issue_fields, "maxResults": 2, "startAt": 0})
    if not p1.ok or not isinstance(p1.data, dict):
        say(f"Status: HTTP {p1.status} {p1.error or ''}", indent=1)
        return verdict(UNK, f"primeira página falhou (HTTP {p1.status} {p1.error or ''})".strip())
    say("Status: autenticado, HTTP 200", indent=1)
    d1 = p1.data
    keys1 = [i.get("key") for i in d1.get("issues") or []]
    has_token = bool(d1.get("nextPageToken"))
    meta1 = {k: d1.get(k) for k in ("startAt", "maxResults", "total", "isLast")}
    say(f"Chaves de topo da resposta: {sorted(d1)}", indent=1)
    say(f"Primeira página (maxResults=2): {len(keys1)} itens {keys1} | {meta1} | nextPageToken presente: {has_token}", indent=1)
    if has_token:
        mech, params2 = "nextPageToken", {"nextPageToken": d1["nextPageToken"]}
    else:
        mech, params2 = "startAt", {"startAt": len(keys1)}
    p2 = J.get(url, {"fields": issue_fields, "maxResults": 2, **params2})
    if not p2.ok or not isinstance(p2.data, dict):
        say(f"Segunda página: HTTP {p2.status} {p2.error or ''}", indent=1)
        return verdict(UNK, f"segunda página falhou (HTTP {p2.status})")
    d2 = p2.data
    keys2 = [i.get("key") for i in d2.get("issues") or []]
    meta2 = {k: d2.get(k) for k in ("startAt", "maxResults", "total", "isLast")}
    say(f"Segunda página (mecanismo usado: {mech}): {len(keys2)} itens {keys2} | {meta2} | "
        f"nextPageToken presente: {bool(d2.get('nextPageToken'))}", indent=1)
    cap = J.get(url, {"fields": "summary", "maxResults": 100, "startAt": 0})
    cap_info = ({"maxResults_ecoado": cap.data.get("maxResults"), "retornados": len(cap.data.get("issues") or [])}
                if cap.ok and isinstance(cap.data, dict) else {"erro": cap.status})
    say(f"Sonda de teto (pediu maxResults=100): {cap_info}", indent=1)
    total = d1.get("total")
    detail = {"mecanismo": mech, "pagina1": keys1, "pagina2": keys2, "meta1": meta1, "meta2": meta2, "teto": cap_info,
              "chaves_topo": sorted(d1)}
    if keys2 and set(keys2) & set(keys1):
        say("Conclusão: ❌ o servidor repetiu itens na 2ª página (parâmetro de paginação ignorado?)", indent=1)
        return verdict(DIV, f"2ª página repetiu itens de 1ª usando {mech}", **detail)
    if keys2:
        note = "o código aceita ambos os mecanismos (startAt e nextPageToken) — compatível"
        say(f"Conclusão: ✅ paginação confirmada por {mech}; páginas disjuntas; {note}", indent=1)
        return verdict(OK, f"{mech}: pág.1={len(keys1)} itens, pág.2={len(keys2)} itens disjuntos; total={total}", **detail)
    say("Conclusão: ⚠️ board tem ≤2 issues (ou API não entregou 2ª página); não dá para provar a paginação", indent=1)
    return verdict(PART, f"mecanismo visível ({mech}, chaves {sorted(d1)}) mas 2ª página vazia (total={total})", **detail)


def _cov(sample: list[dict], field: str) -> dict:
    c: Counter = Counter()
    for i in sample:
        f = i.get("fields") or {}
        if field not in f:
            c["ausente"] += 1
        else:
            v = f[field]
            c["null" if v is None else "vazio" if v in ([], {}, "") else "preenchido"] += 1
    return dict(c)


def t2_fields(J: Api, base: str, board: str, sample: list[dict], epic_types: set[str]) -> dict:
    say("JIRA — CAMPOS epic / closedSprints / sprint / issuetype / status / flagged")
    if not sample:
        say("Sem issues do board para inspecionar.", indent=1)
        return verdict(UNK, "board não devolveu issues (ou não acessível)")
    say(f"Amostra: {len(sample)} issues do board (mesmos `fields` do projeto)", indent=1)
    targets = ("epic", "closedSprints", "sprint", "issuetype", "status", "flagged")
    detail: dict = {"amostra": len(sample), "cobertura": {}, "estrutura": {}}
    first = sample[0]
    say(f"Exemplo {first.get('key')}:", indent=1)
    for t in targets:
        say(f"{t}: {shape((first.get('fields') or {}).get(t)) if t in (first.get('fields') or {}) else 'AUSENTE'}", indent=2)
    say("Cobertura na amostra (ausente / null / vazio / preenchido):", indent=1)
    for t in targets:
        cov = _cov(sample, t)
        detail["cobertura"][t] = cov
        ex = next((i for i in sample if (i.get("fields") or {}).get(t) not in (None, [], {}, "")), None)
        shp = shape(ex["fields"][t]) if ex else "n/d"
        detail["estrutura"][t] = shp
        say(f"{t}: {cov} | estrutura de um preenchido: {shp}", indent=2)
    types = Counter(((i["fields"].get("issuetype") or {}).get("name") or "?") for i in sample)
    sp_states = Counter(((i["fields"].get("sprint") or {}).get("state") or "sem sprint") for i in sample)
    say(f"Tipos de issue na amostra: {dict(types)}", indent=1)
    say(f"Estado de `sprint` na amostra: {dict(sp_states)}", indent=1)
    detail["tipos"], detail["sprint_estados"] = dict(types), dict(sp_states)

    # closedSprints: issue real com histórico de sprint encerrada
    with_closed = [i for i in sample if isinstance(i["fields"].get("closedSprints"), list) and i["fields"]["closedSprints"]]
    needed = ("id", "name", "state", "startDate", "endDate", "completeDate")
    closed_ok = False
    if with_closed:
        ex = with_closed[0]
        el = ex["fields"]["closedSprints"][0]
        present = {k: (k in el) for k in needed} if isinstance(el, dict) else {}
        closed_ok = isinstance(el, dict) and all(present.get(k) for k in ("id", "name", "state")) and (
            present.get("endDate") or present.get("completeDate"))
        say(f"Issue com closedSprints preenchido: {ex['key']} ({len(with_closed)} de {len(sample)} na amostra)", indent=1)
        say(f"closedSprints[0]: {shape(el)} | chaves que o código usa: {present}", indent=2)
        detail["closed_exemplo"] = {"issue": ex["key"], "presente": present, "n_issues": len(with_closed)}
    else:
        say("Nenhuma issue da amostra tem closedSprints preenchido.", indent=1)
    cs = J.get(f"{base}/rest/agile/1.0/board/{board}/sprint", {"state": "closed", "maxResults": 50})
    n_closed = len(cs.data.get("values") or []) if cs.ok and isinstance(cs.data, dict) else None
    say(f"Sprints encerradas no board (GET .../sprint?state=closed): {n_closed}", indent=1)
    detail["sprints_encerradas_no_board"] = n_closed

    # epic: o código usa fields.epic.{key,name} OU parent (se o pai for Epic)
    def epic_paths(i: dict) -> tuple[bool, bool]:
        f = i["fields"]
        ep = f.get("epic") if isinstance(f.get("epic"), dict) else {}
        par = f.get("parent") or {}
        par_is_epic = ((par.get("fields") or {}).get("issuetype") or {}).get("name", "").lower() in epic_types
        return bool(ep.get("key")), bool(par_is_epic and par.get("key"))
    non_epics = [i for i in sample if ((i["fields"].get("issuetype") or {}).get("name") or "").lower() not in epic_types]
    via_epic = sum(epic_paths(i)[0] for i in non_epics)
    via_parent = sum(epic_paths(i)[1] for i in non_epics)
    ex_epic = next((i["fields"]["epic"] for i in sample if isinstance(i["fields"].get("epic"), dict) and i["fields"]["epic"]), None)
    say(f"Epic para {len(non_epics)} issues não-Epic: via fields.epic.key = {via_epic}; via parent(Epic) = {via_parent}", indent=1)
    if ex_epic:
        say(f"fields.epic (exemplo): {shape(ex_epic)}  → código lê `key` e `name`", indent=2)
    detail["epic"] = {"via_epic": via_epic, "via_parent": via_parent, "de": len(non_epics),
                      "estrutura": shape(ex_epic) if ex_epic else None}
    flagged_cov = detail["cobertura"]["flagged"]
    if flagged_cov.get("ausente") == len(sample):
        say("Observação: `flagged` NÃO é devolvido em nenhuma issue (no Jira Cloud é um campo custom).", indent=1)
    types_bad = [t for t in ("closedSprints",) if any(t in i["fields"] and not (i["fields"][t] is None or isinstance(i["fields"][t], list))
                                                       for i in sample)]
    epic_works = (via_epic + via_parent) > 0
    if types_bad:
        return verdict(DIV, "closedSprints presente com tipo diferente de lista", **detail)
    if closed_ok and epic_works:
        return verdict(OK, f"closedSprints real com chaves esperadas ({len(with_closed)} issues); epic resolvido em "
                           f"{via_epic + via_parent}/{len(non_epics)} (epic={via_epic}, parent={via_parent})", **detail)
    why = []
    if not closed_ok:
        why.append("nenhuma issue com closedSprints preenchido na amostra" if not with_closed else "closedSprints sem as chaves esperadas")
    if not epic_works:
        why.append("epic não resolvido por fields.epic nem por parent")
    return verdict(PART if (closed_ok or epic_works) else UNK, "; ".join(why) or "parcial", **detail)


def _pick_issues(sample: list[dict], prefer) -> list[str]:
    ordered = sorted(sample, key=lambda i: (0 if prefer(i) else 1))
    return [i["key"] for i in ordered]


def t3_worklog(J: Api, base: str, sample: list[dict], forced: str | None) -> dict:
    say("JIRA — WORKLOG (paginação por issue)")
    say("Endpoint: GET /rest/api/3/issue/{key}/worklog", indent=1)
    by_key = {i["key"]: i for i in sample}
    prefer = lambda i: ((i["fields"].get("worklog") or {}).get("total") or 0) >= 2 or (i["fields"].get("timespent") or 0) > 0  # noqa: E731
    cands = [forced] if forced else _pick_issues(sample, prefer)[:25]
    seen_one = None
    for key in cands:
        p1 = J.get(f"{base}/rest/api/3/issue/{key}/worklog", {"maxResults": 1, "startAt": 0})
        if not p1.ok or not isinstance(p1.data, dict):
            continue
        total = p1.data.get("total")
        if not total:
            continue
        w1 = p1.data.get("worklogs") or []
        row1 = {"issue": key, "total": total, "startAt": p1.data.get("startAt"), "maxResults": p1.data.get("maxResults"),
                "retornados": len(w1), "chaves": sorted(p1.data)}
        emb = ((by_key.get(key) or {}).get("fields") or {}).get("worklog")
        say(f"{key}: página 1 → {row1}", indent=1)
        if emb:
            say(f"embutido na issue: total={emb.get('total')}, entregues={len(emb.get('worklogs') or [])}, "
                f"maxResults={emb.get('maxResults')}", indent=2)
        if total < 2:
            seen_one = seen_one or row1
            continue
        p2 = J.get(f"{base}/rest/api/3/issue/{key}/worklog", {"maxResults": 1, "startAt": 1})
        w2 = (p2.data or {}).get("worklogs") or [] if p2.ok and isinstance(p2.data, dict) else []
        row2 = {"issue": key, "total": (p2.data or {}).get("total") if p2.ok else None,
                "startAt": (p2.data or {}).get("startAt") if p2.ok else None,
                "maxResults": (p2.data or {}).get("maxResults") if p2.ok else None, "retornados": len(w2)}
        say(f"{key}: página 2 → {row2}", indent=1)
        distinct = bool(w1 and w2 and w1[0].get("id") != w2[0].get("id"))
        if distinct:
            say("Conclusão: ✅ startAt/maxResults do worklog funcionam (2ª página traz outro registro)", indent=1)
            return verdict(OK, f"{key}: total={total}; pág.1 e pág.2 (maxResults=1) com ids distintos", pagina1=row1, pagina2=row2)
        say("Conclusão: ❌ 2ª página não trouxe registro distinto", indent=1)
        return verdict(DIV, f"{key}: total={total} mas startAt=1 não avançou", pagina1=row1, pagina2=row2)
    if seen_one:
        say("Conclusão: ⚠️ só há issues com 1 worklog; paginação de 2ª página não pôde ser provada", indent=1)
        return verdict(PART, "estrutura confirmada (total/startAt/maxResults) mas nenhuma issue com ≥2 worklogs", pagina1=seen_one)
    say("Nenhuma issue com worklog encontrada na amostra. Não inventei dados.", indent=1)
    return verdict(UNK, "nenhuma issue com worklog na amostra")


def t4_changelog(J: Api, base: str, sample: list[dict], forced: str | None) -> dict:
    say("JIRA — CHANGELOG (paginação por issue)")
    say("Endpoint: GET /rest/api/3/issue/{key}/changelog", indent=1)
    prefer = lambda i: ((i["fields"].get("status") or {}).get("statusCategory") or {}).get("key") in ("indeterminate", "done")  # noqa: E731
    cands = [forced] if forced else _pick_issues(sample, prefer)[:25]
    seen_one = None
    for key in cands:
        p1 = J.get(f"{base}/rest/api/3/issue/{key}/changelog", {"maxResults": 1, "startAt": 0})
        if not p1.ok or not isinstance(p1.data, dict):
            continue
        total, v1 = p1.data.get("total"), p1.data.get("values") or []
        if not total:
            continue
        item_keys = sorted((v1[0].get("items") or [{}])[0]) if v1 else []
        row1 = {"issue": key, "total": total, "startAt": p1.data.get("startAt"), "maxResults": p1.data.get("maxResults"),
                "isLast": p1.data.get("isLast"), "retornados": len(v1), "chaves": sorted(p1.data), "chaves_item": item_keys}
        say(f"{key}: página 1 → {row1}", indent=1)
        if total < 2:
            seen_one = seen_one or row1
            continue
        p2 = J.get(f"{base}/rest/api/3/issue/{key}/changelog", {"maxResults": 1, "startAt": 1})
        v2 = (p2.data or {}).get("values") or [] if p2.ok and isinstance(p2.data, dict) else []
        row2 = {"issue": key, "total": (p2.data or {}).get("total") if p2.ok else None,
                "startAt": (p2.data or {}).get("startAt") if p2.ok else None,
                "maxResults": (p2.data or {}).get("maxResults") if p2.ok else None, "retornados": len(v2)}
        say(f"{key}: página 2 → {row2}", indent=1)
        if v1 and v2 and v1[0].get("id") != v2[0].get("id"):
            say("Conclusão: ✅ paginação do changelog confirmada", indent=1)
            return verdict(OK, f"{key}: total={total}; pág.1/pág.2 (maxResults=1) com ids distintos", pagina1=row1, pagina2=row2)
        say("Conclusão: ❌ 2ª página não trouxe registro distinto", indent=1)
        return verdict(DIV, f"{key}: total={total} mas startAt=1 não avançou", pagina1=row1, pagina2=row2)
    if seen_one:
        return verdict(PART, "estrutura confirmada mas nenhuma issue com ≥2 entradas de histórico", pagina1=seen_one)
    say("Nenhuma issue com histórico encontrada na amostra.", indent=1)
    return verdict(UNK, "nenhuma issue com changelog na amostra")


def t9_mvp_jira(J: Api, base: str, board: str, issue_fields: str) -> dict:
    """Campos de que o MVP depende. Só GET. Registra o que existe, o que está vazio e o que NÃO existe (nada é inventado)."""
    say("JIRA — CAMPOS DO MVP (Story Points, Flagged, links de bloqueio, due date, prioridade, Sprint no histórico)")
    r = J.get(f"{base}/rest/api/3/field")
    catalog = [f for f in (r.data if r.ok and isinstance(r.data, list) else []) if isinstance(f, dict)]
    if not catalog:
        return verdict(UNK, f"GET /rest/api/3/field indisponível (HTTP {r.status} {r.error or ''})".strip())
    names = ("story points", "story point estimate")
    sp = [f for f in catalog if f.get("custom") and (f.get("name") or "").strip().lower() in names]
    flag = [f for f in catalog if f.get("custom") and (f.get("name") or "").strip().lower() == "flagged"]
    say(f"Campos de Story Points no catálogo: {[(f['id'], f['name']) for f in sp] or 'NENHUM'}", indent=1)
    say(f"Campo Flagged (impedimento): {[(f['id'], f['name']) for f in flag] or 'NENHUM'}", indent=1)
    cfg = J.get(f"{base}/rest/agile/1.0/board/{board}/configuration")
    est = (((cfg.data or {}).get("estimation") or {}).get("field") or {}) if cfg.ok and isinstance(cfg.data, dict) else {}
    say(f"Estimativa configurada no board: {est.get('fieldId') or 'não informada'} ({est.get('displayName') or '—'})", indent=1)
    ids = [f["id"] for f in sp + flag]
    sample, _ = sample_board(J, base, board, ",".join([issue_fields, *ids]), 100)
    is_sub = lambda i: bool(((i.get("fields") or {}).get("issuetype") or {}).get("subtask"))  # noqa: E731
    parents, subs = [i for i in sample if not is_sub(i)], [i for i in sample if is_sub(i)]

    def numeric(group: list[dict], fid: str) -> int:
        return sum(1 for i in group if isinstance((i.get("fields") or {}).get(fid), (int, float)) and not isinstance((i.get("fields") or {}).get(fid), bool))
    sp_cov = {f["id"]: {"stories": f"{numeric(parents, f['id'])}/{len(parents)}", "subtasks": f"{numeric(subs, f['id'])}/{len(subs)}"} for f in sp}
    say(f"Story Points numéricos por campo (preenchidos/total na amostra de {len(sample)}): {sp_cov or 'n/a'}", indent=1)
    cover = {"duedate": _cov(sample, "duedate"), "priority": _cov(sample, "priority"), "issuelinks": _cov(sample, "issuelinks"),
             "flagged (boolean do agile)": _cov(sample, "flagged")}
    for k, v in cover.items():
        say(f"{k}: {v}", indent=1)
    blocks = sum(1 for i in sample for ln in ((i.get("fields") or {}).get("issuelinks") or [])
                 if ln.get("inwardIssue") and ((ln.get("type") or {}).get("name", "").lower() == "blocks" or "blocked by" in (ln.get("type") or {}).get("inward", "").lower()))
    say(f"Links 'is blocked by' (issue bloqueadora no lado inward): {blocks}", indent=1)
    status = Counter(((i.get("fields") or {}).get("status") or {}).get("name") for i in sample)
    say(f"Status reais do board (nome → qtd): {dict(status)}", indent=1)
    fields_seen: Counter = Counter()
    sprint_item: dict = {}
    for i in sample[:12]:
        c = J.get(f"{base}/rest/api/3/issue/{i['key']}/changelog", {"maxResults": 100, "startAt": 0})
        for h in (c.data or {}).get("values") or [] if c.ok and isinstance(c.data, dict) else []:
            for it in h.get("items") or []:
                fields_seen[it.get("field")] += 1
                if it.get("field") == "Sprint" and not sprint_item:
                    sprint_item = {k: it.get(k) for k in ("from", "to", "fromString", "toString")}
    say(f"Campos que aparecem no changelog (12 issues): {dict(fields_seen)}", indent=1)
    say(f"Exemplo de evento 'Sprint' (ids/nomes): {sprint_item or 'nenhum encontrado'}", indent=1)
    ev = {"story_points": sp_cov, "flagged_fields": [f["id"] for f in flag], "board_estimation": est.get("fieldId"),
          "cobertura": cover, "links_bloqueio": blocks, "changelog_fields": dict(fields_seen), "evento_sprint": sprint_item}
    if not sp:
        say("Conclusão: ❌ não há campo de Story Points no catálogo: o MVP exibe 'indisponível' (comportamento previsto).", indent=1)
        return verdict(DIV, "campo de Story Points ausente no catálogo do Jira", **ev)
    filled = any(numeric(parents, f["id"]) or numeric(subs, f["id"]) for f in sp)
    if not filled:
        return verdict(PART, "campo de Story Points existe mas sem valores numéricos na amostra", **ev)
    note = f"; {len(sp)} candidatos (desempate pelo board: {est.get('fieldId')})" if len(sp) > 1 else ""
    return verdict(OK, f"Story Points numéricos encontrados em {[k for k, v in sp_cov.items() if not v['stories'].startswith('0/')]}{note}", **ev)


# ============================================================================ GITHUB
def _compare_row(r: Resp, label: str) -> dict:
    d = r.data if isinstance(r.data, dict) else {}
    return {"variante": label, "http": r.status, "erro": r.error, "status": d.get("status"), "ahead_by": d.get("ahead_by"),
            "behind_by": d.get("behind_by"), "total_commits": d.get("total_commits"),
            "commits_na_pagina": len(d.get("commits") or []), "mensagem": d.get("message") if r.status != 200 else None,
            "url_enviada": r.url}


def t5_compare(G: Api, base: str, default: str, branches: list[str], forced: str | None) -> dict:
    say("GITHUB — compare COM BRANCH CONTENDO '/'")
    slash = [b for b in branches if "/" in b]
    pref = [b for b in slash if re.match(r"feature/(backend|frontend)/", b)]
    chosen = [forced] if forced else (pref[:2] or slash[:2])
    special = [b for b in branches if re.search(r"[^A-Za-z0-9._/\-]", b) and b not in chosen][:2]
    say(f"Branches no repositório: {len(branches)} | com '/': {len(slash)} | com caracteres especiais: "
        f"{len([b for b in branches if re.search(r'[^A-Za-z0-9._/-]', b)])}", indent=1)
    if not chosen:
        say("Nenhuma branch com '/' encontrada. Não é possível validar com dados reais.", indent=1)
        return verdict(UNK, "repositório sem branch contendo '/'")
    results, worst = [], OK
    for br in chosen + special:
        bh = f"{default}...{br}"
        variants = (
            ("A projeto: quote(safe='/.')", quote(bh, safe="/."), {"per_page": 100, "page": 1}),
            ("B tudo codificado (%2F)", quote(bh, safe="."), {"per_page": 1}),
            ("C sem codificar", bh, {"per_page": 1}),
        )
        say(f"base={default}  head={br}", indent=1)
        rows = []
        for label, path, params in variants:
            r = G.get(f"{base}/compare/{path}", params)
            row = _compare_row(r, label)
            rows.append(row)
            say(f"{label}: HTTP {row['http']} status={row['status']} ahead={row['ahead_by']} behind={row['behind_by']} "
                f"total_commits={row['total_commits']}" + (f" msg={row['mensagem']}" if row["mensagem"] else ""), indent=2)
            say(f"URL enviada: {row['url_enviada']}", indent=3)
        results.append({"branch": br, "variantes": rows})
        a, others = rows[0], rows[1:]
        if "/" in br:
            if a["http"] != 200 and any(o["http"] == 200 for o in others):
                worst = DIV
                say("→ ❌ a forma usada pelo projeto falhou, outra codificação funcionou", indent=2)
            elif a["http"] != 200:
                worst = worst if worst == DIV else UNK
    ok_slash = [r for r in results if "/" in r["branch"] and r["variantes"][0]["http"] == 200]
    if worst == OK and ok_slash:
        say("Conclusão: ✅ o compare funciona com branch contendo '/' usando a codificação do projeto", indent=1)
        return verdict(OK, f"HTTP 200 para {len(ok_slash)} branch(es) com '/' (A=quote(safe='/.'))", resultados=results)
    say(f"Conclusão: {worst} ver detalhes acima", indent=1)
    return verdict(worst, "compare com '/' não retornou 200 com a codificação do projeto", resultados=results)


def _dates(c: dict) -> tuple[datetime | None, datetime | None]:
    cm = c.get("commit") or {}
    return pdt((cm.get("author") or {}).get("date")), pdt((cm.get("committer") or {}).get("date"))


def t6_since(G: Api, base: str, default: str, branches: list[str], chosen: str | None, hours: int, lookback: int) -> dict:
    say("GITHUB — SEMÂNTICA DE `since`")
    now = datetime.now(timezone.utc)
    since = iso(now - timedelta(hours=hours))
    say(f"Listagem real de commits com since={since} (últimas {hours}h):", indent=1)
    listed = 0
    for br in dict.fromkeys([default] + ([chosen] if chosen else [])):
        r = G.get(f"{base}/commits", {"sha": br, "since": since, "per_page": 30})
        rows = r.data if r.ok and isinstance(r.data, list) else []
        say(f"[{br}] HTTP {r.status}, {len(rows)} commit(s)", indent=2)
        for c in rows[:15]:
            a, cm = _dates(c)
            delta = f"{int((cm - a).total_seconds())}s" if a and cm else "?"
            say(f"{c['sha'][:7]}  author={(c.get('commit') or {}).get('author', {}).get('date')}  "
                f"committer={(c.get('commit') or {}).get('committer', {}).get('date')}  (committer−author={delta})", indent=3)
        listed += len(rows)
    if listed == 0:
        say(f"Nenhum commit nas últimas {hours}h nesses ramos (não é erro).", indent=2)

    # candidatos: commits em que author.date != committer.date (≥ 60 s), da janela do projeto e de outras branches
    pool: list[dict] = []
    pool += G.paginate(f"{base}/commits", {"sha": default, "since": iso(now - timedelta(days=lookback))}, max_pages=3)
    for br in [b for b in branches if b != default][:5]:
        r = G.get(f"{base}/commits", {"sha": br, "per_page": 50})
        pool += r.data if r.ok and isinstance(r.data, list) else []
    uniq = {c["sha"]: c for c in pool}
    cands = []
    for c in uniq.values():
        a, cm = _dates(c)
        if a and cm and abs((cm - a).total_seconds()) >= SUMMARY_MIN_GAP_S:
            cands.append((c["sha"], a, cm))
    say(f"Commits examinados: {len(uniq)} | com |committer−author| ≥ {SUMMARY_MIN_GAP_S}s: {len(cands)}", indent=1)
    if not cands:
        say("Não foi possível determinar conclusivamente com os dados disponíveis.", indent=1)
        return verdict(UNK, "nenhum commit real com author.date ≠ committer.date para separar as hipóteses",
                       examinados=len(uniq))

    def included(sha: str, s: datetime) -> bool | None:
        r = G.get(f"{base}/commits", {"sha": sha, "since": iso(s), "per_page": 1})
        if not r.ok or not isinstance(r.data, list):
            return None
        return bool(r.data) and r.data[0].get("sha") == sha

    outcomes = []
    for sha, a, cm in cands[:4]:
        lo, hi = min(a, cm), max(a, cm)
        mid = lo + timedelta(seconds=int((hi - lo).total_seconds() // 2))
        ctrl_in, at_mid, ctrl_out = included(sha, lo - timedelta(hours=1)), included(sha, mid), included(sha, hi + timedelta(seconds=60))
        valid = ctrl_in is True and ctrl_out is False and at_mid is not None
        who = None
        if valid:
            who = "committer.date" if (at_mid == (cm > a)) else "author.date"
        say(f"{sha[:7]}: author={iso(a)} committer={iso(cm)} | since intermediário={iso(mid)} → "
            f"{'incluído' if at_mid else 'excluído'} | controles: antes={ctrl_in} depois={ctrl_out} | "
            f"{'usa ' + who if who else 'INCONCLUSIVO (controle falhou)'}", indent=2)
        outcomes.append({"sha": sha[:7], "author": iso(a), "committer": iso(cm), "mid": iso(mid), "incluido_no_mid": at_mid,
                         "controle_antes": ctrl_in, "controle_depois": ctrl_out, "usa": who})
    used = {o["usa"] for o in outcomes if o["usa"]}
    if len(used) == 1:
        w = used.pop()
        n = sum(1 for o in outcomes if o["usa"])
        say(f"Conclusão: ✅ `since` filtra por {w} ({n} commit(s) com controles válidos). "
            f"O Moonfoxes exibe `date = commit.author.date`.", indent=1)
        return verdict(OK, f"since compara com {w} em {n}/{len(outcomes)} commits testados (controles antes/depois válidos)",
                       testes=outcomes, usa=w)
    if len(used) > 1:
        say("Conclusão: ⚠️ resultados inconsistentes entre commits; não força conclusão", indent=1)
        return verdict(PART, "commits diferentes indicaram datas diferentes", testes=outcomes)
    say("Não foi possível determinar conclusivamente com os dados disponíveis.", indent=1)
    return verdict(UNK, "controles falharam em todos os candidatos", testes=outcomes)


def t7_prs(G: Api, base: str, default: str, forced_pr: int | None, max_prs: int, repo_info: dict) -> dict:
    say("GITHUB — PR MERGED / REBASE-AND-MERGE")
    allowed = {k: repo_info.get(k) for k in ("allow_merge_commit", "allow_squash_merge", "allow_rebase_merge")}
    say(f"Métodos de merge habilitados hoje no repositório (evidência fraca sobre o passado): {allowed}", indent=1)
    if forced_pr:
        numbers = [forced_pr]
    else:
        numbers = []
        for page in (1, 2, 3):
            r = G.get(f"{base}/pulls", {"state": "closed", "sort": "updated", "direction": "desc", "per_page": 50, "page": page})
            if not r.ok or not isinstance(r.data, list):
                break
            numbers += [p["number"] for p in r.data if p.get("merged_at") and (p.get("base") or {}).get("ref") == default]
            if len(r.data) < 50 or len(numbers) >= max_prs:
                break
        numbers = numbers[:max_prs]
    if not numbers:
        say("Nenhuma PR merged encontrada. Rebase-and-merge não pôde ser validado conclusivamente.", indent=1)
        return verdict(UNK, "nenhuma PR merged na base padrão")
    details, rebase_like, squash_like, merge_like, ambiguous = [], 0, 0, 0, 0
    for n in numbers:
        pr = G.get(f"{base}/pulls/{n}")
        if not pr.ok or not isinstance(pr.data, dict):
            say(f"PR #{n}: HTTP {pr.status}", indent=1)
            continue
        p = pr.data
        if not p.get("merged_at"):
            say(f"PR #{n}: não foi merged (state={p.get('state')}) — ignorada", indent=1)
            continue
        head_sha, head_ref, base_ref, mc = p["head"]["sha"], p["head"]["ref"], p["base"]["ref"], p.get("merge_commit_sha")
        commits = G.paginate(f"{base}/pulls/{n}/commits", per_page=100, max_pages=3)
        k = len(commits)
        observed = [f"state={p.get('state')} merged_at={p.get('merged_at')}", f"merge_commit_sha={(mc or 'null')[:7]}",
                    f"head={head_ref}@{head_sha[:7]} base={base_ref}",
                    f"commits da PR={k} (campo commits={p.get('commits')})",
                    f"último commit da PR == head.sha: {bool(commits) and commits[-1]['sha'] == head_sha}"]
        infer, unproven = [], ["a API não expõe o método de merge usado"]
        parents = None
        mcd = G.get(f"{base}/commits/{mc}") if mc else None
        if mcd is not None and mcd.ok and isinstance(mcd.data, dict):
            parents = len(mcd.data.get("parents") or [])
            observed.append(f"merge_commit_sha tem {parents} pai(s)")
            observed.append(f"committer do merge_commit == web-flow: "
                            f"{((mcd.data.get('committer') or {}).get('login') or '') == 'web-flow'}")
        anc = G.get(f"{base}/compare/{quote(head_sha, safe='')}...{quote(default, safe='/.')}", {"per_page": 1})
        anc_status = anc.data.get("status") if anc.ok and isinstance(anc.data, dict) else None
        head_in_default = anc_status in ("ahead", "identical") if anc_status else None
        observed.append(f"head.sha da PR é ancestral de {default}: {head_in_default} (compare status={anc_status})")
        cls = "indeterminado"
        if parents is None:
            infer.append("sem merge_commit_sha legível: método indeterminável")
        elif parents >= 2:
            cls, merge_like = "merge commit", merge_like + 1
            infer.append("2 pais no merge_commit_sha: é um merge commit (observação direta, não inferência)")
        elif head_in_default is True:
            cls = "fast-forward/indeterminado"
            infer.append("merge com 1 pai e head ancestral: possível fast-forward; método indeterminável")
        else:
            top = G.get(f"{base}/commits", {"sha": mc, "per_page": max(k, 1)}) if mc else None
            top_commits = list(reversed(top.data)) if top is not None and top.ok and isinstance(top.data, list) else []
            eq = lambda c: ((c.get("commit") or {}).get("author", {}).get("email"),  # noqa: E731
                            (c.get("commit") or {}).get("author", {}).get("date"),
                            ((c.get("commit") or {}).get("message") or "").split("\n", 1)[0])
            if k >= 2 and len(top_commits) >= k and all(eq(a) == eq(b) for a, b in zip(top_commits[-k:], commits, strict=True)) \
                    and all(a["sha"] != b["sha"] for a, b in zip(top_commits[-k:], commits, strict=True)):
                cls, rebase_like = "compatível com rebase-and-merge", rebase_like + 1
                diff_dates = sum(1 for a in top_commits[-k:]
                                 if (_dates(a)[0] and _dates(a)[1] and _dates(a)[0] != _dates(a)[1]))
                observed.append(f"os {k} commits no topo de {default} repetem (autor.email, author.date, título) dos {k} "
                                f"da PR com SHAs diferentes; committer.date ≠ author.date em {diff_dates}/{k}")
                infer.append("padrão compatível com rebase-and-merge (mesma mudança reescrita: novo SHA, mesmo autor/data/título)")
            elif mc and top_commits and f"(#{n})" in ((top_commits[-1].get("commit") or {}).get("message") or "").split("\n", 1)[0] \
                    and all(top_commits[-1]["sha"] != c["sha"] for c in commits):
                cls, squash_like = "compatível com squash", squash_like + 1
                infer.append("1 commit na main com sufixo (#N) no título e sem correspondência 1-1 com os da PR: compatível com squash")
            else:
                cls, ambiguous = "ambíguo (squash ou rebase de 1 commit)", ambiguous + 1
                infer.append("1 pai e head fora do histórico da main, mas sem sinal que separe squash de rebase")
        say(f"PR #{n} → {cls}", indent=1)
        say("observado: " + " | ".join(observed), indent=2)
        say("inferência: " + ("; ".join(infer) or "—"), indent=2)
        say("não comprovado: " + "; ".join(unproven), indent=2)
        details.append({"pr": n, "classe": cls, "observado": observed, "inferencia": infer})
    counts = {"merge": merge_like, "rebase_compat": rebase_like, "squash_compat": squash_like, "ambiguo": ambiguous}
    say(f"Resumo das {len(details)} PRs analisadas: {counts}", indent=1)
    if rebase_like:
        say("Conclusão: ⚠️ há PRs com padrão COMPATÍVEL com rebase-and-merge (SHAs novos; autor/data/título preservados). "
            "O método em si é inferido, não provado.", indent=1)
        return verdict(PART, f"{rebase_like} PR(s) compatíveis com rebase (inferência); nenhum campo da API confirma o método",
                       contagem=counts, prs=details, metodos_habilitados=allowed)
    say("Rebase-and-merge não pôde ser validado conclusivamente.", indent=1)
    return verdict(UNK, "nenhuma PR com padrão de rebase identificável; Rebase-and-merge não pôde ser validado conclusivamente",
                   contagem=counts, prs=details, metodos_habilitados=allowed)


# ============================================================================ TESTE 8 — chamadas reais
def t10_gh_reviews(G: Api, base: str, max_prs: int) -> dict:
    """Dados de revisão de PR de que o MVP depende. Só GET."""
    say("GITHUB — REVIEWS DE PR (requested_reviewers, /pulls/{n}/reviews)")
    r = G.get(f"{base}/pulls", {"state": "all", "per_page": 30, "sort": "updated", "direction": "desc"})
    prs = [p for p in (r.data if r.ok and isinstance(r.data, list) else []) if isinstance(p, dict)]
    if not prs:
        return verdict(UNK, f"nenhuma PR listada (HTTP {r.status} {r.error or ''})".strip())
    keys = {k: all(k in p for p in prs) for k in ("requested_reviewers", "requested_teams", "draft", "merged_at", "user")}
    say(f"Chaves presentes em TODAS as PRs da listagem: {keys}", indent=1)
    pick = [p for p in prs if p.get("state") == "open"][:max_prs // 2 or 1] + [p for p in prs if p.get("merged_at")][:max_prs]
    states: Counter = Counter()
    rows, no_review, errors = [], 0, 0
    for p in pick[:max_prs]:
        rv = G.get(f"{base}/pulls/{p['number']}/reviews", {"per_page": 100})
        if not rv.ok or not isinstance(rv.data, list):
            errors += 1
            rows.append({"pr": p["number"], "http": rv.status})
            continue
        for x in rv.data:
            states[x.get("state")] += 1
        no_review += 0 if rv.data else 1
        first = rv.data[0] if rv.data else {}
        rows.append({"pr": p["number"], "estado_pr": p.get("state"), "reviews": len(rv.data), "chaves_review": sorted(first) if first else [],
                     "tipo_usuario": (first.get("user") or {}).get("type") if first else None, "submitted_at": bool(first.get("submitted_at")) if first else None})
    for row in rows:
        say(str(row), indent=2)
    say(f"Estados de review encontrados: {dict(states)} | PRs sem nenhum review: {no_review}/{len(rows)} | erros: {errors}", indent=1)
    ev = {"chaves_listagem": keys, "estados_review": dict(states), "amostra": rows}
    if errors == len(rows):
        say("Conclusão: ❌ /pulls/{n}/reviews não respondeu (permissão do token?): o MVP mostra 'revisão desconhecida'.", indent=1)
        return verdict(DIV, "endpoint de reviews indisponível para o token", **ev)
    if not states:
        return verdict(PART, "endpoint de reviews responde, mas nenhuma PR da amostra tem review para provar o formato", **ev)
    return verdict(OK, f"reviews lidos em {len(rows) - errors} PRs; estados {dict(states)}", **ev)


def t8_run(project_root: Path, env_file: Path | None, args, s_override, jira_reachable: bool, gh_reachable: bool, G_diag: Api) -> dict:
    say("MOONFOXES — QUANTIDADE REAL DE CHAMADAS EM UMA ATUALIZAÇÃO")
    sys.path.insert(0, str(project_root))
    from domain.people import DevMapper
    from services.github import GitHubService
    from services.http import HttpClient
    from services.jira import JiraService
    settings = s_override
    ledger = Ledger(cap=args.max_run_requests)
    factory = session_factory(ledger, args.allow_jql_post)
    mapper = DevMapper(settings.dev_mapping)

    out: dict = {"jira": None, "github": None}
    notes: list[str] = []
    t_all = time.perf_counter()
    if jira_reachable:
        http = HttpClient("Jira", headers={"Accept": "application/json"}, auth=HTTPBasicAuth(settings.jira.email, settings.jira.token),
                          session_factory=factory)
        t0 = time.perf_counter()
        try:
            res = JiraService(http, settings, mapper).fetch()
            out["jira"] = {"secs": time.perf_counter() - t0, "status": res.status, "stats": res.stats,
                           "warnings": res.warnings[:6], "errors": res.errors[:3], "http_calls_attr": http.calls}
        except (ReadOnlyViolation, RequestCapExceeded) as e:
            notes.append(f"Jira abortado: {e}" + (" — reexecute com --allow-jql-post" if "search/jql" in str(e) else ""))
            out["jira"] = {"secs": time.perf_counter() - t0, "abortado": str(e)}
    else:
        notes.append("Jira NÃO executado (não alcançável neste ambiente).")
    if gh_reachable:
        http = HttpClient("GitHub", headers={"Authorization": f"Bearer {settings.github.token}", "Accept": "application/vnd.github+json",
                                             "X-GitHub-Api-Version": GH_VERSION}, session_factory=factory)
        t0 = time.perf_counter()
        try:
            res = GitHubService(http, settings, mapper).fetch()
            out["github"] = {"secs": time.perf_counter() - t0, "status": res.status, "stats": res.stats,
                             "warnings": res.warnings[:6], "errors": res.errors[:3], "http_calls_attr": http.calls}
        except (ReadOnlyViolation, RequestCapExceeded) as e:
            notes.append(f"GitHub abortado: {e}")
            out["github"] = {"secs": time.perf_counter() - t0, "abortado": str(e)}
    total_secs = time.perf_counter() - t_all

    rows = ledger.rows
    by_src = Counter(r["source"] for r in rows)
    say(f"Requests Jira: {by_src.get('Jira', 0)}", indent=1)
    say(f"Requests GitHub: {by_src.get('GitHub', 0)}", indent=1)
    say(f"Total: {len(rows)}", indent=1)
    say(f"Tempo total: {total_secs:.1f}s" + "".join(f" | {k}: {v['secs']:.1f}s" for k, v in out.items() if v), indent=1)
    rl = [r["remaining"] for r in rows if r["source"] == "GitHub" and r["remaining"] is not None]
    if rl:
        say(f"Cota GitHub (estimada pelos cabeçalhos X-RateLimit-Remaining): {max(rl) - min(rl) + 1} consumida(s); "
            f"menor valor restante visto: {min(rl)}", indent=1)
    grouped: dict = defaultdict(lambda: Counter())
    for r in rows:
        grouped[r["source"]][f"{r['method']} {r['endpoint']}"] += 1
    for src in ("Jira", "GitHub"):
        if grouped.get(src):
            say(src, indent=1)
            for ep, n in sorted(grouped[src].items(), key=lambda kv: -kv[1]):
                say(f"{ep} → {n}", indent=2)
    codes = Counter(f"{r['source']} {r['status']}" for r in rows)
    say(f"Distribuição de status HTTP: {dict(codes)}", indent=1)
    for src in ("jira", "github"):
        v = out[src]
        if v and "stats" in v:
            st = {k: v2 for k, v2 in v["stats"].items() if k not in ("worklog_partial", "changelog_partial", "repos")}
            say(f"{src}: status={v['status']} stats={st} | HttpClient.calls={v['http_calls_attr']} (inclui retries)", indent=1)
            for w in v["warnings"]:
                say(f"aviso: {w}", indent=2)
            for e in v["errors"]:
                say(f"ERRO: {e}", indent=2)
    if ledger.blocked:
        say(f"Requisições BLOQUEADAS pelo guard read-only: {dict(Counter(ledger.blocked))}", indent=1)
    for n in notes:
        say(n, indent=1)
    payload = {"jira": by_src.get("Jira", 0), "github": by_src.get("GitHub", 0), "total": len(rows), "secs": round(total_secs, 1),
               "por_endpoint": {s: dict(c) for s, c in grouped.items()}, "status_http": dict(codes),
               "cota_consumida_estimada": (max(rl) - min(rl) + 1) if rl else None,
               "menor_restante_visto": min(rl) if rl else None, "notas": notes, "execucoes": out,
               "bloqueadas": dict(Counter(ledger.blocked))}
    complete = out["jira"] and out["github"] and "abortado" not in out["jira"] and "abortado" not in out["github"]
    if complete:
        return verdict(OK, f"medido: Jira={payload['jira']} GitHub={payload['github']} total={payload['total']} em {payload['secs']}s", **payload)
    if any(v and "abortado" not in v for v in out.values()):
        return verdict(PART, f"medido só parcialmente: Jira={payload['jira']} GitHub={payload['github']}; " + "; ".join(notes), **payload)
    return verdict(UNK, "; ".join(notes) or "nada medido", **payload)


# ============================================================================ main
def main() -> int:
    ap = argparse.ArgumentParser(description="Validação real read-only das APIs Jira/GitHub do Moonfoxes")
    ap.add_argument("--project-root", type=Path)
    ap.add_argument("--env-file", type=Path, help=".env alternativo (padrão: <raiz>/.env)")
    ap.add_argument("--jira-domain"), ap.add_argument("--board-id"), ap.add_argument("--org"), ap.add_argument("--repo")
    ap.add_argument("--branch", help="branch (com '/') para o teste compare")
    ap.add_argument("--issue", help="chave Jira para os testes de worklog/changelog (ex.: JH-10)")
    ap.add_argument("--pr", type=int, help="número de uma PR merged para o teste 7")
    ap.add_argument("--since-hours", type=int, default=48)
    ap.add_argument("--sample-issues", type=int, default=200)
    ap.add_argument("--max-prs", type=int, default=10)
    ap.add_argument("--only", help="lista separada por vírgula: t1,t2,...,t10")
    ap.add_argument("--skip-run", action="store_true", help="não executa o teste 8")
    ap.add_argument("--allow-jql-post", action="store_true", help="libera SOMENTE POST /rest/api/3/search/jql (consulta) no teste 8")
    ap.add_argument("--max-run-requests", type=int, default=3000)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows: console cp1252 quebra com emojis
    except Exception:
        pass

    here = Path(__file__).resolve().parent
    root = args.project_root or next((p for p in (here, here.parent) if (p / "settings.py").exists()), here.parent)
    sys.path.insert(0, str(root))
    from services.jira import EPIC_TYPES, ISSUE_FIELDS
    from settings import OBRIGATORIAS, load_settings

    env_path = args.env_file or root / ".env"
    s = load_settings(env_path=env_path)
    if args.jira_domain or args.board_id:
        s = replace(s, jira=replace(s.jira, domain=args.jira_domain or s.jira.domain, board_id=args.board_id or s.jira.board_id))
    if args.org or args.repo:
        s = replace(s, github=replace(s.github, org=args.org or s.github.org, repos=(args.repo,) if args.repo else s.github.repos))
    REDACT.add(s.jira.token, s.jira.email, s.github.token)

    jira_ready = bool(s.jira.email and s.jira.token and s.jira.domain and s.jira.board_id)
    gh_ready = bool(s.github.token and s.github.org and s.github.repos)
    if not jira_ready and not gh_ready:
        say("Credenciais indisponíveis. NÃO continuei com mocks.")
        say(f"Defina no ambiente ou em {env_path.name}: {', '.join(OBRIGATORIAS)} (segredos: TOKEN, GITHUB_TOKEN, EMAIL)")
        say("Não secretos: JIRA_DOMAIN, BOARD_ID, JIRA_PROJECT; e github.org/repos em config.json (ou --org/--repo).")
        return 2

    only = {x.strip().lower() for x in args.only.split(",")} if args.only else {f"t{i}" for i in range(1, 11)}
    if args.skip_run:
        only.discard("t8")
    ledger_diag = Ledger()
    results: dict[str, dict] = {}

    def guarded(name: str, fn) -> dict:
        try:
            return fn()
        except (ReadOnlyViolation, RequestCapExceeded) as e:
            say(f"{name} abortado: {e}")
            return verdict(UNK, f"abortado: {e}")
        except Exception as e:  # noqa: BLE001 - um teste nunca derruba os outros
            say(f"{name} falhou com {type(e).__name__}: {e}")
            LOG.append(traceback.format_exc(limit=2))
            return verdict(UNK, f"exceção {type(e).__name__}")

    # ---- ambiente
    say("# Validação Real Jira/GitHub — Moonfoxes")
    say("## Ambiente")
    fp = hashlib.sha256(b"".join((root / p).read_bytes() for p in ("services/jira.py", "services/github.py", "services/http.py"))).hexdigest()[:12]
    say(f"Python: {platform.python_version()} | OS: {platform.platform()} | Moonfoxes: sem versão declarada; "
        f"impressão digital services/{{jira,github,http}}.py = {fp}", indent=1)
    say(f"Credenciais presentes (sem valores): Jira={'sim' if jira_ready else 'NÃO'} "
        f"GitHub={'sim' if s.github.token else 'NÃO'} | ausentes obrigatórias: {list(s.missing_env) or 'nenhuma'}", indent=1)
    say("Modo: READ-ONLY (guard recusa qualquer método além de GET/HEAD)", indent=1)

    # ---- Jira
    jbase = f"https://{s.jira.domain}"
    J = None
    jira_info: dict = {"blocked": "credenciais Jira ausentes"}
    sample: list[dict] = []
    board_meta: dict = {}
    if jira_ready:
        jsess = session_factory(ledger_diag, False)()
        jsess.auth, jsess.headers["Accept"] = HTTPBasicAuth(s.jira.email, s.jira.token), "application/json"
        J = Api(jsess)
        jira_info = jira_preflight(J, jbase)
    say(f"Jira: {jira_info.get('deployment') or '?'} {jira_info.get('version') or ''} | {jira_info.get('auth')} "
        f"| {jira_info.get('blocked') or 'alcançável'}", indent=1)
    jira_reachable = jira_ready and not jira_info.get("blocked")

    say("")
    say("## Jira")
    jira_tests = {"t1": "Paginação Jira", "t2": "epic/closedSprints", "t3": "Worklog (paginação)", "t4": "Changelog (paginação)",
                  "t9": "Campos do MVP (Story Points/Flagged/links/Sprint)"}
    if jira_reachable and (only & {"t1", "t2", "t3", "t4"}):
        sample, board_meta = sample_board(J, jbase, s.jira.board_id, ISSUE_FIELDS, args.sample_issues)
        say(f"Amostra do board carregada: {len(sample)} issues (total informado pela API: {board_meta.get('total')})", indent=1)
    for tid, name in jira_tests.items():
        if tid not in only:
            continue
        if not jira_reachable:
            reason = jira_info.get("blocked", "Jira não alcançável")
            say(f"{name}: NÃO EXECUTADO — {reason}")
            results[tid] = verdict(UNK, f"Jira inalcançável: {reason}")
            continue
        fn = {"t1": lambda: t1_pagination(J, jbase, s.jira.board_id, ISSUE_FIELDS),
              "t2": lambda: t2_fields(J, jbase, s.jira.board_id, sample, {t.lower() for t in EPIC_TYPES}),
              "t3": lambda: t3_worklog(J, jbase, sample, args.issue),
              "t4": lambda: t4_changelog(J, jbase, sample, args.issue),
              "t9": lambda: t9_mvp_jira(J, jbase, s.jira.board_id, ISSUE_FIELDS)}[tid]
        results[tid] = guarded(name, fn)
        say("")

    # ---- GitHub
    say("## GitHub")
    G, gh_reachable, repo_info, default, branches = None, False, {}, "main", []
    if gh_ready:
        gsess = session_factory(ledger_diag, False)()
        gsess.headers.update({"Authorization": f"Bearer {s.github.token}", "Accept": "application/vnd.github+json",
                              "X-GitHub-Api-Version": GH_VERSION})
        G = Api(gsess)
        repo = s.github.repos[0]
        base = f"{GH_API}/repos/{s.github.org}/{repo}"
        r = G.get(base)
        if r.ok and isinstance(r.data, dict):
            gh_reachable, repo_info = True, r.data
            default = r.data.get("default_branch") or "main"
            branches = [b["name"] for b in G.paginate(f"{base}/branches", max_pages=10)]
            say(f"API: versão solicitada {GH_VERSION}, selecionada pelo servidor: {r.headers.get('x-github-api-version-selected')} | "
                f"repo {s.github.org}/{repo} | branch padrão: {default} | branches: {len(branches)}", indent=1)
        else:
            deny = r.headers.get("x-deny-reason")
            say(f"GitHub indisponível: HTTP {r.status} {r.error or ''} {('(' + deny + ')') if deny else ''}", indent=1)
    else:
        say("Credenciais/organização/repositório GitHub ausentes.", indent=1)
    gh_tests = {"t5": "Compare com '/'", "t6": "since", "t7": "PR merged / rebase", "t10": "Reviews de PR"}
    slash_pref = args.branch or next((b for b in branches if re.match(r"feature/(backend|frontend)/", b)), None) or \
        next((b for b in branches if "/" in b), None)
    for tid, name in gh_tests.items():
        if tid not in only:
            continue
        if not gh_reachable:
            say(f"{name}: NÃO EXECUTADO — GitHub não alcançável/sem credenciais")
            results[tid] = verdict(UNK, "GitHub inalcançável")
            continue
        fn = {"t5": lambda: t5_compare(G, base, default, branches, args.branch),
              "t6": lambda: t6_since(G, base, default, branches, slash_pref, args.since_hours, s.github.lookback_days),
              "t7": lambda: t7_prs(G, base, default, args.pr, args.max_prs, repo_info),
              "t10": lambda: t10_gh_reviews(G, base, args.max_prs)}[tid]
        results[tid] = guarded(name, fn)
        say("")

    # ---- Teste 8
    say("## Performance")
    if "t8" in only:
        if not (jira_reachable or gh_reachable):
            say("Nenhuma API alcançável: nada a medir.")
            results["t8"] = verdict(UNK, "nenhuma API alcançável")
        else:
            results["t8"] = guarded("Teste 8", lambda: t8_run(root, env_path, args, s, jira_reachable, gh_reachable, G or Api(session_factory(ledger_diag, False)())))
    else:
        say("Teste 8 não solicitado.")

    # ---- matriz
    say("")
    say("## Matriz final")
    matrix = (("Paginação Jira", "t1"), ("Compare com `/`", "t5"), ("`since`", "t6"), ("Rebase", "t7"),
              ("epic/closedSprints", "t2"), ("Chamadas reais", "t8"), ("(extra) Worklog paginado", "t3"), ("(extra) Changelog paginado", "t4"),
              ("MVP: Story Points / Flagged / links / Sprint no histórico", "t9"), ("MVP: reviews de PR", "t10"))
    say("| Hipótese | Resultado | Evidência |")
    say("|---|---|---|")
    for label, tid in matrix:
        v = results.get(tid)
        if v:
            say(f"| {label} | {v['status']} {LABEL[v['status']]} | {v['evidence']} |")
        else:
            say(f"| {label} | — | não executado nesta rodada |")

    out_dir = args.out or here / "validation_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(REDACT(json.dumps(results, ensure_ascii=False, indent=2, default=str)), encoding="utf-8")
    (out_dir / "console.log").write_text(REDACT("\n".join(LOG)), encoding="utf-8")
    say(f"\nArquivos (sem segredos): {out_dir / 'results.json'} | {out_dir / 'console.log'}")
    say(f"Requisições de diagnóstico (testes 1–7): {len(ledger_diag.rows)} | bloqueadas pelo guard: {len(ledger_diag.blocked)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
