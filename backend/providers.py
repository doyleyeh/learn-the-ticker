from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from backend.data import (
    ASSETS,
    ELIGIBLE_NOT_CACHED_ASSETS,
    OUT_OF_SCOPE_COMMON_STOCKS,
    STUB_TIMESTAMP,
    UNSUPPORTED_ASSETS,
    normalize_ticker,
)
from backend.models import (
    AssetIdentity,
    AssetStatus,
    AssetType,
    EvidenceState,
    FreshnessState,
    ProviderCapability,
    ProviderDataCategory,
    ProviderError,
    ProviderFact,
    ProviderKind,
    ProviderLicensing,
    ProviderRecentDevelopmentCandidate,
    ProviderRequestMetadata,
    ProviderResponse,
    ProviderResponseFreshness,
    ProviderResponseState,
    ProviderSourceAttribution,
    ProviderSourceUsage,
    SourceAllowlistStatus,
    SourceOperationPermissions,
    SourceQuality,
    SourceUsePolicy,
)
from backend.provider_adapters.sec_stock import (
    build_sec_stock_provider_response,
    sec_stock_fixture_for_ticker,
)
from backend.provider_adapters.etf_issuer import (
    build_etf_issuer_provider_response,
    etf_issuer_fixture_for_ticker,
)


NO_LIVE_EXTERNAL_CALLS = True
DEFAULT_PROVIDER_RETRIEVED_AT = STUB_TIMESTAMP


class ProviderAdapter(Protocol):
    provider_name: str
    provider_kind: ProviderKind
    default_data_category: ProviderDataCategory
    capability: ProviderCapability

    def fetch(self, request_metadata: ProviderRequestMetadata) -> ProviderResponse:
        ...


ProviderResponseBuilder = Callable[["MockProviderAdapter", ProviderRequestMetadata], ProviderResponse]


class MockProviderAdapter:
    def __init__(
        self,
        *,
        provider_name: str,
        provider_kind: ProviderKind,
        default_data_category: ProviderDataCategory,
        capability: ProviderCapability,
        response_builder: ProviderResponseBuilder,
    ) -> None:
        self.provider_name = provider_name
        self.provider_kind = provider_kind
        self.default_data_category = default_data_category
        self.capability = capability
        self._response_builder = response_builder

    def request(self, ticker: str, data_category: ProviderDataCategory | None = None) -> ProviderRequestMetadata:
        normalized = normalize_ticker(ticker)
        category = data_category or self.default_data_category
        return ProviderRequestMetadata(
            request_id=f"mock-{self.provider_kind.value}-{normalized.lower()}-{category.value}",
            requested_ticker=ticker,
            normalized_ticker=normalized,
            requested_at=DEFAULT_PROVIDER_RETRIEVED_AT,
            data_category=category,
        )

    def fetch(self, request_metadata: ProviderRequestMetadata) -> ProviderResponse:
        return self._response_builder(self, request_metadata)


def mock_sec_stock_adapter() -> MockProviderAdapter:
    return MockProviderAdapter(
        provider_name="Mock SEC EDGAR",
        provider_kind=ProviderKind.sec,
        default_data_category=ProviderDataCategory.canonical_stock_facts,
        capability=ProviderCapability(
            provider_name="Mock SEC EDGAR",
            provider_kind=ProviderKind.sec,
            data_categories=[ProviderDataCategory.canonical_stock_facts],
            supports_canonical_facts=True,
            requires_credentials=False,
            live_calls_allowed=False,
        ),
        response_builder=_build_sec_response,
    )


def mock_etf_issuer_adapter() -> MockProviderAdapter:
    return MockProviderAdapter(
        provider_name="Mock ETF Issuer",
        provider_kind=ProviderKind.etf_issuer,
        default_data_category=ProviderDataCategory.etf_issuer_facts,
        capability=ProviderCapability(
            provider_name="Mock ETF Issuer",
            provider_kind=ProviderKind.etf_issuer,
            data_categories=[ProviderDataCategory.etf_issuer_facts, ProviderDataCategory.etf_holdings_metadata],
            supports_canonical_facts=True,
            requires_credentials=False,
            live_calls_allowed=False,
        ),
        response_builder=_build_etf_issuer_response,
    )


def mock_market_reference_adapter() -> MockProviderAdapter:
    return MockProviderAdapter(
        provider_name="Mock Market Reference",
        provider_kind=ProviderKind.market_reference,
        default_data_category=ProviderDataCategory.market_reference,
        capability=ProviderCapability(
            provider_name="Mock Market Reference",
            provider_kind=ProviderKind.market_reference,
            data_categories=[ProviderDataCategory.asset_resolution, ProviderDataCategory.market_reference],
            supports_asset_resolution=True,
            supports_canonical_facts=True,
            requires_credentials=False,
            live_calls_allowed=False,
        ),
        response_builder=_build_market_reference_response,
    )


def mock_recent_development_adapter() -> MockProviderAdapter:
    return MockProviderAdapter(
        provider_name="Mock Recent Development Provider",
        provider_kind=ProviderKind.recent_development,
        default_data_category=ProviderDataCategory.recent_developments,
        capability=ProviderCapability(
            provider_name="Mock Recent Development Provider",
            provider_kind=ProviderKind.recent_development,
            data_categories=[ProviderDataCategory.recent_developments],
            supports_recent_developments=True,
            requires_credentials=False,
            live_calls_allowed=False,
        ),
        response_builder=_build_recent_development_response,
    )


def get_mock_provider_adapters() -> dict[ProviderKind, ProviderAdapter]:
    return {
        ProviderKind.sec: mock_sec_stock_adapter(),
        ProviderKind.etf_issuer: mock_etf_issuer_adapter(),
        ProviderKind.market_reference: mock_market_reference_adapter(),
        ProviderKind.recent_development: mock_recent_development_adapter(),
    }


def fetch_mock_provider_response(
    provider_kind: ProviderKind,
    ticker: str,
    data_category: ProviderDataCategory | None = None,
) -> ProviderResponse:
    adapters = get_mock_provider_adapters()
    adapter = adapters[provider_kind]
    if isinstance(adapter, MockProviderAdapter):
        return adapter.fetch(adapter.request(ticker, data_category))
    request = ProviderRequestMetadata(
        request_id=f"mock-{provider_kind.value}-{normalize_ticker(ticker).lower()}",
        requested_ticker=ticker,
        normalized_ticker=normalize_ticker(ticker),
        requested_at=DEFAULT_PROVIDER_RETRIEVED_AT,
        data_category=data_category or adapter.default_data_category,
    )
    return adapter.fetch(request)


def _build_sec_response(adapter: MockProviderAdapter, request: ProviderRequestMetadata) -> ProviderResponse:
    ticker = request.normalized_ticker
    licensing = _official_public_licensing(adapter.provider_name)

    if sec_stock_fixture_for_ticker(ticker) is not None:
        return build_sec_stock_provider_response(adapter, request, licensing)

    if ticker in ELIGIBLE_NOT_CACHED_ASSETS:
        return _eligible_not_cached_response(adapter, request, licensing)
    if ticker in UNSUPPORTED_ASSETS:
        return _unsupported_response(adapter, request, licensing)
    if ticker in OUT_OF_SCOPE_COMMON_STOCKS:
        return _out_of_scope_response(adapter, request, licensing)
    return _unknown_response(adapter, request, licensing)


def _build_etf_issuer_response(adapter: MockProviderAdapter, request: ProviderRequestMetadata) -> ProviderResponse:
    ticker = request.normalized_ticker
    licensing = _official_public_licensing(adapter.provider_name)

    if etf_issuer_fixture_for_ticker(ticker) is not None:
        return build_etf_issuer_provider_response(adapter, request, licensing)

    if ticker in ELIGIBLE_NOT_CACHED_ASSETS:
        return _eligible_not_cached_response(adapter, request, licensing)
    if ticker in UNSUPPORTED_ASSETS:
        return _unsupported_response(adapter, request, licensing)
    if ticker in OUT_OF_SCOPE_COMMON_STOCKS:
        return _out_of_scope_response(adapter, request, licensing)
    return _unknown_response(adapter, request, licensing)


def _build_market_reference_response(adapter: MockProviderAdapter, request: ProviderRequestMetadata) -> ProviderResponse:
    ticker = request.normalized_ticker
    licensing = _restricted_market_licensing(adapter.provider_name)

    if ticker in ASSETS or ticker in ELIGIBLE_NOT_CACHED_ASSETS:
        asset = _known_asset_identity(ticker)
        state = ProviderResponseState.supported if ticker in ASSETS else ProviderResponseState.eligible_not_cached
        source = _source(
            adapter=adapter,
            ticker=ticker,
            data_category=request.data_category,
            source_document_id=f"provider_market_{ticker.lower()}_reference",
            source_type="structured_market_reference",
            title=f"{ticker} structured market/reference deterministic provider fixture",
            publisher="Mock Market Reference",
            url=None,
            published_at=None,
            as_of_date="2026-04-01",
            freshness_state=FreshnessState.fresh,
            is_official=False,
            usage=ProviderSourceUsage.structured_reference,
            source_rank=4,
            can_support_canonical_facts=True,
            can_support_recent_developments=False,
            licensing=licensing,
        )
        facts = [
            _fact(
                ticker=ticker,
                data_category=ProviderDataCategory.asset_resolution,
                fact_id=f"provider_fact_{ticker.lower()}_asset_resolution",
                field_name="asset_resolution",
                value={
                    "ticker": asset.ticker if asset else ticker,
                    "asset_type": asset.asset_type.value if asset else "unknown",
                    "exchange": asset.exchange if asset else None,
                    "eligible_not_cached": ticker not in ASSETS,
                },
                as_of_date="2026-04-01",
                source_document_ids=[source.source_document_id],
                citation_ids=[f"provider_cite_{ticker.lower()}_market_reference"],
                fact_layer="structured_reference",
            )
        ]
        message = (
            f"Deterministic structured market/reference response for {ticker}; "
            "restricted provider payloads are not exportable."
        )
        return _response(
            adapter=adapter,
            request=request,
            state=state,
            licensing=licensing,
            asset=asset,
            source_attributions=[source],
            facts=facts,
            freshness_state=FreshnessState.fresh,
            as_of_date="2026-04-01",
            message=message,
        )

    if ticker in UNSUPPORTED_ASSETS:
        return _unsupported_response(adapter, request, licensing)
    if ticker in OUT_OF_SCOPE_COMMON_STOCKS:
        return _out_of_scope_response(adapter, request, licensing)
    return _unknown_response(adapter, request, licensing)


def _build_recent_development_response(adapter: MockProviderAdapter, request: ProviderRequestMetadata) -> ProviderResponse:
    ticker = request.normalized_ticker
    licensing = _recent_context_licensing(adapter.provider_name)

    if ticker == "AAPL":
        source = _source(
            adapter=adapter,
            ticker=ticker,
            data_category=ProviderDataCategory.recent_developments,
            source_document_id="provider_recent_aapl_filing_review",
            source_type="sec_filing_recent_context",
            title="Apple Inc. recent filing review deterministic provider fixture",
            publisher="U.S. SEC",
            url="https://www.sec.gov/Archives/edgar/data/320193/provider-fixture",
            published_at="2026-04-01",
            as_of_date=None,
            freshness_state=FreshnessState.fresh,
            is_official=True,
            usage=ProviderSourceUsage.recent_context,
            source_rank=1,
            can_support_canonical_facts=False,
            can_support_recent_developments=True,
            licensing=licensing,
        )
        candidate = ProviderRecentDevelopmentCandidate(
            event_id="provider_recent_aapl_filing_review_2026",
            asset_ticker=ticker,
            event_type="filing_review",
            title="Recent SEC filing review fixture",
            summary="A deterministic fixture marks a recent SEC filing review as recent context only.",
            event_date="2026-04-01",
            source_date="2026-04-01",
            retrieved_at=DEFAULT_PROVIDER_RETRIEVED_AT,
            freshness_state=FreshnessState.fresh,
            source_document_id=source.source_document_id,
            citation_ids=["provider_cite_aapl_recent_filing_review"],
            is_high_signal=True,
            can_overwrite_canonical_facts=False,
        )
        return _response(
            adapter=adapter,
            request=request,
            state=ProviderResponseState.supported,
            licensing=licensing,
            asset=_known_asset_identity(ticker),
            source_attributions=[source],
            recent_developments=[candidate],
            freshness_state=FreshnessState.fresh,
            as_of_date="2026-04-01",
            message="Deterministic AAPL recent-development candidate; it is recent context only.",
        )

    if ticker in {"VOO", "QQQ"}:
        source = _source(
            adapter=adapter,
            ticker=ticker,
            data_category=ProviderDataCategory.recent_developments,
            source_document_id=f"provider_recent_{ticker.lower()}_no_high_signal_review",
            source_type="recent_development_review",
            title=f"{ticker} no-high-signal recent-development review fixture",
            publisher=adapter.provider_name,
            url=None,
            published_at=None,
            as_of_date="2026-04-20",
            freshness_state=FreshnessState.fresh,
            is_official=False,
            usage=ProviderSourceUsage.recent_context,
            source_rank=6,
            can_support_canonical_facts=False,
            can_support_recent_developments=True,
            licensing=licensing,
        )
        return _response(
            adapter=adapter,
            request=request,
            state=ProviderResponseState.no_high_signal,
            licensing=licensing,
            asset=_known_asset_identity(ticker),
            source_attributions=[source],
            freshness_state=FreshnessState.fresh,
            as_of_date="2026-04-20",
            message=f"No supported high-signal recent-development candidate is present for {ticker}.",
        )

    if ticker in ELIGIBLE_NOT_CACHED_ASSETS:
        return _eligible_not_cached_response(adapter, request, licensing)
    if ticker in UNSUPPORTED_ASSETS:
        return _unsupported_response(adapter, request, licensing)
    if ticker in OUT_OF_SCOPE_COMMON_STOCKS:
        return _out_of_scope_response(adapter, request, licensing)
    return _unavailable_response(adapter, request, licensing)


def _known_asset_identity(ticker: str) -> AssetIdentity | None:
    if ticker in ASSETS:
        return ASSETS[ticker]["identity"].model_copy(deep=True)
    eligible = ELIGIBLE_NOT_CACHED_ASSETS.get(ticker)
    if eligible:
        return AssetIdentity(
            ticker=ticker,
            name=str(eligible["name"]),
            asset_type=AssetType(str(eligible["asset_type"])),
            exchange=str(eligible["exchange"]) if eligible.get("exchange") else None,
            issuer=str(eligible["issuer"]) if eligible.get("issuer") else None,
            status=AssetStatus.supported,
            supported=True,
        )
    if ticker in UNSUPPORTED_ASSETS:
        return AssetIdentity(
            ticker=ticker,
            name=ticker,
            asset_type=AssetType.unsupported,
            status=AssetStatus.unsupported,
            supported=False,
        )
    out_of_scope = OUT_OF_SCOPE_COMMON_STOCKS.get(ticker)
    if out_of_scope:
        return AssetIdentity(
            ticker=ticker,
            name=str(out_of_scope["name"]),
            asset_type=AssetType.stock,
            exchange=str(out_of_scope["exchange"]) if out_of_scope.get("exchange") else None,
            status=AssetStatus.unknown,
            supported=False,
        )
    return None


def _fact(
    *,
    ticker: str,
    data_category: ProviderDataCategory,
    fact_id: str,
    field_name: str,
    value: object,
    source_document_ids: list[str],
    citation_ids: list[str],
    fact_layer: str,
    unit: str | None = None,
    as_of_date: str | None = "2026-04-01",
) -> ProviderFact:
    return ProviderFact(
        fact_id=fact_id,
        asset_ticker=ticker,
        data_category=data_category,
        field_name=field_name,
        value=value,
        unit=unit,
        as_of_date=as_of_date,
        retrieved_at=DEFAULT_PROVIDER_RETRIEVED_AT,
        freshness_state=FreshnessState.fresh,
        evidence_state=EvidenceState.supported,
        source_document_ids=source_document_ids,
        citation_ids=citation_ids,
        fact_layer=fact_layer,  # type: ignore[arg-type]
        uses_glossary_as_support=False,
    )


def _source(
    *,
    adapter: MockProviderAdapter,
    ticker: str,
    data_category: ProviderDataCategory,
    source_document_id: str,
    source_type: str,
    title: str,
    publisher: str,
    url: str | None,
    published_at: str | None,
    as_of_date: str | None,
    freshness_state: FreshnessState,
    is_official: bool,
    usage: ProviderSourceUsage,
    source_rank: int,
    can_support_canonical_facts: bool,
    can_support_recent_developments: bool,
    licensing: ProviderLicensing,
) -> ProviderSourceAttribution:
    return ProviderSourceAttribution(
        source_document_id=source_document_id,
        asset_ticker=ticker,
        source_type=source_type,
        title=title,
        publisher=publisher,
        url=url,
        published_at=published_at,
        as_of_date=as_of_date,
        retrieved_at=DEFAULT_PROVIDER_RETRIEVED_AT,
        freshness_state=freshness_state,
        is_official=is_official,
        provider_name=adapter.provider_name,
        provider_kind=adapter.provider_kind,
        data_category=data_category,
        usage=usage,
        source_rank=source_rank,
        can_support_canonical_facts=can_support_canonical_facts,
        can_support_recent_developments=can_support_recent_developments,
        licensing=licensing,
        source_quality=(
            SourceQuality.issuer
            if adapter.provider_kind is ProviderKind.etf_issuer
            else SourceQuality.official
            if is_official
            else SourceQuality.provider
        ),
        allowlist_status=licensing.allowlist_status,
        source_use_policy=licensing.source_use_policy,
        permitted_operations=licensing.permitted_operations,
    )


def _response(
    *,
    adapter: MockProviderAdapter,
    request: ProviderRequestMetadata,
    state: ProviderResponseState,
    licensing: ProviderLicensing,
    message: str,
    freshness_state: FreshnessState,
    as_of_date: str | None = None,
    asset: AssetIdentity | None = None,
    source_attributions: list[ProviderSourceAttribution] | None = None,
    facts: list[ProviderFact] | None = None,
    recent_developments: list[ProviderRecentDevelopmentCandidate] | None = None,
    errors: list[ProviderError] | None = None,
) -> ProviderResponse:
    return ProviderResponse(
        request_metadata=request,
        provider_name=adapter.provider_name,
        provider_kind=adapter.provider_kind,
        data_category=request.data_category,
        state=state,
        capability=adapter.capability,
        asset=asset,
        source_attributions=source_attributions or [],
        facts=facts or [],
        recent_developments=recent_developments or [],
        freshness=ProviderResponseFreshness(
            as_of_date=as_of_date,
            retrieved_at=DEFAULT_PROVIDER_RETRIEVED_AT,
            freshness_state=freshness_state,
        ),
        licensing=licensing,
        errors=errors or [],
        no_live_external_calls=NO_LIVE_EXTERNAL_CALLS,
        message=message,
    )


def _eligible_not_cached_response(
    adapter: MockProviderAdapter,
    request: ProviderRequestMetadata,
    licensing: ProviderLicensing,
) -> ProviderResponse:
    return _response(
        adapter=adapter,
        request=request,
        state=ProviderResponseState.eligible_not_cached,
        licensing=licensing,
        asset=_known_asset_identity(request.normalized_ticker),
        freshness_state=FreshnessState.unknown,
        message=(
            f"{request.normalized_ticker} is eligible but not cached in deterministic provider fixtures; "
            "no generated output was created."
        ),
    )


def _unsupported_response(
    adapter: MockProviderAdapter,
    request: ProviderRequestMetadata,
    licensing: ProviderLicensing,
) -> ProviderResponse:
    ticker = request.normalized_ticker
    return _response(
        adapter=adapter,
        request=request,
        state=ProviderResponseState.unsupported,
        licensing=licensing,
        asset=_known_asset_identity(ticker),
        freshness_state=FreshnessState.unavailable,
        errors=[
            ProviderError(
                code="recognized_unsupported_asset",
                message=UNSUPPORTED_ASSETS[ticker],
                retryable=False,
                response_state=ProviderResponseState.unsupported,
            )
        ],
        message=f"{ticker} is recognized but unsupported; no provider facts or generated outputs were created.",
    )


def _out_of_scope_response(
    adapter: MockProviderAdapter,
    request: ProviderRequestMetadata,
    licensing: ProviderLicensing,
) -> ProviderResponse:
    ticker = request.normalized_ticker
    return _response(
        adapter=adapter,
        request=request,
        state=ProviderResponseState.out_of_scope,
        licensing=licensing,
        asset=_known_asset_identity(ticker),
        freshness_state=FreshnessState.unavailable,
        errors=[
            ProviderError(
                code="recognized_common_stock_outside_top500_manifest",
                message=str(OUT_OF_SCOPE_COMMON_STOCKS[ticker]["reason"]),
                retryable=False,
                response_state=ProviderResponseState.out_of_scope,
            )
        ],
        message=(
            f"{ticker} is a recognized common stock outside the local Top-500 manifest; "
            "no provider facts or generated outputs were created."
        ),
    )


def _unknown_response(
    adapter: MockProviderAdapter,
    request: ProviderRequestMetadata,
    licensing: ProviderLicensing,
) -> ProviderResponse:
    return _response(
        adapter=adapter,
        request=request,
        state=ProviderResponseState.unknown,
        licensing=licensing,
        asset=None,
        freshness_state=FreshnessState.unknown,
        errors=[
            ProviderError(
                code="unknown_asset",
                message="No deterministic provider fixture matched the requested ticker.",
                retryable=False,
                response_state=ProviderResponseState.unknown,
            )
        ],
        message="Unknown asset in deterministic provider fixtures; no facts are invented.",
    )


def _unavailable_response(
    adapter: MockProviderAdapter,
    request: ProviderRequestMetadata,
    licensing: ProviderLicensing,
) -> ProviderResponse:
    return _response(
        adapter=adapter,
        request=request,
        state=ProviderResponseState.unavailable,
        licensing=licensing,
        asset=None,
        freshness_state=FreshnessState.unavailable,
        errors=[
            ProviderError(
                code="provider_fixture_unavailable",
                message="The deterministic provider fixture is unavailable for this request.",
                retryable=True,
                response_state=ProviderResponseState.unavailable,
            )
        ],
        message="Provider fixture unavailable; no facts, recent events, or generated outputs were created.",
    )


def _official_public_licensing(provider_name: str) -> ProviderLicensing:
    return ProviderLicensing(
        provider_name=provider_name,
        attribution_required=True,
        display_allowed=True,
        cache_allowed=True,
        export_allowed=True,
        redistribution_allowed=False,
        allowed_export_fields=["source metadata", "short supporting excerpts", "citation identifiers"],
        permission_note=(
            "Official public-source metadata and short supporting excerpts may be exported in local fixtures; "
            "full source documents are not redistributed by this provider contract."
        ),
        source_use_policy=SourceUsePolicy.full_text_allowed,
        allowlist_status=SourceAllowlistStatus.allowed,
        permitted_operations=SourceOperationPermissions(
            can_store_metadata=True,
            can_store_raw_text=True,
            can_display_metadata=True,
            can_display_excerpt=True,
            can_summarize=True,
            can_cache=True,
            can_export_metadata=True,
            can_export_excerpt=True,
            can_export_full_text=False,
            can_support_generated_output=True,
            can_support_citations=True,
            can_support_canonical_facts=True,
            can_support_recent_developments=True,
        ),
    )


def _restricted_market_licensing(provider_name: str) -> ProviderLicensing:
    return ProviderLicensing(
        provider_name=provider_name,
        attribution_required=True,
        display_allowed=True,
        cache_allowed=True,
        export_allowed=False,
        redistribution_allowed=False,
        allowed_export_fields=["provider attribution", "field labels", "as-of dates"],
        permission_note=(
            "Structured market/reference provider payloads are permission-limited; this mock contract does not "
            "grant redistribution or export rights for restricted provider data."
        ),
        source_use_policy=SourceUsePolicy.metadata_only,
        allowlist_status=SourceAllowlistStatus.allowed,
        permitted_operations=SourceOperationPermissions(
            can_store_metadata=True,
            can_store_raw_text=False,
            can_display_metadata=True,
            can_display_excerpt=False,
            can_summarize=False,
            can_cache=True,
            can_export_metadata=False,
            can_export_excerpt=False,
            can_export_full_text=False,
            can_support_generated_output=False,
            can_support_citations=False,
            can_support_canonical_facts=False,
            can_support_recent_developments=False,
        ),
    )


def _recent_context_licensing(provider_name: str) -> ProviderLicensing:
    return ProviderLicensing(
        provider_name=provider_name,
        attribution_required=True,
        display_allowed=True,
        cache_allowed=True,
        export_allowed=False,
        redistribution_allowed=False,
        allowed_export_fields=["source title", "publisher", "source date", "retrieved timestamp"],
        permission_note=(
            "Recent-development provider outputs are context signals only; full articles or restricted payloads "
            "are not exportable unless rights are confirmed."
        ),
        source_use_policy=SourceUsePolicy.summary_allowed,
        allowlist_status=SourceAllowlistStatus.allowed,
        permitted_operations=SourceOperationPermissions(
            can_store_metadata=True,
            can_store_raw_text=False,
            can_display_metadata=True,
            can_display_excerpt=True,
            can_summarize=True,
            can_cache=True,
            can_export_metadata=False,
            can_export_excerpt=False,
            can_export_full_text=False,
            can_support_generated_output=True,
            can_support_citations=True,
            can_support_canonical_facts=False,
            can_support_recent_developments=True,
        ),
    )
