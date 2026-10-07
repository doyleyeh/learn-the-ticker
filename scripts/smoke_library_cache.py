"""Private PostgreSQL cache races, rollback and exact surviving-library restore."""
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event as Signal, local

from sqlalchemy import event

from backend.app.backup import make_backup, preview_backup, restore_backup
from backend.app.comparisons import build_comparison
from backend.app.contracts import AssetIdentity, EvidenceBundle, TermRequest
from backend.app.db import Database
from backend.app.library_cache import manage_cache
from backend.app.lifecycle import InstanceLock, PrivatePostgres
from backend.app.migrate import migrate
from scripts.smoke_library_scale import fingerprints
from tests.desktop.import_deletion_fixture import seed_imports
from tests.desktop.library_scale_fixture import seed_assets


def admission_orderings(db):
    role = local()
    for kind in ("bookmark", "term"):
        for first in ("admit", "evict"):
            asset = AssetIdentity(id=f"TEST:CACHE:{kind}:{first}", name="Synthetic cache race", symbol="CACHE", asset_type="other")
            bundle = EvidenceBundle(asset=asset)
            db.put("bundle:" + bundle.id, "bundle", bundle.model_dump(mode="json"), asset.id)
            db.put("asset:" + asset.id, "asset", bundle.model_dump(mode="json"))
            job_id = "cache-" + kind + "-" + first
            held, reached, release = Signal(), Signal(), Signal()

            def before(connection, cursor, statement, parameters, context, executemany):
                task = getattr(role, "name", None)
                if task != first and "pg_advisory_xact_lock" in statement:
                    reached.set()
                if first == "admit" and task == "admit" and statement.startswith("INSERT INTO"):
                    held.set()
                    assert release.wait(10), "Eviction did not reach the admission gate"

            def after(connection, cursor, statement, parameters, context, executemany):
                if first == "evict" and getattr(role, "name", None) == "evict" and "pg_advisory_xact_lock(" in statement:
                    held.set()
                    assert release.wait(10), "Admission did not reach the eviction gate"

            def operation(name):
                role.name = name
                try:
                    if name == "evict":
                        return manage_cache(db, evict=True, budget_bytes=0)
                    if kind == "bookmark":
                        return db.create_saved(bundle.id, "Synthetic race bookmark")
                    return db.queue_term(job_id, TermRequest(term="revenue", bundle_id=bundle.id))
                except ValueError as exc:
                    return str(exc)

            event.listen(db.engine, "before_cursor_execute", before)
            event.listen(db.engine, "after_cursor_execute", after)
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    a = pool.submit(operation, first)
                    try:
                        assert held.wait(10), "First operation did not hold its transaction gate"
                        b = pool.submit(operation, "evict" if first == "admit" else "admit")
                        assert reached.wait(10), "Second operation did not reach the transaction gate"
                    finally:
                        release.set()
                    one, two = a.result(timeout=20), b.result(timeout=20)
                if first == "admit":
                    assert db.get("bundle:" + bundle.id) == bundle.model_dump(mode="json")
                    if kind == "bookmark":
                        assert one["bundle_id"] == bundle.id and two.disposable_bytes == 0
                    else:
                        assert one is None and two.deferred_for_active_work and db.job(job_id)["status"] == "queued"
                        db.transition(job_id, "cancelled")
                else:
                    assert one.removed_items > 0 and isinstance(two, str)
                    assert ("snapshot not found" if kind == "bookmark" else "saved evidence") in two
                    assert not db.get("bundle:" + bundle.id) and not db.job(job_id)
            finally:
                event.remove(db.engine, "before_cursor_execute", before)
                event.remove(db.engine, "after_cursor_execute", after)
            make_backup(db)


def main():
    root = Path(__file__).resolve().parents[1] / ".local" / ("library-cache-" + secrets.token_hex(6))
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
        seed_assets(source, 3)
        documents, _, _ = seed_imports(source)
        comparison = build_comparison(*(EvidenceBundle.model_validate(source.get(f"bundle:scale-{i}-0")) for i in (0, 1)))
        source.put("comparison:" + comparison.id, "comparison", comparison.model_dump(mode="json"))
        before = fingerprints(source)
        summary = manage_cache(source, budget_bytes=0)
        assert summary.disposable_bytes > 0 and summary.protected_bytes > 0 and fingerprints(source) == before
        class InjectedFailure(RuntimeError):
            pass
        def fail(connection, cursor, statement, parameters, context, executemany):
            if statement.startswith("DELETE FROM records"):
                raise InjectedFailure("Synthetic late cache deletion failure")
        event.listen(source.engine, "before_cursor_execute", fail)
        try:
            try:
                manage_cache(source, evict=True, budget_bytes=0)
            except InjectedFailure:
                pass
            else:
                raise AssertionError("Cache rollback was not exercised")
        finally:
            event.remove(source.engine, "before_cursor_execute", fail)
        assert fingerprints(source) == before
        admission_orderings(source)
        summary = manage_cache(source, evict=True, budget_bytes=0)
        assert summary.disposable_bytes == 0
        assert source.get("comparison:" + comparison.id) == comparison.model_dump(mode="json")
        assert source.get("bundle:scale-0-0") and source.get("bundle:scale-0-1") and source.get("bundle:scale-1-0")
        assert not source.get("bundle:scale-2-0") and not source.get("asset:TEST:SCALE:0002")
        for document in documents:
            assert source.get("import:" + document.id) == document.model_dump(mode="json")
        expected = fingerprints(source, restored_settings=True)
        archive = make_backup(source)
        restore_backup(target, archive, preview_backup(target, archive).fingerprint)
        assert fingerprints(target) == expected
        target.engine.dispose()
        clusters[1].stop()
        clusters[1].start()
        restarted = Database(clusters[1].url())
        databases.append(restarted)
        assert fingerprints(restarted) == expected
        assert manage_cache(restarted, evict=True, budget_bytes=0).removed_items == 0
        print("Protected cache passed: real payload accounting, four PostgreSQL admission orderings, active deferral, late rollback, preserved saved/import/comparison references and actual restore/restart.")
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
