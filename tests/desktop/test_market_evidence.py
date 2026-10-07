import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.backup import BackupError, make_backup, preview_backup, read_backup, restore_backup
from backend.app.contracts import Claim, EvidenceBundle, ResearchRequest, ResearchResult, Settings, Source, TermExplanation, TermRequest
from backend.app.db import Database, Job
from backend.app.evidence import candidate_metadata, factual_context
from backend.app.evidence_reuse import conversation_evidence
from backend.app.market_evidence import attach_market, market_fingerprint
from backend.app.market_mapping import map_yahoo_history
from backend.app.research import research_prompt
from backend.app.terms import term_key, term_prompt, validate_explanation
from tests.desktop.financial_fixture import AT
from tests.desktop.market_fixture import market_bundle
from tests.desktop.test_backup import alter
from tests.desktop.test_market_mapping import history
from tests.desktop.test_structured_financials import identities

TOKEN = "market-operation-test-" * 4


def seed(db, bundle):
    with db.session.begin() as session:
        session.add(Job(id="market", status="running", request={"query": "Synthetic history"}))
    db.complete_research("market", bundle.model_dump(mode="json"))


def test_typed_exact_original_citations_and_adjustments_round_trip():
    value = market_bundle()
    copied = EvidenceBundle.model_validate_json(value.model_dump_json())
    assert copied == value
    assert copied.market.bars[0].volume == "9007199254740993"
    assert copied.market.actions[0].value == "0.123456789012345678"
    assert copied.market.actions[1].value == "3/2"
    assert copied.market.close_basis == "split_adjusted"
    assert copied.market.adjusted_close_basis == "splits_and_distributions"
    assert copied.market.source_id == copied.sources[-1].id
    assert copied.sources[-1].retrieved_at == AT and not copied.sources[-1].official
    assert copied.sources[-1].usage_scope == "private_yahoo_v1"
    assert copied.financials and copied.asset.currency is None
    assert EvidenceBundle(asset=value.asset).market is None


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(identity_verification=None),
    lambda p: p.update(market=None),
    lambda p: p["asset"].update(exchange="US"),
    lambda p: p["market"].update(usage_scope="standard"),
    lambda p: p["market"].update(currency="EUR"),
    lambda p: p["market"].update(close_basis="unadjusted"),
    lambda p: p["market"].update(exchange_label="NasdaqGM"),
    lambda p: p["market"].update(source_id="wrong"),
    lambda p: p["market"].update(checked_at="2026-10-06T00:00:00Z"),
    lambda p: p["market"].update(requested_end="2026-10-04"),
    lambda p: p["market"].update(gaps=[]),
    lambda p: p["market"].update(gaps=["calendar_completeness_unverified"] * 2),
    lambda p: p["market"]["bars"].reverse(),
    lambda p: p["market"]["bars"].append(p["market"]["bars"][0]),
    lambda p: p["market"]["bars"][0].update(date="2025-01-02"),
    lambda p: p["market"]["bars"][0].update(close="999"),
    lambda p: p["market"]["bars"][0].update(close="11.0"),
    lambda p: p["market"]["bars"][0].update(close="no number"),
    lambda p: p["market"]["bars"][0].update(close="NaN"),
    lambda p: p["market"]["bars"][0].update(close=11),
    lambda p: p["market"]["bars"][0].update(volume="1.2"),
    lambda p: p["market"]["actions"][1].update(value="3/0"),
    lambda p: p["market"]["actions"][1].update(value="3"),
    lambda p: p["market"]["actions"].append(p["market"]["actions"][0]),
    lambda p: p["sources"][-1].update(usage_scope="standard"),
    lambda p: p["sources"][-1].update(official=True),
    lambda p: p["sources"][-1].update(policy="full_text_allowed"),
    lambda p: p["sources"][-1].update(title="Injected custom source content"),
    lambda p: p["sources"][-1].update(content_hash="0" * 64),
    lambda p: p["sources"][-1].update(as_of="2026-10-01"),
    lambda p: p["sources"][-1].update(retrieved_at="2026-10-05T00:00:00Z"),
])
def test_scope_number_rights_and_date_tampering_fail_before_publication(mutate):
    payload = market_bundle().model_dump(mode="json")
    mutate(payload)
    # Recompute the checksum to test semantics independently of corruption detection.
    if payload.get("market"):
        payload["market"]["fingerprint"] = market_fingerprint(payload["market"])
    db = Database("sqlite://", testing=True)
    with db.session.begin() as session:
        session.add(Job(id="market", status="running", request={"query": "Synthetic history"}))
    with pytest.raises(ValueError):
        db.complete_research("market", payload)
    assert not db.list("bundle") and not db.list("asset") and not db.events("market")


def test_mutation_without_new_fingerprint_is_detected_and_model_has_no_market_field():
    payload = market_bundle().model_dump(mode="json")
    payload["market"]["bars"][0]["volume"] = "99"
    with pytest.raises(ValueError, match="fingerprint"):
        EvidenceBundle.model_validate(payload)
    with pytest.raises(ValueError):
        ResearchResult.model_validate({"market": payload["market"]})
    candidate = candidate_metadata(market_bundle().sources[-1])
    assert candidate.usage_scope == "standard" and not candidate.verified and candidate.provenance == "agent_candidate"


@pytest.mark.parametrize("consent", [False, None, "true", 1])
def test_local_admission_requires_explicit_boolean_consent(consent):
    instrument, _ = identities()
    mapped = map_yahoo_history(history(), instrument, at=AT)
    with pytest.raises(ValueError, match="opt-in"):
        attach_market(EvidenceBundle(asset=instrument.asset, identity_verification=instrument.verification),
                      mapped, personal_mode=consent, created_at=AT)


def test_no_old_mapping_refresh_or_in_place_market_replacement():
    instrument, _ = identities()
    mapped = map_yahoo_history(history(), instrument, at=AT)
    base = EvidenceBundle(asset=instrument.asset, identity_verification=instrument.verification)
    with pytest.raises(ValueError):
        attach_market(base, mapped, personal_mode=True, created_at=AT + timedelta(days=1))
    with pytest.raises(ValueError):
        attach_market(market_bundle(), mapped, personal_mode=True, created_at=AT)


def derived_bundle():
    value = market_bundle()
    asset, private, permitted = value.asset.id, value.market.source_id, value.sources[0].id
    claims = [Claim(id="private-fact", asset_id=asset, text="PRIVATE VALUE 98765", kind="fact", source_ids=[private]),
        Claim(id="derived", asset_id=asset, text="PRIVATE DERIVED 56789", kind="calculation", source_ids=[permitted], input_claim_ids=["private-fact"]),
        Claim(id="second-hop", asset_id=asset, text="PRIVATE SECOND HOP", kind="calculation", source_ids=[permitted], input_claim_ids=["derived"]),
        Claim(id="permitted", asset_id=asset, text="PERMITTED ISSUER FACT", kind="fact", source_ids=[permitted])]
    notes = [Claim(asset_id=asset, text="PRIVATE INTERPRETATION", source_ids=[private]),
             Claim(asset_id=asset, text="UNATTRIBUTED INTERPRETATION")]
    return EvidenceBundle.model_validate({**value.model_dump(), "claims": claims, "notes": notes})


def assert_no_private(text):
    for forbidden in ("98765", "56789", "PRIVATE SECOND", "PRIVATE INTERPRETATION", "UNATTRIBUTED", "finance.yahoo.com", "0.123456789012345678"):
        assert forbidden not in text


def assert_admitted_context(text):
    for forbidden in ("PRIVATE VALUE", "PRIVATE DERIVED", "PRIVATE SECOND", "PRIVATE INTERPRETATION", "UNATTRIBUTED"):
        assert forbidden not in text
    assert "finance.yahoo.com" in text and "0.123456789012345678" in text


def test_conversation_term_and_research_context_keep_permitted_original_citations_only():
    value = derived_bundle()
    context = factual_context(value)
    assert_admitted_context(json.dumps(context))
    assert [c["id"] for c in context["claims"]] == ["permitted"]
    assert context["financials"]["observations"] and context["market"]
    assert context["sources"][0]["retrieved_at"] == value.sources[0].model_dump(mode="json")["retrieved_at"]
    assert_admitted_context(research_prompt(ResearchRequest(query="Explain this company"), value.model_dump(mode="json"), []))
    request = TermRequest(term="adjusted close", bundle_id=value.id)
    assert_admitted_context(term_prompt(request, value))
    explanation = TermExplanation(id=term_key(request), term=request.term, bundle_id=value.id, asset_id=value.asset.id,
        language="en", level="beginner", provider="codex", explanation="A private interpretation.", basis="snapshot", source_ids=[value.market.source_id])
    validate_explanation(explanation, value)
    db = Database("sqlite://", testing=True)
    seed(db, value)
    contexts, candidates = conversation_evidence(db, value.asset, [{"role": "assistant", "asset_id": value.asset.id, "bundle_id": value.id}])
    assert contexts and candidates and contexts[0]["market"]
    assert_admitted_context(json.dumps(contexts))
    assert any(str(c.url).startswith("https://finance.yahoo.com/") for c in candidates.values())


def test_only_market_snapshot_still_supplies_original_cited_context():
    value = market_bundle(financials=False)
    db = Database("sqlite://", testing=True)
    seed(db, value)
    context, candidates = conversation_evidence(db, value.asset, [{"role": "assistant", "asset_id": value.asset.id, "bundle_id": value.id}])
    assert len(context) == 1 and context[0]["market"] and context[0]["sources"] and candidates


def test_authenticated_exports_filter_private_derivatives_but_local_page_keeps_history(tmp_path):
    value = derived_bundle()
    db = Database("sqlite://", testing=True)
    seed(db, value)
    app = create_app(db, TOKEN, tmp_path, adapters={"codex": object()})
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer " + TOKEN}
        for format in ("json", "markdown"):
            response = client.get(f"/api/export/{value.id}?format={format}", headers=headers)
            assert response.status_code == 200
            assert_no_private(response.text)
            assert "PERMITTED ISSUER FACT" in response.text and "private backups" in response.text
            assert "9007199254740992" in response.text
        assert "market" not in client.get(f"/api/export/{value.id}", headers=headers).json()
        assert client.get(f"/api/bundles/{value.id}", headers=headers).json()["market"] == value.market.model_dump(mode="json")
    assert db.get("bundle:" + value.id) == value.model_dump(mode="json")


def test_same_user_backup_retains_local_originals_and_resets_network_opt_in():
    value = derived_bundle()
    db, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    seed(db, value)
    db.put("settings", "settings", Settings(experimental_yahoo_enabled=True, cloud_enabled=True).model_dump(mode="json"))
    raw = make_backup(db)
    summary = preview_backup(target, raw)
    restore_backup(target, raw, summary.fingerprint)
    assert target.get("bundle:" + value.id) == value.model_dump(mode="json")
    assert not target.get("settings")["experimental_yahoo_enabled"] and not target.get("settings")["cloud_enabled"]
    assert_admitted_context(json.dumps(factual_context(EvidenceBundle.model_validate(target.get("bundle:" + value.id)))))
    def corrupt(data):
        for record in data["records"]:
            if record["kind"] in ("bundle", "asset"):
                record["payload"]["market"]["bars"][0]["volume"] = "42"
    with pytest.raises(BackupError):
        read_backup(alter(raw, change=corrupt))


@pytest.mark.parametrize("query", ["api_token", "access_key", "crumb", "API-TOKEN"])
def test_source_references_reject_market_authentication_parameters(query):
    with pytest.raises(ValueError):
        Source(asset_id="example", url="https://example.com/history?" + query + "=secret", title="Example", publisher="Example")


def test_legacy_yahoo_metadata_cannot_remove_cloud_or_export_restriction():
    from backend.app.source_operations import shareable_view
    base = market_bundle(financials=False)
    source = Source(id="legacy", asset_id=base.asset.id, url="https://finance.yahoo.com/quote/SYN/", title="PRIVATE LEGACY",
        publisher="Yahoo", policy="summary_allowed", verified=True, usage_scope="standard")
    value = EvidenceBundle(asset=base.asset, sources=[source], claims=[Claim(asset_id=base.asset.id,
        text="PRIVATE LEGACY VALUE", kind="fact", source_ids=[source.id])])
    assert not factual_context(value)["claims"]
    view, notice = shareable_view(value)
    assert notice and not view.claims and not view.sources


def test_optional_live_helper_qualifies_admission_without_printing_prices(monkeypatch):
    import asyncio
    from backend.app.market_retrieval import HistoryRetrieval
    from scripts.qualify_market_history import check
    instrument, _ = identities()
    candidate = history()
    async def retrieve(*args, **kwargs):
        return HistoryRetrieval(None, candidate, (), 4)
    monkeypatch.setattr("scripts.qualify_market_history.covers_boundaries", lambda *args: True)
    store = type("Store", (), {"load": lambda *args: None})()
    report = asyncio.run(check(live=True, symbol="SYN", store=store, retrieve=retrieve,
        check_admission=True, at=AT, resolve=lambda value, at: map_yahoo_history(value, instrument, at=at)))
    assert report["status"] == "retrieval_passed" and report["admission"]["status"] == "passed"
    assert "bars" not in json.dumps(report) and "adjusted_close" not in json.dumps(report)
    assert report["admission"]["cloud_context_included"] and report["admission"]["shareable_export_excluded"]
    assert asyncio.run(check(check_admission=True))["status"] == "not_run"


def test_frontend_private_fixture_passes_the_production_numeric_contract():
    from pathlib import Path
    from backend.app.contracts import EvidenceBundle
    fixture = Path(__file__).resolve().parents[2] / "apps/desktop/src/fixtures/privateMarket.json"
    value = EvidenceBundle.model_validate_json(fixture.read_text(encoding="utf-8"))
    assert value.market and len(value.market.bars) == 2
    assert value.market.bars[0].volume == "9007199254740993"
