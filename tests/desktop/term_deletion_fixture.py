"""Synthetic term/question scopes for explicit deletion and restore checks."""
from backend.app.contracts import EvidenceBundle, RuntimeEvent, TermExplanation, TermRequest
from backend.app.db import Event
from backend.app.terms import term_key, validate_explanation


def seed_terms(db, bundle_id, term="Revenue"):
    bundle = EvidenceBundle.model_validate(db.get("bundle:" + bundle_id))
    values, jobs = [], []
    for index, (term, mode, language, level) in enumerate((
            (term, "term", "en", "beginner"), (term, "term", "zh-TW", "beginner"),
            (term, "question", "en", "beginner"), (term, "term", "en", "intermediate"))):
        request = TermRequest(term=term, mode=mode, language=language, level=level, bundle_id=bundle_id)
        job_id = "term-delete-" + str(index)
        db.queue_term(job_id, request)
        db.transition(job_id, "running")
        value = TermExplanation(id=term_key(request), term=term, mode=mode, bundle_id=bundle_id, asset_id=bundle.asset.id,
            language=language, level=level, provider="codex", basis="insufficient" if mode == "question" else "general",
            explanation="This saved page does not answer this question." if mode == "question" else "This saved definition explains revenue without adding facts.",
            source_ids=[])
        validate_explanation(value, bundle)
        db.complete_term(job_id, value.model_dump(mode="json"))
        with db.session.begin() as session:
            session.add(Event(job_id=job_id, payload=RuntimeEvent(run_id=job_id, kind="run.completed").model_dump(mode="json")))
        values.append(value)
        jobs.append(job_id)
    return values, jobs


def admission_orderings(db, values):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event as Signal, local
    from sqlalchemy import event
    from backend.app.library_deletion import delete_saved_item
    role = local()
    for first, value in (("admit", values[0]), ("delete", values[2])):
        held, reached, release = Signal(), Signal(), Signal()
        request = TermRequest(**value.model_dump(include={"term", "mode", "bundle_id", "language", "level"}))
        job_id = "term-race-" + first
        def before(connection, cursor, statement, parameters, context, executemany):
            if getattr(role, "name", None) != first and "pg_advisory_xact_lock" in statement:
                reached.set()
        def after(connection, cursor, statement, parameters, context, executemany):
            if getattr(role, "name", None) == first and "pg_advisory_xact_lock" in statement:
                held.set()
                assert release.wait(10), "Second operation did not reach the term gate"
        def operation(name):
            role.name = name
            return db.queue_term(job_id, request) if name == "admit" else delete_saved_item(db, "term", value.id)
        event.listen(db.engine, "before_cursor_execute", before)
        event.listen(db.engine, "after_cursor_execute", after)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(operation, first)
                try:
                    assert held.wait(10), "First operation did not hold the term gate"
                    b = pool.submit(operation, "delete" if first == "admit" else "admit")
                    assert reached.wait(10), "Second operation did not reach the term gate"
                finally:
                    release.set()
                one, two = a.result(timeout=15), b.result(timeout=15)
            if first == "admit":
                assert one == value.model_dump(mode="json") and two.deleted and not db.job(job_id)
            else:
                # A distinct explicit request after deletion may generate again;
                # its original evidence still exists, and no old result is reused.
                assert one.deleted and two is None and db.job(job_id)["status"] == "queued"
                db.transition(job_id, "cancelled")
            assert not db.get("term:" + value.id) and db.get("bundle:" + value.bundle_id)
        finally:
            event.remove(db.engine, "before_cursor_execute", before)
            event.remove(db.engine, "after_cursor_execute", after)
