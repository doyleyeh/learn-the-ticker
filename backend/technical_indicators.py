from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.error import URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


TECHNICAL_INDICATOR_SCHEMA_VERSION = "analysis-pack-technical-data-artifact-v1"
TECHNICAL_INDICATOR_ADAPTER_BOUNDARY = "analysis-pack-technical-indicator-adapter-v1"
YAHOO_CHART_USER_AGENT = "Mozilla/5.0 (compatible; learn-the-ticker/0.1; +https://example.local)"
YAHOO_CHART_ALLOWED_HOST = "query1.finance.yahoo.com"


class TechnicalIndicatorFetchError(RuntimeError):
    pass


class PriceSeriesFetcher(Protocol):
    no_live_external_calls: bool

    def fetch_json(self, url: str, *, timeout_seconds: int = 15) -> Any:
        ...


@dataclass(frozen=True)
class UrlLibPriceSeriesFetcher:
    no_live_external_calls: bool = False
    max_bytes: int = 2_000_000
    user_agent: str = YAHOO_CHART_USER_AGENT

    def fetch_json(self, url: str, *, timeout_seconds: int = 15) -> Any:
        _validate_yahoo_chart_url(url)
        request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/json"})
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - URL is adapter-owned and host-allowlisted.
                payload = response.read(self.max_bytes + 1)
        except URLError as exc:
            raise TechnicalIndicatorFetchError("technical_price_series_live_fetch_failed") from exc
        if len(payload) > self.max_bytes:
            raise TechnicalIndicatorFetchError("technical_price_series_payload_too_large")
        try:
            return json.loads(payload.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise TechnicalIndicatorFetchError("technical_price_series_json_invalid") from exc


def build_live_technical_data_artifact(
    tickers: list[str] | tuple[str, ...],
    *,
    bundle_id: str,
    generated_at: str,
    fetcher: PriceSeriesFetcher | None = None,
    range_label: str = "1y",
    interval: str = "1d",
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    source_fetcher = fetcher or UrlLibPriceSeriesFetcher()
    rows: dict[str, Any] = {}
    for ticker in _normalize_tickers(tickers):
        rows[ticker] = _technical_row_for_ticker(
            ticker,
            fetcher=source_fetcher,
            range_label=range_label,
            interval=interval,
            timeout_seconds=timeout_seconds,
        )

    computed = sum(1 for row in rows.values() if row.get("state") == "computed")
    status = "computed" if computed else "unavailable"
    if computed and computed < len(rows):
        status = "partial"
    return {
        "schema_version": TECHNICAL_INDICATOR_SCHEMA_VERSION,
        "adapter_boundary": TECHNICAL_INDICATOR_ADAPTER_BOUNDARY,
        "bundle_id": bundle_id,
        "generated_at": generated_at,
        "source_mode": "live_yahoo_chart",
        "no_live_external_calls": source_fetcher.no_live_external_calls,
        "technical_indicator_status": status,
        "raw_provider_payload_stored": False,
        "raw_provider_payload_exposed": False,
        "tickers": rows,
    }


def build_technical_data_artifact_from_series(
    series_by_ticker: dict[str, list[dict[str, Any]]],
    *,
    bundle_id: str,
    generated_at: str,
    no_live_external_calls: bool = True,
) -> dict[str, Any]:
    rows = {
        ticker.strip().upper(): _computed_row(
            ticker.strip().upper(),
            _normalize_price_points(points),
            no_live_external_calls=no_live_external_calls,
            source_url=f"local://technical-fixture/{ticker.strip().upper()}",
        )
        for ticker, points in series_by_ticker.items()
        if ticker.strip()
    }
    computed = sum(1 for row in rows.values() if row.get("state") == "computed")
    return {
        "schema_version": TECHNICAL_INDICATOR_SCHEMA_VERSION,
        "adapter_boundary": TECHNICAL_INDICATOR_ADAPTER_BOUNDARY,
        "bundle_id": bundle_id,
        "generated_at": generated_at,
        "source_mode": "fixture_price_series",
        "no_live_external_calls": no_live_external_calls,
        "technical_indicator_status": "computed" if computed == len(rows) and rows else "partial",
        "raw_provider_payload_stored": False,
        "raw_provider_payload_exposed": False,
        "tickers": rows,
    }


def fetch_yahoo_price_series(
    ticker: str,
    *,
    fetcher: PriceSeriesFetcher | None = None,
    range_label: str = "1y",
    interval: str = "1d",
    timeout_seconds: int = 15,
) -> list[dict[str, Any]]:
    source_fetcher = fetcher or UrlLibPriceSeriesFetcher()
    url = _yahoo_chart_url(ticker, range_label=range_label, interval=interval)
    payload = source_fetcher.fetch_json(url, timeout_seconds=timeout_seconds)
    return parse_yahoo_chart_price_points(payload)


def parse_yahoo_chart_price_points(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    result = ((payload.get("chart") or {}).get("result") or [])
    if not result or not isinstance(result[0], dict):
        return []
    item = result[0]
    timestamps = item.get("timestamp") if isinstance(item.get("timestamp"), list) else []
    quote_payloads = ((item.get("indicators") or {}).get("quote") or [])
    quote_payload = quote_payloads[0] if quote_payloads and isinstance(quote_payloads[0], dict) else {}
    points: list[dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        close = _list_number(quote_payload.get("close"), index)
        high = _list_number(quote_payload.get("high"), index)
        low = _list_number(quote_payload.get("low"), index)
        open_value = _list_number(quote_payload.get("open"), index)
        volume = _list_number(quote_payload.get("volume"), index)
        if not isinstance(timestamp, (int, float)) or close is None or high is None or low is None:
            continue
        points.append(
            {
                "date": datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat(),
                "open": open_value,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )
    return _normalize_price_points(points)


def compute_technical_indicators(points: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = _normalize_price_points(points)
    closes = [point["close"] for point in normalized]
    highs = [point["high"] for point in normalized]
    lows = [point["low"] for point in normalized]
    volumes = [point.get("volume") for point in normalized]
    if len(closes) < 35:
        raise TechnicalIndicatorFetchError("technical_price_series_too_short")

    kd = _kd(highs, lows, closes)
    macd = _macd(closes)
    moving_averages = {str(period): _last(_sma(closes, period)) for period in (5, 10, 20, 50, 200)}
    moving_averages = {key: _round(value) for key, value in moving_averages.items() if value is not None}
    bias = {
        key: _round(((closes[-1] - value) / value) * 100.0)
        for key, value in moving_averages.items()
        if value
    }
    return {
        "close": _round(closes[-1]),
        "as_of_date": normalized[-1]["date"],
        "point_count": len(normalized),
        "KD": kd,
        "RSI": {"period": 14, "value": _round(_rsi(closes, 14))},
        "MACD": macd,
        "BIAS": bias,
        "DMI_ADX": _dmi_adx(highs, lows, closes, 14),
        "moving_averages": moving_averages,
        "volume_change": _volume_change(volumes),
    }


def _technical_row_for_ticker(
    ticker: str,
    *,
    fetcher: PriceSeriesFetcher,
    range_label: str,
    interval: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    source_url = _yahoo_chart_url(ticker, range_label=range_label, interval=interval)
    try:
        points = fetch_yahoo_price_series(
            ticker,
            fetcher=fetcher,
            range_label=range_label,
            interval=interval,
            timeout_seconds=timeout_seconds,
        )
        return _computed_row(
            ticker,
            points,
            no_live_external_calls=fetcher.no_live_external_calls,
            source_url=source_url,
        )
    except Exception as exc:
        return {
            "state": "unavailable",
            "ticker": ticker,
            "source_mode": "live_yahoo_chart",
            "reason": type(exc).__name__,
            "raw_provider_payload_stored": False,
            "raw_provider_payload_exposed": False,
            "source": _technical_source(ticker, source_url, no_live_external_calls=fetcher.no_live_external_calls),
        }


def _computed_row(
    ticker: str,
    points: list[dict[str, Any]],
    *,
    no_live_external_calls: bool,
    source_url: str,
) -> dict[str, Any]:
    indicators = compute_technical_indicators(points)
    return {
        "state": "computed",
        "ticker": ticker,
        "source_mode": "live_yahoo_chart" if not no_live_external_calls else "fixture_price_series",
        "raw_provider_payload_stored": False,
        "raw_provider_payload_exposed": False,
        "source": _technical_source(ticker, source_url, no_live_external_calls=no_live_external_calls),
        **indicators,
    }


def _technical_source(ticker: str, source_url: str, *, no_live_external_calls: bool) -> dict[str, Any]:
    source_document_id = f"src_technical_{ticker.lower()}_price_series"
    return {
        "source_document_id": source_document_id,
        "citation_id": f"c_technical_{ticker.lower()}_price_series",
        "publisher": "Yahoo Finance" if not no_live_external_calls else "Local technical fixture",
        "title": f"{ticker} OHLCV price-series metadata",
        "url": source_url,
        "source_use_policy": "summary_allowed",
        "storage_mode": "metadata_and_computed_indicators_only",
    }


def _kd(highs: list[float], lows: list[float], closes: list[float], period: int = 9) -> dict[str, Any]:
    k_value = 50.0
    d_value = 50.0
    for index in range(len(closes)):
        if index + 1 < period:
            continue
        high_window = highs[index + 1 - period : index + 1]
        low_window = lows[index + 1 - period : index + 1]
        highest = max(high_window)
        lowest = min(low_window)
        rsv = 50.0 if highest == lowest else ((closes[index] - lowest) / (highest - lowest)) * 100.0
        k_value = (2.0 / 3.0) * k_value + (1.0 / 3.0) * rsv
        d_value = (2.0 / 3.0) * d_value + (1.0 / 3.0) * k_value
    return {"period": period, "K": _round(k_value), "D": _round(d_value)}


def _rsi(closes: list[float], period: int) -> float | None:
    if len(closes) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        change = closes[index] - closes[index - 1]
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for index in range(period + 1, len(closes)):
        change = closes[index] - closes[index - 1]
        avg_gain = ((avg_gain * (period - 1)) + max(change, 0.0)) / period
        avg_loss = ((avg_loss * (period - 1)) + abs(min(change, 0.0))) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _macd(closes: list[float]) -> dict[str, Any]:
    ema12 = _ema_series(closes, 12)
    ema26 = _ema_series(closes, 26)
    diffs = [
        fast - slow
        for fast, slow in zip(ema12, ema26, strict=False)
        if fast is not None and slow is not None
    ]
    signal = _ema_series(diffs, 9)
    macd_value = _last(diffs)
    signal_value = _last(signal)
    histogram = None if macd_value is None or signal_value is None else macd_value - signal_value
    return {
        "fast_ema": 12,
        "slow_ema": 26,
        "signal_ema": 9,
        "macd": _round(macd_value),
        "signal": _round(signal_value),
        "histogram": _round(histogram),
    }


def _dmi_adx(highs: list[float], lows: list[float], closes: list[float], period: int) -> dict[str, Any]:
    trs: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for index in range(1, len(closes)):
        high_diff = highs[index] - highs[index - 1]
        low_diff = lows[index - 1] - lows[index]
        plus_dm.append(high_diff if high_diff > low_diff and high_diff > 0 else 0.0)
        minus_dm.append(low_diff if low_diff > high_diff and low_diff > 0 else 0.0)
        trs.append(max(highs[index] - lows[index], abs(highs[index] - closes[index - 1]), abs(lows[index] - closes[index - 1])))
    atr = _wilder(trs, period)
    plus_smoothed = _wilder(plus_dm, period)
    minus_smoothed = _wilder(minus_dm, period)
    plus_di: list[float | None] = []
    minus_di: list[float | None] = []
    dx: list[float] = []
    for atr_value, plus_value, minus_value in zip(atr, plus_smoothed, minus_smoothed, strict=False):
        if not atr_value:
            plus_di.append(None)
            minus_di.append(None)
            continue
        pdi = 100.0 * (plus_value or 0.0) / atr_value
        mdi = 100.0 * (minus_value or 0.0) / atr_value
        plus_di.append(pdi)
        minus_di.append(mdi)
        total = pdi + mdi
        if total:
            dx.append(100.0 * abs(pdi - mdi) / total)
    adx = _wilder(dx, period)
    return {
        "period": period,
        "plus_di": _round(_last(plus_di)),
        "minus_di": _round(_last(minus_di)),
        "ADX": _round(_last(adx)),
    }


def _volume_change(volumes: list[float | None]) -> dict[str, Any]:
    valid = [volume for volume in volumes if volume is not None]
    if len(valid) < 2 or not valid[-2]:
        return {"latest": _round(valid[-1]) if valid else None, "previous": None, "percent_change": None}
    return {
        "latest": _round(valid[-1]),
        "previous": _round(valid[-2]),
        "percent_change": _round(((valid[-1] - valid[-2]) / valid[-2]) * 100.0),
    }


def _sma(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < period:
            result.append(None)
            continue
        result.append(sum(values[index + 1 - period : index + 1]) / period)
    return result


def _ema_series(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    multiplier = 2.0 / (period + 1)
    ema: float | None = None
    for index, value in enumerate(values):
        if index + 1 < period:
            result.append(None)
            continue
        if ema is None:
            ema = sum(values[index + 1 - period : index + 1]) / period
        else:
            ema = (value - ema) * multiplier + ema
        result.append(ema)
    return result


def _wilder(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    smoothed: float | None = None
    for index, value in enumerate(values):
        if index + 1 < period:
            result.append(None)
            continue
        if smoothed is None:
            smoothed = sum(values[index + 1 - period : index + 1]) / period
        else:
            smoothed = ((smoothed * (period - 1)) + value) / period
        result.append(smoothed)
    return result


def _normalize_price_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for point in points:
        close = _number(point.get("close"))
        high = _number(point.get("high"))
        low = _number(point.get("low"))
        if close is None or high is None or low is None:
            continue
        normalized.append(
            {
                "date": str(point.get("date") or point.get("timestamp") or ""),
                "open": _number(point.get("open")),
                "high": high,
                "low": low,
                "close": close,
                "volume": _number(point.get("volume")),
            }
        )
    return normalized


def _normalize_tickers(tickers: list[str] | tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        clean = ticker.strip().upper()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized


def _list_number(values: Any, index: int) -> float | None:
    if not isinstance(values, list) or index >= len(values):
        return None
    return _number(values[index])


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _last(values: list[float | None]) -> float | None:
    for value in reversed(values):
        if value is not None:
            return value
    return None


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _yahoo_chart_url(ticker: str, *, range_label: str, interval: str) -> str:
    return (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker.strip().upper())}"
        f"?range={quote(range_label)}&interval={quote(interval)}"
    )


def _validate_yahoo_chart_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise TechnicalIndicatorFetchError("technical_source_url_invalid") from exc
    if parsed.scheme != "https":
        raise TechnicalIndicatorFetchError("technical_source_url_scheme_blocked")
    if (parsed.hostname or "").lower() != YAHOO_CHART_ALLOWED_HOST:
        raise TechnicalIndicatorFetchError("technical_source_host_blocked")
