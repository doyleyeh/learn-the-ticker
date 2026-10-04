from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.contracts import EvidenceBundle, RuntimeEvent, uid


class Base(DeclarativeBase):
    pass


class Record(Base):
    """Versioned application documents; credentials are deliberately not part of this schema."""
    __tablename__ = "records"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    parent_id: Mapped[str | None] = mapped_column(String(200), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Job(Base):
    __tablename__ = "research_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    status: Mapped[str] = mapped_column(String(40), index=True, default="queued")
    request: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Event(Base):
    __tablename__ = "runtime_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("research_jobs.id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class Database:
    def __init__(self, url: str, *, testing: bool = False):
        if not testing and not url.startswith("postgresql+psycopg://"):
            raise ValueError("The desktop application requires PostgreSQL")
        kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool} if testing and url == "sqlite://" else {}
        self.engine = create_engine(url, pool_pre_ping=True, **kwargs)
        self.session = sessionmaker(self.engine, expire_on_commit=False)
        if testing:
            Base.metadata.create_all(self.engine)

    def get(self, record_id: str) -> dict | None:
        with self.session() as session:
            record = session.get(Record, record_id)
            return record.payload if record else None

    def put(self, record_id: str, kind: str, payload: dict, parent_id: str | None = None):
        with self.session.begin() as session:
            self._put(session, record_id, kind, payload, parent_id)

    @staticmethod
    def _put(session, record_id, kind, payload, parent_id=None):
        if kind in ("asset", "bundle"):
            EvidenceBundle.model_validate(payload)
        if kind == "import":
            from backend.app.retained_imports import validate_import_write
            validate_import_write(session, record_id, payload, parent_id)
        record = session.get(Record, record_id)
        if record:
            if record.kind != kind:
                raise ValueError("Record type cannot change")
            if kind in ("bundle", "term", "import") and record.payload != payload:
                raise ValueError("Evidence snapshots are immutable")
            record.payload = payload
            record.updated_at = datetime.now(timezone.utc)
        else:
            session.add(Record(id=record_id, kind=kind, payload=payload, parent_id=parent_id))

    def complete_research(self, job_id: str, payload: dict, *, conversation_id: str | None = None):
        """Publish a snapshot and its references together, or leave all of them unchanged."""
        from backend.app.evidence import validate_claim_sources
        validate_claim_sources(EvidenceBundle.model_validate(payload))
        with self.session.begin() as session:
            job = session.get(Job, job_id, with_for_update=True)
            if not job or job.status != "running":
                raise ValueError("Only a running job can publish research")
            asset_id, bundle_id = payload["asset"]["id"], payload["id"]
            self._put(session, "bundle:" + bundle_id, "bundle", payload, asset_id)
            if conversation_id:
                record = session.get(Record, "conversation:" + conversation_id, with_for_update=True)
                if not record or record.payload["asset_id"] != asset_id:
                    raise ValueError("Conversation scope changed during research; retry explicitly")
                conversation = {**record.payload, "last_activity": datetime.now(timezone.utc).isoformat()}
                conversation["messages"] = [*conversation["messages"],
                    {"role": "user", "text": job.request["query"], "asset_id": asset_id},
                    {"role": "assistant", "bundle_id": bundle_id, "asset_id": asset_id}]
                self._put(session, record.id, "conversation", conversation)
                # A narrow follow-up is a separate cited artifact, not a replacement for the asset page.
            else:
                self._put(session, "asset:" + asset_id, "asset", payload)
            job.status, job.result, job.error = "completed", payload, None
            session.add(Event(job_id=job_id, payload=RuntimeEvent(run_id=job_id, kind="evidence.registered", data={"bundle_id": bundle_id}).model_dump(mode="json")))

    def update_conversation(self, conversation_id: str, *, asset_id=None, bookmarked=None) -> dict:
        with self.session.begin() as session:
            record = session.get(Record, "conversation:" + conversation_id, with_for_update=True)
            if not record:
                raise ValueError("Conversation does not exist")
            # Prevent a scope edit from changing the meaning of an in-flight answer.
            if asset_id and any(job.request.get("conversation_id") == conversation_id for job in session.scalars(select(Job).where(Job.status.in_(["queued", "running"])))):
                raise ValueError("Wait for the active answer or cancel it before changing scope")
            payload = {**record.payload, "last_activity": datetime.now(timezone.utc).isoformat()}
            if asset_id and asset_id != payload["asset_id"]:
                if not session.get(Record, "asset:" + asset_id):
                    raise ValueError("Resolve the new asset before changing conversation scope")
                payload["messages"] = [*payload["messages"], {"role": "scope", "text": "Conversation scope changed", "asset_id": asset_id}]
                payload["asset_id"] = asset_id
            if bookmarked is not None:
                payload["bookmarked"] = bookmarked
            self._put(session, record.id, "conversation", payload)
            return payload

    def complete_term(self, job_id: str, payload: dict):
        """An explanation is an immutable interpretation, never a canonical asset update."""
        with self.session.begin() as session:
            job = session.get(Job, job_id, with_for_update=True)
            if not job or job.status != "running":
                raise ValueError("Only a running job can publish an explanation")
            if not session.get(Record, "bundle:" + payload["bundle_id"]):
                raise ValueError("Explanation evidence no longer exists")
            self._put(session, "term:" + payload["id"], "term", payload, payload["bundle_id"])
            job.status, job.result, job.error = "completed", payload, None

    def expire_conversations(self, retention_days: int, *, at: datetime | None = None) -> int:
        cutoff = (at or datetime.now(timezone.utc)) - timedelta(days=retention_days)
        removed = 0
        with self.session.begin() as session:
            jobs = list(session.scalars(select(Job)))
            active = {job.request.get("conversation_id") for job in jobs if job.status in ("queued", "running")}
            for record in session.scalars(select(Record).where(Record.kind == "conversation").with_for_update()):
                payload = record.payload
                last = datetime.fromisoformat((payload.get("last_activity") or payload["created_at"]).replace("Z", "+00:00"))
                if payload.get("bookmarked") or payload["id"] in active or last >= cutoff:
                    continue
                # Expiring messages also removes their job requests and transport events.
                # Evidence snapshots remain available to saved reports and prior citations.
                for job in jobs:
                    if job.request.get("conversation_id") == payload["id"]:
                        session.execute(delete(Event).where(Event.job_id == job.id))
                        session.delete(job)
                session.delete(record)
                removed += 1
        return removed

    def list(self, kind: str, parent_id: str | None = None) -> list[dict]:
        query = select(Record).where(Record.kind == kind).order_by(Record.updated_at.desc())
        if parent_id is not None:
            query = query.where(Record.parent_id == parent_id)
        with self.session() as session:
            return [row.payload for row in session.scalars(query)]

    def job(self, job_id: str) -> dict | None:
        with self.session() as session:
            row = session.get(Job, job_id)
            if not row:
                return None
            return {"id": row.id, "status": row.status, "request": row.request, "result": row.result, "error": row.error}

    def transition(self, job_id: str, status: str, *, result=None, error=None):
        with self.session.begin() as session:
            row = session.get(Job, job_id)
            if row and row.status not in ("cancelled", "completed", "failed"):
                row.status, row.result, row.error = status, result, error

    def recover(self):
        # Never automatically replay a paid or subscription turn after a crash.
        with self.session.begin() as session:
            for job in session.scalars(select(Job).where(Job.status.in_(["queued", "running"]))):
                job.status, job.error = "interrupted", "Application stopped. Review and retry explicitly."

    def events(self, job_id: str, after: int = 0) -> list[dict]:
        with self.session() as session:
            return [{**row.payload, "sequence": row.id} for row in session.scalars(select(Event).where(Event.job_id == job_id, Event.id > after).order_by(Event.id))]
