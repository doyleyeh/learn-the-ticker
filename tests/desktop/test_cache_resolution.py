import asyncio
from datetime import timedelta

import pytest

from backend.app.contracts import AssetIdentity, EvidenceBundle, ResearchRequest, now
from backend.app.db import Database
from backend.app.research import ResearchService
from tests.desktop.test_application import FakeRuntime, IDENTITY, StaticIdentityResolver, payload


def cache(db, asset=IDENTITY, age=0):
    bundle = EvidenceBundle(asset=asset, created_at=now() - timedelta(days=age)).model_dump(mode="json")
    db.put("asset:" + asset.id, "asset", bundle)
    db.put("bundle:" + bundle["id"], "bundle", bundle, asset.id)
    return bundle


@pytest.mark.parametrize("query", ["ALPHA", " alpha  ", "Synthetic Example Company", "synthetic  example company", "xtest:alpha", "ＡＬＰＨＡ"])
def test_repeated_saved_symbol_name_or_identity_reuses_evidence_without_inference(tmp_path, query):
    async def run():
        db = Database("sqlite://", testing=True)
        expected = cache(db)
        runtime = FakeRuntime(payload())
        service = ResearchService(db, {"codex": runtime}, tmp_path)
        result = await service.submit(ResearchRequest(query=query))
        assert result["status"] == "cached" and result["result"] == expected and runtime.calls == 0
        assert not service.tasks
    asyncio.run(run())


def test_ambiguous_saved_symbols_require_identity_even_offline(tmp_path):
    async def run():
        db = Database("sqlite://", testing=True)
        cache(db)
        alternative = IDENTITY.model_copy(update={"id": "OTHER:ALPHA", "exchange": "OTHER"})
        selected = cache(db, alternative)
        runtime = FakeRuntime(payload())
        service = ResearchService(db, {"codex": runtime}, tmp_path)
        result = await service.submit(ResearchRequest(query="ALPHA"))
        assert result["status"] == "needs_identity" and len(result["result"]["candidates"]) == 2
        result = await service.submit(ResearchRequest(query="other:alpha"))
        assert result["result"] == selected and runtime.calls == 0
    asyncio.run(run())


def test_stale_cached_search_remains_available_offline_but_refresh_is_explicit(tmp_path):
    async def run():
        db = Database("sqlite://", testing=True)
        expected = cache(db, age=90)
        service = ResearchService(db, {}, tmp_path)
        result = await service.submit(ResearchRequest(query="ALPHA"))
        assert result["status"] == "cached" and result["result"]["created_at"] == expected["created_at"]
        with pytest.raises(ValueError, match="disabled"):
            await service.submit(ResearchRequest(query="ALPHA", refresh=True))
    asyncio.run(run())


def test_stale_search_uses_existing_identity_during_incremental_research(tmp_path):
    async def run():
        db = Database("sqlite://", testing=True)
        cache(db, age=10)
        db.put("settings", "settings", {"cloud_enabled": True})
        runtime = FakeRuntime(payload())
        service = ResearchService(db, {"codex": runtime}, tmp_path, identity_resolver=StaticIdentityResolver(), verifier=lambda source, _: source)
        result = await service.submit(ResearchRequest(query="ALPHA"))
        await service.tasks[result["id"]]
        assert db.job(result["id"])["request"]["asset_id"] == IDENTITY.id
        assert runtime.calls == 1 and len(db.list("bundle")) == 2
    asyncio.run(run())


@pytest.mark.parametrize("query", ["ALP", "Tell me about ALPHA", "Different Synthetic Example Company"])
def test_partial_names_and_questions_never_silently_select_a_cached_asset(tmp_path, query):
    async def run():
        db = Database("sqlite://", testing=True)
        cache(db)
        service = ResearchService(db, {}, tmp_path)
        assert not service.cached_identities(query)
        with pytest.raises(ValueError, match="disabled"):
            await service.submit(ResearchRequest(query=query))
    asyncio.run(run())


def test_online_fresh_cache_rechecks_independent_scope_without_inference(tmp_path):
    from tests.desktop.test_research_admission import fresh_bundle
    async def run():
        db = Database("sqlite://", testing=True)
        bundle, request = fresh_bundle()
        for key, kind in (("asset:" + bundle.asset.id, "asset"), ("bundle:" + bundle.id, "bundle")):
            db.put(key, kind, bundle.model_dump(mode="json"))
        db.put("settings", "settings", {"cloud_enabled": True})
        runtime = FakeRuntime(payload())
        service = ResearchService(db, {"codex": runtime}, tmp_path, identity_resolver=StaticIdentityResolver())
        result = await service.submit(request)
        assert result["status"] == "cached" and runtime.calls == 0
        assert not service.tasks and result["result"]["id"] == bundle.id
    asyncio.run(run())


@pytest.mark.parametrize("field,value", [("language", "zh-TW"), ("level", "intermediate")])
def test_offline_scope_mismatch_does_not_relabel_a_saved_explanation(tmp_path, field, value):
    from tests.desktop.test_research_admission import fresh_bundle
    async def run():
        db = Database("sqlite://", testing=True)
        bundle, request = fresh_bundle()
        db.put("asset:" + bundle.asset.id, "asset", bundle.model_dump(mode="json"))
        runtime = FakeRuntime(payload())
        service = ResearchService(db, {"codex": runtime}, tmp_path)
        with pytest.raises(ValueError, match="language and reader level"):
            await service.submit(request.model_copy(update={field: value}))
        assert runtime.calls == 0 and db.get("asset:" + bundle.asset.id)["id"] == bundle.id
    asyncio.run(run())
