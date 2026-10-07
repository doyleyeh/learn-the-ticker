from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.backup import make_backup, preview_backup, read_backup, restore_backup
from backend.app.api import create_app
from backend.app.contracts import ResearchRequest, TermRequest
from backend.app.db import Database, Record
from backend.app.library_cache import CacheError, Node, manage_cache, plan
from tests.desktop.import_deletion_fixture import seed_imports
from tests.desktop.library_scale_fixture import seed_assets


def test_disposable_budget_protects_transitive_roots_and_removes_whole_connected_groups():
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    nodes = {"saved": Node(1, at, {"new"}, True), "new": Node(3, at, {"old"}), "old": Node(5, at),
        "disposable-new": Node(4, at + timedelta(days=1), {"old"}),
        "disposable-old": Node(8, at), "job": Node(2, at, {"disposable-old"})}
    protected, size, removed, amount = plan(nodes, 4)
    assert protected == {"saved", "new", "old"}
    assert size == 14 and amount == 10 and removed == {"disposable-old", "job"}
    assert plan(nodes, 100)[2:] == (set(), 0)
    assert plan(nodes, 0)[2] == {"disposable-new", "disposable-old", "job"}


def test_real_payload_accounting_evicts_only_unsaved_graph_and_round_trips_originals():
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    documents, explanations, _ = seed_imports(db)
    originals = {kind: db.list(kind) for kind in ("saved", "conversation", "report", "import", "import_explanation")}
    before = read_backup(make_backup(db))[1]
    summary = manage_cache(db, budget_bytes=0)
    assert summary.protected_bytes > 0 and summary.disposable_bytes > 0 and summary.removed_items == 0
    assert read_backup(make_backup(db))[1] == before
    deleted = manage_cache(db, evict=True, budget_bytes=0)
    assert deleted.disposable_bytes == 0 and deleted.removed_bytes == summary.disposable_bytes
    assert deleted.protected_bytes == summary.protected_bytes
    assert not db.get("asset:TEST:SCALE:0001") and not db.get("bundle:scale-1-1")
    for kind, values in originals.items():
        assert db.list(kind) == values
    assert db.get("bundle:scale-0-0") and db.get("bundle:scale-0-1")
    assert db.get("import:" + documents[0].id) and db.get("import_explanation:" + explanations[0].id)
    archive = make_backup(db)
    target = Database("sqlite://", testing=True)
    restore_backup(target, archive, preview_backup(target, archive).fingerprint)
    for kind in (*originals, "bundle", "asset"):
        assert target.list(kind) == db.list(kind)
    assert manage_cache(db, evict=True, budget_bytes=0).removed_items == 0


def test_active_research_defers_all_eviction_and_admission_protects_term_evidence():
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    db.queue_research("active", ResearchRequest(query="Synthetic uncached request"))
    before = read_backup(make_backup(db))[1]
    assert manage_cache(db, evict=True, budget_bytes=0).deferred_for_active_work
    assert read_backup(make_backup(db))[1] == before
    db.transition("active", "cancelled")
    request = TermRequest(term="revenue", bundle_id="scale-1-0")
    db.queue_term("term", request)
    assert manage_cache(db, evict=True, budget_bytes=0).deferred_for_active_work
    db.transition("term", "cancelled")
    manage_cache(db, evict=True, budget_bytes=0)
    assert db.get("bundle:scale-1-0") and db.job("term")
    assert not db.get("bundle:scale-1-1")
    make_backup(db)


def test_late_eviction_failure_rolls_back_records_jobs_and_events():
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    before = read_backup(make_backup(db))[1]
    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("DELETE FROM records"):
            raise RuntimeError("Synthetic cache write failure")
    event.listen(db.engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Synthetic cache"):
            manage_cache(db, evict=True, budget_bytes=0)
    finally:
        event.remove(db.engine, "before_cursor_execute", fail)
    assert read_backup(make_backup(db))[1] == before


@pytest.mark.parametrize("kind", ["unknown", "saved"])
def test_unknown_or_missing_references_fail_closed_before_any_removal(kind):
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    with db.session.begin() as session:
        session.add(Record(id=kind + ":bad", kind=kind, payload={"bundle_id": "missing"}))
    before = db.list("bundle")
    with pytest.raises(CacheError):
        manage_cache(db, evict=True, budget_bytes=0)
    assert db.list("bundle") == before and db.get(kind + ":bad")


def test_admission_after_eviction_rejects_missing_bookmark_and_term_without_orphans():
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    manage_cache(db, evict=True, budget_bytes=0)
    with pytest.raises(ValueError, match="snapshot not found"):
        db.create_saved("scale-1-0", "Synthetic bookmark")
    with pytest.raises(ValueError, match="saved evidence"):
        db.queue_term("missing", TermRequest(term="revenue", bundle_id="scale-1-0"))
    assert not db.job("missing")
    make_backup(db)


def test_ten_gb_disposable_budget_excludes_protected_work_and_preserves_exact_boundary():
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Weighted metadata checks arithmetic without pretending to store a 10-GB archive.
    nodes = {"protected": Node(20_000_000_000, at, root=True),
        "older": Node(4_000_000_000, at), "newer": Node(6_000_000_000, at + timedelta(days=1))}
    assert plan(nodes, 10_000_000_000)[2:] == (set(), 0)
    nodes["newer"].size += 1
    assert plan(nodes, 10_000_000_000)[2:] == ({"older"}, 4_000_000_000)


def test_authenticated_offline_cache_status_and_cleanup_respect_configured_budget(tmp_path):
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    db.put("settings", "settings", {"cloud_enabled": False, "cache_gb": 2})
    before = read_backup(make_backup(db))[1]
    app = create_app(db, "synthetic-cache-session-" * 3, tmp_path)
    with TestClient(app) as client:
        assert app.state.cache_failure is None
        assert client.get("/api/library/cache").status_code == 401
        assert client.post("/api/library/cache/cleanup").status_code == 401
        headers = {"Authorization": "Bearer " + "synthetic-cache-session-" * 3}
        status = client.get("/api/library/cache", headers=headers)
        cleanup = client.post("/api/library/cache/cleanup", headers=headers)
        assert status.status_code == cleanup.status_code == 200
        assert status.json()["budget_bytes"] == 2_000_000_000
        assert status.json()["protected_bytes"] > 0 and cleanup.json()["removed_items"] == 0
        assert not app.state.service.tasks
    assert read_backup(make_backup(db))[1] == before


def test_invalid_reference_exposes_fixed_cache_failure_and_never_deletes(tmp_path):
    db = Database("sqlite://", testing=True)
    seed_assets(db, 2)
    db.put("saved:bad", "saved", {"id": "bad", "bundle_id": "missing", "title": "Synthetic bad reference"})
    before = db.list("bundle")
    app = create_app(db, "synthetic-cache-session-" * 3, tmp_path)
    with TestClient(app, headers={"Authorization": "Bearer " + "synthetic-cache-session-" * 3}) as client:
        assert app.state.cache_failure == "Cache references require review; no cached work was removed"
        for method, path in ((client.get, "/api/library/cache"), (client.post, "/api/library/cache/cleanup")):
            response = method(path)
            assert response.status_code == 409 and response.json()["detail"] == app.state.cache_failure
    assert db.list("bundle") == before
