"""Official filing-event metadata; it does not verify a document's narrative claims."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta

from backend.app.contracts import FilingPublication, SourcePolicy, now
from backend.app.evidence import MAX_BYTES, fetch_public_bytes
from backend.app.identity import INDEX_URL, ResolvedIdentity, normalized
from backend.app.source_registry import source_rule

EVENT_FORMS = {"8-K", "8-K/A", "6-K", "6-K/A", "10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "40-F/A"}


def index_url(cik):
    if not re.fullmatch(r"[0-9]{10}", cik) or not int(cik):
        raise ValueError("Invalid issuer reference")
    return f"https://data.sec.gov/submissions/CIK{cik}.json"


def document_url(cik, accession, filename):
    if (not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession)
            or not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,199}\.(?:htm|html|txt)", filename)):
        raise ValueError("Unreviewed filing document")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{filename}"


def valid_issuer(issuer, at):
    cik = issuer.asset.identifiers.get("cik", "")
    return (issuer.valid(at) and issuer.verification.authority == "sec-listings-v1"
            and str(issuer.verification.source_url) == INDEX_URL
            and re.fullmatch(r"[0-9]{10}", cik) and int(cik) > 0
            and issuer.asset.id == f"SEC:{cik}:{(issuer.asset.exchange or '').upper()}:{issuer.asset.symbol.upper()}")


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate filing metadata field")
        result[key] = value
    return result


def filing_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Invalid filing date")
    return date.fromisoformat(value)


def parse_filings(raw, issuer, *, retrieved_at):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES or not valid_issuer(issuer, retrieved_at):
        raise ValueError("Unverified filing index scope or bounds")
    try:
        data = json.loads(raw, object_pairs_hook=unique)
    except RecursionError as exc:
        raise ValueError("Filing metadata exceeds parsing limits") from exc
    cik = issuer.asset.identifiers["cik"]
    if (not isinstance(data, dict) or data.get("cik") != cik or not isinstance(data.get("name"), str)
            or normalized(data["name"]) != normalized(issuer.asset.name)):
        raise ValueError("Filing index belongs to a different issuer")
    recent = data.get("filings", {}).get("recent") if isinstance(data.get("filings"), dict) else None
    keys = ("accessionNumber", "filingDate", "reportDate", "form", "primaryDocument")
    if not isinstance(recent, dict) or any(not isinstance(recent.get(key), list) for key in keys):
        raise ValueError("Invalid filing index columns")
    count = len(recent["accessionNumber"])
    if count > 20000 or any(len(recent[key]) != count for key in keys):
        raise ValueError("Mismatched or excessive filing index rows")
    rows, seen = [], set()
    digest = hashlib.sha256(raw).hexdigest()
    for i in range(count):
        accession, filed, reported, form, filename = (recent[key][i] for key in keys)
        if any(not isinstance(value, str) for value in (accession, filed, reported, form, filename)):
            raise ValueError("Invalid filing metadata")
        if form not in EVENT_FORMS:
            continue
        published = filing_date(filed)
        report_date = filing_date(reported) if reported else None
        if published > retrieved_at.date() or (report_date and report_date > published):
            raise ValueError("Inconsistent filing index dates")
        url = document_url(cik, accession, filename)
        if accession in seen:
            raise ValueError("Duplicate filing index accession")
        seen.add(accession)
        rows.append(FilingPublication(cik=cik, accession=accession, form=form, filed=published,
            report_date=report_date, document_url=url, index_url=index_url(cik), index_hash=digest, retrieved_at=retrieved_at))
    return sorted(rows, key=lambda row: (row.filed, row.accession), reverse=True)


class SecFilingsAdapter:
    def __init__(self, fetcher=None, *, clock=now):
        self.fetcher, self.clock = fetcher or fetch_public_bytes, clock

    def retrieve(self, issuer, *, cancelled):
        if cancelled.is_set():
            raise InterruptedError()
        if not valid_issuer(issuer, self.clock()):
            raise ValueError("Filing issuer proof is unavailable")
        url = index_url(issuer.asset.identifiers["cik"])
        rule = source_rule(url)
        if rule is None or rule.id != "sec-submissions-v1":
            raise ValueError("Filing index permission is unavailable")
        raw = self.fetcher(url, accept="application/json")
        if cancelled.is_set():
            raise InterruptedError()
        return parse_filings(raw, issuer, retrieved_at=self.clock())


def validate_publications(bundle):
    if bundle.created_at.tzinfo is None:
        raise ValueError("Dated filing snapshots require a timezone")
    if bundle.financials:
        issuer = ResolvedIdentity(bundle.financials.issuer, bundle.financials.issuer_verification)
    elif bundle.identity_verification:
        issuer = ResolvedIdentity(bundle.asset, bundle.identity_verification)
    else:
        raise ValueError("Dated filings require independent issuer identity")
    for source in bundle.sources:
        proof = source.filing_publication
        if proof is None:
            continue
        expected = document_url(proof.cik, proof.accession, proof.document_url.path.rsplit("/", 1)[-1])
        rule = source_rule(expected)
        if (proof.cik != issuer.asset.identifiers.get("cik") or not valid_issuer(issuer, proof.retrieved_at)
                or str(proof.index_url) != index_url(proof.cik) or str(proof.document_url) != expected
                or str(source.url) != expected or source.asset_id != bundle.asset.id
                or proof.form not in EVENT_FORMS or proof.filed > proof.retrieved_at.date()
                or (proof.report_date and proof.report_date > proof.filed)
                or not source.verified or not source.official or source.policy != SourcePolicy.full_text
                or rule is None or rule.id != "sec-filings-v1" or source.publisher != rule.publisher
                or not re.fullmatch(r"[0-9a-f]{64}", source.content_hash) or not source.excerpt
                or source.provenance != "verified_retrieval"
                or source.published_at != proof.filed or source.as_of != proof.report_date
                or not timedelta(0) <= source.retrieved_at - proof.retrieved_at < timedelta(days=1)
                or source.retrieved_at > bundle.created_at):
            raise ValueError("Filing publication proof does not match its source and issuer")
