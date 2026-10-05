"""Read-only source-age presentation; never refresh or mutate saved evidence."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import AwareDatetime

from backend.app.contracts import Contract, EvidenceBundle, SourcePolicy, now
from backend.app.market_rules import private_market_rule
from backend.app.source_registry import source_rule


class SourceAge(Contract):
    source_id: str
    state: Literal["within_age_limit", "stale", "unknown"]
    reason: Literal["within_age_limit", "old_dates", "missing_dates", "future_dates", "unverified", "unregistered", "rights_changed"]
    max_age_seconds: int | None = None


class BundleFreshness(Contract):
    bundle_id: str
    assessed_at: AwareDatetime
    sources: list[SourceAge]


def assess_freshness(bundle: EvidenceBundle, *, at: datetime | None = None) -> BundleFreshness:
    at = at or now()
    if at.tzinfo is None:
        raise ValueError("Assessment time must include a timezone")
    at = at.astimezone(timezone.utc)
    claim_dates = {}
    for claim in bundle.claims:
        if claim.as_of is not None:
            for source_id in claim.source_ids:
                claim_dates.setdefault(source_id, []).append(claim.as_of)
    rows = []
    for source in bundle.sources:
        rule = source_rule(str(source.url))
        # A Yahoo URL/flag alone cannot establish admitted private numerics.
        if source.usage_scope == "private_yahoo_v1":
            market = bundle.market
            numeric_ids = {market.source_id} if market else set()
            if market and market.valuations:
                numeric_ids.add(market.valuations.source_id)
            rule = private_market_rule(str(source.url)) if source.id in numeric_ids else None
        state, reason = "unknown", "unregistered"
        if not source.verified or not source.content_hash or source.asset_id != bundle.asset.id:
            reason = "unverified"
        elif rule is None:
            reason = "unregistered"
        elif source.policy != rule.policy or source.policy in (SourcePolicy.link, SourcePolicy.rejected):
            reason = "rights_changed"
        else:
            source_dates = [value for value in (source.published_at, source.as_of) if value is not None]
            # A claim date can make evidence older; it cannot certify an undated source.
            dates = source_dates + claim_dates.get(source.id, [])
            if source.retrieved_at > at or any(value > at.date() for value in dates):
                reason = "future_dates"
            elif not source_dates:
                reason = "missing_dates"
            elif (at - source.retrieved_at >= rule.max_age
                    or any(at.date() - value >= rule.max_age for value in dates)):
                state, reason = "stale", "old_dates"
            else:
                state, reason = "within_age_limit", "within_age_limit"
        rows.append(SourceAge(source_id=source.id, state=state, reason=reason,
                              max_age_seconds=int(rule.max_age / timedelta(seconds=1)) if rule else None))
    return BundleFreshness(bundle_id=bundle.id, assessed_at=at, sources=rows)
