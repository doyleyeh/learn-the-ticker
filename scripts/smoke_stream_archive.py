"""Actual private PostgreSQL restore above both legacy archive size ceilings.

Fresh synthetic clusters only. No account, inference, retrieval or user library.
"""
import base64
import json
import os
import random
import secrets
import tracemalloc
from contextlib import ExitStack, contextmanager
from pathlib import Path

from sqlalchemy import event, text

from backend.app.backup import BackupError, MAX_ARCHIVE_BYTES, MAX_CONTENT_BYTES
from backend.app.backup_stream import create_backup_file, preview_backup_file, read_backup_file, restore_backup_file
from backend.app.contracts import ResearchRequest, Settings
from backend.app.db import Database, Event, Job
from backend.app.lifecycle import InstanceLock, PrivatePostgres
from backend.app.migrate import migrate
from scripts.smoke_library_scale import fingerprints, measured, table_counts
from tests.desktop.test_backup import seed
from tests.desktop.test_retained_imports import retained


@contextmanager
def allocated(results, name):
    tracemalloc.start()
    try:
        with measured(results["seconds"], name):
            yield
        results["python_peak_bytes"][name] = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def main():
    root = Path(__file__).resolve().parents[1] / ".local" / ("stream-archive-" + secrets.token_hex(6))
    binaries = Path(os.environ.get("LTT_PG_BIN", "C:/Program Files/PostgreSQL/17/bin"))
    locks, clusters, databases = [], [], []
    results = {"scenario": "synthetic-stream-archive-v1", "provider_calls": 0, "seconds": {}, "python_peak_bytes": {}}
    try:
        for name in ("source", "target"):
            directory = root / name
            directory.mkdir(parents=True)
            locks.append(InstanceLock(directory))
            cluster = PrivatePostgres(directory, binaries)
            clusters.append(cluster)
            cluster.start()
            db = Database(cluster.url())
            databases.append(db)
            migrate(db.engine)
        source, target = databases
        with source.session() as session:
            results["postgresql"] = session.scalar(text("SHOW server_version"))
        seed(source)
        document = retained(source)
        rng = random.Random(61006)
        request = ResearchRequest(query="Synthetic archive volume; not financial evidence").model_dump(mode="json")
        with measured(results["seconds"], "seed_30000_large_synthetic_jobs"):
            for batch in range(300):
                with source.session.begin() as session:
                    for position in range(100):
                        index = batch * 100 + position
                        content = base64.b64encode(rng.randbytes(7500)).decode("ascii")
                        session.add(Job(id=f"volume-{index:05}", status="completed", request=request,
                            result={"educational_redirect": content}))
        # This scenario measures archive volume, not 30,000 generated answers.
        original = fingerprints(source)
        target.put("settings", "settings", Settings(language="en").model_dump(mode="json"))
        target_before = fingerprints(target)
        with ExitStack() as archive_stack:
            with allocated(results, "backup_large_archive"):
                path = archive_stack.enter_context(create_backup_file(source))
            results["archive_bytes"] = path.stat().st_size
            assert results["archive_bytes"] > MAX_ARCHIVE_BYTES
            with allocated(results, "validate_large_archive"):
                with read_backup_file(path) as (manifest, index, fingerprint):
                    results["content_bytes"] = sum(entry.byte_count for entry in manifest.tables.values())
                    assert results["content_bytes"] > MAX_CONTENT_BYTES
                    assert [len(index.records), len(index.jobs), len(index.events)] == table_counts(source)
            summary = preview_backup_file(target, path)
            assert summary.can_restore and summary.format_version == "3" and summary.retained_imports == 1
            assert summary.fingerprint == fingerprint
            def fail(*args):
                raise RuntimeError("Synthetic failure after all archive records/jobs")
            event.listen(Event, "before_insert", fail)
            try:
                with measured(results["seconds"], "late_failure_rollback"):
                    try:
                        restore_backup_file(target, path, fingerprint)
                    except RuntimeError as exc:
                        assert str(exc).startswith("Synthetic failure")
                    else:
                        raise AssertionError("Failure injection did not run")
                assert fingerprints(target) == target_before
            finally:
                event.remove(Event, "before_insert", fail)
            with allocated(results, "restore_large_archive"):
                restore_backup_file(target, path, fingerprint)
            expected = fingerprints(source, restored_settings=True)
            # The single pending job is explicitly interrupted during restore.
            pending = target.job("pending")
            assert pending["status"] == "interrupted"
            actual = fingerprints(target)
            assert {key: value for key, value in actual.items() if key != "job:pending"} == {key: value for key, value in expected.items() if key != "job:pending"}
            assert target.get("import:" + document.id) == document.model_dump(mode="json")
            try:
                restore_backup_file(target, path, fingerprint)
            except BackupError as exc:
                assert "empty library" in str(exc)
            else:
                raise AssertionError("Nonempty target was overwritten")
            assert fingerprints(target) == actual
            results["archive_fingerprint"] = fingerprint
        assert not path.exists()
        with measured(results["seconds"], "restart_and_compare_every_row"):
            target.engine.dispose()
            clusters[1].stop()
            clusters[1].start()
            restarted = Database(clusters[1].url())
            databases.append(restarted)
            migrate(restarted.engine)
            assert fingerprints(restarted) == actual
            with restarted.session.begin() as session:
                session.add(Event(job_id="pending", payload={"sequence": 0, "run_id": "pending", "kind": "run.completed",
                    "timestamp": "2026-10-06T00:00:00Z", "text": "", "data": {}}))
            assert len(restarted.events("pending")) == 2
        assert fingerprints(source) == original
        results["table_counts"] = table_counts(source)
    finally:
        for db in databases:
            db.engine.dispose()
        for cluster in reversed(clusters):
            cluster.stop()
        for lock in locks:
            lock.close()
    assert all(not (root / name / "database/data/postmaster.pid").exists() for name in ("source", "target"))
    results.update(status="passed", owned_clusters_stopped=True)
    (root / "baseline.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2), flush=True)
    print("Stream archive evidence: " + str(root / "baseline.json"), flush=True)


if __name__ == "__main__":
    main()
