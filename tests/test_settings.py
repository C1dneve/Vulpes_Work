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
