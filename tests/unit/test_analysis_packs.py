from __future__ import annotations

import json

from backend.analysis_packs import (
    ANALYSIS_PACK_IMPORT_HISTORY_SCHEMA_VERSION,
    HIGH_DEMAND_ANALYSIS_PACK_TICKERS,
    AnalysisPackRepository,
    DurableAnalysisPackRepository,
    build_economic_indicators_pack,
    build_fixture_analysis_pack_import_bundle,
    compute_analysis_pack_bundle_checksum,
    validate_analysis_pack_import_bundle,
)


NOW = "2026-05-10T12:00:00Z"


def _with_current_checksum(bundle):
    return bundle.model_copy(
        update={
            "validation": bundle.validation.model_copy(
                update={"checksum": compute_analysis_pack_bundle_checksum(bundle)}
            )
        }
    )


def test_economic_indicators_pack_is_us_only_cited_and_rights_safe():
    pack = build_economic_indicators_pack()

    assert pack.schema_version == "economic-indicators-pack-v1"
    assert pack.region == "US"
    assert pack.no_live_external_calls is True
    assert pack.stable_facts_are_separate is True
    assert pack.analysis_pack_metadata is not None
    assert pack.analysis_pack_metadata.analysis_source == "deterministic_fixture"

    required = {
        "gdp",
        "cpi",
        "ppi",
        "retail_sales",
        "nonfarm_payrolls",
        "unemployment",
        "jobless_claims",
        "m2",
        "credit_card_delinquency",
        "private_investment",
        "treasury_10y",
    }
    assert required <= {item.indicator_id for item in pack.items}
    source_ids = {source.source_document_id for source in pack.source_documents}
    citation_ids = {citation.citation_id for citation in pack.citations}
    for item in pack.items:
        assert item.citation_ids
        assert set(item.citation_ids) <= citation_ids
        assert item.source_document_ids
        assert set(item.source_document_ids) <= source_ids
        assert item.source.source_use_policy.value != "rejected"


def test_analysis_pack_import_accepts_fresh_bundle_and_exposes_metadata():
    repo = AnalysisPackRepository()
    bundle = build_fixture_analysis_pack_import_bundle()

    result = repo.import_bundle(bundle, now=NOW)

    assert result.imported is True
    assert result.imported_market_context_pack is True
    assert result.imported_economic_indicators is True
    assert result.imported_ticker_packs == ["QQQ"]
    assert result.reason_codes == []

    market = repo.read_fresh_market_news_response(now=NOW)
    weekly = repo.read_fresh_weekly_news_response("QQQ", now=NOW)
    indicators = repo.read_fresh_economic_indicators_pack(now=NOW)
    assert market is not None
    assert market.analysis_pack_metadata is not None
    assert market.analysis_pack_metadata.analysis_source == "imported_local_pack"
    assert weekly is not None
    assert weekly.analysis_pack_metadata is not None
    assert weekly.analysis_pack_metadata.import_bundle_id == bundle.bundle_id
    assert indicators is not None
    assert indicators.analysis_pack_metadata is not None
    assert indicators.analysis_pack_metadata.validation_status == "passed"


def test_durable_analysis_pack_repository_reloads_imported_bundle(tmp_path):
    storage_path = tmp_path / "analysis-pack-store.json"
    bundle = build_fixture_analysis_pack_import_bundle()

    writer = DurableAnalysisPackRepository(storage_path)
    result = writer.import_bundle(bundle, now=NOW)
    assert result.imported is True
    assert storage_path.exists()

    reader = DurableAnalysisPackRepository(storage_path)
    weekly = reader.read_fresh_weekly_news_response("QQQ", now=NOW)
    market = reader.read_fresh_market_news_response(now=NOW)

    assert weekly is not None
    assert weekly.analysis_pack_metadata is not None
    assert weekly.analysis_pack_metadata.import_bundle_id == bundle.bundle_id
    assert market is not None
    assert "raw_article_text_stored" in storage_path.read_text(encoding="utf-8")


def test_durable_analysis_pack_repository_appends_safe_import_history(tmp_path):
    storage_path = tmp_path / "analysis-pack-store.json"
    bundle = build_fixture_analysis_pack_import_bundle()
    bundle = bundle.model_copy(
        update={"validation_metadata": {**bundle.validation_metadata, "operator_label": "local-operator"}}
    )
    bundle = _with_current_checksum(bundle)

    writer = DurableAnalysisPackRepository(storage_path)
    result = writer.import_bundle(bundle, now=NOW)

    assert result.imported is True
    assert writer.history_path.exists()
    records = [
        json.loads(line)
        for line in writer.history_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    record = records[0]
    assert record["schema_version"] == ANALYSIS_PACK_IMPORT_HISTORY_SCHEMA_VERSION
    assert record["bundle_id"] == bundle.bundle_id
    assert record["imported_at"] == NOW
    assert record["generated_at"] == bundle.generated_at
    assert record["freshness_expires_at"] == bundle.freshness_expires_at
    assert record["validation_status"] == "passed"
    assert record["reason_codes"] == []
    assert record["checksum"] == bundle.validation.checksum
    assert record["source_mode"] == "deterministic_fixture"
    assert record["included_tickers"] == ["QQQ"]
    assert record["operator_label"] == "local-operator"
    assert record["raw_article_text_stored"] is False
    assert record["raw_provider_payload_stored"] is False
    assert record["secret_values_stored"] is False


def test_import_bundle_checksum_raw_payload_and_persona_validation():
    bundle = build_fixture_analysis_pack_import_bundle()

    bad_checksum = bundle.model_copy(update={"validation": bundle.validation.model_copy(update={"checksum": "bad"})})
    assert "checksum_mismatch" in validate_analysis_pack_import_bundle(bad_checksum, now=NOW)

    raw_payload = _with_current_checksum(bundle.model_copy(update={"raw_provider_payload_exposed": True}))
    assert "raw_provider_payload_exposed" in validate_analysis_pack_import_bundle(raw_payload, now=NOW)

    visible_persona = _with_current_checksum(bundle.model_copy(update={"validation_metadata": {"note": "Atlas lens"}}))
    assert "visible_persona_label" in validate_analysis_pack_import_bundle(visible_persona, now=NOW)


def test_analysis_pack_freshness_falls_back_after_expiration():
    repo = AnalysisPackRepository()
    bundle = build_fixture_analysis_pack_import_bundle(
        generated_at="2026-05-01T12:00:00Z",
        freshness_expires_at="2026-05-08T12:00:00Z",
    )
    assert repo.import_bundle(bundle, now="2026-05-01T13:00:00Z").imported is True

    assert repo.read_fresh_market_news_response(now=NOW) is None
    assert repo.read_fresh_weekly_news_response("QQQ", now=NOW) is None
    assert repo.read_fresh_economic_indicators_pack(now=NOW) is None


def test_ticker_import_packs_are_high_demand_only():
    repo = AnalysisPackRepository()
    bundle = build_fixture_analysis_pack_import_bundle()
    qqq_pack = bundle.ticker_packs["QQQ"]
    mixed_bundle = bundle.model_copy(update={"ticker_packs": {"QQQ": qqq_pack, "TSLA": qqq_pack}})
    mixed_bundle = _with_current_checksum(mixed_bundle)

    result = repo.import_bundle(mixed_bundle, now=NOW)

    assert "QQQ" in HIGH_DEMAND_ANALYSIS_PACK_TICKERS
    assert result.imported is True
    assert result.reason_codes == ["non_high_demand_ticker_pack_ignored"]
    assert result.imported_ticker_packs == ["QQQ"]
    assert repo.read_fresh_weekly_news_response("QQQ", now=NOW) is not None
    assert repo.read_fresh_weekly_news_response("TSLA", now=NOW) is None
