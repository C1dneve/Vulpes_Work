import pytest
import requests

from services.http import ApiError, AuthError, HttpClient, NetworkError, NotFound, PermissionDenied, RateLimited, ServerError, friendly
from tests.fakes import FakeSession, make_response


def client(script, **kw):
    sleeps = []
    c = HttpClient("Jira", session_factory=lambda: FakeSession(script), sleep=sleeps.append, backoff=1.0, **kw)
    c.sleeps = sleeps
    return c


def test_success():
    assert client([make_response(200, {"ok": 1})]).get_json("http://x") == {"ok": 1}


def test_204_returns_empty_dict():
    assert client([make_response(204)]).get_json("http://x") == {}


def test_401_is_auth_error_and_not_retried():
    c = client([make_response(401, {"errorMessages": ["bad creds"]})])
    with pytest.raises(AuthError) as e:
        c.get_json("http://x")
    assert c.calls == 1 and "falha de autenticação" in friendly(e.value)


def test_403_is_permission_denied():
    with pytest.raises(PermissionDenied):
        client([make_response(403, {"message": "Resource not accessible"})]).get_json("http://x")


def test_404_is_not_found():
    with pytest.raises(NotFound):
        client([make_response(404, {"message": "Not Found"})]).get_json("http://x")


def test_429_retries_with_retry_after_then_succeeds():
    c = client([make_response(429, {}, {"Retry-After": "2"}), make_response(200, {"ok": True})])
    assert c.get_json("http://x") == {"ok": True}
    assert c.sleeps == [2.0]


def test_github_primary_rate_limit_403_is_rate_limited_not_permission():
    hdr = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1000"}
    c = HttpClient("GitHub", session_factory=lambda: FakeSession([make_response(403, {"message": "rate limit"}, hdr)]),
                   sleep=lambda s: None, clock=lambda: 990.0, max_wait=5)
    with pytest.raises(RateLimited) as e:  # esperaria 10s > max_wait: não trava a UI
        c.get_json("http://x")
    assert e.value.retry_after == 10.0


def test_429_gives_up_after_max_retries():
    c = client([make_response(429, {}, {"Retry-After": "1"})] * 4, max_retries=3)
    with pytest.raises(RateLimited):
        c.get_json("http://x")
    assert c.calls == 4


def test_5xx_retries_with_exponential_backoff():
    c = client([make_response(502), make_response(503), make_response(200, {"ok": 1})])
    assert c.get_json("http://x") == {"ok": 1}
    assert c.sleeps == [1.0, 2.0]


def test_5xx_persistent_raises_server_error():
    with pytest.raises(ServerError):
        client([make_response(500)] * 4, max_retries=3).get_json("http://x")


def test_timeout_is_retried_then_network_error():
    c = client([requests.Timeout()] * 4, max_retries=3)
    with pytest.raises(NetworkError) as e:
        c.get_json("http://x")
    assert "tempo esgotado" in friendly(e.value)


def test_connection_error_then_success():
    c = client([requests.ConnectionError("boom"), make_response(200, {"ok": 1})])
    assert c.get_json("http://x") == {"ok": 1}


def test_invalid_json_raises():
    r = make_response(200)
    r._content = b"<html>"
    with pytest.raises(ApiError):
        client([r]).get_json("http://x")


def test_rate_headers_are_tracked():
    c = client([make_response(200, {}, {"X-RateLimit-Remaining": "4321", "X-RateLimit-Limit": "5000"})])
    c.get_json("http://x")
    assert c.rate["remaining"] == 4321 and c.rate["limit"] == 5000


def test_friendly_never_leaks_token():
    c = client([make_response(401, {"errorMessages": ["x"]})])
    with pytest.raises(AuthError) as e:
        c.get_json("http://x")
    assert "tok" not in friendly(e.value).lower().replace("token", "")
