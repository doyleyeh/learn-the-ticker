import asyncio
import json
from datetime import timedelta

import pytest

from backend.app.api import create_app
from backend.app.contracts import AssetIdentity, EvidenceBundle, ResearchRequest, now
from backend.app.db import Database
from backend.app.identity import INDEX_URL, ResolvedIdentity, SecIdentityResolver, identity_hash, parse_sec_listings, select_exact
from tests.desktop.test_application import FakeRuntime, IDENTITY, StaticIdentityResolver, TOKEN, payload


def listing_bytes(rows=None):
    return json.dumps({"fields": ["cik", "name", "ticker", "exchange"], "data": rows if rows is not None else [
        [1, "Synthetic Company", "ALPHA", "Nasdaq"], [1, "Synthetic Company", "ALPHA.B", "Nasdaq"],
        [2, "Other Company", "ALPHA", "NYSE"], [3, "Unlisted Company", "UNL", None],
    ]}).encode()


def test_uncached_listings_classes_and_ambiguity_are_independent_of_provider():
    rows = parse_sec_listings(listing_bytes(), now())
    assert len(select_exact("ALPHA", rows)) == 2
    assert len(select_exact("synthetic  company", rows)) == 2
    chosen = select_exact("sec:0000000001:nasdaq:alpha.b", rows)
    assert len(chosen) == 1 and chosen[0].asset.identifiers == {"cik": "0000000001"}
    assert chosen[0].asset.asset_type == "unknown" and chosen[0].asset.currency is None
    assert str(chosen[0].verification.source_url) == INDEX_URL and chosen[0].valid(now())
    assert not select_exact("ALP", rows) and not select_exact("Tell me about ALPHA", rows)
    assert not select_exact("UNL", rows)


@pytest.mark.parametrize("record", [
    [True, "Name", "X", "Nasdaq"], [0, "Name", "X", "Nasdaq"], [10**10, "Name", "X", "Nasdaq"],
    [1, "", "X", "Nasdaq"], [1, "Name", "X/other", "Nasdaq"], [1, "Name", "X", ""],
    [1, "Name", "X", 3], [1, "Name", "X"], [1, "Name", "X", "Nasdaq", "extra"],
])
def test_malformed_independent_listing_fails_closed(record):
    with pytest.raises(ValueError):
        parse_sec_listings(listing_bytes([record]), now())


@pytest.mark.parametrize("raw", [b'{}', b'[]', b'{"fields":[],"fields":[],"data":[]}', listing_bytes([]),
                                   listing_bytes([[1, "First", "X", "Nasdaq"], [1, "Conflicting", "X", "Nasdaq"]])])
def test_wrong_duplicate_or_empty_registry_never_partially_certifies(raw):
    with pytest.raises(ValueError):
        parse_sec_listings(raw, now())


def test_resolver_fetch_is_bounded_cached_and_contact_not_part_of_records():
    calls, at = [], now()
    def fetch(url, **kwargs):
        calls.append((url, kwargs))
        return listing_bytes()
    resolver = SecIdentityResolver(fetcher=fetch, user_agent="Synthetic/1 test@example.invalid", clock=lambda: at)
    first = resolver.resolve("ALPHA")
    assert len(first) == 2 and len(calls) == 1
    assert resolver.resolve("OTHER COMPANY") and len(calls) == 1
    assert "test@example.invalid" not in repr(first)
    at += timedelta(hours=2)
    # Per-instance cooldown is monotonic, independent of source/clock timestamps.
    resolver._attempted -= 61
    assert resolver.resolve("ALPHA") and len(calls) == 2
    assert all(url == INDEX_URL and kwargs["accept"] == "application/json" for url, kwargs in calls)


@pytest.mark.parametrize("contact", ["", "Generic app", "Synthetic x@y.z\r\nAuthorization: secret", "é test@example.invalid"])
def test_missing_or_unsafe_contact_never_fetches(contact):
    resolver = SecIdentityResolver(fetcher=lambda *a, **k: pytest.fail("unexpected network request"), user_agent=contact)
    assert resolver.resolve("ALPHA") == []


def test_failed_refresh_does_not_reuse_old_registry_or_retry():
    at, calls = now(), []
    def fetch(*args, **kwargs):
        calls.append(True)
        if len(calls) > 1:
            raise OSError("private diagnostics")
        return listing_bytes()
    resolver = SecIdentityResolver(fetcher=fetch, user_agent="Synthetic test@example.invalid", clock=lambda: at)
    assert resolver.resolve("ALPHA")
    at += timedelta(hours=2)
    resolver._attempted -= 61
    with pytest.raises(OSError):
        resolver.resolve("ALPHA")
    assert resolver.resolve("ALPHA") == [] and len(calls) == 2


@pytest.mark.parametrize("attribute,value", [
    ("exchange", "OTHER"), ("symbol", "WRONG"), ("asset_type", "option"), ("currency", "EUR"),
    ("name", "Other Company"), ("identifiers", {"cik": "0000000002"}),
    ("identifiers", {"expiry": "2030-01-01", "strike": "10", "right": "call"}),
])
def test_same_id_cannot_change_listing_contract_or_class(tmp_path, attribute, value):
    async def run():
        proposed = payload()
        proposed["candidates"][0][attribute] = value
        db = Database("sqlite://", testing=True)
        db.put("settings", "settings", {"cloud_enabled": True})
        runtime = FakeRuntime(proposed)
        service = create_app(db, TOKEN, tmp_path, adapters={"codex": runtime}, identity_resolver=StaticIdentityResolver(),
                             verifier=lambda *a: pytest.fail("Identity must precede source retrieval")).state.service
        result = await service.submit(ResearchRequest(query="ALPHA"))
        await service.tasks[result["id"]]
        assert db.job(result["id"])["status"] == "needs_identity"
        assert not db.list("asset") and not db.list("bundle")
    asyncio.run(run())


def test_independent_ambiguity_does_not_consume_inference(tmp_path):
    async def run():
        db = Database("sqlite://", testing=True)
        db.put("settings", "settings", {"cloud_enabled": True})
        other = IDENTITY.model_copy(update={"id": "OTHER:ALPHA", "exchange": "OTHER"})
        runtime = FakeRuntime(payload())
        service = create_app(db, TOKEN, tmp_path, adapters={"codex": runtime}, identity_resolver=StaticIdentityResolver(IDENTITY, other)).state.service
        result = await service.submit(ResearchRequest(query="ALPHA"))
        await service.tasks[result["id"]]
        assert db.job(result["id"])["status"] == "needs_identity" and runtime.calls == 0
    asyncio.run(run())


def test_unverified_model_identity_is_never_saved(tmp_path):
    async def run():
        db = Database("sqlite://", testing=True)
        db.put("settings", "settings", {"cloud_enabled": True})
        service = create_app(db, TOKEN, tmp_path, adapters={"codex": FakeRuntime(payload())},
                             verifier=lambda *a: pytest.fail("Unresolved identities cannot fetch claims")).state.service
        result = await service.submit(ResearchRequest(query="ALPHA"))
        await service.tasks[result["id"]]
        assert db.job(result["id"])["status"] == "needs_identity" and not db.list("asset")
    asyncio.run(run())


def test_verified_model_proposal_still_requires_confirmation_of_unresolved_request(tmp_path):
    class InitiallyUnresolved(StaticIdentityResolver):
        def resolve(self, query):
            return [] if query == "An unclear user query" else super().resolve(query)
    async def run():
        db = Database("sqlite://", testing=True)
        db.put("settings", "settings", {"cloud_enabled": True})
        runtime = FakeRuntime(payload())
        service = create_app(db, TOKEN, tmp_path, adapters={"codex": runtime}, identity_resolver=InitiallyUnresolved(),
                             verifier=lambda *a: pytest.fail("Unconfirmed scope cannot fetch claims")).state.service
        result = await service.submit(ResearchRequest(query="An unclear user query"))
        await service.tasks[result["id"]]
        job = db.job(result["id"])
        assert job["status"] == "needs_identity" and runtime.calls == 1
        assert job["result"]["candidates"][0]["id"] == IDENTITY.id
        assert "Confirm" in job["result"]["message"] and not db.list("asset") and not db.list("bundle")
    asyncio.run(run())


def test_registered_record_must_bind_full_identity_and_freshness():
    row = StaticIdentityResolver().resolve("ALPHA")[0]
    assert row.valid(now())
    assert not ResolvedIdentity(IDENTITY.model_copy(update={"currency": "USD"}), row.verification).valid(now())
    assert not row.valid(now() + timedelta(days=1))
    assert not row.valid(now() - timedelta(hours=1))


@pytest.mark.parametrize("kind", ["stock", "etf", "fund", "crypto", "option", "bond", "future", "index", "other", "unknown"])
def test_scope_fingerprint_covers_every_asset_category(kind):
    asset = AssetIdentity.model_validate(payload(kind)["candidates"][0])
    assert identity_hash(asset) != identity_hash(asset.model_copy(update={"identifiers": {"contract": "different"}}))


def test_live_helper_is_explicit_and_never_reports_contacts_or_raw_failures():
    from scripts.qualify_sec_identity import check
    class Failure:
        def resolve(self, query):
            raise OSError("PRIVATE_DIAGNOSTICS test@example.invalid")
    assert check(resolver=Failure())["status"] == "not_run"
    result = check(live=True, resolver=Failure())
    assert result["status"] == "blocked" and "PRIVATE" not in str(result) and "@" not in str(result)
    result = check(live=True, resolver=StaticIdentityResolver())
    assert result["status"] == "passed" and "Synthetic Example Company" not in str(result)
