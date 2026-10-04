"""Read-only cache admission; a fresh wrapper cannot refresh an old source."""
from datetime import timedelta
import re

from backend.app.contracts import EvidenceBundle, ResearchRequest, now
from backend.app.identity import identity_hash
from backend.app.source_registry import source_rule


def reusable(bundle: EvidenceBundle, request: ResearchRequest, *, at=None) -> bool:
    at = at or now()
    # Financial reuse needs a structured refresh policy (M2-T03). No fresh prose
    # claim may make a separate old numeric series appear current.
    if bundle.financials is not None or bundle.market is not None or bundle.completion != "complete":
        return False
    if (request.refresh or request.conversation_id or bundle.asset.id != request.asset_id
            or bundle.language != request.language or bundle.level != request.level
            or bundle.state in ("unavailable", "stale")):
        return False
    # Until each adapter can prove latest-source coverage, latest requests always recheck.
    if re.search(r"\b(latest|current|today|now|recent|up.to.date)\b|最新|目前|今天|現在|近期", request.query, re.I):
        return False
    proof = bundle.identity_verification
    if (not proof or proof.identity_hash != identity_hash(bundle.asset)
            or not timedelta(0) <= at - proof.retrieved_at < timedelta(days=1)
            or bundle.created_at.tzinfo is None
            or not timedelta(0) <= at - bundle.created_at < timedelta(days=1)
            or not bundle.claims):
        return False
    sources = {source.id: source for source in bundle.sources}
    for claim in bundle.claims:
        if not claim.source_ids:
            return False
        for sid in claim.source_ids:
            source = sources.get(sid)
            rule = source_rule(str(source.url)) if source else None
            if (not source or not rule or not source.verified or source.asset_id != bundle.asset.id
                    or source.policy != rule.policy or not source.content_hash
                    or not timedelta(0) <= at - source.retrieved_at < rule.max_age):
                return False
            dates = [value for value in (source.published_at, source.as_of, claim.as_of) if value is not None]
            if not dates or any(value > at.date() or at.date() - value >= rule.max_age for value in dates):
                return False
    return True
