"""Pessoas: slug canônico, nome de exibição, mapeamento GitHub -> Jira, bots e sugestões de vínculo."""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

import pandas as pd

from domain.text import strip_accents

DEFAULT_BOTS = {"dependabot", "githubactions", "renovate", "renovatebot", "copilot", "web-flow"}


def slugify(name: object) -> str:
    """'Vitor Assis' -> 'vitor-assis'. Vazio/NaN -> 'nenhum'."""
    if name is None or (not isinstance(name, (list, tuple, dict, set)) and pd.isna(name)) or not str(name).strip():
        return "nenhum"
    s = strip_accents(name).lower().strip().replace(" ", "-")
    return re.sub(r"[^a-z0-9\-]", "", s) or "nenhum"


def simplify(name: object) -> str:
    """Só letras e dígitos minúsculos: 'guilherme-leite1701' == 'GuilhermeLeite1701'."""
    return re.sub(r"[^a-z0-9]", "", strip_accents(name).lower())


def nome_exibicao(slug: object) -> str:
    """Nome 'bonito' SÓ para exibir. Nunca use para agrupar/filtrar (use o slug)."""
    if not slug or slug == "nenhum" or (not isinstance(slug, (list, tuple)) and pd.isna(slug)):
        return "Nenhum"
    return " ".join(p.capitalize() for p in str(slug).split("-"))


def is_bot(login: str | None, name: str | None = None, author_type: str | None = None,
           extra: tuple[str, ...] = ()) -> bool:
    """Bot por tipo da API (`Bot`), sufixo `[bot]` ou lista (padrão + configurada)."""
    if (author_type or "").lower() == "bot":
        return True
    known = DEFAULT_BOTS | {simplify(x) for x in extra}
    for raw in (login, name):
        s = (raw or "").lower()
        if s.endswith("[bot]") or simplify(s.replace("[bot]", "")) in known:
            return True
    return False


@dataclass(frozen=True)
class Author:
    slug: str
    mapped: bool  # True = ligado a alguém do Jira (por mapeamento manual ou por nome igual)


class DevMapper:
    """Mapeia login/nome do GitHub para o slug do colaborador no Jira.

    `mapping` vem do config.json (`dev_mapping`: login -> slug). A chave é comparada por `simplify`,
    então `guilherme-leite1701` e `GuilhermeLeite1701` são a mesma. Quem não estiver no mapeamento
    NÃO é descartado nem "chutado": fica com `mapped=False` e aparece em "Autores não mapeados".
    """

    def __init__(self, mapping: dict[str, str] | None = None, known_slugs: set[str] | None = None):
        self.mapping = {simplify(k): v for k, v in (mapping or {}).items()}
        self.known_slugs = set(known_slugs or ())

    def jira(self, display_name: object) -> str:
        """Slug de um nome vindo do Jira (displayName)."""
        return self.mapping.get(simplify(display_name)) or slugify(display_name)

    def github(self, login: str | None, name: str | None = None) -> Author:
        for raw in (login, name):
            hit = self.mapping.get(simplify(raw)) if raw else None
            if hit:
                return Author(hit, True)
        slug = slugify(login or name)
        return Author(slug, slug in self.known_slugs)


def suggest_matches(login: str | None, name: str | None, slugs: list[str], limit: int = 3) -> list[tuple[str, float]]:
    """Sugestões de colaborador do Jira para um autor não mapeado (ex.: 'Pedro P.' -> pedro-pereira-rodrigues)."""
    queries = [q for q in (login, name) if q]
    scored: list[tuple[str, float]] = []
    for slug in slugs:
        if slug == "nenhum":
            continue
        best = 0.0
        slug_tokens = slug.split("-")
        for q in queries:
            best = max(best, SequenceMatcher(None, simplify(q), simplify(slug)).ratio())
            q_tokens = [t for t in re.split(r"[^a-z0-9]+", strip_accents(q).lower()) if t]
            # todos os tokens do autor são prefixo de tokens do slug, na ordem ("pedro","p" -> pedro,pereira)
            if q_tokens:
                i, ok = 0, True
                for t in q_tokens:
                    while i < len(slug_tokens) and not slug_tokens[i].startswith(t):
                        i += 1
                    if i == len(slug_tokens):
                        ok = False
                        break
                    i += 1
                if ok and len(q_tokens) >= 2:
                    best = max(best, 0.9)
        if best >= 0.5:
            scored.append((slug, round(best, 2)))
    return sorted(scored, key=lambda x: -x[1])[:limit]


def unmapped_authors(commits: pd.DataFrame) -> pd.DataFrame:
    """Autores humanos de commits que não estão ligados a ninguém do Jira, com contagem de commits."""
    cols = ["author_login", "author_name", "author_email", "commits"]
    if commits.empty or "author_mapped" not in commits:
        return pd.DataFrame(columns=cols)
    df = commits[(~commits["author_mapped"]) & (commits["kind"] == "human")]
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = (df.assign(author_login=df["author_login"].fillna(""), author_email=df["author_email"].fillna(""))
           .groupby(["author_login", "author_name", "author_email"], dropna=False).size().reset_index(name="commits"))
    return g.sort_values("commits", ascending=False).reset_index(drop=True)
