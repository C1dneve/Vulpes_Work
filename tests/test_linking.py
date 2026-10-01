import pandas as pd
import pytest

from domain.linking import (
    branches_for_story,
    check_commit_message,
    commits_for_item,
    commits_for_story,
    display_id,
    extract_jira_keys,
    extract_us_ids,
    normalize_us_id,
    parse_branch,
    parse_pr_title,
    prs_for_story,
    story_level_commits,
)

P = r"JH-\d+"


class TestUSId:
    @pytest.mark.parametrize("text", [
        "fix status 1.2 endpoint", "bonus 2.5 no relatório", "virus 1.1", "campus 3.4 ajustes",
        "Give US 1.5x now", "us 1.2 lowercase with space", "focus 9.9", "versão 1.2",
    ])
    def test_false_positives_are_rejected(self, text):
        assert extract_us_ids(text) == []

    @pytest.mark.parametrize("text,expected", [
        ("feat: US2.1 cadastro", ["US2.1"]), ("US#1.2 Listagem", ["US1.2"]), ("US 2.2 login", ["US2.2"]),
        ("feature/backend/JH-123-US2.1-cadastro", ["US2.1"]), ("us2.3-x", ["US2.3"]), ("US-4.5", ["US4.5"]),
        ("US02.01", ["US2.1"]), ("US2.1 e US2.2", ["US2.1", "US2.2"]), ("US2.1 US2.1", ["US2.1"]),
        ("fim de frase US2.1.", ["US2.1"]), ("(US3.2)", ["US3.2"]),
    ])
    def test_real_cases(self, text, expected):
        assert extract_us_ids(text) == expected

    def test_us1_1_and_us1_2_stay_distinct(self):
        # Bug original: ambos viravam "US1".
        assert normalize_us_id(1, 1) != normalize_us_id(1, 2)
        assert extract_us_ids("US1.1") != extract_us_ids("US1.2")

    def test_three_levels_not_truncated_silently(self):
        assert extract_us_ids("US2.1.3") == []  # formato desconhecido: não inventa vínculo


class TestJiraKey:
    def test_configurable_pattern(self):
        assert extract_jira_keys("feat(JH-101): x", P) == ["JH-101"]
        assert extract_jira_keys("feat(ABC-7): x", r"ABC-\d+") == ["ABC-7"]
        assert extract_jira_keys("feat(JH-101): x", r"ABC-\d+") == []

    def test_boundaries_and_lowercase_branch(self):
        assert extract_jira_keys("feature/backend/jh-123-us2.1", P) == ["JH-123"]
        assert extract_jira_keys("XJH-123", P) == []
        assert extract_jira_keys("JH-123x", P) == []

    def test_multiple_keys_ordered_unique(self):
        assert extract_jira_keys("JH-2 JH-1 JH-2", P) == ["JH-2", "JH-1"]


class TestCommit:
    def test_valid_convention(self):
        c = check_commit_message("feat(JH-101): implementar validação do cadastro de cliente", P)
        assert c.is_valid and c.follows_convention and not c.problems and c.scope_keys == ("JH-101",)

    def test_commit_without_key_is_invalid(self):
        c = check_commit_message("feat: implementar validação do cadastro", P)
        assert not c.is_valid and "sem_jira_key" in c.problems

    def test_key_outside_scope_links_but_breaks_convention(self):
        c = check_commit_message("JH-101 implementar validação do cadastro", P)
        assert c.is_valid and not c.follows_convention and "fora_da_convencao" in c.problems

    @pytest.mark.parametrize("desc", ["ajustes", "fix", "wip", "update", "att", "mudanças"])
    def test_generic_description_is_flagged(self, desc):
        assert "descricao_generica" in check_commit_message(f"feat(JH-1): {desc}", P).problems

    def test_merge_and_revert_commits_are_exempt(self):
        for m in ["Merge pull request #4 from x/y", "Merge branch 'main' into feature/x", 'Revert "feat(JH-1): a"']:
            c = check_commit_message(m, P)
            assert c.exempt and c.is_valid and not c.problems

    def test_only_title_is_considered(self):
        c = check_commit_message("chore: ajuste geral do projeto inteiro\n\nRefs JH-9", P)
        assert not c.has_jira_key


class TestBranchAndPR:
    def test_backend_and_frontend(self):
        b = parse_branch("feature/backend/JH-123-US2.1-cadastro", P)
        f = parse_branch("feature/frontend/JH-123-US2.1-cadastro", P)
        assert (b.kind, b.jira_key, b.us_id, b.follows_convention) == ("backend", "JH-123", "US2.1", True)
        assert f.kind == "frontend" and f.us_id == "US2.1"

    def test_legacy_branch_without_key(self):
        b = parse_branch("feature/frontend/US1.1-Cadastro-de-Cliente", P)
        assert (b.kind, b.jira_key, b.us_id, b.follows_convention) == ("frontend", None, "US1.1", False)

    def test_unrelated_branch(self):
        b = parse_branch("hotfix/status-1.2", P)
        assert (b.kind, b.jira_key, b.us_id) == (None, None, None)

    def test_pr_title_convention(self):
        p = parse_pr_title("[JH-123] US2.1 — Cadastro de cliente", P)
        assert (p.jira_key, p.us_id, p.follows_convention) == ("JH-123", "US2.1", True)

    def test_pr_title_outside_convention(self):
        p = parse_pr_title("Cadastro de cliente US2.1 JH-123", P)
        assert (p.jira_key, p.us_id, p.follows_convention) == ("JH-123", "US2.1", False)


class TestResolution:
    KNOWN = {"JH-100", "JH-101", "JH-102", "JH-103"}

    def commits(self):
        return pd.DataFrame([
            {"sha": "a", "jira_key": "JH-101", "us_id": "US2.1", "date": pd.Timestamp("2026-09-01", tz="UTC")},
            {"sha": "b", "jira_key": "JH-102", "us_id": "US2.1", "date": pd.Timestamp("2026-09-02", tz="UTC")},
            {"sha": "c", "jira_key": None, "us_id": "US2.1", "date": pd.Timestamp("2026-09-03", tz="UTC")},
            {"sha": "d", "jira_key": None, "us_id": "US2.2", "date": pd.Timestamp("2026-09-04", tz="UTC")},
            {"sha": "e", "jira_key": "JH-100", "us_id": None, "date": pd.Timestamp("2026-09-05", tz="UTC")},
        ])

    def item(self, key="JH-101"):
        return pd.Series({"subtask_key": key, "story_key": "JH-100", "us_id": "US2.1"})

    def test_key_wins_over_visual_id(self):
        got = commits_for_item(self.commits(), self.item("JH-101"), self.KNOWN)
        # P0.1: Commit = Subtask. Só o commit que cita JH-101 é dele: "b" (chave de OUTRA task), "c" (só US2.1)
        # e "e" (só a chave da Story) NÃO viram evidência de execução de JH-101.
        assert set(got["sha"]) == {"a"}

    def test_us2_1_does_not_capture_us2_2(self):
        assert "d" not in set(commits_for_item(self.commits(), self.item(), self.KNOWN)["sha"])

    def test_story_level(self):
        got = commits_for_story(self.commits(), "JH-100", "US2.1", {"JH-101", "JH-102"}, self.KNOWN)
        assert set(got["sha"]) == {"a", "b", "c", "e"}

    def test_empty(self):
        assert commits_for_item(pd.DataFrame(columns=["jira_key", "us_id", "date"]), self.item(), self.KNOWN).empty


# ---------------------------------------------------------------- P0.1: Commit = Subtask
class TestCommitIsSubtask:
    KNOWN = {"JH-100", "JH-101", "JH-102", "JH-103", "JH-200", "JH-201"}
    CHILDREN = {"JH-101", "JH-102", "JH-103"}

    def frame(self):
        def c(sha, key, us=None, ref=None):
            return {"sha": sha, "jira_key": key, "us_id": us, "ref_jira_key": ref, "kind": "human",
                    "date": pd.Timestamp("2026-09-01", tz="UTC")}
        return pd.DataFrame([
            c("sub101", "JH-101", "US2.1", "JH-100"),          # feat(JH-101): ... dentro da PR [JH-100] US2.1
            c("story", "JH-100", "US2.1"),                      # feat(JH-100): ...  (chave da STORY)
            c("nokey", None, "US2.1"),                           # "ajustes no formulário" (só US visual)
            c("inherit", None, "US2.1", "JH-100"),               # sem chave; chave herdada da PR/branch
            c("other", "JH-201", "US2.1", "JH-100"),             # chave de Subtask de OUTRA story dentro dessa PR
            c("unknown", "JH-999", "US2.1", "JH-100"),           # chave que o Jira do board não conhece
        ])

    def item(self, key):
        return pd.Series({"subtask_key": key, "story_key": "JH-100", "us_id": "US2.1"})

    def shas(self, key):
        return sorted(commits_for_item(self.frame(), self.item(key), self.KNOWN)["sha"])

    def test_case1_subtask_key_goes_only_to_that_subtask(self):
        assert self.shas("JH-101") == ["sub101"]

    def test_case2_story_key_is_not_attributed_to_subtasks(self):
        for key in self.CHILDREN:
            assert "story" not in self.shas(key)

    def test_case3_commit_without_key_is_not_attributed_by_us(self):
        for key in self.CHILDREN:
            assert "nokey" not in self.shas(key)

    def test_case4_key_inherited_from_pr_or_branch_is_not_a_subtask_key(self):
        for key in self.CHILDREN:
            assert not {"inherit", "unknown"} & set(self.shas(key))

    def test_case5_one_commit_counts_once_across_the_story(self):
        counts = {k: len(self.shas(k)) for k in ("JH-101", "JH-102", "JH-103")}
        assert counts == {"JH-101": 1, "JH-102": 0, "JH-103": 0}

    def test_subtask_of_another_story_does_not_leak(self):
        assert "other" not in self.shas("JH-101")

    def test_story_level_gets_everything_that_names_the_story_and_not_a_subtask(self):
        got = story_level_commits(self.frame(), "JH-100", "US2.1", self.CHILDREN, self.KNOWN)
        assert set(got["sha"]) == {"story", "nokey", "inherit", "unknown"}   # 'other' tem chave conhecida de outra story
        allc = commits_for_story(self.frame(), "JH-100", "US2.1", self.CHILDREN, self.KNOWN)
        assert set(allc["sha"]) == {"sub101", "story", "nokey", "inherit", "unknown"}

    def test_reference_without_visual_id_still_reaches_the_story(self):
        df = pd.DataFrame([{"sha": "x", "jira_key": None, "us_id": None, "ref_jira_key": "JH-100",
                            "date": pd.Timestamp("2026-09-01", tz="UTC")}])
        assert list(commits_for_story(df, "JH-100", None, self.CHILDREN, self.KNOWN)["sha"]) == ["x"]

    def test_standalone_item_is_its_own_story(self):
        alone = pd.Series({"subtask_key": "JH-300", "story_key": "JH-300", "us_id": "US9.1"})
        df = pd.DataFrame([
            {"sha": "k", "jira_key": "JH-300", "us_id": None, "date": pd.Timestamp("2026-09-01", tz="UTC")},
            {"sha": "u", "jira_key": None, "us_id": "US9.1", "date": pd.Timestamp("2026-09-02", tz="UTC")},
        ])
        assert set(commits_for_item(df, alone, {"JH-300"})["sha"]) == {"k", "u"}

    def test_frames_without_ref_column_still_work(self):
        df = self.frame().drop(columns="ref_jira_key")
        assert list(commits_for_item(df, self.item("JH-101"), self.KNOWN)["sha"]) == ["sub101"]


# ---------------------------------------------------------------- P0.4: Jira Key vence o US visual (Story / Branch / PR)
class TestStoryRefs:
    KNOWN = {"JH-100", "JH-101", "JH-200"}

    def branches(self):
        return pd.DataFrame([
            {"branch": "main", "is_default": True, "jira_key": None, "us_id": None},
            {"branch": "feature/backend/JH-100-US2.1-x", "is_default": False, "jira_key": "JH-100", "us_id": "US2.1"},
            {"branch": "feature/frontend/JH-100-sem-us", "is_default": False, "jira_key": "JH-100", "us_id": None},
            {"branch": "feature/backend/US2.1-legado", "is_default": False, "jira_key": None, "us_id": "US2.1"},
            {"branch": "feature/backend/JH-200-US2.1-erro", "is_default": False, "jira_key": "JH-200", "us_id": "US2.1"},
        ])

    def test_key_only_relation_is_found_without_visual_id(self):
        got = branches_for_story(self.branches(), "JH-100", None, {"JH-101"}, self.KNOWN)
        assert set(got["branch"]) == {"feature/backend/JH-100-US2.1-x", "feature/frontend/JH-100-sem-us"}

    def test_visual_id_is_only_a_fallback_for_branch_without_known_key(self):
        got = branches_for_story(self.branches(), "JH-100", "US2.1", {"JH-101"}, self.KNOWN)
        assert set(got["branch"]) == {"feature/backend/JH-100-US2.1-x", "feature/frontend/JH-100-sem-us",
                                      "feature/backend/US2.1-legado"}   # JH-200 tem chave de OUTRA story: US2.1 não a traz

    def test_default_branch_is_never_a_story_branch(self):
        assert "main" not in set(branches_for_story(self.branches(), "JH-100", "US2.1", set(), self.KNOWN)["branch"])

    def test_prs_follow_the_same_rule(self):
        prs = pd.DataFrame([{"number": 1, "jira_key": "JH-100", "us_id": None},
                            {"number": 2, "jira_key": None, "us_id": "US2.1"},
                            {"number": 3, "jira_key": "JH-200", "us_id": "US2.1"}])
        assert set(prs_for_story(prs, "JH-100", "US2.1", set(), self.KNOWN)["number"]) == {1, 2}
        assert set(prs_for_story(prs, "JH-100", None, set(), self.KNOWN)["number"]) == {1}

    def test_empty_frames(self):
        assert branches_for_story(pd.DataFrame(columns=["branch"]), "JH-1", None, set(), set()).empty
        assert prs_for_story(pd.DataFrame(columns=["number"]), "JH-1", None, set(), set()).empty

    def test_display_id_puts_the_jira_key_first(self):
        assert display_id("JH-123", "US2.1") == "JH-123 · US2.1"
        assert display_id("JH-123", None) == "JH-123"
        assert display_id(None, "US2.1") == "US2.1"
        assert display_id(float("nan"), None) == ""
