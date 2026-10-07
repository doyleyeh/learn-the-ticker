"""Explicit removal of saved artifacts; cited evidence is never cascaded away."""
from typing import Literal

from pydantic import Field, ValidationError
from sqlalchemy import delete, select

from backend.app.contracts import Contract
from backend.app.db import Event, Job, Record

SavedItemKind = Literal["saved", "conversation", "comparison", "report", "term"]
RetainedItemKind = Literal["import", "import_explanation"]


class SavedItemDeletion(Contract):
    kind: SavedItemKind
    id: str = Field(min_length=1, max_length=200)
    deleted: bool
    evidence_preserved: Literal[True] = True


def delete_saved_item(db, kind: SavedItemKind, item_id: str) -> SavedItemDeletion:
    result = SavedItemDeletion(kind=kind, id=item_id, deleted=False)
    with db.session(info={"cache_maintenance": kind == "term"}) as session, session.begin():
        record = session.get(Record, kind + ":" + item_id, with_for_update=True)
        if record is None:
            return result
        if record.kind != kind:
            raise ValueError("Saved item type is inconsistent; nothing was deleted")
        if kind == "conversation":
            # Same lock as queue_research. A waiting admission either commits
            # first and blocks deletion, or sees the deleted conversation.
            related = Job.request["conversation_id"].as_string() == item_id
            if session.scalar(select(Job.id).where(related, Job.status.in_(["queued", "running"])).limit(1)):
                raise ValueError("Wait for the active answer or cancel it before deleting this conversation")
            session.execute(delete(Event).where(Event.job_id.in_(select(Job.id).where(related))))
            session.execute(delete(Job).where(related))
        if kind == "term":
            from backend.app.contracts import TermExplanation, TermRequest
            from backend.app.terms import term_key
            try:
                value = TermExplanation.model_validate(record.payload)
                scope = TermRequest(**value.model_dump(include={"term", "mode", "bundle_id", "language", "level"}))
            except ValidationError:
                raise ValueError("Saved explanation scope is inconsistent; nothing was deleted") from None
            if value.id != item_id or term_key(scope) != item_id:
                raise ValueError("Saved explanation scope is inconsistent; nothing was deleted")
            # The exclusive gate precedes admission's shared gate. Compare the
            # canonical key in Python: SQL lower() is not Unicode casefold().
            rows = session.execute(select(Job.id, Job.status, Job.request).where(
                Job.request["purpose"].as_string() == "term_explanation",
                Job.request["bundle_id"].as_string() == value.bundle_id))
            try:
                matching = [row for row in rows if term_key(TermRequest.model_validate(row.request)) == item_id]
            except ValidationError:
                raise ValueError("Saved explanation jobs are inconsistent; nothing was deleted") from None
            if any(row.status in ("queued", "running") for row in matching):
                raise ValueError("Wait for the active explanation or cancel it before deleting this item")
            identifiers = [row.id for row in matching]
            for start in range(0, len(identifiers), 500):
                selected = identifiers[start:start + 500]
                session.execute(delete(Event).where(Event.job_id.in_(selected)))
                session.execute(delete(Job).where(Job.id.in_(selected)))
        session.delete(record)
    return result.model_copy(update={"deleted": True})


class RetainedItemDeletion(Contract):
    kind: RetainedItemKind
    id: str = Field(min_length=1, max_length=200)
    deleted: bool
    original_document_preserved: bool


def delete_retained_item(db, kind: RetainedItemKind, item_id: str) -> RetainedItemDeletion:
    result = RetainedItemDeletion(kind=kind, id=item_id, deleted=False,
        original_document_preserved=kind == "import_explanation")
    with db.session.begin() as session:
        # Every explanation admission and deletion locks its original document
        # first. Read only the parent identifier before obtaining that lock.
        document_id = item_id if kind == "import" else session.scalar(
            select(Record.parent_id).where(Record.id == "import_explanation:" + item_id, Record.kind == "import_explanation"))
        if document_id is None:
            return result
        source = session.get(Record, "import:" + document_id, with_for_update=True)
        record = source if kind == "import" else session.get(Record, "import_explanation:" + item_id, with_for_update=True)
        if record is None:
            return result
        if not source or source.kind != "import" or record.kind != kind:
            raise ValueError("Retained item references are inconsistent; nothing was deleted")
        related = (Job.request["purpose"].as_string() == "import_explanation") & (Job.request["document_id"].as_string() == document_id)
        if kind == "import_explanation":
            if record.payload.get("document_id") != document_id:
                raise ValueError("Retained item references are inconsistent; nothing was deleted")
            for field in ("content_hash", "language", "level"):
                related &= Job.request[field].as_string() == record.payload[field]
        if session.scalar(select(Job.id).where(related, Job.status.in_(["queued", "running"])).limit(1)):
            raise ValueError("Wait for the active document explanation or cancel it before deleting this item")
        session.execute(delete(Event).where(Event.job_id.in_(select(Job.id).where(related))))
        session.execute(delete(Job).where(related))
        if kind == "import":
            session.execute(delete(Record).where(Record.kind == "import_explanation", Record.parent_id == document_id))
        session.delete(record)
    return result.model_copy(update={"deleted": True})
