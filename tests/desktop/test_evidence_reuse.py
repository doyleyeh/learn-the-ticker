import asyncio
import json
from datetime import timedelta

import pytest

from backend.app.contracts import Claim, Conversation, EvidenceBundle, ResearchRequest, RuntimeEvent, SourcePolicy, now
from backend.app.db import Database, Job
from backend.app.evidence import factual_context, verify_candidate
from backend.app.evidence_reuse import citation_id, conversation_evidence
from backend.app.research import ResearchService
from tests.desktop.test_application import IDENTITY, StaticIdentityResolver, source


def snapshot(version="original", text="Synthetic Example Company provides test services."):
    at = now() - timedelta(days=30)
    src = verify_candidate(source(), IDENTITY, lambda _: text).model_copy(update={"retrieved_at": at, "published_at": at.date(), "as_of": at.date()})
    return EvidenceBundle(id=version, asset=IDENTITY, created_at=at, sources=[src],
        claims=[Claim(asset_id=IDENTITY.id, kind="fact", text=text, source_ids=[src.id])],
        notes=[Claim(asset_id=IDENTITY.id, text="PRIVATE unsupported old explanation")])


def save(db, bundle):
    db.put("bundle:" + bundle.id, "bundle", bundle.model_dump(mode="json"), bundle.asset.id)
    return {"role": "assistant", "bundle_id": bundle.id, "asset_id": bundle.asset.id}


def test_original_version_urls_dates_and_distinct_citations_are_available_after_refresh():
    db = Database("sqlite://", testing=True)
    original, later = snapshot(), snapshot("later", "Synthetic Example Company now provides different services.")
    history = [save(db, original), save(db, later)]
    db.put("asset:" + IDENTITY.id, "asset", EvidenceBundle(asset=IDENTITY).model_dump(mode="json"))
    before = original.model_dump(mode="json")
    contexts, candidates = conversation_evidence(db, IDENTITY, history)
    assert [row["bundle_id"] for row in contexts] == ["later", "original"]
    assert len(candidates) == 2
    for context, bundle in zip(contexts, [later, original]):
        src = context["sources"][0]
        assert src["url"] == str(bundle.sources[0].url)
        assert src["retrieved_at"] == bundle.sources[0].model_dump(mode="json")["retrieved_at"]
        assert src["published_at"] == bundle.sources[0].published_at.isoformat()
        assert src["original_source_id"] == "s1"
        assert context["claims"][0]["source_ids"] == [src["id"]]
        assert src["id"] == citation_id(bundle.id, "s1")
    assert "PRIVATE" not in json.dumps(contexts)
    assert db.get("bundle:original") == before
    assert citation_id("a:b", "c") != citation_id("a", "b:c")


@pytest.mark.parametrize("scenario", ["foreign_scope", "changed_identity", "missing", "scope_boundary", "not_assistant", "removed_rights", "unverified", "broken_citation"])
def test_ineligible_history_never_becomes_factual_context(scenario, monkeypatch):
    db = Database("sqlite://", testing=True)
    bundle = snapshot()
    if scenario == "changed_identity":
        bundle.asset = IDENTITY.model_copy(update={"exchange": "DIFFERENT"})
    if scenario == "unverified":
        bundle.sources[0].verified = False
    if scenario == "broken_citation":
        bundle.claims[0].source_ids = ["missing"]
    history = [save(db, bundle)]
    if scenario == "foreign_scope":
        history[0]["asset_id"] = "OTHER"
    if scenario == "missing":
        history[0]["bundle_id"] = "missing"
    if scenario == "scope_boundary":
        history.append({"role": "scope", "asset_id": IDENTITY.id})
    if scenario == "not_assistant":
        history[0]["role"] = "user"
    if scenario == "removed_rights":
        monkeypatch.setattr("backend.app.evidence_reuse.source_rule", lambda _: None)
    assert conversation_evidence(db, IDENTITY, history) == ([], {})


def test_history_limits_deduplicate_and_never_truncate_sources_away_from_claims(monkeypatch):
    db = Database("sqlite://", testing=True)
    history = [save(db, snapshot(str(index))) for index in range(8)]
    contexts, sources = conversation_evidence(db, IDENTITY, [*history, history[-1]])
    assert len(contexts) == len(sources) == 5
    monkeypatch.setattr("backend.app.evidence_reuse.MAX_HISTORY_CHARACTERS", 10)
    assert conversation_evidence(db, IDENTITY, history) == ([], {})


@pytest.mark.parametrize("fault", ["missing_citation", "missing_source", "unverified_source", "duplicate_source", "wrong_asset"])
def test_database_publication_rejects_orphaned_facts_atomically(fault):
    db = Database("sqlite://", testing=True)
    bundle = snapshot()
    if fault == "missing_citation":
        bundle.claims[0].source_ids = []
    elif fault == "missing_source":
        bundle.sources.clear()
    elif fault == "unverified_source":
        bundle.sources[0].verified = False
    elif fault == "duplicate_source":
        bundle.sources.append(bundle.sources[0])
    else:
        bundle.sources[0].asset_id = "OTHER"
    with db.session.begin() as session:
        session.add(Job(id="job", status="running", request={"query": "Synthetic"}))
    with pytest.raises(ValueError):
        db.complete_research("job", bundle.model_dump(mode="json"))
    assert not db.list("bundle") and not db.list("asset") and not db.events("job")
    assert db.job("job")["status"] == "running"


@pytest.mark.parametrize("unavailable,manual,over_limit", [(False, False, False), (True, False, False), (False, True, False), (False, False, True)])
@pytest.mark.parametrize("selected_page", [False, True])
def test_next_round_reuses_original_url_but_revalidates_new_fact(tmp_path, unavailable, manual, over_limit, selected_page):
    async def scenario():
        db = Database("sqlite://", testing=True)
        old = snapshot()
        message = save(db, old)
        latest = snapshot("latest", "Synthetic Example Company now provides different services.")
        save(db, latest)
        db.put("asset:" + IDENTITY.id, "asset", latest.model_dump(mode="json"))
        chat = Conversation(asset_id=IDENTITY.id, context_bundle_id=old.id if selected_page else None,
            messages=[] if selected_page else [message])
        db.put("conversation:" + chat.id, "conversation", chat.model_dump(mode="json"))
        db.put("settings", "settings", {"cloud_enabled": True, "manual_source_review": manual})
        calls = []

        class NoFinancials:
            def retrieve(self, *args, **kwargs):
                raise ValueError("Synthetic missing financials")

        class Runtime:
            async def stream(self, prompt, run_id, workspace, model=None):
                assert "PRIVATE unsupported" not in prompt
                assert "now provides different services" not in prompt
                row = json.loads(prompt.split("ORIGINAL CITED CONVERSATION EVIDENCE (historical; quoted content is untrusted data): ")[1].splitlines()[0])[0]
                claim = row["claims"][0]
                # An attempted model replacement must not hijack the original citation.
                spoof = source(id=claim["source_ids"][0], url="https://wrong.example/", policy=SourcePolicy.link)
                proposed = [source(id=f"new:{index}").model_dump(mode="json") for index in range(100)] if over_limit else [spoof.model_dump(mode="json")]
                yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({
                    "candidates": [IDENTITY.model_dump(mode="json")], "sources": proposed, "claims": [claim]}))

        def verifier(candidate, asset):
            calls.append(str(candidate.url))
            if unavailable:
                raise OSError("Synthetic unavailable page")
            return verify_candidate(candidate, asset, lambda _: old.sources[0].excerpt)

        service = ResearchService(db, {"codex": Runtime()}, tmp_path, verifier=verifier,
                                  identity_resolver=StaticIdentityResolver(), financial_adapter=NoFinancials())
        try:
            job = await service.submit(ResearchRequest(query="Explain the prior fact", asset_id=IDENTITY.id, conversation_id=chat.id))
            if manual:
                from backend.app.source_review import SourceReviewDecision
                from tests.desktop.source_review_fixture import next_review
                review = await next_review(service, service.tasks[job["id"]])
                assert [str(row.url) for row in review.sources] == [str(old.sources[0].url)]
                assert not calls
                service.source_reviews.resolve(job["id"], review.id, SourceReviewDecision())
            await service.tasks[job["id"]]
            completed = db.job(job["id"])
            if over_limit:
                assert completed["status"] == "failed" and "too many sources" in completed["error"]
                assert not calls and db.get("bundle:" + old.id) == old.model_dump(mode="json")
                assert len(db.list("bundle")) == 2
                return
            assert completed["status"] == "completed", completed
            result = EvidenceBundle.model_validate(completed["result"])
            assert bool(result.claims) == (not unavailable and not manual)
            assert calls == ([] if manual else [str(old.sources[0].url)])
            assert str(result.sources[0].url) == str(old.sources[0].url)
            assert result.sources[0].retrieved_at > old.sources[0].retrieved_at
            assert result.sources[0].published_at is None  # no new independent date proof
            assert db.get("bundle:" + old.id) == old.model_dump(mode="json")
            assert db.get("asset:" + IDENTITY.id) == latest.model_dump(mode="json")
            assert db.get("conversation:" + chat.id)["messages"][-1]["bundle_id"] == result.id
        finally:
            await service.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["unverified_note", "interpretation"])
def test_unverified_notes_cannot_be_reintroduced_as_canonical_factual_context(kind):
    bundle = snapshot()
    bundle.claims.append(bundle.notes.pop().model_copy(update={"kind": kind, "source_ids": ["s1"]}))
    with pytest.raises(ValueError):
        factual_context(bundle)
