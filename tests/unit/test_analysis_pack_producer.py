from __future__ import annotations

import json
import subprocess
import sys

from backend.analysis_pack_producer import (
    CODEX_INSTRUCTIONS_PATH,
    ANALYSIS_PACK_PRODUCER_SCHEMA_VERSION,
    build_analysis_pack_bundle,
    build_macro_cache_artifact,
    build_technical_data_artifact,
    default_analysis_pack_tickers,
)
from backend.analysis_packs import validate_analysis_pack_import_bundle


NOW = "2026-05-10T12:00:00Z"
EXPIRES = "2026-05-17T12:00:00Z"


def test_analysis_pack_producer_builds_valid_market_and_ticker_bundle():
    bundle, summary = build_analysis_pack_bundle(
        tickers=["QQQ", "VOO", "TSLA"],
        bundle_id="producer-test-bundle",
        generated_at=NOW,
        freshness_expires_at=EXPIRES,
    )

    assert validate_analysis_pack_import_bundle(bundle, now=NOW) == []
    assert summary["schema_version"] == ANALYSIS_PACK_PRODUCER_SCHEMA_VERSION
    assert summary["validation_status"] == "passed"
    assert summary["market_context_pack_included"] is True
    assert summary["economic_indicators_included"] is True
    assert summary["included_tickers"] == ["QQQ", "VOO"]
    assert summary["skipped_tickers"] == [
        {"ticker": "TSLA", "reason": "not_high_demand_allowlisted"}
    ]
    assert bundle.market_context_pack is not None
    assert bundle.market_context_pack.market_ai_comprehensive_analysis.analysis_available is True
    assert set(bundle.ticker_packs) == {"QQQ", "VOO"}
    assert bundle.validation_metadata["codex_instruction_path"] == CODEX_INSTRUCTIONS_PATH
    assert bundle.validation_metadata["no_html_injection"] is True
    assert bundle.validation_metadata["visible_persona_labels_allowed"] is False
    assert bundle.raw_article_text_collected is False
    assert bundle.raw_provider_payload_exposed is False


def test_analysis_pack_producer_default_tickers_follow_current_supported_seed():
    assert default_analysis_pack_tickers() == ("AAPL", "VOO", "QQQ")


def test_producer_writes_technical_and_macro_artifacts_without_live_calls():
    bundle, _ = build_analysis_pack_bundle(
        tickers=["QQQ"],
        bundle_id="producer-artifact-test",
        generated_at=NOW,
        freshness_expires_at=EXPIRES,
    )
    technical = build_technical_data_artifact(bundle)
    macro = build_macro_cache_artifact(bundle)

    assert technical["schema_version"] == "analysis-pack-technical-data-artifact-v1"
    assert technical["no_live_external_calls"] is True
    assert technical["technical_indicator_status"] == "not_computed_without_live_market_data_adapter"
    assert {"KD", "RSI", "MACD", "BIAS", "DMI_ADX"} <= set(technical["indicators_reserved"])
    assert macro["schema_version"] == "analysis-pack-macro-cache-artifact-v1"
    assert macro["upsert_only"] is True
    assert {"gdp", "cpi", "treasury_10y"} <= set(macro["indicators"])


def test_build_analysis_pack_bundle_cli_writes_expected_files(tmp_path):
    bundle_path = tmp_path / "analysis-pack-bundle.json"
    summary_path = tmp_path / "analysis-pack-summary.json"
    technical_path = tmp_path / "technical_data.json"
    macro_path = tmp_path / "macro_cache.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_analysis_pack_bundle.py",
            "--ticker",
            "QQQ",
            "--bundle-id",
            "cli-producer-test",
            "--generated-at",
            NOW,
            "--freshness-expires-at",
            EXPIRES,
            "--output",
            str(bundle_path),
            "--summary-output",
            str(summary_path),
            "--technical-output",
            str(technical_path),
            "--macro-output",
            str(macro_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    technical = json.loads(technical_path.read_text(encoding="utf-8"))
    macro = json.loads(macro_path.read_text(encoding="utf-8"))
    assert bundle["schema_version"] == "analysis-pack-import-bundle-v1"
    assert summary["validation_status"] == "passed"
    assert technical["schema_version"] == "analysis-pack-technical-data-artifact-v1"
    assert macro["schema_version"] == "analysis-pack-macro-cache-artifact-v1"

    validate = subprocess.run(
        [
            sys.executable,
            "scripts/build_analysis_pack_bundle.py",
            "--validate-only",
            "--input",
            str(bundle_path),
            "--summary-output",
            str(summary_path),
            "--now",
            NOW,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert validate.returncode == 0


def test_codex_operator_script_and_instructions_have_required_markers():
    script = open("scripts/run_analysis_pack_codex.sh", "r", encoding="utf-8").read()
    instructions = open(CODEX_INSTRUCTIONS_PATH, "r", encoding="utf-8").read()

    assert "ltt_codex_exec -a never exec --sandbox workspace-write" in script
    assert "scripts/build_analysis_pack_bundle.py" in script
    assert "scripts/upload_analysis_pack_bundle.py" in script
    assert "analysis-pack-bundle.json" in script
    assert "technical_data.json" in script
    assert "macro_cache.json" in script
    assert "Generate English educational content for v1." in instructions
    assert "Do not inject HTML into app pages." in instructions
    assert "Market News Focus is reusable market-wide context." in instructions
    assert "Ticker imported packs are high-demand only" in instructions
    assert "technical_data.json" in instructions
