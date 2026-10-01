"""Escape de HTML/Markdown e busca textual literal.

Todo texto vindo do Jira/GitHub (títulos, branches, nomes...) é NÃO CONFIÁVEL. Ele só entra em HTML
por `esc()`; trechos de HTML já seguros (gerados pelos componentes da app) são marcados com `Safe`.
"""
from __future__ import annotations

import html
import re
import unicodedata

import pandas as pd


class Safe(str):
    """HTML já seguro (produzido por componentes desta aplicação). `esc()` não escapa de novo."""

    __slots__ = ()


def esc(value: object) -> Safe:
    """Escapa `value` para uso em HTML. None/NaN viram string vazia; `Safe` passa direto."""
    if isinstance(value, Safe):
        return value
    if value is None:
        return Safe("")
    if not isinstance(value, (list, tuple, dict, set)) and pd.isna(value):
        return Safe("")
    return Safe(html.escape(str(value), quote=True))


_MD_SPECIAL = re.compile(r"([\\`*_\[\]()<>|~$#])")


def md_esc(value: object) -> str:
    """Escapa caracteres com significado em Markdown (usar em st.markdown SEM unsafe_allow_html)."""
    if value is None or (not isinstance(value, (list, tuple, dict, set)) and pd.isna(value)):
        return ""
    return _MD_SPECIAL.sub(r"\\\1", str(value))


def strip_accents(text: object) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(text or "")) if unicodedata.category(c) != "Mn")


def literal_contains(series: pd.Series, term: str, case: bool = False) -> pd.Series:
    """Busca de TEXTO LITERAL (regex=False): `(`, `[`, `*`, `+` não quebram nem viram padrão."""
    return series.fillna("").astype(str).str.contains(term, case=case, regex=False, na=False)
