import asyncio
from dataclasses import replace
import json
from pathlib import Path
import threading

from fastapi.testclient import TestClient
import pytest

from backend.app.api import create_app
from backend.app.contracts import EvidenceBundle, ResearchRequest
from backend.app.db import Database
from backend.app.evidence import factual_context
from backend.app.market_evidence import market_fingerprint
from backend.app.market_history import MarketDataError
from backend.app.source_review import SourceReviewScope, SourceReviewDecision
from tests.desktop.market_fixture import market_bundle, valuation_candidate
from tests.desktop.test_market_evidence import seed, TOKEN
from tests.desktop.test_market_research import service
from tests.desktop.test_source_review import pending


def test_original_valuation_references_survive_contract_and_frontend_fixture():
    value = market_bundle(valuations=True)
    assert EvidenceBundle.model_validate_json(value.model_dump_json()) == value
    data = value.market.valuations
    assert data.source_id != value.market.source_id and len(data.points) == 6
    assert data.points[0].value == "9007199254740993"
    source = next(s for s in value.sources if s.id == data.source_id)
    assert source.as_of.isoformat() == "2026-01-05" and source.content_hash == valuation_candidate().content_hash
    fixture = EvidenceBundle.model_validate_json(Path("apps/desktop/src/fixtures/privateValuations.json").read_text())
    assert fixture.market.valuations == data


@pytest.mark.parametrize("field,value", [("metric", "ForwardPeRatio"), ("date", "2027-01-01"),
    ("period_type", "TTM"), ("currency", None), ("value", "NaN"), ("value", "01"),
    ("value", "1e9"), ("value", None), ("reason", "currency_missing")])
def test_reject_tampered_point_even_with_recomputed_checksum(field, value):
    payload = market_bundle(valuations=True).model_dump(mode="json")
    payload["market"]["valuations"]["points"][0][field] = value
    payload["market"]["fingerprint"] = market_fingerprint(payload["market"])
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(payload)


@pytest.mark.parametrize("field,value", [("url", "https://finance.yahoo.com/quote/OTHER/key-statistics/"),
    ("asset_id", "OTHER"), ("verified", False), ("usage_scope", "standard"), ("as_of", "2026-01-04"),
    ("policy", "full_text_allowed"), ("retrieved_at", "2026-10-05T00:00:00Z"), ("content_hash", "a" * 64)])
def test_reject_detached_or_relabelled_valuation_source(field, value):
    payload = market_bundle(valuations=True).model_dump(mode="json")
    payload["sources"][-1][field] = value
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(payload)


def test_old_versions_do_not_gain_provider_values_and_duplicates_are_rejected():
    old = market_bundle().model_dump(mode="json")
    del old["market"]["valuations"], old["market"]["valuation_gap"]
    assert EvidenceBundle.model_validate(old).market.valuations is None
    payload = market_bundle(valuations=True).model_dump(mode="json")
    payload["market"]["valuations"]["points"].append(payload["market"]["valuations"]["points"][0])
    payload["market"]["fingerprint"] = market_fingerprint(payload["market"])
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(payload)


def test_live_page_preserves_values_but_context_and_both_exports_omit_them(tmp_path):
    value = market_bundle(valuations=True, financials=False)
    assert "28.123456789012345678" not in json.dumps(factual_context(value))
    db = Database("sqlite://", testing=True)
    seed(db, value)
    with TestClient(create_app(db, TOKEN, tmp_path, adapters={"codex": object()})) as client:
        headers = {"Authorization": "Bearer " + TOKEN}
        assert client.get(f"/api/bundles/{value.id}", headers=headers).json()["market"]["valuations"] == value.market.valuations.model_dump(mode="json")
        for format in ("json", "markdown"):
            response = client.get(f"/api/export/{value.id}?format={format}", headers=headers)
            assert response.status_code == 200
            for forbidden in ("28.123456789012345678", "key-statistics", value.market.valuations.source_id):
                assert forbidden not in response.text
            assert "private backups" in response.text


def test_valuation_failure_retains_prices_without_retry_or_model_leak(tmp_path):
    calls = []
    async def failed(*args):
        calls.append(1)
        raise MarketDataError("source_access_denied")
    async def run():
        app, instrument, _, prompts = service(tmp_path, valuations=failed)
        job = await app.submit(ResearchRequest(query=instrument.asset.id))
        await app.tasks[job["id"]]
        value = EvidenceBundle.model_validate(app.db.job(job["id"])["result"])
        assert value.market.valuation_gap == "source_unavailable" and value.market.valuations is None
        assert value.market.bars and calls == [1] and "28.123456789" not in prompts[0]
        await app.close()
    asyncio.run(run())


def test_review_can_select_prices_without_contacting_valuation_endpoint(tmp_path):
    async def forbidden(*args):
        pytest.fail("unselected valuation request")
    async def run():
        app, instrument, _, _ = service(tmp_path, valuations=forbidden, review=True)
        task = asyncio.create_task(app.market_adapter.retrieve(instrument, threading.Event(), SourceReviewScope(app, "valuation")))
        review = await pending(app.source_reviews, task)
        selected = [s.id for s in review.sources if str(s.url).endswith("/history/")]
        app.source_reviews.resolve("valuation", review.id, SourceReviewDecision(source_ids=selected))
        result, _ = await task
        assert result.history and result.valuations is None and result.valuation_gap == "not_selected"
        await app.close()
    asyncio.run(run())


def test_valuation_cancellation_releases_owned_slot_and_publishes_no_values(tmp_path):
    async def run():
        started, closed = asyncio.Event(), asyncio.Event()
        async def slow(*args):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                closed.set()
        app, instrument, _, prompts = service(tmp_path, valuations=slow)
        job = await app.submit(ResearchRequest(query=instrument.asset.id))
        await started.wait()
        assert app.retrieval._value == 1
        await app.cancel(job["id"])
        assert closed.is_set() and app.retrieval._value == 2 and not prompts
        assert all(not b.get("market") for b in app.db.list("bundle"))
        await app.close()
    asyncio.run(run())


def test_newly_enabled_review_withholds_valuation_after_fetch(tmp_path):
    async def run():
        app, instrument, _, _ = service(tmp_path)
        async def change_review(symbol, start, end):
            app.db.put("settings", "settings", {"cloud_enabled": True, "experimental_yahoo_enabled": True, "manual_source_review": True})
            return replace(valuation_candidate(), requested_start=start, requested_end=end), 3
        app.market_adapter.valuations = change_review
        result, _ = await app.market_adapter.retrieve(instrument, threading.Event(), SourceReviewScope(app, "valuation"))
        assert result.valuations is None and result.valuation_gap == "not_selected"
        await app.close()
    asyncio.run(run())
