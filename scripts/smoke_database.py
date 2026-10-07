"""Private PostgreSQL transaction, persistence and supervisor recovery smoke; no providers."""
import os
import secrets
from pathlib import Path

from sqlalchemy import event

from backend.app.contracts import AssetIdentity, EvidenceBundle
from backend.app.db import Database, Event, Job
from backend.app.lifecycle import InstanceLock, PrivatePostgres
from backend.app.migrate import migrate


def main():
    root = Path(__file__).resolve().parents[1] / ".local" / ("database-smoke-" + secrets.token_hex(4))
    root.mkdir(parents=True)
    binaries = Path(os.environ.get("LTT_PG_BIN", "C:/Program Files/PostgreSQL/17/bin"))
    lock = InstanceLock(root)
    postgres = PrivatePostgres(root, binaries)
    database = None
    try:
        try:
            duplicate = InstanceLock(root)
        except RuntimeError:
            pass
        else:
            duplicate.close()
            raise AssertionError("Duplicate library lock was not rejected")
        postgres.start()
        database = Database(postgres.url())
        migrate(database.engine)
        bundle = EvidenceBundle(asset=AssetIdentity(id="TEST:ONLY", symbol="ONLY", name="Synthetic PostgreSQL test", asset_type="other")).model_dump(mode="json")
        with database.session.begin() as session:
            session.add(Job(id="atomic", request={"query": "Synthetic research"}, status="running"))

        def fail_event(*args):
            raise RuntimeError("Simulated interrupted commit")

        event.listen(Event, "before_insert", fail_event)
        try:
            try:
                database.complete_research("atomic", bundle)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Failure injection did not trigger")
        finally:
            event.remove(Event, "before_insert", fail_event)
        assert database.job("atomic")["status"] == "running" and not database.list("bundle")
        database.complete_research("atomic", bundle)
        database.engine.dispose()
        database = None

        # Simulate loss of the owning supervisor object while the private DB is alive.
        recovered = PrivatePostgres(root, binaries)
        recovered.start()
        assert recovered.port == postgres.port
        postgres.started = False
        postgres = recovered
        database = Database(postgres.url())
        assert database.job("atomic")["status"] == "completed"
        assert database.get("asset:TEST:ONLY")["id"] == bundle["id"]
        database.engine.dispose()
        database = None
        postgres.stop()
        postgres.start()
        database = Database(postgres.url())
        assert database.get("bundle:" + bundle["id"])["asset"]["id"] == "TEST:ONLY"
        from tests.desktop.retention_fixture import concurrent_retention
        retained = concurrent_retention(database)
        database.engine.dispose()
        database = None
        postgres.stop()
        postgres.start()
        database = Database(postgres.url())
        assert all(database.get(key) == value for key, value in retained.items())
        assert database.job("queue-first-retention-job")["status"] == "queued"
        assert database.get("conversation:expiry-first-retention") is None
        assert database.job("expiry-first-retention-job") is None
        from backend.app.backup import make_backup, read_backup
        read_backup(make_backup(database))  # No orphan references after either ordering/restart.
        print("Private PostgreSQL lock, atomic rollback/commit, supervisor recovery and restart persistence passed.")
        print("Concurrent conversation admission/expiry passed in both lock orderings; original saved evidence remained unchanged.")
    finally:
        if database:
            database.engine.dispose()
        postgres.stop()
        lock.close()
    assert not (root / "database/data/postmaster.pid").exists()


if __name__ == "__main__":
    main()
