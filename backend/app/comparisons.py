"""Immutable, descriptive comparisons of explicitly selected admitted evidence.

No retrieval, model invocation, price arithmetic, or ranking lives in this module.
Creation aligns retained values once; ordinary reads return the stored result.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import AwareDatetime, Field, ValidationError

from backend.app.contracts import AssetIdentity, Contract, EvidenceBundle, now, uid
from backend.app.evidence import normalize, validate_claim_sources
from backend.app.identity import identity_hash
from backend.app.sec_financials import CONCEPTS
from backend.app.source_registry import source_rule
from backend.safety import find_forbidden_output_phrases

METHOD = "saved-evidence-alignment-v2"
MAX_CONTEXT = 800_000


class ComparisonRequest(Contract):
    left_bundle_id: str = Field(min_length=1, max_length=200)
    right_bundle_id: str = Field(min_length=1, max_length=200)


class ComparisonSide(Contract):
    bundle_id: str = Field(min_length=1, max_length=200)
    asset: AssetIdentity
    saved_at: AwareDatetime
    state: Literal["partial", "available", "stale", "unavailable"]
    completion: Literal["complete", "section_checkpoint"]
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class ComparisonCell(Contract):
    state: Literal["available", "missing", "not_applicable", "unknown_type", "conflict"] = "missing"
    value: str | None = Field(default=None, max_length=100, pattern=r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")
    text: str | None = Field(default=None, max_length=10000)
    unit: str | None = Field(default=None, max_length=30)
    start: date | None = None
    end: date | None = None
    basis: str | None = Field(default=None, max_length=200)
    source_ids: list[str] = Field(default_factory=list, max_length=10)
    evidence_ids: list[str] = Field(default_factory=list, max_length=10)


class ComparisonRow(Contract):
    id: str = Field(max_length=160)
    label: str = Field(max_length=200)
    left: ComparisonCell
    right: ComparisonCell
    alignment: Literal["aligned", "descriptive", "missing_evidence", "different_types", "different_units", "different_periods", "different_methods", "share_basis_unverified"]


class ComparisonResult(Contract):
    id: str = Field(default_factory=uid, pattern=r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
    method: Literal["saved-evidence-alignment-v1", "saved-evidence-alignment-v2"] = METHOD
    created_at: AwareDatetime = Field(default_factory=now)
    left: ComparisonSide
    right: ComparisonSide
    rows: list[ComparisonRow] = Field(min_length=1, max_length=100)


def side(bundle):
    payload = json.dumps(bundle.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return ComparisonSide(bundle_id=bundle.id, asset=bundle.asset, saved_at=bundle.created_at,
        state=bundle.state, completion=bundle.completion, fingerprint=hashlib.sha256(payload.encode()).hexdigest())


def checked_bundle(payload):
    try:
        bundle = EvidenceBundle.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Saved comparison evidence could not be validated") from exc
    proof = bundle.identity_verification
    if (not proof or proof.identity_hash != identity_hash(bundle.asset)
            or bundle.created_at.tzinfo is None or proof.retrieved_at > bundle.created_at):
        raise ValueError("Each comparison page needs an independently resolved identity; research it first")
    validate_claim_sources(bundle)
    return bundle


def missing(bundle, *, types=None):
    kind = bundle.asset.asset_type
    state = "unknown_type" if kind == "unknown" else "not_applicable" if types and kind not in types else "missing"
    return ComparisonCell(state=state)


def financial_cell(bundle, concept, period):
    absent = missing(bundle, types={"stock"})
    if absent.state != "missing" or not bundle.financials:
        return absent
    rows = [r for r in bundle.financials.observations if r.concept == "us-gaap:" + concept and r.period == period and r.revision != "superseded"]
    if not rows:
        return absent
    latest = max(r.end for r in rows)
    rows = [r for r in rows if r.end == latest]
    if len(rows) != 1 or rows[0].revision != "current":
        return ComparisonCell(state="conflict", end=latest)
    row = rows[0]
    return ComparisonCell(state="available", value=row.value, unit=row.unit, start=row.start, end=row.end,
        basis="issuer-reported:" + row.period, source_ids=[row.source_id], evidence_ids=[row.id])


def return_cell(bundle, period, field):
    absent = missing(bundle)
    if absent.state != "missing" or not bundle.market:
        return absent
    row = next((r for r in bundle.market.returns if r.period == period), None)
    if not row:
        return absent
    value = getattr(row, field)
    return ComparisonCell(state="available" if value is not None else "missing", value=value,
        unit="%", start=row.start, end=row.end, basis=bundle.market.return_method + ":" + field + ":" + bundle.market.currency,
        source_ids=[row.source_id], evidence_ids=["return:" + period + ":" + field])


VALUATIONS = {"MarketCap": "Market capitalization", "EnterpriseValue": "Enterprise value", "PeRatio": "Trailing P/E",
    "PsRatio": "P/S", "PbRatio": "P/B", "EnterprisesValueRevenueRatio": "EV/revenue", "EnterprisesValueEBITDARatio": "EV/EBITDA"}


def valuation_cell(bundle, metric, sampling):
    absent = missing(bundle, types={"stock"})
    values = bundle.market.valuations if bundle.market else None
    if absent.state != "missing" or not values:
        return absent
    rows = [r for r in values.points if r.metric == metric and r.sampling == sampling]
    if not rows:
        return absent
    rows = [r for r in rows if r.date == max(p.date for p in rows)]
    # Distinct sampling/denominator semantics are never silently collapsed.
    if len(rows) != 1:
        return ComparisonCell(state="conflict", end=rows[0].date)
    row = rows[0]
    return ComparisonCell(state="available" if row.value is not None else "missing", value=row.value,
        unit=row.currency if metric in ("MarketCap", "EnterpriseValue") else "ratio", end=row.date,
        basis=values.method + ":" + row.sampling + ":" + row.period_type, source_ids=[values.source_id],
        evidence_ids=["valuation:" + metric + ":" + row.sampling + ":" + row.date.isoformat()])


def narrative_cell(bundle, section, *, method):
    types = {"etf", "fund"} if section in ("benchmark", "holdings", "construction", "costs", "expense_ratio", "holdings_count", "breadth") else None
    absent = missing(bundle, types=types)
    if method == METHOD and section == "overview" and absent.state == "unknown_type":
        # An unresolved type suppresses type-dependent metrics, not an admitted overview.
        absent = ComparisonCell()
    if absent.state != "missing":
        return absent
    aliases = {"holdings": "holdings_exposure", "construction": "construction_methodology",
        "costs": "cost_trading_context", "risks": "etf_specific_risks", "beginner_role": "fund_objective_role"}
    sections = {section, aliases.get(section, section)} if method == METHOD else {section}
    for claim in bundle.claims:
        if (claim.section not in sections or claim.kind != "fact" or claim.value is not None
                or len(claim.source_ids) > 10 or find_forbidden_output_phrases(claim.text)):
            continue
        sources = {s.id: s for s in bundle.sources}
        if not claim.source_ids or any(sid not in sources or not source_rule(str(sources[sid].url))
                or source_rule(str(sources[sid].url)).policy != sources[sid].policy
                or sources[sid].policy.value not in ("full_text_allowed", "summary_allowed")
                for sid in claim.source_ids):
            continue
        if not any(normalize(claim.text) in normalize(sources[sid].excerpt) for sid in claim.source_ids):
            continue
        return ComparisonCell(state="available", text=claim.text, end=claim.as_of, basis="cited_description",
            source_ids=claim.source_ids, evidence_ids=[claim.id])
    return absent


def alignment(left, right, left_type, right_type):
    if left.state != "available" or right.state != "available":
        return "missing_evidence"
    if left.text is not None or right.text is not None:
        return "descriptive"
    if left_type != right_type:
        return "different_types"
    if left.unit != right.unit:
        return "different_units"
    if (left.start, left.end) != (right.start, right.end):
        return "different_periods"
    if left.basis != right.basis:
        return "different_methods"
    if left.unit and ("share" in left.unit or left.unit == "shares"):
        return "share_basis_unverified"
    return "aligned"


def aligned_rows(left, right, *, method):
    rows = []
    def add(key, label, getter):
        a, b = getter(left), getter(right)
        rows.append(ComparisonRow(id=key, label=label, left=a, right=b,
            alignment=alignment(a, b, left.asset.asset_type, right.asset.asset_type)))
    for section, label in (("overview", "Overview"), ("benchmark", "Benchmark"), ("holdings", "Holdings"),
                           ("expense_ratio", "Expense ratio"), ("holdings_count", "Holdings count"), ("breadth", "Breadth"),
                           ("construction", "Construction"), ("costs", "Costs"), ("risks", "Risks"), ("beginner_role", "Educational role")):
        add("description:" + section, label, lambda bundle: narrative_cell(bundle, section, method=method))
    for concept, (kind, _) in CONCEPTS.items():
        for period in (["instant"] if kind == "instant" else ["annual", "quarter"]):
            add("financial:" + concept + ":" + period, concept + " — " + period, lambda bundle: financial_cell(bundle, concept, period))
    for period in ("ytd", "1y", "3y", "5y", "retained"):
        for field, label in (("price_percent", "Price return"), ("total_return_estimate_percent", "Total return estimate (provider-adjusted)")):
            add("return:" + period + ":" + field, label + " — " + period, lambda bundle: return_cell(bundle, period, field))
    for metric, label in VALUATIONS.items():
        for sampling in ("annual", "quarterly", "trailing"):
            add("valuation:" + metric + ":" + sampling, label + " — " + sampling,
                lambda bundle: valuation_cell(bundle, metric, sampling))
    return rows


def build_comparison(left, right, *, created_at=None, result_id=None, method=METHOD):
    if len(left.model_dump_json()) + len(right.model_dump_json()) > MAX_CONTEXT:
        raise ValueError("Selected comparison evidence exceeds the bounded context limit")
    left, right = checked_bundle(left), checked_bundle(right)
    at = created_at or now()
    if left.asset.id == right.asset.id:
        raise ValueError("Select two different independently resolved assets")
    if max(left.created_at, right.created_at) > at:
        raise ValueError("Comparison evidence cannot be newer than its result")
    return ComparisonResult(id=result_id or uid(), method=method, created_at=at, left=side(left), right=side(right), rows=aligned_rows(left, right, method=method))


def validate_comparison(result, lookup):
    """Publication/archive consistency check, never used to generate on GET."""
    original = [lookup(selected.bundle_id) for selected in (result.left, result.right)]
    if not all(original):
        raise ValueError("Comparison references missing original evidence")
    left, right = (checked_bundle(payload) for payload in original)
    expected = build_comparison(left, right, created_at=result.created_at, result_id=result.id, method=result.method)
    if expected != result:
        raise ValueError("Comparison differs from its original evidence or alignment method")


def create_comparison(db, request):
    from backend.app.contracts import Settings
    from backend.app.db import Record
    with db.session.begin() as session:
        settings = session.get(Record, "settings", with_for_update=True)
        if not settings or not Settings.model_validate(settings.payload).cloud_enabled:
            raise ValueError("Offline mode permits previously generated comparisons only")
        def original(version):
            row = session.get(Record, "bundle:" + version)
            if not row or row.kind != "bundle":
                raise ValueError("Selected comparison evidence is missing")
            return checked_bundle(row.payload)
        result = build_comparison(original(request.left_bundle_id), original(request.right_bundle_id))
        db._put(session, "comparison:" + result.id, "comparison", result.model_dump(mode="json"))
        return result
