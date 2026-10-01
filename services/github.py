"""Rastreia commits, branches e Pull Requests do GitHub (REST) e os vincula ao Jira.

Como decidimos que um commit foi ENTREGUE (o antigo `on_main` falhava com Squash and Merge):
  1. o SHA está no histórico da branch padrão (merge commit / fast-forward), OU
  2. o commit pertence a uma PR **merged na branch padrão** (`/pulls/{n}/commits`). Com squash ou rebase o
     SHA original nunca chega à main, mas a PR prova a entrega — e continua valendo mesmo se a branch
     de origem foi apagada.
Três fatos distintos (nunca misturar): `on_main` = o SHA literal está na branch padrão; `delivered_via_pr` = o commit
pertence a uma PR merged na base padrão; `on_main_equivalent` = o SHA não está na main, mas há uma cópia equivalente
dela (rebase: mesmo autor/data/título). `delivered_via` resume: "main" > "main_equivalente" > "pr".
Uma branch é "entregue" quando existe PR merged na base padrão cujo `head.sha` é o topo atual da branch;
commits empurrados DEPOIS do merge continuam pendentes (`compare` do head da PR até a branch).

Sem limites artificiais: toda listagem pagina até esgotar; a janela é por data (`since`, configurável).
"""
from __future__ import annotations

import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from math import ceil
from typing import Any
from urllib.parse import quote

import pandas as pd

from domain import timeutil
from domain.linking import check_commit_message, extract_jira_keys, extract_us_ids, parse_branch, parse_pr_title
from domain.people import DevMapper, is_bot
from domain.pr_review import ReviewSummary, review_state, summarize_reviews
from services.http import ApiError, AuthError, HttpClient, NotFound, friendly
from services.results import SourceResult
from settings import Settings

API = "https://api.github.com"
PAGE = 100
PR_COMMITS_API_LIMIT = 250  # limite documentado do endpoint /pulls/{n}/commits
_MERGE_TITLE = re.compile(r"^(Merge (pull request|branch|remote-tracking branch))", re.IGNORECASE)

COMMIT_COLS = ["sha", "url", "repo", "author", "author_login", "author_name", "author_email", "author_mapped", "kind",
               "is_bot", "is_merge", "date", "message", "title", "us_id", "jira_key", "jira_keys", "ref_jira_key", "ref_us_id",
               "link_source", "valid_message", "message_problems", "branches", "branch_label", "pr_numbers",
               "on_main", "on_main_equivalent", "delivered_via_pr", "delivered", "delivered_via"]
BRANCH_COLS = ["repo", "branch", "is_default", "kind", "head_sha", "ahead_main", "behind_main", "pending_commits",
               "delivered", "last_commit", "last_author", "us_id", "jira_key", "follows_convention", "pr", "pr_state",
               "pr_numbers", "compare_status"]
PR_COLS = ["repo", "number", "title", "author", "author_login", "state", "draft", "head", "head_sha", "base",
           "base_is_default", "created", "updated", "closed_at", "merged_at", "merge_commit_sha", "merge_method",
           "url", "us_id", "jira_key", "kind", "follows_convention",
           # revisão (reviews REAIS do GitHub; ver domain/pr_review.py)
           "requested_reviewers", "reviews_known", "review_count", "approvals", "changes_requested", "commented_reviewers",
           "first_review_at", "last_review_at", "last_review_state", "review_state"]


@dataclass
class GitHubData:
    commits: pd.DataFrame
    branches: pd.DataFrame
    prs: pd.DataFrame

    @classmethod
    def empty(cls) -> GitHubData:
        return cls(*(pd.DataFrame(columns=c) for c in (COMMIT_COLS, BRANCH_COLS, PR_COLS)))


def _eq_key(raw: dict) -> tuple:
    """Chave de commit 'equivalente' (rebase copia autor+data+título, mas troca o SHA)."""
    c = raw.get("commit") or {}
    a = c.get("author") or {}
    return a.get("email"), a.get("date"), (c.get("message") or "").split("\n", 1)[0]


class GitHubService:
    def __init__(self, http: HttpClient, settings: Settings, mapper: DevMapper, max_pages: int = 500, max_workers: int = 4):
        self.http, self.cfg, self.mapper = http, settings, mapper
        self.org = settings.github.org
        self.key_pattern = settings.linking.jira_key_pattern
        self.max_pages, self.max_workers = max_pages, max_workers
        self._warnings: list[str] = []

    # ------------------------------------------------------------ HTTP / paginação
    def _paginate(self, url: str, params: dict[str, Any] | None = None, what: str = "") -> list[dict]:
        """Todas as páginas (per_page=100) até uma página incompleta. Só para se atingir a salvaguarda."""
        out: list[dict] = []
        for page in range(1, self.max_pages + 1):
            data = self.http.get_json(url, {**(params or {}), "per_page": PAGE, "page": page})
            if not isinstance(data, list):
                raise ApiError("GitHub", f"resposta inesperada em {what or url}", url=url)
            out += data
            if len(data) < PAGE:
                return out
        self._warnings.append(f"{what or url}: atingiu a salvaguarda de {self.max_pages} páginas; lista pode estar incompleta")
        return out

    def _list_prs(self, base: str, since_iso: str) -> list[dict]:
        """PRs abertas (TODAS, mesmo antigas: 'aberta há tempo excessivo' importa) + fechadas/merged na janela."""
        opened = self._paginate(f"{base}/pulls", {"state": "open", "sort": "updated", "direction": "desc"}, "PRs abertas")
        closed: list[dict] = []
        for page in range(1, self.max_pages + 1):
            data = self.http.get_json(f"{base}/pulls", {"state": "closed", "sort": "updated", "direction": "desc",
                                                        "per_page": PAGE, "page": page})
            closed += [p for p in data if (p.get("updated_at") or "") >= since_iso]
            if len(data) < PAGE or any((p.get("updated_at") or "") < since_iso for p in data):
                break  # ordenado por atualização decrescente: o resto é mais antigo que a janela
        return opened + closed

    def _compare(self, base: str, basehead: str) -> dict:
        """`compare` com todos os commits (paginado). basehead = 'BASE...HEAD'."""
        url = f"{base}/compare/{quote(basehead, safe='/.')}"
        first = self.http.get_json(url, {"per_page": PAGE, "page": 1})
        commits = list(first.get("commits") or [])
        total = first.get("total_commits", len(commits))
        for page in range(2, min(ceil(total / PAGE), self.max_pages) + 1):
            commits += self.http.get_json(url, {"per_page": PAGE, "page": page}).get("commits") or []
        if len(commits) < total:
            self._warnings.append(f"compare {basehead}: {len(commits)} de {total} commits carregados")
        return {"ahead_by": first.get("ahead_by", 0), "behind_by": first.get("behind_by", 0),
                "status": first.get("status"), "commits": commits}

    # ------------------------------------------------------------ um repositório
    def _pr_commits(self, base: str, number: int) -> list[dict]:
        try:
            lst = self._paginate(f"{base}/pulls/{number}/commits", what=f"commits da PR #{number}")
        except AuthError:
            raise
        except ApiError as e:
            self._warnings.append(f"PR #{number}: commits indisponíveis ({friendly(e)})")
            return []
        if len(lst) >= PR_COMMITS_API_LIMIT:
            self._warnings.append(f"PR #{number}: a API limita a {PR_COMMITS_API_LIMIT} commits por PR; lista pode estar truncada")
        return lst

    def _pr_reviews(self, base: str, number: int) -> list[dict] | None:
        """Reviews de uma PR (paginado). `None` = indisponível (não se assume 'sem revisão' quando não deu para ler)."""
        try:
            return self._paginate(f"{base}/pulls/{number}/reviews", what=f"reviews da PR #{number}")
        except AuthError:
            raise
        except ApiError as e:
            self._warnings.append(f"PR #{number}: reviews indisponíveis ({friendly(e)}); estado de revisão desconhecido")
            return None

    def _fetch_repo(self, repo: str, since_iso: str) -> tuple[list[dict], list[dict], list[dict]]:
        base = f"{API}/repos/{self.org}/{repo}"
        default = self.http.get_json(base)["default_branch"]
        branches = self._paginate(f"{base}/branches", what=f"{repo}: branches")
        prs_raw = self._list_prs(base, since_iso)
        main_raw = self._paginate(f"{base}/commits", {"sha": default, "since": since_iso}, f"{repo}: commits da {default}")
        main_shas = {c["sha"] for c in main_raw}
        main_literal = frozenset(main_shas)  # SHAs literalmente na main; `main_shas` é alterado pelo dedupe de rebase abaixo
        main_by_sha = {c["sha"]: c for c in main_raw}
        full = f"{self.org}/{repo}"

        def same_repo(p: dict) -> bool:
            return ((p["head"].get("repo") or {}).get("full_name") or "").lower() == full.lower()

        merged_default = [p for p in prs_raw if p.get("merged_at") and p["base"]["ref"] == default]
        merge_shas = {p["merge_commit_sha"] for p in merged_default if p.get("merge_commit_sha")}

        # commits de cada PR aberta/merged (prova de entrega e de trabalho em andamento)
        need = [p for p in prs_raw if p["state"] == "open" or p.get("merged_at")]
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            pr_commits = dict(zip((p["number"] for p in need), pool.map(lambda p: self._pr_commits(base, p["number"]), need), strict=True))
        # reviews só de PRs abertas ou merged (o que alimenta "aguardando revisão", "revisada" e a Timeline)
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            pr_reviews = dict(zip((p["number"] for p in need), pool.map(lambda p: self._pr_reviews(base, p["number"]), need), strict=True))
        pr_delivered_shas = {c["sha"] for p in merged_default for c in pr_commits.get(p["number"], [])}
        pr_by_number = {p["number"]: p for p in prs_raw}
        pr_of_sha: dict[str, list[int]] = defaultdict(list)
        for n, lst in pr_commits.items():
            for c in lst:
                pr_of_sha[c["sha"]].append(n)
        prs_by_head: dict[str, list[dict]] = defaultdict(list)
        for p in prs_raw:
            if same_repo(p):
                prs_by_head[p["head"]["ref"]].append(p)

        # branches: só faz `compare` quando é preciso
        commits: dict[str, dict] = {}

        def add(raw: dict, branch: str | None) -> None:
            e = commits.setdefault(raw["sha"], {"raw": raw, "branches": []})
            if branch and branch not in e["branches"]:
                e["branches"].append(branch)

        for c in main_raw:
            add(c, default)
        for n, lst in pr_commits.items():
            head = pr_by_number[n]["head"]["ref"]
            for c in lst:
                add(c, head)

        # commits "equivalentes" (rebase): a cópia na main é a mesma mudança da PR; não contar duas vezes
        pr_eq = {_eq_key(c): c["sha"] for lst in pr_commits.values() for c in lst}
        for sha in list(commits):
            if sha in main_shas and sha not in pr_delivered_shas and _eq_key(commits[sha]["raw"]) in pr_eq:
                twin = pr_eq[_eq_key(commits[sha]["raw"])]
                if twin != sha and twin in commits:
                    del commits[sha]
                    main_shas.discard(sha)
                    main_shas.add(twin)

        branch_rows: list[dict] = []
        todo = []
        for b in branches:
            name, head_sha = b["name"], b["commit"]["sha"]
            if name == default:
                continue
            # PR "principal" da branch: aberta > merged > fechada; empate: a mais recente
            mine = sorted(prs_by_head.get(name, []),
                          key=lambda p: (0 if p["state"] == "open" else 1 if p.get("merged_at") else 2, -p["number"]))
            merged_here = sorted([p for p in mine if p.get("merged_at") and p["base"]["ref"] == default],
                                 key=lambda p: p["merged_at"])
            if head_sha in main_shas or any(p["head"]["sha"] == head_sha for p in merged_here):
                todo.append((b, mine, None, "merged"))  # já entregue: nenhuma chamada extra
            else:
                basehead = f"{merged_here[-1]['head']['sha']}...{name}" if merged_here else f"{default}...{name}"
                todo.append((b, mine, basehead, None))

        def run_compare(item: tuple) -> dict | None:
            _, _, basehead, _ = item
            if basehead is None:
                return None
            try:
                return self._compare(base, basehead)
            except AuthError:
                raise
            except NotFound:
                self._warnings.append(f"compare {basehead}: não encontrado; branch tratada como sem pendências verificáveis")
                return {"ahead_by": 0, "behind_by": 0, "status": "not_found", "commits": []}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            compares = list(pool.map(run_compare, todo))

        for (b, mine, _, tag), cmp_ in zip(todo, compares, strict=True):
            name, head_sha = b["name"], b["commit"]["sha"]
            info = parse_branch(name, self.key_pattern)
            latest = mine[0] if mine else None
            ahead = cmp_["ahead_by"] if cmp_ else 0
            for c in (cmp_ or {}).get("commits", []):
                add(c, name)
            last_raw = (cmp_["commits"][-1] if cmp_ and cmp_["commits"] else None)
            if last_raw is None and latest is not None and pr_commits.get(latest["number"]):
                last_raw = pr_commits[latest["number"]][-1]
            lc = (last_raw or {}).get("commit", {}).get("author", {}) if last_raw else {}
            la = ((last_raw or {}).get("author") or {}).get("login") if last_raw else None
            branch_rows.append({
                "repo": repo, "branch": name, "is_default": False, "kind": info.kind, "head_sha": head_sha,
                "ahead_main": ahead, "behind_main": cmp_["behind_by"] if cmp_ else 0, "pending_commits": ahead,
                "delivered": ahead == 0 and (tag == "merged" or any(p.get("merged_at") for p in mine)),
                "last_commit": timeutil.parse_ts(lc.get("date")),
                "last_author": self.mapper.github(la, lc.get("name")).slug if last_raw else "",
                "us_id": info.us_id, "jira_key": info.jira_key, "follows_convention": info.follows_convention,
                "pr": f"#{latest['number']}" if latest else None,
                "pr_state": (("merged" if latest.get("merged_at") else latest["state"]) if latest else None),
                "pr_numbers": [p["number"] for p in mine], "compare_status": (cmp_ or {}).get("status", tag),
            })
        branch_rows.append({"repo": repo, "branch": default, "is_default": True, "kind": None, "head_sha": None,
                            "ahead_main": 0, "behind_main": 0, "pending_commits": 0, "delivered": True,
                            "last_commit": pd.NaT, "last_author": "", "us_id": None, "jira_key": None,
                            "follows_convention": False, "pr": None, "pr_state": None, "pr_numbers": [], "compare_status": "default"})

        # ---- linhas de commit
        rows = []
        for sha, e in commits.items():
            raw = e["raw"]
            info = raw.get("commit") or {}
            msg = info.get("message") or ""
            title = msg.split("\n", 1)[0]
            login = (raw.get("author") or {}).get("login")
            a = info.get("author") or {}
            bot = is_bot(login, a.get("name"), (raw.get("author") or {}).get("type"), self.cfg.github.bot_logins)
            merge = len(raw.get("parents") or []) > 1 or sha in merge_shas or bool(_MERGE_TITLE.match(title))
            author = self.mapper.github(login, a.get("name"))
            chk = check_commit_message(msg, self.key_pattern)
            msg_keys, msg_us = extract_jira_keys(msg, self.key_pattern), extract_us_ids(msg)

            ref_key = ref_us = ref_src = None
            for n in sorted(pr_of_sha.get(sha, []), reverse=True):  # PR(s) que contêm o commit
                pref = parse_pr_title(pr_by_number[n]["title"], self.key_pattern)
                bref = parse_branch(pr_by_number[n]["head"]["ref"], self.key_pattern)
                ref_key, ref_us = pref.jira_key or bref.jira_key, pref.us_id or bref.us_id
                if ref_key or ref_us:
                    ref_src = "pr"
                    break
            if not (ref_key or ref_us):
                for br in e["branches"]:
                    if br == default:
                        continue
                    bref = parse_branch(br, self.key_pattern)
                    if bref.jira_key or bref.us_id:
                        ref_key, ref_us, ref_src = bref.jira_key, bref.us_id, "branch"
                        break

            on_main = sha in main_literal
            on_main_eq = sha in main_shas and not on_main  # cópia equivalente (rebase) na main, com outro SHA
            via_pr = sha in pr_delivered_shas
            delivered_via = "main" if on_main else ("main_equivalente" if on_main_eq else ("pr" if via_pr else None))
            kind = "bot" if bot else ("merge" if merge else "human")
            rows.append({
                "sha": sha, "url": f"https://github.com/{full}/commit/{sha}", "repo": repo, "author": author.slug,
                "author_login": login, "author_name": a.get("name"), "author_email": a.get("email"),
                "author_mapped": author.mapped, "kind": kind, "is_bot": bot, "is_merge": merge,
                "date": timeutil.parse_ts(a.get("date")), "message": msg, "title": title,
                "us_id": msg_us[0] if msg_us else ref_us, "jira_key": msg_keys[0] if msg_keys else None,
                "jira_keys": msg_keys, "ref_jira_key": ref_key, "ref_us_id": ref_us,   # ref_* = da PR/branch, NÃO da mensagem
                "link_source": "mensagem" if (msg_keys or msg_us) else ref_src,
                "valid_message": (chk.is_valid if kind == "human" else None),
                "message_problems": ",".join(chk.problems) if kind == "human" else "",
                "branches": e["branches"], "branch_label": default if delivered_via == "main" else (e["branches"][0] if e["branches"] else default),
                "pr_numbers": sorted(pr_of_sha.get(sha, [])), "on_main": on_main, "on_main_equivalent": on_main_eq,
                "delivered_via_pr": via_pr, "delivered": delivered_via is not None, "delivered_via": delivered_via,
            })

        # ---- linhas de PR
        pr_rows = []
        for p in prs_raw:
            pref, bref = parse_pr_title(p["title"], self.key_pattern), parse_branch(p["head"]["ref"], self.key_pattern)
            login = (p.get("user") or {}).get("login")
            mc = main_by_sha.get(p.get("merge_commit_sha") or "")
            method = None
            if p.get("merged_at"):
                method = ("merge" if len(mc.get("parents") or []) > 1 else "squash_ou_rebase") if mc else "desconhecido"
            state = "merged" if p.get("merged_at") else p["state"]
            draft = bool(p.get("draft"))
            rv = summarize_reviews(pr_reviews.get(p["number"]), login, self.cfg.github.bot_logins) if p["number"] in pr_reviews else ReviewSummary(False)
            requested = [u.get("login") for u in p.get("requested_reviewers") or [] if u.get("login")] \
                + [f"team:{t.get('slug')}" for t in p.get("requested_teams") or [] if t.get("slug")]
            pr_rows.append({
                "repo": repo, "number": p["number"], "title": p["title"], "author": self.mapper.github(login).slug,
                "author_login": login, "state": state, "draft": bool(p.get("draft")), "head": p["head"]["ref"],
                "head_sha": p["head"]["sha"], "base": p["base"]["ref"], "base_is_default": p["base"]["ref"] == default,
                "created": timeutil.parse_ts(p.get("created_at")), "updated": timeutil.parse_ts(p.get("updated_at")),
                "closed_at": timeutil.parse_ts(p.get("closed_at")), "merged_at": timeutil.parse_ts(p.get("merged_at")),
                "merge_commit_sha": p.get("merge_commit_sha"), "merge_method": method, "url": p["html_url"],
                "us_id": pref.us_id or bref.us_id, "jira_key": pref.jira_key or bref.jira_key, "kind": bref.kind,
                "follows_convention": pref.follows_convention,
                "requested_reviewers": requested, "reviews_known": rv.known, "review_count": rv.review_count,
                "approvals": rv.approvals, "changes_requested": rv.changes_requested, "commented_reviewers": rv.commented,
                "first_review_at": rv.first_review_at, "last_review_at": rv.last_review_at,
                "last_review_state": rv.last_review_state, "review_state": review_state(state, draft, rv),
            })
        return rows, branch_rows, pr_rows

    # ------------------------------------------------------------ entrada
    def fetch(self) -> SourceResult:
        try:
            return self._fetch()
        except Exception as e:  # payload inesperado nunca derruba o app: vira falha controlada (com log)
            return SourceResult.unexpected("GitHub", e, (self.cfg.github.token,))

    def _fetch(self) -> SourceResult:
        g = self.cfg.github
        if not g.token:
            return SourceResult.failed("GitHub", "GITHUB_TOKEN não definido")
        if not g.org or not g.repos:
            return SourceResult.failed("GitHub", "Organização/repositórios não configurados (config.json → github)")
        self._warnings = []
        since_iso = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=g.lookback_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        commits: list[dict] = []
        branches: list[dict] = []
        prs: list[dict] = []
        repo_errors: list[str] = []
        for repo in g.repos:
            try:
                c, b, p = self._fetch_repo(repo, since_iso)
                commits += c
                branches += b
                prs += p
            except AuthError as e:
                return SourceResult.failed("GitHub", friendly(e))
            except ApiError as e:
                repo_errors.append(f"{self.org}/{repo}: {friendly(e)}")
            except Exception as e:  # payload inesperado em UM repositório: os demais continuam (resultado parcial)
                SourceResult.unexpected("GitHub", e, (g.token,))  # registra o traceback no log
                repo_errors.append(f"{self.org}/{repo}: resposta inesperada da API ({type(e).__name__})")
        if len(repo_errors) == len(g.repos):
            return SourceResult.failed("GitHub", *repo_errors)

        df_c = pd.DataFrame(commits, columns=COMMIT_COLS)
        df_b = pd.DataFrame(branches, columns=BRANCH_COLS)
        df_p = pd.DataFrame(prs, columns=PR_COLS)
        if not df_c.empty:
            df_c = df_c.sort_values("date", ascending=False).reset_index(drop=True)
        warnings = repo_errors + list(dict.fromkeys(self._warnings))
        remaining = self.http.rate.get("remaining")
        if remaining is not None and remaining < 100:
            warnings.append(f"Restam só {int(remaining)} requisições no limite do GitHub; evite atualizar de novo agora.")
        stats = {"commits": len(df_c), "branches": int((~df_b["is_default"]).sum()) if not df_b.empty else 0,
                 "prs": len(df_p), "lookback_days": g.lookback_days, "api_calls": self.http.calls,
                 "rate_remaining": remaining, "repos": list(g.repos)}
        return SourceResult("GitHub", GitHubData(df_c, df_b, df_p), warnings=warnings, stats=stats)
