import asyncio
import json

import pytest
from pydantic import ValidationError

from backend.app.backup import BackupError, make_backup, read_backup, restore_backup, preview_backup
from backend.app.contracts import TermRequest, TermExplanation
from backend.app.db import Database
from backend.app.terms import term_key, validate_explanation
from tests.desktop.test_backup import alter
from tests.desktop.test_terms import TermRuntime, completed, setup


def question(bundle, text="What does this saved page say about revenue?"):
    return TermRequest(mode="question", term=text, bundle_id=bundle.id)


def test_saved_question_never_retrieves_or_changes_evidence_and_reuses_offline(tmp_path):
    async def run():
        runtime = TermRuntime({"explanation": "The saved page reports revenue of 12 million USD.", "basis": "snapshot", "source_ids": ["s1"]})
        db, bundle, _, research, service = setup(tmp_path, runtime)
        def forbidden(*args, **kwargs):
            raise AssertionError("Saved-page learning must not retrieve or resolve")
        research.retrieve = research.verifier = forbidden
        request = question(bundle)
        result = await completed(service, request)
        assert result["status"] == "completed" and result["result"]["mode"] == "question"
        assert result["result"]["source_ids"] == ["s1"]
        assert not runtime.calls[0]["browsing"]
        assert "UNVERIFIED_PRIVATE_NOTE" not in runtime.calls[0]["prompt"]
        assert "SAVED-PAGE QUESTION" in runtime.calls[0]["prompt"]
        assert db.get("bundle:" + bundle.id) == bundle.model_dump(mode="json")
        assert db.get("asset:" + bundle.asset.id) == bundle.model_dump(mode="json")
        assert not db.research_jobs()
        db.put("settings", "settings", {"cloud_enabled": False, "provider": "claude"})
        assert (await service.submit(request))["result"] == result["result"]
        assert len(runtime.calls) == 1
        assert service.lookup(request.model_copy(update={"mode": "term"}))["status"] == "unavailable"
    asyncio.run(run())


@pytest.mark.parametrize("text", ["What is the latest revenue today?", "How did another company perform?", "Compute a new forecast from these figures."])
def test_absent_scope_remains_insufficient_without_research(tmp_path, text):
    async def run():
        runtime = TermRuntime({"explanation": "This saved page cannot support that request. Start new research for additional evidence.", "basis": "insufficient"})
        db, bundle, _, _, service = setup(tmp_path, runtime)
        result = await completed(service, question(bundle, text))
        assert result["status"] == "completed" and result["result"]["basis"] == "insufficient"
        assert result["result"]["source_ids"] == [] and not runtime.calls[0]["browsing"]
        assert len(db.list("bundle")) == 1
    asyncio.run(run())


@pytest.mark.parametrize("result", [
    {"explanation": "The user says revenue is 987654 USD.", "basis": "insufficient"},
    {"explanation": "Revenue is 987654 USD.", "basis": "general"},
    {"explanation": "An unsupported fact.", "basis": "snapshot", "source_ids": ["other-version"]},
    {"explanation": "No support exists.", "basis": "insufficient", "source_ids": ["s1"]},
])
def test_question_text_and_invalid_citations_cannot_establish_facts(tmp_path, result):
    async def run():
        db, bundle, _, _, service = setup(tmp_path, TermRuntime(result))
        job = await completed(service, question(bundle, "Is revenue 987654 USD?"))
        assert job["status"] == "failed" and not db.list("term")
    asyncio.run(run())


def test_tool_attempt_stops_question_without_fallback(tmp_path):
    async def run():
        db, bundle, runtime, _, service = setup(tmp_path, TermRuntime(tool=True))
        result = await completed(service, question(bundle))
        assert result["status"] == "failed" and not db.list("term")
        assert len(runtime.calls) == 1 and not runtime.calls[0]["browsing"]
    asyncio.run(run())


def test_question_limits_and_legacy_term_key():
    legacy = TermRequest(term="Revenue", bundle_id="old")
    import hashlib
    assert term_key(legacy) == hashlib.sha256(json.dumps(["old", "revenue", "en", "beginner"]).encode()).hexdigest()
    assert term_key(legacy.model_copy(update={"mode": "question"})) != term_key(legacy)
    text = "How does this saved page explain revenue and what original context should a beginner understand before interpreting it?"
    assert TermRequest(term=text, mode="question", bundle_id="old").term == text
    with pytest.raises(ValidationError): TermRequest(term=text, bundle_id="old")
    with pytest.raises(ValidationError): TermRequest(term="x" * 1001, mode="question", bundle_id="old")


def test_questions_restore_original_scope_and_are_not_automatically_refreshed(tmp_path):
    async def run():
        db, bundle, runtime, _, service = setup(tmp_path)
        result = await completed(service, question(bundle))
        assert await service.refresh(bundle.id, "another-version") == (0, 0)
        assert len(runtime.calls) == 1
        raw = make_backup(db)
        target = Database("sqlite://", testing=True)
        restore_backup(target, raw, preview_backup(target, raw).fingerprint)
        assert target.job(result["id"])["result"] == result["result"]
        assert target.list("term") == db.list("term")
        validate_explanation(TermExplanation.model_validate(target.list("term")[0]), bundle)
        def change_mode(value): value["jobs"][0]["request"]["mode"] = "term"
        with pytest.raises(BackupError): read_backup(alter(raw, change=change_mode))
    asyncio.run(run())


def test_legacy_term_archives_without_mode_remain_readable(tmp_path):
    async def run():
        db, bundle, _, _, service = setup(tmp_path)
        result = await completed(service, TermRequest(term="revenue", bundle_id=bundle.id))
        def legacy(value):
            for row in value["records"]:
                if row["kind"] == "term": row["payload"].pop("mode")
            for row in value["jobs"]:
                row["request"].pop("mode")
                row["result"].pop("mode")
        raw = alter(make_backup(db), change=legacy)
        target = Database("sqlite://", testing=True)
        restore_backup(target, raw, preview_backup(target, raw).fingerprint)
        assert TermExplanation.model_validate(target.job(result["id"])["result"]).model_dump(mode="json") == result["result"]
        assert target.list("term")[0] == result["result"]
    asyncio.run(run())


def test_live_question_helper_requires_explicit_opt_in(monkeypatch):
    from scripts import qualify_saved_questions
    def forbidden(*args): raise AssertionError("No profile/provider access without --live")
    monkeypatch.setattr(qualify_saved_questions, "resolve_profile", forbidden)
    assert asyncio.run(qualify_saved_questions.check()) == {"status": "not_requested", "generation_requested": False}


def test_live_helper_diagnostics_exclude_candidate_and_raw_errors(tmp_path):
    from scripts.qualify_saved_questions import candidate_diagnostic
    _, bundle, _, _, _ = setup(tmp_path)
    request = question(bundle)
    assert candidate_diagnostic("sensitive diagnostic", request, bundle) == "response_shape"
    assert candidate_diagnostic(json.dumps({"basis": "snapshot", "source_ids": ["s1"], "explanation": "Revenue is 987654 USD."}), request, bundle) == "unsupported_number"
