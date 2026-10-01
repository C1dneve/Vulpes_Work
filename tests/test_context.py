import pandas as pd

from services.context import (
    Bundle,
    Context,
    apply_context,
    default_sprint,
    sprint_options,
    sprint_window,
    stories_in_sprint,
)

TZ = "America/Sao_Paulo"


def ts(s):
    return pd.Timestamp(s, tz=TZ)


def bundle():
    stories = pd.DataFrame([
        {"story_key": "JH-1", "story_summary": "US2.1", "sprint": "Sprint 5", "sprint_state": "active", "us_id": "US2.1",
         "sprint_start": ts("2026-09-21"), "sprint_end": ts("2026-10-05")},
        {"story_key": "JH-2", "story_summary": "US2.2", "sprint": "Sprint 5", "sprint_state": "active", "us_id": "US2.2",
         "sprint_start": ts("2026-09-21"), "sprint_end": ts("2026-10-05")},
        {"story_key": "JH-9", "story_summary": "US1.1", "sprint": "Sprint 4", "sprint_state": "closed", "us_id": "US1.1",
         "sprint_start": ts("2026-09-07"), "sprint_end": ts("2026-09-20")},
    ])
    items = pd.DataFrame([
        {"subtask_key": "JH-11", "story_key": "JH-1", "sprint": "Sprint 5", "assignee": "cid"},
        {"subtask_key": "JH-12", "story_key": "JH-1", "sprint": "Sprint 5", "assignee": "samuel"},
        {"subtask_key": "JH-21", "story_key": "JH-2", "sprint": "Sprint 5", "assignee": "cid"},
        {"subtask_key": "JH-91", "story_key": "JH-9", "sprint": "Sprint 4", "assignee": "cid"},
    ])
    sprints = pd.DataFrame([
        {"sprint_id": 4, "name": "Sprint 4", "state": "closed", "start": ts("2026-09-07"), "end": ts("2026-09-20"), "complete": pd.NaT},
        {"sprint_id": 5, "name": "Sprint 5", "state": "active", "start": ts("2026-09-21"), "end": ts("2026-10-05"), "complete": pd.NaT}])
    wl = pd.DataFrame([{"subtask_key": "JH-11", "author": "cid"}, {"subtask_key": "JH-11", "author": "samuel"},
                       {"subtask_key": "JH-91", "author": "cid"}])
    cl = pd.DataFrame([{"subtask_key": "JH-11"}, {"subtask_key": "JH-91"}])

    def commit(sha, key, us, author, when):
        return {"sha": sha, "jira_key": key, "us_id": us, "author": author, "date": ts(when)}
    commits = pd.DataFrame([
        commit("a", "JH-11", "US2.1", "cid", "2026-09-22"),
        commit("b", "JH-12", "US2.1", "samuel", "2026-09-23"),
        commit("c", None, "US2.2", "cid", "2026-09-24"),
        commit("d", "JH-91", "US1.1", "cid", "2026-09-10"),      # sprint anterior
        commit("e", None, None, "cid", "2026-09-25"),            # sem vínculo, dentro da janela
        commit("f", None, None, "cid", "2026-08-01"),            # sem vínculo, fora da janela
        commit("g", "JH-12", "US2.2", "samuel", "2026-09-26"),   # chave de OUTRA task vence o ID visual US2.2
    ])
    branches = pd.DataFrame([
        {"branch": "main", "is_default": True, "jira_key": None, "us_id": None, "last_author": "", "last_commit": pd.NaT},
        {"branch": "feature/a", "is_default": False, "jira_key": "JH-1", "us_id": "US2.1", "last_author": "cid", "last_commit": ts("2026-09-22")},
        {"branch": "feature/old", "is_default": False, "jira_key": "JH-9", "us_id": "US1.1", "last_author": "cid", "last_commit": ts("2026-09-10")},
    ])
    prs = pd.DataFrame([
        {"number": 1, "jira_key": "JH-1", "us_id": "US2.1", "author": "cid", "created": ts("2026-09-22")},
        {"number": 2, "jira_key": "JH-9", "us_id": "US1.1", "author": "cid", "created": ts("2026-09-10")},
    ])
    return Bundle(stories, items, wl, cl, sprints, commits, branches, prs)


def test_default_is_active_sprint():
    b = bundle()
    assert default_sprint(b.stories, b.sprints) == "Sprint 5"
    assert sprint_options(b.stories, b.sprints) == ["Sprint 5", "Sprint 4"]


def test_default_without_sprints_frame_uses_story_state():
    b = bundle()
    assert default_sprint(b.stories, b.sprints.iloc[0:0]) == "Sprint 5"


def test_sprint_filter_applies_to_every_frame():
    b = bundle()
    s = apply_context(b, Context(sprint="Sprint 5"))
    assert set(s.items["subtask_key"]) == {"JH-11", "JH-12", "JH-21"}
    assert set(s.commits["sha"]) == {"a", "b", "c", "e", "g"}          # d (sprint 4) e f (fora da janela) saem
    assert set(s.worklogs["subtask_key"]) == {"JH-11"} and set(s.changelog["subtask_key"]) == {"JH-11"}
    assert set(s.branches["branch"]) == {"feature/a"} and set(s.prs["number"]) == {1}


def test_dev_filter_applies_to_every_frame():
    s = apply_context(bundle(), Context(sprint="Sprint 5", dev="cid"))
    assert set(s.items["subtask_key"]) == {"JH-11", "JH-21"}
    assert set(s.commits["author"]) == {"cid"} and set(s.commits["sha"]) == {"a", "c", "e"}
    assert set(s.worklogs["author"]) == {"cid"}
    assert set(s.prs["author"]) == {"cid"}


def test_key_beats_visual_id_across_stories():
    s = apply_context(bundle(), Context(sprint="Sprint 5", story_keys=("JH-2",)))
    assert "g" not in set(s.commits["sha"])   # g cita JH-12 (story JH-1) mesmo dizendo US2.2
    assert "c" in set(s.commits["sha"])


def test_manual_story_narrowing_drops_unlinked_activity():
    s = apply_context(bundle(), Context(sprint="Sprint 5", story_keys=("JH-1",)))
    assert s.narrowed
    assert set(s.commits["sha"]) == {"a", "b", "g"}   # g cita JH-12, filha de JH-1: pertence ao escopo
    assert "e" not in set(s.commits["sha"]) and "c" not in set(s.commits["sha"])


def test_all_sprints_keeps_everything_linked_and_unlinked():
    b = bundle()
    s = apply_context(b, Context())
    assert len(s.commits) == len(b.commits) and len(s.items) == len(b.items) and len(s.branches) == 3


def test_sprint_window_uses_board_dates_then_falls_back_to_stories():
    b = bundle()
    assert sprint_window(b.stories, b.sprints, "Sprint 5") == (pd.Timestamp("2026-09-21"), pd.Timestamp("2026-10-05"))
    assert sprint_window(b.stories, b.sprints.iloc[0:0], "Sprint 4") == (pd.Timestamp("2026-09-07"), pd.Timestamp("2026-09-20"))
    assert sprint_window(b.stories.iloc[0:0], b.sprints.iloc[0:0], None) == (None, None)


def test_empty_frames_do_not_crash():
    b = bundle()
    e = Bundle(b.stories, b.items, b.worklogs.iloc[0:0], b.changelog.iloc[0:0], b.sprints,
               b.commits.iloc[0:0], b.branches.iloc[0:0], b.prs.iloc[0:0])
    s = apply_context(e, Context(sprint="Sprint 5", dev="cid"))
    assert s.commits.empty and s.branches.empty and s.prs.empty and s.worklogs.empty


# ---------------------------------------------------------------- P0.2: sprint da Subtask x sprint da Story
def split_sprint_bundle():
    """JH-1 (Story) está na Sprint 4, mas a Subtask JH-11 está na Sprint 5; JH-12 herda a Sprint 4."""
    b = bundle()
    b.stories.loc[b.stories["story_key"] == "JH-1", ["sprint", "sprint_state"]] = ["Sprint 4", "closed"]
    b.items.loc[b.items["subtask_key"] == "JH-12", "sprint"] = "Sprint 4"   # herdou a da Story
    return b


def test_story_stays_in_scope_when_only_its_subtask_is_in_the_sprint():
    sc = apply_context(split_sprint_bundle(), Context(sprint="Sprint 5"))
    assert set(sc.items["subtask_key"]) == {"JH-11", "JH-21"}
    assert "JH-1" in set(sc.stories["story_key"])      # a Story de outra Sprint continua disponível para exibir JH-11


def test_story_not_duplicated_when_it_is_in_the_sprint_and_has_subtasks_there():
    sc = apply_context(bundle(), Context(sprint="Sprint 5"))
    assert sc.stories["story_key"].is_unique and set(sc.stories["story_key"]) == {"JH-1", "JH-2"}
    b = split_sprint_bundle()
    assert stories_in_sprint(b.stories, b.items, "Sprint 4")["story_key"].is_unique


def test_story_in_sprint_without_its_subtasks_there_is_still_a_story_of_that_sprint():
    sc = apply_context(split_sprint_bundle(), Context(sprint="Sprint 4"))
    assert "JH-1" in set(sc.stories["story_key"]) and "JH-12" in set(sc.items["subtask_key"])
    assert "JH-11" not in set(sc.items["subtask_key"])


def test_manual_story_selection_is_not_seen_as_narrowing_with_the_expanded_scope():
    b = split_sprint_bundle()
    keys = tuple(stories_in_sprint(b.stories, b.items, "Sprint 5")["story_key"])   # o que a barra lateral oferece
    assert not apply_context(b, Context(sprint="Sprint 5", story_keys=keys)).narrowed


# ---------------------------------------------------------------- P0.4: chave herdada da PR/branch entra no escopo
def test_commit_with_only_a_pr_reference_key_follows_its_story():
    b = bundle()
    b.stories["us_id"] = None   # a Story não tem ID visual: só a chave do Jira liga o GitHub
    b.commits["ref_jira_key"] = None
    b.commits.loc[b.commits["sha"] == "c", ["us_id", "ref_jira_key"]] = [None, "JH-2"]
    sc = apply_context(b, Context(sprint="Sprint 5", story_keys=("JH-2",)))
    assert "c" in set(sc.commits["sha"])
    sc = apply_context(b, Context(sprint="Sprint 5", story_keys=("JH-1",)))
    assert "c" not in set(sc.commits["sha"])


def test_own_key_of_another_issue_beats_the_pr_reference():
    b = bundle()
    b.commits["ref_jira_key"] = None
    b.commits.loc[b.commits["sha"] == "b", "ref_jira_key"] = "JH-2"   # PR da JH-2, mas o commit cita JH-12 (story JH-1)
    sc = apply_context(b, Context(sprint="Sprint 5", story_keys=("JH-2",)))
    assert "b" not in set(sc.commits["sha"])
