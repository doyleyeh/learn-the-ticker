"""Date-proven weekly context, separate from canonical facts and model notes.

Retains the useful Eastern-week and sparse-context rules from the fixture selector.
Only the independently registered SEC filing-date adapter is currently qualified.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field

from backend.app.contracts import Contract, EvidenceBundle, SourcePolicy
from backend.app.evidence import normalize, validate_claim_sources
from backend.app.identity import identity_hash
from backend.app.source_operations import private_source
from backend.app.source_registry import source_rule
from backend.safety import find_forbidden_output_phrases

EASTERN = ZoneInfo("America/New_York")
MAX_ITEMS = 8
MAX_INPUT = 800_000


class WeeklyWindow(Contract):
    as_of: date
    timezone: Literal["America/New_York"] = "America/New_York"
    previous_start: date
    previous_end: date
    current_start: date | None
    current_end: date | None
    earlier_start: date
    earlier_end: date


class DatedItem(Contract):
    event_id: str
    source_id: str
    claim_id: str | None = None
    title: str
    text: str | None = None
    published: date
    effective: date | None
    bucket: Literal["previous_week", "current_week", "earlier_context"]
    date_basis: Literal["verified_sec_filing_date"] = "verified_sec_filing_date"


class WeeklyFocus(Contract):
    method: Literal["verified-filing-week-v1"] = "verified-filing-week-v1"
    window: WeeklyWindow
    weekly: list[DatedItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    earlier: list[DatedItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    earlier_requested: bool
    analysis_available: bool
    coverage: Literal["saved_verified_filings_only"] = "saved_verified_filings_only"


def weekly_window(as_of: datetime | date) -> WeeklyWindow:
    if isinstance(as_of, datetime):
        if as_of.tzinfo is None:
            raise ValueError("Weekly selection needs an explicit timezone")
        day = as_of.astimezone(EASTERN).date()
    elif isinstance(as_of, date):
        day = as_of
    else:
        raise ValueError("Weekly selection needs a date or aware timestamp")
    monday = day - timedelta(days=day.weekday())
    return WeeklyWindow(as_of=day, previous_start=monday - timedelta(days=7), previous_end=monday - timedelta(days=1),
        current_start=monday if day > monday else None, current_end=day - timedelta(days=1) if day > monday else None,
        earlier_start=day - timedelta(days=30), earlier_end=monday - timedelta(days=8))


def select_weekly(payload, *, as_of: datetime | date) -> WeeklyFocus:
    bundle = EvidenceBundle.model_validate(payload)
    if len(bundle.model_dump_json()) > MAX_INPUT or len(bundle.sources) > 200 or len(bundle.claims) > 1000:
        raise ValueError("Weekly evidence exceeds bounded selection limits")
    proof = bundle.identity_verification
    if not proof or proof.identity_hash != identity_hash(bundle.asset) or proof.retrieved_at > bundle.created_at:
        raise ValueError("Weekly selection needs independently resolved original evidence")
    validate_claim_sources(bundle)
    window = weekly_window(as_of)
    candidates = []
    for source in bundle.sources:
        publication, rule = source.filing_publication, source_rule(str(source.url))
        if (publication is None or rule is None or rule.id != "sec-filings-v1"
                or rule.policy != SourcePolicy.full_text or source.policy != rule.policy or private_source(source)
                or source.publisher != rule.publisher or source.asset_id != bundle.asset.id):
            continue
        day = publication.filed  # The reporting period is not the publication/event date.
        if not window.earlier_start <= day < window.as_of:
            continue
        quote = next((claim for claim in bundle.claims if claim.section == "news" and claim.kind == "fact"
            and claim.value is None and claim.source_ids == [source.id]
            and normalize(claim.text) in normalize(source.excerpt)
            and not find_forbidden_output_phrases(claim.text)), None)
        bucket = "earlier_context" if day < window.previous_start else "previous_week" if day <= window.previous_end else "current_week"
        item = DatedItem(event_id=publication.cik + ":" + publication.accession, source_id=source.id,
            claim_id=quote.id if quote else None, title=publication.form + " filing", text=quote.text if quote else None,
            published=day, effective=publication.report_date, bucket=bucket)
        candidates.append((item, source))
    # Every currently qualified item is official. Stable keys make source order irrelevant.
    candidates.sort(key=lambda pair: (-pair[0].published.toordinal(), pair[0].event_id, pair[0].source_id))
    weekly, earlier, events, bodies = [], [], set(), set()
    for item, source in candidates:
        if item.event_id in events or source.content_hash in bodies:
            continue
        events.add(item.event_id)
        bodies.add(source.content_hash)
        (earlier if item.bucket == "earlier_context" else weekly).append(item)
    weekly = weekly[:MAX_ITEMS]
    sparse = len(weekly) < 3
    return WeeklyFocus(window=window, weekly=weekly, earlier=earlier[:MAX_ITEMS] if sparse else [],
        earlier_requested=sparse, analysis_available=len(weekly) >= 2)
