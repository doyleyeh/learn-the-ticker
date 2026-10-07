"""Calculated issuer statistics preserve exact inputs and source/version boundaries."""
import json

import pytest

from backend.app.contracts import EvidenceBundle
from backend.app.db import Database
from backend.app.evidence import factual_context
from backend.app.evidence_reuse import conversation_evidence
from backend.app.financial_evidence import attach_financials
from backend.app.financial_ratios import METHOD, income_percent
from backend.app.structured_financials import SecFinancialAdapter
from tests.desktop.financial_fixture import AT, financial_result, financial_ui_bundle
from tests.desktop.test_evidence_reuse import save


BASE = {"start": "2025-01-01", "end": "2025-12-31", "val": 10,
        "accn": "0000009999-26-000001", "filed": "2026-02-01", "form": "10-K", "fy": 2025, "fp": "FY"}


def calculated(revenues=None, income=None, revenue_unit="USD", income_unit="USD", second_revenue=False):
    identities = financial_result()
    class Resolver:
        @property
        def sec(self):
            return self

        def resolve(self, query):
            return [identities.issuer] if query == "SYN" else [identities.instrument]

    def fetch(url, **_):
        concept = url.rsplit("/", 1)[-1].removesuffix(".json")
        is_income = concept == "NetIncomeLoss"
        rows = income if is_income else revenues
        unit = income_unit if is_income else revenue_unit
        return json.dumps({"cik": 1, "taxonomy": "us-gaap", "tag": concept, "entityName": "SYNTHETIC COMPANY",
            "units": {unit: rows if rows is not None else [{**BASE, "val": 10 if is_income else 30}]}}).encode()

    concepts = ("Revenues", "NetIncomeLoss") + (("RevenueFromContractWithCustomerExcludingAssessedTax",) if second_revenue else ())
    result = SecFinancialAdapter(Resolver(), fetch, clock=lambda: AT).retrieve("FIGI:chosen", concepts=concepts)
    base = EvidenceBundle(asset=result.instrument.asset, identity_verification=result.instrument.verification, created_at=AT)
    return attach_financials(base, result, created_at=AT)


@pytest.mark.parametrize("income,revenue,expected", [
    ("1", "3", "33.333333"), ("-1", "3", "-33.333333"),
    ("1", "200000000", "0"), ("3", "200000000", "0.000002"),
    ("-1", "200000000", "0"), ("9007199254740993", "3", "300239975158033100"),
    ("0.000000000000000003", "0.000000000000000001", "300"),
])
def test_exact_percentage_rounding(income, revenue, expected):
    assert income_percent(income, revenue) == expected


def test_same_filing_percentage_is_separate_from_reported_numbers_with_both_original_sources():
    bundle = calculated(second_revenue=True)
    assert bundle.financials.ratio_method == METHOD
    assert len(bundle.financials.ratios) == 2
    for ratio in bundle.financials.ratios:
        assert ratio.percent == "33.333333" and ratio.reason is None
        inputs = [row for row in bundle.financials.observations if row.id in ratio.input_ids]
        assert len(inputs) == 2 and {row.source_id for row in inputs} == set(ratio.source_ids)
    context = factual_context(bundle)
    assert len(context["financials"]["ratios"]) == 2
    assert not context["claims"]
    assert EvidenceBundle.model_validate_json(bundle.model_dump_json()) == bundle


@pytest.mark.parametrize("kwargs,reason", [
    ({"income": []}, "missing_income"),
    ({"income": [{**BASE, "start": "2025-01-02"}]}, "missing_income"),
    ({"income": [{**BASE, "end": "2025-12-30"}]}, "missing_income"),
    ({"income_unit": "EUR"}, "different_units"),
    ({"income": [{**BASE, "accn": "0000009999-26-000002"}]}, "different_filings"),
    ({"income": [{**BASE, "filed": "2026-03-01"}]}, "different_filings"),
    ({"revenues": [{**BASE, "val": 0}]}, "nonpositive_revenue"),
    ({"revenues": [{**BASE, "val": -1}]}, "nonpositive_revenue"),
    ({"income": [BASE, {**BASE, "val": 11, "accn": "0000009999-26-000002"}]}, "conflicting_inputs"),
    ({"income": [BASE, {**BASE, "accn": "0000009999-26-000002"}]}, "ambiguous_inputs"),
])
def test_incompatible_current_inputs_never_fall_back(kwargs, reason):
    bundle = calculated(**kwargs)
    ratio = bundle.financials.ratios[0]
    assert ratio.reason == reason and ratio.percent is None
    assert factual_context(bundle)["financials"]["ratios"] == []


def test_restated_latest_input_does_not_fall_back_to_older_matching_filing():
    bundle = calculated(income=[BASE, {**BASE, "val": 20, "filed": "2026-03-01", "accn": "0000009999-26-000002"}])
    ratio = bundle.financials.ratios[0]
    assert ratio.reason == "different_filings"
    assert len(ratio.input_ids) == 2
    assert all(row.revision == "current" for row in bundle.financials.observations if row.id in ratio.input_ids)


def test_negative_income_and_annual_quarter_separation():
    quarter = {**BASE, "end": "2025-03-31", "val": 5, "fp": "Q1", "form": "10-Q"}
    bundle = calculated(revenues=[{**BASE, "val": 20}, quarter], income=[{**BASE, "val": -5}, quarter])
    assert [(row.period, row.percent) for row in bundle.financials.ratios] == [("annual", "-25"), ("quarter", "100")]


@pytest.mark.parametrize("change", [
    {"percent": "34"}, {"percent": "33.3333330"}, {"reason": "missing_income"},
    {"input_ids": []}, {"source_ids": ["missing"]}, {"end": "2024-12-31"},
])
def test_retained_result_tampering_is_rejected(change):
    payload = calculated().model_dump(mode="json")
    payload["financials"]["ratios"][0].update(change)
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(payload)


def test_legacy_snapshot_is_read_without_new_calculation_and_method_cannot_be_removed_alone():
    payload = calculated().model_dump(mode="json")
    payload["financials"].pop("ratio_method")
    with pytest.raises(ValueError):
        EvidenceBundle.model_validate(payload)
    payload["financials"].pop("ratios")
    old = EvidenceBundle.model_validate(payload)
    assert old.financials.ratio_method is None and old.financials.ratios == []
    assert "ratios" not in factual_context(old)["financials"]


def test_reused_ratios_keep_version_scoped_citations_and_original_inputs():
    db = Database("sqlite://", testing=True)
    try:
        bundle = financial_ui_bundle()
        before = bundle.model_dump(mode="json")
        contexts, candidates = conversation_evidence(db, bundle.asset, [save(db, bundle)])
        context = contexts[0]
        ratios = context["financials"]["ratios"]
        assert len(ratios) == 2
        observations = {row["id"]: row for row in context["financials"]["observations"]}
        for ratio in ratios:
            assert set(ratio["source_ids"]) == {observations[key]["source_id"] for key in ratio["input_ids"]}
            assert all(candidates[key].retrieved_at == AT for key in ratio["source_ids"])
        assert db.get("bundle:" + bundle.id) == before
    finally:
        db.engine.dispose()


def test_sec_and_market_share_cloud_context_but_export_keeps_only_sec():
    from backend.app.identity import ResolvedIdentity
    from backend.app.market_evidence import attach_market
    from backend.app.market_mapping import map_yahoo_history
    from backend.app.source_operations import shareable_view
    from tests.desktop.market_fixture import market_candidate
    base = calculated()
    mapped = map_yahoo_history(market_candidate(), ResolvedIdentity(base.asset, base.identity_verification), at=AT)
    bundle = attach_market(base, mapped, personal_mode=True, created_at=AT)
    context = factual_context(bundle)
    assert context["financials"]["ratios"][0]["percent"] == "33.333333"
    assert context["market"]["source_id"] == bundle.market.source_id
    assert bundle.market.source_id in json.dumps(context)
    exported, notice = shareable_view(bundle)
    assert notice and exported.market is None and exported.financials == base.financials
    assert all(sid in {source.id for source in exported.sources} for ratio in exported.financials.ratios for sid in ratio.source_ids)


def test_default_history_keeps_five_annual_and_twelve_quarter_results_without_inventing_missing_periods():
    annual = [{**BASE, "start": f"{year}-01-01", "end": f"{year}-12-31"} for year in range(2015, 2026)]
    quarter = [{**BASE, "start": f"{year}-{month:02d}-01", "end": f"{year}-{month+2:02d}-{day}", "fp": "Q1", "form": "10-Q"}
               for year in range(2020, 2026) for month, day in ((1, 31), (4, 30), (7, 30), (10, 31))]
    bundle = calculated(revenues=annual + quarter, income=annual + quarter)
    assert len(bundle.financials.ratios) == 17
    assert len([row for row in bundle.financials.ratios if row.period == "annual"]) == 5
    assert len([row for row in bundle.financials.ratios if row.period == "quarter"]) == 12


def test_authenticated_exports_retain_calculated_method_inputs_and_original_sources(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app.api import create_app
    from tests.desktop.test_financial_evidence import seed, TOKEN
    db = Database("sqlite://", testing=True)
    try:
        bundle = calculated()
        seed(db, bundle)
        with TestClient(create_app(db, TOKEN, tmp_path)) as client:
            path = "/api/export/" + bundle.id
            headers = {"Authorization": "Bearer " + TOKEN}
            payload = client.get(path, headers=headers).json()
            assert payload["financials"]["ratios"] == bundle.financials.model_dump(mode="json")["ratios"]
            markdown = client.get(path + "?format=markdown", headers=headers).text
            assert "## Calculated issuer statistics" in markdown and "33.333333%" in markdown and METHOD in markdown
            assert all(sid in markdown for sid in bundle.financials.ratios[0].source_ids)
            assert all(oid in markdown for oid in bundle.financials.ratios[0].input_ids)
            assert all(str(source.url) in markdown for source in bundle.sources)
    finally:
        db.engine.dispose()
