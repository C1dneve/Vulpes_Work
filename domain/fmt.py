"""Formatação de horas, durações e pontos. Ausente é `—`, nunca `0`."""
from __future__ import annotations

from numbers import Real

import pandas as pd

NA = "—"


def isna(v: object) -> bool:
    return v is None or (not isinstance(v, (list, tuple, dict, set)) and bool(pd.isna(v)))


def _number(value: object) -> float | None:
    """Retorna um número real sem tentar operar sobre valores arbitrários vindos de DataFrames."""
    if isna(value) or not isinstance(value, Real):
        return None
    return float(value)


def fmt_hours(h: object) -> str:
    """8 -> '8h'; 1.5 -> '1.5h'; ausente -> '—'."""
    number = _number(h)
    if number is None:
        return NA
    return f"{number:.0f}h" if abs(number - round(number)) < 0.05 else f"{number:.1f}h"


def fmt_points(p: object) -> str:
    number = _number(p)
    if number is None:
        return NA
    return f"{number:.0f}" if abs(number - round(number)) < 1e-9 else f"{number:g}"


def fmt_duration(hours: object) -> str:
    """Duração em tempo CORRIDO (não horário comercial): 28.0 -> '1d 4h'; 5.5 -> '5h 30min'; 0.2 -> '12min'."""
    number = _number(hours)
    if number is None:
        return NA
    minutes = round(max(number, 0) * 60)
    if minutes < 1:
        return "<1min"
    d, rest = divmod(minutes, 1440)
    h, m = divmod(rest, 60)
    if d:
        return f"{d}d {h}h" if h else f"{d}d"
    if h:
        return f"{h}h {m}min" if m else f"{h}h"
    return f"{m}min"
