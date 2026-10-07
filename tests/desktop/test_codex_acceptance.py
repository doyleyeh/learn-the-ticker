import asyncio
import json
from types import SimpleNamespace

import pytest

from backend.app.contracts import RuntimeCapabilities
from backend.app.runtime_base import AIRuntime, RuntimeFailure
from backend.app.runtime_policy import QUALIFICATIONS
from scripts import qualify_codex_acceptance as probe
from tests.desktop.test_codex import FakeRPC


QUOTE = "Stocks represent shares of ownership in a company."
URL = "https://www.investor.gov/example"


@pytest.mark.parametrize("change", [
    {"url": "https://www.investor.gov.evil.test/example"},
    {"url": "https://user:password@www.investor.gov/example"},
    {"url": "https://www.investor.gov/example?private=secret"},
    {"url": "https://www.investor.gov/example#private"},
    {"url": "https://www.investor.gov:444/example"},
    {"url": "http://www.investor.gov/example"},
    {"url": []}, {"quote": []}, {"quote": "short"}, {"quote": "x" * 201}, {"quote": " " * 30},
    {"unexpected": "private"},
])
def test_source_probe_rejects_untrusted_candidate_before_retrieval(tmp_path, monkeypatch, change):
    async def collect(*args, **kwargs): return json.dumps({"url": URL, "quote": QUOTE} | change), 1
    def forbidden(url): pytest.fail("retrieved invalid candidate")
    monkeypatch.setattr(probe, "collect", collect)
    with pytest.raises((RuntimeFailure, ValueError)):
        asyncio.run(probe.source_probe(None, tmp_path, "synthetic", fetcher=forbidden))


@pytest.mark.parametrize("supported,search", [(True, True), (False, True), (True, False)])
def test_source_requires_observed_search_and_independent_exact_support(tmp_path, monkeypatch, supported, search):
    async def collect(*args, **kwargs):
        assert kwargs["browsing"]
        return json.dumps({"url": URL, "quote": QUOTE}), int(search)
    fetched = []
    def fetcher(url):
        fetched.append(url)
        return "Document prefix " + (QUOTE.upper() if supported else "different content")
    monkeypatch.setattr(probe, "collect", collect)
    if supported and search:
        result = asyncio.run(probe.source_probe(None, tmp_path, "synthetic", fetcher=fetcher))
        assert result["quote_independently_supported"] and len(result["document_sha256"]) == 64
        assert QUOTE not in json.dumps(result) and URL not in json.dumps(result)
    else:
        with pytest.raises(RuntimeFailure): asyncio.run(probe.source_probe(None, tmp_path, "synthetic", fetcher=fetcher))
    assert fetched == ([URL] if search else [])


@pytest.mark.parametrize("disconnect", [False, True])
@pytest.mark.parametrize("included", [False, True])
def test_service_probe_exercises_owned_lifecycle_and_never_bypasses_quota(tmp_path, monkeypatch, disconnect, included):
    instances = []
    class ControlledRPC(FakeRPC):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self.account = {"type": "chatgpt"}
            self.process = object()
            self.exited = asyncio.Event()
            instances.append(self)

        async def request(self, method, params, **kwargs):
            if method == "account/rateLimits/read": return {"ordinaryUsageAllowed": included}
            return await super().request(method, params, **kwargs)

        async def event(self):
            await self.exited.wait()
            raise RuntimeFailure("Codex disconnected; reconnect before retrying.")

        async def close(self):
            self.process = None
            self.closed = True
            self.exited.set()

    async def discover(self):
        return RuntimeCapabilities(provider="codex", installed=True, version="synthetic", qualification="protocol_only")

    monkeypatch.setattr(AIRuntime, "check", discover)
    before = dict(QUALIFICATIONS)
    coroutine = probe.service_probe(tmp_path, tmp_path / "workspace", "synthetic-model", "synthetic", disconnect=disconnect, rpc_base=ControlledRPC)
    if included:
        result = asyncio.run(coroutine)
        assert all(result.values())
        assert ("cloud_consent_disabled" in result) != disconnect
    else:
        with pytest.raises(RuntimeFailure, match="could not be exercised"): asyncio.run(coroutine)
        assert all(method != "turn/start" for rpc in instances for method, _ in rpc.requests)
    assert instances and all(rpc.closed for rpc in instances) and QUALIFICATIONS == before


def test_additional_acceptance_stops_on_failure_without_retry_or_promotion(tmp_path, monkeypatch):
    calls = []
    async def enforced(profile): return True
    async def source(*args, **kwargs):
        calls.append("source")
        return {"quote_independently_supported": True}
    async def service(*args, **kwargs):
        calls.append("consent")
        raise RuntimeFailure("private-provider-diagnostic")
    monkeypatch.setattr(probe, "enforcement_ready", enforced)
    monkeypatch.setattr(probe, "source_probe", source)
    monkeypatch.setattr(probe, "service_probe", service)
    before = dict(QUALIFICATIONS)
    report = asyncio.run(probe.acceptance(tmp_path, {"status": "preflight_passed", "version": "synthetic", "model": "synthetic", "live_qualified": False}))
    assert calls == ["source", "consent"] and report["stage"] == "consent"
    assert report["status"] == "blocked" and not report["live_qualified"] and QUALIFICATIONS == before
    assert "private" not in json.dumps(report)


@pytest.mark.parametrize("failure", [False, RuntimeFailure("private-diagnostic")])
def test_failed_enforcement_never_starts_additional_inference(tmp_path, monkeypatch, failure):
    async def enforced(profile):
        if isinstance(failure, Exception): raise failure
        return failure
    async def forbidden(*args, **kwargs): pytest.fail("inference after failed enforcement")
    monkeypatch.setattr(probe, "enforcement_ready", enforced)
    monkeypatch.setattr(probe, "source_probe", forbidden)
    report = asyncio.run(probe.acceptance(tmp_path, {"status": "preflight_passed", "live_qualified": False}))
    assert report["blocker"] == "sandbox_enforcement" and report["generation_requested"] is False
    assert "private" not in json.dumps(report)


def test_default_command_is_preflight_only(tmp_path, monkeypatch, capsys):
    async def preflight(profile, model):
        assert model == "selected"
        return {"status": "preflight_passed", "generation_requested": False, "live_qualified": False}
    async def forbidden(*args): pytest.fail("default invocation requested generation")
    monkeypatch.setattr(probe, "preflight", preflight)
    monkeypatch.setattr(probe, "acceptance", forbidden)
    assert asyncio.run(probe.run(SimpleNamespace(profile=str(tmp_path), model="selected", live=False))) == 0
    assert json.loads(capsys.readouterr().out)["generation_requested"] is False
