"""Conversation page selection is immutable, explicit and separate from fresh evidence."""
import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.backup import BackupError, make_backup, preview_backup, read_backup, restore_backup
from backend.app.contracts import Conversation, EvidenceBundle, ResearchRequest
from backend.app.db import Database
from backend.app.evidence_reuse import conversation_evidence
from tests.desktop.test_application import IDENTITY, TOKEN
from tests.desktop.test_backup import alter
from tests.desktop.test_evidence_reuse import save, snapshot


def library():
    db = Database("sqlite://", testing=True)
    old = snapshot("old-page")
    current = snapshot("current-page", "Synthetic Example Company now provides different services.")
    for bundle in (old, current):
        save(db, bundle)
    db.put("asset:" + IDENTITY.id, "asset", current.model_dump(mode="json"))
    return db, old, current


def test_api_uses_selected_page_and_old_clients_capture_current_once(tmp_path):
    db, old, current = library()
    app = create_app(db, TOKEN, tmp_path)
    with TestClient(app, headers={"Authorization": "Bearer " + TOKEN}) as client:
        selected = client.post("/api/conversations", json={"asset_id": IDENTITY.id, "context_bundle_id": old.id})
        assert selected.status_code == 201
        chat = selected.json()
        assert chat["context_bundle_id"] == old.id
        assert chat["messages"][0]["context_bundle_id"] == old.id
        default = client.post("/api/conversations", json={"asset_id": IDENTITY.id}).json()
        assert default["context_bundle_id"] == current.id
        invalid = client.post("/api/conversations", json={"asset_id": IDENTITY.id, "context_bundle_id": "absent"})
        assert invalid.status_code == 409
        result = client.put("/api/conversations/" + chat["id"], json={"context_bundle_id": current.id})
        assert result.status_code == 200 and result.json()["context_bundle_id"] == current.id
        assert result.json()["messages"][0]["context_bundle_id"] == old.id


@pytest.mark.parametrize("fault", ["missing", "foreign_asset", "changed_identity"])
def test_bad_selection_cannot_change_chat_or_start_a_run(fault):
    db, old, current = library()
    chat = db.create_conversation(IDENTITY.id, old.id)
    if fault == "missing":
        version = "absent"
    else:
        asset = IDENTITY.model_copy(update={"id": "OTHER"} if fault == "foreign_asset" else {"exchange": "OTHER"})
        wrong = EvidenceBundle(asset=asset)
        save(db, wrong)
        version = wrong.id
    with pytest.raises(ValueError, match="evidence"):
        db.update_conversation(chat["id"], context_bundle_id=version, bookmarked=True)
    assert db.get("conversation:" + chat["id"]) == chat
    with pytest.raises(ValueError, match="Select conversation evidence"):
        db.queue_research("wrong", ResearchRequest(query="Explain", asset_id=IDENTITY.id,
            conversation_id=chat["id"], context_bundle_id=version))
    assert db.job("wrong") is None


def test_refresh_does_not_rebind_and_explicit_change_waits_for_active_answer():
    db, old, current = library()
    chat = db.create_conversation(IDENTITY.id, old.id)
    newer = snapshot("newer-page")
    save(db, newer)
    db.put("asset:" + IDENTITY.id, "asset", newer.model_dump(mode="json"))
    request = db.queue_research("answer", ResearchRequest(query="Explain", asset_id=IDENTITY.id, conversation_id=chat["id"]))
    assert request.context_bundle_id == old.id
    for change in ({"context_bundle_id": newer.id}, {"asset_id": "OTHER"}):
        with pytest.raises(ValueError, match="active answer"):
            db.update_conversation(chat["id"], **change)
    assert db.update_conversation(chat["id"], bookmarked=True)["context_bundle_id"] == old.id
    db.transition("answer", "cancelled")
    updated = db.update_conversation(chat["id"], context_bundle_id=newer.id)
    assert [entry["context_bundle_id"] for entry in updated["messages"]] == [old.id, newer.id]
    assert db.job("answer")["request"]["context_bundle_id"] == old.id
    again = db.update_conversation(chat["id"], context_bundle_id=newer.id)
    assert again["messages"] == updated["messages"]


def test_legacy_chat_has_no_invented_original_page_and_can_select_one():
    db, old, current = library()
    legacy = Conversation(asset_id=IDENTITY.id, messages=[save(db, old)]).model_dump(mode="json")
    legacy.pop("context_bundle_id")
    legacy["messages"][0].pop("context_bundle_id", None)
    db.put("conversation:" + legacy["id"], "conversation", legacy)
    request = db.queue_research("legacy", ResearchRequest(query="Explain", asset_id=IDENTITY.id, conversation_id=legacy["id"]))
    assert request.context_bundle_id is None
    assert "context_bundle_id" not in db.get("conversation:" + legacy["id"])
    db.transition("legacy", "cancelled")
    selected = db.update_conversation(legacy["id"], context_bundle_id=current.id)
    assert selected["messages"][0]["bundle_id"] == old.id
    assert selected["context_bundle_id"] == current.id


def test_selected_context_survives_long_history_but_scope_changes_exclude_old_answers():
    db, old, current = library()
    answers = [save(db, snapshot("answer-" + str(index))) for index in range(22)]
    contexts, _ = conversation_evidence(db, IDENTITY, answers, context_bundle_id=old.id)
    assert contexts[0]["bundle_id"] == old.id and len(contexts) == 5
    boundary = {"role": "scope", "asset_id": IDENTITY.id, "text": "Selected page", "context_bundle_id": current.id}
    contexts, _ = conversation_evidence(db, IDENTITY, [*answers, boundary], context_bundle_id=current.id)
    assert [entry["bundle_id"] for entry in contexts] == [current.id]
    assert contexts[0]["sources"][0]["published_at"] == current.sources[0].published_at.isoformat()
    assert not contexts[0].get("notes")


@pytest.mark.parametrize("target", ["current", "scope_entry", "job"])
@pytest.mark.parametrize("version", ["absent", "foreign"])
def test_restore_rejects_broken_context_references(target, version):
    db, old, current = library()
    chat = db.create_conversation(IDENTITY.id, old.id)
    foreign = EvidenceBundle(id="foreign", asset=IDENTITY.model_copy(update={"id": "OTHER"}))
    save(db, foreign)
    db.queue_research("pending", ResearchRequest(query="Explain", asset_id=IDENTITY.id, conversation_id=chat["id"]))
    raw = make_backup(db)
    def tamper(data):
        if target == "job":
            data["jobs"][0]["request"]["context_bundle_id"] = version
        else:
            row = next(entry for entry in data["records"] if entry["kind"] == "conversation")["payload"]
            (row if target == "current" else row["messages"][0])["context_bundle_id"] = version
    with pytest.raises(BackupError, match="context"):
        read_backup(alter(raw, change=tamper))
    destination = Database("sqlite://", testing=True)
    restore_backup(destination, raw, preview_backup(destination, raw).fingerprint)
    assert destination.get("conversation:" + chat["id"]) == chat
    assert destination.job("pending")["request"]["context_bundle_id"] == old.id
    assert destination.job("pending")["status"] == "interrupted"
    assert destination.get("asset:" + IDENTITY.id)["id"] == current.id
