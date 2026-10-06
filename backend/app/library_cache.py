"""Budget disposable payloads without removing saved references or reading bodies."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from pydantic import Field
from sqlalchemy import JSON, LargeBinary, Text, cast, delete, func, select
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH

from backend.app.contracts import Contract, Settings
from backend.app.db import Event, Job, Record


class CacheError(ValueError):
    pass


class CacheSummary(Contract):
    budget_bytes: int = Field(ge=0)
    disposable_bytes: int = Field(ge=0)
    protected_bytes: int = Field(ge=0)
    removed_bytes: int = Field(default=0, ge=0)
    removed_items: int = Field(default=0, ge=0)
    deferred_for_active_work: bool = False
    # These are stored JSON payload bytes, not allocated PostgreSQL disk space.
    accounting: Literal["stored_json_payload_bytes"] = "stored_json_payload_bytes"


@dataclass
class Node:
    size: int
    at: datetime
    refs: set[str] = field(default_factory=set)
    root: bool = False


def byte_size(session, column):
    value = cast(column, Text)
    size = func.octet_length(value) if session.bind.dialect.name == "postgresql" else func.length(cast(value, LargeBinary))
    return func.coalesce(size, 0)


def stamp(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def graph(session):
    """Project identifiers/locators and server-side lengths, never financial bodies."""
    p = Record.payload
    postgres = session.bind.dialect.name == "postgresql"
    if postgres:
        message_versions = func.jsonb_path_query_array(cast(p, JSONB), cast('$.messages[*].bundle_id', JSONPATH), type_=JSON)
        message_contexts = func.jsonb_path_query_array(cast(p, JSONB), cast('$.messages[*].context_bundle_id', JSONPATH), type_=JSON)
    else:
        message_versions = message_contexts = p["messages"]
    rows = session.execute(select(Record.id, Record.kind, Record.updated_at, byte_size(session, p).label("size"),
        p["id"].as_string().label("version"), p["asset_id"].as_string().label("asset"),
        p["bundle_id"].as_string().label("bundle"), p["context_bundle_id"].as_string().label("context"),
        p["context_references"].label("originals"), p["left"]["bundle_id"].as_string().label("left"),
        p["right"]["bundle_id"].as_string().label("right"), p["document_id"].as_string().label("document"),
        message_versions.label("versions"), message_contexts.label("contexts")))
    nodes = {}
    for row in rows:
        refs = set()
        def add(kind, value, required=False):
            if value is None and not required:
                return
            if not isinstance(value, str) or not value:
                raise CacheError("Cache references require review; no cached work was removed")
            refs.add(kind + ":" + value)
        if row.kind == "asset":
            add("bundle", row.version, True)
        elif row.kind == "bundle":
            for original in row.originals or []:
                add("bundle", original.get("bundle_id"), True)
        elif row.kind in ("saved", "report", "term"):
            add("bundle", row.bundle, True)
        elif row.kind == "comparison":
            add("bundle", row.left, True)
            add("bundle", row.right, True)
        elif row.kind == "conversation":
            add("asset", row.asset, True)
            add("bundle", row.context)
            for value in row.versions or []:
                add("bundle", value if postgres else value.get("bundle_id"))
            for value in row.contexts or []:
                add("bundle", value if postgres else value.get("context_bundle_id"))
        elif row.kind == "import_explanation":
            add("import", row.document, True)
        elif row.kind not in ("settings", "import"):
            raise CacheError("Unknown library record; no cached work was removed")
        nodes[row.id] = Node(row.size, stamp(row.updated_at), refs, row.kind not in ("asset", "bundle"))

    q, r = Job.request, Job.result
    active = False
    for row in session.execute(select(Job.id, Job.status, Job.created_at,
            (byte_size(session, q) + byte_size(session, r)).label("size"),
            q["purpose"].as_string().label("purpose"), q["conversation_id"].as_string().label("conversation"),
            q["context_bundle_id"].as_string().label("context"), q["bundle_id"].as_string().label("bundle"),
            q["document_id"].as_string().label("document"), r["id"].as_string().label("result"))):
        if row.purpose not in (None, "term_explanation", "import_explanation"):
            raise CacheError("Unknown library job; no cached work was removed")
        refs = set()
        for kind, value in (("conversation", row.conversation), ("bundle", row.context),
                ("bundle", row.bundle), ("import", row.document)):
            if value:
                refs.add(kind + ":" + value)
        if row.result:
            kind = {None: "bundle", "term_explanation": "term", "import_explanation": "import_explanation"}.get(row.purpose)
            if kind is None:
                raise CacheError("Unknown library job; no cached work was removed")
            refs.add(kind + ":" + row.result)
        running = row.status in ("queued", "running")
        active |= running
        # Explicit conversation/learning history persists with those saved items.
        nodes["job:" + row.id] = Node(row.size, stamp(row.created_at), refs, running or bool(row.conversation or row.purpose))
    for row in session.execute(select(Event.id, Event.job_id, byte_size(session, Event.payload).label("size"),
            Event.payload["data"]["bundle_id"].as_string().label("bundle"))):
        job = nodes.get("job:" + row.job_id)
        if not job:
            raise CacheError("Orphaned library event; no cached work was removed")
        refs = {"job:" + row.job_id}
        if row.bundle:
            refs.add("bundle:" + row.bundle)
        nodes["event:" + str(row.id)] = Node(row.size, job.at, refs, job.root)
    for node in nodes.values():
        if node.refs - nodes.keys():
            raise CacheError("Cache references require review; no cached work was removed")
    return nodes, active


def plan(nodes, budget):
    """Keep root closure; evict oldest complete disposable reference components."""
    protected, pending = set(), [key for key, node in nodes.items() if node.root]
    while pending:
        key = pending.pop()
        if key not in protected:
            protected.add(key)
            pending.extend(nodes[key].refs - protected)
    available = nodes.keys() - protected
    neighbors = {key: set(nodes[key].refs & available) for key in available}
    for key, refs in list(neighbors.items()):
        for ref in refs.copy():
            neighbors[ref].add(key)
    groups = []
    unseen = set(available)
    for seed in sorted(available):
        if seed not in unseen:
            continue
        group, pending = set(), [seed]
        while pending:
            key = pending.pop()
            if key in group:
                continue
            group.add(key)
            pending.extend(neighbors[key] - group)
        unseen -= group
        # A current/new item keeps its connected originals recent as a group.
        groups.append((max(nodes[key].at for key in group), min(group), group))
    disposable = sum(nodes[key].size for key in available)
    removed, amount = set(), 0
    for _, _, group in sorted(groups):
        if disposable - amount <= budget:
            break
        removed |= group
        amount += sum(nodes[key].size for key in group)
    return protected, disposable, removed, amount


def manage_cache(db, *, evict=False, budget_bytes=None):
    # Internal smaller test budgets do not alter validated user settings.
    with db.session(info={"cache_maintenance": True}) as session, session.begin():
        settings = session.get(Record, "settings")
        budget = budget_bytes if budget_bytes is not None else Settings.model_validate(settings.payload if settings else {}).cache_gb * 1_000_000_000
        if not isinstance(budget, int) or budget < 0:
            raise ValueError("Invalid cache budget")
        nodes, active = graph(session)
        protected, disposable, remove, amount = plan(nodes, budget)
        summary = CacheSummary(budget_bytes=budget, disposable_bytes=disposable,
            protected_bytes=sum(nodes[key].size for key in protected), deferred_for_active_work=active and disposable > budget)
        if evict and not active and remove:
            # Delete dependants before jobs. The exclusive gate precedes all
            # ordinary transaction locks, including reference admission.
            events = [int(key[6:]) for key in remove if key.startswith("event:")]
            jobs = [key[4:] for key in remove if key.startswith("job:")]
            records = [key for key in remove if not key.startswith(("event:", "job:"))]
            for model, identifiers in ((Event, events), (Job, jobs), (Record, records)):
                for start in range(0, len(identifiers), 500):
                    session.execute(delete(model).where(model.id.in_(identifiers[start:start + 500])))
            summary = summary.model_copy(update={"disposable_bytes": disposable - amount,
                "removed_bytes": amount, "removed_items": len(remove)})
        return summary
