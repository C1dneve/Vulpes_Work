import json

from settings import load_settings, merge_env_file, save_dev_mapping
from tests.conftest import ENV


def test_real_environment_beats_env_file_and_is_not_mutated(tmp_path):
    (tmp_path / ".env").write_text("EMAIL=file@x\nTOKEN=file-token\nGITHUB_TOKEN=g\nJIRA_DOMAIN=d\nBOARD_ID=1\nJIRA_PROJECT=JH\n")
    s = load_settings(env_path=tmp_path / ".env", config_path=tmp_path / "c.json", environ={"EMAIL": "prod@x"})
    assert s.jira.email == "prod@x" and s.jira.token == "file-token" and s.ready


def test_missing_env_is_reported(tmp_path):
    s = load_settings(env_path=tmp_path / ".env", config_path=tmp_path / "c.json", environ={"EMAIL": "a"})
    assert not s.ready and "TOKEN" in s.missing_env and "EMAIL" not in s.missing_env


def test_secrets_are_hidden_from_repr(tmp_path):
    s = load_settings(env_path=tmp_path / ".env", config_path=tmp_path / "c.json", environ=ENV)
    assert "ghp_x" not in repr(s) and "tok" not in repr(s.jira)


def test_jira_key_pattern_defaults_to_project_and_is_configurable(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"github": {"org": "T", "repos": ["r"]}}))
    assert load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV).linking.jira_key_pattern == r"JH-\d+"
    cfg.write_text(json.dumps({"github": {"org": "T", "repos": ["r"]}, "regex": {"jira_key_pattern": r"(?:JH|AB)-\d+"}}))
    assert load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV).linking.jira_key_pattern == r"(?:JH|AB)-\d+"


def test_invalid_config_is_reported_not_crashing(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text("{ nao e json")
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    assert any("inválido" in p for p in s.problems)
    cfg.write_text(json.dumps({"github": {"org": "T", "repos": ["r"], "lookback_days": -3}, "regex": {"jira_key_pattern": "(["}}))
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    assert s.github.lookback_days == 90
    assert any("regex" in p and "válida" in p for p in s.problems)
    assert s.linking.jira_key_pattern == ""   # não deixa uma regex quebrada chegar aos extratores


def test_merge_env_preserves_existing_keys_and_comments(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# meu comentário\nEXTRA_PROD_SECRET=nao-apague\nTOKEN=velho\n")
    merge_env_file(env, {"TOKEN": "novo", "EMAIL": "a@b.c", "VAZIO": ""})
    txt = env.read_text()
    assert "# meu comentário" in txt and "EXTRA_PROD_SECRET=nao-apague" in txt
    assert "TOKEN=novo" in txt and "TOKEN=velho" not in txt and "EMAIL=a@b.c" in txt and "VAZIO" not in txt


def test_merge_env_quotes_values_with_spaces(tmp_path):
    env = tmp_path / ".env"
    merge_env_file(env, {"X": "a b#c"})
    assert load_settings(env_path=env, config_path=tmp_path / "c.json", environ={}).jira.email == ""
    from dotenv import dotenv_values
    assert dotenv_values(env)["X"] == "a b#c"


def test_save_dev_mapping_touches_only_dev_mapping(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"github": {"org": "T", "repos": ["r"]}, "dev_mapping": {"a": "b"}}))
    save_dev_mapping(cfg, "Pedro P.", "pedro-pereira-rodrigues")
    out = json.loads(cfg.read_text())
    assert out["dev_mapping"] == {"a": "b", "Pedro P.": "pedro-pereira-rodrigues"} and out["github"]["org"] == "T"



def test_pydantic_rejects_wrong_config_types_and_keeps_valid_siblings(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"github": {"org": "Team", "repos": ["repo"], "lookback_days": "90"}}))
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    assert s.github.org == "Team"
    assert s.github.repos == ("repo",)
    assert s.github.lookback_days == 90
    assert any("github.lookback_days" in problem and "inteiro" in problem for problem in s.problems)


def test_pydantic_validates_developer_mapping_shape(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"github": {"org": "Team", "repos": ["repo"]}, "dev_mapping": ["not-a-map"]}))
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    assert s.dev_mapping == {}
    assert any("dev_mapping" in problem for problem in s.problems)


def test_environment_type_error_does_not_echo_received_value(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"github": {"org": "Team", "repos": ["repo"]}}))
    marker = "SENSITIVE_MARKER_DO_NOT_ECHO"
    environ = {**ENV, "EMAIL": 123456, "TOKEN": marker}
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=environ)
    assert "EMAIL" in s.missing_env
    assert all(marker not in problem for problem in s.problems)
    assert "123456" not in " ".join(s.problems)


def test_missing_optional_configuration_fields_use_defaults(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"github": {"org": "Team", "repos": ["repo"]}}))
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    assert s.github.lookback_days == 90
    assert s.linking.use_jira_key_as_canonical is False


def test_obsolete_regex_keys_are_reported_and_ignored(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({
        "github": {"org": "Team", "repos": ["repo"]},
        "regex": {"us_summary_pattern": "pattern antigo"},
    }))
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    assert any("regex.us_summary_pattern é obsoleto" in problem for problem in s.problems)
    assert s.linking.jira_key_pattern == r"JH-\d+"


def test_configuration_precedence_real_environment_then_env_file_then_json(tmp_path):
    env_path = tmp_path / ".env"
    cfg = tmp_path / "config.json"
    env_path.write_text("GITHUB_ORG=env-file\n")
    cfg.write_text(json.dumps({"github": {"org": "config-json", "repos": ["repo"]}}))

    real_env = load_settings(env_path=env_path, config_path=cfg, environ={**ENV, "GITHUB_ORG": "real-environment"})
    env_file = load_settings(env_path=env_path, config_path=cfg, environ=ENV)
    config_json = load_settings(env_path=tmp_path / "missing.env", config_path=cfg, environ=ENV)

    assert real_env.github.org == "real-environment"
    assert env_file.github.org == "env-file"
    assert config_json.github.org == "config-json"


def test_invalid_management_threshold_falls_back_with_warning(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({
        "github": {"org": "Team", "repos": ["repo"]},
        "management": {"due_soon_days": 0},
    }))
    s = load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)
    assert s.management.due_soon_days == 2
    assert any("management.due_soon_days" in problem for problem in s.problems)
