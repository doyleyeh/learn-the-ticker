from __future__ import annotations

import json
import subprocess
import sys

from backend.analysis_pack_producer import (
    CODEX_INSTRUCTIONS_PATH,
    ANALYSIS_PACK_PRODUCER_SCHEMA_VERSION,
    build_analysis_pack_bundle,
    build_ai_context_artifact_from_bundle,
    build_macro_cache_artifact,
    build_technical_data_artifact,
    default_analysis_pack_tickers,
    default_live_analysis_pack_tickers,
    resolve_analysis_pack_live_default,
    upsert_macro_cache_artifact,
)
from backend.analysis_packs import compute_analysis_pack_bundle_checksum, validate_analysis_pack_import_bundle
from backend.analysis_pack_numeric_validation import validate_analysis_pack_numeric_integrity
from backend.economic_indicators_live import parse_fred_csv


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
    assert default_live_analysis_pack_tickers() == (
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
        "VOO",
        "QQQ",
        "SPY",
        "VTI",
        "IVV",
        "XLK",
    )


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
    assert macro["indicators"]["gdp"]["primary_source"]["publisher"] == "BEA"
    assert macro["indicators"]["gdp"]["cross_check_sources"]


def test_analysis_pack_live_default_resolver_is_live_locally_and_deterministic_for_automation():
    assert resolve_analysis_pack_live_default(env={}, argv=["scripts/build_analysis_pack_bundle.py"]) is True
    assert resolve_analysis_pack_live_default(env={"CI": "true"}, argv=["scripts/build_analysis_pack_bundle.py"]) is False
    assert resolve_analysis_pack_live_default(env={"PYTEST_CURRENT_TEST": "x"}, argv=["scripts/build_analysis_pack_bundle.py"]) is False
    assert resolve_analysis_pack_live_default(env={}, argv=["evals/run_static_evals.py"]) is False
    assert resolve_analysis_pack_live_default(env={"LTT_ANALYSIS_PACK_DETERMINISTIC": "true"}, argv=[]) is False


def test_macro_cache_upsert_preserves_existing_rows_and_blocks_large_count_drop():
    bundle, _ = build_analysis_pack_bundle(
        tickers=["QQQ"],
        bundle_id="macro-upsert-test",
        generated_at=NOW,
        freshness_expires_at=EXPIRES,
        live=False,
    )
    current = build_macro_cache_artifact(bundle)
    previous = {
        **current,
        "indicators": {
            **current["indicators"],
            "legacy_indicator": {
                "name": "Legacy Indicator",
                "value": "1.0",
                "as_of_date": "2026-01",
            },
        },
    }

    merged = upsert_macro_cache_artifact(previous, current)

    assert "legacy_indicator" in merged["indicators"]
    assert merged["upsert_guard"]["previous_indicator_count"] == len(previous["indicators"])
    assert merged["upsert_guard"]["merged_indicator_count"] == len(previous["indicators"])

    sparse = {**current, "indicators": {"gdp": current["indicators"]["gdp"]}}
    try:
        upsert_macro_cache_artifact(previous, sparse)
    except ValueError as exc:
        assert "macro_cache_indicator_count_drop_blocked" in str(exc)
    else:
        raise AssertionError("Expected sparse macro cache update to be blocked.")


def test_fred_csv_parser_accepts_series_id_value_column():
    observations = parse_fred_csv("observation_date,GDP\n2026-01-01,31856.3\n")

    assert observations == [("2026-01-01", 31856.3)]


def test_build_analysis_pack_bundle_cli_writes_expected_files(tmp_path):
    bundle_path = tmp_path / "analysis-pack-bundle.json"
    summary_path = tmp_path / "analysis-pack-summary.json"
    technical_path = tmp_path / "technical_data.json"
    macro_path = tmp_path / "macro_cache.json"
    ai_context_path = tmp_path / "ai_context.json"

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
            "--ai-context-output",
            str(ai_context_path),
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
    ai_context = json.loads(ai_context_path.read_text(encoding="utf-8"))
    assert bundle["schema_version"] == "analysis-pack-import-bundle-v1"
    assert summary["validation_status"] == "passed"
    assert technical["schema_version"] == "analysis-pack-technical-data-artifact-v1"
    assert macro["schema_version"] == "analysis-pack-macro-cache-artifact-v1"
    assert ai_context["schema_version"] == "analysis-pack-ai-context-v1"

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


def test_live_analysis_pack_producer_uses_live_adapters_with_fixture_fetchers():
    bundle, summary = build_analysis_pack_bundle(
        tickers=["QQQ"],
        bundle_id="live-producer-test",
        generated_at=NOW,
        freshness_expires_at=EXPIRES,
        live=True,
        market_fetcher=_FakeMarketNewsFetcher(),
        lightweight_fetcher=_FakeLightweightFetcher(),
        technical_fetcher=_FakeTechnicalFetcher(),
        economic_fetcher=_FakeEconomicFetcher(),
    )

    assert validate_analysis_pack_import_bundle(bundle, now=NOW) == []
    assert summary["validation_status"] == "passed"
    assert summary["source_mode"] == "live_operator"
    assert summary["no_live_external_calls"] is False
    assert summary["technical_indicator_status"] == "computed"
    assert bundle.market_context_pack is not None
    assert bundle.market_context_pack.market_news_focus.no_live_external_calls is False
    assert bundle.economic_indicators is not None
    assert bundle.economic_indicators.no_live_external_calls is False
    assert set(bundle.ticker_packs) == {"QQQ"}
    ai_context = build_ai_context_artifact_from_bundle(bundle)
    assert ai_context["schema_version"] == "analysis-pack-ai-context-v1"
    assert "selected_items" in ai_context["market_news"]
    assert ai_context["tickers"]["QQQ"]["weekly_news_items"]
    assert ai_context["economic_indicators"]
    assert ai_context["technical_indicators"]["QQQ"]["state"] == "computed"
    assert any(fact["fact_id"] == "economic:vix" for fact in ai_context["allowed_numeric_facts"])
    assert any(fact["fact_id"] == "technical:QQQ:ADX" for fact in ai_context["allowed_numeric_facts"])

    technical = build_technical_data_artifact(bundle)
    qqq = technical["tickers"]["QQQ"]
    assert qqq["state"] == "computed"
    assert qqq["KD"]["D"] is not None
    assert qqq["RSI"]["value"] is not None
    assert qqq["MACD"]["macd"] is not None
    assert qqq["BIAS"]["20"] is not None
    assert qqq["DMI_ADX"]["ADX"] is not None
    assert qqq["moving_averages"]["50"] is not None
    assert qqq["volume_change"]["percent_change"] is not None


def test_codex_operator_script_and_instructions_have_required_markers():
    script = open("scripts/run_analysis_pack_codex.sh", "r", encoding="utf-8").read()
    instructions = open(CODEX_INSTRUCTIONS_PATH, "r", encoding="utf-8").read()

    assert "ltt_codex_exec -a never exec --sandbox workspace-write" in script
    assert "scripts/build_analysis_pack_bundle.py" in script
    assert "scripts/upload_analysis_pack_bundle.py" in script
    assert "analysis-pack-bundle.json" in script
    assert "technical_data.json" in script
    assert "macro_cache.json" in script
    assert "ai_context.json" in script
    assert "--deterministic" in script
    assert "Generate English educational content for v1." in instructions
    assert "Do not inject HTML into app pages." in instructions
    assert "Market News Focus is reusable market-wide context." in instructions
    assert "Ticker imported packs are high-demand only" in instructions
    assert "technical_data.json" in instructions
    assert "Global Macro/Fed" in instructions
    assert "official historical actuals" in instructions
    assert "AI Context And Numeric Integrity" in instructions
    assert "Do not copy article bodies" in instructions


def test_numeric_validator_rejects_deviating_values_and_technical_field_misuse():
    bundle, _ = build_analysis_pack_bundle(
        tickers=["QQQ"],
        bundle_id="numeric-validation-test",
        generated_at=NOW,
        freshness_expires_at=EXPIRES,
        live=False,
    )
    assert bundle.market_context_pack is not None
    analysis = bundle.market_context_pack.market_ai_comprehensive_analysis
    bad_sections = [
        section.model_copy(update={"analysis": "The VIX is 60 and QQQ ADX price is 40."})
        if section.section_id == "macro_policy"
        else section
        for section in analysis.sections
    ]
    bad_analysis = analysis.model_copy(update={"sections": bad_sections})
    bad_bundle = bundle.model_copy(
        deep=True,
        update={
            "market_context_pack": bundle.market_context_pack.model_copy(
                update={"market_ai_comprehensive_analysis": bad_analysis}
            )
        },
    )
    bad_bundle = bad_bundle.model_copy(
        update={
            "validation": bad_bundle.validation.model_copy(
                update={"checksum": compute_analysis_pack_bundle_checksum(bad_bundle)}
            )
        }
    )

    reason_codes = validate_analysis_pack_numeric_integrity(bad_bundle)

    assert "unsupported_or_deviating_numeric_claim" in reason_codes
    assert "technical_indicator_field_misused_as_price" in reason_codes


class _FakeMarketNewsFetcher:
    no_live_external_calls = False

    def fetch_text(self, url, *, headers=None, timeout_seconds=15):
        del url, headers, timeout_seconds
        items = [
            ("Reuters", "Federal Reserve inflation Treasury yields move after jobs report", "Fed policy and inflation expectations shaped Treasury yield trading.", "https://www.reuters.com/markets/fed-yields"),
            ("Bloomberg", "S&P 500 and Nasdaq stocks react to earnings week", "Major US equity indexes moved as earnings updates reset sector expectations.", "https://www.bloomberg.com/markets/stocks-earnings"),
            ("CNBC", "AI semiconductor chips stay in focus for big technology companies", "AI infrastructure and semiconductor demand remained a central market theme.", "https://www.cnbc.com/technology/ai-chips"),
            ("Reuters", "Oil and Red Sea shipping risk keep supply chain concerns visible", "Energy and shipping headlines kept geopolitical risk in the market discussion.", "https://www.reuters.com/world/oil-shipping"),
            ("Wall Street Journal", "Banks credit liquidity and consumer stress watched by investors", "Credit and liquidity conditions remained a sentiment input for markets.", "https://www.wsj.com/markets/credit-liquidity"),
        ]
        body = "".join(
            f"<item><title>{title}</title><link>{link}</link><description>{desc}</description>"
            f"<pubDate>Sat, 09 May 2026 12:00:00 GMT</pubDate><source>{source}</source></item>"
            for source, title, desc, link in items
        )
        return f"<rss><channel><language>en</language>{body}</channel></rss>"

    def fetch_json(self, url, *, headers=None, timeout_seconds=15):
        del url, headers, timeout_seconds
        return {}


class _FakeLightweightFetcher:
    no_live_external_calls = False

    def fetch_json(self, url, *, user_agent, timeout_seconds):
        del user_agent, timeout_seconds
        if "finance/search" in url:
            return {
                "quotes": [{"symbol": "QQQ", "quoteType": "ETF", "shortname": "Invesco QQQ Trust"}],
                "news": [
                    {
                        "uuid": "qqq-live-1",
                        "title": "QQQ tracks technology stocks as Nasdaq earnings dominate the week",
                        "summary": "The fund remained tied to large technology and communications names during an earnings-heavy week.",
                        "publisher": "Reuters",
                        "link": "https://www.reuters.com/markets/qqq-tech-earnings",
                        "providerPublishTime": 1778241600,
                        "relatedTickers": ["QQQ"],
                    },
                    {
                        "uuid": "qqq-live-2",
                        "title": "Invesco QQQ volume rises as AI chip headlines lift index funds",
                        "summary": "AI and semiconductor headlines kept QQQ-linked trading activity elevated.",
                        "publisher": "Bloomberg",
                        "link": "https://www.bloomberg.com/markets/qqq-ai-chips",
                        "providerPublishTime": 1778328000,
                        "relatedTickers": ["QQQ"],
                    },
                ],
            }
        if "finance/chart" in url:
            return _chart_payload()
        if "quoteSummary" in url:
            return {"quoteSummary": {"result": [{"summaryDetail": {}, "defaultKeyStatistics": {}, "financialData": {}}]}}
        return {}


class _FakeTechnicalFetcher:
    no_live_external_calls = False

    def fetch_json(self, url, *, timeout_seconds=15):
        del url, timeout_seconds
        return _chart_payload(day_count=260)


class _FakeEconomicFetcher:
    no_live_external_calls = False

    def fetch_text(self, url, *, timeout_seconds=15):
        del url, timeout_seconds
        rows = ["observation_date,value"]
        for index in range(18):
            year = 2024 + ((index + 6) // 12)
            month = ((index + 6) % 12) + 1
            rows.append(f"{year:04d}-{month:02d}-01,{100 + index * 1.5:.2f}")
        return "\n".join(rows)


def _chart_payload(day_count: int = 80) -> dict:
    timestamps = [1770000000 + day * 86400 for day in range(day_count)]
    opens = [100.0 + day * 0.4 for day in range(day_count)]
    highs = [value + 1.2 for value in opens]
    lows = [value - 1.1 for value in opens]
    closes = [value + (0.25 if day % 2 == 0 else -0.15) for day, value in enumerate(opens)]
    volumes = [1_000_000 + day * 2000 for day in range(day_count)]
    return {
        "chart": {
            "result": [
                {
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": opens,
                                "high": highs,
                                "low": lows,
                                "close": closes,
                                "volume": volumes,
                            }
                        ]
                    },
                    "meta": {"currency": "USD"},
                }
            ]
        }
    }
