from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import Any, Protocol
from urllib.error import URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from backend.models import (
    Citation,
    EconomicIndicatorCategory,
    EconomicIndicatorItem,
    EconomicIndicatorsPackResponse,
    EconomicIndicatorTrendDirection,
    EvidenceState,
    FreshnessState,
    SourceAllowlistStatus,
    SourceDocument,
    SourceExportRights,
    SourceOperationPermissions,
    SourceParserStatus,
    SourceQuality,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
    WeeklyNewsContractState,
    WeeklyNewsSourceMetadata,
)


LIVE_ECONOMIC_INDICATORS_BOUNDARY = "analysis-pack-live-economic-indicators-v1"
FRED_ALLOWED_HOST = "fred.stlouisfed.org"
FRED_USER_AGENT = "Mozilla/5.0 (compatible; learn-the-ticker/0.1; +https://example.local)"


class EconomicIndicatorFetchError(RuntimeError):
    pass


class EconomicIndicatorFetcher(Protocol):
    no_live_external_calls: bool

    def fetch_text(self, url: str, *, timeout_seconds: int = 15) -> str:
        ...


@dataclass(frozen=True)
class UrlLibEconomicIndicatorFetcher:
    no_live_external_calls: bool = False
    max_bytes: int = 1_000_000
    user_agent: str = FRED_USER_AGENT

    def fetch_text(self, url: str, *, timeout_seconds: int = 15) -> str:
        _validate_fred_url(url)
        request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "text/csv"})
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - URL is adapter-owned and host-allowlisted.
                payload = response.read(self.max_bytes + 1)
        except URLError as exc:
            raise EconomicIndicatorFetchError("economic_indicator_live_fetch_failed") from exc
        if len(payload) > self.max_bytes:
            raise EconomicIndicatorFetchError("economic_indicator_payload_too_large")
        return payload.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class _SeriesSpec:
    indicator_id: str
    series_id: str
    name: str
    category: EconomicIndicatorCategory
    unit: str
    publisher: str
    transform: str


_SERIES_SPECS = (
    _SeriesSpec("gdp", "GDP", "Gross Domestic Product", EconomicIndicatorCategory.official_historical_actual, "USD billions annualized", "BEA via FRED", "level"),
    _SeriesSpec("cpi", "CPIAUCSL", "Consumer Price Index", EconomicIndicatorCategory.official_historical_actual, "percent year over year", "BLS via FRED", "yoy_percent"),
    _SeriesSpec("ppi", "PPIACO", "Producer Price Index", EconomicIndicatorCategory.official_historical_actual, "percent year over year", "BLS via FRED", "yoy_percent"),
    _SeriesSpec("retail_sales", "RSAFS", "Retail Sales", EconomicIndicatorCategory.official_historical_actual, "percent month over month", "U.S. Census Bureau via FRED", "mom_percent"),
    _SeriesSpec("nonfarm_payrolls", "PAYEMS", "Nonfarm Payrolls", EconomicIndicatorCategory.official_historical_actual, "jobs monthly change", "BLS via FRED", "monthly_change_thousands_to_jobs"),
    _SeriesSpec("unemployment", "UNRATE", "Unemployment Rate", EconomicIndicatorCategory.official_historical_actual, "percent", "BLS via FRED", "level"),
    _SeriesSpec("jobless_claims", "ICSA", "Initial Jobless Claims", EconomicIndicatorCategory.official_historical_actual, "claims", "U.S. Department of Labor via FRED", "level"),
    _SeriesSpec("m2", "M2SL", "M2 Money Supply", EconomicIndicatorCategory.official_historical_actual, "USD billions", "Federal Reserve via FRED", "level"),
    _SeriesSpec("credit_card_delinquency", "DRCCLACBS", "Credit Card Delinquency Rate", EconomicIndicatorCategory.official_historical_actual, "percent", "Federal Reserve via FRED", "level"),
    _SeriesSpec("private_investment", "GPDIC1", "Real Private Domestic Investment", EconomicIndicatorCategory.official_historical_actual, "percent quarter over quarter annualized", "BEA via FRED", "qoq_annualized_percent"),
    _SeriesSpec("treasury_10y", "DGS10", "10-Year Treasury Yield", EconomicIndicatorCategory.official_historical_actual, "percent", "U.S. Treasury via FRED", "level"),
    _SeriesSpec("treasury_3m", "DGS3MO", "3-Month Treasury Yield", EconomicIndicatorCategory.official_historical_actual, "percent", "U.S. Treasury via FRED", "level"),
    _SeriesSpec("dxy", "DTWEXBGS", "U.S. Dollar Index Proxy", EconomicIndicatorCategory.market_reference, "index level", "Federal Reserve via FRED", "level"),
    _SeriesSpec("vix", "VIXCLS", "Cboe Volatility Index (VIX)", EconomicIndicatorCategory.market_reference, "index level", "Cboe via FRED", "level"),
    _SeriesSpec("wti_oil", "DCOILWTICO", "WTI Crude Oil", EconomicIndicatorCategory.market_reference, "USD per barrel", "EIA via FRED", "level"),
)


def build_live_economic_indicators_pack(
    *,
    generated_at: str,
    fetcher: EconomicIndicatorFetcher | None = None,
    timeout_seconds: int = 15,
) -> EconomicIndicatorsPackResponse:
    source_fetcher = fetcher or UrlLibEconomicIndicatorFetcher()
    retrieved_at = generated_at
    items: list[EconomicIndicatorItem] = []
    citations: list[Citation] = []
    sources: list[SourceDocument] = []

    for spec in _SERIES_SPECS:
        observations = _fetch_series_observations(spec.series_id, fetcher=source_fetcher, timeout_seconds=timeout_seconds)
        if len(observations) < 2:
            continue
        item, citation, source = _item_from_observations(spec, observations, retrieved_at=retrieved_at)
        items.append(item)
        citations.append(citation)
        sources.append(source)

    if not items:
        raise EconomicIndicatorFetchError("economic_indicator_live_series_unavailable")

    latest_dates = [item.as_of_date for item in items if item.as_of_date]
    return EconomicIndicatorsPackResponse(
        state=WeeklyNewsContractState.available,
        region="US",
        as_of_date=max(latest_dates) if latest_dates else generated_at[:10],
        items=items,
        citations=citations,
        source_documents=sources,
        analysis_pack_metadata=None,
        no_live_external_calls=source_fetcher.no_live_external_calls,
        stable_facts_are_separate=True,
    )


def parse_fred_csv(text: str) -> list[tuple[str, float]]:
    observations: list[tuple[str, float]] = []
    reader = csv.DictReader(StringIO(text))
    value_field = None
    if reader.fieldnames:
        value_field = next((field for field in reader.fieldnames if field not in {"observation_date", "DATE"}), None)
    for row in reader:
        date_value = str(row.get("observation_date") or row.get("DATE") or "").strip()
        raw_value = str(row.get("value") or row.get("VALUE") or (row.get(value_field) if value_field else "") or "").strip()
        if not date_value or raw_value in {"", "."}:
            continue
        try:
            observations.append((date_value, float(raw_value)))
        except ValueError:
            continue
    return observations


def _fetch_series_observations(
    series_id: str,
    *,
    fetcher: EconomicIndicatorFetcher,
    timeout_seconds: int,
) -> list[tuple[str, float]]:
    text = fetcher.fetch_text(_fred_csv_url(series_id), timeout_seconds=timeout_seconds)
    return parse_fred_csv(text)


def _item_from_observations(
    spec: _SeriesSpec,
    observations: list[tuple[str, float]],
    *,
    retrieved_at: str,
) -> tuple[EconomicIndicatorItem, Citation, SourceDocument]:
    current_date, current_value = observations[-1]
    previous_date, previous_value = observations[-2]
    transformed = _transform_value(spec.transform, observations)
    numeric_value = transformed if transformed is not None else current_value
    value = _format_indicator_value(numeric_value, spec.unit)
    trend = _trend_direction(numeric_value, _transform_value(spec.transform, observations[:-1]) or previous_value)
    source_document_id = f"src_economic_live_{spec.indicator_id}"
    citation_id = f"c_economic_live_{spec.indicator_id}"
    url = _fred_csv_url(spec.series_id)
    is_market_reference = spec.category is EconomicIndicatorCategory.market_reference
    source_quality = SourceQuality.provider if is_market_reference else SourceQuality.official
    source_type = "market_reference_time_series" if is_market_reference else "official_macro_time_series"
    source = SourceDocument(
        source_document_id=source_document_id,
        source_type=source_type,
        title=f"{spec.name} live time-series metadata",
        publisher=spec.publisher,
        url=url,
        published_at=current_date,
        as_of_date=current_date,
        retrieved_at=retrieved_at,
        freshness_state=FreshnessState.fresh,
        is_official=not is_market_reference,
        supporting_passage=(
            f"Latest {spec.series_id} observation used for {spec.name}; source stores metadata and computed value only."
        ),
        source_quality=source_quality,
        allowlist_status=SourceAllowlistStatus.allowed,
        source_use_policy=SourceUsePolicy.summary_allowed,
        permitted_operations=_SUMMARY_ONLY_OPERATIONS,
        source_identity=f"fred:{spec.series_id}",
        storage_rights=SourceStorageRights.summary_allowed,
        export_rights=SourceExportRights.excerpts_allowed,
        review_status=SourceReviewStatus.approved,
        approval_rationale="FRED CSV endpoint is used as a source-labeled structured time-series record for local operator packs.",
        parser_status=SourceParserStatus.parsed,
    )
    citation = Citation(
        citation_id=citation_id,
        source_document_id=source_document_id,
        title=source.title,
        publisher=spec.publisher,
        freshness_state=FreshnessState.fresh,
    )
    item = EconomicIndicatorItem(
        indicator_id=spec.indicator_id,
        name=spec.name,
        category=spec.category,
        value=value,
        numeric_value=round(numeric_value, 4),
        unit=spec.unit,
        period=current_date,
        as_of_date=current_date,
        published_at=current_date,
        retrieved_at=retrieved_at,
        source=WeeklyNewsSourceMetadata(
            source_document_id=source_document_id,
            source_type=source_type,
            title=source.title,
            publisher=spec.publisher,
            url=url,
            published_at=current_date,
            as_of_date=current_date,
            retrieved_at=retrieved_at,
            freshness_state=FreshnessState.fresh,
            is_official=not is_market_reference,
            source_quality=source_quality,
            allowlist_status=SourceAllowlistStatus.allowed,
            source_use_policy=SourceUsePolicy.summary_allowed,
        ),
        freshness_state=FreshnessState.fresh,
        trend_direction=trend,
        citation_ids=[citation_id],
        source_document_ids=[source_document_id],
        evidence_state=EvidenceState.supported,
    )
    return item, citation, source


def _transform_value(transform: str, observations: list[tuple[str, float]]) -> float | None:
    if not observations:
        return None
    latest = observations[-1][1]
    if transform == "level":
        return latest
    if transform == "yoy_percent":
        if len(observations) < 13 or observations[-13][1] == 0:
            return None
        return ((latest / observations[-13][1]) - 1.0) * 100.0
    if transform == "mom_percent":
        if len(observations) < 2 or observations[-2][1] == 0:
            return None
        return ((latest / observations[-2][1]) - 1.0) * 100.0
    if transform == "monthly_change_thousands_to_jobs":
        if len(observations) < 2:
            return None
        return (latest - observations[-2][1]) * 1000.0
    if transform == "qoq_annualized_percent":
        if len(observations) < 2 or observations[-2][1] == 0:
            return None
        return (((latest / observations[-2][1]) ** 4.0) - 1.0) * 100.0
    return latest


def _trend_direction(current: float, previous: float | None) -> EconomicIndicatorTrendDirection:
    if previous is None:
        return EconomicIndicatorTrendDirection.unknown
    if current > previous:
        return EconomicIndicatorTrendDirection.up
    if current < previous:
        return EconomicIndicatorTrendDirection.down
    return EconomicIndicatorTrendDirection.neutral


def _format_indicator_value(value: float, unit: str) -> str:
    if "percent" in unit:
        return f"{value:.2f}%"
    if "jobs" in unit or "claims" in unit:
        return f"{value:,.0f}"
    if abs(value) >= 1000:
        return f"{value:,.1f}"
    return f"{value:.2f}"


def _fred_csv_url(series_id: str) -> str:
    return f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={quote(series_id)}"


def _validate_fred_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise EconomicIndicatorFetchError("economic_indicator_source_url_invalid") from exc
    if parsed.scheme != "https":
        raise EconomicIndicatorFetchError("economic_indicator_source_url_scheme_blocked")
    if (parsed.hostname or "").lower() != FRED_ALLOWED_HOST:
        raise EconomicIndicatorFetchError("economic_indicator_source_host_blocked")


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
