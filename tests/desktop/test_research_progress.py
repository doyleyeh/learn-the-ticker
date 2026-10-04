import asyncio
import copy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.api import create_app
from backend.app.backup import StoredRecord, make_backup, preview_backup, read_backup, restore_backup, validate_library
from backend.app.contracts import Claim, EvidenceBundle, ResearchRequest, RuntimeEvent
from backend.app.db import Database, Event, Job
from backend.app.financial_evidence import attach_financials
from tests.desktop.financial_fixture import AT, financial_result
from tests.desktop.test_application import TOKEN
from tests.desktop.test_structured_research import Runtime, service_at


def checkpoint():
    result = financial_result()
    bundle = attach_financials(EvidenceBundle(asset=result.instrument.asset,
        identity_verification=result.instrument.verification, level="beginner", created_at=AT), result, created_at=AT)
    return EvidenceBundle.model_validate({**bundle.model_dump(), "completion": "section_checkpoint"})


@pytest.mark.parametrize("ending", ["complete", "cancel", "invalid", "manual"])
def test_financial_section_precedes_inference_and_survives_terminal_state(tmp_path, ending):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        class Paused(Runtime):
            async def stream(self, *args, **kwargs):
                entered.set()
                await release.wait()
                if ending == "invalid":
                    yield RuntimeEvent(run_id=args[1], kind="message.delta", text="Unvalidated SECRET output")
                else:
                    async for row in super().stream(*args, **kwargs):
                        yield row
        service, _, _ = service_at(tmp_path, runtime=Paused(financial_result()))
        original = EvidenceBundle(asset=financial_result().instrument.asset, created_at=AT)
        service.db.put("bundle:" + original.id, "bundle", original.model_dump(mode="json"), original.asset.id)
        service.db.put("asset:" + original.asset.id, "asset", original.model_dump(mode="json"))
        job = await service.submit(ResearchRequest(query="Latest financials", asset_id=original.asset.id, refresh=True))
        task = service.tasks[job["id"]]
        await asyncio.wait_for(entered.wait(), 2)
        partial = service.db.job(job["id"])["result"]
        assert partial["completion"] == "section_checkpoint" and partial["financials"]["observations"]
        assert not partial["notes"] and not partial["claims"]
        assert service.db.get("asset:" + original.asset.id) == original.model_dump(mode="json")
        # Actual running-job archive includes the admitted version, not provider output.
        archive = make_backup(service.db)
        target = Database("sqlite://", testing=True)
        restore_backup(target, archive, preview_backup(target, archive).fingerprint)
        assert target.job(job["id"])["status"] == "interrupted"
        assert target.job(job["id"])["result"] == partial
        if ending == "cancel":
            await service.cancel(job["id"])
        else:
            if ending == "manual":
                service.db.put("settings", "settings", {"cloud_enabled": True, "manual_source_review": True})
            release.set()
            await task
        terminal = service.db.job(job["id"])
        assert service.db.get("bundle:" + partial["id"]) == partial
        if ending in ("cancel", "invalid"):
            assert terminal["status"] == ("cancelled" if ending == "cancel" else "failed")
            assert terminal["result"] == partial and service.db.get("asset:" + original.asset.id)["id"] == original.id
        else:
            assert terminal["status"] == "completed" and terminal["result"]["completion"] == "complete"
            assert terminal["result"]["id"] != partial["id"]
            if ending == "manual":
                assert terminal["result"]["financials"] is None
        assert all("SECRET" not in str(row) for row in service.db.events(job["id"]))
        await service.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("change", ["note", "invented_fact", "candidate", "wrong_identity", "empty", "unavailable"])
def test_checkpoint_rejects_unadmitted_content(change):
    value = checkpoint().model_dump(mode="json")
    if change == "note":
        value["notes"] = [Claim(asset_id=value["asset"]["id"], text="Unverified").model_dump(mode="json")]
    elif change == "invented_fact":
        value["claims"] = [Claim(asset_id=value["asset"]["id"], text="Invented fact", kind="fact", source_ids=[value["sources"][0]["id"]]).model_dump(mode="json")]
    elif change == "candidate":
        value["sources"][0]["verified"] = False
    elif change == "wrong_identity":
        value["asset"]["name"] = "Wrong identity"
    elif change == "empty":
        value["financials"] = None
        value["sources"] = []
    else:
        value["state"] = "unavailable"
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(value)


def test_checkpoint_transaction_scope_and_canonical_guards():
    db = Database("sqlite://", testing=True)
    value = checkpoint()
    with db.session.begin() as session:
        session.add(Job(id="partial", status="running", request={"query": "Synthetic", "asset_id": value.asset.id}))
        session.add(Job(id="wrong", status="running", request={"query": "Synthetic", "asset_id": "OTHER"}))
    with pytest.raises(ValueError, match="scope"):
        db.checkpoint_research("wrong", value)
    with pytest.raises(ValueError, match="asset page"):
        db.put("asset:" + value.asset.id, "asset", value.model_dump(mode="json"))
    with pytest.raises(ValueError, match="complete"):
        db.complete_research("partial", value.model_dump(mode="json"))
    def fail(*args):
        raise RuntimeError("Synthetic checkpoint transaction failure")
    event.listen(Event, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="transaction"):
            db.checkpoint_research("partial", value)
    finally:
        event.remove(Event, "before_insert", fail)
    assert not db.list("bundle") and db.job("partial")["result"] is None and not db.events("partial")
    db.checkpoint_research("partial", value)
    db.recover()
    assert db.job("partial")["status"] == "interrupted" and db.job("partial")["result"] == value.model_dump(mode="json")
    changed = copy.deepcopy(value.model_dump(mode="json"))
    changed["language"] = "zh-TW"
    with pytest.raises(ValueError, match="immutable"):
        db.put("bundle:" + value.id, "bundle", changed)


def test_partial_export_discloses_incomplete_state_and_original_citations(tmp_path):
    db = Database("sqlite://", testing=True)
    value = checkpoint()
    db.put("bundle:" + value.id, "bundle", value.model_dump(mode="json"), value.asset.id)
    with TestClient(create_app(db, TOKEN, tmp_path), headers={"Authorization": "Bearer " + TOKEN}) as client:
        response = client.get(f"/api/export/{value.id}?format=markdown")
        assert response.status_code == 200 and "Incomplete research" in response.text
        assert str(value.sources[0].url) in response.text and value.financials.observations[0].value in response.text
        assert client.get(f"/api/export/{value.id}").json()["completion"] == "section_checkpoint"


@pytest.mark.parametrize("tamper", ["completed_job", "current_asset"])
def test_archive_cannot_promote_incomplete_research(tamper):
    db = Database("sqlite://", testing=True)
    value = checkpoint()
    with db.session.begin() as session:
        session.add(Job(id="partial", status="running", request={"query": "Synthetic"}))
    db.checkpoint_research("partial", value)
    _, data = read_backup(make_backup(db))
    if tamper == "completed_job":
        data.jobs[0].status = "completed"
    else:
        data.records.append(StoredRecord(id="asset:" + value.asset.id, kind="asset", payload=value.model_dump(mode="json"), updated_at=AT))
    with pytest.raises(ValueError, match="checkpoint|incomplete"):
        validate_library(data)
