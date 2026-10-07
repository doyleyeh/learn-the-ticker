"""Typed private history admission and archive consistency, separate from prose."""
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
from zoneinfo import ZoneInfo

from backend.app.contracts import EvidenceBundle, MarketEvidence, Source, SourcePolicy, now
from backend.app.identity import ResolvedIdentity, identity_hash
from backend.app.market_history import HistoryCandidate, MarketAction, _bar, _number, _window
from backend.app.market_mapping import map_yahoo_history
from backend.app.market_returns import METHOD, returns_for_history

TITLE = "Yahoo Finance daily history (unofficial; experimental personal use only)"


def exact_decimal(value):
    try:
        return Decimal(value)
    except ArithmeticError:
        raise ValueError("Invalid market decimal") from None


def market_source_id(url, digest, retrieved_at):
    return "yahoo:" + hashlib.sha256(f"{url}\n{digest}\n{retrieved_at.isoformat()}".encode()).hexdigest()


def market_fingerprint(data):
    """Corruption detection, not an authenticity signature or a new source hash."""
    if isinstance(data, MarketEvidence):
        data = data.model_dump(mode="json")
    if data.get("valuations") is None and data.get("valuation_gap") is None:
        data = {k: v for k, v in data.items() if k not in ("valuations", "valuation_gap")}
    if data.get("estimates") is None and data.get("estimate_gap") is None:
        data = {k: v for k, v in data.items() if k not in ("estimates", "estimate_gap")}
    if data.get("return_method") is None and not data.get("returns"):
        # Pre-calculation snapshots retain their original fingerprint and no results
        # are silently generated when opening an old archive offline.
        data = {k: v for k, v in data.items() if k not in ("return_method", "returns")}
    return hashlib.sha256(json.dumps({k: v for k, v in data.items() if k != "fingerprint"},
                                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_market(bundle):
    data = bundle.market
    private = [s for s in bundle.sources if s.provenance == "market_adapter" or s.usage_scope == "private_yahoo_v1"]
    if data is None:
        if private:
            raise ValueError("Private market source requires typed history")
        return
    expected = {data.source_id} | ({data.valuations.source_id} if data.valuations else set())
    expected |= {data.estimates.source_id} if data.estimates else set()
    if (len(private) != len(expected) or {s.id for s in private} != expected
            or len({s.id for s in bundle.sources}) != len(bundle.sources)
            or not bundle.identity_verification or bundle.created_at.tzinfo is None
            or not timedelta(0) <= bundle.created_at - data.checked_at < timedelta(days=1)
            or data.fingerprint != market_fingerprint(data)):
        raise ValueError("Market evidence checkpoint or fingerprint is inconsistent")
    source = next(s for s in private if s.id == data.source_id)
    if data.valuations:
        from backend.app.valuation_evidence import validate_valuations
        if data.valuation_gap is not None or data.valuations.source_id == data.source_id:
            raise ValueError("Valuation source or availability is inconsistent")
        validate_valuations(bundle, data.valuations, next(s for s in private if s.id == data.valuations.source_id))
    if data.estimates:
        from backend.app.estimate_evidence import validate_estimates
        if data.estimate_gap is not None or data.estimates.source_id in {data.source_id, data.valuations.source_id if data.valuations else None}:
            raise ValueError("Estimate source or availability is inconsistent")
        validate_estimates(bundle, data.estimates, next(s for s in private if s.id == data.estimates.source_id))
    url = f"https://finance.yahoo.com/quote/{bundle.asset.symbol}/history/"
    if (str(source.url) != url or source.asset_id != bundle.asset.id
            or source.id != market_source_id(url, source.content_hash, source.retrieved_at)
            or source.title != TITLE or source.publisher != "Yahoo Finance via yfinance"
            or source.usage_scope != "private_yahoo_v1" or source.provenance != "market_adapter"
            or source.policy != SourcePolicy.metadata or not source.verified or source.official
            or source.excerpt or source.published_at is not None or source.filing_publication is not None
            or source.as_of != data.bars[-1].date):
        raise ValueError("Market source provenance is inconsistent")
    first, last = _window(data.requested_start.isoformat(), data.requested_end.isoformat())
    if last >= source.retrieved_at.astimezone(ZoneInfo(data.timezone)).date():
        raise ValueError("Daily history must exclude the open exchange day")
    if len(set(data.gaps)) != len(data.gaps) or "calendar_completeness_unverified" not in data.gaps:
        raise ValueError("Market coverage uncertainty must remain explicit")
    bars = []
    for row in data.bars:
        values = [getattr(row, key) for key in ("open", "high", "low", "close", "adjusted_close", "volume")]
        bar = _bar(row.date.isoformat(), [exact_decimal(value) for value in values])
        if not first <= row.date <= last or list(asdict(bar).values())[1:] != values:
            raise ValueError("Market values must be canonical exact decimals within the requested period")
        bars.append(bar)
    if [row.date for row in bars] != sorted({row.date for row in bars}):
        raise ValueError("Market days must be unique and ordered")
    actions = []
    for row in data.actions:
        parts = row.value.split("/")
        expected = 2 if row.kind == "splits" else 1
        if (not first <= row.date <= last or len(parts) != expected
                or any(_number(exact_decimal(part), positive=row.kind == "splits") != part for part in parts)):
            raise ValueError("Invalid market corporate action")
        actions.append(MarketAction(row.date.isoformat(), row.kind, row.value))
    if [(r.date, r.kind) for r in actions] != sorted({(r.date, r.kind) for r in actions}):
        raise ValueError("Corporate actions must be unique and ordered")
    history = HistoryCandidate(data.provider, bundle.asset.symbol, data.currency, data.exchange,
        data.instrument_type, data.timezone, data.name, url, source.content_hash,
        first.isoformat(), last.isoformat(), data.close_basis, tuple(bars), tuple(actions),
        tuple(data.gaps), data.exchange_label, source.retrieved_at)
    map_yahoo_history(history, ResolvedIdentity(bundle.asset, bundle.identity_verification), at=data.checked_at)
    if (data.return_method is None and data.returns) or (data.return_method == METHOD and data.returns != returns_for_history(data)):
        raise ValueError("Retained market returns differ from their exact admitted inputs and method")


def attach_market(bundle, mapped, *, personal_mode=False, created_at=None):
    """Require explicit opt-in; caller publishes a new immutable evidence version."""
    created_at = created_at or now()
    if personal_mode is not True:
        raise ValueError("Experimental private Yahoo mode requires explicit opt-in")
    history = mapped.history
    map_yahoo_history(history, mapped.instrument, at=created_at)
    if (bundle.market is not None or identity_hash(bundle.asset) != identity_hash(mapped.instrument.asset)
            or bundle.identity_verification != mapped.instrument.verification):
        raise ValueError("Market history requires a new snapshot with the same independent identity")
    if set(history.gaps) - {"instrument_mapping_unverified", "missing_price_rows"}:
        raise ValueError("Market history has unsupported admission gaps")
    sid = market_source_id(history.source_url, history.content_hash, history.retrieved_at)
    source = Source(id=sid, asset_id=bundle.asset.id, url=history.source_url, title=TITLE,
        publisher="Yahoo Finance via yfinance", retrieved_at=history.retrieved_at,
        as_of=history.bars[-1].date if history.bars else None, content_hash=history.content_hash,
        policy=SourcePolicy.metadata, official=False, verified=True,
        provenance="market_adapter", usage_scope="private_yahoo_v1")
    data = MarketEvidence(source_id=sid, checked_at=mapped.checked_at, name=history.name,
        exchange=history.exchange, exchange_label=history.exchange_label, currency=history.currency,
        requested_start=history.requested_start, requested_end=history.requested_end,
        bars=[asdict(row) for row in history.bars], actions=[asdict(row) for row in history.actions],
        gaps=[gap for gap in history.gaps if gap != "instrument_mapping_unverified"] + ["calendar_completeness_unverified"],
        fingerprint="0" * 64)
    data.return_method = METHOD
    data.returns = returns_for_history(data)
    from backend.app.valuation_evidence import attach_valuations
    data.valuations, valuation_source = attach_valuations(bundle, mapped, created_at=created_at)
    data.valuation_gap = mapped.valuation_gap
    from backend.app.estimate_evidence import attach_estimates
    data.estimates, estimate_source = attach_estimates(bundle, mapped, created_at=created_at)
    data.estimate_gap = mapped.estimate_gap
    data.fingerprint = market_fingerprint(data)
    return EvidenceBundle.model_validate({**bundle.model_dump(), "created_at": created_at,
        "market": data, "sources": [*bundle.sources, source, *[s for s in (valuation_source, estimate_source) if s]], "state": "partial"})
