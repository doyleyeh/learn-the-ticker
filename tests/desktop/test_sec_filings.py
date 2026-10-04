import asyncio
import json
import threading
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.contracts import Claim, EvidenceBundle, ResearchRequest, RuntimeEvent, Source
from backend.app.db import Database
from backend.app.evidence import candidate_metadata, verify_candidate
from backend.app.sec_filings import SecFilingsAdapter, parse_filings
from tests.desktop.financial_fixture import AT, financial_bundle, financial_result
from tests.desktop.test_structured_research import service_at, finish


def raw(**changes):
    recent = {"accessionNumber": ["0000009999-26-000003"], "filingDate": ["2026-09-17"],
              "reportDate": ["2026-09-15"], "form": ["8-K"], "primaryDocument": ["event.htm"]}
    recent.update(changes)
    return json.dumps({"cik": "0000000001", "name": "SYNTHETIC COMPANY", "filings": {"recent": recent}}).encode()


def parse(value=None):
    return parse_filings(raw() if value is None else value, financial_result().issuer, retrieved_at=AT)


def dated_bundle():
    bundle = financial_bundle()
    proof = parse()[0]
    source = Source(id="event", asset_id=bundle.financials.issuer.id, url=proof.document_url, title="Synthetic filing", publisher="candidate")
    source = verify_candidate(source, bundle.financials.issuer, lambda _: "SYNTHETIC COMPANY reported a material event.")
    source = source.model_copy(update={"asset_id": bundle.asset.id, "retrieved_at": AT, "filing_publication": proof,
                                       "published_at": proof.filed, "as_of": proof.report_date})
    return EvidenceBundle.model_validate({**bundle.model_dump(), "sources": [*bundle.sources, source]})


def test_index_dates_are_issuer_bound_and_document_url_uses_issuer_not_filing_agent():
    proof = parse()[0]
    assert str(proof.document_url) == "https://www.sec.gov/Archives/edgar/data/1/000000999926000003/event.htm"
    assert str(proof.index_url) == "https://data.sec.gov/submissions/CIK0000000001.json"
    assert proof.filed.isoformat() == "2026-09-17" and proof.report_date.isoformat() == "2026-09-15"
    assert len(proof.index_hash) == 64 and proof.retrieved_at == AT
    assert EvidenceBundle.model_validate_json(dated_bundle().model_dump_json()).sources[-1].filing_publication == proof


@pytest.mark.parametrize("changes", [
    {"filingDate": []}, {"form": "8-K"}, {"reportDate": [None]}, {"filingDate": ["2030-01-01"]},
    {"filingDate": ["2026-9-1"]}, {"reportDate": ["2026-09-18"]}, {"accessionNumber": ["../secrets"]},
    {"primaryDocument": ["../event.htm"]}, {"primaryDocument": ["https://elsewhere.example/a.htm"]},
    {"primaryDocument": ["event.pdf"]}, {"primaryDocument": ["event.htm?token=private"]},
    {"primaryDocument": ["dir\\event.htm"]}, {"form": [None]},
])
def test_malformed_arrays_dates_and_noncanonical_documents_fail(changes):
    with pytest.raises(ValueError):
        parse(raw(**changes))


def test_wrong_issuer_name_cik_duplicate_keys_and_large_documents_fail():
    for value in (raw().replace(b'SYNTHETIC COMPANY', b'DIFFERENT COMPANY'), raw().replace(b'0000000001', b'0000000002'),
                  raw().replace(b'"cik":', b'"cik": "0000000001", "cik":'), b' ' * 2_000_001,
                  b'[' * 2000 + b'0' + b']' * 2000):
        with pytest.raises(ValueError):
            parse(value)
    with pytest.raises(ValueError):
        parse_filings(raw(), financial_result().issuer, retrieved_at=AT + timedelta(days=2))
    assert parse(raw(form=["4"], primaryDocument=["xslF345/form4.xml"])) == []


@pytest.mark.parametrize("change", [
    lambda s: s.update(published_at="2026-10-04"),
    lambda s: s.update(as_of="2026-10-04"),
    lambda s: s.update(content_hash=""),
    lambda s: s.update(verified=False),
    lambda s: s.update(excerpt=""),
    lambda s: s.update(policy="link_only", excerpt=""),
    lambda s: s["filing_publication"].update(cik="0000000002"),
    lambda s: s["filing_publication"].update(index_url="https://data.sec.gov/submissions/CIK0000000002.json"),
    lambda s: s["filing_publication"].update(document_url="https://www.sec.gov/Archives/edgar/data/1/000000999926000004/event.htm"),
    lambda s: s["filing_publication"].update(retrieved_at="2030-01-01T00:00:00Z"),
])
def test_changed_publication_proofs_never_validate_as_dated_evidence(change):
    payload = dated_bundle().model_dump(mode="json")
    change(payload["sources"][-1])
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(payload)


def test_model_date_proof_is_cleared_and_cancellation_stops_index_processing():
    source = dated_bundle().sources[-1]
    cleaned = candidate_metadata(source)
    assert cleaned.filing_publication is None and cleaned.published_at is None and cleaned.as_of is None
    cancelled = threading.Event()
    def fetch(*args, **kwargs):
        cancelled.set()
        return raw()
    with pytest.raises(InterruptedError):
        SecFilingsAdapter(fetch, clock=lambda: AT).retrieve(financial_result().issuer, cancelled=cancelled)


def test_source_dates_and_index_references_survive_personal_exports(tmp_path):
    bundle = dated_bundle()
    db = Database("sqlite://", testing=True)
    db.put("bundle:" + bundle.id, "bundle", bundle.model_dump(mode="json"))
    token = "f" * 64
    with TestClient(create_app(db, token, tmp_path)) as client:
        response = client.get("/api/export/" + bundle.id + "?format=markdown", headers={"Authorization": "Bearer " + token})
        assert response.status_code == 200
        assert "published 2026-09-17; as of 2026-09-15" in response.text
        assert "https://data.sec.gov/submissions/CIK0000000001.json" in response.text
        assert bundle.sources[-1].filing_publication.index_hash in response.text


def test_real_source_verifier_uses_separate_issuer_then_persists_publication_scope(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.evidence.now", lambda: AT)
    async def scenario():
        service, runtime, _ = service_at(tmp_path)
        service.filing_adapter = SecFilingsAdapter(lambda *args, **kwargs: raw(), clock=lambda: AT)
        service.verifier = lambda source, asset: verify_candidate(source, asset, lambda _: "SYNTHETIC COMPANY reported a material event.")
        proof = parse()[0]
        async def stream(prompt, run_id, workspace, model=None):
            assert "2026-09-17" in prompt and "OFFICIAL FILING EVENTS" in prompt
            source = Source(id="event", asset_id=runtime.result.instrument.asset.id, url=proof.document_url, title="Synthetic event", publisher="candidate")
            claim = Claim(asset_id=source.asset_id, text="SYNTHETIC COMPANY reported a material event.", kind="fact", source_ids=[source.id])
            yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({"candidates": [runtime.result.instrument.asset.model_dump(mode="json")],
                "sources": [source.model_dump(mode="json")], "claims": [claim.model_dump(mode="json")]}))
        runtime.stream = stream
        job = await finish(service, ResearchRequest(query="FIGI:chosen"))
        assert job["status"] == "completed", job
        bundle = EvidenceBundle.model_validate(job["result"])
        assert len(bundle.claims) == 1
        source = next(source for source in bundle.sources if source.id == "event")
        assert source.filing_publication == proof and source.asset_id == bundle.asset.id
        assert source.published_at.isoformat() == "2026-09-17" and source.as_of.isoformat() == "2026-09-15"
        assert any("No source published today" in note.text for note in bundle.notes)
        await service.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("manual_during_inference", [False, True])
def test_bounded_filing_text_precedes_inference_and_model_cannot_replace_it(tmp_path, monkeypatch, manual_during_inference):
    monkeypatch.setattr("backend.app.evidence.now", lambda: AT)
    async def scenario():
        service, runtime, _ = service_at(tmp_path)
        service.filing_adapter = SecFilingsAdapter(lambda *args, **kwargs: raw(
            accessionNumber=[f"0000009999-26-00000{i}" for i in (3, 4, 5)],
            filingDate=["2026-09-17"] * 3, reportDate=["2026-09-15"] * 3,
            form=["8-K"] * 3, primaryDocument=[f"event{i}.htm" for i in (3, 4, 5)]), clock=lambda: AT)
        seen = []
        def verifier(source, asset):
            seen.append(str(source.url))
            return verify_candidate(source, asset, lambda _: "SYNTHETIC COMPANY reported a material event.")
        service.verifier = verifier
        async def stream(prompt, run_id, workspace, model=None):
            assert len(seen) == 2 and seen[0].endswith("event5.htm") and seen[1].endswith("event4.htm")
            line = next(line for line in prompt.splitlines() if line.startswith("INDEPENDENTLY RETRIEVED FILING SOURCES"))
            sources = json.loads(line.split(": ", 1)[1])
            assert len(sources) == 2 and sources[0]["excerpt"] == "SYNTHETIC COMPANY reported a material event."
            candidate = {**sources[0], "url": "https://unreviewed.example/replacement", "excerpt": "MADE_UP", "filing_publication": None}
            claim = Claim(asset_id=runtime.result.instrument.asset.id, kind="fact", text=sources[0]["excerpt"], source_ids=[sources[0]["id"]])
            if manual_during_inference:
                service.db.put("settings", "settings", {"cloud_enabled": True, "manual_source_review": True})
            yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({"candidates": [runtime.result.instrument.asset.model_dump(mode="json")],
                "sources": [candidate], "claims": [claim.model_dump(mode="json")]}))
        runtime.stream = stream
        job = await finish(service)
        assert job["status"] == "completed", job
        bundle = EvidenceBundle.model_validate(job["result"])
        assert len(seen) == 2 and "MADE_UP" not in bundle.model_dump_json()
        assert len(bundle.claims) == (0 if manual_during_inference else 1)
        assert sum(source.filing_publication is not None for source in bundle.sources) == (0 if manual_during_inference else 2)
        if manual_during_inference:
            assert all(not source.verified and not source.excerpt for source in bundle.sources)
        await service.close()
    asyncio.run(scenario())


def test_filing_access_failure_is_not_retried_after_inference(tmp_path):
    from backend.app.evidence import SourceFetchError
    async def scenario():
        service, runtime, _ = service_at(tmp_path)
        service.filing_adapter = SecFilingsAdapter(lambda *args, **kwargs: raw(), clock=lambda: AT)
        calls = []
        def unavailable(source, asset):
            calls.append(str(source.url))
            raise SourceFetchError(429)
        service.verifier = unavailable
        async def stream(prompt, run_id, workspace, model=None):
            assert len(calls) == 1 and "INDEPENDENTLY RETRIEVED FILING SOURCES" not in prompt
            candidate = Source(asset_id=runtime.result.instrument.asset.id, url=parse()[0].document_url, title="Candidate", publisher="candidate")
            yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({"candidates": [runtime.result.instrument.asset.model_dump(mode="json")], "sources": [candidate.model_dump(mode="json")]}))
        runtime.stream = stream
        job = await finish(service)
        assert job["status"] == "completed" and len(calls) == 1
        assert not job["result"]["claims"] and job["result"]["sources"][0]["filing_publication"] is None
        await service.close()
    asyncio.run(scenario())
