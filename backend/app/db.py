from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, case, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.contracts import Conversation, EvidenceBundle, RuntimeEvent, uid


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
            bundle = EvidenceBundle.model_validate(payload)
            if kind == "asset" and bundle.completion != "complete":
                raise ValueError("An incomplete run cannot replace the asset page")
        if kind == "import":
            from backend.app.retained_imports import validate_import_write
            validate_import_write(session, record_id, payload, parent_id)
        if kind == "comparison":
            from backend.app.comparisons import ComparisonResult, validate_comparison
            result = ComparisonResult.model_validate(payload)
            if record_id != "comparison:" + result.id or parent_id is not None:
                raise ValueError("Comparison identity is inconsistent")
            def original(version):
                source = session.get(Record, "bundle:" + version)
                return source.payload if source and source.kind == "bundle" else None
            validate_comparison(result, original)
        if kind == "report":
            from backend.app.reports import ResearchReport, validate_report
            result = ResearchReport.model_validate(payload)
            if record_id != "report:" + result.id or parent_id != result.bundle_id:
                raise ValueError("Report identity is inconsistent")
            def report_original(version):
                source = session.get(Record, "bundle:" + version)
                return source.payload if source and source.kind == "bundle" else None
            validate_report(result, report_original)
        record = session.get(Record, record_id)
        if record:
            if record.kind != kind:
                raise ValueError("Record type cannot change")
            if kind in ("bundle", "term", "import", "import_explanation", "comparison", "report") and record.payload != payload:
                raise ValueError("Evidence snapshots are immutable")
            record.payload = payload
            record.updated_at = datetime.now(timezone.utc)
        else:
            session.add(Record(id=record_id, kind=kind, payload=payload, parent_id=parent_id))

    def complete_research(self, job_id: str, payload: dict, *, conversation_id: str | None = None):
        """Publish a snapshot and its references together, or leave all of them unchanged."""
        from backend.app.evidence import validate_claim_sources
        bundle = EvidenceBundle.model_validate(payload)
        validate_claim_sources(bundle)
        if bundle.completion != "complete":
            raise ValueError("A section checkpoint cannot complete a research run")
        with self.session.begin() as session:
            job = session.get(Job, job_id, with_for_update=True)
            if not job or job.status != "running":
                raise ValueError("Only a running job can publish research")
            asset_id, bundle_id = payload["asset"]["id"], payload["id"]
            from backend.app.evidence_reuse import validate_context_references
            def original(version):
                record = session.get(Record, "bundle:" + version)
                return record.payload if record and record.kind == "bundle" else None
            validate_context_references(bundle, original)
            self._put(session, "bundle:" + bundle_id, "bundle", payload, asset_id)
            if conversation_id:
                record = session.get(Record, "conversation:" + conversation_id, with_for_update=True)
                if (not record or record.payload["asset_id"] != asset_id
                        or record.payload.get("context_bundle_id") != job.request.get("context_bundle_id")):
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

    def checkpoint_research(self, job_id: str, bundle: EvidenceBundle):
        value = EvidenceBundle.model_validate(bundle.model_dump())
        if value.completion != "section_checkpoint":
            raise ValueError("Progress requires a section checkpoint")
        with self.session.begin() as session:
            job = session.get(Job, job_id, with_for_update=True)
            if not job or job.status != "running" or job.request.get("purpose"):
                raise ValueError("Only active research can admit a section")
            if job.request.get("asset_id") not in (None, value.asset.id):
                raise ValueError("Section scope differs from the request")
            if (job.request.get("language", "en"), job.request.get("level", "beginner")) != (value.language, value.level):
                raise ValueError("Section language or reader level differs from the request")
            payload = value.model_dump(mode="json")
            self._put(session, "bundle:" + value.id, "bundle", payload, value.asset.id)
            job.result = payload
            session.add(Event(job_id=job_id, payload=RuntimeEvent(run_id=job_id, kind="evidence.registered",
                text="Independently checked evidence is available; research is still incomplete.", data={"bundle_id": value.id}).model_dump(mode="json")))

    @staticmethod
    def conversation_context(session, asset_id, context_bundle_id=None):
        from backend.app.identity import identity_hash
        current = session.get(Record, "asset:" + asset_id)
        if not current or current.kind != "asset":
            raise ValueError("Resolve the asset before selecting conversation evidence")
        version = context_bundle_id or current.payload["id"]
        original = session.get(Record, "bundle:" + version)
        if not original or original.kind != "bundle":
            raise ValueError("Conversation page evidence is missing")
        bundle = EvidenceBundle.model_validate(original.payload)
        if bundle.id != version or identity_hash(bundle.asset) != identity_hash(EvidenceBundle.model_validate(current.payload).asset):
            raise ValueError("Conversation page evidence does not match the resolved asset")
        return version

    def create_conversation(self, asset_id, context_bundle_id=None):
        with self.session.begin() as session:
            version = self.conversation_context(session, asset_id, context_bundle_id)
            payload = Conversation(asset_id=asset_id, context_bundle_id=version,
                messages=[{"role": "scope", "text": "Conversation started with selected page evidence",
                           "asset_id": asset_id, "context_bundle_id": version}],
                last_activity=datetime.now(timezone.utc)).model_dump(mode="json")
            self._put(session, "conversation:" + payload["id"], "conversation", payload)
            return payload

    def queue_research(self, job_id, request):
        """Freeze page context while holding the same lock as explicit scope changes."""
        with self.session.begin() as session:
            if request.conversation_id:
                record = session.get(Record, "conversation:" + request.conversation_id, with_for_update=True)
                if not record or record.kind != "conversation":
                    raise ValueError("Conversation does not exist")
                if request.asset_id != record.payload["asset_id"]:
                    raise ValueError("Confirm a conversation scope change before researching another asset")
                version = record.payload.get("context_bundle_id")
                if request.context_bundle_id and request.context_bundle_id != version:
                    raise ValueError("Select conversation evidence before starting an answer")
                if version:
                    self.conversation_context(session, request.asset_id, version)
                request = request.model_copy(update={"context_bundle_id": version})
                # An admitted question is user activity even if its answer later
                # fails or is cancelled. Renew within the same locked transaction.
                self._put(session, record.id, "conversation", {
                    **record.payload, "last_activity": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")})
            elif request.context_bundle_id:
                raise ValueError("Page context selection requires a conversation")
            session.add(Job(id=job_id, request=request.model_dump(mode="json"), status="queued"))
        return request

    def update_conversation(self, conversation_id: str, *, asset_id=None, context_bundle_id=None, bookmarked=None) -> dict:
        with self.session.begin() as session:
            record = session.get(Record, "conversation:" + conversation_id, with_for_update=True)
            if not record:
                raise ValueError("Conversation does not exist")
            # Prevent a scope edit from changing the meaning of an in-flight answer.
            if (asset_id or context_bundle_id) and any(job.request.get("conversation_id") == conversation_id for job in session.scalars(select(Job).where(Job.status.in_(["queued", "running"])))):
                raise ValueError("Wait for the active answer or cancel it before changing scope")
            payload = {**record.payload, "last_activity": datetime.now(timezone.utc).isoformat()}
            changed_asset = asset_id and asset_id != payload["asset_id"]
            if changed_asset or context_bundle_id:
                selected_asset = asset_id or payload["asset_id"]
                version = self.conversation_context(session, selected_asset, context_bundle_id)
                if changed_asset or version != payload.get("context_bundle_id"):
                    payload["messages"] = [*payload["messages"], {"role": "scope",
                        "text": "Conversation scope changed" if changed_asset else "Conversation page evidence changed",
                        "asset_id": selected_asset, "context_bundle_id": version}]
                    payload["asset_id"], payload["context_bundle_id"] = selected_asset, version
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

    def queue_import_explanation(self, job_id, request):
        """Recheck the source after parsing, under the same lock as deletion."""
        from backend.app.import_learning import ImportExplanation, learning_key, validate_learning
        from backend.app.import_storage import RetainedImportView, summary
        from backend.app.retained_imports import RetainedImport
        with self.session.begin() as session:
            source = session.get(Record, "import:" + request.document_id, with_for_update=True)
            if not source or source.kind != "import":
                raise ValueError("Retained document no longer exists")
            retained = RetainedImport.model_validate(source.payload)
            if retained.document.content_hash != request.content_hash:
                raise ValueError("Retained document scope changed")
            cached = session.get(Record, "import_explanation:" + learning_key(request))
            if cached:
                validate_learning(ImportExplanation.model_validate(cached.payload),
                    RetainedImportView(item=summary(retained), document=retained.document))
                return cached.payload
            session.add(Job(id=job_id, request=request.model_dump(mode="json"), status="queued"))
        return None

    def complete_import_explanation(self, job_id: str, payload: dict):
        from backend.app.import_learning import ImportExplanation, ImportLearningRequest, learning_key, validate_learning
        from backend.app.import_storage import RetainedImportView, summary
        from backend.app.retained_imports import RetainedImport
        with self.session.begin() as session:
            job = session.get(Job, job_id, with_for_update=True)
            if not job or job.status != "running":
                raise ValueError("Only a running job can publish an explanation")
            request = ImportLearningRequest.model_validate(job.request)
            value = ImportExplanation.model_validate(payload)
            source = session.get(Record, "import:" + request.document_id)
            if not source or value.id != learning_key(request) or (value.provider, value.model) != (request.provider, request.model):
                raise ValueError("Explanation scope changed")
            retained = RetainedImport.model_validate(source.payload)
            validate_learning(value, RetainedImportView(item=summary(retained), document=retained.document))
            self._put(session, "import_explanation:" + value.id, "import_explanation", payload, value.document_id)
            job.status, job.result, job.error = "completed", payload, None

    def expire_conversations(self, retention_days: int, *, at: datetime | None = None) -> int:
        cutoff = (at or datetime.now(timezone.utc)) - timedelta(days=retention_days)
        removed = 0
        with self.session.begin() as session:
            # Admission takes this same row lock before inserting its job. Read
            # job metadata only after acquiring the locks, so a waiter observes
            # committed admission instead of deleting from an earlier snapshot.
            records = list(session.scalars(select(Record).where(Record.kind == "conversation").with_for_update()))
            conversation_id = Job.request["conversation_id"].as_string()
            jobs = session.execute(select(Job.id, Job.status, conversation_id.label("conversation_id"))
                .where(conversation_id.is_not(None)))
            by_conversation = {}
            for job in jobs:
                by_conversation.setdefault(job.conversation_id, []).append(job)
            for record in records:
                payload = record.payload
                related = by_conversation.get(payload["id"], [])
                last = datetime.fromisoformat((payload.get("last_activity") or payload["created_at"]).replace("Z", "+00:00"))
                if payload.get("bookmarked") or any(job.status in ("queued", "running") for job in related) or last >= cutoff:
                    continue
                # Expiring messages also removes their job requests and transport events.
                # Evidence snapshots remain available to saved reports and prior citations.
                for job in related:
                    session.execute(delete(Event).where(Event.job_id == job.id))
                    session.execute(delete(Job).where(Job.id == job.id))
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

    def research_jobs(self) -> list[dict]:
        from backend.app.contracts import ResearchJobSummary
        # Bound before loading payloads. Learning jobs have a purpose and are recovered
        # through their document/term cache, not as asset research.
        query = select(Job.id, Job.status, Job.request, Job.created_at).where(Job.request["purpose"].as_string().is_(None))
        query = query.order_by(case((Job.status.in_(["queued", "running"]), 0), else_=1), Job.created_at.desc(), Job.id.desc()).limit(50)
        with self.session() as session:
            return [ResearchJobSummary(id=row.id, status=row.status, request=row.request,
                created_at=row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc)).model_dump(mode="json")
                for row in session.execute(query)]

    def transition(self, job_id: str, status: str, *, result=None, error=None):
        with self.session.begin() as session:
            row = session.get(Job, job_id)
            if row and row.status not in ("cancelled", "completed", "failed"):
                if result is None and status in ("cancelled", "failed", "interrupted") and (row.result or {}).get("completion") == "section_checkpoint":
                    result = row.result
                row.status, row.result, row.error = status, result, error

    def recover(self):
        # Never automatically replay a paid or subscription turn after a crash.
        with self.session.begin() as session:
            for job in session.scalars(select(Job).where(Job.status.in_(["queued", "running"]))):
                job.status, job.error = "interrupted", "Application stopped. Review and retry explicitly."

    def events(self, job_id: str, after: int = 0) -> list[dict]:
        with self.session() as session:
            return [{**row.payload, "sequence": row.id} for row in session.scalars(select(Event).where(Event.job_id == job_id, Event.id > after).order_by(Event.id))]
