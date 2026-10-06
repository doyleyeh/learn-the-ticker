from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from backend.app.contracts import AssetIdentity, Conversation, EvidenceBundle, ResearchRequest
from backend.app.db import Database, Event, Job


def snapshot(identity="TEST:ONE"):
    return EvidenceBundle(asset=AssetIdentity(id=identity, symbol="ONE", name="Synthetic One", asset_type="stock")).model_dump(mode="json")


def test_publish_rolls_back_all_references_when_commit_fails():
    db = Database("sqlite://", testing=True)
    bundle = snapshot()
    with db.session.begin() as session:
        session.add(Job(id="atomic", status="running", request={"query": "Explain ONE"}))

    def unavailable_event_storage(*args):
        raise RuntimeError("Simulated write failure")

    event.listen(Event, "before_insert", unavailable_event_storage)
    try:
        with pytest.raises(RuntimeError, match="Simulated"):
            db.complete_research("atomic", bundle)
    finally:
        event.remove(Event, "before_insert", unavailable_event_storage)
    assert db.job("atomic")["status"] == "running"
    assert not db.list("bundle") and not db.list("asset") and not db.events("atomic")
    db.complete_research("atomic", bundle)
    assert db.job("atomic")["status"] == "completed"
    assert db.get("asset:TEST:ONE")["id"] == bundle["id"]
    with pytest.raises(ValueError, match="immutable"):
        db.put("bundle:" + bundle["id"], "bundle", {**bundle, "language": "zh-TW"})
    assert db.get("bundle:" + bundle["id"])["language"] == "en"


def test_followup_preserves_asset_page_and_records_scoped_citations():
    db = Database("sqlite://", testing=True)
    original, answer = snapshot(), snapshot()
    db.put("asset:TEST:ONE", "asset", original)
    db.put("conversation:chat", "conversation", {"id": "chat", "asset_id": "TEST:ONE", "messages": [], "bookmarked": False, "created_at": datetime.now(timezone.utc).isoformat()})
    with db.session.begin() as session:
        session.add(Job(id="question", status="running", request={"query": "What is a share?", "conversation_id": "chat"}))
    with pytest.raises(ValueError, match="active answer"):
        db.update_conversation("chat", asset_id="TEST:TWO")
    db.complete_research("question", answer, conversation_id="chat")
    assert db.get("asset:TEST:ONE")["id"] == original["id"]
    messages = db.get("conversation:chat")["messages"]
    assert messages[-1]["bundle_id"] == answer["id"] and messages[-1]["asset_id"] == "TEST:ONE"
    with pytest.raises(ValueError, match="Resolve"):
        db.update_conversation("chat", asset_id="TEST:MISSING")
    second = snapshot("TEST:TWO")
    db.put("bundle:" + second["id"], "bundle", second)
    db.put("asset:TEST:TWO", "asset", second)
    changed = db.update_conversation("chat", asset_id="TEST:TWO", bookmarked=True)
    assert changed["messages"][-1]["role"] == "scope"
    assert changed["messages"][1]["asset_id"] == "TEST:ONE"
    assert changed["asset_id"] == "TEST:TWO" and changed["bookmarked"]


def test_idle_expiry_removes_transcripts_and_requests_but_keeps_saved_evidence():
    db = Database("sqlite://", testing=True)
    at = datetime.now(timezone.utc)
    bundle = snapshot()
    db.put("bundle:" + bundle["id"], "bundle", bundle)
    db.put("saved:report", "saved", {"id": "report", "bundle_id": bundle["id"]})
    for name, age, bookmarked in [("expired", 181, False), ("recent", 179, False), ("bookmarked", 365, True), ("active", 365, False)]:
        db.put("conversation:" + name, "conversation", {"id": name, "asset_id": "TEST:ONE", "created_at": (at - timedelta(days=age)).isoformat(), "messages": [], "bookmarked": bookmarked})
        with db.session.begin() as session:
            session.add(Job(id=name, request={"query": "Private question", "conversation_id": name}, status="running" if name == "active" else "completed"))
        with db.session.begin() as session:
            session.add(Event(job_id=name, payload={"text": "progress"}))
    assert db.expire_conversations(180, at=at) == 1
    assert not db.get("conversation:expired") and not db.job("expired") and not db.events("expired")
    assert {chat["id"] for chat in db.list("conversation")} == {"recent", "bookmarked", "active"}
    assert db.get("bundle:" + bundle["id"]) and db.get("saved:report")


def idle_conversation(db):
    bundle = snapshot()
    db.put("bundle:" + bundle["id"], "bundle", bundle, bundle["asset"]["id"])
    db.put("asset:" + bundle["asset"]["id"], "asset", bundle)
    old = datetime.now(timezone.utc) - timedelta(days=365)
    chat = Conversation(id="idle", asset_id=bundle["asset"]["id"], context_bundle_id=bundle["id"],
        created_at=old, last_activity=old).model_dump(mode="json")
    db.put("conversation:idle", "conversation", chat)
    request = ResearchRequest(query="Explain the original evidence", asset_id=chat["asset_id"],
        context_bundle_id=bundle["id"], conversation_id="idle")
    return chat, bundle, request


@pytest.mark.parametrize("terminal", ["failed", "cancelled", "interrupted"])
def test_admitted_question_renews_retention_even_without_a_successful_answer(terminal):
    db = Database("sqlite://", testing=True)
    original, bundle, request = idle_conversation(db)
    before = datetime.now(timezone.utc)
    db.queue_research("renewed", request)
    changed = db.get("conversation:idle")
    renewed = datetime.fromisoformat(changed["last_activity"].replace("Z", "+00:00"))
    assert before <= renewed <= datetime.now(timezone.utc)
    assert {**changed, "last_activity": original["last_activity"]} == original
    db.transition("renewed", terminal)
    assert db.expire_conversations(180, at=renewed + timedelta(days=180)) == 0
    assert db.expire_conversations(180, at=renewed + timedelta(days=180, microseconds=1)) == 1
    assert db.get("bundle:" + bundle["id"]) == bundle
    assert db.get("asset:" + bundle["asset"]["id"]) == bundle
    assert db.job("renewed") is None


def test_failed_job_admission_rolls_back_idle_renewal():
    db = Database("sqlite://", testing=True)
    original, _, request = idle_conversation(db)
    def fail(*_):
        raise RuntimeError("Synthetic admission failure")
    event.listen(Job, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="Synthetic admission"):
            db.queue_research("failed-admission", request)
    finally:
        event.remove(Job, "before_insert", fail)
    assert db.get("conversation:idle") == original
    assert db.job("failed-admission") is None


def test_failed_expiry_rolls_back_events_jobs_and_conversation():
    db = Database("sqlite://", testing=True)
    original, bundle, _ = idle_conversation(db)
    with db.session.begin() as session:
        session.add(Job(id="old-answer", status="failed", request={"query": "Synthetic old question", "conversation_id": "idle"}))
        session.flush()
        session.add(Event(job_id="old-answer", payload={"kind": "run.failed", "text": "Synthetic failure"}))
    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("DELETE FROM research_jobs"):
            raise RuntimeError("Synthetic retention failure")
    event.listen(db.engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Synthetic retention"):
            db.expire_conversations(180)
    finally:
        event.remove(db.engine, "before_cursor_execute", fail)
    assert db.get("conversation:idle") == original
    assert db.job("old-answer")["status"] == "failed"
    assert len(db.events("old-answer")) == 1
    assert db.get("bundle:" + bundle["id"]) == bundle
