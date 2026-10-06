import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.api import create_app
from backend.app.backup import make_backup, preview_backup, read_backup, restore_backup
from backend.app.contracts import TermRequest
from backend.app.db import Database, Job
from backend.app.library_deletion import delete_saved_item
from tests.desktop.library_scale_fixture import seed_assets
from tests.desktop.term_deletion_fixture import seed_terms


@pytest.mark.parametrize("index", [0, 2])
def test_authenticated_offline_term_question_deletion_preserves_other_scopes_and_originals(tmp_path, index):
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    values, jobs = seed_terms(db, "scale-0-0")
    original = db.list("bundle")
    token = "synthetic-term-delete-" * 3
    path = "/api/library/items/term/" + values[index].id
    with TestClient(create_app(db, token, tmp_path)) as client:
        assert client.delete(path).status_code == 401
        headers = {"Authorization": "Bearer " + token}
        response = client.delete(path, headers=headers)
        assert response.status_code == 200 and response.json()["deleted"] and response.json()["evidence_preserved"]
        assert client.delete(path, headers=headers).json()["deleted"] is False
    assert db.list("bundle") == original and db.job(jobs[index]) is None and not db.events(jobs[index])
    assert {row["id"] for row in db.list("term")} == {value.id for i, value in enumerate(values) if i != index}
    archive = make_backup(db)
    target = Database("sqlite://", testing=True)
    restore_backup(target, archive, preview_backup(target, archive).fingerprint)
    assert target.list("term") == db.list("term") and target.list("bundle") == original
    assert target.job(jobs[index]) is None


@pytest.mark.parametrize("original, equivalent", [("Revenue", "REVENUE"), ("Straße", "STRASSE")])
def test_active_same_scope_refuses_delete_and_casefold_equivalent_failed_jobs_are_removed(original, equivalent):
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    values, jobs = seed_terms(db, "scale-0-0", original)
    request = TermRequest(term=equivalent, bundle_id="scale-0-0")
    # A restored pending request can coexist with an earlier cached result.
    with db.session.begin() as session:
        session.add(Job(id="retry", status="queued", request=request.model_dump(mode="json")))
    before = read_backup(make_backup(db))[1]
    with pytest.raises(ValueError, match="active explanation"):
        delete_saved_item(db, "term", values[0].id)
    assert read_backup(make_backup(db))[1] == before
    db.transition("retry", "failed")
    delete_saved_item(db, "term", values[0].id)
    assert not db.job("retry") and not db.job(jobs[0]) and db.job(jobs[2])
    assert db.get("bundle:scale-0-0")
    make_backup(db)


def test_late_term_delete_failure_rolls_back_explanation_jobs_events():
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    values, _ = seed_terms(db, "scale-0-0")
    before = read_backup(make_backup(db))[1]
    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("DELETE FROM records"):
            raise RuntimeError("Synthetic term deletion failure")
    event.listen(db.engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Synthetic term deletion"):
            delete_saved_item(db, "term", values[0].id)
    finally:
        event.remove(db.engine, "before_cursor_execute", fail)
    assert read_backup(make_backup(db))[1] == before


def test_malformed_job_does_not_expose_stored_content_or_partially_remove_items(tmp_path):
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    values, jobs = seed_terms(db, "scale-0-0")
    with db.session.begin() as session:
        job = session.get(Job, jobs[0])
        job.request = {**job.request, "term": "\x00PRIVATE_STORED_DIAGNOSTIC"}
    with TestClient(create_app(db, "synthetic-term-delete-" * 3, tmp_path),
            headers={"Authorization": "Bearer " + "synthetic-term-delete-" * 3}) as client:
        response = client.delete("/api/library/items/term/" + values[0].id)
        assert response.status_code == 409 and "PRIVATE" not in response.text
    assert db.get("term:" + values[0].id) and db.job(jobs[0]) and db.events(jobs[0])
