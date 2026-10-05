from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from backend.app.contracts import AssetIdentity, EvidenceBundle
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
