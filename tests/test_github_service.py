"""GitHub: entrega via PR merged (squash/rebase), paginação total, bots, merge commits, autores."""
import pandas as pd
import pytest

from services.github import GitHubService
from services.http import AuthError, NotFound
from tests.fakes import FakeHttp, iso, paged_list

BR_BACK = "feature/backend/JH-123-US2.1-cadastro"
BR_FRONT = "feature/frontend/JH-123-US2.1-cadastro"


def gh_commit(sha, msg, login="samuelmartins00", name="Samuel Martins", email="s@x", days=3, parents=1, ctype="User"):
    return {"sha": sha, "parents": [{"sha": f"p{i}"} for i in range(parents)],
            "author": {"login": login, "type": ctype} if login else None,
            "commit": {"message": msg, "author": {"name": name, "email": email, "date": iso(days)}}}


def gh_pr(number, head, head_sha, state="open", merged=False, base="main", title=None, merge_sha=None, days=2):
    return {"number": number, "title": title or f"[JH-123] US2.1 — Cadastro (#{number})", "state": state,
            "user": {"login": "samuelmartins00"}, "draft": False, "html_url": f"https://github.com/Team/repo/pull/{number}",
            "head": {"ref": head, "sha": head_sha, "repo": {"full_name": "Team/repo"}}, "base": {"ref": base},
            "created_at": iso(days + 1), "updated_at": iso(days), "closed_at": iso(days) if state == "closed" else None,
            "merged_at": iso(days) if merged else None, "merge_commit_sha": merge_sha}


def routes(main, branches, prs_open=(), prs_closed=(), pr_commits=None, compares=None, extra=(), reviews=None):
    pr_commits = pr_commits or {}
    reviews = reviews or {}
    compares = compares or {}

    def pulls(url, params):
        src = prs_open if params["state"] == "open" else prs_closed
        return paged_list(list(src))(url, params)

    def compare(url, params):
        basehead = url.split("/compare/")[1]
        r = compares[basehead]
        commits = r["commits"]
        n, page = params.get("per_page", 100), params.get("page", 1)
        return {**r, "total_commits": len(commits), "commits": commits[(page - 1) * n: page * n]}

    r = [(r"/repos/Team/repo$", {"default_branch": "main"}),
         (r"/repos/Team/repo/branches$", paged_list([{"name": n, "commit": {"sha": s}} for n, s in branches])),
         (r"/repos/Team/repo/pulls$", pulls),
         (r"/repos/Team/repo/commits$", paged_list(main)),
         (r"/repos/Team/repo/compare/", compare)]
    for number, lst in pr_commits.items():
        r.append((rf"/repos/Team/repo/pulls/{number}/commits$", paged_list(lst)))
    for number, lst in reviews.items():   # lst pode ser uma Exception (API de reviews indisponível)
        r.append((rf"/repos/Team/repo/pulls/{number}/reviews$", lst if isinstance(lst, Exception) else paged_list(lst)))
    r.append((r"/repos/Team/repo/pulls/\d+/reviews$", paged_list([])))   # padrão: lido e sem reviews
    return list(extra) + r


def run(settings, mapper, rts):
    http = FakeHttp(rts)
    res = GitHubService(http, settings, mapper).fetch()
    return res, http


def by_sha(df):
    return df.set_index("sha")


# ---------------------------------------------------------------- squash merge (o bug original)
def squash_scenario(with_branch=True, branch_head="c3", compare_post=None):
    c1 = gh_commit("c1", "feat(JH-101): implementar validação do cadastro de cliente")
    c2 = gh_commit("c2", "feat(JH-102): criar endpoint de consulta de clientes")
    c3 = gh_commit("c3", "feat(JH-103): adicionar testes do formulário")
    squash = gh_commit("s1", "[JH-123] US2.1 — Cadastro (#42)\n\n* feat(JH-101): a\n* feat(JH-102): b", days=1)
    older = gh_commit("m0", "chore: configuração inicial do repositório", days=20)
    pr = gh_pr(42, BR_BACK, "c3", state="closed", merged=True, merge_sha="s1")
    branches = [("main", "s1")] + ([(BR_BACK, branch_head)] if with_branch else [])
    return routes([squash, older], branches, prs_closed=[pr], pr_commits={42: [c1, c2, c3]},
                  compares=compare_post or {})


def test_squash_merged_commits_are_delivered_even_though_sha_is_not_on_main(settings, mapper):
    res, _ = run(settings, mapper, squash_scenario(with_branch=False))
    assert res.ok
    df = by_sha(res.data.commits)
    for sha in ("c1", "c2", "c3"):
        assert df.loc[sha, "delivered"], sha           # antes: on_main=False para sempre
        assert df.loc[sha, "delivered_via"] == "pr"
        assert df.loc[sha, "pr_numbers"] == [42]
    assert df.loc["m0", "delivered_via"] == "main"


def test_squash_commit_itself_is_a_merge_not_human_activity(settings, mapper):
    res, _ = run(settings, mapper, squash_scenario(with_branch=False))
    df = by_sha(res.data.commits)
    assert df.loc["s1", "kind"] == "merge" and df.loc["s1", "is_merge"]
    assert set(df[df["kind"] == "human"].index) == {"c1", "c2", "c3", "m0"}


def test_deleted_branch_work_is_still_visible_through_the_pr(settings, mapper):
    res, _ = run(settings, mapper, squash_scenario(with_branch=False))
    assert BR_BACK not in set(res.data.branches["branch"])   # branch apagada após o merge
    assert {"c1", "c2", "c3"} <= set(res.data.commits["sha"])  # mas o trabalho não some do dashboard


def test_subtask_keys_come_from_commits_and_story_key_from_pr(settings, mapper):
    res, _ = run(settings, mapper, squash_scenario(with_branch=False))
    df = by_sha(res.data.commits)
    assert [df.loc[s, "jira_key"] for s in ("c1", "c2", "c3")] == ["JH-101", "JH-102", "JH-103"]
    assert df.loc["c1", "us_id"] == "US2.1"   # herdado do título da PR
    assert df.loc["c1", "link_source"] == "mensagem"


def test_branch_kept_after_squash_is_delivered_and_needs_no_compare(settings, mapper):
    res, http = run(settings, mapper, squash_scenario(with_branch=True, branch_head="c3"))
    b = res.data.branches.set_index("branch").loc[BR_BACK]
    assert b["delivered"] and b["pending_commits"] == 0 and b["pr_state"] == "merged" and b["kind"] == "backend"
    assert http.urls("/compare/") == []   # evita chamadas desnecessárias


def test_commit_pushed_after_merge_stays_pending(settings, mapper):
    c4 = gh_commit("c4", "feat(JH-104): ajustar mensagem de erro do cadastro", days=0.5)
    rts = squash_scenario(with_branch=True, branch_head="c4",
                          compare_post={f"c3...{BR_BACK}": {"ahead_by": 1, "behind_by": 0, "status": "ahead", "commits": [c4]}})
    res, http = run(settings, mapper, rts)
    b = res.data.branches.set_index("branch").loc[BR_BACK]
    assert b["pending_commits"] == 1 and not b["delivered"]
    df = by_sha(res.data.commits)
    assert not df.loc["c4", "delivered"] and df.loc["c1", "delivered"]
    assert http.urls("/compare/c3...")  # compara a partir do head da PR, não da main (senão contaria o squash inteiro)


# ---------------------------------------------------------------- PR aberta, backend x frontend
def test_open_prs_backend_and_frontend_are_kept_apart(settings, mapper):
    b1 = gh_commit("b1", "feat(JH-101): implementar validação do cadastro de cliente")
    f1 = gh_commit("f1", "feat(JH-104): criar formulário de cadastro de cliente", login="c1dneve", name="Cid")
    f2 = gh_commit("f2", "feat(JH-105): integrar formulário com a API de clientes", login="c1dneve", name="Cid")
    rts = routes([gh_commit("m0", "chore: configuração inicial do repositório", days=30)],
                 [("main", "m0"), (BR_BACK, "b1"), (BR_FRONT, "f2")],
                 prs_open=[gh_pr(42, BR_BACK, "b1"), gh_pr(43, BR_FRONT, "f2")],
                 pr_commits={42: [b1], 43: [f1, f2]},
                 compares={f"main...{BR_BACK}": {"ahead_by": 1, "behind_by": 0, "status": "ahead", "commits": [b1]},
                           f"main...{BR_FRONT}": {"ahead_by": 2, "behind_by": 0, "status": "ahead", "commits": [f1, f2]}})
    res, _ = run(settings, mapper, rts)
    br = res.data.branches.set_index("branch")
    assert (br.loc[BR_BACK, "kind"], br.loc[BR_BACK, "pending_commits"], br.loc[BR_BACK, "pr"]) == ("backend", 1, "#42")
    assert (br.loc[BR_FRONT, "kind"], br.loc[BR_FRONT, "pending_commits"], br.loc[BR_FRONT, "pr_state"]) == ("frontend", 2, "open")
    assert not res.data.commits[res.data.commits["sha"].isin(["b1", "f1", "f2"])]["delivered"].any()
    assert br.loc[BR_FRONT, "last_author"] == "cid-daniel-neves-d-oliveira"


# ---------------------------------------------------------------- bots, merges, autores
def test_bots_merge_commits_and_unmapped_authors(settings, mapper):
    main = [
        gh_commit("h1", "feat(JH-1): implementar cadastro de clientes completo"),
        gh_commit("bot", "chore(deps): bump requests from 2.31 to 2.32", login="dependabot[bot]", name="dependabot[bot]", ctype="Bot"),
        gh_commit("mrg", "Merge branch 'main' into feature/x", parents=2),
        gh_commit("unm", "feat(JH-2): criar listagem de clientes cadastrados", login=None, name="Pedro P.", email="pp@x"),
    ]
    res, _ = run(settings, mapper, routes(main, [("main", "h1")]))
    df = by_sha(res.data.commits)
    assert (df.loc["bot", "kind"], df.loc["bot", "is_bot"]) == ("bot", True)
    assert df.loc["mrg", "kind"] == "merge"
    assert df.loc["h1", "kind"] == "human" and df.loc["h1", "author"] == "samuel-martins" and df.loc["h1", "author_mapped"]
    assert df.loc["unm", "kind"] == "human" and not df.loc["unm", "author_mapped"]
    from domain.people import unmapped_authors
    assert unmapped_authors(res.data.commits)["author_name"].tolist() == ["Pedro P."]


def test_commit_message_validation_flags(settings, mapper):
    main = [gh_commit("ok", "feat(JH-1): implementar cadastro de clientes completo"),
            gh_commit("nokey", "ajustes gerais"), gh_commit("gen", "feat(JH-3): fix")]
    df = by_sha(run(settings, mapper, routes(main, [("main", "ok")]))[0].data.commits)
    assert df.loc["ok", "valid_message"] and not df.loc["nokey", "valid_message"]
    assert "sem_jira_key" in df.loc["nokey", "message_problems"]
    assert "descricao_generica" in df.loc["gen", "message_problems"]


def test_us_id_in_message_is_not_confused_by_lookalike_words(settings, mapper):
    df = by_sha(run(settings, mapper, routes([gh_commit("x", "fix status 1.2 e bonus 2.5 no relatório mensal")],
                                              [("main", "x")]))[0].data.commits)
    assert df.loc["x", "us_id"] is None and df.loc["x", "link_source"] is None


# ---------------------------------------------------------------- rebase: cópia na main não conta duas vezes
def test_rebase_copy_on_main_is_not_double_counted(settings, mapper):
    orig = gh_commit("p1", "feat(JH-101): implementar validação do cadastro de cliente", days=3)
    copy = gh_commit("r1", "feat(JH-101): implementar validação do cadastro de cliente", days=3)  # mesmo autor/data/título
    copy["commit"]["author"]["date"] = orig["commit"]["author"]["date"]
    rts = routes([copy], [("main", "r1")], prs_closed=[gh_pr(9, "feature/x", "p1", state="closed", merged=True, merge_sha="r1")],
                 pr_commits={9: [orig]})
    df = run(settings, mapper, rts)[0].data.commits
    assert len(df) == 1 and df.iloc[0]["delivered"]


# ---------------------------------------------------------------- paginação
def test_no_artificial_limit_600_commits_on_main(settings, mapper):
    main = [gh_commit(f"s{i:04d}", f"feat(JH-1): implementar item numero {i}", days=1 + i / 1000) for i in range(600)]
    res, http = run(settings, mapper, routes(main, [("main", "s0000")]))
    assert len(res.data.commits) == 600     # antes: 5 páginas x 100 = 500
    assert len(http.urls("/commits")) == 7  # 6 páginas cheias + 1 vazia... termina na página incompleta


def test_pr_listing_paginates_open_prs_and_stops_closed_at_window(settings, mapper):
    open_prs = [gh_pr(i, f"feature/b{i}", f"h{i}", days=100) for i in range(1, 121)]   # 120 abertas ANTIGAS: devem vir todas
    old_closed = [gh_pr(500 + i, f"feature/o{i}", f"o{i}", state="closed", merged=True, days=200) for i in range(5)]
    rts = routes([gh_commit("m", "chore: configuração inicial do repositório")], [("main", "m")],
                 prs_open=open_prs, prs_closed=old_closed,
                 pr_commits={i: [] for i in range(1, 121)})
    res, _ = run(settings, mapper, rts)
    prs = res.data.prs
    assert len(prs[prs["state"] == "open"]) == 120   # PR aberta há muito tempo não some (auditoria precisa dela)
    assert prs[prs["state"] == "merged"].empty       # fechadas fora da janela de 90 dias ficam de fora


def test_compare_is_paginated(settings, mapper):
    many = [gh_commit(f"k{i:03d}", f"feat(JH-1): implementar parte numero {i}") for i in range(230)]
    rts = routes([gh_commit("m", "chore: configuração inicial do repositório")], [("main", "m"), (BR_BACK, "k229")],
                 compares={f"main...{BR_BACK}": {"ahead_by": 230, "behind_by": 0, "status": "ahead", "commits": many}})
    res, _ = run(settings, mapper, rts)
    assert res.data.branches.set_index("branch").loc[BR_BACK, "pending_commits"] == 230
    assert len(res.data.commits[~res.data.commits["delivered"]]) == 230


# ---------------------------------------------------------------- erros
def test_auth_error_is_failure_not_empty_dataframe(settings, mapper):
    res, _ = run(settings, mapper, [(r"/repos/Team/repo$", AuthError("GitHub", "Bad credentials", 401))])
    assert not res.ok and res.data is None
    assert "falha de autenticação" in res.errors[0]


def test_one_repo_failing_is_partial_not_total(tmp_path, mapper):
    import json

    from settings import load_settings
    from tests.conftest import ENV, MAPPING
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"github": {"org": "Team", "repos": ["repo", "gone"]}, "dev_mapping": MAPPING}))
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    rts = routes([gh_commit("m", "chore: configuração inicial do repositório")], [("main", "m")],
                 extra=[(r"/repos/Team/gone$", NotFound("GitHub", "Not Found", 404))])
    res, _ = run(s, mapper, rts)
    assert res.ok and res.partial and len(res.data.commits) == 1
    assert "Team/gone" in res.warnings[0]


def test_all_repos_failing_is_error(settings, mapper):
    res, _ = run(settings, mapper, [(r"/repos/Team/repo$", NotFound("GitHub", "Not Found", 404))])
    assert not res.ok and res.data is None


def test_missing_token_is_error(tmp_path, mapper):
    from settings import load_settings
    s = load_settings(env_path=tmp_path / ".env", config_path=tmp_path / "nope.json", environ={})
    res = GitHubService(FakeHttp([]), s, mapper).fetch()
    assert not res.ok and "GITHUB_TOKEN" in res.errors[0]


def test_low_rate_limit_produces_warning(settings, mapper):
    http = FakeHttp(routes([gh_commit("m", "chore: configuração inicial do repositório")], [("main", "m")]))
    http.rate["remaining"] = 42
    res = GitHubService(http, settings, mapper).fetch()
    assert any("42" in w for w in res.warnings)


def test_dates_are_localized(settings, mapper):
    df = run(settings, mapper, routes([gh_commit("m", "chore: configuração inicial do repositório")], [("main", "m")]))[0].data.commits
    assert str(df["date"].dt.tz) == "America/Sao_Paulo"


@pytest.mark.parametrize("field", ["created", "updated"])
def test_pr_dates_are_tz_aware(settings, mapper, field):
    rts = routes([gh_commit("m", "chore: configuração inicial do repositório")], [("main", "m")],
                 prs_open=[gh_pr(1, "feature/x", "h1")], pr_commits={1: []})
    prs = run(settings, mapper, rts)[0].data.prs
    assert prs[field].dt.tz is not None and isinstance(prs.iloc[0][field], pd.Timestamp)


# ---------------------------------------------------------------- P0.1: chave própria x referência herdada da PR/branch
def test_key_from_pr_or_branch_is_kept_apart_from_the_commit_own_key(settings, mapper):
    res, _ = run(settings, mapper, squash_scenario(with_branch=False))
    df = by_sha(res.data.commits)
    assert df.loc["c1", "jira_key"] == "JH-101"                    # da própria mensagem
    assert df.loc["c1", "ref_jira_key"] == "JH-123"                # da PR [JH-123]: chave da STORY, não da Subtask
    assert df.loc["c1", "ref_us_id"] == "US2.1"


def test_commit_without_key_does_not_inherit_the_story_key_as_its_own(settings, mapper):
    keyless = gh_commit("k1", "ajustes no formulário de cadastro de clientes")
    squash = gh_commit("s1", "[JH-123] US2.1 — Cadastro (#42)", days=1)
    pr = gh_pr(42, BR_BACK, "k1", state="closed", merged=True, merge_sha="s1")
    res, _ = run(settings, mapper, routes([squash], [("main", "s1")], prs_closed=[pr], pr_commits={42: [keyless]}))
    row = by_sha(res.data.commits).loc["k1"]
    assert row["jira_key"] is None and row["ref_jira_key"] == "JH-123"
    assert row["link_source"] == "pr" and not row["valid_message"]   # a regra "sem chave = inválido" continua valendo


# ---------------------------------------------------------------- on_main x delivered_via_pr
def test_squash_commits_are_delivered_via_pr_but_not_on_main(settings, mapper):
    res, _ = run(settings, mapper, squash_scenario(with_branch=False))
    df = by_sha(res.data.commits)
    for sha in ("c1", "c2", "c3"):
        assert not df.loc[sha, "on_main"] and not df.loc[sha, "on_main_equivalent"]
        assert df.loc[sha, "delivered_via_pr"] and df.loc[sha, "delivered"] and df.loc[sha, "delivered_via"] == "pr"


def test_commit_literally_on_main_is_not_delivered_via_pr(settings, mapper):
    direct = gh_commit("d1", "fix(JH-101): corrigir cálculo do total do pedido", days=1)
    res, _ = run(settings, mapper, routes([direct], [("main", "d1")]))
    row = by_sha(res.data.commits).loc["d1"]
    assert row["on_main"] and not row["delivered_via_pr"] and row["delivered_via"] == "main"


def test_rebase_twin_is_not_confused_with_the_literal_sha_on_main(settings, mapper):
    orig = gh_commit("p1", "feat(JH-101): implementar validação do cadastro de cliente", days=3)
    copy = gh_commit("r1", "feat(JH-101): implementar validação do cadastro de cliente", days=3)
    copy["commit"]["author"]["date"] = orig["commit"]["author"]["date"]
    rts = routes([copy], [("main", "r1")], prs_closed=[gh_pr(9, "feature/x", "p1", state="closed", merged=True, merge_sha="r1")],
                 pr_commits={9: [orig]})
    df = run(settings, mapper, rts)[0].data.commits
    row = df.iloc[0]
    assert len(df) == 1 and row["sha"] == "p1"
    assert not row["on_main"]                                  # o SHA p1 NÃO está na main
    assert row["on_main_equivalent"] and row["delivered_via_pr"]
    assert row["delivered"] and row["delivered_via"] == "main_equivalente"


def test_commit_of_a_still_open_pr_is_neither_on_main_nor_delivered(settings, mapper):
    c = gh_commit("w1", "feat(JH-101): implementar validação do cadastro de cliente", days=1)
    pr = gh_pr(7, BR_BACK, "w1", state="open")
    res, _ = run(settings, mapper, routes([], [("main", "m0"), (BR_BACK, "w1")], prs_open=[pr], pr_commits={7: [c]},
                                           compares={f"main...{BR_BACK}": {"ahead_by": 1, "behind_by": 0, "status": "ahead", "commits": [c]}}))
    row = by_sha(res.data.commits).loc["w1"]
    assert not row["on_main"] and not row["delivered_via_pr"] and not row["delivered"] and row["delivered_via"] is None


# ---------------------------------------------------------------- P0.5: payload inesperado
def test_unexpected_payload_is_a_controlled_failure_not_a_traceback(settings, mapper):
    rts = [(r"/repos/Team/repo/branches$", lambda u, p: [{"name": "feature/x"}])] + routes([], [("main", "m1")])   # branch sem "commit"
    res, _ = run(settings, mapper, rts)
    assert res.status == "error" and res.data is None
    assert "KeyError" in res.errors[0] and settings.github.token not in res.errors[0]


def test_unexpected_error_outside_the_repo_loop_is_controlled_and_never_leaks_the_token(settings, mapper, monkeypatch):
    svc = GitHubService(FakeHttp([]), settings, mapper)

    def boom():
        raise RuntimeError(f"falhou com Authorization: Bearer {settings.github.token}")
    monkeypatch.setattr(svc, "_fetch", boom)     # falha fora do laço por repositório: só a rede de segurança de fetch() pega
    res = svc.fetch()
    assert res.status == "error" and "RuntimeError" in res.errors[0]
    assert settings.github.token not in " ".join(res.errors) and "***" in res.errors[0]


def test_malformed_rows_after_the_repo_loop_do_not_crash(settings, mapper, monkeypatch):
    svc = GitHubService(FakeHttp([]), settings, mapper)
    monkeypatch.setattr(svc, "_fetch_repo", lambda repo, since: ([1], [], []))   # linha que não é dict: erro ao montar o DataFrame
    res = svc.fetch()
    assert res.status == "error" and res.data is None


def test_unexpected_error_in_one_repo_keeps_the_others(settings, mapper, monkeypatch):
    from dataclasses import replace
    two = replace(settings, github=replace(settings.github, repos=("bad", "good")))
    svc = GitHubService(FakeHttp([]), two, mapper)

    def fetch_repo(repo, since):
        if repo == "bad":
            raise KeyError("commit")
        return [], [{"repo": repo, "branch": "main", "is_default": True, "kind": None, "head_sha": None, "ahead_main": 0,
                     "behind_main": 0, "pending_commits": 0, "delivered": True, "last_commit": pd.NaT, "last_author": "",
                     "us_id": None, "jira_key": None, "follows_convention": False, "pr": None, "pr_state": None,
                     "pr_numbers": [], "compare_status": "default"}], []
    monkeypatch.setattr(svc, "_fetch_repo", fetch_repo)
    res = svc.fetch()
    assert res.status == "partial" and res.data is not None
    assert any("bad" in w and "KeyError" in w for w in res.warnings)
