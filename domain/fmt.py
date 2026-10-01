"""Formatação de horas, durações e pontos. Ausente é `—`, nunca `0`."""
from __future__ import annotations

import pandas as pd

NA = "—"


def isna(v: object) -> bool:
    return v is None or (not isinstance(v, (list, tuple, dict, set)) and bool(pd.isna(v)))


def fmt_hours(h: object) -> str:
    """8 -> '8h'; 1.5 -> '1.5h'; ausente -> '—'."""
    if isna(h):
        return NA
    return f"{h:.0f}h" if abs(h - round(h)) < 0.05 else f"{h:.1f}h"


def fmt_points(p: object) -> str:
    if isna(p):
        return NA
    return f"{p:.0f}" if abs(p - round(p)) < 1e-9 else f"{p:g}"


def fmt_duration(hours: object) -> str:
    """Duração em tempo CORRIDO (não horário comercial): 28.0 -> '1d 4h'; 5.5 -> '5h 30min'; 0.2 -> '12min'."""
    if isna(hours):
        return NA
    minutes = round(max(float(hours), 0) * 60)
    if minutes < 1:
        return "<1min"
    d, rest = divmod(minutes, 1440)
    h, m = divmod(rest, 60)
    if d:
        return f"{d}d {h}h" if h else f"{d}d"
    if h:
        return f"{h}h {m}min" if m else f"{h}h"
    return f"{m}min"
