"""Configuração centralizada. `load_settings()` lê .env + config.json e VALIDA; sem efeitos no import.

Precedência das variáveis: ambiente real do processo > arquivo .env (segredos de produção nunca são
sobrescritos por um .env local). O config.json guarda o que não é segredo (org, repos, regras).
"""
from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

from domain.thresholds import Thresholds, parse_thresholds

ROOT = Path(__file__).parent
OBRIGATORIAS = ("EMAIL", "TOKEN", "JIRA_DOMAIN", "BOARD_ID", "JIRA_PROJECT", "GITHUB_TOKEN")
OBSOLETAS = ("us_summary_pattern", "commit_pattern", "us_format")


@dataclass(frozen=True)
class JiraSettings:
    email: str = ""
    token: str = field(default="", repr=False)
    domain: str = ""
    board_id: str = ""
    project: str = ""
    story_points_field: str = ""   # id do campo (ex.: customfield_10016); vazio = descobrir pelo Jira


@dataclass(frozen=True)
class GitHubSettings:
    token: str = field(default="", repr=False)
    org: str = ""
    repos: tuple[str, ...] = ()
    lookback_days: int = 90
    bot_logins: tuple[str, ...] = ()


@dataclass(frozen=True)
class LinkSettings:
    jira_key_pattern: str = ""
    subtask_pattern: str = r"^\s*(BE|FE|UXDB)-?\s*0*(\d+)"
    use_jira_key_as_canonical: bool = False


@dataclass(frozen=True)
class Settings:
    jira: JiraSettings
    github: GitHubSettings
    linking: LinkSettings
    dev_mapping: dict[str, str]
    config_path: Path
    env_path: Path
    missing_env: tuple[str, ...] = ()
    problems: tuple[str, ...] = ()  # config.json inválido/obsoleto: mostrar na página Configurações
    management: Thresholds = field(default_factory=Thresholds)  # limiares de gestão (config.json → management)

    @property
    def ready(self) -> bool:
        return not self.missing_env


def read_env(env_path: Path, environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """.env (se existir) por baixo, ambiente real por cima. Não altera os.environ."""
    merged = {k: v for k, v in dotenv_values(env_path).items() if v is not None} if env_path.exists() else {}
    merged.update({k: v for k, v in (os.environ if environ is None else environ).items() if v})
    return merged


def load_settings(env_path: Path | None = None, config_path: Path | None = None,
                  environ: Mapping[str, str] | None = None) -> Settings:
    env_path, config_path = env_path or ROOT / ".env", config_path or ROOT / "config.json"
    env = read_env(env_path, environ)
    problems: list[str] = []

    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        cfg = {}
        problems.append(f"{config_path.name} não encontrado — usando padrões (sem repositórios).")
    except json.JSONDecodeError as e:
        cfg = {}
        problems.append(f"{config_path.name} inválido (linha {e.lineno}): {e.msg}")

    gh, rx = cfg.get("github") or {}, cfg.get("regex") or {}
    project = env.get("JIRA_PROJECT", "")
    org = env.get("GITHUB_ORG") or gh.get("org", "")
    repos = tuple(gh.get("repos") or ())
    if not org:
        problems.append("Organização do GitHub não definida (config.json → github.org ou GITHUB_ORG).")
    if not repos:
        problems.append("Nenhum repositório em config.json → github.repos.")
    lookback = gh.get("lookback_days", 90)
    if not isinstance(lookback, int) or lookback <= 0:
        problems.append("github.lookback_days deve ser um inteiro > 0; usando 90.")
        lookback = 90

    key_pattern = rx.get("jira_key_pattern") or (rf"{re.escape(project)}-\d+" if project else "")
    subtask_pattern = rx.get("subtask_summary_pattern") or LinkSettings.subtask_pattern
    for label, pat in (("regex.jira_key_pattern", key_pattern), ("regex.subtask_summary_pattern", subtask_pattern)):
        try:
            re.compile(pat)
        except re.error as e:
            problems.append(f"{label} não é uma regex válida: {e}")
            key_pattern = key_pattern if label != "regex.jira_key_pattern" else ""
    for k in OBSOLETAS:
        if k in rx:
            problems.append(f"regex.{k} é obsoleto e foi ignorado (regra de vínculo agora é central e testada).")

    jira_cfg = cfg.get("jira") or {}
    sp_field = jira_cfg.get("story_points_field") or "" if isinstance(jira_cfg, dict) else ""
    if sp_field and not re.fullmatch(r"customfield_\d+", str(sp_field)):
        problems.append("jira.story_points_field deve ser um id como customfield_10016; será descoberto automaticamente.")
        sp_field = ""
    management = parse_thresholds(cfg.get("management"), problems)

    mapping = cfg.get("dev_mapping") or {}
    if not isinstance(mapping, dict):
        problems.append("dev_mapping deve ser um objeto {login_github: slug_jira}.")
        mapping = {}

    return Settings(
        jira=JiraSettings(env.get("EMAIL", ""), env.get("TOKEN", ""), env.get("JIRA_DOMAIN", ""),
                          env.get("BOARD_ID", ""), project, str(sp_field)),
        github=GitHubSettings(env.get("GITHUB_TOKEN", ""), org, repos, lookback, tuple(gh.get("bot_logins") or ())),
        linking=LinkSettings(key_pattern, subtask_pattern, bool(rx.get("use_jira_key_as_canonical", False))),
        dev_mapping=dict(mapping), config_path=config_path, env_path=env_path,
        missing_env=tuple(v for v in OBRIGATORIAS if not env.get(v)), problems=tuple(problems), management=management,
    )


# ------------------------------------------------------------------ escrita segura
def merge_env_file(env_path: Path, updates: Mapping[str, str]) -> None:
    """Atualiza/cria só as chaves de `updates` no .env, preservando comentários e chaves que já existem.

    (A versão anterior reescrevia o arquivo inteiro e apagava tudo que não estava no formulário.)
    """
    if env_path.exists():
        encoding = "utf-8"
        try:
            lines = env_path.read_text(encoding=encoding).splitlines()
        except UnicodeDecodeError:
            encoding = "cp1252"
            lines = env_path.read_text(encoding=encoding).splitlines()
    else:
        encoding = "utf-8"
        lines = []
    pending = {k: v for k, v in updates.items() if v}

    def fmt(v: str) -> str:
        return f'"{v}"' if re.search(r"[\s#\"']", v) else v

    out = []
    for line in lines:
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if m and m.group(1) in pending:
            out.append(f"{m.group(1)}={fmt(pending.pop(m.group(1)))}")
        else:
            out.append(line)
    out += [f"{k}={fmt(v)}" for k, v in pending.items()]
    tmp = env_path.with_suffix(env_path.suffix + ".tmp")
    tmp.write_text("\n".join(out) + "\n", encoding=encoding)
    os.replace(tmp, env_path)


def save_dev_mapping(config_path: Path, key: str, slug: str) -> None:
    """Vincula um autor do GitHub (login ou nome) a um colaborador do Jira, alterando SÓ `dev_mapping`."""
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    cfg.setdefault("dev_mapping", {})[key] = slug
    tmp = config_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, config_path)
