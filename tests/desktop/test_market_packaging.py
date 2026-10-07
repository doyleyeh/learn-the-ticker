import asyncio
import hashlib
import importlib.metadata
import io
import json
from types import SimpleNamespace

import pytest

from backend.app import yfinance_worker as worker
from backend.app.market_history import MarketDataError
from scripts.package_backend import check_market_dependencies


def test_build_stops_on_absent_or_changed_optional_dependencies(tmp_path):
    (tmp_path / "requirements-market-data.txt").write_text("# reviewed\nyfinance==1.7.0\n")
    def missing(name):
        raise importlib.metadata.PackageNotFoundError(name)
    for version in (missing, lambda _: "999"):
        with pytest.raises(SystemExit, match="requirements-market-data"):
            check_market_dependencies(tmp_path, version=version)


def test_build_requires_unchanged_notices_with_cross_platform_newlines(tmp_path):
    (tmp_path / "requirements-market-data.txt").write_text("yfinance==1.7.0\n")
    notices = tmp_path / "docs/licenses/market"
    notices.mkdir(parents=True)
    notice = notices / "yfinance.txt"
    notice.write_bytes(b"Synthetic license\r\n")
    (notices / "manifest.json").write_text(json.dumps([{"notice": notice.name,
        "sha256": hashlib.sha256(b"Synthetic license\n").hexdigest()}]))
    check_market_dependencies(tmp_path, version=lambda _: "1.7.0")
    notice.write_text("changed")
    with pytest.raises(SystemExit, match="notice differs"):
        check_market_dependencies(tmp_path, version=lambda _: "1.7.0")


@pytest.mark.parametrize("check_only,payload,expected", [
    (True, {}, {"version": worker.VERSION, "network": False}),
    (True, {"symbol": "TEST"}, {"error": "invalid_worker_request"}),
    (False, {}, {"error": "invalid_worker_request"}),
])
def test_dependency_mode_cannot_retrieve(monkeypatch, check_only, payload, expected):
    output = io.BytesIO()
    monkeypatch.setattr(worker.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode())))
    monkeypatch.setattr(worker.sys, "stdout", SimpleNamespace(buffer=output))
    monkeypatch.setattr(worker, "dependency_report", lambda: {"version": worker.VERSION, "network": False})
    monkeypatch.setattr(worker, "retrieve", lambda _: (_ for _ in ()).throw(MarketDataError("invalid_worker_request")))
    worker.main(check_only=check_only)
    assert json.loads(output.getvalue()) == expected


@pytest.mark.parametrize("result", [[], {"error": "raw untrusted diagnostics"},
    {"version": worker.VERSION, "native": "x", "network": True}])
def test_dependency_probe_rejects_malformed_worker_output(monkeypatch, result):
    async def run(request, *, check_only):
        assert request == {} and check_only
        return result
    monkeypatch.setattr(worker, "run_worker", run)
    with pytest.raises(MarketDataError, match="worker_limit"):
        asyncio.run(worker.check_dependencies())


def test_frozen_dependency_probe_uses_same_executable(monkeypatch):
    monkeypatch.setattr(worker.sys, "frozen", True, raising=False)
    assert worker.worker_command(check_only=True) == [worker.sys.executable, "--check-private-market"]
