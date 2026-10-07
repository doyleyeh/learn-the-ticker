"""Original references and private admission for supplied valuation observations."""
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal
import re
from zoneinfo import ZoneInfo

from backend.app.contracts import MarketValuations, Source, SourcePolicy
from backend.app.market_history import _window
from backend.app.market_valuations import FREQUENCIES
from backend.app.sec_financials import number_text

TITLE = "Yahoo Finance valuation measures (provider calculations; experimental personal use only)"


def attach_valuations(bundle, mapped, *, created_at):
    from backend.app.market_evidence import market_source_id
    candidate = mapped.valuations
    if candidate is None:
        return None, None
    if (candidate.symbol != bundle.asset.symbol or candidate.retrieved_at is None
            or candidate.retrieved_at.tzinfo is None or not timedelta(0) <= created_at - candidate.retrieved_at < timedelta(days=1)
            or not candidate.points or not re.fullmatch(r"[0-9a-f]{64}", candidate.content_hash)):
        raise ValueError("Valuation candidate does not match the independently mapped listing")
    source = Source(id=market_source_id(candidate.source_url, candidate.content_hash, candidate.retrieved_at),
        asset_id=bundle.asset.id, url=candidate.source_url, title=TITLE, publisher="Yahoo Finance via yfinance",
        retrieved_at=candidate.retrieved_at, as_of=max(p.date for p in candidate.points),
        content_hash=candidate.content_hash, policy=SourcePolicy.metadata, official=False, verified=True,
        provenance="market_adapter", usage_scope="private_yahoo_v1")
    return MarketValuations(source_id=source.id, requested_start=candidate.requested_start,
        requested_end=candidate.requested_end, points=[asdict(point) for point in candidate.points]), source


def validate_valuations(bundle, data, source):
    from backend.app.market_evidence import market_source_id
    first, last = _window(data.requested_start.isoformat(), data.requested_end.isoformat())
    if (str(source.url) != f"https://finance.yahoo.com/quote/{bundle.asset.symbol}/key-statistics/"
            or source.id != data.source_id or source.asset_id != bundle.asset.id
            or source.id != market_source_id(str(source.url), source.content_hash, source.retrieved_at)
            or not re.fullmatch(r"[0-9a-f]{64}", source.content_hash)
            or source.title != TITLE or source.publisher != "Yahoo Finance via yfinance"
            or source.usage_scope != "private_yahoo_v1" or source.provenance != "market_adapter"
            or source.policy != SourcePolicy.metadata or not source.verified or source.official
            or source.excerpt or source.published_at is not None or source.filing_publication is not None
            or not timedelta(0) <= bundle.created_at - source.retrieved_at < timedelta(days=1)
            or last >= source.retrieved_at.astimezone(ZoneInfo("America/New_York")).date()
            or first < bundle.market.requested_start or last > bundle.market.requested_end
            or source.as_of != max(row.date for row in data.points)):
        raise ValueError("Valuation source provenance is inconsistent")
    keys = [(p.metric, p.sampling, p.date) for p in data.points]
    if keys != sorted(set(keys)):
        raise ValueError("Valuation observations must be uniquely ordered")
    for point in data.points:
        cash = point.metric in ("MarketCap", "EnterpriseValue")
        if (not first <= point.date <= last or point.period_type != FREQUENCIES[point.sampling]
                or (point.value is not None and (point.reason is not None or (cash and point.currency is None)))
                or (point.value is None and point.reason is None)
                or (point.reason == "currency_missing" and (not cash or point.currency is not None))):
            raise ValueError("Valuation date, period or unit is inconsistent")
        if point.value is not None:
            try:
                if number_text(Decimal(point.value)) != point.value:
                    raise ValueError
            except (ValueError, ArithmeticError):
                raise ValueError("Valuation must preserve a canonical finite decimal") from None
