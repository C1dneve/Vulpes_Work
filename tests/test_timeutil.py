import pandas as pd

from domain import timeutil


def test_jira_offset_without_colon():
    ts = timeutil.parse_ts("2026-09-24T15:04:05.123-0300")
    assert str(ts.tz) == "America/Sao_Paulo"
    assert (ts.hour, ts.minute) == (15, 4)


def test_github_utc_z_is_converted_to_sao_paulo():
    ts = timeutil.parse_ts("2026-09-25T01:00:00Z")
    assert (ts.day, ts.hour) == (24, 22)  # 01h UTC = 22h do dia anterior em SP


def test_local_date_is_not_utc_date():
    assert timeutil.local_date("2026-09-25T01:00:00Z") == pd.Timestamp("2026-09-24")
    assert timeutil.local_date("2026-09-24T23:30:00.000-0300") == pd.Timestamp("2026-09-24")


def test_invalid_and_empty_become_nat():
    assert pd.isna(timeutil.parse_ts(None))
    assert pd.isna(timeutil.parse_ts(""))
    assert pd.isna(timeutil.parse_ts("lixo"))
    assert pd.isna(timeutil.local_date(None))


def test_naive_input_is_local():
    assert timeutil.parse_ts("2026-09-24T10:00:00").hour == 10


def test_series_and_local_dates():
    s = timeutil.parse_series(pd.Series(["2026-09-25T01:00:00Z", "2026-09-24T12:00:00-0300"]))
    assert timeutil.local_dates(s).tolist() == [pd.Timestamp("2026-09-24")] * 2


def test_today_is_naive_midnight_in_sao_paulo():
    t = timeutil.today()
    assert t.tzinfo is None and (t.hour, t.minute) == (0, 0)
