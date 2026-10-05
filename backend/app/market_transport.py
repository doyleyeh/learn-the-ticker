"""Bounded read-only market transports; returned bytes are unadmitted candidates."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, time, timedelta, timezone
from urllib.parse import urlsplit

import httpx

from backend.app.market_history import MAX_BYTES, MarketDataError, _json, _window, valid_symbol

TRANSPORT_ERRORS = frozenset({"source_access_denied", "source_rate_limited", "source_unavailable",
    "request_not_allowed", "request_limit", "response_size", "source_redirect", "source_not_found"})

# Stable libcurl ABI: HTTP_VERSION=84 / HTTP/1.1=2, HTTPAUTH=107,
# PROXYAUTH=111. curl_cffi applies these last, after impersonation options.
# Disable HTTP/2/3 and ambient authentication in the reviewed private worker.
YAHOO_CURL_OPTIONS = {84: 2, 107: 0, 111: 0}


def status_error(status, *, cookie=False):
    # fc.yahoo.com's anonymous cookie bootstrap normally returns 404 + Set-Cookie.
    if status == 200 or (cookie and status == 404):
        return None
    if status == 429:
        return "source_rate_limited"
    if status in (401, 403, 451, 999):
        return "source_access_denied"
    if 300 <= status < 400:
        return "source_redirect"
    return "source_not_found" if status == 404 else "source_unavailable"


def fetch_eodhd_prices(symbol, start, end, credential, *, _transport=None):
    """Header auth only. No token in URLs; caller selects an entitled time window."""
    valid_symbol(symbol)
    _window(start, end)
    try:
        with httpx.Client(verify=True, trust_env=False, follow_redirects=False, timeout=15,
                          transport=_transport) as client:
            with client.stream("GET", f"https://eodhd.com/api/eod/{symbol}",
                    headers={"Authorization": "Bearer " + credential.api_key,
                             "User-Agent": "LearnTheTicker/0.2", "Accept": "application/json"},
                    params={"from": start, "to": end, "period": "d", "fmt": "json"}) as response:
                error = status_error(response.status_code)
                if error:
                    raise MarketDataError(error)
                chunks, count = [], 0
                for part in response.iter_bytes(chunk_size=65536):
                    count += len(part)
                    if count > MAX_BYTES:
                        raise MarketDataError("response_size")
                    chunks.append(part)
                return b"".join(chunks)
    except MarketDataError:
        raise
    except Exception:
        raise MarketDataError("source_unavailable") from None


def fetch_free_eodhd_prices(symbol, start, end, credential, *, _transport=None, cancelled=None):
    """Recheck observed free-tier/no-overage scope before a production history call."""
    valid_symbol(symbol)
    first, last = _window(start, end)
    if (last - first).days > 366:
        raise MarketDataError("invalid_window")
    try:
        with httpx.Client(verify=True, trust_env=False, follow_redirects=False, timeout=15, transport=_transport) as client:
            with client.stream("GET", "https://eodhd.com/api/user", headers={
                "Authorization": "Bearer " + credential.api_key, "User-Agent": "LearnTheTicker/0.2", "Accept": "application/json"}) as response:
                error = status_error(response.status_code)
                if error:
                    raise MarketDataError(error)
                raw = bytearray()
                for part in response.iter_bytes(chunk_size=8192):
                    raw.extend(part)
                    if len(raw) > 65536:
                        raise MarketDataError("response_size")
        data = _json(bytes(raw))
        if (not isinstance(data, dict) or any(type(data.get(k)) is not int for k in ("dailyRateLimit", "apiRequests", "extraLimit"))
                or data["dailyRateLimit"] != 20 or data["extraLimit"] != 0 or not 0 <= data["apiRequests"] <= 18):
            raise MarketDataError("account_scope_unqualified")
        if cancelled is not None and cancelled.is_set():
            raise InterruptedError
        return fetch_eodhd_prices(symbol, start, end, credential, _transport=_transport)
    except (MarketDataError, InterruptedError):
        raise
    except Exception:
        raise MarketDataError("source_unavailable") from None


class YahooPolicy:
    """Only a cookie bootstrap, crumb and two chart GETs; denial is sticky."""
    def __init__(self, symbol, start, end):
        self.symbol = valid_symbol(symbol)
        self.first, self.last = _window(start, end)
        self.count = 0
        self.error = None
        self.used = set()
        self.raw = None

    def fail(self, code):
        if self.error is None:
            self.error = code
        raise MarketDataError(self.error)

    def before(self, method, url, params=None):
        if self.error:
            self.fail(self.error)
        if self.count >= 4:
            self.fail("request_limit")
        try:
            parts = urlsplit(url)
            if (method.upper() != "GET" or parts.scheme != "https" or parts.username or parts.password
                    or parts.port is not None or parts.query or parts.fragment):
                raise ValueError
            params = {} if params is None else params
            if not isinstance(params, Mapping):
                raise ValueError
            params = dict(params)
            crumb = params.pop("crumb", None)
            if crumb is not None and (not isinstance(crumb, str) or not 1 <= len(crumb) <= 256):
                raise ValueError
            if parts.hostname == "fc.yahoo.com" and parts.path in ("", "/") and not params and crumb is None:
                kind = "cookie"
            elif (parts.hostname in ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
                    and parts.path == "/v1/test/getcrumb" and not params and crumb is None):
                kind = "crumb"
            else:
                kind = self.data_kind(parts, params)
            if kind in self.used:
                raise ValueError
        except (ValueError, TypeError, AttributeError, OverflowError):
            self.fail("request_not_allowed")
        self.used.add(kind)
        self.count += 1
        return kind

    def data_kind(self, parts, params):
        if (parts.hostname not in ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
                or parts.path != f"/v8/finance/chart/{self.symbol}"):
            raise ValueError
        if params == {"range": "1d", "interval": "1d"}:
            return "timezone"
        if (set(params) != {"period1", "period2", "interval", "includePrePost", "events"}
                or params["interval"] != "1d" or params["includePrePost"] is not False
                or params["events"] != "div,splits,capitalGains"):
            raise ValueError
        for key, day in (("period1", self.first), ("period2", self.last + timedelta(days=1))):
            stamp = params[key]
            midnight = int(datetime.combine(day, time(), timezone.utc).timestamp())
            # yfinance converts exchange-local midnight to UTC, not system-local time.
            if type(stamp) is not int or abs(stamp - midnight) > 14 * 3600:
                raise ValueError
        return "history"

    def received(self, kind, status, raw):
        error = status_error(status, cookie=kind == "cookie")
        if error:
            self.fail(error)
        if len(raw) > (MAX_BYTES if kind in ("history", "timezone", "valuation") else 65536):
            self.fail("response_size")
        if kind in ("history", "valuation"):
            self.raw = raw


class YahooValuationPolicy(YahooPolicy):
    """Only anonymous bootstrap and one exact bounded valuation request."""
    def data_kind(self, parts, params):
        from backend.app.market_valuations import valuation_request
        url, expected = valuation_request(self.symbol, self.first.isoformat(), self.last.isoformat())
        if parts.geturl() != url or params != expected or any(type(params.get(k)) is not int for k in ("period1", "period2")):
            raise ValueError
        return "valuation"


def yahoo_session(policy, *, _base=None):
    """Restrict the pinned library at its session boundary, including its retries."""
    if _base is None:
        from curl_cffi.requests import Session
        _base = Session

    class BoundedSession(_base):
        def request(self, method, url, **kwargs):
            kind = policy.before(method, url, kwargs.get("params"))
            # No foreign form submission, custom proxy, credentials or response hook.
            if set(kwargs) - {"params", "timeout", "allow_redirects"}:
                policy.fail("request_not_allowed")
            parts, size = [], 0
            limit = MAX_BYTES if kind in ("history", "timezone", "valuation") else 65536
            def collect(part):
                nonlocal size
                size += len(part)
                if size > limit:
                    policy.error = "response_size"
                    return 0  # libcurl aborts writing; no unbounded body accumulation.
                parts.append(part)
                return len(part)
            try:
                response = super().request(method, url, params=kwargs.get("params"), timeout=10,
                    allow_redirects=False, verify=True, content_callback=collect)
                if policy.error:
                    policy.fail(policy.error)
                raw = b"".join(parts)
                policy.received(kind, response.status_code, raw)
                response.content = raw
                return response
            except MarketDataError:
                raise
            except Exception:
                policy.fail(policy.error or "source_unavailable")

    # Anonymous library session only. Never import browser or user login cookies.
    return BoundedSession(trust_env=False, verify=True, allow_redirects=False, impersonate="chrome",
                          curl_options=dict(YAHOO_CURL_OPTIONS))
