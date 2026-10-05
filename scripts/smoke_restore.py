"""Restore a complete synthetic library between two private PostgreSQL clusters."""
import os
import json
import asyncio
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from sqlalchemy import event

from backend.app.backup import BackupError, preview_backup, restore_backup
from backend.app.contracts import AssetIdentity, Conversation, EvidenceBundle, IdentityVerification, RuntimeEvent, SavedResearch, Settings, TermExplanation, TermRequest, now, uid
from backend.app.identity import identity_hash
from backend.app.evidence_reuse import conversation_evidence
from backend.app.db import Database, Event, Job
from backend.app.lifecycle import InstanceLock, PrivatePostgres
from backend.app.migrate import migrate
from backend.app.terms import term_key
from tests.desktop.financial_fixture import publish_financial_snapshot, financial_ui_bundle
from tests.desktop.test_market_research import service as market_service
from backend.app.evidence import factual_context
from backend.app.source_operations import shareable_view
from backend.app.freshness import assess_freshness
from tests.desktop.source_review_fixture import backup_during_review, publish_review_snapshot
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
        async def publish_market():
            service, instrument, _, prompts = market_service(roots[0] / "synthetic-market", database=source)
            from backend.app.contracts import ResearchRequest
            try:
                job = await service.submit(ResearchRequest(query=instrument.asset.id))
                await service.tasks[job["id"]]
                result = source.job(job["id"])
                assert result["status"] == "completed"
                assert len(prompts) == 1 and "https://finance.yahoo.com/quote/SYN/" in prompts[0]
                return EvidenceBundle.model_validate(result["result"])
            finally:
                await service.close()
        market = asyncio.run(publish_market())
        market_payload = market.model_dump(mode="json")
        from tests.desktop.test_market_cloud import publish_numeric_followup
        from backend.app.evidence_reuse import validate_context_references
        cloud_original, cloud_answer = asyncio.run(publish_numeric_followup(source, roots[0] / "synthetic-cloud-learning"))
        reviewed_job = asyncio.run(publish_review_snapshot(source, roots[0] / "synthetic-source-review"))
        reviewed_ids = {row["id"] for row in source.list("bundle")}
        financial_job = asyncio.run(publish_financial_snapshot(source, roots[0] / "synthetic-research"))
        financial = EvidenceBundle.model_validate(financial_job["result"])
        sections = [row for row in source.list("bundle") if row["completion"] == "section_checkpoint" and row["id"] not in reviewed_ids]
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
        ratio_bundle = financial_ui_bundle()
        ratio_payload = ratio_bundle.model_dump(mode="json")
        source.put("bundle:" + ratio_bundle.id, "bundle", ratio_payload, ratio_bundle.asset.id)
        assert len([row for row in ratio_bundle.financials.ratios if row.percent == "100"]) == 2
        identity = AssetIdentity(id="TEST:RESTORE", symbol="RESTORE", name="Synthetic restored asset", asset_type="other")
        proof = IdentityVerification(authority="synthetic-restore", source_url="https://identity.example/restore",
                                     retrieved_at=now(), content_hash="a" * 64, identity_hash=identity_hash(identity))
        old, latest = EvidenceBundle(asset=identity), EvidenceBundle(asset=identity, level="intermediate", identity_verification=proof)
        for bundle in (old, latest):
            source.put("bundle:" + bundle.id, "bundle", bundle.model_dump(mode="json"), identity.id)
        source.put("asset:" + identity.id, "asset", latest.model_dump(mode="json"))
        saved = SavedResearch(bundle_id=old.id, title="Original saved version")
        source.put("saved:" + saved.id, "saved", saved.model_dump(mode="json"), identity.id)
        chat = Conversation(asset_id=identity.id, bookmarked=True, messages=[
            {"role": "assistant", "asset_id": identity.id, "bundle_id": old.id}])
        source.put("conversation:" + chat.id, "conversation", chat.model_dump(mode="json"))
        source.update_conversation(chat.id, asset_id=financial.asset.id)
        original_chat = Conversation.model_validate(source.update_conversation(chat.id, asset_id=identity.id)).model_dump(mode="json")
        assert [message["role"] for message in original_chat["messages"]] == ["assistant", "scope", "scope"]
        source.put("settings", "settings", Settings(cloud_enabled=True, experimental_yahoo_enabled=True, language="zh-TW", model="synthetic-selected-model").model_dump(mode="json"))
        term_request = TermRequest(term="liquidity", bundle_id=old.id)
        term = TermExplanation(id=term_key(term_request), term=term_request.term, bundle_id=old.id, asset_id=identity.id, language="en", level="beginner", provider="codex", basis="general", explanation="Synthetic general explanation for the restore scenario.")
        with source.session.begin() as session:
            session.add(Job(id="term-job", status="running", request=term_request.model_dump(mode="json")))
        source.complete_term("term-job", term.model_dump(mode="json"))
        question_request = TermRequest(mode="question", term="What does the retained valuation measure mean?", bundle_id=cloud_original.id)
        question = TermExplanation(id=term_key(question_request), mode="question", term=question_request.term,
            bundle_id=cloud_original.id, asset_id=cloud_original.asset.id, language="en", level="beginner", provider="codex",
            basis="snapshot", source_ids=[cloud_original.market.valuations.source_id],
            explanation="The retained trailing P/E is 29.5. It is a historical provider measure, not a forecast.")
        with source.session.begin() as session:
            session.add(Job(id="question-job", status="running", request=question_request.model_dump(mode="json")))
        source.complete_term("question-job", question.model_dump(mode="json"))
        estimate_request = TermRequest(mode="question", term="What does the retained EPS estimate mean?", bundle_id=market.id)
        estimate_question = TermExplanation(id=term_key(estimate_request), mode="question", term=estimate_request.term,
            bundle_id=market.id, asset_id=market.asset.id, language="en", level="beginner", provider="codex",
            basis="snapshot", source_ids=[market.market.estimates.source_id],
            explanation="The supplied EPS opinion averages 1.25000000000000001 USD/share. Its publication time is unknown.")
        with source.session.begin() as session:
            session.add(Job(id="estimate-question-job", status="running", request=estimate_request.model_dump(mode="json")))
        source.complete_term("estimate-question-job", estimate_question.model_dump(mode="json"))
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
        archive, pending_review_job, pending_review_id = asyncio.run(backup_during_review(source, roots[0] / "synthetic-pending-review"))
        original_jobs = {row["id"]: row for row in source.research_jobs()}
        assert original_jobs["pending"]["status"] == "running"
        assert import_job["id"] not in original_jobs and "term-job" not in original_jobs
        archive_path = roots[0] / "library.lttbackup"
        archive_path.write_bytes(archive)
        summary = preview_backup(target, archive)
        assert summary.can_restore and summary.assets == 2 and summary.evidence_versions == 16 and summary.saved_reports == 1 and summary.term_explanations == 3
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
        assert target.job(pending_review_job)["status"] == "interrupted" and target.job(pending_review_job)["result"] is None
        assert target.job(reviewed_job["id"])["result"] == reviewed_job["result"]
        assert not target.list("source_review") and pending_review_id not in str(target.events(pending_review_job))
        assert restored_jobs[financial_job["id"]] == original_jobs[financial_job["id"]]
        assert target.get("bundle:" + old.id) and target.get("asset:" + identity.id)["id"] == latest.id
        assert target.list("saved")[0]["bundle_id"] == old.id
        assert target.get("conversation:" + chat.id) == original_chat
        assert target.list("conversation")[0]["bookmarked"]
        assert target.get("term:" + term.id)["bundle_id"] == old.id and target.job("term-job")["result"]["id"] == term.id
        assert target.get("term:" + question.id) == question.model_dump(mode="json")
        assert target.job("pending")["status"] == "interrupted" and not target.get("settings")["cloud_enabled"]
        assert target.get("settings")["model"] == "synthetic-selected-model"
        assert not target.get("settings")["experimental_yahoo_enabled"]
        assert target.get("bundle:" + market.id) == market_payload
        assert target.get("bundle:" + ratio_bundle.id) == ratio_payload
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
        assert restarted.get("bundle:" + cloud_original.id) == cloud_original.model_dump(mode="json")
        assert restarted.get("bundle:" + cloud_answer.id) == cloud_answer.model_dump(mode="json")
        validate_context_references(cloud_answer, lambda bid: restarted.get("bundle:" + bid))
        assert not shareable_view(cloud_answer)[0].notes
        assert {row["id"]: row for row in restarted.research_jobs()} == restored_jobs
        assert restarted.job("progressive-pending")["result"] == progress.model_dump(mode="json")
        assert restarted.get("bundle:" + progress.id) == progress.model_dump(mode="json")
        assert restarted.job(pending_review_job)["status"] == "interrupted"
        assert restarted.job(reviewed_job["id"])["result"] == reviewed_job["result"]
        assert restarted.list("saved")[0]["bundle_id"] == old.id
        assert restarted.get("conversation:" + chat.id) == original_chat
        assert restarted.get("asset:" + identity.id)["id"] == latest.id
        assert restarted.get("asset:" + identity.id)["identity_verification"] == proof.model_dump(mode="json")
        assert restarted.get("asset:" + identity.id)["level"] == "intermediate"
        assert restarted.get("bundle:" + old.id)["identity_verification"] is None
        assert len(restarted.events("pending")) == 2
        assert restarted.get("term:" + term.id) == term.model_dump(mode="json")
        assert restarted.get("term:" + question.id) == question.model_dump(mode="json")
        assert restarted.job("question-job")["result"] == question.model_dump(mode="json")
        assert restarted.get("term:" + estimate_question.id) == estimate_question.model_dump(mode="json")
        assert restarted.job("estimate-question-job")["result"] == estimate_question.model_dump(mode="json")
        assert restarted.get("settings")["model"] == "synthetic-selected-model"
        assert not restarted.get("settings")["experimental_yahoo_enabled"]
        restored_market = EvidenceBundle.model_validate(restarted.get("bundle:" + market.id))
        restored_ratios = EvidenceBundle.model_validate(restarted.get("bundle:" + ratio_bundle.id))
        assert restored_ratios.model_dump(mode="json") == ratio_payload
        assert factual_context(restored_ratios) == factual_context(ratio_bundle)
        assert restored_market.model_dump(mode="json") == market_payload
        assert restored_market.market.bars[0].volume == "9007199254740993"
        assert restored_market.market.actions[0].value == "0.123456789012345678"
        assert restored_market.market.returns == market.market.returns
        assert restored_market.market.valuations == market.market.valuations
        assert len(restored_market.market.valuations.points) == 6
        assert any(p.value == "28.123456789012345678" for p in restored_market.market.valuations.points)
        assert restored_market.market.estimates == market.market.estimates
        assert restored_market.market.estimates.points[0].average == "1.25000000000000001"
        estimate_source = next(s for s in restored_market.sources if s.id == restored_market.market.estimates.source_id)
        assert estimate_source.as_of is estimate_source.published_at is None
        assert restored_market.market.returns[-1].price_percent == "27.272727"
        assert restored_market.market.returns[-1].total_return_estimate_percent == "40"
        assert restored_market.sources[-1] == market.sources[-1]
        age_at = now()
        assert assess_freshness(restored_market, at=age_at) == assess_freshness(market, at=age_at)
        assert restarted.get("bundle:" + market.id) == market_payload
        restored_context = factual_context(restored_market)
        assert "28.123456789012345678" in json.dumps(restored_context)
        assert restored_context["market"] and restored_context["financials"]["observations"]
        assert any(source["id"] == market.market.source_id for source in restored_context["sources"])
        exported, notice = shareable_view(restored_market)
        assert notice and exported.market is None and market.sources[-1] not in exported.sources
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
        print("Yahoo history, exact decimals/actions, cloud interpretations and original-version references survived restore/restart; shared numerical context, shareable export filtering and reset network opt-in passed.")
        print("Stored price/provider-adjusted return results, endpoint dates, original source references and missing-window reasons survived restore/restart.")
        print("Read-only source-age assessment preserved original restored dates and immutable private history without retrieval.")
        print("Stored SEC net-income/revenue percentages, exact input IDs, method, gaps and original source citations survived restore/restart.")
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
