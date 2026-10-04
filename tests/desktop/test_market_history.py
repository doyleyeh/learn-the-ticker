"""Synthetic original-response fixtures; no market or subscription requests."""
import copy
import hashlib
import json
from datetime import datetime, timezone

import pytest

from backend.app.market_history import MAX_BYTES, MarketDataError, parse_eodhd_prices, parse_yahoo_chart

START, END = "2026-01-01", "2026-01-31"
STAMP = int(datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc).timestamp())


def yahoo():
    return {"chart": {"error": None, "result": [{
        "meta": {"symbol": "TEST", "currency": "USD", "exchangeTimezoneName": "America/New_York",
                 "exchangeName": "NMS", "instrumentType": "EQUITY", "longName": "Synthetic issuer"},
        "timestamp": [STAMP],
        "indicators": {"quote": [{"open": [10], "high": [12], "low": [9], "close": [11], "volume": [100]}],
                       "adjclose": [{"adjclose": [10]}]},
        "events": {"dividends": {str(STAMP): {"date": STAMP, "amount": 0.5}},
                   "splits": {str(STAMP): {"date": STAMP, "numerator": 3, "denominator": 2}}},
    }]}}


def result(data):
    return data["chart"]["result"][0]


def eod():
    return [{"date": "2026-01-02", "open": 10, "high": 12, "low": 9, "close": 11,
             "adjusted_close": 10, "volume": 100}]


def parse(data, vendor="yahoo"):
    raw = json.dumps(data).encode() if not isinstance(data, bytes) else data
    return (parse_yahoo_chart(raw, "TEST", START, END) if vendor == "yahoo"
            else parse_eodhd_prices(raw, "TEST.US", START, END))


def test_original_decimals_hash_actions_and_provider_adjustments_stay_distinct():
    raw = json.dumps(yahoo()).encode().replace(b'"volume": [100]', b'"volume": [9007199254740993]')
    raw = raw.replace(b'"amount": 0.5', b'"amount": 0.123456789012345678')
    value = parse(raw)
    assert value.bars[0].volume == "9007199254740993"
    assert value.actions[0].value == "0.123456789012345678"
    assert value.actions[1].value == "3/2"
    assert value.content_hash == hashlib.sha256(raw).hexdigest()
    assert value.close_basis == "split_adjusted" and value.currency == "USD"
    assert value.gaps == ("instrument_mapping_unverified",)
    other = parse(eod(), "eodhd")
    assert other.close_basis == "unadjusted" and other.currency is None
    assert "corporate_actions_not_attached" in other.gaps
    assert other.bars[0].adjusted_close == "10" and other.bars[0].close == "11"
    assert "?" not in other.source_url and "?" not in value.source_url


@pytest.mark.parametrize("vendor", ["yahoo", "eodhd"])
@pytest.mark.parametrize("bad", [b"NaN", b"Infinity", b"1e99999999", b"1e-99999999", b"true", b'"11"', b"-1", b"0"])
def test_invalid_prices_cannot_be_candidates(vendor, bad):
    raw = json.dumps(yahoo() if vendor == "yahoo" else eod()).encode()
    raw = raw.replace(b'"close": [11]', b'"close": [' + bad + b']') if vendor == "yahoo" else raw.replace(b'"close": 11', b'"close": ' + bad)
    with pytest.raises(MarketDataError):
        parse(raw, vendor)


@pytest.mark.parametrize("vendor", ["yahoo", "eodhd"])
def test_missing_points_are_gaps_and_never_filled(vendor):
    data = yahoo() if vendor == "yahoo" else eod()
    if vendor == "yahoo":
        result(data)["indicators"]["adjclose"][0]["adjclose"] = [None]
    else:
        data[0]["close"] = None
    value = parse(data, vendor)
    assert not value.bars and {"missing_price_rows", "no_prices"} <= set(value.gaps)


@pytest.mark.parametrize("vendor", ["yahoo", "eodhd"])
def test_inconsistent_ohlc_and_fractional_volume_are_rejected(vendor):
    data = yahoo() if vendor == "yahoo" else eod()
    for key, invalid in (("high", 9), ("low", 11), ("volume", 1.5)):
        modified = copy.deepcopy(data)
        if vendor == "yahoo":
            result(modified)["indicators"]["quote"][0][key] = [invalid]
        else:
            modified[0][key] = invalid
        with pytest.raises(MarketDataError):
            parse(modified, vendor)


@pytest.mark.parametrize("vendor", ["yahoo", "eodhd"])
@pytest.mark.parametrize("raw", [b" " * (MAX_BYTES + 1), b'{"x":1,"x":2}', b"[" * 2000 + b"]" * 2000, b"null", b"{}"],
                         ids=["oversized", "duplicate-fields", "deep", "null", "object"])
def test_bounded_strict_json(vendor, raw):
    with pytest.raises(MarketDataError):
        parse(raw, vendor)


@pytest.mark.parametrize("changes", [
    {"symbol": "OTHER"}, {"currency": "USd"}, {"currency": None}, {"exchangeTimezoneName": "not-a-zone"},
    {"exchangeName": []}, {"instrumentType": ""}, {"longName": "a" * 301},
])
def test_yahoo_identity_metadata_must_match_and_remains_unverified(changes):
    data = yahoo()
    result(data)["meta"].update(changes)
    with pytest.raises(MarketDataError):
        parse(data)


@pytest.mark.parametrize("stamp", [True, 1.5, 253402300800, STAMP + 32 * 86400, STAMP - 3 * 86400])
def test_timestamp_type_range_and_request_window(stamp):
    data = yahoo()
    result(data)["timestamp"] = [stamp]
    with pytest.raises(MarketDataError):
        parse(data)


def test_exchange_local_date_is_used_instead_of_utc_date():
    data = yahoo()
    result(data)["timestamp"] = [int(datetime(2026, 1, 3, 1, tzinfo=timezone.utc).timestamp())]
    assert parse(data).bars[0].date == "2026-01-02"


def test_array_mismatch_duplicate_day_and_duplicate_actions_fail_closed():
    data = yahoo()
    result(data)["indicators"]["quote"][0]["low"] = []
    with pytest.raises(MarketDataError):
        parse(data)
    data = yahoo()
    result(data)["timestamp"] *= 2
    for entry in result(data)["indicators"].values():
        for values in entry[0].values():
            values *= 2
    with pytest.raises(MarketDataError):
        parse(data)
    data = yahoo()
    result(data)["events"]["dividends"]["other"] = {"date": STAMP, "amount": 1}
    with pytest.raises(MarketDataError):
        parse(data)


def test_invalid_action_ratios_and_unexpected_events_are_not_ignored():
    for changes in ({"denominator": 0}, {"numerator": -1}, {"date": True}):
        data = yahoo()
        result(data)["events"]["splits"][str(STAMP)].update(changes)
        with pytest.raises(MarketDataError):
            parse(data)
    data = yahoo()
    result(data)["events"]["unrecognized"] = {}
    with pytest.raises(MarketDataError):
        parse(data)


def test_eodhd_duplicates_wrong_dates_and_empty_results_are_explicit():
    for data in (eod() * 2, [dict(eod()[0], date="2026-02-01")], [dict(eod()[0], date="2026-1-2")]):
        with pytest.raises(MarketDataError):
            parse(data, "eodhd")
    assert "no_prices" in parse([], "eodhd").gaps


@pytest.mark.parametrize("symbol,start,end", [
    ("../../secret", START, END), ("TEST?api_token=secret", START, END),
    ("TEST", END, START), ("TEST", "2000-01-01", END), ("TEST", "2026-02-30", END),
])
def test_requests_are_bounded_before_parsing(symbol, start, end):
    with pytest.raises(MarketDataError):
        parse_yahoo_chart(json.dumps(yahoo()).encode(), symbol, start, end)
