"""Application-owned numeric admission; provider output has no financial DTO field."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict
from decimal import Decimal

from backend.app.contracts import EvidenceBundle, FinancialEvidence, FinancialObservation, Source, SourcePolicy, now
from backend.app.identity import ResolvedIdentity, identity_hash
from backend.app.financial_ratios import METHOD, ratios_for_financials
from backend.app.sec_financials import CONCEPTS, ConceptObservations, IssuerObservation, concept_url, default_history, mark_revisions, number_text, observation_id, unit_supported
from backend.app.source_registry import source_rule
from backend.app.structured_financials import StructuredFinancials, matching_issuer

GLOBAL_GAPS = {"price_history_unavailable", "corporate_actions_unavailable", "source_access_or_rate_limited"}
CONCEPT_GAPS = {"unsupported_unit", "unsupported_form", "no_supported_observations", "conflicting_latest_values",
                "nonstandard_or_year_to_date_period", "incomplete_annual_history", "incomplete_quarter_history",
                "incomplete_instant_history", "source_unavailable_or_invalid"}


def source_id(url, digest, retrieved_at):
    return "sec:" + hashlib.sha256(f"{url}\n{digest}\n{retrieved_at.isoformat()}".encode()).hexdigest()


def validate_financials(bundle: EvidenceBundle):
    """Check historical internal consistency, never claim archive authenticity or freshness."""
    data = bundle.financials
    if data is None:
        return
    if (bundle.identity_verification is None or bundle.created_at.tzinfo is None
            or data.checked_at > bundle.created_at):
        raise ValueError("Financial evidence lacks its identity checkpoint")
    instrument = ResolvedIdentity(bundle.asset, bundle.identity_verification)
    issuer = ResolvedIdentity(data.issuer, data.issuer_verification)
    if matching_issuer(instrument, [issuer], at=data.checked_at) is None:
        raise ValueError("Financial issuer association does not match the bundle scope")
    allowed_gaps = GLOBAL_GAPS | {f"{concept}:{gap}" for concept in CONCEPTS for gap in CONCEPT_GAPS}
    if len(set(data.gaps)) != len(data.gaps) or not set(data.gaps) <= allowed_gaps:
        raise ValueError("Unrecognized financial availability metadata")
    if not {"price_history_unavailable", "corporate_actions_unavailable"} <= set(data.gaps):
        raise ValueError("Unqualified price and corporate-action coverage must remain explicit")
    sources = {row.id: row for row in bundle.sources}
    if len(sources) != len(bundle.sources) or len({row.id for row in data.observations}) != len(data.observations):
        raise ValueError("Duplicate financial evidence references")
    rows, used, concept_sources = [], set(), {}
    for row in data.observations:
        concept = row.concept.removeprefix("us-gaap:")
        if row.concept != "us-gaap:" + concept or concept not in CONCEPTS or row.cik != data.issuer.identifiers.get("cik"):
            raise ValueError("Wrong issuer or financial concept")
        source = sources.get(row.source_id)
        if concept in concept_sources and concept_sources[concept] != row.source_id:
            raise ValueError("One concept snapshot cannot mix different retrievals")
        concept_sources[concept] = row.source_id
        url = concept_url(row.cik, concept)
        rule = source_rule(url)
        if (source is None or rule is None or rule.id != "sec-company-concept-v1"
                or str(source.url) != url or source.asset_id != bundle.asset.id
                or source.policy != SourcePolicy.full_text or source.policy != rule.policy
                or not source.official or not source.verified or source.provenance != "structured_adapter"
                or source.publisher != rule.publisher or source.excerpt
                or not re.fullmatch(r"[0-9a-f]{64}", source.content_hash)
                or source.id != source_id(url, source.content_hash, source.retrieved_at)
                or not data.checked_at <= source.retrieved_at <= bundle.created_at):
            raise ValueError("Financial source provenance is missing or inconsistent")
        if (not unit_supported(row.unit, concept) or number_text(Decimal(row.value)) != row.value
                or row.end > row.filed or row.filed > source.retrieved_at.date()
                or row.reported_fiscal_year > source.retrieved_at.year + 1):
            raise ValueError("Invalid financial value, unit or date")
        days = (row.end - row.start).days + 1 if row.start else None
        period = ("instant" if days is None else "annual" if 330 <= days <= 400
                  else "quarter" if 70 <= days <= 110 else "other_duration")
        if ((CONCEPTS[concept][0] == "instant") != (row.start is None)
                or (days is not None and days <= 0) or row.period != period):
            raise ValueError("Financial period is inconsistent with its concept and dates")
        expected = observation_id(row.cik, concept, row.unit, row.start, row.end, row.accession,
                                  row.filed, row.form, row.value, row.reported_fiscal_year, row.reported_fiscal_period)
        if row.id != expected:
            raise ValueError("Financial observation fingerprint does not match its content")
        values = row.model_dump(exclude={"schema_version", "source_id", "supersedes"})
        rows.append(IssuerObservation(**values, supersedes=tuple(row.supersedes), source_url=url,
                                     source_hash=source.content_hash, retrieved_at=source.retrieved_at))
        used.add(source.id)
    actual = {row.id: row for row in data.observations}
    for expected in mark_revisions(tuple(rows)):
        row = actual[expected.id]
        if row.revision != expected.revision or tuple(row.supersedes) != expected.supersedes:
            raise ValueError("Financial revision references or conflict state are inconsistent")
        if row.revision == "conflict" and expected.concept.removeprefix("us-gaap:") + ":conflicting_latest_values" not in data.gaps:
            raise ValueError("Financial conflict disclosure is missing")
    for sid in used:
        group = [row for row in data.observations if row.source_id == sid]
        if sources[sid].published_at != max(row.filed for row in group) or sources[sid].as_of != max(row.end for row in group):
            raise ValueError("Financial source dates disagree with the retained observations")
    for concept in {row.concept.removeprefix("us-gaap:") for row in rows}:
        group = tuple(row for row in rows if row.concept == "us-gaap:" + concept)
        selected = default_history(ConceptObservations(data.issuer.identifiers["cik"], concept, group, ()))
        if not {concept + ":" + gap for gap in selected.gaps} <= set(data.gaps):
            raise ValueError("Financial history gaps are not disclosed")
    if any(row.provenance == "structured_adapter" and row.id not in used for row in bundle.sources):
        raise ValueError("Structured source has no admitted financial observations")
    if ((data.ratio_method is None and data.ratios)
            or (data.ratio_method == METHOD and data.ratios != ratios_for_financials(data))):
        raise ValueError("Financial ratios differ from their admitted inputs and method")


def attach_financials(bundle: EvidenceBundle, result: StructuredFinancials, *, created_at=None) -> EvidenceBundle:
    """Attach only separately retrieved adapter results to a new, unsaved bundle."""
    created_at = created_at or now()
    if (result.instrument is None or result.issuer is None or result.checked_at is None
            or identity_hash(result.instrument.asset) != identity_hash(bundle.asset)
            or bundle.identity_verification != result.instrument.verification):
        raise ValueError("Structured result belongs to a different instrument checkpoint")
    if matching_issuer(result.instrument, [result.issuer], at=created_at) is None:
        raise ValueError("Structured result requires a current identity recheck before publication")
    if bundle.financials is not None:
        raise ValueError("Create a new snapshot for financial refresh")
    sources, observations = {}, []
    for group in result.concepts:
        if group.cik != result.issuer.asset.identifiers.get("cik") or group.concept not in CONCEPTS:
            raise ValueError("Structured concept scope mismatch")
        for row in group.observations:
            if row.cik != group.cik or row.concept != "us-gaap:" + group.concept:
                raise ValueError("Structured observation scope mismatch")
            sid = source_id(row.source_url, row.source_hash, row.retrieved_at)
            rule = source_rule(row.source_url)
            if rule is None or rule.id != "sec-company-concept-v1":
                raise ValueError("Structured source rights are unavailable")
            if sid not in sources:
                sources[sid] = Source(id=sid, asset_id=bundle.asset.id, url=row.source_url,
                    title="SEC issuer observations: " + group.concept, publisher=rule.publisher,
                    retrieved_at=row.retrieved_at, published_at=row.filed, as_of=row.end,
                    content_hash=row.source_hash, policy=rule.policy, official=True, verified=True,
                    provenance="structured_adapter")
            else:
                sources[sid].published_at = max(sources[sid].published_at, row.filed)
                sources[sid].as_of = max(sources[sid].as_of, row.end)
            values = asdict(row)
            for key in ("source_url", "source_hash", "retrieved_at"):
                values.pop(key)
            observations.append(FinancialObservation(**values, source_id=sid))
    data = FinancialEvidence(issuer=result.issuer.asset, issuer_verification=result.issuer.verification,
                             checked_at=result.checked_at, observations=observations, gaps=list(result.gaps))
    data.ratio_method = METHOD
    data.ratios = ratios_for_financials(data)
    # Revalidate, rather than model_copy (which bypasses Pydantic validators).
    return EvidenceBundle.model_validate({**bundle.model_dump(), "created_at": created_at,
        "sources": [*bundle.sources, *sources.values()], "financials": data, "state": "partial"})


def numeric_context(bundle: EvidenceBundle) -> list[dict]:
    """Only current unconflicted issuer observations, never model claims or notes."""
    validate_financials(bundle)
    if bundle.financials is None:
        return []
    return [row.model_dump(mode="json") for row in bundle.financials.observations if row.revision == "current"]
