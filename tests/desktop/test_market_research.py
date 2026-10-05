import asyncio
from dataclasses import replace
import json
import threading

import httpx
import pytest

from backend.app.contracts import EvidenceBundle, ResearchRequest, RuntimeEvent
from backend.app.data_credentials import DataCredential
from backend.app.db import Database
from backend.app.evidence import factual_context
from backend.app.market_history import MarketDataError
from backend.app.market_research import MarketResearch
from backend.app.market_transport import fetch_free_eodhd_prices
from backend.app.research import ResearchService
from backend.app.source_registry import source_rule
from backend.app.source_review import SourceReviewDecision, SourceReviewScope
from tests.desktop.financial_fixture import AT, financial_result
from tests.desktop.test_market_mapping import history
from tests.desktop.test_source_review import pending
from tests.desktop.market_fixture import market_candidate, valuation_candidate


def service(tmp_path, *, enabled=True, review=False, credential=None, yahoo=None, primary=None, database=None, valuations=None):
    result, calls, prompts = financial_result(), [], []
    class Resolver:
        def resolve(self, query):
            return [result.instrument]
    class Financial:
        def retrieve(self, *args, **kwargs):
            return result
    class Filings:
        def retrieve(self, *args, **kwargs):
            return []
    class Store:
        def load(self, name):
            calls.append("vault")
            return credential
    class Runtime:
        async def stream(self, prompt, run_id, workspace, model=None):
            prompts.append(prompt)
            yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({
                "candidates": [result.instrument.asset.model_dump(mode="json")], "sources": [], "claims": []}))
    async def fallback(symbol, start, end):
        calls.append("yahoo")
        return replace(market_candidate(), requested_start=start, requested_end=end), 4
    async def supplied_valuations(symbol, start, end):
        return replace(valuation_candidate(), requested_start=start, requested_end=end), 3
    def first(symbol, start, end, credential, cancelled=None):
        calls.append("primary")
        return json.dumps([{"date": start, "open": 1, "high": 1, "low": 1, "close": 1, "adjusted_close": 1, "volume": 100}]).encode()
    db = database if database is not None else Database("sqlite://", testing=True)
    db.put("settings", "settings", {"cloud_enabled": True, "experimental_yahoo_enabled": enabled, "manual_source_review": review})
    value = ResearchService(db, {"codex": Runtime()}, tmp_path, identity_resolver=Resolver(),
        financial_adapter=Financial(), filing_adapter=Filings(), clock=lambda: AT)
    value.market_adapter = MarketResearch(value, store_factory=Store, primary=primary or first, yahoo=yahoo or fallback,
        valuations=valuations or supplied_valuations)
    return value, result.instrument, calls, prompts


@pytest.mark.parametrize("enabled", [False, True])
def test_real_research_pipeline_supplies_admitted_market_context_after_opt_in(tmp_path, enabled):
    async def run():
        app, instrument, calls, prompts = service(tmp_path, enabled=enabled)
        job = await app.submit(ResearchRequest(query=instrument.asset.id))
        await app.tasks[job["id"]]
        completed = app.db.job(job["id"])
        assert completed["status"] == "completed", completed["error"]
        value = EvidenceBundle.model_validate(completed["result"])
        assert bool(value.market) == enabled and value.financials
        assert calls == (["vault", "yahoo"] if enabled else [])
        assert len(prompts) == 1 and ("https://finance.yahoo.com/quote/SYN/" in prompts[0]) == enabled
        if enabled:
            assert "CURRENT RETRIEVAL OF HISTORICAL MARKET EVIDENCE" in prompts[0] and value.market.source_id in prompts[0]
            assert value.market.valuations.source_id in prompts[0]
            assert factual_context(value)["market"]["bars"] == value.market.model_dump(mode="json")["bars"]
            sections = [r for r in app.db.list("bundle") if r["completion"] == "section_checkpoint"]
            assert len(sections) == 2 and len([r for r in sections if r["market"]]) == 1
            assert all(r["id"] != value.id for r in sections)
            assert app.db.get("asset:" + instrument.asset.id)["id"] == value.id
        await app.close()
    asyncio.run(run())


def test_primary_api_precedes_fallback_but_denial_never_triggers_equivalent_extraction(tmp_path):
    async def run():
        app, instrument, calls, _ = service(tmp_path, credential=DataCredential("synthetic"))
        scope = SourceReviewScope(app, "market")
        mapped, gap = await app.market_adapter.retrieve(instrument, threading.Event(), scope)
        assert mapped and not gap and calls == ["vault", "primary", "yahoo"]
        def denied(*args, **kwargs):
            raise MarketDataError("source_rate_limited")
        app.market_adapter.primary = denied
        calls.clear()
        mapped, gap = await app.market_adapter.retrieve(instrument, threading.Event(), scope)
        assert mapped is None and gap and calls == ["vault"]
        await app.close()
    asyncio.run(run())


@pytest.mark.parametrize("outcome", ["yahoo_only", "skip", "cancel", "revoke"])
def test_private_source_review_has_exact_numeric_scope_and_no_general_text_grant(tmp_path, outcome):
    async def run():
        app, instrument, calls, _ = service(tmp_path, review=True)
        scope = SourceReviewScope(app, "market")
        task = asyncio.create_task(app.market_adapter.retrieve(instrument, threading.Event(), scope))
        review = await pending(app.source_reviews, task)
        assert not calls and app.retrieval._value == 2 and app.inference._value == 1
        assert len(review.sources) == 3 and all(row.local_numeric_only for row in review.sources)
        assert all(source_rule(str(row.url)) is None for row in review.sources)
        selected = [row.id for row in review.sources if "yahoo" in str(row.url)] if outcome in ("yahoo_only", "revoke") else []
        if outcome == "revoke":
            app.db.put("settings", "settings", {"cloud_enabled": True, "experimental_yahoo_enabled": False})
        app.source_reviews.resolve("market", review.id, SourceReviewDecision(source_ids=selected, cancel=outcome == "cancel"))
        if outcome in ("cancel", "revoke"):
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            mapped, gap = await task
            assert bool(mapped) == (outcome == "yahoo_only")
            assert bool(gap) == (outcome != "yahoo_only")
        assert calls == (["yahoo"] if outcome == "yahoo_only" else [])
        assert not app.source_reviews.snapshot()
        await app.close()
    asyncio.run(run())


def test_cancellation_closes_yahoo_before_releasing_slot_and_keeps_prior_financial_section(tmp_path):
    async def run():
        started, stopped = asyncio.Event(), asyncio.Event()
        async def slow(*args):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()
        app, instrument, _, prompts = service(tmp_path, yahoo=slow)
        job = await app.submit(ResearchRequest(query=instrument.asset.id))
        await started.wait()
        assert app.retrieval._value == 1 and not prompts
        await app.cancel(job["id"])
        assert stopped.is_set() and app.retrieval._value == 2 and not prompts
        assert app.db.job(job["id"])["status"] == "cancelled"
        assert not app.db.list("asset")
        assert len(app.db.list("bundle")) == 1 and app.db.list("bundle")[0]["financials"]
        await app.close()
    asyncio.run(run())


def test_two_shared_retrieval_slots_bound_owned_yahoo_workers(tmp_path):
    async def run():
        active, peak, starts = 0, 0, 0
        two, release = asyncio.Event(), asyncio.Event()
        async def slow(symbol, start, end):
            nonlocal active, peak, starts
            active += 1
            starts += 1
            peak = max(peak, active)
            if active == 2:
                two.set()
            try:
                await release.wait()
                return replace(history(), requested_start=start, requested_end=end), 4
            finally:
                active -= 1
        app, instrument, _, _ = service(tmp_path, yahoo=slow)
        tasks = [asyncio.create_task(app.market_adapter.retrieve(instrument, threading.Event(), SourceReviewScope(app, str(i)))) for i in range(3)]
        await two.wait()
        assert starts == 2 and app.retrieval._value == 0
        release.set()
        results = await asyncio.gather(*tasks)
        assert peak == 2 and starts == 3 and all(row[0] for row in results)
        assert app.retrieval._value == 2
        await app.close()
    asyncio.run(run())


@pytest.mark.parametrize("account,expected", [
    ({"dailyRateLimit": 20, "apiRequests": 0, "extraLimit": 0}, True),
    ({"dailyRateLimit": 20, "apiRequests": 18, "extraLimit": 0}, True),
    ({"dailyRateLimit": 20, "apiRequests": 19, "extraLimit": 0}, False),
    ({"dailyRateLimit": 100000, "apiRequests": 0, "extraLimit": 0}, False),
    ({"dailyRateLimit": 20, "apiRequests": 0, "extraLimit": 100}, False),
    ({"dailyRateLimit": 20, "apiRequests": "0", "extraLimit": 0}, False),
    ({"dailyRateLimit": 20, "apiRequests": False, "extraLimit": 0}, False),
    ({}, False),
])
def test_production_account_check_refuses_unknown_paid_overage_or_exhausted_scope(account, expected):
    paths = []
    def handler(request):
        assert request.headers["authorization"] == "Bearer synthetic-key"
        assert "synthetic-key" not in str(request.url)
        paths.append(request.url.path)
        return httpx.Response(200, json={**account, "email": "must-not-be-retained@example.test"} if request.url.path.endswith("/user") else [])
    call = lambda: fetch_free_eodhd_prices("SYN.US", "2026-01-01", "2026-01-31", DataCredential("synthetic-key"), _transport=httpx.MockTransport(handler))
    if expected:
        assert call() == b"[]" and len(paths) == 2
    else:
        with pytest.raises(MarketDataError, match="account_scope_unqualified"):
            call()
        assert paths == ["/api/user"]


def test_cancelled_account_check_stops_before_price_request():
    stopped = threading.Event()
    def handler(request):
        assert request.url.path == "/api/user"
        stopped.set()
        return httpx.Response(200, json={"dailyRateLimit": 20, "apiRequests": 0, "extraLimit": 0})
    with pytest.raises(InterruptedError):
        fetch_free_eodhd_prices("SYN.US", "2026-01-01", "2026-01-31", DataCredential("synthetic"),
            _transport=httpx.MockTransport(handler), cancelled=stopped)


def test_primary_rechecks_manual_review_after_waiting_for_retrieval_slot(tmp_path):
    async def run():
        app, instrument, calls, _ = service(tmp_path, credential=DataCredential("synthetic"))
        retrieve, count = app.retrieve, 0
        async def delayed(function, *args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:  # Vault has completed; primary source was approved automatically before queuing.
                app.db.put("settings", "settings", {"cloud_enabled": True, "experimental_yahoo_enabled": True, "manual_source_review": True})
            return await retrieve(function, *args, **kwargs)
        app.retrieve = delayed
        mapped, gap = await app.market_adapter.retrieve(instrument, threading.Event(), SourceReviewScope(app, "queued"))
        assert mapped is None and gap and calls == ["vault"]
        await app.close()
    asyncio.run(run())


def test_production_live_helper_defaults_to_no_access_and_summarizes_without_values(tmp_path):
    from scripts.qualify_market_research import check
    assert asyncio.run(check())["status"] == "not_run"
    assert asyncio.run(check(live=True, asset_id="NVDA"))["status"] == "blocked"
    def factory(db, workspace):
        value, _, _, _ = service(workspace, database=db)
        return value
    instrument = financial_result().instrument
    result = asyncio.run(check(live=True, asset_id=instrument.asset.id, service_factory=factory))
    assert result["status"] == "qualified" and result["checkpoint_preserved"]
    assert result["cloud_context_included"] and result["shareable_export_excluded"]
    assert "9007199254740993" not in json.dumps(result) and "27.272727" not in json.dumps(result)
