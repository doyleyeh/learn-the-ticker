import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.api import create_app
from backend.app.backup import make_backup, preview_backup, read_backup, restore_backup
from backend.app.db import Database
from backend.app.import_learning import ImportLearningRequest, learning_key
from backend.app.library_deletion import delete_retained_item
from tests.desktop.import_deletion_fixture import seed_imports
from tests.desktop.test_import_learning import setup

TOKEN = "synthetic-import-deletion-" * 3


@pytest.mark.parametrize("kind", ["import", "import_explanation"])
def test_authenticated_offline_deletion_is_scoped_idempotent_and_restorable(tmp_path, kind):
    db = Database("sqlite://", testing=True)
    documents, values, jobs = seed_imports(db)
    item_id = documents[0].id if kind == "import" else values[0].id
    path = f"/api/library/documents/{kind}/{item_id}"
    original_archive = make_backup(db)
    with TestClient(create_app(db, TOKEN, tmp_path)) as client:
        assert client.delete(path).status_code == 401
        response = client.delete(path, headers={"Authorization": "Bearer " + TOKEN})
        assert response.status_code == 200 and response.json() == {
            "schema_version": "1", "kind": kind, "id": item_id, "deleted": True,
            "original_document_preserved": kind == "import_explanation"}
        assert client.delete(path, headers={"Authorization": "Bearer " + TOKEN}).json()["deleted"] is False
    assert db.get("import:" + documents[1].id) == documents[1].model_dump(mode="json")
    assert db.get("import_explanation:" + values[2].id) == values[2].model_dump(mode="json")
    removed = jobs[:2] if kind == "import" else jobs[:1]
    assert all(db.job(job_id) is None and db.events(job_id) == [] for job_id in removed)
    assert all(db.job(job_id) and db.events(job_id) for job_id in jobs if job_id not in removed)
    if kind == "import_explanation":
        assert db.get("import:" + documents[0].id) == documents[0].model_dump(mode="json")
        assert db.get("import_explanation:" + values[1].id) == values[1].model_dump(mode="json")
    else:
        assert not db.get("import:" + documents[0].id) and not db.get("import_explanation:" + values[1].id)
    archive = make_backup(db)
    target = Database("sqlite://", testing=True)
    restore_backup(target, archive, preview_backup(target, archive).fingerprint)
    assert target.list("import") == db.list("import") and target.list("import_explanation") == db.list("import_explanation")
    assert target.get(kind + ":" + item_id) is None
    # Deleting in this library cannot rewrite an already downloaded backup.
    assert len(read_backup(original_archive)[1].records) == 6


@pytest.mark.parametrize("kind", ["bundle", "asset", "settings", "saved", "term", "unknown"])
def test_document_delete_cannot_remove_other_kinds(tmp_path, kind):
    db = Database("sqlite://", testing=True)
    documents, _, _ = seed_imports(db)
    before = read_backup(make_backup(db))[1]
    with TestClient(create_app(db, TOKEN, tmp_path), headers={"Authorization": "Bearer " + TOKEN}) as client:
        assert client.delete(f"/api/library/documents/{kind}/{documents[0].id}").status_code == 422
    assert read_backup(make_backup(db))[1] == before


def test_active_explanation_blocks_document_deletion_but_other_language_can_be_deleted():
    db = Database("sqlite://", testing=True)
    documents, values, _ = seed_imports(db)
    request = ImportLearningRequest(document_id=documents[0].id, content_hash=documents[0].document.content_hash,
        level="intermediate", transmission_confirmed=True)
    db.queue_import_explanation("active-document-job", request)
    with pytest.raises(ValueError, match="active document explanation"):
        delete_retained_item(db, "import", documents[0].id)
    assert delete_retained_item(db, "import_explanation", values[0].id).deleted
    assert db.job("active-document-job")["status"] == "queued"
    db.transition("active-document-job", "cancelled")
    assert delete_retained_item(db, "import", documents[0].id).deleted
    assert db.job("active-document-job") is None
    make_backup(db)


@pytest.mark.parametrize("kind", ["import", "import_explanation"])
def test_late_delete_failure_restores_all_originals_explanations_jobs_and_events(kind):
    db = Database("sqlite://", testing=True)
    documents, values, _ = seed_imports(db)
    before = read_backup(make_backup(db))[1]
    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("DELETE FROM records"):
            raise RuntimeError("Synthetic retained-item deletion failure")
    event.listen(db.engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Synthetic retained-item deletion"):
            delete_retained_item(db, kind, documents[0].id if kind == "import" else values[0].id)
    finally:
        event.remove(db.engine, "before_cursor_execute", fail)
    assert read_backup(make_backup(db))[1] == before


def test_parser_completion_after_deletion_cannot_admit_a_job_or_call_provider(tmp_path, monkeypatch):
    async def scenario():
        db, item, runtime, research, service, request = setup(tmp_path)
        lookup = service.lookup
        async def deleted_while_parsing(scope):
            result = await lookup(scope)
            delete_retained_item(db, "import", item.id)
            return result
        monkeypatch.setattr(service, "lookup", deleted_while_parsing)
        with pytest.raises(ValueError, match="no longer exists"):
            await service.submit(request)
        assert not runtime.calls and not research.tasks and not service.pending
        assert read_backup(make_backup(db))[1].jobs == []
        await research.close()
    asyncio.run(scenario())


def test_admission_rechecks_hash_and_reuses_existing_explanation_without_new_job():
    db = Database("sqlite://", testing=True)
    documents, values, _ = seed_imports(db)
    request = ImportLearningRequest(document_id=documents[0].id, content_hash=documents[0].document.content_hash, transmission_confirmed=True)
    assert db.queue_import_explanation("redundant", request) == values[0].model_dump(mode="json")
    assert not db.job("redundant")
    with pytest.raises(ValueError, match="scope changed"):
        db.queue_import_explanation("changed", request.model_copy(update={"content_hash": "0" * 64}))
    assert not db.job("changed") and db.get("import_explanation:" + learning_key(request))
