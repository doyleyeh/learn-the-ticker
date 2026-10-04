"""Bounded SEC concept parsing. Issuer observations are not instrument facts."""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal

from backend.app.evidence import MAX_BYTES

# Concept semantics stay separate; similar labels are not interchangeable history.
CONCEPTS = {
    "Assets": ("instant", "currency"),
    "Liabilities": ("instant", "currency"),
    "StockholdersEquity": ("instant", "currency"),
    "Revenues": ("duration", "currency"),
    "RevenueFromContractWithCustomerExcludingAssessedTax": ("duration", "currency"),
    "NetIncomeLoss": ("duration", "currency"),
    "NetCashProvidedByUsedInOperatingActivities": ("duration", "currency"),
    "EarningsPerShareDiluted": ("duration", "per_share"),
    "WeightedAverageNumberOfDilutedSharesOutstanding": ("duration", "shares"),
}
CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CNY", "HKD", "CHF", "KRW", "INR", "TWD"}
FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "40-F/A"}


@dataclass(frozen=True)
class IssuerObservation:
    id: str
    cik: str
    concept: str
    value: str
    unit: str
    start: date | None
    end: date
    period: str
    accession: str
    filed: date
    form: str
    reported_fiscal_year: int
    reported_fiscal_period: str
    source_url: str
    source_hash: str
    retrieved_at: datetime
    revision: str = "current"
    supersedes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConceptObservations:
    cik: str
    concept: str
    observations: tuple[IssuerObservation, ...]
    gaps: tuple[str, ...]


def concept_url(cik: str, concept: str) -> str:
    if not re.fullmatch(r"[0-9]{10}", cik) or not int(cik) or concept not in CONCEPTS:
        raise ValueError("Unregistered issuer or concept")
    return f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Invalid filing date")
    return date.fromisoformat(value)


def _number(value):
    # Parse JSON numbers directly as Decimal; never round them through binary floats.
    if type(value) not in (int, Decimal) or not Decimal(value).is_finite():
        raise ValueError("Invalid financial number")
    if Decimal(value).adjusted() > 40 or Decimal(value).as_tuple().exponent < -18:
        raise ValueError("Financial number exceeds precision limit")
    result = format(Decimal(value), "f")
    if len(result) > 80:
        raise ValueError("Financial number exceeds precision limit")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if Decimal(value) == 0 else result


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate structured source field")
        result[key] = value
    return result


def _constant(_):
    raise ValueError("Non-finite structured source number")


def _unit_supported(unit, concept):
    kind = CONCEPTS[concept][1]
    return ((kind == "currency" and unit in CURRENCIES)
            or (kind == "per_share" and unit in {currency + "/shares" for currency in CURRENCIES})
            or (kind == "shares" and unit == "shares"))


def parse_concept(raw: bytes, *, cik: str, concept: str, retrieved_at: datetime) -> ConceptObservations:
    url = concept_url(cik, concept)
    if (not isinstance(raw, bytes) or len(raw) > MAX_BYTES or retrieved_at.tzinfo is None):
        raise ValueError("Invalid structured retrieval bounds")
    try:
        data = json.loads(raw, parse_float=Decimal, parse_constant=_constant, object_pairs_hook=_unique)
    except (RecursionError, ArithmeticError) as exc:
        raise ValueError("Structured source exceeds parsing limits") from exc
    if (not isinstance(data, dict) or type(data.get("cik")) is not int or data["cik"] != int(cik)
            or data.get("taxonomy") != "us-gaap" or data.get("tag") != concept
            or not isinstance(data.get("entityName"), str) or not data["entityName"].strip()
            or not isinstance(data.get("units"), dict) or len(data["units"]) > 50):
        raise ValueError("Structured source does not match the requested issuer and concept")
    digest, rows, gaps, count = hashlib.sha256(raw).hexdigest(), {}, set(), 0
    for unit, entries in data["units"].items():
        if not isinstance(entries, list):
            raise ValueError("Invalid structured observations")
        count += len(entries)
        if count > 10_000:
            raise ValueError("Too many structured observations")
        if not _unit_supported(unit, concept):
            gaps.add("unsupported_unit")
            continue
        for item in entries:
            if not isinstance(item, dict):
                raise ValueError("Invalid structured observation")
            if not isinstance(item.get("form"), str):
                raise ValueError("Invalid filing form")
            if item["form"] not in FORMS:
                gaps.add("unsupported_form")
                continue
            accession = item.get("accn")
            if not isinstance(accession, str) or not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession):
                raise ValueError("Invalid filing reference")
            # The accession prefix may be a filing agent: it must not be treated as the issuer CIK.
            end, filed = _date(item.get("end")), _date(item.get("filed"))
            start = _date(item["start"]) if "start" in item else None
            if end > filed or filed > retrieved_at.date() or (start is not None and start > end):
                raise ValueError("Inconsistent financial dates")
            fy, fp = item.get("fy"), item.get("fp")
            if type(fy) is not int or not 1900 <= fy <= retrieved_at.year + 1 or not isinstance(fp, str) or fp not in {"FY", "Q1", "Q2", "Q3", "Q4"}:
                raise ValueError("Invalid reported fiscal labels")
            # Fiscal labels belong to the filing, not necessarily its comparative observation.
            if CONCEPTS[concept][0] == "instant":
                if start is not None:
                    raise ValueError("Instant concept has a duration")
                period = "instant"
            else:
                if start is None:
                    raise ValueError("Duration concept is missing its start date")
                days = (end - start).days + 1
                period = "annual" if 330 <= days <= 400 else "quarter" if 70 <= days <= 110 else "other_duration"
                if period == "other_duration":
                    gaps.add("nonstandard_or_year_to_date_period")
            value = _number(item.get("val"))
            identity = [cik, concept, unit, str(start), str(end), accession, str(filed), item["form"], value, fy, fp]
            key = hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()
            rows[key] = IssuerObservation(key, cik, "us-gaap:" + concept, value, unit, start, end, period, accession,
                                          filed, item["form"], fy, fp, url, digest, retrieved_at)
    result = mark_revisions(tuple(rows.values()))
    if not result:
        gaps.add("no_supported_observations")
    if any(row.revision == "conflict" for row in result):
        gaps.add("conflicting_latest_values")
    return ConceptObservations(cik, concept, result, tuple(sorted(gaps)))


def mark_revisions(rows: tuple[IssuerObservation, ...]) -> tuple[IssuerObservation, ...]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row.cik, row.concept, row.unit, row.start, row.end)].append(row)
    result = []
    for group in grouped.values():
        if len(group) > 128:
            raise ValueError("Too many revisions for one financial period")
        latest = max(row.filed for row in group)
        current = [row for row in group if row.filed == latest]
        conflict = len({row.value for row in current}) > 1
        older = tuple(sorted(row.id for row in group if row.filed < latest))
        for row in group:
            state = "superseded" if row.filed < latest else "conflict" if conflict else "current"
            result.append(replace(row, revision=state, supersedes=older if row.filed == latest else ()))
    return tuple(sorted(result, key=lambda row: (row.concept, row.unit, row.end, row.start or row.end, row.filed, row.id)))


def default_history(data: ConceptObservations) -> ConceptObservations:
    """Select periods without fabricating quarters, converting units or discarding revisions."""
    selected, gaps = [], set(data.gaps)
    for unit in sorted({row.unit for row in data.observations}):
        for period, limit in (("annual", 5), ("quarter", 12), ("instant", 20)):
            rows = [row for row in data.observations if row.unit == unit and row.period == period]
            latest = max((row.end for row in rows), default=None)
            cutoff = latest - timedelta(days=3 * 366 + 7 if period == "quarter" else 5 * 366) if latest else None
            dates = sorted({(row.start, row.end) for row in rows if row.end >= cutoff}, key=lambda dates: dates[1], reverse=True)[:limit]
            selected.extend(row for row in rows if (row.start, row.end) in dates)
            if (CONCEPTS[data.concept][0] == "instant") == (period == "instant") and len(dates) < limit:
                gaps.add("incomplete_" + period + "_history")
            if any((newer[1] - older[1]).days > (400 if period == "annual" else 110) for newer, older in zip(dates, dates[1:])):
                gaps.add("incomplete_" + period + "_history")
    return replace(data, observations=tuple(selected), gaps=tuple(sorted(gaps)))
