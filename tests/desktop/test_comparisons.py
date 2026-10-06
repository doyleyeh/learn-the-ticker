from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.api import create_app
from backend.app.backup import make_backup, preview_backup, read_backup, restore_backup
from backend.app.comparisons import ComparisonRequest, ComparisonResult, alignment, build_comparison, create_comparison
from backend.app.contracts import Claim, Settings, Source, SourcePolicy, uid
from backend.app.db import Database
from backend.safety import find_forbidden_output_phrases
from tests.desktop.comparison_fixture import comparison_pair, empty_comparison_asset, seed_comparison
from tests.desktop.financial_fixture import AT
from tests.desktop.test_backup import alter
from tests.desktop.market_fixture import market_bundle

TOKEN = "comparison-test-" * 5


def revenue(result):
    return next(r for r in result.rows if r.id == "financial:Revenues:annual")


@pytest.mark.parametrize("changes,expected", [({}, "aligned"), ({"unit": "EUR"}, "different_units"),
    ({"end": "2025-12-30"}, "different_periods"), ({"conflict": True}, "missing_evidence")])
def test_original_exact_values_align_only_with_compatible_periods_units_and_no_conflicts(changes, expected):
    left, right = comparison_pair(**changes)
    result = build_comparison(left, right)
    row = revenue(result)
    assert row.alignment == expected
    assert row.left.value == "9007199254740992"
    assert row.left.source_ids == [left.financials.observations[-1].source_id]
    assert row.left.evidence_ids == [left.financials.observations[-1].id]
    assert row.left.start.isoformat() == "2025-01-01"
    assert result.left.saved_at == AT and result.created_at > AT
    if changes.get("conflict"):
        assert row.right.value is None and row.right.state == "conflict"
    else:
        assert row.right.value == "9007199254740993"
    assert not find_forbidden_output_phrases(result.model_dump_json())


@pytest.mark.parametrize("kind", ["etf", "fund", "bond", "crypto", "option", "future", "index", "other", "unknown"])
def test_mixed_types_have_explicit_gaps_without_stock_metric_imputation(kind):
    left, _ = comparison_pair()
    result = build_comparison(left, empty_comparison_asset(kind))
    row = revenue(result)
    assert row.alignment == "missing_evidence" and row.right.value is None
    assert row.right.state == ("unknown_type" if kind == "unknown" else "not_applicable")
    assert result.right.asset.asset_type == kind
    assert result.left.asset.asset_type == "stock"


def test_no_unverified_note_or_generated_interpretation_becomes_comparison_input():
    left, right = comparison_pair()
    left.notes.append(Claim(asset_id=left.asset.id, text="UNVERIFIED PHANTOM 999", section="overview"))
    assert "PHANTOM" not in build_comparison(left, right).model_dump_json()
    left.identity_verification = None
    with pytest.raises(ValueError):
        build_comparison(left, right)


def test_same_asset_foreign_identity_future_time_and_oversized_context_rejected(monkeypatch):
    left, right = comparison_pair()
    with pytest.raises(ValueError, match="different"):
        build_comparison(left, left)
    with pytest.raises(ValueError, match="newer"):
        build_comparison(left, right, created_at=AT - timedelta(days=1))
    right.asset.name = "Wrong asset"
    with pytest.raises(ValueError):
        build_comparison(left, right)
    monkeypatch.setattr("backend.app.comparisons.MAX_CONTEXT", 5)
    with pytest.raises(ValueError, match="bounded"):
        build_comparison(left, comparison_pair()[1])


def test_share_basis_and_return_method_must_match_even_with_equal_periods():
    row = revenue(build_comparison(*comparison_pair()))
    assert alignment(row.left, row.right.model_copy(update={"basis": "different"}), "stock", "stock") == "different_methods"
    assert alignment(row.left, row.right, "stock", "etf") == "different_types"
    assert alignment(row.left.model_copy(update={"unit": "USD/shares"}), row.right.model_copy(update={"unit": "USD/shares"}), "stock", "stock") == "share_basis_unverified"


def test_retained_private_returns_and_valuations_keep_exact_methods_and_original_citations():
    left = market_bundle(valuations=True)
    right = comparison_pair()[1]
    result = build_comparison(left, right)
    row = next(r for r in result.rows if r.id == "return:retained:price_percent")
    original = left.market.returns[-1]
    assert row.left.value == original.price_percent and row.left.start == original.start and row.left.end == original.end
    assert row.left.source_ids == [left.market.source_id] and row.right.state == "missing"
    reverse = build_comparison(right, left)
    assert [r.left for r in reverse.rows] == [r.right for r in result.rows]
    assert [r.right for r in reverse.rows] == [r.left for r in result.rows]
    valuation = next(r for r in result.rows if r.id == "valuation:PeRatio:trailing")
    assert valuation.left.source_ids == [left.market.valuations.source_id]
    assert valuation.left.value == "29.5"
    quarterly = next(r for r in result.rows if r.id == "valuation:PeRatio:quarterly")
    assert quarterly.left.value is None and quarterly.left.state == "missing"
    assert quarterly.left.end == valuation.left.end
    db = Database("sqlite://", testing=True)
    seed_comparison(db, (left, right))
    created = create_comparison(db, ComparisonRequest(left_bundle_id=left.id, right_bundle_id=right.id))
    target = Database("sqlite://", testing=True)
    raw = make_backup(db)
    restore_backup(target, raw, preview_backup(target, raw).fingerprint)
    assert target.get("comparison:" + created.id) == created.model_dump(mode="json")
    assert not target.get("settings")["experimental_yahoo_enabled"]


def test_cited_fund_descriptions_preserve_both_sides_and_never_infer_numeric_metrics():
    left, right = empty_comparison_asset("etf"), empty_comparison_asset("fund")
    for bundle in (left, right):
        source = Source(id="same-local-citation-id", asset_id=bundle.asset.id,
            url="https://www.sec.gov/Archives/edgar/data/1/000000000126000001/report.htm",
            title="Synthetic fund description", publisher="SEC", policy=SourcePolicy.full_text,
            verified=True, provenance="verified_retrieval", excerpt="This fund tracks a broad index.", retrieved_at=AT)
        bundle.sources = [source]
        bundle.claims = [Claim(asset_id=bundle.asset.id, kind="fact", section="benchmark", text=source.excerpt, source_ids=[source.id])]
    result = build_comparison(left, right)
    row = next(r for r in result.rows if r.id == "description:benchmark")
    assert row.alignment == "descriptive" and row.left.text == row.right.text
    assert result.left.bundle_id != result.right.bundle_id
    assert all(c.value is None for r in result.rows for c in (r.left, r.right))
    right.sources[0].policy, right.sources[0].excerpt = SourcePolicy.link, ""
    restricted = build_comparison(left, right)
    assert next(r for r in restricted.rows if r.id == row.id).right.state == "missing"


def test_immutable_publication_restore_and_offline_api_reads_never_generate(tmp_path, monkeypatch):
    db = Database("sqlite://", testing=True)
    left, right = seed_comparison(db)
    request = ComparisonRequest(left_bundle_id=left.id, right_bundle_id=right.id)
    app = create_app(db, TOKEN, tmp_path)
    with TestClient(app) as client:
        assert client.post("/api/comparisons", json=request.model_dump()).status_code == 401
        client.headers["Authorization"] = "Bearer " + TOKEN
        response = client.post("/api/comparisons", json=request.model_dump())
        assert response.status_code == 200, response.text
        result = ComparisonResult.model_validate(response.json())
        payload = result.model_dump(mode="json")
        with pytest.raises(ValueError, match="immutable"):
            db.put("comparison:" + result.id, "comparison", {**payload, "created_at": (result.created_at + timedelta(seconds=1)).isoformat()})
        refreshed = left.model_copy(update={"id": uid()})
        db.put("bundle:" + refreshed.id, "bundle", refreshed.model_dump(mode="json"), left.asset.id)
        db.put("asset:" + left.asset.id, "asset", refreshed.model_dump(mode="json"))
        archive = make_backup(db)
        target = Database("sqlite://", testing=True)
        restore_backup(target, archive, preview_backup(target, archive).fingerprint)
        assert target.get("comparison:" + result.id) == payload
        assert target.get("asset:" + left.asset.id)["id"] == refreshed.id
        db.put("settings", "settings", Settings().model_dump(mode="json"))
        def never(*args, **kwargs):
            raise AssertionError("Offline read attempted comparison generation")
        monkeypatch.setattr("backend.app.comparisons.build_comparison", never)
        assert client.get("/api/comparisons/" + result.id).json() == payload
        assert client.get("/api/comparisons").json()[0]["left"]["bundle_id"] == left.id
        assert client.post("/api/comparisons", json=request.model_dump()).status_code == 409
        assert client.get("/api/comparisons/missing").status_code == 404


@pytest.mark.parametrize("change", ["value", "source", "bundle", "alignment", "identity", "missing"])
def test_archive_rejects_comparison_tampering_even_with_recomputed_archive_checksum(change):
    db = Database("sqlite://", testing=True)
    left, right = seed_comparison(db)
    result = create_comparison(db, ComparisonRequest(left_bundle_id=left.id, right_bundle_id=right.id))
    raw = make_backup(db)
    def mutate(data):
        record = next(r for r in data["records"] if r["kind"] == "comparison")["payload"]
        row = next(r for r in record["rows"] if r["id"] == "financial:Revenues:annual")
        if change == "value": row["left"]["value"] = "1"
        elif change == "source": row["left"]["source_ids"] = row["right"]["source_ids"]
        elif change == "alignment": row["alignment"] = "different_periods"
        elif change == "bundle": record["left"]["bundle_id"] = right.id
        elif change == "identity": record["left"]["asset"]["exchange"] = "wrong"
        else: data["records"] = [r for r in data["records"] if r["id"] != "bundle:" + left.id]
    with pytest.raises(ValueError):
        read_backup(alter(raw, change=mutate))
    assert db.get("comparison:" + result.id) == result.model_dump(mode="json")


def test_publication_failure_leaves_no_partial_comparison():
    db = Database("sqlite://", testing=True)
    left, right = seed_comparison(db)
    def fail_commit(*args):
        raise RuntimeError("synthetic interrupted write")
    event.listen(db.engine, "commit", fail_commit)
    try:
        with pytest.raises(RuntimeError):
            create_comparison(db, ComparisonRequest(left_bundle_id=left.id, right_bundle_id=right.id))
    finally:
        event.remove(db.engine, "commit", fail_commit)
    assert not db.list("comparison") and len(db.list("bundle")) == 2
