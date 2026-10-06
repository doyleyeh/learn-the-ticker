"""Measure 1,000 synthetic assets and ~60 MiB attachments on private PostgreSQL.

Always creates fresh isolated clusters; accepts no existing library path or URL.
No provider access, performance threshold, production schema or archive-limit change.
"""
import asyncio
import hashlib
import json
import os
import platform
import secrets
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter

from sqlalchemy import event, func, select, text

from backend.app.backup import BackupError, make_backup, preview_backup, restore_backup
from backend.app.db import Database, Event, Job, Record
from backend.app.lifecycle import InstanceLock, PrivatePostgres
from backend.app.migrate import migrate
from backend.app.retained_imports import RetainedImport
from tests.desktop.library_scale_fixture import seed_assets, seed_attachments


@contextmanager
def measured(results, name):
    started = perf_counter()
    yield
    results[name] = round(perf_counter() - started, 4)
    print(json.dumps({"stage": name, "seconds": results[name]}), flush=True)


def fingerprints(db, *, restored_settings=False):
    """Compare every payload, relationship, event and timestamp across transfer."""
    result = {}
    with db.session() as session:
        for row in session.scalars(select(Record).order_by(Record.id).execution_options(yield_per=25)):
            payload = row.payload
            if row.kind == "settings" and restored_settings:
                payload = {**payload, "cloud_enabled": False, "experimental_yahoo_enabled": False, "start_at_login": False}
            data = [row.kind, row.parent_id, row.updated_at.isoformat(), payload]
            result[row.id] = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        for row in session.scalars(select(Job).order_by(Job.id).execution_options(yield_per=25)):
            data = [row.status, row.request, row.result, row.error, row.created_at.isoformat()]
            result["job:" + row.id] = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        for row in session.scalars(select(Event).order_by(Event.id).execution_options(yield_per=100)):
            data = [row.job_id, row.payload]
            result["event:" + str(row.id)] = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result


def table_counts(db):
    with db.session() as session:
        return [session.scalar(select(func.count()).select_from(model)) for model in (Record, Job, Event)]


def verify_attachments(db, expected):
    with db.session() as session:
        rows = session.scalars(select(Record).where(Record.kind == "import").execution_options(yield_per=1))
        actual = {}
        for row in rows:
            item = RetainedImport.model_validate(row.payload)
            content = item.content()
            actual[item.id] = (len(content), hashlib.sha256(content).hexdigest())
            assert not item.verified and "unverified_import" in item.document.limitations
        assert actual == expected


def main():
    workspace = Path(__file__).resolve().parents[1]
    root = workspace / ".local" / ("library-scale-" + secrets.token_hex(6))
    roots = [root / name for name in ("source", "target")]
    binaries = Path(os.environ.get("LTT_PG_BIN", "C:/Program Files/PostgreSQL/17/bin"))
    locks, clusters, databases = [], [], []
    timings = {}
    results = {"scenario": "synthetic-library-scale-v1", "assets": 1000,
        "platform": platform.system(), "machine": platform.machine(), "python": platform.python_version(),
        "seconds": timings, "provider_calls": 0, "performance_threshold": None}
    try:
        with measured(timings, "initialize_two_clusters"):
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
        with source.session() as session:
            results["postgresql"] = session.scalar(text("SHOW server_version"))
        with measured(timings, "publish_2000_cited_versions"):
            seed_assets(source)
        with measured(timings, "parse_and_retain_24_attachments"):
            attachments = asyncio.run(seed_attachments(source))
        results["attachment_bytes"] = sum(size for size, _ in attachments.values())
        assert 60 * 1024 * 1024 < results["attachment_bytes"] < 64 * 1024 * 1024
        results["table_counts"] = table_counts(source)
        assert results["table_counts"] == [3325, 2000, 2000]
        original = fingerprints(source)
        expected = fingerprints(source, restored_settings=True)
        with measured(timings, "list_1000_assets"):
            assets = source.list("asset")
            assert len(assets) == 1000
            results["asset_list_json_bytes"] = len(json.dumps(assets).encode())
        with measured(timings, "read_100_original_saved_pages"):
            saved = source.list("saved")
            assert len(saved) == 100
            for row in saved:
                bundle = source.get("bundle:" + row["bundle_id"])
                assert bundle["id"].endswith("-0")
                assert bundle["claims"][0]["source_ids"] == [bundle["sources"][0]["id"]]
                assert source.get("asset:" + bundle["asset"]["id"])["id"].endswith("-1")
        with measured(timings, "backup"):
            archive = make_backup(source)
        results["archive_bytes"] = len(archive)
        assert len(archive) > 60 * 1024 * 1024
        (root / "synthetic-library.lttbackup").write_bytes(archive)
        with measured(timings, "preview"):
            summary = preview_backup(target, archive)
            assert summary.can_restore and summary.format_version == "2"
            assert (summary.assets, summary.evidence_versions, summary.saved_reports, summary.conversations,
                summary.dated_reports, summary.retained_imports, summary.jobs) == (1000, 2000, 100, 100, 100, 24, 2000)
            assert summary.attachment_bytes == results["attachment_bytes"]
        class InjectedFailure(RuntimeError):
            pass
        def fail_event(*_):
            raise InjectedFailure("Synthetic failure after all records and jobs were staged")
        event.listen(Event, "before_insert", fail_event)
        try:
            with measured(timings, "failed_restore_rollback"):
                try:
                    restore_backup(target, archive, summary.fingerprint)
                except InjectedFailure:
                    pass
                else:
                    raise AssertionError("Restore failure injection did not run")
                assert table_counts(target) == [0, 0, 0]
        finally:
            event.remove(Event, "before_insert", fail_event)
        with measured(timings, "restore"):
            restore_backup(target, archive, summary.fingerprint)
        with measured(timings, "validate_all_restored_payloads"):
            assert fingerprints(target) == expected
            verify_attachments(target, attachments)
        with measured(timings, "reject_nonempty_target"):
            try:
                restore_backup(target, archive, summary.fingerprint)
            except BackupError as exc:
                assert "empty library" in str(exc)
            else:
                raise AssertionError("Nonempty library was replaced")
            assert fingerprints(target) == expected
        with measured(timings, "restart_and_validate_all_payloads"):
            target.engine.dispose()
            clusters[1].stop()
            clusters[1].start()
            restarted = Database(clusters[1].url())
            databases.append(restarted)
            migrate(restarted.engine)
            assert fingerprints(restarted) == expected
            verify_attachments(restarted, attachments)
            assert table_counts(restarted) == results["table_counts"]
            with restarted.session.begin() as session:
                session.add(Event(job_id="scale-job-0-0", payload={"sequence": 0, "run_id": "scale-job-0-0",
                    "kind": "run.completed", "timestamp": "2026-10-03T00:00:00Z", "text": "", "data": {}}))
            assert len(restarted.events("scale-job-0-0")) == 2
        assert fingerprints(source) == original
    finally:
        for db in databases:
            db.engine.dispose()
        for cluster in reversed(clusters):
            cluster.stop()
        for lock in locks:
            lock.close()
    assert all(not (directory / "database/data/postmaster.pid").exists() for directory in roots)
    results["owned_clusters_stopped"] = True
    results["status"] = "passed"
    (root / "baseline.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2), flush=True)
    print("Synthetic scale evidence: " + str(root / "baseline.json"), flush=True)


if __name__ == "__main__":
    main()
