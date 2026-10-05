"""Dated provider calculations, never a join of market prices and issuer EPS."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import hashlib

from backend.app.market_history import MarketDataError, _day, _json, _window, valid_symbol
from backend.app.sec_financials import number_text

METRICS = {
    "MarketCap": "Market capitalization", "EnterpriseValue": "Enterprise value",
    "PeRatio": "Trailing P/E", "PsRatio": "Price/sales", "PbRatio": "Price/book",
    "EnterprisesValueRevenueRatio": "EV/revenue", "EnterprisesValueEBITDARatio": "EV/EBITDA",
}
FREQUENCIES = {"annual": "12M", "quarterly": "3M", "trailing": "TTM"}
TYPES = tuple(prefix + metric for prefix in FREQUENCIES for metric in METRICS)
MAX_POINTS = 600


@dataclass(frozen=True)
class ValuationPoint:
    metric: str
    sampling: str
    date: str
    period_type: str
    currency: str | None
    value: str | None
    reason: str | None = None


@dataclass(frozen=True)
class ValuationCandidate:
    symbol: str
    requested_start: str
    requested_end: str
    content_hash: str
    points: tuple[ValuationPoint, ...]
    retrieved_at: datetime | None = None

    @property
    def source_url(self):
        return f"https://finance.yahoo.com/quote/{self.symbol}/key-statistics/"


def valuation_request(symbol, start, end):
    valid_symbol(symbol)
    first, last = _window(start, end)
    return f"https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}", {
        "symbol": symbol, "type": ",".join(TYPES),
        "period1": int(datetime.combine(first, time(), timezone.utc).timestamp()),
        "period2": int(datetime.combine(last + timedelta(days=1), time(), timezone.utc).timestamp()),
    }


def parse_valuations(raw, symbol, start, end):
    valid_symbol(symbol)
    first, last = _window(start, end)
    data = _json(raw)
    try:
        series = data["timeseries"]
        if series.get("error") is not None or not isinstance(series["result"], list) or len(series["result"]) > len(TYPES):
            raise ValueError
        points, seen_types, seen_points = [], set(), set()
        for item in series["result"]:
            meta = item["meta"]
            types = meta["type"]
            if (meta["symbol"] != [symbol] or not isinstance(types, list) or len(types) != 1
                    or types[0] not in TYPES or types[0] in seen_types):
                raise ValueError
            kind = types[0]
            seen_types.add(kind)
            prefix = next(prefix for prefix in FREQUENCIES if kind.startswith(prefix))
            metric = kind[len(prefix):]
            if set(item) - {"meta", "timestamp", kind}:
                raise ValueError
            rows = item.get(kind, [])
            if not isinstance(rows, list) or len(rows) > MAX_POINTS:
                raise ValueError
            for row in rows:
                if row is None:
                    continue
                day = _day(row["asOfDate"])
                currency = row.get("currencyCode")
                if (not first <= day <= last or row.get("periodType") != FREQUENCIES[prefix]
                        or currency not in (None, "USD")):
                    raise ValueError
                key = metric, prefix, day.isoformat()
                if key in seen_points:
                    raise ValueError
                seen_points.add(key)
                reported = row.get("reportedValue")
                if reported is not None and not isinstance(reported, dict):
                    raise ValueError
                value = reported.get("raw") if isinstance(reported, dict) else None
                text = number_text(value) if value is not None else None
                reason = "value_missing" if text is None else (
                    "currency_missing" if metric in ("MarketCap", "EnterpriseValue") and currency is None else None)
                points.append(ValuationPoint(metric, prefix, day.isoformat(), row["periodType"], currency,
                    text if reason is None else None, reason))
                if len(points) > MAX_POINTS:
                    raise ValueError
        return ValuationCandidate(symbol, start, end, hashlib.sha256(raw).hexdigest(),
            tuple(sorted(points, key=lambda point: (point.metric, point.sampling, point.date))))
    except (ValueError, TypeError, KeyError, AttributeError, StopIteration):
        raise MarketDataError("invalid_yahoo_valuations") from None
