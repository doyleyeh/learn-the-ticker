from __future__ import annotations

from backend.etf_issuer_source_packs import (
    ETF_ISSUER_SOURCE_PACK_POLICY_VERSION,
    ETF_ISSUER_SOURCE_PACK_SCHEMA_VERSION,
    build_automated_etf_issuer_source_pack,
)


def test_automated_etf_issuer_source_pack_prefers_structured_sources_without_per_source_human_review():
    pack = build_automated_etf_issuer_source_pack(
        ticker="VOO",
        fund_name="Vanguard S&P 500 ETF",
        issuer="Vanguard",
    )

    assert pack is not None
    diagnostics = pack.diagnostics
    assert diagnostics["schema_version"] == ETF_ISSUER_SOURCE_PACK_SCHEMA_VERSION
    assert diagnostics["policy_version"] == ETF_ISSUER_SOURCE_PACK_POLICY_VERSION
    assert diagnostics["source_pack_status"] == "automated_policy_ready"
    assert diagnostics["structured_sources_first"] is True
    assert diagnostics["human_review_required_per_source"] is False
    assert diagnostics["automated_policy_can_approve_known_source_patterns"] is True
    assert diagnostics["fallback_order"] == ["official_issuer", "provider_api", "yahoo"]
    assert {"product_page", "fact_sheet", "holdings", "exposures", "prospectus", "shareholder_report"} <= set(
        diagnostics["source_types"]
    )
    assert all(source.raw_body_storage_allowed is False for source in pack.sources)


def test_etf_issuer_source_pack_blocks_complex_products_before_parser_or_provider_unlock():
    pack = build_automated_etf_issuer_source_pack(
        ticker="TQQQ",
        fund_name="ProShares UltraPro QQQ 3x Leveraged ETF",
        issuer="ProShares",
    )

    assert pack is None

    vanguard_complex = build_automated_etf_issuer_source_pack(
        ticker="VLEV",
        fund_name="Vanguard Leveraged Single Stock ETF",
        issuer="Vanguard",
    )

    assert vanguard_complex is not None
    assert vanguard_complex.source_pack_status == "blocked_unsupported_product_gate"
    assert vanguard_complex.unsupported_product_gate_passed is False
    assert vanguard_complex.sources == ()
