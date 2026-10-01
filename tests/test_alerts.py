"""MVP / Fase 5 — alertas operacionais: regra, severidade e (principalmente) ausência de falso positivo."""
import pandas as pd

from domain import alerts as A
from domain import statuses as S
from domain.sprint_view import enrich_items
from domain.thresholds import Thresholds
from tests.test_sprint_view import CHANGELOG_COLS, commit, story, task, ts

NOW = pd.Timestamp("2026-09-30 10:00", tz="America/Sao_Paulo")       # quarta
TH = Thresholds()
KNOWN = {"JH-100", "JH-101", "JH-102", "JH-103"}
GH_START = ts("2026-07-01")


def pr(number=42, state="open", review="aguardando_revisao", kind="backend", key="JH-100", created="2026-09-29 10:00", merged=None,
       author="ana", draft=False, **kw):
    return {"number": number, "title": f"[{key}] US2.1 — Cadastro", "author": author, "state": state, "created": ts(created),
            "merged_at": ts(merged) if merged else pd.NaT, "review_state": review, "reviews_known": review != "desconhecido",
            "review_count": 0, "last_review_at": pd.NaT, "jira_key": key, "us_id": "US2.1", "kind": kind, "base_is_default": True,
            "url": f"https://github.com/x/y/pull/{number}", "draft": draft, **kw}


def run(tasks, prs=(), commits=(), stories=None, github_ok=True, sprint=None, github_since=GH_START, now=NOW):
    items = pd.DataFrame(tasks)
    st = pd.DataFrame(stories if stories is not None else [story("JH-100", "US2.1")])
    cm = pd.DataFrame(commits) if commits else pd.DataFrame(columns=["sha", "jira_key", "ref_jira_key", "us_id", "author", "date", "delivered", "kind"])
    p = pd.DataFrame(prs) if prs else pd.DataFrame(columns=list(pr()))
    empty_cl = pd.DataFrame(columns=CHANGELOG_COLS)
    empty_wl = pd.DataFrame(columns=["subtask_key", "started", "author", "time_spent_h"])
    ie = enrich_items(items, empty_cl, empty_wl, cm, KNOWN, now, TH)
    return A.build_alerts(ie, st, items, cm, p, known_keys=KNOWN, now=now, th=TH, github_ok=github_ok, github_since=github_since, sprint=sprint)


def rules(rep, rule=None):
    df = rep.alerts
    return df if rule is None else df[df["rule"] == rule]


def t(key="JH-101", **kw):
    return task(key, "JH-100", kw.pop("who", "ana"), code=kw.pop("code", "BE-01"),
                **{"created": ts("2026-09-21"), "subtask_summary": f"Task {key}", **kw})


# ---------------------------------------------------------------- Jira
def test_blocked_task_is_high_severity_with_provable_reason_only():
    rep = run([t(flagged=True, flagged_since=ts("2026-09-29 10:00"), blocked_by=["JH-55 — Liberar ambiente"]), t("JH-102", flagged=True)])
    b = rules(rep, "bloqueada").set_index("key")
    assert b.loc["JH-101", "severity"] == "alta" and "Bloqueada por JH-55 — Liberar ambiente" in b.loc["JH-101", "detail"]
    assert "há 1d" in b.loc["JH-101", "detail"]
    assert "motivo não informado no Jira" in b.loc["JH-102", "detail"]          # sem fonte confiável: não inventa motivo


def test_overdue_is_high_and_done_overdue_is_not_an_alert():
    rep = run([t(due="2026-09-25"), t("JH-102", group=S.CONCLUIDA, due="2026-09-01")])
    a = rules(rep, "atrasada")
    assert a["key"].tolist() == ["JH-101"] and a.iloc[0]["severity"] == "alta" and "5d de atraso" in a.iloc[0]["detail"]


def test_inactive_task_is_medium_and_pending_task_is_not():
    rep = run([t(updated="2026-09-24 10:00"), t("JH-102", group=S.PENDENTE, updated="2026-09-01 10:00")])
    a = rules(rep, "inativa")
    assert a["key"].tolist() == ["JH-101"] and a.iloc[0]["severity"] == "média"


def test_recent_completion_is_informational_and_old_completion_is_not_listed():
    rep = run([t(group=S.CONCLUIDA, resolved=ts("2026-09-29 15:00")), t("JH-102", group=S.CONCLUIDA, resolved=ts("2026-09-10 15:00"))],
              commits=[commit("a", "JH-101"), commit("b", "JH-102")], prs=[pr()])
    c = rules(rep, "concluida")
    assert c["key"].tolist() == ["JH-101"] and c.iloc[0]["severity"] == "info"


def test_sprint_end_rules():
    sp = lambda end, state="active": {"name": "Sprint 5", "end": ts(end), "state": state}  # noqa: E731
    open_task = [t()]
    assert rules(run(open_task, sprint=sp("2026-10-01")), "sprint_fim").iloc[0]["severity"] == "média"      # termina em 1 dia
    ended = rules(run(open_task, sprint=sp("2026-09-28")), "sprint_fim").iloc[0]
    assert ended["severity"] == "alta" and "venceu há 2d" in ended["detail"]
    assert rules(run(open_task, sprint=sp("2026-10-20")), "sprint_fim").empty                                # longe do fim
    assert rules(run([t(group=S.CONCLUIDA)], commits=[commit("a", "JH-101")], prs=[pr()], sprint=sp("2026-10-01")), "sprint_fim").empty
    assert rules(run(open_task, sprint=None), "sprint_fim").empty                                            # "Todas": não se aplica
    assert rules(run(open_task, sprint=sp("2026-09-28", "closed")), "sprint_fim").empty


# ---------------------------------------------------------------- GitHub: PRs
def test_pr_awaiting_review_escalates_only_after_the_review_threshold():
    fresh, old = pr(1, created="2026-09-30 08:00", key="JH-100"), pr(2, created="2026-09-28 10:00")
    rep = run([t()], prs=[fresh, old])
    a = rules(rep, "pr_aguardando_revisao").set_index("key")
    assert a.loc["PR #1", "severity"] == "baixa" and a.loc["PR #2", "severity"] == "média"
    assert "sem nenhum review" in a.loc["PR #2", "detail"] and a.loc["PR #2", "owners"] == ["ana"]


def test_reviewed_states_are_distinguished_from_unreviewed():
    rep = run([t()], prs=[pr(1, review="comentada"), pr(2, review="mudancas_solicitadas"), pr(3, review="aprovada"),
                          pr(4, review="rascunho", draft=True), pr(5, review="desconhecido")])
    sev = {r["key"]: (r["rule"], r["severity"]) for _, r in rep.alerts.iterrows() if r["entity"] == "pr"}
    assert sev["PR #1"] == ("pr_comentada", "baixa") and sev["PR #2"] == ("pr_mudancas", "média")
    assert sev["PR #3"] == ("pr_aberta", "info") and sev["PR #4"] == ("pr_aberta", "info")
    assert sev["PR #5"] == ("pr_aberta", "info") and "desconhecido" in rules(rep, "pr_aberta").set_index("key").loc["PR #5", "detail"]
    assert rules(rep, "pr_aguardando_revisao").empty          # nenhuma delas é "aguardando": PR existir não é PR sem revisão


def test_old_open_pr_is_flagged_even_if_reviewed():
    rep = run([t()], prs=[pr(1, review="comentada", created="2026-09-20 10:00")])
    assert rules(rep, "pr_antiga").iloc[0]["severity"] == "média" and "limiar: 5d" in rules(rep, "pr_antiga").iloc[0]["detail"]


def test_merged_pr_is_informational_only_when_recent_and_notes_missing_review():
    rep = run([t(group=S.CONCLUIDA, code="BE-01")], commits=[commit("a", "JH-101")],
              prs=[pr(1, state="merged", review="mergeada", merged="2026-09-29 10:00"),
                   pr(2, state="merged", review="mergeada", merged="2026-09-01 10:00")])
    m = rules(rep, "pr_mergeada")
    assert m["key"].tolist() == ["PR #1"] and m.iloc[0]["severity"] == "info" and "sem nenhum review" in m.iloc[0]["detail"]


# ---------------------------------------------------------------- Jira <-> GitHub
def test_done_without_github_evidence_depends_on_code_side_and_is_high_confidence_only_for_code_tasks():
    rep = run([t(group=S.CONCLUIDA), t("JH-102", group=S.CONCLUIDA, code="UXDB-01")], prs=[pr()])
    a = rules(rep, "done_sem_github").set_index("key")
    assert a.loc["JH-101", "severity"] == "média" and a.loc["JH-102", "severity"] == "baixa"
    assert "pode não gerar commit" in a.loc["JH-102", "detail"]


def test_a_commit_that_cites_only_the_story_is_not_evidence_for_the_subtask():
    rep = run([t(group=S.CONCLUIDA)], commits=[commit("b", "JH-100")], prs=[pr()])
    assert rules(rep, "done_sem_github")["key"].tolist() == ["JH-101"]        # commit da Story não prova a Subtask (regra P0)


def test_done_with_commits_is_fine_when_the_story_has_a_pr_of_its_side():
    rep = run([t(group=S.CONCLUIDA)], commits=[commit("a", "JH-101")], prs=[pr(kind="backend")])
    assert rules(rep, "done_sem_github").empty and rules(rep, "done_sem_pr").empty


def test_done_with_commits_but_no_pr_is_flagged():
    rep = run([t(group=S.CONCLUIDA)], commits=[commit("a", "JH-101")])
    a = rules(rep, "done_sem_pr")
    assert a["key"].tolist() == ["JH-101"] and "de backend" in a.iloc[0]["detail"] and rules(rep, "done_sem_github").empty


def test_a_frontend_pr_does_not_cover_a_backend_task_but_a_sideless_pr_does():
    task_ = [t(group=S.CONCLUIDA)]
    assert rules(run(task_, commits=[commit("a", "JH-101")], prs=[pr(kind="frontend")]), "done_sem_pr")["key"].tolist() == ["JH-101"]
    assert rules(run(task_, commits=[commit("a", "JH-101")], prs=[pr(kind=None)]), "done_sem_pr").empty


def test_merged_pr_with_jira_still_in_progress_names_only_same_side_subtasks():
    rep = run([t("JH-101", code="BE-01", group=S.ANDAMENTO), t("JH-102", code="FE-01", group=S.ANDAMENTO),
               t("JH-103", code="BE-02", group=S.CONCLUIDA)],
              prs=[pr(7, state="merged", review="mergeada", kind="backend", merged="2026-09-29 09:00")],
              commits=[commit("a", "JH-101"), commit("b", "JH-103")])
    a = rules(rep, "pr_mergeada_jira_aberto")
    assert len(a) == 1 and a.iloc[0]["key"] == "PR #7" and a.iloc[0]["story_key"] == "JH-100"
    assert "JH-101" in a.iloc[0]["detail"] and "JH-102" not in a.iloc[0]["detail"] and "JH-103" not in a.iloc[0]["detail"]
    assert a.iloc[0]["owners"] == ["ana"] and a.iloc[0]["severity"] == "média"


def test_merged_pr_is_no_inconsistency_when_a_new_pr_of_the_same_side_is_open():
    rep = run([t(group=S.ANDAMENTO)], commits=[commit("a", "JH-101")],
              prs=[pr(7, state="merged", review="mergeada", merged="2026-09-29 09:00"), pr(8)])
    assert rules(rep, "pr_mergeada_jira_aberto").empty


def test_merged_pr_without_side_covers_subtasks_with_a_side():
    rep = run([t(code="FE-01")], commits=[commit("a", "JH-101")], prs=[pr(7, state="merged", review="mergeada", kind=None, merged="2026-09-29 09:00")])
    assert rules(rep, "pr_mergeada_jira_aberto")["key"].tolist() == ["PR #7"]


def test_in_analysis_without_pr_is_flagged_only_for_code_tasks():
    rep = run([t("JH-101", code="BE-01", group=S.ANALISE), t("JH-102", code="UXDB-01", group=S.ANALISE)])
    assert rules(rep, "analise_sem_pr")["key"].tolist() == ["JH-101"]
    assert rules(run([t(group=S.ANALISE)], prs=[pr(review="aguardando_revisao")]), "analise_sem_pr").empty


def test_human_commit_without_jira_key_is_flagged_but_bots_and_merges_are_not():
    cm = [commit("a", None), commit("b", "JH-101"), commit("c", None, kind="bot"), commit("d", None, kind="merge")]
    rep = run([t()], commits=cm, prs=[pr()])
    a = rules(rep, "commit_sem_jira_key")
    assert a["key"].tolist() == ["a"] and a.iloc[0]["owners"] == ["ana"]


# ---------------------------------------------------------------- sem falso positivo
def test_github_unavailable_disables_github_dependent_rules_and_says_so():
    rep = run([t(group=S.CONCLUIDA), t("JH-102", group=S.ANALISE)], github_ok=False, prs=[pr()])
    assert not set(rep.alerts["rule"]) & (A.GH_RULES | {"pr_aguardando_revisao", "pr_aberta", "pr_antiga"})
    assert any("GitHub indisponível" in n for n in rep.notes)


def test_done_task_created_before_the_github_window_is_not_verifiable():
    rep = run([t(group=S.CONCLUIDA, created=ts("2026-05-01"))], prs=[pr()], github_since=GH_START)
    assert rules(rep, "done_sem_github").empty


def test_severities_are_not_all_equal_and_are_ordered_high_first():
    rep = run([t(due="2026-09-25"), t("JH-102", group=S.CONCLUIDA)], prs=[pr(created="2026-09-30 08:00")],
              commits=[commit("a", None)])
    sev = rep.alerts["severity"].tolist()
    assert len(set(sev)) >= 3 and sev == sorted(sev, key=lambda s: -A.SEV_ORDER[s])


def test_alerts_are_filtered_by_person_without_losing_team_evidence():
    # JH-102 é do zeca e está Done com commit; a PR que o cobre foi escrita pela ana: não pode virar "Done sem PR" só porque o filtro é zeca
    rep = run([t("JH-101", who="ana", due="2026-09-25"), t("JH-102", who="zeca", group=S.CONCLUIDA, code="BE-02")],
              commits=[commit("z", "JH-102", author="zeca")], prs=[pr(author="ana", kind="backend")])
    assert rules(rep, "done_sem_pr").empty
    assert A.for_person(rep.alerts, "zeca").empty                                  # nada falso para quem não tem pendência
    assert set(A.for_person(rep.alerts, "ana")["rule"]) == {"atrasada", "pr_aguardando_revisao"}   # a PR dela + a task dela
    assert len(A.for_person(rep.alerts, None)) == len(rep.alerts)


def test_empty_inputs_give_an_empty_report():
    rep = run([t(group=S.CONCLUIDA, resolved=ts("2026-01-01"))], commits=[commit("a", "JH-101")], prs=[pr(kind=None)])
    assert rep.alerts.empty or set(rep.alerts["severity"]) <= {"baixa", "info", "média"}
    assert list(rep.alerts.columns) == A.ALERT_COLS
