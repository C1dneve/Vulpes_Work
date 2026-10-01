"""As verificações t9/t10 do validador real (tools/validate_real_apis.py) devem rodar e dar veredito coerente com respostas simuladas.
Como o validador real exige credenciais do usuário, este teste garante que ele não quebra na primeira execução."""
import importlib.util
import re
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("validate_real_apis", Path(__file__).resolve().parent.parent / "tools" / "validate_real_apis.py")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)


class Canned(V.Api):
    def __init__(self, routes):
        self.routes = routes

    def get(self, url, params=None):
        for pat, (status, data) in self.routes:
            if re.search(pat, url):
                return V.Resp(status, data(url, params) if callable(data) else data, {}, url, 0.0)
        return V.Resp(404, None, {}, url, 0.0, "rota não simulada")


def issue(key, sub=False, sp=None, extra=None):
    f = {"issuetype": {"name": "Sub-task" if sub else "Story", "subtask": sub}, "status": {"name": "Em andamento"}, "duedate": None,
         "priority": {"name": "High"}, "issuelinks": [], "flagged": False}
    if sp is not None:
        f["customfield_10016"] = sp
    f.update(extra or {})
    return {"key": key, "fields": f}


def jira_routes(catalog, issues, board_cfg=None, changelog=None):
    return [(r"/rest/api/3/field$", (200, catalog)), (r"/configuration$", (200, board_cfg or {})),
            (r"/board/7/issue$", (200, {"issues": issues, "total": len(issues), "isLast": True})),
            (r"/changelog$", (200, {"values": changelog or []}))]


SP_FIELD = {"id": "customfield_10016", "name": "Story point estimate", "custom": True}
FLAG_FIELD = {"id": "customfield_10021", "name": "Flagged", "custom": True}


def test_t9_confirms_story_points_and_reads_sprint_events():
    sprint_ev = [{"items": [{"field": "Sprint", "from": "4", "to": "4, 5", "fromString": "Sprint 4", "toString": "Sprint 4, Sprint 5"}]}]
    J = Canned(jira_routes([SP_FIELD, FLAG_FIELD], [issue("JH-1", sp=5), issue("JH-2", sub=True)], changelog=sprint_ev))
    r = V.t9_mvp_jira(J, "https://x.atlassian.net", "7", "summary")
    assert r["status"] == V.OK and r["story_points"]["customfield_10016"]["stories"] == "1/1"
    assert r["flagged_fields"] == ["customfield_10021"] and r["evento_sprint"]["to"] == "4, 5" and r["changelog_fields"]["Sprint"] >= 1


def test_t9_reports_missing_story_points_field_as_a_divergence_not_a_pass():
    r = V.t9_mvp_jira(Canned(jira_routes([{"id": "summary", "name": "Summary", "custom": False}], [issue("JH-1")])),
                       "https://x.atlassian.net", "7", "summary")
    assert r["status"] == V.DIV and "ausente" in r["evidence"]


def test_t9_field_without_values_is_partial_and_ambiguous_fields_use_the_board():
    r = V.t9_mvp_jira(Canned(jira_routes([SP_FIELD], [issue("JH-1")])), "https://x.atlassian.net", "7", "summary")
    assert r["status"] == V.PART
    sp2 = {"id": "customfield_10026", "name": "Story Points", "custom": True}
    cfg = {"estimation": {"field": {"fieldId": "customfield_10026", "displayName": "Story Points"}}}
    r = V.t9_mvp_jira(Canned(jira_routes([SP_FIELD, sp2], [issue("JH-1", sp=3)], board_cfg=cfg)), "https://x.atlassian.net", "7", "summary")
    assert r["status"] == V.OK and r["board_estimation"] == "customfield_10026" and "desempate" in r["evidence"]


def test_t9_unavailable_field_catalog_is_unknown():
    r = V.t9_mvp_jira(Canned([(r"/rest/api/3/field$", (403, None))]), "https://x.atlassian.net", "7", "summary")
    assert r["status"] == V.UNK


def pr(n, state="open", merged=None):
    return {"number": n, "state": state, "merged_at": merged, "draft": False, "user": {"login": "a"}, "requested_reviewers": [], "requested_teams": []}


def test_t10_reviews_ok_with_real_looking_payload():
    rv = [{"id": 1, "state": "APPROVED", "submitted_at": "2026-09-25T10:00:00Z", "user": {"login": "b", "type": "User"}}]
    G = Canned([(r"/pulls$", (200, [pr(1), pr(2, "closed", "2026-09-20T10:00:00Z")])), (r"/pulls/1/reviews$", (200, rv)), (r"/pulls/2/reviews$", (200, []))])
    r = V.t10_gh_reviews(G, "https://api.github.com/repos/o/r", 4)
    assert r["status"] == V.OK and r["estados_review"] == {"APPROVED": 1} and all(r["chaves_listagem"].values())


def test_t10_endpoint_forbidden_is_a_divergence_and_no_reviews_is_partial():
    G = Canned([(r"/pulls$", (200, [pr(1)])), (r"/pulls/1/reviews$", (403, None))])
    assert V.t10_gh_reviews(G, "https://api.github.com/repos/o/r", 4)["status"] == V.DIV
    G = Canned([(r"/pulls$", (200, [pr(1)])), (r"/pulls/1/reviews$", (200, []))])
    assert V.t10_gh_reviews(G, "https://api.github.com/repos/o/r", 4)["status"] == V.PART
    assert V.t10_gh_reviews(Canned([(r"/pulls$", (500, None))]), "https://api.github.com/repos/o/r", 4)["status"] == V.UNK


@pytest.mark.parametrize("name", ["t9_mvp_jira", "t10_gh_reviews"])
def test_new_checks_are_wired_into_the_tool(name):
    assert hasattr(V, name)
    src = (
    Path(__file__).resolve().parent.parent / "tools" / "validate_real_apis.py"
    ).read_text(encoding="utf-8")
    assert name.split("_")[0] in src and '"t9"' in src and '"t10"' in src
