"""Explicit removal of saved artifacts; cited evidence is never cascaded away."""
from typing import Literal

from pydantic import Field
from sqlalchemy import delete, select

from backend.app.contracts import Contract
from backend.app.db import Event, Job, Record

SavedItemKind = Literal["saved", "conversation", "comparison", "report"]


class SavedItemDeletion(Contract):
    kind: SavedItemKind
    id: str = Field(min_length=1, max_length=200)
    deleted: bool
    evidence_preserved: Literal[True] = True


def delete_saved_item(db, kind: SavedItemKind, item_id: str) -> SavedItemDeletion:
    result = SavedItemDeletion(kind=kind, id=item_id, deleted=False)
    with db.session.begin() as session:
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
        session.delete(record)
    return result.model_copy(update={"deleted": True})
