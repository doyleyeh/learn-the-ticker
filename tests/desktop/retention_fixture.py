"""Actual PostgreSQL admission/expiry ordering; events coordinate threads, not sleeps."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Event as Signal, local

from sqlalchemy import event

from backend.app.contracts import AssetIdentity, Conversation, EvidenceBundle, ResearchRequest, SavedResearch, now


def concurrent_retention(db):
    asset = AssetIdentity(id="TEST:RETENTION", symbol="RETENTION", name="Synthetic retention test", asset_type="other")
    bundle = EvidenceBundle(asset=asset)
    original = bundle.model_dump(mode="json")
    db.put("bundle:" + bundle.id, "bundle", original, asset.id)
    db.put("asset:" + asset.id, "asset", original)
    saved = SavedResearch(bundle_id=bundle.id, title="Synthetic retention protected evidence")
    db.put("saved:" + saved.id, "saved", saved.model_dump(mode="json"), asset.id)
    at = now()
    old = at - timedelta(days=365)

    def conversation(identifier):
        item = Conversation(id=identifier, asset_id=asset.id, context_bundle_id=bundle.id,
            created_at=old, last_activity=old,
            messages=[{"role": "assistant", "asset_id": asset.id, "bundle_id": bundle.id}])
        db.put("conversation:" + item.id, "conversation", item.model_dump(mode="json"))
        return ResearchRequest(query="Explain the retained evidence", asset_id=asset.id,
            conversation_id=item.id, context_bundle_id=bundle.id)

    role = local()
    queue_held, expiry_reached, release_queue = Signal(), Signal(), Signal()
    request = conversation("queue-first-retention")

    def queue_first_hook(connection, cursor, statement, parameters, context, executemany):
        task = getattr(role, "name", None)
        if task == "queue" and statement.startswith("INSERT INTO research_jobs"):
            queue_held.set()  # Queue admission holds the conversation row lock.
            assert release_queue.wait(10), "Expiry did not reach the conversation lock"
        if task == "expiry" and "FROM records" in statement and "FOR UPDATE" in statement:
            expiry_reached.set()

    def queue(value, identifier):
        role.name = "queue"
        return db.queue_research(identifier, value)

    def expire():
        role.name = "expiry"
        return db.expire_conversations(180, at=at)

    event.listen(db.engine, "before_cursor_execute", queue_first_hook)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            admitted = pool.submit(queue, request, "queue-first-retention-job")
            try:
                assert queue_held.wait(10), "Queue admission did not obtain its lock"
                expired = pool.submit(expire)
                assert expiry_reached.wait(10), "Expiry did not run concurrently"
            finally:
                release_queue.set()
            admitted.result(timeout=15)
            assert expired.result(timeout=15) == 0, "Retention deleted a concurrently admitted conversation"
    finally:
        event.remove(db.engine, "before_cursor_execute", queue_first_hook)
    renewed = db.get("conversation:" + request.conversation_id)
    assert renewed and datetime.fromisoformat(renewed["last_activity"].replace("Z", "+00:00")) >= at
    assert db.job("queue-first-retention-job")["status"] == "queued"

    expiry_held, queue_reached, release_expiry = Signal(), Signal(), Signal()
    request = conversation("expiry-first-retention")

    def expiry_first_before(connection, cursor, statement, parameters, context, executemany):
        if getattr(role, "name", None) == "queue" and "FROM records" in statement and "FOR UPDATE" in statement:
            queue_reached.set()

    def expiry_first_after(connection, cursor, statement, parameters, context, executemany):
        if getattr(role, "name", None) == "expiry" and "FROM records" in statement and "FOR UPDATE" in statement:
            expiry_held.set()  # PostgreSQL executed FOR UPDATE; expiry owns the lock.
            assert release_expiry.wait(10), "Queue admission did not reach the expiry lock"

    event.listen(db.engine, "before_cursor_execute", expiry_first_before)
    event.listen(db.engine, "after_cursor_execute", expiry_first_after)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            expired = pool.submit(expire)
            try:
                assert expiry_held.wait(10), "Expiry did not obtain its lock"
                admitted = pool.submit(queue, request, "expiry-first-retention-job")
                assert queue_reached.wait(10), "Queue admission did not run concurrently"
            finally:
                release_expiry.set()
            assert expired.result(timeout=15) == 1
            try:
                admitted.result(timeout=15)
            except ValueError as exc:
                assert str(exc) == "Conversation does not exist"
            else:
                raise AssertionError("Admission succeeded after its conversation expired")
    finally:
        event.remove(db.engine, "before_cursor_execute", expiry_first_before)
        event.remove(db.engine, "after_cursor_execute", expiry_first_after)
    assert db.get("conversation:expiry-first-retention") is None
    assert db.job("expiry-first-retention-job") is None
    assert db.get("bundle:" + bundle.id) == original
    assert db.get("asset:" + asset.id) == original
    assert db.get("saved:" + saved.id) == saved.model_dump(mode="json")
    return {"conversation:queue-first-retention": renewed, "bundle:" + bundle.id: original,
        "asset:" + asset.id: original, "saved:" + saved.id: saved.model_dump(mode="json")}
