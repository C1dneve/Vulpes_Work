"""Regras de vínculo Jira <-> GitHub (funções puras, sem rede).

Modelo oficial do time:
    Branch = User Story   |   PR = User Story   |   Commit = Subtask
    branch : feature/backend/JH-123-US2.1-cadastro   (ou .../frontend/...)
    PR     : [JH-123] US2.1 — Cadastro de cliente
    commit : feat(JH-101): descrição real da alteração

Dois identificadores convivem durante a transição:
    US2.1  = identificador VISUAL (amigável)      JH-123 = identificador OFICIAL de integração
Quando os dois existem, a chave do Jira sempre tem prioridade.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd

# "US2.1", "US#2.1", "US 2.1", "us-2.1", "us2.1" — mas NUNCA dentro de palavras ("status 1.2", "bonus 2.5",
# "virus 1.1"): exige fronteira antes do "US" e não aceita letra/dígito logo depois do número.
# "US" com espaço só é aceito em maiúsculas, para não casar "us 1.5" de frases comuns.
_US_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:US\s?#?|[Uu][Ss][#\-]?)0*(\d+)\.0*(\d+)(?![0-9A-Za-z]|\.\d)"
)

BRANCH_KINDS = ("backend", "frontend")

# Descrições que não dizem o que mudou (a convenção pede "descrição real da alteração").
_GENERIC = {
    "ajuste", "ajustes", "fix", "fixes", "wip", "update", "updates", "changes", "change", "commit",
    "alteracao", "alteracoes", "correcao", "correcoes", "att", "atualizacao", "teste", "testes", "misc",
}


def normalize_us_id(epic: str | int, story: str | int) -> str:
    """`US{epic}.{story}` sem zeros à esquerda. O número depois do ponto NUNCA é descartado."""
    return f"US{int(epic)}.{int(story)}"


def extract_us_ids(text: str | None) -> list[str]:
    """Todos os IDs visuais de User Story no texto, sem repetição e na ordem em que aparecem."""
    out: list[str] = []
    for m in _US_RE.finditer(text or ""):
        us = normalize_us_id(m.group(1), m.group(2))
        if us not in out:
            out.append(us)
    return out


@lru_cache(maxsize=32)
def jira_key_regex(pattern: str) -> re.Pattern[str]:
    """Regex de chave do Jira a partir de um padrão CONFIGURÁVEL (ex.: `JH-\\d+`), com fronteiras."""
    return re.compile(rf"(?<![A-Za-z0-9])({pattern})(?![A-Za-z0-9])", re.IGNORECASE)


def extract_jira_keys(text: str | None, pattern: str) -> list[str]:
    """Todas as chaves do Jira no texto (maiúsculas, sem repetição, em ordem)."""
    out: list[str] = []
    for m in jira_key_regex(pattern).finditer(text or ""):
        key = m.group(1).upper()
        if key not in out:
            out.append(key)
    return out


# ------------------------------------------------------------------ commit
_CC_RE = re.compile(r"^\s*(?P<type>[A-Za-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*(?P<desc>.*)$", re.DOTALL)
_MERGE_MSG = re.compile(r"^(Merge (pull request|branch|remote-tracking branch)|Revert \")", re.IGNORECASE)


@dataclass(frozen=True)
class CommitCheck:
    type: str | None
    scope_keys: tuple[str, ...]
    keys: tuple[str, ...]  # todas as chaves Jira em qualquer lugar do título
    description: str
    has_jira_key: bool  # regra dura: sem chave o commit é inválido
    follows_convention: bool  # tipo(CHAVE): descrição
    generic_description: bool
    exempt: bool  # merge/revert automáticos não seguem a convenção
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        return self.exempt or self.has_jira_key


def check_commit_message(message: str | None, key_pattern: str, min_desc_chars: int = 10) -> CommitCheck:
    """Valida `feat(JH-101): descrição real`. Só olha o título (primeira linha)."""
    title = (message or "").split("\n", 1)[0].strip()
    exempt = bool(_MERGE_MSG.match(title))
    keys = tuple(extract_jira_keys(title, key_pattern))
    m = _CC_RE.match(title)
    ctype = m.group("type").lower() if m else None
    scope_keys = tuple(extract_jira_keys(m.group("scope"), key_pattern)) if m and m.group("scope") else ()
    desc = (m.group("desc") if m else title).strip()
    follows = bool(m and scope_keys)
    normalized = re.sub(r"[^a-z0-9 ]", "", desc.lower()).strip()
    generic = bool(desc) and (normalized in _GENERIC or len(desc) < min_desc_chars)

    problems: list[str] = []
    if not exempt:
        if not keys:
            problems.append("sem_jira_key")
        elif not follows:
            problems.append("fora_da_convencao")
        if generic:
            problems.append("descricao_generica")
    return CommitCheck(ctype, scope_keys, keys, desc, bool(keys), follows, generic, exempt, tuple(problems))


# ------------------------------------------------------------------ branch / PR
@dataclass(frozen=True)
class BranchRef:
    kind: str | None  # "backend" | "frontend" | None
    jira_key: str | None
    us_id: str | None
    follows_convention: bool


def parse_branch(name: str | None, key_pattern: str) -> BranchRef:
    """`feature/backend/JH-123-US2.1-cadastro`. Aceita nomes legados sem chave (ex.: `US1.1-Cadastro`)."""
    name = name or ""
    kind = next((p.lower() for p in name.split("/") if p.lower() in BRANCH_KINDS), None)
    keys, us = extract_jira_keys(name, key_pattern), extract_us_ids(name)
    convention = re.compile(rf"^feature/({'|'.join(BRANCH_KINDS)})/(?:{key_pattern})-US\d+\.\d+-.+", re.IGNORECASE)
    return BranchRef(kind, keys[0] if keys else None, us[0] if us else None, bool(convention.match(name)))


@dataclass(frozen=True)
class PRRef:
    jira_key: str | None
    us_id: str | None
    follows_convention: bool


def parse_pr_title(title: str | None, key_pattern: str) -> PRRef:
    """`[JH-123] US2.1 — Cadastro de cliente`. A chave entre colchetes tem prioridade."""
    title = title or ""
    bracket = re.match(rf"^\s*\[({key_pattern})\]", title, re.IGNORECASE)
    keys = extract_jira_keys(title, key_pattern)
    us = extract_us_ids(title)
    convention = re.compile(rf"^\s*\[(?:{key_pattern})\]\s+US\d+\.\d+\s+[—–-]\s+\S", re.IGNORECASE)
    key = bracket.group(1).upper() if bracket else (keys[0] if keys else None)
    return PRRef(key, us[0] if us else None, bool(convention.match(title)))


# ------------------------------------------------------------------ resolução commit/branch/PR <-> item
# Regra do time: Commit = Subtask; Branch = User Story; PR = User Story.
#   * `jira_key` do commit é SEMPRE a chave citada na PRÓPRIA mensagem. A chave/US herdada da PR ou da branch
#     fica separada (`ref_jira_key` / `ref_us_id`) e nunca vira "chave de Subtask".
#   * Um commit só pertence a uma Subtask quando a mensagem cita a chave dela. Chave da Story, ID visual
#     (US2.1) e referência de PR/branch relacionam o commit à STORY, nunca a todas as Subtasks dela.
def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Coluna do DataFrame ou série vazia (None) quando ela não existe (frames antigos/de teste)."""
    return df[name] if name in df else pd.Series([None] * len(df), index=df.index, dtype="object")


def _story_mask(df: pd.DataFrame, story_key: str, us_id: str | None, child_keys: set[str] | frozenset[str],
                known_keys: set[str]) -> pd.Series:
    """Linhas (commit/branch/PR) que pertencem a UMA User Story. A chave oficial do Jira vence o ID visual.

    1. chave própria = a Story ou uma Subtask dela;
    2. sem chave própria conhecida: chave herdada da PR/branch (`ref_jira_key`) = a Story;
    3. sem chave própria conhecida: ID visual (US2.1) igual ao da Story.
    Se a linha cita a chave de OUTRA issue conhecida, nem a referência nem o ID visual a trazem para cá.
    """
    own = _col(df, "jira_key")
    unknown_own = ~own.isin(known_keys)
    m = own.isin(set(child_keys) | {story_key})
    m |= (_col(df, "ref_jira_key") == story_key) & unknown_own
    if us_id:
        m |= (_col(df, "us_id") == us_id) & unknown_own
    return m.fillna(False).astype(bool)


def commits_for_item(commits: pd.DataFrame, item: pd.Series, known_keys: set[str]) -> pd.DataFrame:
    """Commits de UMA task (Subtask/Bug): só os que citam a chave DELA na mensagem.

    Exceção: item "standalone" (story sem filhos, bug solto), que é a própria User Story — nele valem as
    regras de vínculo de Story (`commits_for_story`).
    """
    if commits.empty:
        return commits
    m = commits["jira_key"] == item["subtask_key"]
    if item["story_key"] == item["subtask_key"]:
        us = item.get("us_id")
        m |= _story_mask(commits, item["story_key"], us if pd.notna(us) else None, frozenset(), known_keys)
    return commits[m].sort_values("date", ascending=False)


def commits_for_story(commits: pd.DataFrame, story_key: str, us_id: str | None,
                      child_keys: set[str], known_keys: set[str]) -> pd.DataFrame:
    """Commits de uma User Story inteira (chave da story, de qualquer filha, referência de PR/branch ou ID visual)."""
    if commits.empty:
        return commits
    return commits[_story_mask(commits, story_key, us_id, child_keys, known_keys)].sort_values("date", ascending=False)


def story_level_commits(commits: pd.DataFrame, story_key: str, us_id: str | None,
                        child_keys: set[str], known_keys: set[str]) -> pd.DataFrame:
    """Commits da Story que NÃO citam uma Subtask (só a Story, a PR/branch ou o ID visual). Não provam execução de Subtask."""
    cs = commits_for_story(commits, story_key, us_id, child_keys, known_keys)
    return cs if cs.empty else cs[~cs["jira_key"].isin(set(child_keys))]


def branches_for_story(branches: pd.DataFrame, story_key: str, us_id: str | None,
                       child_keys: set[str], known_keys: set[str]) -> pd.DataFrame:
    """Branches de uma User Story: a chave do Jira vence; o ID visual só vale para branch sem chave conhecida."""
    if branches.empty:
        return branches
    not_default = ~_col(branches, "is_default").fillna(False).astype(bool)
    return branches[_story_mask(branches, story_key, us_id, child_keys, known_keys) & not_default]


def prs_for_story(prs: pd.DataFrame, story_key: str, us_id: str | None,
                  child_keys: set[str], known_keys: set[str]) -> pd.DataFrame:
    """Pull Requests de uma User Story (mesma regra das branches)."""
    if prs.empty:
        return prs
    return prs[_story_mask(prs, story_key, us_id, child_keys, known_keys)]


def display_id(jira_key: object, us_id: object) -> str:
    """Identificador para exibir: chave oficial do Jira primeiro, ID visual depois (`JH-123 · US2.1`)."""
    parts = [str(v) for v in (jira_key, us_id) if v is not None and not (not isinstance(v, (list, tuple)) and pd.isna(v)) and str(v)]
    return " · ".join(dict.fromkeys(parts))
