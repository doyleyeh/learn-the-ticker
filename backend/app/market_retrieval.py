"""Explicit EODHD-first history selection; no library write or numerical admission."""
from dataclasses import dataclass
from datetime import date, timedelta

from backend.app.market_history import HistoryCandidate, MarketDataError, _window, parse_eodhd_prices, valid_symbol
from backend.app.market_transport import fetch_eodhd_prices
from backend.app.yfinance_worker import fetch_yahoo_history


@dataclass(frozen=True)
class HistoryRetrieval:
    primary: HistoryCandidate | None
    selected: HistoryCandidate | None
    gaps: tuple[str, ...]
    yahoo_requests: int = 0


def covers_boundaries(candidate, start, end):
    """Boundary heuristic only: it does not prove trading-calendar completeness."""
    first, last = _window(start, end)
    return (bool(candidate.bars) and "missing_price_rows" not in candidate.gaps
            and date.fromisoformat(candidate.bars[0].date) <= first + timedelta(days=7)
            and date.fromisoformat(candidate.bars[-1].date) >= last - timedelta(days=7))


async def retrieve_history(symbol, start, end, *, credential, eodhd_start,
                           eodhd_fetch=fetch_eodhd_prices, yahoo_fetch=fetch_yahoo_history):
    """Developer qualification lane. Primary window must match the known plan.

    The caller explicitly selects the symbol pair; independent listing concordance
    is still required before either result can be admitted. No denied/quota request
    triggers a fallback. A full Yahoo candidate replaces, never splices, the series.
    """
    valid_symbol(symbol)
    first, last = _window(start, end)
    entitled, _ = _window(eodhd_start, end)
    if entitled < first or entitled > last or (last - entitled).days > 366:
        raise MarketDataError("invalid_window")
    primary, gaps = None, []
    if credential is not None:
        try:
            raw = eodhd_fetch(symbol + ".US", eodhd_start, end, credential)
            primary = parse_eodhd_prices(raw, symbol + ".US", eodhd_start, end)
        except MarketDataError as exc:
            # No equivalent extraction after denial, quota or ambiguous failure.
            return HistoryRetrieval(None, None, ("eodhd:" + str(exc),))
        if covers_boundaries(primary, start, end):
            return HistoryRetrieval(primary, primary, ())
        gaps.append("eodhd:requested_history_incomplete")
    else:
        gaps.append("eodhd:credential_missing")
    try:
        fallback, requests = await yahoo_fetch(symbol, start, end)
    except MarketDataError as exc:
        return HistoryRetrieval(primary, primary, tuple(gaps + ["yahoo:" + str(exc)]))
    if not covers_boundaries(fallback, start, end):
        gaps.append("yahoo:requested_history_incomplete")
    return HistoryRetrieval(primary, fallback, tuple(gaps), requests)
