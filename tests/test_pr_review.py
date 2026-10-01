"""MVP / Fase 1 — estado de revisão de PR: só reviews REAIS de outra pessoa contam; falha de leitura = desconhecido."""
import pytest

from domain import pr_review as R
from services.http import ApiError
from tests.fakes import iso
from tests.test_github_service import BR_BACK, gh_commit, gh_pr, routes, run


def rv(state, login="c1dneve", days=1.0, rtype="User"):
    return {"state": state, "user": {"login": login, "type": rtype}, "submitted_at": iso(days)}


def summ(reviews, author="samuelmartins00"):
    return R.summarize_reviews(reviews, author)


def test_no_reviews_read_ok_means_awaiting_review():
    s = summ([])
    assert s.known and s.review_count == 0
    assert R.review_state("open", False, s) == R.AGUARDANDO


def test_unreadable_reviews_are_unknown_never_awaiting():
    s = summ(None)
    assert not s.known and R.review_state("open", False, s) == R.DESCONHECIDO


def test_author_bots_and_pending_reviews_do_not_count():
    s = summ([rv("APPROVED", login="samuelmartins00"), rv("APPROVED", login="copilot-pull-request-reviewer[bot]", rtype="Bot"),
              rv("CHANGES_REQUESTED", login="c1dneve") | {"state": "PENDING"}])
    assert s.review_count == 0 and R.review_state("open", False, s) == R.AGUARDANDO


def test_comment_only_is_commented_not_approved():
    s = summ([rv("COMMENTED")])
    assert R.review_state("open", False, s) == R.COMENTADA and s.commented == 1 and s.approvals == 0


def test_changes_requested_wins_and_a_later_comment_does_not_undo_it():
    s = summ([rv("CHANGES_REQUESTED", days=3), rv("COMMENTED", days=1)])
    assert R.review_state("open", False, s) == R.MUDANCAS and s.changes_requested == 1 and s.commented == 0


def test_latest_decision_per_reviewer_wins_and_dismissed_clears():
    assert R.review_state("open", False, summ([rv("CHANGES_REQUESTED", days=3), rv("APPROVED", days=1)])) == R.APROVADA
    s = summ([rv("APPROVED", days=3), rv("DISMISSED", days=1)])
    assert R.review_state("open", False, s) == R.AGUARDANDO and s.review_count == 2   # anulada: precisa de nova revisão


def test_draft_merged_and_closed_states_take_precedence():
    s = summ([])
    assert R.review_state("open", True, s) == R.RASCUNHO
    assert R.review_state("merged", False, s) == R.MERGEADA and R.review_state("closed", False, s) == R.FECHADA


def test_review_timestamps_are_tz_aware_local():
    s = summ([rv("COMMENTED", days=3), rv("APPROVED", days=1)])
    assert str(s.first_review_at.tz) == "America/Sao_Paulo" and s.first_review_at < s.last_review_at
    assert s.last_review_state == "approved"


# ---------------------------------------------------------------- integração com o serviço
def scenario(reviews=None, **pr_kw):
    c1 = gh_commit("c1", "feat(JH-101): implementar validação do cadastro")
    pr = gh_pr(7, BR_BACK, "c1", **pr_kw)
    pr["requested_reviewers"] = [{"login": "c1dneve"}]
    pr["requested_teams"] = [{"slug": "backend"}]
    return routes([], [("main", "m"), (BR_BACK, "c1")], prs_open=[pr], pr_commits={7: [c1]}, reviews={7: reviews} if reviews is not None else None,
                  compares={f"main...{BR_BACK}": {"ahead_by": 1, "behind_by": 0, "status": "ahead", "commits": [c1]}})


def test_service_marks_open_pr_without_reviews_as_awaiting(settings, mapper):
    res, _ = run(settings, mapper, scenario())
    p = res.data.prs.iloc[0]
    assert p["review_state"] == R.AGUARDANDO and p["reviews_known"] and p["requested_reviewers"] == ["c1dneve", "team:backend"]


def test_service_reads_real_reviews(settings, mapper):
    res, http = run(settings, mapper, scenario(reviews=[rv("COMMENTED", days=1.5), rv("APPROVED", days=0.5)]))
    p = res.data.prs.iloc[0]
    assert p["review_state"] == R.APROVADA and p["approvals"] == 1 and p["review_count"] == 2
    assert p["first_review_at"] < p["last_review_at"] and http.urls("/pulls/7/reviews")


def test_service_does_not_assume_awaiting_when_reviews_fail(settings, mapper):
    res, _ = run(settings, mapper, scenario(reviews=ApiError("GitHub", "boom", status=500)))
    p = res.data.prs.iloc[0]
    assert p["review_state"] == R.DESCONHECIDO and not p["reviews_known"]
    assert any("reviews indisponíveis" in w for w in res.warnings)


def test_service_merged_pr_keeps_review_facts(settings, mapper):
    c1 = gh_commit("c1", "feat(JH-101): implementar validação do cadastro")
    sq = gh_commit("s1", "[JH-123] US2.1 — Cadastro (#42)", days=1)
    pr = gh_pr(42, BR_BACK, "c1", state="closed", merged=True, merge_sha="s1")
    rts = routes([sq], [("main", "s1")], prs_closed=[pr], pr_commits={42: [c1]}, reviews={42: [rv("APPROVED", days=2)]})
    res, _ = run(settings, mapper, rts)
    p = res.data.prs.iloc[0]
    assert p["review_state"] == R.MERGEADA and p["approvals"] == 1     # mergeada COM revisão; sem revisão teria review_count 0


def test_closed_unmerged_pr_does_not_fetch_reviews(settings, mapper):
    pr = gh_pr(9, "feature/backend/JH-9-US1.1-x", "z", state="closed")
    res, http = run(settings, mapper, routes([], [("main", "m")], prs_closed=[pr]))
    p = res.data.prs.iloc[0]
    assert p["review_state"] == R.FECHADA and not http.urls("/pulls/9/reviews")


@pytest.mark.parametrize("col", ["requested_reviewers", "review_state", "first_review_at"])
def test_empty_github_frames_have_review_columns(col):
    from services.github import GitHubData
    assert col in GitHubData.empty().prs.columns


def test_reviews_are_one_call_per_open_or_merged_pr_never_per_commit_or_closed_pr(settings, mapper):
    cs = [gh_commit(f"c{i}", f"feat(JH-101): parte {i} do cadastro") for i in range(5)]
    open_pr = gh_pr(7, BR_BACK, "c0")
    closed_pr = gh_pr(9, "feature/backend/JH-9-US1.1-x", "z", state="closed")
    res, http = run(settings, mapper, routes([], [("main", "m"), (BR_BACK, "c0")], prs_open=[open_pr], prs_closed=[closed_pr],
                                             pr_commits={7: cs}, compares={f"main...{BR_BACK}": {"ahead_by": 5, "behind_by": 0, "status": "ahead", "commits": cs}}))
    assert res.ok and len(http.urls("/reviews")) == 1 and http.urls("/pulls/7/reviews")
