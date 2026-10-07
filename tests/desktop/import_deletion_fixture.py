"""Small synthetic originals and interpretations published through storage contracts."""
from backend.app.contracts import RuntimeEvent, now
from backend.app.db import Event
from backend.app.import_documents import parse_document
from backend.app.import_learning import ImportExplanation, ImportLearningRequest, learning_key, passages
from backend.app.import_previews import ImportPreview
from backend.app.retained_imports import retain_import


def seed_imports(db):
    documents, explanations, jobs = [], [], []
    for index in range(2):
        raw = f"Metric,Value\nSynthetic{index},123\n".encode()
        parsed = parse_document(raw, "csv", permission_confirmed=True)
        preview = ImportPreview(state="unverified", origin="local_file", document=parsed, checked_at=now())
        item = retain_import(db, raw, preview, title=f"Synthetic deletion document {index}", storage_and_backup_confirmed=True)
        documents.append(item)
        locator = next(key for key, text in passages(parsed).items() if text == "123")
        for language in ("en", "zh-TW"):
            request = ImportLearningRequest(document_id=item.id, content_hash=parsed.content_hash, language=language, transmission_confirmed=True)
            job_id = f"document-{index}-{language}"
            assert db.queue_import_explanation(job_id, request) is None
            db.transition(job_id, "running")
            value = ImportExplanation(document_id=item.id, content_hash=parsed.content_hash, language=language,
                provider="codex", id=learning_key(request), explanation="The document contains an unverified value.",
                references=[{"locator": locator, "quote": "123"}])
            db.complete_import_explanation(job_id, value.model_dump(mode="json"))
            with db.session.begin() as session:
                session.add(Event(job_id=job_id, payload=RuntimeEvent(run_id=job_id, kind="run.completed").model_dump(mode="json")))
            explanations.append(value)
            jobs.append(job_id)
    return documents, explanations, jobs


def admission_orderings(db, original):
    """Exercise both actual PostgreSQL lock orderings without timing sleeps."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event as Signal, local
    from sqlalchemy import event
    from backend.app.library_deletion import delete_retained_item
    role = local()
    for first in ("queue", "delete"):
        item = retain_import(db, original.content(), ImportPreview(state="unverified", origin="local_file",
            document=original.document, checked_at=now()), title="Synthetic race document", storage_and_backup_confirmed=True)
        request = ImportLearningRequest(document_id=item.id, content_hash=item.document.content_hash, transmission_confirmed=True)
        job_id = "document-race-" + first
        held, reached, release = Signal(), Signal(), Signal()

        def before(connection, cursor, statement, parameters, context, executemany):
            task = getattr(role, "name", None)
            if first == "queue" and task == "queue" and statement.startswith("INSERT INTO research_jobs"):
                held.set()
                assert release.wait(10), "Deletion did not reach document admission lock"
            if task != first and "FROM records" in statement and "FOR UPDATE" in statement:
                reached.set()

        def after(connection, cursor, statement, parameters, context, executemany):
            if first == "delete" and getattr(role, "name", None) == "delete" and "FROM records" in statement and "FOR UPDATE" in statement:
                held.set()
                assert release.wait(10), "Admission did not reach document deletion lock"

        def operation(name):
            role.name = name
            try:
                return db.queue_import_explanation(job_id, request) if name == "queue" else delete_retained_item(db, "import", item.id)
            except ValueError as exc:
                return str(exc)

        event.listen(db.engine, "before_cursor_execute", before)
        event.listen(db.engine, "after_cursor_execute", after)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(operation, first)
                try:
                    assert held.wait(10), "First operation did not obtain the document lock"
                    b = pool.submit(operation, "delete" if first == "queue" else "queue")
                    assert reached.wait(10), "Second operation did not reach the document lock"
                finally:
                    release.set()
                one, two = a.result(timeout=15), b.result(timeout=15)
            if first == "queue":
                assert one is None and "active document explanation" in two
                assert db.get("import:" + item.id) and db.job(job_id)["status"] == "queued"
                db.transition(job_id, "cancelled")
                assert delete_retained_item(db, "import", item.id).deleted
            else:
                assert one.deleted and two == "Retained document no longer exists"
            assert db.get("import:" + item.id) is None and db.job(job_id) is None
        finally:
            event.remove(db.engine, "before_cursor_execute", before)
            event.remove(db.engine, "after_cursor_execute", after)
