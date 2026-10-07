"""Source-linked return snapshots; no prices invented or corporate actions reapplied."""
from datetime import date, timedelta
from fractions import Fraction

from backend.app.contracts import MarketReturn

METHOD = "yahoo-adjusted-ratio-v1"
METHOD_DESCRIPTION = (
    "Price return uses split-adjusted close: (end / start - 1) × 100. "
    "Total return estimate uses Yahoo's split/distribution-adjusted close ratio, "
    "a provider-adjusted reinvestment proxy, not a reconstruction of cash reinvested on payment dates. "
    "Dividends and split ratios are not added again. Both use the same observed start/end dates "
    "and exclude fees, taxes and currency conversion. Percentages round to six decimal places, ties to even. "
    "Source adjustment errors remain possible; no repair or imputation is applied."
)


def years_before(day, years):
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def percent_change(start, end):
    """Exact rational arithmetic until the final six-decimal percentage rounding."""
    initial, final = Fraction(start), Fraction(end)
    if initial <= 0 or final <= 0:
        raise ValueError("Returns require positive admitted endpoint prices")
    scaled = (final / initial - 1) * 100_000_000
    sign = -1 if scaled < 0 else 1
    quotient, remainder = divmod(abs(scaled.numerator), scaled.denominator)
    if 2 * remainder > scaled.denominator or (2 * remainder == scaled.denominator and quotient % 2):
        quotient += 1
    whole, decimal = divmod(quotient, 1_000_000)
    value = str(whole) + ("." + f"{decimal:06d}".rstrip("0") if decimal else "")
    return ("-" if sign < 0 and quotient else "") + value


def returns_for_history(data):
    """Caller validates typed history first; results are rechecked before persistence."""
    if not data.bars:
        raise ValueError("No admitted price history")
    last = data.bars[-1]
    windows = [("ytd", date(last.date.year, 1, 1) - timedelta(days=1)),
               *[(f"{years}y", years_before(last.date, years)) for years in (1, 3, 5)],
               ("retained", data.bars[0].date)]
    result = []
    for period, requested in windows:
        before = [bar for bar in data.bars if bar.date <= requested]
        first = before[-1] if before and (requested - before[-1].date).days <= 7 else None
        selected = [bar for bar in data.bars if first and bar.date >= first.date]
        reason = ("missing_price_rows" if "missing_price_rows" in data.gaps else
                  "start_boundary_missing" if first is None else
                  "insufficient_observations" if len(selected) < 2 else
                  "history_gap" if any((right.date - left.date).days > 7 for left, right in zip(selected, selected[1:])) else None)
        result.append(MarketReturn(period=period, source_id=data.source_id, requested_start=requested,
            start=first.date if first else None, end=last.date, reason=reason,
            price_percent=percent_change(first.close, last.close) if reason is None else None,
            total_return_estimate_percent=percent_change(first.adjusted_close, last.adjusted_close) if reason is None else None))
    return result
