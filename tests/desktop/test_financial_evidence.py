import json
from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.backup import BackupError, make_backup, preview_backup, restore_backup
from backend.app.contracts import Claim, EvidenceBundle, ResearchRequest, ResearchResult, SavedResearch
from backend.app.db import Database, Job
from backend.app.evidence import admit_bundle, factual_context
from backend.app.financial_evidence import attach_financials, numeric_context
from backend.app.research_cache import reusable
from tests.desktop.test_backup import alter
from tests.desktop.financial_fixture import AT, financial_bundle, financial_result

TOKEN = "e" * 64


def seed(db, bundle):
    with db.session.begin() as session:
        session.add(Job(id="financial", status="running", request=ResearchRequest(query="Synthetic issuer").model_dump(mode="json")))
    db.complete_research("financial", bundle.model_dump(mode="json"))


def test_exact_decimals_versions_and_issuer_scope_survive_serialization():
    bundle = financial_bundle()
    roundtrip = EvidenceBundle.model_validate_json(bundle.model_dump_json())
    assert roundtrip == bundle and roundtrip.financials.scope == "issuer"
    assert [row.value for row in bundle.financials.observations] == ["9007199254740993", "9007199254740992"]
    assert [row.revision for row in bundle.financials.observations] == ["superseded", "current"]
    assert bundle.asset.identifiers.get("cik") is None
    assert all(source.verified and source.excerpt == "" and source.provenance == "structured_adapter" for source in bundle.sources)
    assert not bundle.claims and "corporate_actions_unavailable" in bundle.financials.gaps


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(identity_verification=None),
    lambda p: p["asset"].update(exchange="US"),
    lambda p: p["financials"]["issuer"].update(name="Different issuer"),
    lambda p: p["financials"]["issuer_verification"].update(authority="provider"),
    lambda p: p["financials"].update(checked_at="2030-01-01T00:00:00Z"),
    lambda p: p["financials"]["observations"][0].update(cik="0000000002"),
    lambda p: p["financials"]["observations"][0].update(concept="us-gaap:Unregistered"),
    lambda p: p["financials"]["observations"][0].update(value=9007199254740993),
    lambda p: p["financials"]["observations"][0].update(value="9007199254740993.0"),
    lambda p: p["financials"]["observations"][0].update(value="9007199254740994"),
    lambda p: p["financials"]["observations"][0].update(unit="shares"),
    lambda p: p["financials"]["observations"][0].update(period="quarter"),
    lambda p: p["financials"]["observations"][0].update(filed="2030-01-01"),
    lambda p: p["financials"]["observations"][0].update(source_id="missing"),
    lambda p: p["financials"]["observations"][0].update(revision="current"),
    lambda p: p["financials"]["observations"][1].update(supersedes=[]),
    lambda p: p["financials"]["observations"][1].update(supersedes=[p["financials"]["observations"][1]["id"]]),
    lambda p: p["financials"]["observations"].append(p["financials"]["observations"][0]),
    lambda p: p["financials"].update(gaps=["provider raw diagnostic"]),
    lambda p: p["financials"]["gaps"].remove("Revenues:incomplete_quarter_history"),
    lambda p: p["sources"][0].update(asset_id="WRONG"),
    lambda p: p["sources"][0].update(verified=False),
    lambda p: p["sources"][0].update(policy="metadata_only"),
    lambda p: p["sources"][0].update(url="https://data.sec.gov/api/xbrl/companyconcept/CIK0000000002/us-gaap/Revenues.json"),
    lambda p: p["sources"][0].update(content_hash="0" * 64),
    lambda p: p["sources"][0].update(retrieved_at="2030-01-01T00:00:00Z"),
    lambda p: p["sources"][0].update(published_at="2026-10-04"),
    lambda p: p["sources"][0].update(as_of="2026-10-04"),
    lambda p: p["sources"][0].update(excerpt="Provider's invented numbers"),
    lambda p: p["sources"][0].update(provenance="agent_candidate"),
])
def test_changed_scope_value_period_rights_dates_or_revisions_fail_before_writes(mutate):
    payload = financial_bundle().model_dump(mode="json")
    mutate(payload)
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(payload)
    db = Database("sqlite://", testing=True)
    with db.session.begin() as session:
        session.add(Job(id="financial", status="running", request={"query": "Synthetic"}))
    with pytest.raises(ValueError):
        db.complete_research("financial", payload)
    assert not db.list("bundle") and not db.list("asset") and not db.events("financial")
    assert db.job("financial")["status"] == "running"


def test_conflicts_and_unverified_model_values_never_enter_numeric_context():
    bundle = financial_bundle(conflict=True)
    assert numeric_context(bundle) == []
    context = factual_context(bundle)
    assert context["financials"]["observations"] == [] and not context["sources"]
    assert "Revenues:conflicting_latest_values" in context["financials"]["gaps"]
    payload = bundle.model_dump(mode="json")
    payload["financials"]["gaps"].remove("Revenues:conflicting_latest_values")
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(payload)
    candidate = Claim(asset_id=bundle.asset.id, kind="fact", text="Revenue is 123", value=123, unit="USD", source_ids=[bundle.sources[0].id])
    proposed = admit_bundle(bundle.asset, bundle.sources, [candidate])
    assert not proposed.claims and proposed.notes[0].value is None and numeric_context(proposed) == []
    with pytest.raises(ValueError):
        ResearchResult.model_validate({"candidates": [bundle.asset.model_dump()], "financials": bundle.financials.model_dump()})


def test_current_numeric_context_keeps_dates_units_and_citations_without_notes():
    bundle = financial_bundle()
    bundle.notes.append(Claim(asset_id=bundle.asset.id, text="UNVERIFIED secret fantasy 123"))
    context = factual_context(bundle)
    assert "UNVERIFIED" not in json.dumps(context)
    row = context["financials"]["observations"][0]
    assert row["value"] == "9007199254740992" and row["unit"] == "USD"
    assert row["end"] == "2025-12-31" and row["source_id"] == context["sources"][0]["id"]
    assert not reusable(bundle, ResearchRequest(query="Synthetic", asset_id=bundle.asset.id, language="zh-TW", level="intermediate"), at=AT)


def test_adapter_scope_and_snapshot_immutability_are_required():
    result = financial_result()
    bundle = EvidenceBundle(asset=result.instrument.asset, identity_verification=result.instrument.verification, created_at=AT)
    with pytest.raises(ValueError):
        attach_financials(bundle, replace(result, issuer=None), created_at=AT)
    with pytest.raises(ValueError):
        attach_financials(bundle, result, created_at=AT + timedelta(days=2))
    with pytest.raises(ValueError):
        attach_financials(financial_bundle(), result, created_at=AT)
    db = Database("sqlite://", testing=True)
    seed(db, financial_bundle())
    saved = db.list("bundle")[0]
    changed = {**saved, "language": "en"}
    with pytest.raises(ValueError, match="immutable"):
        db.put("bundle:" + saved["id"], "bundle", changed)


def test_archive_restore_retains_exact_values_conflicts_and_rejects_modified_references():
    source, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    bundle = financial_bundle(conflict=True)
    seed(source, bundle)
    saved = SavedResearch(bundle_id=bundle.id, title="Historical conflict")
    source.put("saved:" + saved.id, "saved", saved.model_dump(mode="json"))
    archive = make_backup(source)
    restore_backup(target, archive, preview_backup(target, archive).fingerprint)
    assert target.get("bundle:" + bundle.id) == bundle.model_dump(mode="json")
    assert target.job("financial")["result"] == bundle.model_dump(mode="json")
    assert target.list("saved")[0]["bundle_id"] == bundle.id
    def mutate(data):
        for record in data["records"]:
            if record["kind"] in ("asset", "bundle"):
                record["payload"]["financials"]["observations"][0]["source_id"] = "missing"
    # Even a recomputed archive checksum cannot bypass internal numeric validation.
    with pytest.raises(BackupError):
        preview_backup(Database("sqlite://", testing=True), alter(archive, change=mutate))


def test_exports_retain_exact_numbers_dates_revisions_and_citations(tmp_path):
    db = Database("sqlite://", testing=True)
    bundle = financial_bundle(conflict=True)
    seed(db, bundle)
    with TestClient(create_app(db, TOKEN, tmp_path)) as client:
        path, headers = "/api/export/" + bundle.id, {"Authorization": "Bearer " + TOKEN}
        result = client.get(path, headers=headers).json()
        assert result["financials"]["observations"][0]["value"] == "9007199254740993"
        text = client.get(path + "?format=markdown", headers=headers).text
        assert all(word in text for word in ("Issuer financial", "9007199254740993 USD", "2025-12-31", "conflict", "superseded", bundle.sources[0].id))
        assert all("excerpt" not in source for source in result["sources"])


def test_legacy_snapshot_stays_readable_without_retroactive_numeric_verification():
    payload = financial_bundle().model_dump(mode="json")
    for key in ("financials", "identity_verification", "level"):
        payload.pop(key)
    payload["sources"] = []
    assert EvidenceBundle.model_validate(payload).financials is None


def test_live_helper_checks_contract_with_synthetic_transport_and_sanitizes_bad_admission(monkeypatch):
    from scripts.qualify_sec_financials import check
    monkeypatch.setattr("backend.app.financial_evidence.now", lambda: AT)
    class Adapter:
        def retrieve(self, query):
            return financial_result()
    assert check(live=True, adapter=Adapter())["numeric_contract_validated"]
    class WrongScope:
        def retrieve(self, query):
            return replace(financial_result(), checked_at=AT + timedelta(days=2))
    report = check(live=True, adapter=WrongScope())
    assert report["status"] == "blocked" and "observations" not in report
