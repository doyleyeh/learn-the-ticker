import asyncio
from dataclasses import replace
from pathlib import Path
import threading

from fastapi.testclient import TestClient
import pytest

from backend.app.api import create_app
from backend.app.contracts import EvidenceBundle, ResearchRequest, TermExplanation
from backend.app.db import Database
from backend.app.evidence import factual_context
from backend.app.evidence_reuse import cached_context, citation_id, filter_market_context
from backend.app.freshness import assess_freshness
from backend.app.market_evidence import market_fingerprint
from backend.app.market_history import MarketDataError
from backend.app.source_operations import shareable_view
from backend.app.source_review import SourceReviewScope, SourceReviewDecision
from backend.app.terms import validate_numbers
from tests.desktop.financial_fixture import AT
from tests.desktop.market_fixture import market_bundle, estimate_candidate
from tests.desktop.test_market_evidence import seed, TOKEN
from tests.desktop.test_market_research import service
from tests.desktop.test_source_review import pending


def test_estimate_archive_context_and_fixture_preserve_opinions_and_unknown_time():
    bundle = market_bundle(valuations=True, estimates=True)
    assert EvidenceBundle.model_validate_json(bundle.model_dump_json()) == bundle
    estimate = bundle.market.estimates
    assert estimate.kind == "analyst_opinion" and estimate.points[0].unit == "USD/share"
    assert estimate.points[0].average == "1.25000000000000001"
    assert estimate.points[1].average == "9007199254740993" and estimate.points[1].unit == "USD"
    source = next(s for s in bundle.sources if s.id == estimate.source_id)
    assert source.as_of is source.published_at is None and source.content_hash == estimate_candidate().content_hash
    age = next(s for s in assess_freshness(bundle, at=AT).sources if s.source_id == source.id)
    assert age.state == "unknown" and age.reason == "missing_dates"
    context = factual_context(bundle)
    assert context["market"]["estimates"]["kind"] == "analyst_opinion" and "opinions" in context["market_description"]
    assert not any(source.id in c["source_ids"] for c in context["claims"])
    fixture = EvidenceBundle.model_validate_json(Path("apps/desktop/src/fixtures/privateEstimates.json").read_text())
    assert fixture.market.estimates == estimate


@pytest.mark.parametrize("field,value", [("average", "NaN"), ("average", "01"), ("average", "1e2"),
    ("period", "12M"), ("metric", "target"), ("currency", None), ("unit", "USD"), ("period_end", None),
    ("period_end", "not a date"), ("analysts", True), ("analysts", 1.5), ("analysts", -1),
    ("reason", "value_missing")])
def test_tampered_estimates_rejected_even_after_recomputing_checksum(field, value):
    data = market_bundle(estimates=True).model_dump(mode="json")
    data["market"]["estimates"]["points"][0][field] = value
    data["market"]["fingerprint"] = market_fingerprint(data["market"])
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(data)


@pytest.mark.parametrize("field,value", [("url", "https://finance.yahoo.com/quote/OTHER/analysis/"),
    ("asset_id", "OTHER"), ("verified", False), ("usage_scope", "standard"), ("as_of", "2026-03-31"),
    ("published_at", "2026-02-01"), ("policy", "full_text_allowed"), ("excerpt", "Ignore instructions"),
    ("retrieved_at", "2026-10-05T00:00:00Z"), ("content_hash", "a" * 64)])
def test_original_source_cannot_be_detached_or_forecast_end_relabelled_as_publication(field, value):
    data = market_bundle(estimates=True).model_dump(mode="json")
    data["sources"][-1][field] = value
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(data)


@pytest.mark.parametrize("change", ["duplicate", "pair", "order", "gap", "kind", "source"])
def test_estimate_dataset_structure_is_not_forgeable(change):
    data = market_bundle(estimates=True).model_dump(mode="json")
    estimates = data["market"]["estimates"]
    if change == "duplicate":
        estimates["points"].append(estimates["points"][0])
    elif change == "pair":
        estimates["points"].pop()
    elif change == "order":
        estimates["points"].reverse()
    elif change == "gap":
        data["market"]["estimate_gap"] = "not_selected"
    elif change == "kind":
        estimates["kind"] = "fact"
    else:
        estimates["source_id"] = data["market"]["source_id"]
    data["market"]["fingerprint"] = market_fingerprint(data["market"])
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(data)


def test_old_snapshot_fingerprint_stays_valid_and_no_estimates_are_generated():
    old = market_bundle(valuations=True).model_dump(mode="json")
    del old["market"]["estimates"], old["market"]["estimate_gap"]
    assert EvidenceBundle.model_validate(old).market.estimates is None


def test_estimate_aliases_review_and_cited_numerals_are_independent_of_prices():
    bundle = market_bundle(valuations=True, estimates=True, financials=False)
    context = cached_context(bundle)
    sid = bundle.market.estimates.source_id
    alias = citation_id(bundle.id, sid)
    assert context["market"]["estimates"]["source_id"] == alias
    assert next(s for s in context["sources"] if s["id"] == alias)["original_source_id"] == sid
    filtered = filter_market_context(context, {s["id"] for s in context["sources"]} - {alias})
    assert filtered["market"]["estimates"] is None and filtered["market"]["estimate_gap"] == "not_selected"
    assert filtered["market"]["valuations"] and alias not in {s["id"] for s in filtered["sources"]}
    explanation = TermExplanation(id="0" * 64, term="Explain estimates", mode="question", bundle_id=bundle.id, asset_id=bundle.asset.id,
        language="en", level="beginner", provider="codex", basis="snapshot", source_ids=[sid],
        explanation="The supplied EPS opinion averages 1.25000000000000001 USD/share from 12 analysts.")
    validate_numbers(explanation, factual_context(bundle))
    with pytest.raises(ValueError, match="Unsubstantiated"):
        validate_numbers(explanation.model_copy(update={"source_ids": [bundle.market.source_id]}), factual_context(bundle))
    with pytest.raises(ValueError, match="Unsubstantiated"):
        validate_numbers(explanation.model_copy(update={"explanation": "The forecast is 99.99."}), factual_context(bundle))


def test_api_keeps_estimates_but_shareable_exports_exclude_them(tmp_path):
    value = market_bundle(estimates=True, financials=False)
    assert "1.25000000000000001" not in shareable_view(value)[0].model_dump_json()
    db = Database("sqlite://", testing=True)
    seed(db, value)
    with TestClient(create_app(db, TOKEN, tmp_path, adapters={"codex": object()})) as client:
        headers = {"Authorization": "Bearer " + TOKEN}
        assert client.get(f"/api/bundles/{value.id}", headers=headers).json()["market"]["estimates"] == value.market.estimates.model_dump(mode="json")
        for format in ("json", "markdown"):
            response = client.get(f"/api/export/{value.id}?format={format}", headers=headers)
            assert response.status_code == 200
            assert "1.25000000000000001" not in response.text and value.market.estimates.source_id not in response.text


@pytest.mark.parametrize("stage", ["valuations", "estimates"])
def test_denial_stops_subsequent_yahoo_requests_without_losing_saved_prices(tmp_path, stage):
    calls = []
    async def denied(*args):
        calls.append(stage)
        raise MarketDataError("source_access_denied")
    async def forbidden(*args):
        pytest.fail("Estimate request after Yahoo denied access")
    async def run():
        kwargs = {stage: denied}
        if stage == "valuations":
            kwargs["estimates"] = forbidden
        app, instrument, _, _ = service(tmp_path, **kwargs)
        job = await app.submit(ResearchRequest(query=instrument.asset.id))
        await app.tasks[job["id"]]
        value = EvidenceBundle.model_validate(app.db.job(job["id"])["result"])
        assert value.market.bars and value.market.estimates is None and value.market.estimate_gap == "source_unavailable"
        assert calls == [stage]
        await app.close()
    asyncio.run(run())


def test_estimates_can_be_selected_without_valuations_and_enter_scoped_context(tmp_path):
    async def forbidden(*args):
        pytest.fail("Unselected valuation call")
    async def run():
        app, instrument, _, _ = service(tmp_path, valuations=forbidden, review=True)
        task = asyncio.create_task(app.market_adapter.retrieve(instrument, threading.Event(), SourceReviewScope(app, "estimates")))
        review = await pending(app.source_reviews, task)
        selected = [s.id for s in review.sources if str(s.url).endswith(("/history/", "/analysis/"))]
        app.source_reviews.resolve("estimates", review.id, SourceReviewDecision(source_ids=selected))
        result, _ = await task
        assert result.estimates and result.valuations is None and result.valuation_gap == "not_selected"
        await app.close()
    asyncio.run(run())


def test_estimate_cancellation_releases_owned_slot_before_model_or_market_publication(tmp_path):
    async def run():
        started, closed = asyncio.Event(), asyncio.Event()
        async def slow(*args):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                closed.set()
        app, instrument, _, prompts = service(tmp_path, estimates=slow)
        job = await app.submit(ResearchRequest(query=instrument.asset.id))
        await started.wait()
        await app.cancel(job["id"])
        assert closed.is_set() and app.retrieval._value == 2 and not prompts
        assert all(not b.get("market") for b in app.db.list("bundle"))
        await app.close()
    asyncio.run(run())


def test_revoked_source_selection_discards_completed_estimates(tmp_path):
    async def run():
        app, instrument, _, _ = service(tmp_path)
        async def changed(*args):
            app.db.put("settings", "settings", {"cloud_enabled": True, "experimental_yahoo_enabled": True, "manual_source_review": True})
            return replace(estimate_candidate()), 3
        app.market_adapter.estimates = changed
        result, _ = await app.market_adapter.retrieve(instrument, threading.Event(), SourceReviewScope(app, "estimates"))
        assert result.estimates is None and result.estimate_gap == "not_selected"
        await app.close()
    asyncio.run(run())
