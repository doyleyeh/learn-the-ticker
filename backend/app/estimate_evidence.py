"""Private attributed opinions, with no claim to a forecast publication timestamp."""
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal
import re

from backend.app.contracts import AnalystEstimates, Source, SourcePolicy
from backend.app.market_estimates import PERIODS
from backend.app.sec_financials import number_text

TITLE = "Yahoo Finance analyst estimates (opinions; experimental personal use only)"


def estimate_unit(metric, currency):
    return ("USD/share" if metric == "eps" else "USD") if currency == "USD" else None


def attach_estimates(bundle, mapped, *, created_at):
    from backend.app.market_evidence import market_source_id
    candidate = mapped.estimates
    if candidate is None:
        return None, None
    if (candidate.symbol != bundle.asset.symbol or candidate.retrieved_at is None
            or candidate.retrieved_at.tzinfo is None or not timedelta(0) <= created_at - candidate.retrieved_at < timedelta(days=1)
            or not candidate.points or not re.fullmatch(r"[0-9a-f]{64}", candidate.content_hash)):
        raise ValueError("Estimates require the same independently mapped listing")
    source = Source(id=market_source_id(candidate.source_url, candidate.content_hash, candidate.retrieved_at),
        asset_id=bundle.asset.id, url=candidate.source_url, title=TITLE, publisher="Yahoo Finance via yfinance",
        retrieved_at=candidate.retrieved_at, content_hash=candidate.content_hash,
        policy=SourcePolicy.metadata, official=False, verified=True, provenance="market_adapter", usage_scope="private_yahoo_v1")
    return AnalystEstimates(source_id=source.id, points=[{**asdict(point),
        "unit": estimate_unit(point.metric, point.currency)} for point in candidate.points]), source


def validate_estimates(bundle, data, source):
    from backend.app.market_evidence import market_source_id
    if (str(source.url) != f"https://finance.yahoo.com/quote/{bundle.asset.symbol}/analysis/"
            or source.id != data.source_id or source.asset_id != bundle.asset.id
            or source.id != market_source_id(str(source.url), source.content_hash, source.retrieved_at)
            or not re.fullmatch(r"[0-9a-f]{64}", source.content_hash)
            or source.title != TITLE or source.publisher != "Yahoo Finance via yfinance"
            or source.usage_scope != "private_yahoo_v1" or source.provenance != "market_adapter"
            or source.policy != SourcePolicy.metadata or not source.verified or source.official
            or source.excerpt or source.as_of is not None or source.published_at is not None or source.filing_publication is not None
            or not timedelta(0) <= bundle.created_at - source.retrieved_at < timedelta(days=1)):
        raise ValueError("Estimate source provenance is inconsistent")
    keys = [(PERIODS.index(p.period), p.metric) for p in data.points]
    if keys != sorted(set(keys)) or any({p.metric for p in data.points if p.period == period} != {"eps", "revenue"}
            for period in {p.period for p in data.points}):
        raise ValueError("Estimate observations must be uniquely ordered metric pairs")
    for point in data.points:
        values = [point.average, point.low, point.high]
        reason = ("period_missing" if point.period_end is None else "currency_missing" if point.currency is None
                  else "value_missing" if all(value is None for value in values) else None)
        if (point.reason != reason or point.unit != estimate_unit(point.metric, point.currency)
                or (reason is not None and any(value is not None for value in values))):
            raise ValueError("Estimate period, currency, availability or unit is inconsistent")
        for value in values:
            if value is not None:
                try:
                    if number_text(Decimal(value)) != value:
                        raise ValueError
                except (ValueError, ArithmeticError):
                    raise ValueError("Estimate must preserve a canonical finite decimal") from None
