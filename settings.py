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
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool, StrictInt, ValidationError

from domain.thresholds import Thresholds, parse_thresholds

ROOT = Path(__file__).parent
OBRIGATORIAS = ("EMAIL", "TOKEN", "JIRA_DOMAIN", "BOARD_ID", "JIRA_PROJECT", "GITHUB_TOKEN")
OBSOLETAS = ("us_summary_pattern", "commit_pattern", "us_format")


class _EnvironmentSchema(BaseModel):
    """Valida os tipos das variáveis sem permitir que segredos apareçam em erros ou reprs."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    email: str = Field(default="", validation_alias="EMAIL")
    token: SecretStr = Field(default=SecretStr(""), validation_alias="TOKEN")
    jira_domain: str = Field(default="", validation_alias="JIRA_DOMAIN")
    board_id: str = Field(default="", validation_alias="BOARD_ID")
    jira_project: str = Field(default="", validation_alias="JIRA_PROJECT")
    github_token: SecretStr = Field(default=SecretStr(""), validation_alias="GITHUB_TOKEN")


class _GitHubConfigSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    org: str = ""
    repos: list[str] = Field(default_factory=list)
    lookback_days: StrictInt = Field(default=90, gt=0)
    bot_logins: list[str] = Field(default_factory=list)


class _RegexConfigSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    jira_key_pattern: str = ""
    subtask_summary_pattern: str = ""
    use_jira_key_as_canonical: StrictBool = False


class _JiraConfigSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    story_points_field: str = ""


class _ManagementConfigSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    due_soon_days: StrictInt = Field(default=2, gt=0)
    inactive_business_days: StrictInt = Field(default=2, gt=0)
    pr_review_wait_hours: StrictInt = Field(default=24, gt=0)
    pr_old_days: StrictInt = Field(default=5, gt=0)
    sprint_ending_days: StrictInt = Field(default=2, gt=0)
    recent_days: StrictInt = Field(default=2, gt=0)


class _DevMappingSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mapping: dict[str, str] = Field(default_factory=dict)


def _validation_message(error: dict[str, object]) -> str:
    """Traduz erros de tipo/limite sem incluir o valor recebido (pode ser sensível)."""
    kind = str(error.get("type", ""))
    type_messages = {
        "string_type": "deve ser texto",
        "dict_type": "deve ser um objeto",
        "list_type": "deve ser uma lista",
        "bool_type": "deve ser um booleano",
        "int_type": "deve ser um inteiro",
    }
    if kind in type_messages:
        return type_messages[kind]
    if kind in {"greater_than", "greater_than_equal"}:
        return "deve ser maior que zero"
    if kind == "extra_forbidden":
        return "contém um campo não permitido"
    return "tem um valor inválido"


def _validate_section(schema: type[BaseModel], raw: object, name: str, problems: list[str]) -> dict:
    """Valida campos de uma seção individualmente para manter os campos válidos mesmo se outro falhar."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        problems.append(f"{name} deve ser um objeto; usando padrões.")
        return {}
    defaults = schema().model_dump()
    fields = schema.model_fields
    for key, value in raw.items():
        if key not in fields:
            defaults[key] = value
            continue
        try:
            parsed = schema.model_validate({key: value})
            defaults[key] = getattr(parsed, key)
        except ValidationError as exc:
            for issue in exc.errors():
                field_name = ".".join(str(part) for part in issue.get("loc", (key,)))
                problems.append(f"{name}.{field_name} {_validation_message(issue)}; usando padrão.")
    return defaults


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
    raw_env = read_env(env_path, environ)
    problems: list[str] = []

    # Pydantic valida os tipos das variáveis. Valores não textuais são descartados sem serem exibidos.
    safe_env = {key: value for key, value in raw_env.items() if isinstance(value, str)}
    for key, value in raw_env.items():
        if key in OBRIGATORIAS and not isinstance(value, str):
            problems.append(f"{key} deve ser texto; variável ignorada.")
    try:
        env_model = _EnvironmentSchema.model_validate(safe_env)
    except ValidationError as exc:
        # Não usar str(exc) nem errors() diretamente: ambos podem conter o valor recebido.
        for issue in exc.errors():
            loc = str(issue.get("loc", ["variável"])[0]).upper()
            problems.append(f"{loc} {_validation_message(issue)}.")
        env_model = _EnvironmentSchema()

    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        cfg = {}
        problems.append(f"{config_path.name} não encontrado — usando padrões (sem repositórios).")
    except json.JSONDecodeError as e:
        cfg = {}
        problems.append(f"{config_path.name} inválido (linha {e.lineno}): {e.msg}")

    if not isinstance(cfg, dict):
        problems.append(f"{config_path.name} deve conter um objeto JSON na raiz; usando padrões.")
        cfg = {}

    gh = _validate_section(_GitHubConfigSchema, cfg.get("github"), "github", problems)
    rx = _validate_section(_RegexConfigSchema, cfg.get("regex"), "regex", problems)
    jira_cfg = _validate_section(_JiraConfigSchema, cfg.get("jira"), "jira", problems)

    project = env_model.jira_project
    org = safe_env.get("GITHUB_ORG") or gh.get("org", "")
    repos = tuple(gh.get("repos") or ())
    if not org:
        problems.append("Organização do GitHub não definida (config.json → github.org ou GITHUB_ORG).")
    if not repos:
        problems.append("Nenhum repositório em config.json → github.repos.")

    lookback = gh.get("lookback_days", 90)
    # Compatibilidade defensiva caso uma versão antiga do JSON tenha tipos inesperados.
    if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback <= 0:
        if not any(p.startswith("github.lookback_days") for p in problems):
            problems.append("github.lookback_days deve ser um inteiro maior que 0; usando 90.")
        lookback = 90

    key_pattern = rx.get("jira_key_pattern") or (rf"{re.escape(project)}-\d+" if project else "")
    subtask_pattern = rx.get("subtask_summary_pattern") or LinkSettings.subtask_pattern
    for label, pat in (("regex.jira_key_pattern", key_pattern), ("regex.subtask_summary_pattern", subtask_pattern)):
        try:
            re.compile(pat)
        except re.error as e:
            problems.append(f"{label} não é uma regex válida: {e}")
            if label == "regex.jira_key_pattern":
                key_pattern = ""
            else:
                subtask_pattern = LinkSettings.subtask_pattern
    for k in OBSOLETAS:
        if k in rx:
            problems.append(f"regex.{k} é obsoleto e foi ignorado (regra de vínculo agora é central e testada).")

    sp_field = jira_cfg.get("story_points_field") or ""
    if sp_field and not re.fullmatch(r"customfield_\d+", str(sp_field)):
        problems.append("jira.story_points_field deve ser um id como customfield_10016; será descoberto automaticamente.")
        sp_field = ""

    management_cfg = _validate_section(_ManagementConfigSchema, cfg.get("management"), "management", problems)
    management = parse_thresholds(management_cfg, problems)

    raw_mapping = cfg.get("dev_mapping") or {}
    try:
        mapping = _DevMappingSchema.model_validate({"mapping": raw_mapping}).mapping
    except ValidationError as exc:
        for issue in exc.errors():
            problems.append(f"dev_mapping deve ser um objeto de texto para texto ({_validation_message(issue)}); usando vazio.")
        mapping = {}

    # Remove mensagens repetidas que podem surgir da validação Pydantic + compatibilidade legada.
    problems = list(dict.fromkeys(problems))
    env_values = {
        "EMAIL": env_model.email,
        "TOKEN": env_model.token.get_secret_value(),
        "JIRA_DOMAIN": env_model.jira_domain,
        "BOARD_ID": env_model.board_id,
        "JIRA_PROJECT": env_model.jira_project,
        "GITHUB_TOKEN": env_model.github_token.get_secret_value(),
    }
    missing_env = tuple(key for key in OBRIGATORIAS if not env_values.get(key, "").strip())

    return Settings(
        jira=JiraSettings(env_values["EMAIL"], env_values["TOKEN"], env_values["JIRA_DOMAIN"],
                          env_values["BOARD_ID"], env_values["JIRA_PROJECT"], str(sp_field)),
        github=GitHubSettings(env_values["GITHUB_TOKEN"], str(org), repos, lookback, tuple(gh.get("bot_logins") or ())),
        linking=LinkSettings(key_pattern, subtask_pattern, bool(rx.get("use_jira_key_as_canonical", False))),
        dev_mapping=dict(mapping), config_path=config_path, env_path=env_path,
        missing_env=missing_env, problems=tuple(problems), management=management,
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
