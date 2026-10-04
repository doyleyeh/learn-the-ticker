"""Restore a complete synthetic library between two private PostgreSQL clusters."""
import os
import secrets
from pathlib import Path

from sqlalchemy import event

from backend.app.backup import BackupError, make_backup, preview_backup, restore_backup
from backend.app.contracts import AssetIdentity, Conversation, EvidenceBundle, IdentityVerification, RuntimeEvent, SavedResearch, Settings, TermExplanation, TermRequest, now
from backend.app.identity import identity_hash
from backend.app.db import Database, Event, Job
from backend.app.lifecycle import InstanceLock, PrivatePostgres
from backend.app.migrate import migrate
from backend.app.terms import term_key
from tests.desktop.financial_fixture import financial_bundle


def main():
    workspace = Path(__file__).resolve().parents[1]
    run = secrets.token_hex(4)
    binaries = Path(os.environ.get("LTT_PG_BIN", "C:/Program Files/PostgreSQL/17/bin"))
    roots = [workspace / ".local" / f"restore-{run}-{name}" for name in ("source", "target")]
    locks, clusters, databases = [], [], []
    try:
        for root in roots:
            root.mkdir(parents=True)
            locks.append(InstanceLock(root))
            cluster = PrivatePostgres(root, binaries)
            clusters.append(cluster)
            cluster.start()
            db = Database(cluster.url())
            databases.append(db)
            migrate(db.engine)
        source, target = databases
        financial = financial_bundle(conflict=True)
        with source.session.begin() as session:
            session.add(Job(id="financial", status="running", request={"query": "Synthetic issuer"}))
        source.complete_research("financial", financial.model_dump(mode="json"))
        identity = AssetIdentity(id="TEST:RESTORE", symbol="RESTORE", name="Synthetic restored asset", asset_type="other")
        proof = IdentityVerification(authority="synthetic-restore", source_url="https://identity.example/restore",
                                     retrieved_at=now(), content_hash="a" * 64, identity_hash=identity_hash(identity))
        old, latest = EvidenceBundle(asset=identity), EvidenceBundle(asset=identity, level="intermediate", identity_verification=proof)
        for bundle in (old, latest):
            source.put("bundle:" + bundle.id, "bundle", bundle.model_dump(mode="json"), identity.id)
        source.put("asset:" + identity.id, "asset", latest.model_dump(mode="json"))
        saved = SavedResearch(bundle_id=old.id, title="Original saved version")
        source.put("saved:" + saved.id, "saved", saved.model_dump(mode="json"), identity.id)
        chat = Conversation(asset_id=identity.id, bookmarked=True)
        source.put("conversation:" + chat.id, "conversation", chat.model_dump(mode="json"))
        source.put("settings", "settings", Settings(cloud_enabled=True, language="zh-TW", model="synthetic-selected-model").model_dump(mode="json"))
        term_request = TermRequest(term="liquidity", bundle_id=old.id)
        term = TermExplanation(id=term_key(term_request), term=term_request.term, bundle_id=old.id, asset_id=identity.id, language="en", level="beginner", provider="codex", basis="general", explanation="Synthetic general explanation for the restore scenario.")
        with source.session.begin() as session:
            session.add(Job(id="term-job", status="running", request=term_request.model_dump(mode="json")))
        source.complete_term("term-job", term.model_dump(mode="json"))
        with source.session.begin() as session:
            session.add(Job(id="pending", status="running", request={"query": "Synthetic pending turn", "conversation_id": chat.id, "asset_id": identity.id}))
        with source.session.begin() as session:
            session.add(Event(job_id="pending", payload=RuntimeEvent(run_id="pending", kind="run.started").model_dump(mode="json")))
        archive = make_backup(source)
        archive_path = roots[0] / "library.lttbackup"
        archive_path.write_bytes(archive)
        summary = preview_backup(target, archive)
        assert summary.can_restore and summary.assets == 2 and summary.evidence_versions == 3 and summary.saved_reports == 1 and summary.term_explanations == 1

        def fail_event(*args):
            raise RuntimeError("Simulated restored-event write failure")

        event.listen(Event, "before_insert", fail_event)
        try:
            try:
                restore_backup(target, archive, summary.fingerprint)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Failure injection did not trigger")
        finally:
            event.remove(Event, "before_insert", fail_event)
        assert not target.list("asset") and not target.list("settings") and not target.job("pending")
        restore_backup(target, archive, summary.fingerprint)
        assert target.get("bundle:" + old.id) and target.get("asset:" + identity.id)["id"] == latest.id
        assert target.list("saved")[0]["bundle_id"] == old.id
        assert target.list("conversation")[0]["bookmarked"]
        assert target.list("term")[0]["bundle_id"] == old.id and target.job("term-job")["result"]["id"] == term.id
        assert target.job("pending")["status"] == "interrupted" and not target.get("settings")["cloud_enabled"]
        assert target.get("settings")["model"] == "synthetic-selected-model"
        assert target.get("bundle:" + financial.id) == financial.model_dump(mode="json")
        assert target.job("financial")["result"] == financial.model_dump(mode="json")
        with target.session.begin() as session:
            session.add(Event(job_id="pending", payload=RuntimeEvent(run_id="pending", kind="run.cancelled").model_dump(mode="json")))
        assert len(target.events("pending")) == 2
        try:
            restore_backup(target, archive, summary.fingerprint)
        except BackupError:
            pass
        else:
            raise AssertionError("Restore overwrote a non-empty library")
        target.engine.dispose()
        clusters[1].stop()
        clusters[1].start()
        restarted = Database(clusters[1].url())
        databases.append(restarted)
        assert restarted.list("saved")[0]["bundle_id"] == old.id
        assert restarted.get("asset:" + identity.id)["id"] == latest.id
        assert restarted.get("asset:" + identity.id)["identity_verification"] == proof.model_dump(mode="json")
        assert restarted.get("asset:" + identity.id)["level"] == "intermediate"
        assert restarted.get("bundle:" + old.id)["identity_verification"] is None
        assert len(restarted.events("pending")) == 2
        assert restarted.get("term:" + term.id) == term.model_dump(mode="json")
        assert restarted.get("settings")["model"] == "synthetic-selected-model"
        assert restarted.get("asset:" + financial.asset.id) == financial.model_dump(mode="json")
        assert restarted.get("bundle:" + financial.id)["financials"]["observations"][0]["value"] == "9007199254740993"
        assert restarted.job("financial")["result"] == financial.model_dump(mode="json")
        print("PostgreSQL full-library restore, rollback on failure, preserved saved versions, event sequence and restart passed.")
        print("Typed issuer observations, exact decimals, separate identity proofs and conflict/revision references survived actual restore and restart.")
        print("Non-empty restore was rejected; cloud consent reset and no provider calls were made.")
    finally:
        for db in databases:
            db.engine.dispose()
        for cluster in reversed(clusters):
            cluster.stop()
        for lock in locks:
            lock.close()
    assert all(not (root / "database/data/postmaster.pid").exists() for root in roots)


if __name__ == "__main__":
    main()
