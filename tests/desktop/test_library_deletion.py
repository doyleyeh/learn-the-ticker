"""Deletion is explicit, local, scoped and separate from evidence eviction."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.api import create_app
from backend.app.backup import make_backup, preview_backup, restore_backup
from backend.app.comparisons import build_comparison
from backend.app.contracts import EvidenceBundle, ResearchRequest, RuntimeEvent
from backend.app.db import Database, Event
from backend.app.library_deletion import delete_saved_item
from tests.desktop.library_scale_fixture import seed_assets

TOKEN = "synthetic-deletion-session-" * 3


def seed(db):
    seed_assets(db, 2)
    comparison = build_comparison(*(EvidenceBundle.model_validate(db.get(f"bundle:scale-{index}-0")) for index in (0, 1)))
    db.put("comparison:" + comparison.id, "comparison", comparison.model_dump(mode="json"))
    return {kind: db.list(kind)[0]["id"] for kind in ("saved", "conversation", "comparison", "report")}


@pytest.mark.parametrize("kind", ["saved", "conversation", "comparison", "report"])
def test_authenticated_offline_delete_is_idempotent_and_preserves_all_other_artifacts(tmp_path, kind):
    db = Database("sqlite://", testing=True)
    ids = seed(db)
    db.put("settings", "settings", {"cloud_enabled": False})
    originals = {name: db.list(name) for name in ("asset", "bundle", "saved", "conversation", "comparison", "report")}
    path = f"/api/library/items/{kind}/{ids[kind]}"
    with TestClient(create_app(db, TOKEN, tmp_path)) as client:
        assert client.delete(path).status_code == 401
        response = client.delete(path, headers={"Authorization": "Bearer " + TOKEN})
        assert response.status_code == 200 and response.json() == {
            "schema_version": "1", "kind": kind, "id": ids[kind], "deleted": True, "evidence_preserved": True}
        assert client.delete(path, headers={"Authorization": "Bearer " + TOKEN}).json()["deleted"] is False
    for name, rows in originals.items():
        assert db.list(name) == ([] if name == kind else rows)
    archive = make_backup(db)
    target = Database("sqlite://", testing=True)
    restore_backup(target, archive, preview_backup(target, archive).fingerprint)
    assert target.get(kind + ":" + ids[kind]) is None
    assert target.list("bundle") == db.list("bundle")
    assert target.list("asset") == db.list("asset")


@pytest.mark.parametrize("kind", ["bundle", "asset", "settings", "import", "term", "job", "unknown"])
def test_delete_rejects_unimplemented_or_protected_record_types(tmp_path, kind):
    db = Database("sqlite://", testing=True)
    seed(db)
    before = make_backup(db)
    with TestClient(create_app(db, TOKEN, tmp_path), headers={"Authorization": "Bearer " + TOKEN}) as client:
        assert client.delete(f"/api/library/items/{kind}/scale-0-0").status_code == 422
    # No mutation: compare archive data rather than manifest creation timestamps.
    from backend.app.backup import read_backup
    assert read_backup(make_backup(db))[1] == read_backup(before)[1]


def test_active_conversation_cannot_be_deleted_then_cancelled_job_events_are_removed_atomically():
    db = Database("sqlite://", testing=True)
    ids = seed(db)
    chat = db.get("conversation:" + ids["conversation"])
    db.queue_research("question", ResearchRequest(query="Synthetic question", asset_id=chat["asset_id"], conversation_id=chat["id"]))
    with db.session.begin() as session:
        session.add(Event(job_id="question", payload=RuntimeEvent(run_id="question", kind="run.started").model_dump(mode="json")))
    with pytest.raises(ValueError, match="active answer"):
        delete_saved_item(db, "conversation", chat["id"])
    assert db.job("question")["status"] == "queued" and db.get("conversation:" + chat["id"])
    db.transition("question", "cancelled")
    delete_saved_item(db, "conversation", chat["id"])
    assert not db.job("question") and not db.events("question")
    assert db.get("saved:" + ids["saved"]) and db.get("bundle:" + chat["context_bundle_id"])
    make_backup(db)


def test_delete_failure_rolls_back_transcript_jobs_events_and_keeps_saved_references():
    db = Database("sqlite://", testing=True)
    ids = seed(db)
    chat = db.get("conversation:" + ids["conversation"])
    db.queue_research("question", ResearchRequest(query="Synthetic question", asset_id=chat["asset_id"], conversation_id=chat["id"]))
    db.transition("question", "failed")
    with db.session.begin() as session:
        session.add(Event(job_id="question", payload=RuntimeEvent(run_id="question", kind="run.failed").model_dump(mode="json")))
    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("DELETE FROM records"):
            raise RuntimeError("Synthetic deletion failure")
    event.listen(db.engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Synthetic deletion"):
            delete_saved_item(db, "conversation", chat["id"])
    finally:
        event.remove(db.engine, "before_cursor_execute", fail)
    assert db.get("conversation:" + chat["id"]) and db.job("question")["status"] == "failed"
    assert len(db.events("question")) == 1
    assert db.get("saved:" + ids["saved"]) and db.get("bundle:" + chat["context_bundle_id"])
    make_backup(db)
