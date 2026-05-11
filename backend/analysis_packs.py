from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.data import STUB_TIMESTAMP
from backend.market_news import build_market_news_response
from backend.models import (
    AIComprehensiveAnalysisResponse,
    AnalysisPackImportBundle,
    AnalysisPackImportResponse,
    AnalysisPackRuntimeMetadata,
    AnalysisPackValidationMetadata,
    Citation,
    EconomicIndicatorCategory,
    EconomicIndicatorItem,
    EconomicIndicatorsPackResponse,
    EconomicIndicatorTrendDirection,
    EvidenceState,
    FreshnessState,
    MarketNewsResponse,
    SourceAllowlistStatus,
    SourceDocument,
    SourceExportRights,
    SourceOperationPermissions,
    SourceParserStatus,
    SourceQuality,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
    StateMessage,
    WeeklyNewsContractState,
    WeeklyNewsResponse,
    WeeklyNewsSourceMetadata,
)
from backend.overview import generate_asset_overview


ANALYSIS_PACK_IMPORT_BUNDLE_SCHEMA_VERSION = "analysis-pack-import-bundle-v1"
ECONOMIC_INDICATORS_PACK_SCHEMA_VERSION = "economic-indicators-pack-v1"
MARKET_CONTEXT_PACK_SCHEMA_VERSION = "market_context_pack-v1"
ANALYSIS_PACK_VALIDATOR_VERSION = "analysis-pack-import-validator-v1"
ANALYSIS_PACK_MAX_AGE_DAYS = 7
ANALYSIS_PACK_DURABLE_STORE_SCHEMA_VERSION = "analysis-pack-durable-store-v1"
HIGH_DEMAND_ANALYSIS_PACK_TICKERS = (
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

_FORBIDDEN_VALUE_MARKERS = (
    "raw article body",
    "raw_article_body",
    "raw provider payload",
    "provider payload value",
    "hidden prompt",
    "raw model reasoning",
    "authorization:",
    "bearer ",
    "api_key",
    "secret",
    "xoxb-",
    "ghp_",
)

_VISIBLE_PERSONA_PATTERN = re.compile(r"\b(atlas|sophia|kenji|crow|rain)\b", re.IGNORECASE)

_SUMMARY_ONLY_OPERATIONS = SourceOperationPermissions(
    can_store_metadata=True,
    can_store_raw_text=False,
    can_display_metadata=True,
    can_display_excerpt=True,
    can_summarize=True,
    can_cache=True,
    can_export_metadata=True,
    can_export_excerpt=True,
    can_export_full_text=False,
    can_support_generated_output=True,
    can_support_citations=True,
    can_support_canonical_facts=False,
    can_support_recent_developments=True,
)


class AnalysisPackRepository:
    def __init__(self) -> None:
        self._bundle: AnalysisPackImportBundle | None = None

    def clear(self) -> None:
        self._bundle = None

    def import_bundle(
        self,
        bundle: AnalysisPackImportBundle,
        *,
        now: datetime | str | None = None,
    ) -> AnalysisPackImportResponse:
        reason_codes = validate_analysis_pack_import_bundle(bundle, now=now)
        imported_tickers = [
            ticker
            for ticker in sorted(bundle.ticker_packs)
            if ticker.upper() in HIGH_DEMAND_ANALYSIS_PACK_TICKERS
        ]
        ignored_tickers = [
            ticker
            for ticker in sorted(bundle.ticker_packs)
            if ticker.upper() not in HIGH_DEMAND_ANALYSIS_PACK_TICKERS
        ]
        if ignored_tickers:
            reason_codes.append("non_high_demand_ticker_pack_ignored")

        imported = not reason_codes or reason_codes == ["non_high_demand_ticker_pack_ignored"]
        if imported:
            filtered_bundle = bundle.model_copy(
                deep=True,
                update={
                    "ticker_packs": {
                        ticker.upper(): pack
                        for ticker, pack in bundle.ticker_packs.items()
                        if ticker.upper() in HIGH_DEMAND_ANALYSIS_PACK_TICKERS
                    }
                },
            )
            filtered_bundle = filtered_bundle.model_copy(
                update={
                    "validation": filtered_bundle.validation.model_copy(
                        update={"checksum": compute_analysis_pack_bundle_checksum(filtered_bundle)}
                    )
                }
            )
            self._bundle = filtered_bundle

        return AnalysisPackImportResponse(
            imported=imported,
            bundle_id=bundle.bundle_id,
            validation_status="passed" if imported else "failed",
            reason_codes=reason_codes,
            imported_market_context_pack=imported and bundle.market_context_pack is not None,
            imported_ticker_packs=imported_tickers if imported else [],
            imported_economic_indicators=imported and bundle.economic_indicators is not None,
        )

    def read_fresh_market_news_response(self, *, now: datetime | str | None = None) -> MarketNewsResponse | None:
        bundle = self._fresh_bundle(now=now)
        if bundle is None or bundle.market_context_pack is None:
            return None
        return bundle.market_context_pack.model_copy(
            update={"analysis_pack_metadata": _runtime_metadata(bundle)}
        )

    def read_fresh_weekly_news_response(
        self,
        ticker: str,
        *,
        now: datetime | str | None = None,
    ) -> WeeklyNewsResponse | None:
        normalized_ticker = ticker.strip().upper()
        if normalized_ticker not in HIGH_DEMAND_ANALYSIS_PACK_TICKERS:
            return None
        bundle = self._fresh_bundle(now=now)
        if bundle is None:
            return None
        weekly = bundle.ticker_packs.get(normalized_ticker)
        if weekly is None:
            return None
        return weekly.model_copy(update={"analysis_pack_metadata": _runtime_metadata(bundle)})

    def read_fresh_economic_indicators_pack(
        self,
        *,
        now: datetime | str | None = None,
    ) -> EconomicIndicatorsPackResponse | None:
        bundle = self._fresh_bundle(now=now)
        if bundle is None or bundle.economic_indicators is None:
            return None
        return bundle.economic_indicators.model_copy(
            update={"analysis_pack_metadata": _runtime_metadata(bundle)}
        )

    def _fresh_bundle(self, *, now: datetime | str | None = None) -> AnalysisPackImportBundle | None:
        if self._bundle is None:
            return None
        if validate_analysis_pack_import_bundle(self._bundle, now=now):
            return None
        return self._bundle


class DurableAnalysisPackRepository(AnalysisPackRepository):
    def __init__(self, storage_path: str | Path) -> None:
        super().__init__()
        self.storage_path = Path(storage_path).expanduser()

    def clear(self) -> None:
        super().clear()
        try:
            self.storage_path.unlink(missing_ok=True)
        except OSError:
            return

    def import_bundle(
        self,
        bundle: AnalysisPackImportBundle,
        *,
        now: datetime | str | None = None,
    ) -> AnalysisPackImportResponse:
        response = super().import_bundle(bundle, now=now)
        if response.imported and self._bundle is not None:
            self._persist_bundle(self._bundle)
        return response

    def _fresh_bundle(self, *, now: datetime | str | None = None) -> AnalysisPackImportBundle | None:
        if self._bundle is None:
            self._bundle = self._load_bundle()
        return super()._fresh_bundle(now=now)

    def _persist_bundle(self, bundle: AnalysisPackImportBundle) -> None:
        envelope = {
            "schema_version": ANALYSIS_PACK_DURABLE_STORE_SCHEMA_VERSION,
            "bundle_id": bundle.bundle_id,
            "stored_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "raw_article_text_stored": False,
            "raw_provider_payload_stored": False,
            "secret_values_stored": False,
            "bundle": bundle.model_dump(mode="json"),
        }
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        temp_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(self.storage_path)

    def _load_bundle(self) -> AnalysisPackImportBundle | None:
        if not self.storage_path.exists():
            return None
        try:
            envelope = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if envelope.get("schema_version") != ANALYSIS_PACK_DURABLE_STORE_SCHEMA_VERSION:
                return None
            bundle_payload = envelope.get("bundle")
            if not isinstance(bundle_payload, dict):
                return None
            bundle = AnalysisPackImportBundle.model_validate(bundle_payload)
            if validate_analysis_pack_import_bundle(bundle, now=bundle.generated_at):
                return None
            return bundle
        except Exception:
            return None


def build_analysis_pack_repository_from_env(env: dict[str, str] | None = None) -> AnalysisPackRepository:
    source = os.environ if env is None else env
    storage_path = (source.get("ANALYSIS_PACK_REPOSITORY_PATH") or source.get("LTT_ANALYSIS_PACK_REPOSITORY_PATH") or "").strip()
    if storage_path:
        return DurableAnalysisPackRepository(storage_path)
    return AnalysisPackRepository()


_ANALYSIS_PACK_REPOSITORY = build_analysis_pack_repository_from_env()


def analysis_pack_repository() -> AnalysisPackRepository:
    return _ANALYSIS_PACK_REPOSITORY


def configure_analysis_pack_repository(repository: AnalysisPackRepository | None) -> None:
    global _ANALYSIS_PACK_REPOSITORY
    _ANALYSIS_PACK_REPOSITORY = repository or build_analysis_pack_repository_from_env()


def build_backend_generated_metadata() -> AnalysisPackRuntimeMetadata:
    return AnalysisPackRuntimeMetadata(
        analysis_source="backend_generated",
        validation_status="not_applicable",
    )


def build_deterministic_fixture_metadata() -> AnalysisPackRuntimeMetadata:
    return AnalysisPackRuntimeMetadata(
        analysis_source="deterministic_fixture",
        validation_status="passed",
    )


def compute_analysis_pack_bundle_checksum(bundle: AnalysisPackImportBundle) -> str:
    payload = bundle.model_copy(
        deep=True,
        update={
            "validation": bundle.validation.model_copy(update={"checksum": None})
        },
    ).model_dump(mode="json")
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_analysis_pack_import_bundle(
    bundle: AnalysisPackImportBundle,
    *,
    now: datetime | str | None = None,
) -> list[str]:
    reason_codes: list[str] = []
    if bundle.schema_version != ANALYSIS_PACK_IMPORT_BUNDLE_SCHEMA_VERSION:
        reason_codes.append("unsupported_bundle_schema")
    if bundle.market_context_pack_schema_version != MARKET_CONTEXT_PACK_SCHEMA_VERSION:
        reason_codes.append("unsupported_market_context_pack_schema")
    if bundle.validation.validation_status != "passed":
        reason_codes.append("bundle_validation_not_passed")
    if bundle.validation.validator_version != ANALYSIS_PACK_VALIDATOR_VERSION:
        reason_codes.append("unsupported_validator_version")
    if bundle.validation.checksum and bundle.validation.checksum != compute_analysis_pack_bundle_checksum(bundle):
        reason_codes.append("checksum_mismatch")
    if bundle.raw_article_text_collected:
        reason_codes.append("raw_article_text_collected")
    if bundle.raw_provider_payload_exposed:
        reason_codes.append("raw_provider_payload_exposed")
    if _contains_forbidden_value_marker(bundle):
        reason_codes.append("forbidden_raw_or_secret_value")
    if _contains_visible_persona_label(bundle):
        reason_codes.append("visible_persona_label")
    if not _is_fresh(bundle, now=now):
        reason_codes.append("stale_or_expired")
    if bundle.economic_indicators is not None:
        reason_codes.extend(_validate_economic_indicators(bundle.economic_indicators))
    reason_codes.extend(_validate_source_sets(bundle))
    return list(dict.fromkeys(reason_codes))


def build_economic_indicators_pack(
    *,
    metadata: AnalysisPackRuntimeMetadata | None = None,
) -> EconomicIndicatorsPackResponse:
    rows = [
        ("gdp", "Gross Domestic Product", EconomicIndicatorCategory.official_historical_actual, "2.0%", 2.0, "percent annualized", "2026-Q1", "2026-04-30", "BEA", "https://www.bea.gov/", "up"),
        ("cpi", "Consumer Price Index", EconomicIndicatorCategory.official_historical_actual, "3.3%", 3.3, "percent year over year", "2026-03", "2026-04-10", "BLS", "https://www.bls.gov/cpi/", "up"),
        ("ppi", "Producer Price Index", EconomicIndicatorCategory.official_historical_actual, "4.0%", 4.0, "percent year over year", "2026-03", "2026-04-11", "BLS", "https://www.bls.gov/ppi/", "up"),
        ("retail_sales", "Retail Sales", EconomicIndicatorCategory.official_historical_actual, "1.7%", 1.7, "percent month over month", "2026-03", "2026-04-15", "U.S. Census Bureau", "https://www.census.gov/retail/", "up"),
        ("nonfarm_payrolls", "Nonfarm Payrolls", EconomicIndicatorCategory.official_historical_actual, "115,000", 115000.0, "jobs", "2026-04", "2026-05-01", "BLS", "https://www.bls.gov/ces/", "up"),
        ("unemployment", "Unemployment Rate", EconomicIndicatorCategory.official_historical_actual, "4.3%", 4.3, "percent", "2026-04", "2026-05-01", "BLS", "https://www.bls.gov/cps/", "neutral"),
        ("jobless_claims", "Initial Jobless Claims", EconomicIndicatorCategory.official_historical_actual, "200,000", 200000.0, "claims", "2026-05-02", "2026-05-07", "U.S. Department of Labor", "https://www.dol.gov/ui/data.pdf", "up"),
        ("m2", "M2 Money Supply", EconomicIndicatorCategory.official_historical_actual, "22.69T", 22.69, "USD trillions", "2026-03", "2026-04-22", "Federal Reserve", "https://www.federalreserve.gov/releases/h6/", "up"),
        ("credit_card_delinquency", "Credit Card Delinquency Rate", EconomicIndicatorCategory.official_historical_actual, "2.94%", 2.94, "percent", "2026-Q1", "2026-05-01", "Federal Reserve", "https://www.federalreserve.gov/releases/chargeoff/", "neutral"),
        ("private_investment", "Real Private Fixed Investment", EconomicIndicatorCategory.official_historical_actual, "2.9%", 2.9, "percent annualized", "2026-Q1", "2026-04-30", "BEA", "https://www.bea.gov/data/gdp/gross-domestic-product", "up"),
        ("treasury_10y", "10-Year Treasury Yield", EconomicIndicatorCategory.official_historical_actual, "4.43%", 4.43, "percent", "2026-05-07", "2026-05-07", "U.S. Treasury", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", "up"),
        ("treasury_3m", "3-Month Treasury Yield", EconomicIndicatorCategory.official_historical_actual, "3.68%", 3.68, "percent", "2026-05-07", "2026-05-07", "U.S. Treasury", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", "up"),
        ("dxy", "U.S. Dollar Index (DXY)", EconomicIndicatorCategory.market_reference, "97.80", 97.8, "index level", "2026-05-07", "2026-05-07", "Market reference fixture", "local://fixtures/economic-indicators/dxy", "down"),
        ("vix", "Cboe Volatility Index (VIX)", EconomicIndicatorCategory.market_reference, "17.19", 17.19, "index level", "2026-05-07", "2026-05-07", "Market reference fixture", "local://fixtures/economic-indicators/vix", "down"),
        ("wti_oil", "WTI Crude Oil", EconomicIndicatorCategory.market_reference, "120.50", 120.5, "USD per barrel", "2026-05-09", "2026-05-09", "Market reference fixture", "local://fixtures/economic-indicators/wti", "up"),
    ]

    items: list[EconomicIndicatorItem] = []
    citations: list[Citation] = []
    sources: list[SourceDocument] = []
    for row in rows:
        item, citation, source = _build_indicator_item(*row)
        items.append(item)
        citations.append(citation)
        sources.append(source)

    return EconomicIndicatorsPackResponse(
        state=WeeklyNewsContractState.available,
        region="US",
        as_of_date="2026-05-10",
        items=items,
        citations=citations,
        source_documents=sources,
        analysis_pack_metadata=metadata or build_deterministic_fixture_metadata(),
        no_live_external_calls=True,
        stable_facts_are_separate=True,
    )


def build_fixture_analysis_pack_import_bundle(
    *,
    bundle_id: str = "fixture-analysis-bundle-2026-05-10",
    generated_at: str = "2026-05-10T12:00:00Z",
    freshness_expires_at: str = "2026-05-17T12:00:00Z",
    ticker: str = "QQQ",
) -> AnalysisPackImportBundle:
    market = build_market_news_response()
    market = market.model_copy(update={"analysis_pack_metadata": None})
    overview = generate_asset_overview(ticker)
    weekly = WeeklyNewsResponse(
        asset=overview.asset,
        state=overview.state,
        weekly_news_focus=overview.weekly_news_focus,
        ai_comprehensive_analysis=_safe_importable_ai_analysis(overview.ai_comprehensive_analysis),
    )
    economic = build_economic_indicators_pack(metadata=None)
    bundle = AnalysisPackImportBundle(
        bundle_id=bundle_id,
        generated_at=generated_at,
        freshness_expires_at=freshness_expires_at,
        prompt_version="codex-assisted-analysis-pack-prompt-v1",
        validation=AnalysisPackValidationMetadata(
            validation_status="passed",
            validator_version=ANALYSIS_PACK_VALIDATOR_VERSION,
            checked_at=generated_at,
        ),
        market_context_pack=market,
        ticker_packs={ticker.upper(): weekly},
        economic_indicators=economic,
        source_documents=[*market.market_news_focus.source_documents, *economic.source_documents],
        citations=[*market.market_news_focus.citations, *economic.citations],
        validation_metadata={
            "no_visible_persona_labels": True,
            "no_raw_article_or_provider_payload_storage": True,
            "normal_ci_no_live_external_calls": True,
        },
        checksums={},
        longer_ticker_candidate_history={
            ticker.upper(): [
                {
                    "candidate_id": f"{ticker.upper()}-fixture-dedupe-candidate",
                    "dedupe_only": True,
                    "may_support_current_claims": False,
                }
            ]
        },
    )
    checksum = compute_analysis_pack_bundle_checksum(bundle)
    return bundle.model_copy(update={"validation": bundle.validation.model_copy(update={"checksum": checksum})})


def _runtime_metadata(bundle: AnalysisPackImportBundle) -> AnalysisPackRuntimeMetadata:
    return AnalysisPackRuntimeMetadata(
        analysis_source="imported_local_pack",
        freshness_expires_at=bundle.freshness_expires_at,
        import_bundle_id=bundle.bundle_id,
        validation_status="passed",
    )


def _safe_importable_ai_analysis(
    analysis: AIComprehensiveAnalysisResponse | None,
) -> AIComprehensiveAnalysisResponse:
    if analysis is not None:
        return analysis
    overview = generate_asset_overview("QQQ")
    if overview.ai_comprehensive_analysis is None:
        raise ValueError("Fixture QQQ overview must include AI Comprehensive Analysis response.")
    return overview.ai_comprehensive_analysis


def _build_indicator_item(
    indicator_id: str,
    name: str,
    category: EconomicIndicatorCategory,
    value: str,
    numeric_value: float | None,
    unit: str | None,
    period: str,
    published_at: str,
    publisher: str,
    url: str,
    trend: str,
) -> tuple[EconomicIndicatorItem, Citation, SourceDocument]:
    source_document_id = f"src_economic_{indicator_id}"
    citation_id = f"c_economic_{indicator_id}"
    retrieved_at = "2026-05-10T12:00:00Z"
    is_market_reference = category is EconomicIndicatorCategory.market_reference
    source_quality = SourceQuality.provider if is_market_reference else SourceQuality.official
    source_type = "market_reference" if is_market_reference else "official_macro_release"
    source = SourceDocument(
        source_document_id=source_document_id,
        source_type=source_type,
        title=f"{name} source record",
        publisher=publisher,
        url=url,
        published_at=published_at,
        as_of_date=period,
        retrieved_at=retrieved_at,
        freshness_state=FreshnessState.fresh,
        is_official=not is_market_reference,
        supporting_passage=(
            f"Deterministic economic indicator fixture for {name}; imported bundles should replace this "
            "with the latest validated official or source-labeled record."
        ),
        source_quality=source_quality,
        allowlist_status=SourceAllowlistStatus.allowed,
        source_use_policy=SourceUsePolicy.summary_allowed,
        permitted_operations=_SUMMARY_ONLY_OPERATIONS,
        source_identity=publisher.lower().replace(" ", "_"),
        storage_rights=SourceStorageRights.summary_allowed,
        export_rights=SourceExportRights.excerpts_allowed,
        review_status=SourceReviewStatus.approved,
        approval_rationale="Deterministic fixture source validates Economic Indicators pack structure without live calls.",
        parser_status=SourceParserStatus.parsed,
    )
    citation = Citation(
        citation_id=citation_id,
        source_document_id=source_document_id,
        title=source.title,
        publisher=publisher,
        freshness_state=FreshnessState.fresh,
    )
    item = EconomicIndicatorItem(
        indicator_id=indicator_id,
        name=name,
        category=category,
        value=value,
        numeric_value=numeric_value,
        unit=unit,
        period=period,
        as_of_date=period,
        published_at=published_at,
        retrieved_at=retrieved_at,
        source=WeeklyNewsSourceMetadata(
            source_document_id=source_document_id,
            source_type=source_type,
            title=source.title,
            publisher=publisher,
            url=url,
            published_at=published_at,
            as_of_date=period,
            retrieved_at=retrieved_at,
            freshness_state=FreshnessState.fresh,
            is_official=not is_market_reference,
            source_quality=source_quality,
            allowlist_status=SourceAllowlistStatus.allowed,
            source_use_policy=SourceUsePolicy.summary_allowed,
        ),
        freshness_state=FreshnessState.fresh,
        trend_direction=EconomicIndicatorTrendDirection(trend),
        citation_ids=[citation_id],
        source_document_ids=[source_document_id],
        evidence_state=EvidenceState.supported,
    )
    return item, citation, source


def _validate_economic_indicators(pack: EconomicIndicatorsPackResponse) -> list[str]:
    reason_codes: list[str] = []
    if pack.schema_version != ECONOMIC_INDICATORS_PACK_SCHEMA_VERSION:
        reason_codes.append("unsupported_economic_indicators_schema")
    if pack.region != "US":
        reason_codes.append("economic_indicators_region_not_us")
    source_ids = {source.source_document_id for source in pack.source_documents}
    citation_ids = {citation.citation_id for citation in pack.citations}
    required_ids = {
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
    present_ids = {item.indicator_id for item in pack.items}
    missing_required = sorted(required_ids - present_ids)
    if missing_required:
        reason_codes.append("economic_indicators_missing_required_rows")
    for item in pack.items:
        if not item.citation_ids or not set(item.citation_ids) <= citation_ids:
            reason_codes.append("economic_indicator_missing_or_unknown_citation")
        if not item.source_document_ids or not set(item.source_document_ids) <= source_ids:
            reason_codes.append("economic_indicator_missing_or_unknown_source")
        if item.source.source_use_policy == SourceUsePolicy.rejected:
            reason_codes.append("economic_indicator_rejected_source_policy")
    return reason_codes


def _validate_source_sets(bundle: AnalysisPackImportBundle) -> list[str]:
    reason_codes: list[str] = []
    source_documents = list(bundle.source_documents)
    citations = list(bundle.citations)
    if bundle.market_context_pack is not None:
        source_documents.extend(bundle.market_context_pack.market_news_focus.source_documents)
        citations.extend(bundle.market_context_pack.market_news_focus.citations)
    if bundle.economic_indicators is not None:
        source_documents.extend(bundle.economic_indicators.source_documents)
        citations.extend(bundle.economic_indicators.citations)
    for weekly in bundle.ticker_packs.values():
        source_documents.extend(weekly.weekly_news_focus.source_documents)
        citations.extend(weekly.weekly_news_focus.citations)

    source_ids = {source.source_document_id for source in source_documents}
    for citation in citations:
        if citation.source_document_id not in source_ids:
            reason_codes.append("citation_source_document_missing")
    for source in source_documents:
        if source.source_use_policy == SourceUsePolicy.rejected:
            reason_codes.append("rejected_source_policy")
        if source.allowlist_status in {SourceAllowlistStatus.rejected, SourceAllowlistStatus.not_allowlisted}:
            reason_codes.append("source_not_allowed")
        if source.review_status == SourceReviewStatus.rejected:
            reason_codes.append("source_review_rejected")
    return reason_codes


def _is_fresh(bundle: AnalysisPackImportBundle, *, now: datetime | str | None = None) -> bool:
    current = _coerce_datetime(now) if now is not None else datetime.now(timezone.utc)
    generated_at = _coerce_datetime(bundle.generated_at)
    freshness_expires_at = _coerce_datetime(bundle.freshness_expires_at)
    if current > freshness_expires_at:
        return False
    return (current - generated_at).total_seconds() <= ANALYSIS_PACK_MAX_AGE_DAYS * 24 * 60 * 60


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _contains_forbidden_value_marker(bundle: AnalysisPackImportBundle) -> bool:
    for value in _iter_text_values(bundle.model_dump(mode="json")):
        lowered = value.lower()
        if any(marker in lowered for marker in _FORBIDDEN_VALUE_MARKERS):
            return True
    return False


def _contains_visible_persona_label(bundle: AnalysisPackImportBundle) -> bool:
    for value in _iter_text_values(bundle.model_dump(mode="json")):
        if _VISIBLE_PERSONA_PATTERN.search(value):
            return True
    return False


def _iter_text_values(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _iter_text_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_text_values(child)
