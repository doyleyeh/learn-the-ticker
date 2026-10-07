"""Bounded market-history candidates. Parsing does not grant factual admission."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from backend.app.sec_financials import number_text

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 2000


class MarketDataError(ValueError):
    """Fixed diagnostic codes only; never include a response, key or URL."""


@dataclass(frozen=True)
class PriceBar:
    date: str
    open: str
    high: str
    low: str
    close: str
    adjusted_close: str
    volume: str


@dataclass(frozen=True)
class MarketAction:
    date: str
    kind: str
    value: str


@dataclass(frozen=True)
class HistoryCandidate:
    provider: str
    symbol: str
    currency: str | None
    exchange: str | None
    instrument_type: str | None
    timezone: str | None
    name: str | None
    source_url: str
    content_hash: str
    requested_start: str
    requested_end: str
    # Yahoo's close is split-adjusted even with auto_adjust=False. EODHD's is raw.
    close_basis: str
    bars: tuple[PriceBar, ...]
    actions: tuple[MarketAction, ...]
    gaps: tuple[str, ...]
    exchange_label: str | None = None
    retrieved_at: datetime | None = None


def valid_symbol(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9.^=-]{0,29}", value):
        raise MarketDataError("invalid_symbol")
    return value


def _json(raw: bytes):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise MarketDataError("response_size")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise MarketDataError("duplicate_field")
            result[key] = value
        return result
    def nonfinite(_):
        raise MarketDataError("invalid_number")
    try:
        return json.loads(raw, parse_float=Decimal, parse_constant=nonfinite, object_pairs_hook=unique)
    except MarketDataError:
        raise
    except Exception:
        raise MarketDataError("invalid_json") from None


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise MarketDataError("invalid_date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise MarketDataError("invalid_date") from None


def _window(start, end):
    first, last = _day(start), _day(end)
    if not 0 <= (last - first).days <= 6 * 366:
        raise MarketDataError("invalid_window")
    return first, last


def _number(value, *, positive=False, integer=False):
    try:
        text = number_text(value)
        number = Decimal(text)
        if number < 0 or (positive and number <= 0) or (integer and number != number.to_integral_value()):
            raise ValueError
        return text
    except ValueError:
        raise MarketDataError("invalid_number") from None


def _bar(day, values):
    if len(values) != 6:
        raise MarketDataError("price_shape")
    if any(value is None for value in values):
        return None
    values = [_number(value, positive=index != 5, integer=index == 5) for index, value in enumerate(values)]
    opened, high, low, closed = map(Decimal, values[:4])
    if not low <= min(opened, closed) <= max(opened, closed) <= high:
        raise MarketDataError("invalid_ohlc")
    return PriceBar(day, *values)


def parse_eodhd_prices(raw: bytes, symbol: str, start: str, end: str) -> HistoryCandidate:
    """One EOD response alone cannot establish instrument mapping or actions."""
    valid_symbol(symbol)
    first, last = _window(start, end)
    data = _json(raw)
    if not isinstance(data, list) or len(data) > MAX_ROWS:
        raise MarketDataError("price_shape")
    rows, seen, missing = [], set(), False
    for row in data:
        if not isinstance(row, dict) or not {"date", "open", "high", "low", "close", "adjusted_close", "volume"} <= row.keys():
            raise MarketDataError("price_shape")
        day = _day(row["date"])
        if not first <= day <= last or day in seen:
            raise MarketDataError("date_outside_window_or_duplicate")
        seen.add(day)
        bar = _bar(day.isoformat(), [row[key] for key in ("open", "high", "low", "close", "adjusted_close", "volume")])
        if bar is None:
            missing = True
        else:
            rows.append(bar)
    gaps = ["instrument_mapping_unverified", "corporate_actions_not_attached"]
    if missing:
        gaps.append("missing_price_rows")
    if not rows:
        gaps.append("no_prices")
    return HistoryCandidate("eodhd", symbol, None, None, None, None, None,
        f"https://eodhd.com/api/eod/{symbol}", hashlib.sha256(raw).hexdigest(), start, end,
        "unadjusted", tuple(sorted(rows, key=lambda row: row.date)), (), tuple(gaps))


def parse_yahoo_chart(raw: bytes, symbol: str, start: str, end: str) -> HistoryCandidate:
    """Read original chart JSON, never dataframe-rounded/auto-repaired prices."""
    valid_symbol(symbol)
    first, last = _window(start, end)
    data = _json(raw)
    try:
        chart = data["chart"]
        if chart.get("error") is not None or not isinstance(chart["result"], list) or len(chart["result"]) != 1:
            raise ValueError
        result = chart["result"][0]
        meta = result["meta"]
        if meta["symbol"] != symbol or not re.fullmatch(r"[A-Z]{3}", meta["currency"]):
            raise ValueError
        zone = ZoneInfo(meta["exchangeTimezoneName"])
        stamps = result.get("timestamp") or []
        if not isinstance(stamps, list) or len(stamps) > MAX_ROWS:
            raise ValueError
        quote = result["indicators"]["quote"]
        adjusted = result["indicators"]["adjclose"]
        if len(quote) != 1 or len(adjusted) != 1:
            raise ValueError
        arrays = [quote[0][key] for key in ("open", "high", "low", "close")]
        arrays += [adjusted[0]["adjclose"], quote[0]["volume"]]
        if any(not isinstance(array, list) or len(array) != len(stamps) for array in arrays):
            raise ValueError
        rows, seen, missing = [], set(), False
        def local_day(stamp):
            if type(stamp) is not int or not 0 <= stamp <= 253402300799:
                raise ValueError
            day = datetime.fromtimestamp(stamp, timezone.utc).astimezone(zone).date()
            if not first <= day <= last:
                raise ValueError
            return day.isoformat()
        for index, stamp in enumerate(stamps):
            day = local_day(stamp)
            if day in seen:
                raise ValueError
            seen.add(day)
            bar = _bar(day, [array[index] for array in arrays])
            if bar is None:
                missing = True
            else:
                rows.append(bar)
        actions = []
        events = result.get("events", {})
        if not isinstance(events, dict) or set(events) - {"dividends", "splits", "capitalGains"}:
            raise ValueError
        for kind, field in (("dividends", "amount"), ("splits", "numerator"), ("capitalGains", "amount")):
            items = events.get(kind, {})
            if not isinstance(items, dict) or len(items) > MAX_ROWS:
                raise ValueError
            for action in items.values():
                day = local_day(action["date"])
                amount = _number(action[field], positive=kind == "splits")
                if kind == "splits":
                    denominator = _number(action["denominator"], positive=True)
                    # Preserve ratio components; do not round a ratio into a float.
                    amount += "/" + denominator
                actions.append(MarketAction(day, kind, amount))
        if len({(row.date, row.kind) for row in actions}) != len(actions):
            raise ValueError
        for key in ("exchangeName", "fullExchangeName", "instrumentType", "shortName", "longName"):
            if key in meta and (not isinstance(meta[key], str) or not 1 <= len(meta[key]) <= 300
                                or any(unicodedata.category(char).startswith("C") for char in meta[key])):
                raise ValueError
    except MarketDataError:
        raise
    except Exception:
        raise MarketDataError("invalid_yahoo_chart") from None
    gaps = ["instrument_mapping_unverified"]
    if missing:
        gaps.append("missing_price_rows")
    if not rows:
        gaps.append("no_prices")
    return HistoryCandidate("yahoo_yfinance", symbol, meta["currency"], meta.get("exchangeName"),
        meta.get("instrumentType"), meta["exchangeTimezoneName"], meta.get("longName") or meta.get("shortName"),
        f"https://finance.yahoo.com/quote/{symbol}/history/", hashlib.sha256(raw).hexdigest(), start, end,
        "split_adjusted", tuple(sorted(rows, key=lambda row: row.date)),
        tuple(sorted(actions, key=lambda row: (row.date, row.kind))), tuple(gaps), meta.get("fullExchangeName"))
