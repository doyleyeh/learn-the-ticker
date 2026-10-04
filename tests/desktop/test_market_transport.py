import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest

from backend.app.data_credentials import DataCredential
from backend.app.market_history import MAX_BYTES, MarketDataError
from backend.app.market_transport import YahooPolicy, fetch_eodhd_prices, yahoo_session
from backend.app import yfinance_worker

START, END = "2026-01-01", "2026-01-31"
CHART = "https://query2.finance.yahoo.com/v8/finance/chart/TEST"
COOKIE = "https://fc.yahoo.com"


def params():
    return {"period1": int(datetime(2026, 1, 1, 5, tzinfo=timezone.utc).timestamp()),
            "period2": int(datetime(2026, 2, 1, 5, tzinfo=timezone.utc).timestamp()),
            "interval": "1d", "includePrePost": False, "events": "div,splits,capitalGains"}


def test_eodhd_secret_is_header_only_and_redirects_are_not_followed():
    calls = []
    def handler(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer synthetic-secret"
        assert "synthetic-secret" not in str(request.url)
        assert request.url.params["from"] == START and request.url.params["to"] == END
        return httpx.Response(302, headers={"Location": "https://other.example/"})
    with pytest.raises(MarketDataError, match="^source_redirect$"):
        fetch_eodhd_prices("TEST.US", START, END, DataCredential("synthetic-secret"), _transport=httpx.MockTransport(handler))
    assert len(calls) == 1


@pytest.mark.parametrize("status,code", [(401, "source_access_denied"), (403, "source_access_denied"),
    (429, "source_rate_limited"), (500, "source_unavailable"), (404, "source_not_found")])
def test_eodhd_denial_is_sanitized_without_retry(status, code):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, content=b"synthetic-secret private diagnostics")
    with pytest.raises(MarketDataError, match="^" + code + "$"):
        fetch_eodhd_prices("TEST.US", START, END, DataCredential("synthetic-secret"), _transport=httpx.MockTransport(handler))
    assert len(calls) == 1


def test_eodhd_stream_is_bounded_and_network_errors_are_redacted():
    for transport, code in (
        (httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * (MAX_BYTES + 1))), "response_size"),
        (httpx.MockTransport(lambda _: (_ for _ in ()).throw(OSError("synthetic-secret"))), "source_unavailable"),
    ):
        with pytest.raises(MarketDataError, match="^" + code + "$"):
            fetch_eodhd_prices("TEST.US", START, END, DataCredential("synthetic-secret"), _transport=transport)


def test_yahoo_exact_anonymous_bootstrap_and_two_chart_gets():
    policy = YahooPolicy("TEST", START, END)
    assert policy.before("GET", COOKIE) == "cookie"
    policy.received("cookie", 404, b"")
    assert policy.before("GET", "https://query1.finance.yahoo.com/v1/test/getcrumb") == "crumb"
    policy.received("crumb", 200, b"anonymous-session-value")
    assert policy.before("GET", CHART, {"range": "1d", "interval": "1d", "crumb": "session"}) == "timezone"
    assert policy.before("GET", CHART, params()) == "history"
    policy.received("history", 200, b"original-json")
    assert policy.raw == b"original-json" and policy.count == 4
    with pytest.raises(MarketDataError, match="request_limit"):
        policy.before("GET", CHART, params())


@pytest.mark.parametrize("method,url,query", [
    ("POST", "https://consent.yahoo.com/v2/collectConsent", {}),
    ("GET", "https://guce.yahoo.com/consent", {}),
    ("GET", "https://query2.finance.yahoo.com/v10/finance/quoteSummary/TEST", {}),
    ("GET", "http://query2.finance.yahoo.com/v8/finance/chart/TEST", params()),
    ("GET", "https://127.0.0.1/v8/finance/chart/TEST", params()),
    ("GET", CHART + "?token=secret", params()),
    ("GET", CHART + "#fragment", params()),
    ("GET", CHART.replace("TEST", "OTHER"), params()),
    ("GET", CHART, {"range": "max", "interval": "1m"}),
    ("GET", CHART, dict(params(), period1=1)),
    ("GET", CHART, dict(params(), includePrePost=True)),
    ("GET", CHART, dict(params(), extra="value")),
])
def test_yahoo_no_wider_requests_or_automatic_consent(method, url, query):
    policy = YahooPolicy("TEST", START, END)
    with pytest.raises(MarketDataError, match="request_not_allowed"):
        policy.before(method, url, query)
    with pytest.raises(MarketDataError, match="request_not_allowed"):
        policy.before("GET", COOKIE)
    assert policy.count == 0


@pytest.mark.parametrize("status,code", [(302, "source_redirect"), (401, "source_access_denied"),
    (403, "source_access_denied"), (429, "source_rate_limited"), (999, "source_access_denied"), (500, "source_unavailable")])
def test_yahoo_sticky_failure_blocks_library_retry_or_cookie_switch(status, code):
    policy = YahooPolicy("TEST", START, END)
    policy.before("GET", CHART, params())
    with pytest.raises(MarketDataError, match=code):
        policy.received("history", status, b"raw-diagnostics")
    with pytest.raises(MarketDataError, match=code):
        policy.before("GET", COOKIE)
    assert policy.count == 1 and policy.raw is None


def test_session_overrides_redirects_timeout_tls_and_bounds_stream_before_buffering():
    calls = []
    class FakeBase:
        def __init__(self, **kwargs):
            assert kwargs == {"trust_env": False, "verify": True, "allow_redirects": False,
                              "impersonate": "chrome", "curl_options": {84: 2, 107: 0, 111: 0}}
        def request(self, method, url, **kwargs):
            calls.append((method, url))
            assert kwargs["timeout"] == 10 and kwargs["verify"] and not kwargs["allow_redirects"]
            assert kwargs["content_callback"](b"original-json") == 13
            return SimpleNamespace(status_code=200, content=b"")
    policy = YahooPolicy("TEST", START, END)
    response = yahoo_session(policy, _base=FakeBase).request("GET", CHART, params=params(), timeout=100, allow_redirects=True)
    assert response.content == policy.raw == b"original-json" and len(calls) == 1
    class Oversize(FakeBase):
        def request(self, method, url, **kwargs):
            assert kwargs["content_callback"](b"x" * (MAX_BYTES + 1)) == 0
            return SimpleNamespace(status_code=200)
    policy = YahooPolicy("TEST", START, END)
    with pytest.raises(MarketDataError, match="response_size"):
        yahoo_session(policy, _base=Oversize).request("GET", CHART, params=params())
    assert policy.raw is None


def test_malformed_worker_request_never_imports_yfinance(monkeypatch):
    def forbidden(*args):
        pytest.fail("dependency access before request validation")
    monkeypatch.setattr(yfinance_worker.importlib.metadata, "version", forbidden)
    for request in ({}, {"symbol": "../../x", "start": START, "end": END}, {"symbol": "TEST", "start": END, "end": START}):
        with pytest.raises(MarketDataError, match="invalid_worker_request"):
            yfinance_worker.retrieve(request)


def test_missing_packaged_worker_fails_without_host_python_or_network_fallback(monkeypatch):
    monkeypatch.setattr(yfinance_worker.sys, "frozen", True, raising=False)
    calls = []
    async def unavailable(*args, **kwargs):
        calls.append(args)
        raise OSError("private diagnostic")
    monkeypatch.setattr(yfinance_worker, "launch_owned", unavailable)
    with pytest.raises(MarketDataError, match="^worker_limit$"):
        asyncio.run(yfinance_worker.fetch_yahoo_history("TEST", START, END))
    assert calls == [(yfinance_worker.sys.executable, "--retrieve-private-market")]
