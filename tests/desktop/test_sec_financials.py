import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from backend.app.sec_financials import concept_url, default_history, parse_concept

AT = datetime(2026, 10, 4, tzinfo=timezone.utc)


def entry(**kwargs):
    return {"start": "2025-01-01", "end": "2025-12-31", "val": 100, "accn": "0000009999-26-000001",
            "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2026-02-01", **kwargs}


def raw(rows=None, *, concept="Revenues", units=None, **kwargs):
    return json.dumps({"cik": 1, "taxonomy": "us-gaap", "tag": concept, "entityName": "Synthetic issuer",
                       "label": "Untrusted display label", "description": "Untrusted description",
                       "units": units if units is not None else {"USD": [entry()] if rows is None else rows}, **kwargs}).encode()


def parse(value, concept="Revenues"):
    return parse_concept(value, cik="0000000001", concept=concept, retrieved_at=AT)


def test_issuer_concept_unit_and_filing_provenance_are_preserved_without_floats():
    value = raw().replace(b'"val": 100', b'"val": 9007199254740993.125')
    report = parse(value)
    row = report.observations[0]
    assert row.value == "9007199254740993.125" and row.unit == "USD"
    assert row.cik == "0000000001" and row.concept == "us-gaap:Revenues"
    assert row.accession.startswith("0000009999")  # Filing agent is not the issuer.
    assert row.period == "annual" and row.revision == "current" and row.retrieved_at == AT
    assert row.source_url == concept_url(row.cik, "Revenues") and len(row.source_hash) == 64
    assert "Untrusted" not in repr(report)


@pytest.mark.parametrize("changes", [
    {"cik": 2}, {"cik": True}, {"taxonomy": "custom"}, {"tag": "NetIncomeLoss"},
    {"entityName": ""}, {"units": []},
])
def test_wrong_issuer_concept_and_invalid_envelopes_fail_closed(changes):
    with pytest.raises(ValueError):
        parse(raw(**changes))


@pytest.mark.parametrize("changes", [
    {"val": True}, {"val": "100"}, {"val": None}, {"accn": "../file"},
    {"filed": "2030-01-01"}, {"end": "2026-03-01"}, {"start": "2026-01-01"},
    {"end": "2025-02-30"}, {"filed": "2026-2-1"}, {"fy": True}, {"fy": 2500}, {"fp": "Q5"},
    {"fp": []}, {"form": []}, {"form": None},
])
def test_malformed_numbers_dates_and_provenance_cannot_enter_observations(changes):
    with pytest.raises(ValueError):
        parse(raw([entry(**changes)]))


@pytest.mark.parametrize("number", [b"NaN", b"Infinity", b"-Infinity", b"1e1000000000", b"1e-1000000000", b"1e9999999999999999999999999"])
def test_nonfinite_or_expansion_numbers_fail_before_decimal_formatting(number):
    with pytest.raises(ValueError):
        parse(raw().replace(b'"val": 100', b'"val": ' + number))


def test_duplicate_json_fields_and_oversized_documents_are_rejected():
    with pytest.raises(ValueError):
        parse(raw().replace(b'"cik": 1', b'"cik": 1,"cik": 1'))
    with pytest.raises(ValueError):
        parse(b" " * 2_000_001)
    with pytest.raises(ValueError):
        parse_concept(raw(), cik="0000000001", concept="Revenues", retrieved_at=AT.replace(tzinfo=None))
    with pytest.raises(ValueError):
        parse(b"[" * 2000 + b"0" + b"]" * 2000)


def test_extreme_revision_expansion_is_bounded():
    with pytest.raises(ValueError):
        parse(raw([entry(accn=f"0000009999-26-{index:06}") for index in range(129)]))


def test_instant_duration_and_year_to_date_are_not_inferred_from_fiscal_labels():
    quarter = entry(start="2025-01-01", end="2025-03-31", fy=2026, fp="FY")
    year_to_date = entry(start="2025-01-01", end="2025-06-30", fp="Q2")
    report = parse(raw([quarter, year_to_date]))
    assert {row.period for row in report.observations} == {"quarter", "other_duration"}
    assert "nonstandard_or_year_to_date_period" in report.gaps
    assert all(row.value == "100" for row in report.observations)  # No Q2 subtraction.
    instant = entry()
    del instant["start"]
    assert parse(raw([instant], concept="Assets"), "Assets").observations[0].period == "instant"
    with pytest.raises(ValueError):
        parse(raw([instant]))
    with pytest.raises(ValueError):
        parse(raw(concept="Assets"), "Assets")


def test_units_are_not_converted_or_guessed_and_unreviewed_forms_are_explicit():
    report = parse(raw(units={"USD": [entry()], "EUR": [entry(val=90)], "USDm": [entry(val=1)],
                              "shares": [entry()], "pure": [entry()], "XXX": [entry()]}))
    assert {row.unit for row in report.observations} == {"USD", "EUR"} and "unsupported_unit" in report.gaps
    eps = parse(raw(concept="EarningsPerShareDiluted", units={"USD/shares": [entry(val=1.5)], "USD": [entry()]}), "EarningsPerShareDiluted")
    assert len(eps.observations) == 1 and eps.observations[0].value == "1.5"
    unsupported = parse(raw([entry(form="8-K")]))
    assert not unsupported.observations and set(unsupported.gaps) == {"unsupported_form", "no_supported_observations"}


def test_revisions_keep_original_values_without_resolving_same_date_conflicts():
    original = entry(val=100)
    latest = entry(val=90, filed="2026-03-01", accn="0000009999-26-000002", form="10-K/A")
    report = parse(raw([original, latest, latest]))
    assert len(report.observations) == 2
    old, new = report.observations
    assert old.revision == "superseded" and old.value == "100"
    assert new.revision == "current" and new.value == "90" and new.supersedes == (old.id,)
    conflicted = parse(raw([original, latest, entry(val=95, filed="2026-03-01", accn="0000009999-26-000003")]))
    assert [row.revision for row in conflicted.observations].count("conflict") == 2
    assert "conflicting_latest_values" in conflicted.gaps and not any(row.revision == "current" for row in conflicted.observations)


def test_history_limits_keep_restatements_and_do_not_fill_gaps_with_older_quarters():
    annual = [entry(start=f"{year}-01-01", end=f"{year}-12-31", filed=f"{year+1}-02-01", fy=year,
                    accn=f"0000009999-{(year+1)%100:02}-000001") for year in range(2010, 2026)]
    report = default_history(parse(raw(annual + [entry(val=90, filed="2026-03-01", accn="0000009999-26-000002")])))
    assert {row.end.year for row in report.observations} == {2021, 2022, 2023, 2024, 2025}
    assert len(report.observations) == 6 and "incomplete_quarter_history" in report.gaps
    quarters = [entry(start=f"{year}-01-01", end=f"{year}-03-31", filed=f"{year}-05-01", fy=year, fp="Q1",
                      accn=f"0000009999-{year%100:02}-000001") for year in range(2010, 2027)]
    report = default_history(parse(raw(quarters)))
    assert len(report.observations) == 4 and "incomplete_quarter_history" in report.gaps
    assert all(row.end.year >= 2023 for row in report.observations)


def test_similar_concepts_and_corporate_action_sensitive_units_are_not_spliced():
    revenue = parse(raw())
    contracts = parse(raw(concept="RevenueFromContractWithCustomerExcludingAssessedTax"), "RevenueFromContractWithCustomerExcludingAssessedTax")
    assert revenue.observations[0].concept != contracts.observations[0].concept
    shares = parse(raw(concept="WeightedAverageNumberOfDilutedSharesOutstanding", units={"shares": [entry(val=100), entry(val=200, filed="2026-03-01")]}),
                   "WeightedAverageNumberOfDilutedSharesOutstanding")
    assert {Decimal(row.value) for row in shares.observations} == {Decimal(100), Decimal(200)}
    # No split-adjustment or unit imputation without independent corporate-action data.
