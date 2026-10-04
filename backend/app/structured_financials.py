"""Official issuer financial observations with separately verified instrument scope."""
from __future__ import annotations

import threading
import re
from dataclasses import dataclass
from datetime import datetime

from backend.app.contracts import now
from backend.app.evidence import SourceFetchError, fetch_public_bytes
from backend.app.figi_identity import MAPPING_URL, SEARCH_URL, RegisteredIdentityResolver
from backend.app.identity import INDEX_URL, ResolvedIdentity, normalized
from backend.app.sec_financials import CONCEPTS, ConceptObservations, concept_url, default_history, parse_concept
from backend.app.source_registry import source_rule

# Reviewed source vocabulary, not an asset list. Country composites are not venues.
# https://www.openfigi.com/docs/OpenFIGI-exchange-codes.csv (2026-10-04)
SEC_EXCHANGES = {"UN": "NYSE", "UQ": "Nasdaq", "UR": "Nasdaq", "UW": "Nasdaq"}


@dataclass(frozen=True)
class StructuredFinancials:
    instrument: ResolvedIdentity | None
    issuer: ResolvedIdentity | None
    concepts: tuple[ConceptObservations, ...]
    gaps: tuple[str, ...]
    checked_at: datetime | None = None


def matching_issuer(instrument: ResolvedIdentity, issuers: list[ResolvedIdentity], *, at):
    asset = instrument.asset
    if (not instrument.valid(at) or instrument.verification.authority != "openfigi-v3"
            or str(instrument.verification.source_url) not in (MAPPING_URL, SEARCH_URL)
            or asset.asset_type != "stock" or asset.exchange not in SEC_EXCHANGES
            or asset.identifiers.get("openfigi_securityType2") != "Common Stock"):
        return None
    matches = []
    for row in issuers:
        candidate, proof = row.asset, row.verification
        cik = candidate.identifiers.get("cik", "")
        if (row.valid(at) and proof.authority == "sec-listings-v1" and str(proof.source_url) == INDEX_URL
                and re.fullmatch(r"[0-9]{10}", cik) and int(cik) > 0
                and candidate.id == f"SEC:{cik}:{(candidate.exchange or '').upper()}:{candidate.symbol.upper()}"
                and normalized(candidate.exchange or "") == normalized(SEC_EXCHANGES[asset.exchange])
                and normalized(candidate.symbol) == normalized(asset.symbol)
                and normalized(candidate.name) == normalized(asset.name)):
            matches.append(row)
    # Keep both independent records. No CIK is inserted into the instrument identity.
    return matches[0] if len(matches) == 1 else None


class SecFinancialAdapter:
    def __init__(self, resolver=None, fetcher=None, *, clock=now):
        self.resolver = resolver or RegisteredIdentityResolver()
        self.fetcher, self.clock = fetcher or fetch_public_bytes, clock

    def retrieve(self, query: str, *, concepts=None, cancelled: threading.Event | None = None,
                 resolved: ResolvedIdentity | None = None) -> StructuredFinancials:
        selected = tuple(CONCEPTS) if concepts is None else tuple(concepts)
        if not selected or len(selected) > len(CONCEPTS) or len(set(selected)) != len(selected) or any(key not in CONCEPTS for key in selected):
            raise ValueError("Select registered financial concepts")
        def check_cancel():
            if cancelled is not None and cancelled.is_set():
                raise InterruptedError("Structured retrieval was cancelled")
        check_cancel()
        try:
            instruments = [resolved] if resolved is not None else self.resolver.resolve(query)
        except (ValueError, OSError):
            return StructuredFinancials(None, None, (), ("instrument_identity_unavailable",))
        check_cancel()
        if len(instruments) != 1:
            return StructuredFinancials(None, None, (), ("instrument_identity_ambiguous_or_unavailable",))
        instrument = instruments[0]
        # Resolve issuer records directly from SEC, never from provider output or a user CIK.
        try:
            issuers = self.resolver.sec.resolve(instrument.asset.symbol)
        except (ValueError, OSError):
            return StructuredFinancials(instrument, None, (), ("issuer_identity_unavailable",))
        check_cancel()
        checked_at = self.clock()
        issuer = matching_issuer(instrument, issuers, at=checked_at)
        if issuer is None:
            return StructuredFinancials(instrument, None, (), ("issuer_instrument_association_unconfirmed",))
        results, gaps = [], {"price_history_unavailable", "corporate_actions_unavailable"}
        for concept in selected:
            check_cancel()
            url = concept_url(issuer.asset.identifiers["cik"], concept)
            rule = source_rule(url)
            if rule is None or rule.id != "sec-company-concept-v1":
                raise ValueError("Structured source permission is unavailable")
            try:
                raw = self.fetcher(url, accept="application/json")
                check_cancel()
                result = default_history(parse_concept(raw, cik=issuer.asset.identifiers["cik"], concept=concept, retrieved_at=self.clock()))
            except InterruptedError:
                raise
            except SourceFetchError as exc:
                gaps.add(concept + ":source_unavailable_or_invalid")
                if exc.status in (401, 403, 429) or exc.status >= 500:
                    gaps.add("source_access_or_rate_limited")
                    break
            except (ValueError, OSError):
                gaps.add(concept + ":source_unavailable_or_invalid")
                continue
            else:
                results.append(result)
                gaps.update(concept + ":" + gap for gap in result.gaps)
        check_cancel()
        return StructuredFinancials(instrument, issuer, tuple(results), tuple(sorted(gaps)), checked_at)
