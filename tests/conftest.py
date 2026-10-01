import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.people import DevMapper  # noqa: E402
from settings import load_settings  # noqa: E402

ENV = {"EMAIL": "a@b.c", "TOKEN": "tok", "JIRA_DOMAIN": "x.atlassian.net", "BOARD_ID": "7",
       "JIRA_PROJECT": "JH", "GITHUB_TOKEN": "ghp_x"}
MAPPING = {"samuelmartins00": "samuel-martins", "c1dneve": "cid-daniel-neves-d-oliveira",
           "pedroprdgs": "pedro-pereira-rodrigues"}


@pytest.fixture
def settings(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"github": {"org": "Team", "repos": ["repo"], "lookback_days": 90},
                               "regex": {"use_jira_key_as_canonical": False},
                               "dev_mapping": MAPPING}), encoding="utf-8")
    return load_settings(env_path=tmp_path / ".env", config_path=cfg, environ=ENV)


@pytest.fixture
def mapper():
    return DevMapper(MAPPING, known_slugs={"samuel-martins", "cid-daniel-neves-d-oliveira", "pedro-pereira-rodrigues"})
