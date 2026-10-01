from services.cache import SourceCache
from services.results import SourceResult


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def ok(n=1):
    return SourceResult("Jira", data=n)


def test_ok_result_is_cached_until_ttl():
    clk, calls = Clock(), []
    cache = SourceCache(clk)

    def fetch():
        calls.append(1)
        return ok(len(calls))

    assert cache.get("jira", fetch, ttl=100).data == 1
    clk.t = 99
    assert cache.get("jira", fetch, ttl=100).data == 1 and len(calls) == 1
    clk.t = 101
    assert cache.get("jira", fetch, ttl=100).data == 2


def test_failure_is_never_cached():
    cache, calls = SourceCache(Clock()), []

    def fetch():
        calls.append(1)
        return SourceResult.failed("Jira", "falha de autenticação") if len(calls) == 1 else ok()

    assert not cache.get("jira", fetch).ok
    assert cache.get("jira", fetch).ok  # a falha não ficou "presa" em cache
    assert len(calls) == 2


def test_last_good_survives_a_later_failure():
    cache = SourceCache(Clock())
    cache.get("jira", lambda: ok(7), ttl=10)
    cache.get("jira", lambda: SourceResult.failed("Jira", "x"), force=True)
    assert cache.last_good("jira").data == 7


def test_partial_uses_short_ttl():
    clk = Clock()
    cache, calls = SourceCache(clk), []

    def fetch():
        calls.append(1)
        return SourceResult("GitHub", data=1, warnings=["3 issues parciais"])

    cache.get("github", fetch, ttl=1800, partial_ttl=60)
    clk.t = 61
    cache.get("github", fetch, ttl=1800, partial_ttl=60)
    assert len(calls) == 2


def test_sources_are_independent():
    cache = SourceCache(Clock())
    cache.get("jira", lambda: ok(1))
    cache.get("github", lambda: ok(2))
    cache.clear("jira")
    calls = []
    cache.get("github", lambda: calls.append(1) or ok(9))
    assert not calls  # limpar o Jira não invalida o GitHub
    assert cache.get("jira", lambda: ok(5)).data == 5


def test_age_minutes():
    clk = Clock()
    cache = SourceCache(clk)
    cache.get("jira", ok)
    clk.t = 300
    assert cache.age_minutes("jira") == 5
    assert cache.age_minutes("github") is None


# ---------------------------------------------------------------- P0.5: "Atualizar tudo" não pode perder o último dado bom
def test_clear_all_keeps_last_good_so_a_failed_refresh_still_has_data():
    cache = SourceCache(Clock())
    cache.get("jira", lambda: ok(1), ttl=100)
    cache.get("github", lambda: ok(2), ttl=100)
    cache.clear()                                   # botão "Atualizar tudo"
    failed = cache.get("jira", lambda: SourceResult.failed("Jira", "HTTP 500"), ttl=100)
    assert not failed.ok
    assert cache.last_good("jira").data == 1 and cache.last_good("github").data == 2
    assert cache.age_minutes("jira") is not None


def test_clear_one_source_keeps_its_last_good_and_does_not_touch_the_other():
    cache = SourceCache(Clock())
    cache.get("jira", lambda: ok(1), ttl=100)
    cache.get("github", lambda: ok(2), ttl=100)
    cache.clear("jira")
    assert cache.last_good("jira").data == 1
    calls = []
    assert cache.get("github", lambda: calls.append(1) or ok(9), ttl=100).data == 2 and not calls   # github continua fresco
    assert cache.get("jira", lambda: ok(3), ttl=100).data == 3                                      # jira busca de novo


def test_clear_forces_a_new_fetch():
    cache, calls = SourceCache(Clock()), []
    cache.get("jira", lambda: calls.append(1) or ok(len(calls)), ttl=100)
    cache.clear()
    assert cache.get("jira", lambda: calls.append(1) or ok(len(calls)), ttl=100).data == 2


def test_reset_forgets_everything():
    cache = SourceCache(Clock())
    cache.get("jira", lambda: ok(1), ttl=100)
    cache.reset()
    assert cache.last_good("jira") is None and cache.age_minutes("jira") is None


def test_unexpected_failure_result_is_not_cached_and_keeps_last_good():
    cache = SourceCache(Clock())
    cache.get("github", lambda: ok(1), ttl=100)
    cache.clear()
    res = cache.get("github", lambda: SourceResult.unexpected("GitHub", KeyError("commit"), ("segredo",)), ttl=100)
    assert not res.ok and "KeyError" in res.errors[0]
    assert cache.last_good("github").data == 1
    assert cache.get("github", lambda: ok(2), ttl=100).data == 2      # a falha não ficou em cache
