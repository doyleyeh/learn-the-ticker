"""The common provider path admits typed numbers, never model-created financial facts."""
import asyncio
import json

import pytest

from backend.app.backup import make_backup, preview_backup, read_backup, restore_backup
from backend.app.contracts import EvidenceBundle, ResearchRequest, RuntimeEvent, TermRequest
from backend.app.db import Database
from backend.app.evidence import factual_context
from backend.app.evidence_reuse import citation_id, conversation_evidence, validate_context_references
from backend.app.source_operations import shareable_view
from backend.app.terms import TermService
from tests.desktop.market_fixture import market_bundle
from tests.desktop.test_backup import alter
from tests.desktop.test_market_evidence import seed
from tests.desktop.test_market_research import service
from tests.desktop.test_terms import TermRuntime, completed


async def publish_numeric_followup(db, path, provider="codex"):
    original = market_bundle(valuations=True)
    seed(db, original)
    app, instrument, _, _ = service(path, enabled=False, database=db)
    settings = app.settings().model_copy(update={"provider": provider})
    db.put("settings", "settings", settings.model_dump(mode="json"))
    calls = []
    class Runtime:
        async def stream(self, prompt, run_id, workspace, model=None):
            context = json.loads(prompt.split("ADMITTED SAVED EVIDENCE (original dates, not refreshed): ")[1].splitlines()[0])
            sid = context["market"]["valuations"]["source_id"]
            assert sid == citation_id(original.id, original.market.valuations.source_id)
            assert context["market"]["valuations"]["points"] == original.market.valuations.model_dump(mode="json")["points"]
            calls.append(prompt)
            yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({
                "candidates": [instrument.asset.model_dump(mode="json")],
                "sources": [{"id": sid, "asset_id": instrument.asset.id, "url": "https://wrong.example/", "title": "Spoof", "publisher": "Spoof"}],
                "claims": [{"id": "interpretation", "asset_id": instrument.asset.id, "kind": "fact", "value": 29.5,
                    "text": "Yahoo's retained P/E observation is 29.5; this is historical provider data.", "source_ids": [sid]},
                    {"id": "uncited", "asset_id": instrument.asset.id, "text": "Unattributed interpretation of earlier numerics."}]}))
    app.adapters = {provider: Runtime()}
    try:
        job = await app.submit(ResearchRequest(query="Explain the saved valuation", asset_id=instrument.asset.id, provider=provider))
        await app.tasks[job["id"]]
        result = db.job(job["id"])
        assert result["status"] == "completed", result["error"]
        assert len(calls) == 1
        return original, EvidenceBundle.model_validate(result["result"])
    finally:
        await app.close()


@pytest.mark.parametrize("provider", ["codex", "gemini", "claude"])
def test_shared_research_path_retains_original_refs_and_keeps_interpretations_out_of_facts(tmp_path, provider):
    db = Database("sqlite://", testing=True)
    original, result = asyncio.run(publish_numeric_followup(db, tmp_path, provider))
    assert result.market is None and len(result.context_references) == 2
    note = next(note for note in result.notes if note.id == "interpretation")
    assert note.kind == "unverified_note" and note.value is None and not note.input_claim_ids
    assert not result.claims and "29.5" not in json.dumps(factual_context(result))
    assert all("wrong.example" not in str(source.url) for source in result.sources)
    assert db.get("bundle:" + original.id) == original.model_dump(mode="json")
    exported, notice = shareable_view(result)
    assert notice and not exported.notes and not exported.context_references
    target = Database("sqlite://", testing=True)
    archive = make_backup(db)
    restore_backup(target, archive, preview_backup(target, archive).fingerprint)
    assert target.get("bundle:" + result.id) == result.model_dump(mode="json")
    validate_context_references(result, lambda bid: target.get("bundle:" + bid))
    reused, _ = conversation_evidence(target, result.asset, [{"role": "assistant", "asset_id": result.asset.id, "bundle_id": result.id}])
    assert any(context.get("market", {}).get("source_id") == citation_id(original.id, original.market.source_id) for context in reused)
    assert "Unattributed interpretation" not in json.dumps(reused)
    def corrupt(data):
        for row in data["records"]:
            if row["kind"] in ("bundle", "asset") and row["payload"]["id"] == result.id:
                row["payload"]["context_references"][0]["source_id"] = "invented"
    with pytest.raises(ValueError):
        read_backup(alter(archive, change=corrupt))
    with pytest.raises(ValueError, match="missing"):
        validate_context_references(result, lambda bid: None)


@pytest.mark.parametrize("provider", ["codex", "gemini", "claude"])
@pytest.mark.parametrize("kind", ["price", "return", "valuation", "wrong_citation", "invented"])
def test_terms_use_cited_exact_numbers_through_selected_provider(tmp_path, provider, kind):
    async def run():
        bundle = market_bundle(valuations=True)
        app, _, _, _ = service(tmp_path, enabled=False)
        seed(app.db, bundle)
        app.db.put("settings", "settings", {"cloud_enabled": True, "provider": provider})
        text = {"price": "The observed close was 14 USD.", "return": "The retained price return is 27.272727%.",
                "valuation": "The historical P/E observation was 28.123456789012345678.",
                "wrong_citation": "The P/E observation was 28.123456789012345678.", "invented": "The price was 67890123 USD."}[kind]
        sid = bundle.market.valuations.source_id if kind == "valuation" else bundle.market.source_id
        runtime = TermRuntime({"explanation": text, "basis": "snapshot", "source_ids": [sid]})
        app.adapters = {provider: runtime}
        try:
            learning = TermService(app)
            request = TermRequest(term="Retained observation", bundle_id=bundle.id, provider=provider)
            result = await completed(learning, request)
            assert result["status"] == ("failed" if kind in ("wrong_citation", "invented") else "completed")
            assert len(runtime.calls) == 1 and not runtime.calls[0]["browsing"]
            assert bundle.market.valuations.source_id in runtime.calls[0]["prompt"]
            assert "0.123456789012345678" in runtime.calls[0]["prompt"]
            if result["status"] == "completed":
                assert result["result"]["source_ids"] == [sid]
                app.db.put("settings", "settings", {"cloud_enabled": False, "provider": provider})
                assert (await learning.submit(request))["status"] == "cached"
                assert len(runtime.calls) == 1
        finally:
            await app.close()
    asyncio.run(run())


def test_numeral_support_does_not_round_long_decimals_or_treat_date_separators_as_signs():
    from backend.app.terms import number_tokens
    assert number_tokens("1.1234567890123456789012345678901") != number_tokens("1.1234567890123456789012345678902")
    assert number_tokens("1,234.50") == number_tokens("1234.5")
    assert number_tokens("2026-01-05") == number_tokens("January 5, 2026 1")
    assert number_tokens("-12%") != number_tokens("12%")


def test_new_source_review_during_generation_does_not_publish_unreviewed_interpretation(tmp_path):
    async def run():
        app, instrument, _, _ = service(tmp_path)
        class Runtime:
            async def stream(self, prompt, run_id, workspace, model=None):
                assert "CURRENT RETRIEVAL OF HISTORICAL MARKET EVIDENCE" in prompt
                app.db.put("settings", "settings", {"cloud_enabled": True, "experimental_yahoo_enabled": True, "manual_source_review": True})
                yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({
                    "candidates": [instrument.asset.model_dump(mode="json")], "sources": [], "claims": []}))
        app.adapters = {"codex": Runtime()}
        try:
            job = await app.submit(ResearchRequest(query=instrument.asset.id))
            await app.tasks[job["id"]]
            result = app.db.job(job["id"])
            assert result["status"] == "failed" and "Numerical source review changed" in result["error"]
            assert not app.db.get("asset:" + instrument.asset.id)
            assert all(row["completion"] == "section_checkpoint" for row in app.db.list("bundle"))
        finally:
            await app.close()
    asyncio.run(run())


def test_conversation_aliases_every_numerical_source_and_keeps_original_dates():
    db = Database("sqlite://", testing=True)
    original = market_bundle(valuations=True)
    seed(db, original)
    contexts, _ = conversation_evidence(db, original.asset, [{"role": "assistant", "asset_id": original.asset.id, "bundle_id": original.id}])
    context = contexts[0]
    assert context["market"]["returns"][-1]["source_id"] == citation_id(original.id, original.market.source_id)
    assert context["market"]["valuations"]["source_id"] == citation_id(original.id, original.market.valuations.source_id)
    for source in context["sources"]:
        saved = next(row for row in original.sources if row.id == source["original_source_id"])
        assert source["retrieved_at"] == saved.model_dump(mode="json")["retrieved_at"]


@pytest.mark.parametrize("selected", [True, False])
def test_saved_numerical_review_uses_current_consent_without_reenabling_retrieval(tmp_path, selected):
    from backend.app.source_review import SourceReviewDecision, SourceReviewScope
    from tests.desktop.source_review_fixture import next_review
    async def run():
        app, instrument, calls, _ = service(tmp_path, enabled=False, review=True)
        scope = SourceReviewScope(app, "saved-numerical-review")
        url = "https://finance.yahoo.com/quote/SYN/history/"
        try:
            task = asyncio.create_task(scope.select(instrument.asset.id, [url], numeric_context=True))
            review = await next_review(app, task)
            assert len(review.sources) == 1 and review.sources[0].local_numeric_only
            app.source_reviews.resolve(scope.run_id, review.id, SourceReviewDecision(source_ids=[review.sources[0].id] if selected else []))
            assert (await task) == ({url} if selected else set())
            assert scope.allowed(url) == selected and not calls
            assert not app.settings().experimental_yahoo_enabled
        finally:
            await app.close()
    asyncio.run(run())
