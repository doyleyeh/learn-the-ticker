"""Immutable historical research reports with a separate dated context pack."""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import AwareDatetime, Field

from backend.app.contracts import AssetIdentity, Contract, EvidenceBundle, Settings, now, uid
from backend.app.weekly import WeeklyFocus, select_weekly


class ReportRequest(Contract):
    bundle_id: str = Field(min_length=1, max_length=200)


class ResearchReport(Contract):
    id: str = Field(default_factory=uid, pattern=r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
    method: Literal["saved-research-report-v1"] = "saved-research-report-v1"
    created_at: AwareDatetime = Field(default_factory=now)
    bundle_id: str = Field(min_length=1, max_length=200)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    asset: AssetIdentity
    evidence_saved_at: AwareDatetime
    focus: WeeklyFocus
    reading_guide: str | None = None
    guide_source_ids: list[str] = Field(default_factory=list, max_length=8)


def build_report(payload, *, created_at=None, report_id=None):
    bundle = EvidenceBundle.model_validate(payload)
    at = created_at or now()
    if bundle.created_at > at or bundle.completion != "complete":
        raise ValueError("Reports require a completed original page saved before the report")
    focus = select_weekly(bundle, as_of=at)
    guide = None
    if focus.analysis_available:
        guide = (f"This saved evidence contains {len(focus.weekly)} distinct verified filing publications in the weekly window. "
            "Read each original filing alongside its effective/reporting date: publication during this window does not mean every underlying event occurred this week. "
            "These filings provide partial context, not a complete account of developments or a prediction of returns. Earlier context is excluded from this count.")
    fingerprint = hashlib.sha256(json.dumps(bundle.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return ResearchReport(id=report_id or uid(), created_at=at, bundle_id=bundle.id, fingerprint=fingerprint,
        asset=bundle.asset, evidence_saved_at=bundle.created_at, focus=focus, reading_guide=guide,
        guide_source_ids=[item.source_id for item in focus.weekly] if guide else [])


def validate_report(report, lookup):
    original = lookup(report.bundle_id)
    if original is None:
        raise ValueError("Report references missing original evidence")
    expected = build_report(original, created_at=report.created_at, report_id=report.id)
    if expected != report:
        raise ValueError("Report differs from its original evidence or dated selection")


def create_report(db, request):
    from backend.app.db import Record
    with db.session.begin() as session:
        settings = session.get(Record, "settings", with_for_update=True)
        if not settings or not Settings.model_validate(settings.payload).cloud_enabled:
            raise ValueError("Offline mode permits previously saved reports only")
        original = session.get(Record, "bundle:" + request.bundle_id)
        if original is None or original.kind != "bundle":
            raise ValueError("Selected report evidence is missing")
        result = build_report(original.payload)
        db._put(session, "report:" + result.id, "report", result.model_dump(mode="json"), result.bundle_id)
        return result


def report_markdown(report):
    """Render only normalized stored content, without regenerating dated selection."""
    def clean(value):
        return value.replace("<", "&lt;").replace(">", "&gt;").replace("[", "\\[").replace("]", "\\]")
    window = report.focus.window
    lines = ["# Saved historical report", "", f"Report saved: {report.created_at.isoformat()}",
        f"Original page: {report.bundle_id}; saved {report.evidence_saved_at.isoformat()}",
        "Historical saved evidence; not point-in-time reconstruction. No fresh retrieval or AI synthesis.",
        "", "## Weekly News Focus", f"U.S. Eastern as of {window.as_of}; previous week {window.previous_start} through {window.previous_end}; "
        f"current week {window.current_start or 'empty'} through {window.current_end or 'empty'}.",
        "Partial coverage: independently verified filings in this original page only; absence is not evidence of no developments."]
    for heading, items in (("Weekly items", report.focus.weekly), ("Earlier context (excluded from weekly counts)", report.focus.earlier)):
        lines += ["", "### " + heading]
        lines += [f"- {item.published}: {clean(item.title)}; effective/reporting date {item.effective or 'unknown'}; "
            f"source {clean(item.source_id)}. " + clean(item.text or "No admitted narrative quotation.") for item in items] or ["No qualifying saved items."]
    lines += ["", f"Earlier context requested: {report.focus.earlier_requested}; available range {window.earlier_start} through {window.earlier_end}.",
        "", "## Weekly analysis — app reading guide", report.reading_guide or "Suppressed: fewer than two verified weekly items.",
        "Source references: " + (", ".join(report.guide_source_ids) or "none"), "", "---", ""]
    return "\n".join(lines)
