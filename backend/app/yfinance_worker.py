"""Disposable yfinance process: no vault access, user config, logs or retained cookies."""
from __future__ import annotations

import asyncio
import base64
import contextlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import sys
import tempfile

from backend.app.market_history import MAX_BYTES, MarketDataError, _window, parse_yahoo_chart, valid_symbol
from backend.app.market_transport import TRANSPORT_ERRORS, YAHOO_CURL_OPTIONS, YahooPolicy, YahooValuationPolicy, yahoo_session
from backend.app.market_valuations import parse_valuations, valuation_request
from backend.app.owned_process import close_owned, launch_owned

VERSION = "1.7.0"
MAX_OUTPUT = MAX_BYTES * 2
MEMORY_LIMIT = 1024 * 1024 * 1024
TIMEOUT = 55
ERRORS = TRANSPORT_ERRORS | {"worker_limit", "dependency_unavailable", "invalid_worker_request", "history_unavailable"}


def retrieve(request):
    valuation = isinstance(request, dict) and request.get("operation") == "valuation"
    expected = {"symbol", "start", "end"} | ({"operation"} if valuation else set())
    if not isinstance(request, dict) or set(request) != expected:
        raise MarketDataError("invalid_worker_request")
    try:
        symbol = valid_symbol(request["symbol"])
        first, last = _window(request["start"], request["end"])
        if importlib.metadata.version("yfinance") != VERSION:
            raise ValueError
        import yfinance as yf
        from yfinance.config import YfConfig
    except (ImportError, importlib.metadata.PackageNotFoundError):
        raise MarketDataError("dependency_unavailable") from None
    except ValueError:
        raise MarketDataError("invalid_worker_request") from None
    # The parent selects a fresh cwd and removes it after the entire process exits.
    yf.set_tz_cache_location(str(Path.cwd() / "yahoo-cache"))
    YfConfig.network.retries = 0
    YfConfig.network.proxy = None
    YfConfig.debug.hide_exceptions = False
    policy = (YahooValuationPolicy if valuation else YahooPolicy)(symbol, first.isoformat(), last.isoformat())
    with yahoo_session(policy) as session:
        try:
            ticker = yf.Ticker(symbol, session=session)
            if valuation:
                url, params = valuation_request(symbol, first.isoformat(), last.isoformat())
                ticker._data.get_raw_json(url, params=params, timeout=10)
            else:
                ticker.history(start=first.isoformat(), end=(last + timedelta(days=1)).isoformat(), interval="1d", prepost=False,
                    actions=True, auto_adjust=False, back_adjust=False, repair=False, keepna=True,
                    rounding=False, timeout=10, raise_errors=True)
        except Exception:
            raise MarketDataError(policy.error or "history_unavailable") from None
    if policy.error or policy.raw is None:
        raise MarketDataError(policy.error or "history_unavailable")
    # Admission later parses original JSON with Decimal, never the returned DataFrame.
    return {"raw": base64.b64encode(policy.raw).decode("ascii"), "requests": policy.count, "version": VERSION}


def dependency_report():
    """Exercise the shipped numerical/native imports without creating a network session."""
    import yfinance
    import pandas
    from curl_cffi import Curl, CurlOpt, CurlHttpVersion
    from curl_cffi.requests.utils import set_curl_options
    if importlib.metadata.version("yfinance") != VERSION or yfinance.__version__ != VERSION:
        raise MarketDataError("dependency_unavailable")
    expected = {CurlOpt.HTTP_VERSION: CurlHttpVersion.V1_1, CurlOpt.HTTPAUTH: 0, CurlOpt.PROXYAUTH: 0}
    if YAHOO_CURL_OPTIONS != expected:
        raise MarketDataError("dependency_unavailable")
    class CheckedCurl(Curl):
        def setopt(self, option, value):
            applied[option] = value
            return super().setopt(option, value)
        def perform(self, *args, **kwargs):
            raise MarketDataError("request_not_allowed")
    applied = {}
    curl = CheckedCurl()
    try:
        native = curl.version().decode("ascii")
        # Configure the real native handle, but never perform this request.
        set_curl_options(curl, "GET", "https://query2.finance.yahoo.com/", impersonate="chrome",
                         params_list=[None, None], headers_list=[None, None], cookies_list=[None, None],
                         proxies_list=[None, None], verify_list=[True, True],
                         allow_redirects=False, curl_options=YAHOO_CURL_OPTIONS)
        if any(applied.get(key) != value for key, value in expected.items()):
            raise MarketDataError("dependency_unavailable")
    finally:
        curl.close()
    if pandas.Series([1, 2]).sum() != 3:
        raise MarketDataError("dependency_unavailable")
    return {"version": VERSION, "native": native, "network": False}


def main(*, check_only=False):
    logging.disable(logging.CRITICAL)
    try:
        wire = sys.stdin.buffer.read(2049)
        if len(wire) > 2048:
            raise MarketDataError("invalid_worker_request")
        with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            request = json.loads(wire)
            if check_only:
                if request != {}:
                    raise MarketDataError("invalid_worker_request")
                result = dependency_report()
            else:
                result = retrieve(request)
        output = json.dumps(result).encode()
        if len(output) > MAX_OUTPUT:
            raise MarketDataError("worker_limit")
    except MarketDataError as exc:
        code = str(exc) if str(exc) in ERRORS else "history_unavailable"
        output = json.dumps({"error": code}).encode()
    except Exception:
        output = b'{"error":"history_unavailable"}'
    sys.stdout.buffer.write(output)


def worker_command(*, check_only=False):
    if getattr(sys, "frozen", False):
        return [sys.executable, "--check-private-market" if check_only else "--retrieve-private-market"]
    return [sys.executable, "-m", "backend.app.yfinance_worker", *(["--check-private-market"] if check_only else [])]


async def run_worker(request, *, check_only=False):
    root = Path(__file__).resolve().parents[2]
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ}
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
    if not getattr(sys, "frozen", False):
        environment["PYTHONPATH"] = str(root)
    process = None
    with tempfile.TemporaryDirectory(prefix="ltt-yahoo-") as workspace:
        # A fresh frozen bootloader also extracts inside this owned disposable tree.
        environment.update({"TEMP": workspace, "TMP": workspace})
        try:
            process = await launch_owned(*worker_command(check_only=check_only),
                cwd=workspace, env=environment, memory_limit=MEMORY_LIMIT,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            wire = json.dumps(request).encode()
            async with asyncio.timeout(TIMEOUT):
                # Bounded read also protects the parent if a library unexpectedly writes stdout.
                process.stdin.write(wire)
                await process.stdin.drain()
                process.stdin.close()
                chunks, count = [], 0
                while part := await process.stdout.read(65536):
                    count += len(part)
                    if count > MAX_OUTPUT:
                        raise MarketDataError("worker_limit")
                    chunks.append(part)
                await process.wait()
            if process.returncode != 0:
                raise MarketDataError("worker_limit")
            value = json.loads(b"".join(chunks))
            if isinstance(value, dict) and set(value) == {"error"} and value["error"] in ERRORS:
                raise MarketDataError(value["error"])
            return value
        except MarketDataError:
            raise
        except (OSError, ValueError, TypeError, TimeoutError):
            raise MarketDataError("worker_limit") from None
        finally:
            await close_owned(process)


async def check_dependencies():
    result = await run_worker({}, check_only=True)
    if (not isinstance(result, dict) or set(result) != {"version", "native", "network"}
            or result["version"] != VERSION or result["network"] is not False
            or not isinstance(result["native"], str) or not 1 <= len(result["native"]) <= 512):
        raise MarketDataError("worker_limit")
    return result


async def fetch_yahoo_history(symbol, start, end):
    return await fetch_candidate(symbol, start, end, valuation=False)


async def fetch_yahoo_valuations(symbol, start, end):
    return await fetch_candidate(symbol, start, end, valuation=True)


async def fetch_candidate(symbol, start, end, *, valuation):
    valid_symbol(symbol)
    _window(start, end)
    value = await run_worker({"symbol": symbol, "start": start, "end": end, **({"operation": "valuation"} if valuation else {})})
    try:
        if (not isinstance(value, dict) or set(value) != {"raw", "requests", "version"}
                or value["version"] != VERSION or type(value["requests"]) is not int
                or not 1 <= value["requests"] <= 4):
            raise MarketDataError("worker_limit")
        raw = base64.b64decode(value["raw"], validate=True)
        parser = parse_valuations if valuation else parse_yahoo_chart
        return replace(parser(raw, symbol, start, end), retrieved_at=datetime.now(timezone.utc)), value["requests"]
    except (ValueError, TypeError):
        raise MarketDataError("worker_limit") from None


if __name__ == "__main__":
    main(check_only=sys.argv[1:] == ["--check-private-market"])
