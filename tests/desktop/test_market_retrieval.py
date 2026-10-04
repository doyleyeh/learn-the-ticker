import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from backend.app.data_credentials import DataCredential
from backend.app.market_history import MarketDataError, PriceBar, parse_eodhd_prices
from backend.app.market_retrieval import retrieve_history
from backend.app import yfinance_worker as worker
from scripts.qualify_market_history import check

START, END = "2021-01-01", "2026-01-01"
PRIMARY_START = "2025-01-01"


def candidate():
    value = parse_eodhd_prices(b"[]", "TEST.US", START, END)
    bars = tuple(PriceBar(day, "1", "1", "1", "1", "1", "100") for day in (START, END))
    return replace(value, provider="yahoo_yfinance", symbol="TEST", bars=bars, gaps=("instrument_mapping_unverified",))


def test_incomplete_primary_triggers_selected_fallback_without_splicing():
    calls = []
    def primary(symbol, start, end, credential):
        calls.append(("eodhd", symbol, start, end))
        return json.dumps([{"date": end, "open": 999, "high": 999, "low": 999,
                            "close": 999, "adjusted_close": 999, "volume": 1}]).encode()
    async def fallback(symbol, start, end):
        calls.append(("yahoo", symbol, start, end))
        return candidate(), 4
    value = asyncio.run(retrieve_history("TEST", START, END, credential=DataCredential("synthetic"),
        eodhd_start=PRIMARY_START, eodhd_fetch=primary, yahoo_fetch=fallback))
    assert calls == [("eodhd", "TEST.US", PRIMARY_START, END), ("yahoo", "TEST", START, END)]
    assert value.primary.bars[0].close == "999"
    assert all(bar.close == "1" for bar in value.selected.bars)
    assert value.gaps == ("eodhd:requested_history_incomplete",) and value.yahoo_requests == 4


@pytest.mark.parametrize("error", ["source_access_denied", "source_rate_limited", "source_redirect", "source_unavailable"])
def test_denied_or_failed_primary_never_causes_equivalent_extraction(error):
    def primary(*args):
        raise MarketDataError(error)
    async def forbidden(*args):
        pytest.fail("fallback after failure")
    value = asyncio.run(retrieve_history("TEST", START, END, credential=DataCredential("synthetic"),
        eodhd_start=PRIMARY_START, eodhd_fetch=primary, yahoo_fetch=forbidden))
    assert value.selected is None and value.gaps == ("eodhd:" + error,)


def test_yahoo_failure_preserves_primary_as_partial_and_does_not_retry():
    calls = []
    async def unavailable(*args):
        calls.append(1)
        raise MarketDataError("source_rate_limited")
    value = asyncio.run(retrieve_history("TEST", START, END, credential=DataCredential("synthetic"),
        eodhd_start=PRIMARY_START, eodhd_fetch=lambda *args: b"[]", yahoo_fetch=unavailable))
    assert value.primary is value.selected and len(calls) == 1
    assert value.gaps[-1] == "yahoo:source_rate_limited"


def test_sufficient_primary_does_not_contact_yahoo():
    def primary(*args):
        return json.dumps([{"date": day, "open": 1, "high": 1, "low": 1, "close": 1,
                            "adjusted_close": 1, "volume": 1} for day in (PRIMARY_START, END)]).encode()
    async def forbidden(*args):
        pytest.fail("unnecessary fallback")
    value = asyncio.run(retrieve_history("TEST", PRIMARY_START, END, credential=DataCredential("synthetic"),
        eodhd_start=PRIMARY_START, eodhd_fetch=primary, yahoo_fetch=forbidden))
    assert value.selected is value.primary and not value.gaps and value.yahoo_requests == 0


def test_explicit_helper_default_never_accesses_vault_or_network():
    class Forbidden:
        def load(self, *args):
            pytest.fail("vault access without --live")
    assert asyncio.run(check(store=Forbidden()))["status"] == "not_run"
    async def failing(*args, **kwargs):
        raise OSError("synthetic-secret")
    report = asyncio.run(check(live=True, symbol="TEST", store=type("Missing", (), {"load": lambda *args: None})(),
                               retrieve=failing, at=datetime(2026, 10, 4, tzinfo=timezone.utc)))
    assert report["status"] == "blocked" and "synthetic-secret" not in str(report)


@pytest.mark.parametrize("frozen", [False, True])
def test_worker_uses_private_workspace_allowlisted_environment_and_fixed_errors(monkeypatch, frozen):
    paths, closed = [], []
    class Input:
        def write(self, wire):
            assert set(json.loads(wire)) == {"symbol", "start", "end"}
        async def drain(self):
            pass
        def close(self):
            pass
    async def launch(*args, **kwargs):
        if frozen:
            assert args == (worker.sys.executable, "--retrieve-private-market")
            assert "PYTHONPATH" not in kwargs["env"]
        else:
            assert "-m" in args and args[-1] == "backend.app.yfinance_worker"
        assert "EODHD_API_KEY" not in kwargs["env"] and "HTTP_PROXY" not in kwargs["env"]
        paths.append(Path(kwargs["cwd"]))
        assert paths[-1].is_dir() and not list(paths[-1].iterdir())
        output = asyncio.StreamReader()
        output.feed_data(b'{"error":"source_rate_limited"}')
        output.feed_eof()
        async def wait():
            return 0
        return type("Process", (), {"stdin": Input(), "stdout": output, "returncode": 0, "wait": staticmethod(wait)})()
    async def close(process):
        closed.append(process)
    monkeypatch.setenv("EODHD_API_KEY", "synthetic-secret")
    monkeypatch.setenv("HTTP_PROXY", "http://untrusted.example")
    monkeypatch.setattr(worker.sys, "frozen", frozen, raising=False)
    monkeypatch.setattr(worker, "launch_owned", launch)
    monkeypatch.setattr(worker, "close_owned", close)
    with pytest.raises(MarketDataError, match="source_rate_limited"):
        asyncio.run(worker.fetch_yahoo_history("TEST", START, END))
    assert len(closed) == 1 and all(not path.exists() for path in paths)


def test_worker_cancellation_closes_process_before_removing_workspace(monkeypatch):
    closed = []
    async def scenario():
        launched = asyncio.Event()
        class Input:
            def write(self, _):
                pass
            async def drain(self):
                pass
            def close(self):
                pass
        async def launch(*args, **kwargs):
            process = type("Process", (), {"stdin": Input(), "stdout": asyncio.StreamReader(), "path": Path(kwargs["cwd"])})()
            launched.set()
            return process
        async def close(process):
            assert process.path.exists()
            closed.append(process.path)
        monkeypatch.setattr(worker, "launch_owned", launch)
        monkeypatch.setattr(worker, "close_owned", close)
        task = asyncio.create_task(worker.fetch_yahoo_history("TEST", START, END))
        await launched.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())
    assert len(closed) == 1 and not closed[0].exists()
