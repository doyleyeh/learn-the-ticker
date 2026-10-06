"""Actual private PostgreSQL deletion, admission ordering and restored absence."""
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event as Signal, local

from sqlalchemy import event

from backend.app.backup import make_backup, preview_backup, restore_backup
from backend.app.contracts import ResearchRequest, RuntimeEvent
from backend.app.db import Database, Event
from backend.app.library_deletion import delete_saved_item, delete_retained_item
from tests.desktop.import_deletion_fixture import seed_imports, admission_orderings as document_admission_orderings
from tests.desktop.term_deletion_fixture import seed_terms, admission_orderings as term_admission_orderings
from backend.app.lifecycle import InstanceLock, PrivatePostgres
from backend.app.migrate import migrate
from scripts.smoke_library_scale import fingerprints
from tests.desktop.test_library_deletion import seed


def admission_orderings(db):
    role = local()
    for first in ("queue", "delete"):
        chat = db.create_conversation("TEST:SCALE:0000", "scale-0-0")
        request = ResearchRequest(query="Synthetic concurrent deletion", asset_id=chat["asset_id"], conversation_id=chat["id"])
        job_id = first + "-first-deletion"
        held, reached, release = Signal(), Signal(), Signal()

        def before(connection, cursor, statement, parameters, context, executemany):
            task = getattr(role, "name", None)
            if first == "queue" and task == "queue" and statement.startswith("INSERT INTO research_jobs"):
                held.set()
                assert release.wait(10), "Deletion did not reach the admission lock"
            if task != first and "FROM records" in statement and "FOR UPDATE" in statement:
                reached.set()

        def after(connection, cursor, statement, parameters, context, executemany):
            if first == "delete" and getattr(role, "name", None) == "delete" and "FROM records" in statement and "FOR UPDATE" in statement:
                held.set()
                assert release.wait(10), "Admission did not reach the deletion lock"

        def operation(name):
            role.name = name
            try:
                return db.queue_research(job_id, request) if name == "queue" else delete_saved_item(db, "conversation", chat["id"])
            except ValueError as exc:
                return str(exc)

        event.listen(db.engine, "before_cursor_execute", before)
        event.listen(db.engine, "after_cursor_execute", after)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(operation, first)
                try:
                    assert held.wait(10), "First operation did not obtain its lock"
                    b = pool.submit(operation, "delete" if first == "queue" else "queue")
                    assert reached.wait(10), "Second operation did not reach the same lock"
                finally:
                    release.set()
                first_result, second_result = a.result(timeout=15), b.result(timeout=15)
            if first == "queue":
                assert isinstance(first_result, ResearchRequest)
                assert second_result == "Wait for the active answer or cancel it before deleting this conversation"
                assert db.get("conversation:" + chat["id"]) and db.job(job_id)["status"] == "queued"
                db.transition(job_id, "cancelled")
                assert delete_saved_item(db, "conversation", chat["id"]).deleted
            else:
                assert first_result.deleted and second_result == "Conversation does not exist"
            assert db.get("conversation:" + chat["id"]) is None and db.job(job_id) is None
        finally:
            event.remove(db.engine, "before_cursor_execute", before)
            event.remove(db.engine, "after_cursor_execute", after)


def main():
    root = Path(__file__).resolve().parents[1] / ".local" / ("library-deletion-" + secrets.token_hex(6))
    binaries = Path(os.environ.get("LTT_PG_BIN", "C:/Program Files/PostgreSQL/17/bin"))
    roots = [root / name for name in ("source", "target")]
    locks, clusters, databases = [], [], []
    try:
        for directory in roots:
            directory.mkdir(parents=True)
            locks.append(InstanceLock(directory))
            cluster = PrivatePostgres(directory, binaries)
            clusters.append(cluster)
            cluster.start()
            db = Database(cluster.url())
            databases.append(db)
            migrate(db.engine)
        source, target = databases
        ids = seed(source)
        original_evidence = {key: value for key, value in fingerprints(source).items() if key.startswith(("asset:", "bundle:"))}
        chat = source.get("conversation:" + ids["conversation"])
        source.queue_research("deleted-question", ResearchRequest(query="Synthetic question", asset_id=chat["asset_id"], conversation_id=chat["id"]))
        with source.session.begin() as session:
            session.add(Event(job_id="deleted-question", payload=RuntimeEvent(run_id="deleted-question", kind="run.started").model_dump(mode="json")))
        try:
            delete_saved_item(source, "conversation", chat["id"])
        except ValueError as exc:
            assert "active answer" in str(exc)
        else:
            raise AssertionError("Active conversation was deleted")
        source.transition("deleted-question", "cancelled")
        before = fingerprints(source)
        class InjectedFailure(RuntimeError):
            pass
        def fail(connection, cursor, statement, parameters, context, executemany):
            if statement.startswith("DELETE FROM records"):
                raise InjectedFailure("Synthetic failure after event/job deletion")
        event.listen(source.engine, "before_cursor_execute", fail)
        try:
            try:
                delete_saved_item(source, "conversation", chat["id"])
            except InjectedFailure:
                pass
            else:
                raise AssertionError("Deletion rollback was not exercised")
        finally:
            event.remove(source.engine, "before_cursor_execute", fail)
        assert fingerprints(source) == before
        for kind, item_id in ids.items():
            assert delete_saved_item(source, kind, item_id).deleted
            assert not delete_saved_item(source, kind, item_id).deleted
        assert not source.job("deleted-question") and not source.events("deleted-question")
        admission_orderings(source)
        documents, explanations, document_jobs = seed_imports(source)
        document_admission_orderings(source, documents[0])
        for kind, item_id in (("import_explanation", explanations[0].id), ("import", documents[1].id)):
            before = fingerprints(source)
            event.listen(source.engine, "before_cursor_execute", fail)
            try:
                try:
                    delete_retained_item(source, kind, item_id)
                except InjectedFailure:
                    pass
                else:
                    raise AssertionError("Retained-item rollback was not exercised")
            finally:
                event.remove(source.engine, "before_cursor_execute", fail)
            assert fingerprints(source) == before
            assert delete_retained_item(source, kind, item_id).deleted
            assert not delete_retained_item(source, kind, item_id).deleted
        assert source.get("import:" + documents[0].id) == documents[0].model_dump(mode="json")
        assert source.get("import_explanation:" + explanations[1].id) == explanations[1].model_dump(mode="json")
        assert all(not source.job(job) and not source.events(job) for job in (document_jobs[0], *document_jobs[2:]))
        terms, term_jobs = seed_terms(source, "scale-0-0")
        before = fingerprints(source)
        event.listen(source.engine, "before_cursor_execute", fail)
        try:
            try:
                delete_saved_item(source, "term", terms[0].id)
            except InjectedFailure:
                pass
            else:
                raise AssertionError("Term deletion rollback was not exercised")
        finally:
            event.remove(source.engine, "before_cursor_execute", fail)
        assert fingerprints(source) == before
        term_admission_orderings(source, terms)
        assert all(not source.job(term_jobs[i]) and not source.events(term_jobs[i]) for i in (0, 2))
        assert all(source.get("term:" + terms[i].id) == terms[i].model_dump(mode="json") for i in (1, 3))
        assert {key: value for key, value in fingerprints(source).items() if key.startswith(("asset:", "bundle:"))} == original_evidence
        expected = fingerprints(source, restored_settings=True)
        archive = make_backup(source)
        summary = preview_backup(target, archive)
        assert summary.assets == 2 and summary.evidence_versions == 4
        assert summary.saved_reports == summary.conversations == summary.comparisons == summary.dated_reports == 0
        restore_backup(target, archive, summary.fingerprint)
        assert fingerprints(target) == expected
        target.engine.dispose()
        clusters[1].stop()
        clusters[1].start()
        restarted = Database(clusters[1].url())
        databases.append(restarted)
        assert fingerprints(restarted) == expected
        assert all(restarted.get(kind + ":" + item_id) is None for kind, item_id in ids.items())
        assert restarted.get("import:" + documents[1].id) is None and restarted.get("import_explanation:" + explanations[0].id) is None
        assert restarted.get("import:" + documents[0].id) == documents[0].model_dump(mode="json")
        assert all(restarted.get("term:" + terms[i].id) is None for i in (0, 2))
        assert all(restarted.get("term:" + terms[i].id) == terms[i].model_dump(mode="json") for i in (1, 3))
        print("Explicit saved-item/document/term/question deletion passed: active refusal, PostgreSQL admission orderings, late-failure rollback, unchanged unrelated originals/scopes, idempotence and deleted-item absence after real restore/restart.")
    finally:
        for db in databases:
            db.engine.dispose()
        for cluster in reversed(clusters):
            cluster.stop()
        for lock in locks:
            lock.close()
    assert all(not (directory / "database/data/postmaster.pid").exists() for directory in roots)


if __name__ == "__main__":
    main()
