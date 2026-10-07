import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.contracts import AssetIdentity, Claim, IdentityVerification, ResearchRequest, RuntimeEvent, Source, SourcePolicy, now
from backend.app.identity import ResolvedIdentity, identity_hash
from backend.app.db import Database, Job
from backend.app.evidence import admit_bundle, factual_context, verify_candidate
from backend.app.runtimes import normalize_cli_event, provider_environment

TOKEN = "test-session-token-" * 4
IDENTITY = AssetIdentity(id="XTEST:ALPHA", symbol="ALPHA", name="Synthetic Example Company", asset_type="stock", exchange="XTEST", identifiers={"cik": "0000000001"})


class StaticIdentityResolver:
    """Explicit synthetic trusted adapter; never installed by the production entrypoint."""
    def __init__(self, *assets):
        self.assets = assets or (IDENTITY,)

    def resolve(self, query):
        return [ResolvedIdentity(asset, IdentityVerification(authority="synthetic-test", source_url="https://identity.example/registry",
                retrieved_at=now(), content_hash="a" * 64, identity_hash=identity_hash(asset))) for asset in self.assets]


def source(**kwargs):
    values = dict(id="s1", asset_id=IDENTITY.id, url="https://www.sec.gov/Archives/edgar/data/1/000000000100000001/synthetic.htm", title="Synthetic filing", publisher="Synthetic regulator")
    return Source(**(values | kwargs))


class FakeRuntime:
    def __init__(self, payload, wait=False):
        self.payload, self.calls, self.wait = payload, 0, wait
        self.started = asyncio.Event()

    async def stream(self, prompt, run_id, workspace, model=None):
        self.calls += 1
        self.started.set()
        if self.wait:
            await asyncio.sleep(30)
        yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps(self.payload))


def payload(kind="stock"):
    return {"candidates": [IDENTITY.model_copy(update={"asset_type": kind}).model_dump(mode="json")], "sources": [source().model_dump(mode="json")], "claims": [Claim(asset_id=IDENTITY.id, kind="fact", text="Synthetic Example Company provides test services.", source_ids=["s1"]).model_dump(mode="json")]}


def test_admission_rejects_self_attestation_wrong_asset_and_unsupported_claims():
    candidate = source(url="https://unreviewed.example/article", verified=True, official=True, policy=SourcePolicy.full_text, excerpt="Fake authoritative text")
    clean = verify_candidate(candidate, IDENTITY, lambda _: pytest.fail("Unreviewed sources must not be fetched"))
    assert not clean.verified and not clean.excerpt and clean.policy == SourcePolicy.link
    bundle = admit_bundle(IDENTITY, [clean], [Claim(asset_id=IDENTITY.id, text="Revenue is 5", source_ids=["s1"], kind="fact", value=5, unit="USD"), Claim(asset_id="other", text="Wrong company", source_ids=["s1"], kind="fact")])
    assert not bundle.claims and not bundle.notes
    assert not factual_context(bundle)["claims"] and not factual_context(bundle)["sources"]


def test_exact_supported_prose_can_be_admitted_with_sources():
    verified = verify_candidate(source(), IDENTITY, lambda _: "Synthetic Example Company provides test services.")
    bundle = admit_bundle(IDENTITY, [verified], [Claim(asset_id=IDENTITY.id, kind="fact", text="Synthetic Example Company provides test services.", source_ids=["s1"])])
    assert len(bundle.claims) == 1 and not bundle.notes
    assert bundle.sources[0].content_hash


def test_model_dates_cannot_establish_weekly_relevance():
    from datetime import date
    candidate = source(published_at=date.today(), as_of=date.today())
    verified = verify_candidate(candidate, IDENTITY, lambda _: "Synthetic Example Company provides test services.")
    assert verified.published_at is None and verified.as_of is None
    claim = Claim(asset_id=IDENTITY.id, kind="fact", section="weekly_news", text="Synthetic Example Company provides test services.", source_ids=["s1"], as_of=date.today())
    bundle = admit_bundle(IDENTITY, [verified], [claim])
    assert not bundle.claims and len(bundle.notes) == 1


def test_rejected_source_cannot_feed_unverified_notes():
    denied = source(policy=SourcePolicy.rejected)
    bundle = admit_bundle(IDENTITY, [denied], [Claim(asset_id=IDENTITY.id, kind="unverified_note", text="Disallowed derived text", source_ids=[denied.id])])
    assert not bundle.sources and not bundle.claims and not bundle.notes


def test_authentication_origin_and_secret_free_health(tmp_path):
    db = Database("sqlite://", testing=True)
    with TestClient(create_app(db, TOKEN, tmp_path)) as client:
        assert client.get("/api/health").status_code == 401
        headers = {"Authorization": "Bearer " + TOKEN}
        assert client.get("/api/health", headers=headers).json() == {"status": "ready", "schema_version": "1"}
        assert client.get("/api/health", headers=headers | {"Origin": "https://evil.example"}).status_code == 403
        assert TOKEN not in client.get("/api/health", headers=headers).text
        assert client.post("/api/research", headers=headers, json={"query": "ALPHA"}).status_code == 409
        with client.websocket_connect("/api/events/missing", headers={"origin": "http://127.0.0.1:1420"}) as socket:
            socket.send_json({"token": "wrong"})
            assert socket.receive()["code"] == 1008


def test_event_stream_disconnect_does_not_send_a_second_close(tmp_path):
    async def scenario():
        db = Database("sqlite://", testing=True)
        app = create_app(db, TOKEN, tmp_path)
        with db.session.begin() as session:
            session.add(Job(id="disconnect-test", request={"query": "Synthetic"}, status="running"))
        app.state.service.emit(RuntimeEvent(run_id="disconnect-test", kind="run.started"))
        incoming = iter([{"type": "websocket.connect"}, {"type": "websocket.receive", "text": json.dumps({"token": TOKEN})}])
        sent = []

        async def receive():
            return next(incoming)

        async def send(message):
            sent.append(message["type"])
            if message["type"] == "websocket.send":
                raise OSError("Synthetic client disconnected during navigation")

        await app({"type": "websocket", "asgi": {"version": "3.0"}, "scheme": "ws", "path": "/api/events/disconnect-test", "query_string": b"", "headers": [(b"origin", b"http://127.0.0.1:1420")], "client": ("127.0.0.1", 1), "server": ("127.0.0.1", 2)}, receive, send)
        assert sent == ["websocket.accept", "websocket.send"]
        assert db.job("disconnect-test")["status"] == "running"
    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["stock", "etf", "crypto", "option", "bond", "other"])
def test_dynamic_research_persistence_reuse_and_saved_versions(tmp_path, kind):
    async def scenario():
        db = Database("sqlite://", testing=True)
        adapter = FakeRuntime(payload(kind))
        app = create_app(db, TOKEN, tmp_path, adapters={"codex": adapter}, identity_resolver=StaticIdentityResolver(IDENTITY.model_copy(update={"asset_type": kind})), verifier=lambda s, a: verify_candidate(s, a, lambda _: "Synthetic Example Company provides test services."))
        service = app.state.service
        db.put("settings", "settings", {"cloud_enabled": True})
        result = await service.submit(ResearchRequest(query="An uncached synthetic asset"))
        await service.tasks[result["id"]]
        job = db.job(result["id"])
        assert job["status"] == "completed", job
        assert job["result"]["asset"]["asset_type"] == kind
        assert len(job["result"]["claims"]) == 1
        old_id = job["result"]["id"]
        # This undated document is preserved offline, never reused as fresh online research.
        db.put("settings", "settings", {"cloud_enabled": False})
        cached = await service.submit(ResearchRequest(query="Same asset", asset_id=IDENTITY.id))
        assert cached["status"] == "cached" and adapter.calls == 1
        db.put("settings", "settings", {"cloud_enabled": True})
        refresh = await service.submit(ResearchRequest(query="Refresh", asset_id=IDENTITY.id, refresh=True))
        await service.tasks[refresh["id"]]
        assert db.get("bundle:" + old_id) and len(db.list("bundle", IDENTITY.id)) == 4
        assert sum(row["completion"] == "section_checkpoint" for row in db.list("bundle", IDENTITY.id)) == 2
        assert all("test services" not in event["text"] for event in db.events(result["id"]))
    asyncio.run(scenario())


def test_ambiguity_and_malformed_output_never_create_facts(tmp_path):
    async def scenario():
        db = Database("sqlite://", testing=True)
        value = payload()
        value["candidates"].append(IDENTITY.model_copy(update={"id": "OTHER:ALPHA"}).model_dump(mode="json"))
        runtime = FakeRuntime(value)
        service = create_app(db, TOKEN, tmp_path, adapters={"codex": runtime}, identity_resolver=StaticIdentityResolver()).state.service
        db.put("settings", "settings", {"cloud_enabled": True})
        job = await service.submit(ResearchRequest(query="ALPHA"))
        await service.tasks[job["id"]]
        assert db.job(job["id"])["status"] == "needs_identity" and not db.list("asset")
        runtime.payload = {"secret": "never expose this malformed payload"}
        job = await service.submit(ResearchRequest(query="ALPHA"))
        await service.tasks[job["id"]]
        assert db.job(job["id"])["status"] == "failed"
        assert "secret" not in json.dumps(db.job(job["id"]))
    asyncio.run(scenario())


def test_cancellation_recovery_and_no_subscription_replay(tmp_path):
    async def scenario():
        db = Database("sqlite://", testing=True)
        runtime = FakeRuntime(payload(), wait=True)
        service = create_app(db, TOKEN, tmp_path, adapters={"codex": runtime}, identity_resolver=StaticIdentityResolver()).state.service
        db.put("settings", "settings", {"cloud_enabled": True})
        job = await service.submit(ResearchRequest(query="ALPHA"))
        await asyncio.wait_for(runtime.started.wait(), 2)
        await service.cancel(job["id"])
        assert db.job(job["id"])["status"] == "cancelled"
        with db.session.begin() as session:
            session.add(Job(id="crashed", request={"query": "ALPHA"}, status="running"))
        db.recover()
        assert db.job("crashed")["status"] == "interrupted" and runtime.calls == 1
    asyncio.run(scenario())


def test_provider_events_strip_reasoning_and_environment_secrets(monkeypatch):
    monkeypatch.setenv("LTT_API_TOKEN", "do-not-pass")
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-pass")
    assert "LTT_API_TOKEN" not in provider_environment() and "OPENAI_API_KEY" not in provider_environment()
    raw = {"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": "private reasoning"}, {"type": "text", "text": "Answer"}]}}
    event = normalize_cli_event("claude", raw, "run")
    assert event.text == "Answer"
    assert normalize_cli_event("gemini", {"type": "thought", "content": "private"}, "run") is None


def test_postgres_required_for_production():
    with pytest.raises(ValueError, match="requires PostgreSQL"):
        Database("sqlite://")
