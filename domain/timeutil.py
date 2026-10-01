"""Fuso horário único do Moonfoxes: America/Sao_Paulo (nunca o fuso do servidor).

Regra: TODO timestamp que entra no sistema vira tz-aware em `TZ`. Para agrupar por dia usa-se a data
LOCAL (`local_date`), nunca a data UTC — um commit às 22h em São Paulo é 01h UTC do dia seguinte.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

TZ_NAME = "America/Sao_Paulo"
TZ = ZoneInfo(TZ_NAME)


def parse_ts(value: object) -> pd.Timestamp:
    """Converte string ISO 8601 (Jira `...-0300`, GitHub `...Z`) em Timestamp tz-aware local, ou NaT.

    As duas APIs sempre enviam offset; um valor sem offset é interpretado como horário local.
    """
    if value is None or (not isinstance(value, pd.Timestamp) and pd.isna(value)) or value == "":
        return pd.NaT
    ts = pd.to_datetime(value, format="ISO8601", errors="coerce")
    if pd.isna(ts):
        return pd.NaT
    return ts.tz_localize(TZ) if ts.tzinfo is None else ts.tz_convert(TZ)


def parse_series(values: pd.Series) -> pd.Series:
    """Versão vetorizada de `parse_ts`."""
    return pd.to_datetime(values, utc=True, format="ISO8601", errors="coerce").dt.tz_convert(TZ)


def now() -> pd.Timestamp:
    return pd.Timestamp.now(tz=TZ)


def today() -> pd.Timestamp:
    """Hoje como data local naive à meia-noite (comparável com `local_date`)."""
    return now().tz_localize(None).normalize()


def local_date(ts: object) -> pd.Timestamp:
    """Data local (naive, 00:00) de um Timestamp tz-aware; NaT se não houver valor."""
    ts = parse_ts(ts) if not isinstance(ts, pd.Timestamp) else ts
    if pd.isna(ts):
        return pd.NaT
    ts = ts.tz_localize(TZ) if ts.tzinfo is None else ts.tz_convert(TZ)
    return ts.tz_localize(None).normalize()


def local_dates(series: pd.Series) -> pd.Series:
    """Série tz-aware -> datas locais naive (00:00), prontas para agrupar por dia."""
    return series.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()


def fmt(ts: object, pattern: str = "%d/%m/%Y %H:%M") -> str:
    ts = parse_ts(ts) if not isinstance(ts, pd.Timestamp) else ts
    return "" if pd.isna(ts) else ts.strftime(pattern)
