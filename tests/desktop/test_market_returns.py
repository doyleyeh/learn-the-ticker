from datetime import date
import hashlib
import json

import pytest

from backend.app.contracts import EvidenceBundle, MarketBar
from backend.app.market_evidence import market_fingerprint
from backend.app.market_returns import METHOD, percent_change, returns_for_history, years_before
from backend.app.source_operations import shareable_view
from tests.desktop.market_fixture import market_bundle


def series(days, *, gaps=None):
    data = market_bundle().market
    # Synthetic method tests feed typed price rows. Full admission is tested separately.
    data.bars = [MarketBar(date=day, open="100", high="110", low="90", close="100", adjusted_close="90", volume="100") for day in days]
    if gaps is not None:
        data.gaps = gaps
    return data


def test_price_and_distribution_adjusted_returns_are_distinct_without_double_counted_actions():
    bundle = market_bundle()
    retained = next(row for row in bundle.market.returns if row.period == "retained")
    assert bundle.market.return_method == METHOD
    assert retained.price_percent == "27.272727" and retained.total_return_estimate_percent == "40"
    assert retained.start == date(2026, 1, 2) and retained.end == date(2026, 1, 5)
    assert retained.source_id == bundle.market.source_id
    data = bundle.market.model_copy(deep=True)
    data.actions = []
    assert returns_for_history(data) == bundle.market.returns  # Already reflected by adjusted prices.
    assert all(row.reason == "start_boundary_missing" for row in bundle.market.returns if row.period != "retained")


@pytest.mark.parametrize("start,end,expected", [
    ("100", "110", "10"), ("100", "90", "-10"), ("3", "4", "33.333333"),
    ("200000000", "200000001", "0"), ("200000000", "200000003", "0.000002"),
    ("200000000", "199999999", "0"), ("200000000", "199999997", "-0.000002"),
    ("9007199254740993", "18014398509481986", "100"),
    ("0.000000000000000001", "0.000000000000000002", "100"),
    ("1", "1", "0"), ("10000000000000000000000000000000000000000", "1", "-100"),
])
def test_rational_calculation_rounds_only_final_percent_and_normalizes_negative_zero(start, end, expected):
    assert percent_change(start, end) == expected


@pytest.mark.parametrize("start,end", [("0", "1"), ("1", "0"), ("-1", "1"), ("1", "-1")])
def test_zero_or_negative_prices_cannot_generate_returns(start, end):
    with pytest.raises(ValueError):
        percent_change(start, end)


def test_ytd_uses_prior_year_last_observation_and_never_january_first_available_as_baseline():
    data = series([date(2025, 12, 30), date(2026, 1, 2), date(2026, 1, 5)])
    data.bars[-1].close = "110"
    ytd = returns_for_history(data)[0]
    assert ytd.period == "ytd" and ytd.requested_start == date(2025, 12, 31)
    assert ytd.start == date(2025, 12, 30) and ytd.price_percent == "10"
    data.bars = data.bars[1:]
    assert returns_for_history(data)[0].reason == "start_boundary_missing"


def test_weekend_start_uses_preceding_observation_with_actual_dates_and_no_annualization():
    data = series([date(2025, 10, 3), date(2026, 10, 2)])
    row = returns_for_history(data)[1]
    # A date after the requested boundary is never substituted.
    assert row.requested_start == date(2025, 10, 2) and row.reason == "start_boundary_missing"
    data.bars[0].date = date(2025, 10, 2)
    assert returns_for_history(data)[1].reason == "history_gap"
    assert years_before(date(2024, 2, 29), 1) == date(2023, 2, 28)


def test_full_year_window_with_weekend_boundary_preserves_actual_start_and_end():
    from datetime import timedelta
    start, end = date(2024, 3, 1), date(2025, 3, 3)
    days = [start + timedelta(days=n) for n in range((end - start).days + 1)]
    days = [day for day in days if day.weekday() < 5]
    # Monday's anniversary is a Sunday; retain the actual prior Friday baseline.
    data = series(days)
    row = returns_for_history(data)[1]
    assert row.reason is None and row.start == date(2024, 3, 1) and row.end == date(2025, 3, 3)
    assert row.requested_start == date(2024, 3, 3)
    assert row.price_percent == "0"


def test_missing_rows_sparse_history_and_single_point_do_not_imply_complete_returns():
    data = series([date(2026, 1, 2), date(2026, 1, 5)], gaps=["missing_price_rows", "calendar_completeness_unverified"])
    assert all(row.reason == "missing_price_rows" and row.price_percent is None for row in returns_for_history(data))
    data.gaps = ["calendar_completeness_unverified"]
    data.bars[-1].date = date(2026, 1, 15)
    assert returns_for_history(data)[-1].reason == "history_gap"
    data.bars = data.bars[:1]
    assert returns_for_history(data)[-1].reason == "insufficient_observations"


@pytest.mark.parametrize("change", [
    lambda m: m["returns"][4].update(price_percent="1"),
    lambda m: m["returns"][4].update(total_return_estimate_percent="1"),
    lambda m: m["returns"][4].update(source_id="foreign"),
    lambda m: m["returns"][4].update(start="2026-01-01"),
    lambda m: m["returns"][0].update(reason=None, price_percent="100"),
    lambda m: m["returns"].reverse(),
    lambda m: m.update(returns=[]),
    lambda m: m.update(return_method=None),
])
def test_saved_calculations_are_rechecked_against_exact_original_inputs(change):
    payload = market_bundle().model_dump(mode="json")
    change(payload["market"])
    payload["market"]["fingerprint"] = market_fingerprint(payload["market"])
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(payload)


def test_pre_calculation_snapshot_fingerprint_survives_without_offline_generation():
    payload = market_bundle().model_dump(mode="json")
    market = payload["market"]
    market.pop("returns")
    market.pop("return_method")
    market.pop("valuations")
    market.pop("valuation_gap")
    market["fingerprint"] = hashlib.sha256(json.dumps({k: v for k, v in market.items() if k != "fingerprint"},
                                                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    original = market["fingerprint"]
    restored = EvidenceBundle.model_validate(payload)
    assert restored.market.fingerprint == original and restored.market.returns == [] and restored.market.return_method is None
    assert EvidenceBundle.model_validate_json(restored.model_dump_json()).market.fingerprint == original


def test_derived_returns_remain_private_in_cloud_context_and_export():
    from backend.app.evidence import factual_context
    bundle = market_bundle()
    assert "27.272727" not in json.dumps(factual_context(bundle))
    exported, notice = shareable_view(bundle)
    assert notice and exported.market is None and "27.272727" not in exported.model_dump_json()
