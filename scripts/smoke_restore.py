"""Restore a complete synthetic library between two private PostgreSQL clusters."""
import os
import asyncio
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from sqlalchemy import event

from backend.app.backup import BackupError, make_backup, preview_backup, restore_backup
from backend.app.contracts import AssetIdentity, Conversation, EvidenceBundle, IdentityVerification, RuntimeEvent, SavedResearch, Settings, TermExplanation, TermRequest, now, uid
from backend.app.identity import identity_hash
from backend.app.evidence_reuse import conversation_evidence
from backend.app.db import Database, Event, Job
from backend.app.lifecycle import InstanceLock, PrivatePostgres
from backend.app.migrate import migrate
from backend.app.terms import term_key
from tests.desktop.financial_fixture import publish_financial_snapshot
from tests.desktop.import_fixture import retain_synthetic_documents, explain_synthetic_document
from backend.app.import_previews import ImportPreview
from backend.app.retained_imports import RetainedImport, retain_import


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
        financial_job = asyncio.run(publish_financial_snapshot(source, roots[0] / "synthetic-research"))
        financial = EvidenceBundle.model_validate(financial_job["result"])
        sections = [row for row in source.list("bundle") if row["completion"] == "section_checkpoint"]
        assert len(sections) == 2
        progress = EvidenceBundle.model_validate({**sections[0], "id": uid()})
        with source.session.begin() as session:
            session.add(Job(id="progressive-pending", status="running", request={"query": "Synthetic unfinished research", "asset_id": progress.asset.id}))
        source.checkpoint_research("progressive-pending", progress)
        cited_chat = Conversation(asset_id=financial.asset.id, bookmarked=True, messages=[
            {"role": "assistant", "asset_id": financial.asset.id, "bundle_id": financial.id}])
        source.put("conversation:" + cited_chat.id, "conversation", cited_chat.model_dump(mode="json"))
        original_context, _ = conversation_evidence(source, financial.asset, cited_chat.model_dump(mode="json")["messages"])
        assert original_context and original_context[0]["claims"] and original_context[0]["sources"]
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
        imports = asyncio.run(retain_synthetic_documents(source))
        import_job = asyncio.run(explain_synthetic_document(source, imports[0], roots[0] / "synthetic-import-learning"))
        # The real PostgreSQL lock must serialize two final-slot admissions.
        import backend.app.retained_imports as retained_module
        original_limit = retained_module.MAX_ATTACHMENTS
        retained_module.MAX_ATTACHMENTS = len(imports) + 1
        barrier = Barrier(2)
        original = imports[0]
        preview = ImportPreview(state="unverified", origin="local_file", document=original.document, checked_at=original.checked_at)
        def retain_final_slot():
            barrier.wait(timeout=10)
            try:
                return retain_import(source, original.content(), preview, title="Synthetic concurrent document", storage_and_backup_confirmed=True)
            except ValueError as exc:
                if "capacity" not in str(exc):
                    raise
                return None
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                attempts = [pool.submit(retain_final_slot) for _ in range(2)]
                admitted = [result for attempt in attempts if (result := attempt.result(timeout=20)) is not None]
            assert len(admitted) == 1
            imports.extend(admitted)
        finally:
            retained_module.MAX_ATTACHMENTS = original_limit
        archive = make_backup(source)
        original_jobs = {row["id"]: row for row in source.research_jobs()}
        assert original_jobs["pending"]["status"] == "running"
        assert import_job["id"] not in original_jobs and "term-job" not in original_jobs
        archive_path = roots[0] / "library.lttbackup"
        archive_path.write_bytes(archive)
        summary = preview_backup(target, archive)
        assert summary.can_restore and summary.assets == 2 and summary.evidence_versions == 6 and summary.saved_reports == 1 and summary.term_explanations == 1
        assert summary.format_version == "2" and summary.retained_imports == 5 and summary.attachment_bytes == sum(item.byte_count for item in imports)
        assert summary.import_explanations == 1

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
        assert not target.list("import")
        assert not target.list("import_explanation")
        restore_backup(target, archive, summary.fingerprint)
        restored_jobs = {row["id"]: row for row in target.research_jobs()}
        assert restored_jobs["pending"]["status"] == "interrupted"
        assert restored_jobs["pending"]["request"] == original_jobs["pending"]["request"]
        assert target.job("progressive-pending")["status"] == "interrupted"
        assert target.job("progressive-pending")["result"] == progress.model_dump(mode="json")
        assert restored_jobs[financial_job["id"]] == original_jobs[financial_job["id"]]
        assert target.get("bundle:" + old.id) and target.get("asset:" + identity.id)["id"] == latest.id
        assert target.list("saved")[0]["bundle_id"] == old.id
        assert target.list("conversation")[0]["bookmarked"]
        assert target.list("term")[0]["bundle_id"] == old.id and target.job("term-job")["result"]["id"] == term.id
        assert target.job("pending")["status"] == "interrupted" and not target.get("settings")["cloud_enabled"]
        assert target.get("settings")["model"] == "synthetic-selected-model"
        assert target.get("bundle:" + financial.id) == financial.model_dump(mode="json")
        assert target.job(financial_job["id"])["result"] == financial.model_dump(mode="json")
        assert target.job(import_job["id"])["result"] == import_job["result"]
        assert target.get("import_explanation:" + import_job["result"]["id"]) == import_job["result"]
        restored_context, _ = conversation_evidence(target, financial.asset, target.get("conversation:" + cited_chat.id)["messages"])
        assert restored_context == original_context
        for document in imports:
            assert RetainedImport.model_validate(target.get("import:" + document.id)) == document
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
        assert {row["id"]: row for row in restarted.research_jobs()} == restored_jobs
        assert restarted.job("progressive-pending")["result"] == progress.model_dump(mode="json")
        assert restarted.get("bundle:" + progress.id) == progress.model_dump(mode="json")
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
        assert restarted.job(financial_job["id"])["result"] == financial.model_dump(mode="json")
        assert restarted.job(import_job["id"])["result"] == import_job["result"]
        assert restarted.get("import_explanation:" + import_job["result"]["id"]) == import_job["result"]
        async def reopen_import_explanation():
            from backend.app.import_learning import ImportLearningRequest
            from backend.app.import_learning_service import ImportLearning
            from backend.app.import_previews import ImportPreviews
            from backend.app.import_storage import ImportStorage
            from backend.app.research import ResearchService
            offline = ResearchService(restarted, {}, roots[1] / "offline-import-learning")
            learning = ImportLearning(offline, ImportStorage(ImportPreviews(offline)))
            try:
                cached = await learning.lookup(ImportLearningRequest.model_validate(import_job["request"]))
                assert cached["status"] == "cached" and cached["result"] == import_job["result"]
                assert not offline.tasks
            finally:
                await offline.close()
        asyncio.run(reopen_import_explanation())
        restarted_context, _ = conversation_evidence(restarted, financial.asset, restarted.get("conversation:" + cited_chat.id)["messages"])
        assert restarted_context == original_context
        for document in imports:
            restored = RetainedImport.model_validate(restarted.get("import:" + document.id))
            assert restored == document and restored.content() == document.content() and not restored.verified
        print("PostgreSQL full-library restore, rollback on failure, preserved saved versions, event sequence and restart passed.")
        print("Typed issuer observations, exact decimals, separate identity proofs and conflict/revision references survived actual restore and restart.")
        print("Financial snapshot originated through production research orchestration with explicit synthetic source/runtime adapters.")
        print("Original conversation facts, version-specific citations, source URLs and dates remain reusable after restore and restart.")
        print("Five retained documents across four formats preserved exact bytes, checksums, locators, original provenance and permission through atomic restore and restart; concurrent capacity enforcement passed.")
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
