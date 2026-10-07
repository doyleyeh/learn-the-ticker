"""Original analyst consensus candidates; forecasts never become reported facts."""
from dataclasses import dataclass
from datetime import datetime
import hashlib

from backend.app.market_history import MarketDataError, _day, _json, valid_symbol
from backend.app.sec_financials import number_text

PERIODS = ("0q", "+1q", "0y", "+1y")
METRICS = {"eps": ("earningsEstimate", "earningsCurrency"), "revenue": ("revenueEstimate", "revenueCurrency")}


@dataclass(frozen=True)
class EstimatePoint:
    metric: str
    period: str
    period_end: str | None
    currency: str | None
    average: str | None
    low: str | None
    high: str | None
    analysts: int | None
    reason: str | None = None


@dataclass(frozen=True)
class EstimateCandidate:
    symbol: str
    content_hash: str
    points: tuple[EstimatePoint, ...]
    retrieved_at: datetime | None = None

    @property
    def source_url(self):
        return f"https://finance.yahoo.com/quote/{self.symbol}/analysis/"


def estimate_request(symbol):
    valid_symbol(symbol)
    return f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}", {
        "modules": "earningsTrend", "corsDomain": "finance.yahoo.com", "formatted": "false", "symbol": symbol,
    }


def raw_value(data, key):
    item = data.get(key)
    if item is None:
        return None
    if not isinstance(item, dict):
        raise ValueError
    value = item.get("raw")
    return number_text(value) if value is not None else None


def parse_estimates(raw, symbol):
    """Only per-row currency and raw numbers; no formatted amounts or price currency."""
    valid_symbol(symbol)
    data = _json(raw)
    try:
        summary = data["quoteSummary"]
        result = summary["result"]
        if summary.get("error") is not None or not isinstance(result, list) or len(result) != 1:
            raise ValueError
        item = result[0]
        if set(item) - {"earningsTrend", "symbol"} or item.get("symbol", symbol) != symbol:
            raise ValueError
        trend = item["earningsTrend"]
        if trend.get("symbol", symbol) != symbol:
            raise ValueError
        rows = trend["trend"]
        if not isinstance(rows, list) or len(rows) > 6:
            raise ValueError
        points, seen = [], set()
        for row in rows:
            period = row["period"]
            if period not in (*PERIODS, "+5y", "-5y") or period in seen:
                raise ValueError
            seen.add(period)
            if period not in PERIODS:
                continue  # Long-term growth is outside this dataset.
            end = row.get("endDate")
            end = _day(end).isoformat() if end is not None else None
            for metric, (field, currency_field) in METRICS.items():
                values = row.get(field)
                if values is None:
                    values = {}
                if not isinstance(values, dict):
                    raise ValueError
                currency = values.get(currency_field)
                if currency not in (None, "USD"):
                    raise ValueError  # Current independent market admission is USD only.
                average, low, high = (raw_value(values, key) for key in ("avg", "low", "high"))
                count = raw_value(values, "numberOfAnalysts")
                if count is not None and (not count.isdigit() or not 0 <= int(count) <= 10000):
                    raise ValueError
                analysts = int(count) if count is not None else None
                reason = ("period_missing" if end is None else "currency_missing" if currency is None
                          else "value_missing" if average is None and low is None and high is None else None)
                points.append(EstimatePoint(metric, period, end, currency,
                    average if reason is None else None, low if reason is None else None,
                    high if reason is None else None, analysts, reason))
        return EstimateCandidate(symbol, hashlib.sha256(raw).hexdigest(),
            tuple(sorted(points, key=lambda p: (PERIODS.index(p.period), p.metric))))
    except (ValueError, TypeError, KeyError, AttributeError):
        raise MarketDataError("invalid_yahoo_estimates") from None
