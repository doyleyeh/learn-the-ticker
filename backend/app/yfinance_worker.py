"""Disposable yfinance process: no vault access, user config, logs or retained cookies."""
from __future__ import annotations

import asyncio
import base64
import contextlib
from datetime import timedelta
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import sys
import tempfile

from backend.app.market_history import MAX_BYTES, MarketDataError, _window, parse_yahoo_chart, valid_symbol
from backend.app.market_transport import TRANSPORT_ERRORS, YahooPolicy, yahoo_session
from backend.app.owned_process import close_owned, launch_owned

VERSION = "1.7.0"
MAX_OUTPUT = MAX_BYTES * 2
MEMORY_LIMIT = 1024 * 1024 * 1024
TIMEOUT = 55
ERRORS = TRANSPORT_ERRORS | {"worker_limit", "dependency_unavailable", "invalid_worker_request", "history_unavailable"}


def retrieve(request):
    if not isinstance(request, dict) or set(request) != {"symbol", "start", "end"}:
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
    policy = YahooPolicy(symbol, first.isoformat(), last.isoformat())
    with yahoo_session(policy) as session:
        try:
            yf.Ticker(symbol, session=session).history(start=first.isoformat(),
                end=(last + timedelta(days=1)).isoformat(), interval="1d", prepost=False,
                actions=True, auto_adjust=False, back_adjust=False, repair=False, keepna=True,
                rounding=False, timeout=10, raise_errors=True)
        except Exception:
            raise MarketDataError(policy.error or "history_unavailable") from None
    if policy.error or policy.raw is None:
        raise MarketDataError(policy.error or "history_unavailable")
    # Admission later parses original JSON with Decimal, never the returned DataFrame.
    return {"raw": base64.b64encode(policy.raw).decode("ascii"), "requests": policy.count, "version": VERSION}


def main():
    logging.disable(logging.CRITICAL)
    try:
        wire = sys.stdin.buffer.read(2049)
        if len(wire) > 2048:
            raise MarketDataError("invalid_worker_request")
        with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            result = retrieve(json.loads(wire))
        output = json.dumps(result).encode()
        if len(output) > MAX_OUTPUT:
            raise MarketDataError("worker_limit")
    except MarketDataError as exc:
        code = str(exc) if str(exc) in ERRORS else "history_unavailable"
        output = json.dumps({"error": code}).encode()
    except Exception:
        output = b'{"error":"history_unavailable"}'
    sys.stdout.buffer.write(output)


async def fetch_yahoo_history(symbol, start, end):
    valid_symbol(symbol)
    _window(start, end)
    # This adapter is not yet a qualified packaged application feature.
    if getattr(sys, "frozen", False):
        raise MarketDataError("dependency_unavailable")
    root = Path(__file__).resolve().parents[2]
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ}
    environment.update({"PYTHONPATH": str(root), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
    process = None
    with tempfile.TemporaryDirectory(prefix="ltt-yahoo-") as workspace:
        try:
            process = await launch_owned(sys.executable, "-m", "backend.app.yfinance_worker",
                cwd=workspace, env=environment, memory_limit=MEMORY_LIMIT,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            wire = json.dumps({"symbol": symbol, "start": start, "end": end}).encode()
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
            if (not isinstance(value, dict) or set(value) != {"raw", "requests", "version"}
                    or value["version"] != VERSION or type(value["requests"]) is not int
                    or not 1 <= value["requests"] <= 4):
                raise MarketDataError("worker_limit")
            raw = base64.b64decode(value["raw"], validate=True)
            return parse_yahoo_chart(raw, symbol, start, end), value["requests"]
        except MarketDataError:
            raise
        except (OSError, ValueError, TypeError, TimeoutError):
            raise MarketDataError("worker_limit") from None
        finally:
            await close_owned(process)


if __name__ == "__main__":
    main()
