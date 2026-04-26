from __future__ import annotations

from dataclasses import dataclass
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
    AssetType,
    EvidenceState,
    FreshnessState,
    ProviderCapability,
    ProviderDataCategory,
    ProviderFact,
    ProviderKind,
    ProviderLicensing,
    ProviderRequestMetadata,
    ProviderResponse,
    ProviderResponseFreshness,
    ProviderResponseState,
    ProviderSourceAttribution,
    ProviderSourceUsage,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
)
from backend.source_policy import resolve_source_policy, source_can_support_generated_output


ETF_ISSUER_FIXTURE_CONTRACT_VERSION = "etf-issuer-fixture-adapter-v1"
ETF_ISSUER_ACQUISITION_BOUNDARY = "etf-issuer-acquisition-boundary-v1"
ETF_ISSUER_SOURCE_POLICY_REF = "source-use-policy-v1"


class EtfIssuerFixtureContractError(ValueError):
    """Raised when a deterministic ETF issuer fixture violates the provider contract."""


class EtfIssuerAdapterLike(Protocol):
    provider_name: str
    provider_kind: ProviderKind
    capability: ProviderCapability


@dataclass(frozen=True)
class EtfIdentityFixture:
    ticker: str
    fund_name: str
    issuer: str
    exchange: str
    asset_type: str
    support_state: str
    etf_classification: str
    eligible_not_cached: bool
    leveraged: bool = False
    inverse: bool = False
    etn: bool = False
    active: bool = False
    fixed_income: bool = False
    commodity: bool = False
    multi_asset: bool = False


@dataclass(frozen=True)
class EtfSourceFixture:
    source_document_id: str
    source_type: str
    title: str
    publisher: str
    url: str
    published_at: str | None
    as_of_date: str | None
    freshness_state: FreshnessState
    data_category: ProviderDataCategory
    source_rank: int
    usage: ProviderSourceUsage = ProviderSourceUsage.canonical
    can_support_canonical_facts: bool = True
    can_support_recent_developments: bool = False


@dataclass(frozen=True)
class EtfFactSheetMetadataFixture:
    benchmark: str
    expense_ratio: float
    holdings_count: int
    source_document_id: str
    citation_id: str
    as_of_date: str


@dataclass(frozen=True)
class EtfProspectusReferenceFixture:
    document_type: str
    publication_date: str
    effective_date: str | None
    source_document_id: str
    citation_id: str


@dataclass(frozen=True)
class EtfHoldingExposureFixture:
    field_name: str
    holding_ticker: str | None
    name: str
    weight: float | None
    exposure_category: str
    unit: str
    as_of_date: str
    source_document_id: str
    citation_id: str


@dataclass(frozen=True)
class EtfEvidenceGapFixture:
    field_name: str
    evidence_state: EvidenceState
    freshness_state: FreshnessState
    message: str


@dataclass(frozen=True)
class EtfIssuerFixture:
    identity: EtfIdentityFixture
    sources: tuple[EtfSourceFixture, ...]
    fact_sheet: EtfFactSheetMetadataFixture
    prospectus: EtfProspectusReferenceFixture
    holdings_or_exposures: tuple[EtfHoldingExposureFixture, ...]
    evidence_gaps: tuple[EtfEvidenceGapFixture, ...] = ()


@dataclass(frozen=True)
class EtfIssuerConfigurationReadiness:
    issuer_source_configured: bool
    rate_limit_ready: bool
    live_call_disabled: bool
    no_live_external_calls: bool = True
    configuration_source: str = "deterministic_fixture"


@dataclass(frozen=True)
class EtfIssuerAcquisitionSourceRecord:
    source_document_id: str
    source_type: str
    checksum: str
    source_use_policy: SourceUsePolicy
    allowlist_status: SourceAllowlistStatus
    source_quality: SourceQuality
    freshness_state: FreshnessState
    retrieved_at: str
    as_of_date: str | None
    stores_raw_source_text: bool = False
    stores_raw_provider_payload: bool = False


@dataclass(frozen=True)
class EtfIssuerAcquisitionDiagnostic:
    code: str
    message: str
    evidence_state: EvidenceState
    freshness_state: FreshnessState
    retryable: bool = False
    stores_raw_source_text: bool = False
    stores_raw_provider_payload: bool = False
    stores_secret: bool = False


@dataclass(frozen=True)
class EtfIssuerAcquisitionResult:
    boundary: str
    ticker: str
    issuer: str | None
    response_state: ProviderResponseState
    provider_response: ProviderResponse | None
    configuration_readiness: EtfIssuerConfigurationReadiness
    source_records: tuple[EtfIssuerAcquisitionSourceRecord, ...]
    diagnostics: tuple[EtfIssuerAcquisitionDiagnostic, ...]
    evidence_gap_states: dict[str, str]
    checksum: str | None
    source_policy_ref: str = ETF_ISSUER_SOURCE_POLICY_REF
    no_live_external_calls: bool = True
    opened_database_connection: bool = False
    wrote_source_snapshot: bool = False
    wrote_knowledge_pack: bool = False
    wrote_generated_output_cache: bool = False
    created_generated_asset_page: bool = False
    created_generated_chat_answer: bool = False
    created_generated_comparison: bool = False
    created_generated_risk_summary: bool = False


ETF_ISSUER_FIXTURES: dict[str, EtfIssuerFixture] = {
    "VOO": EtfIssuerFixture(
        identity=EtfIdentityFixture(
            ticker="VOO",
            fund_name="Vanguard S&P 500 ETF",
            issuer="Vanguard",
            exchange="NYSE Arca",
            asset_type="etf",
            support_state="supported",
            etf_classification="non_leveraged_us_equity_index_etf",
            eligible_not_cached=False,
        ),
        sources=(
            EtfSourceFixture(
                source_document_id="provider_issuer_voo_fact_sheet_2026",
                source_type="issuer_fact_sheet",
                title="Vanguard S&P 500 ETF fact sheet deterministic provider fixture",
                publisher="Vanguard",
                url="https://investor.vanguard.com/investment-products/etfs/profile/voo",
                published_at="2026-04-01",
                as_of_date="2026-04-01",
                freshness_state=FreshnessState.fresh,
                data_category=ProviderDataCategory.etf_issuer_facts,
                source_rank=1,
            ),
            EtfSourceFixture(
                source_document_id="provider_issuer_voo_prospectus_2026",
                source_type="summary_prospectus",
                title="Vanguard S&P 500 ETF summary prospectus deterministic provider fixture",
                publisher="Vanguard",
                url="https://investor.vanguard.com/investment-products/etfs/profile/voo",
                published_at="2026-04-01",
                as_of_date="2026-04-01",
                freshness_state=FreshnessState.fresh,
                data_category=ProviderDataCategory.etf_issuer_facts,
                source_rank=2,
            ),
            EtfSourceFixture(
                source_document_id="provider_issuer_voo_holdings_2026",
                source_type="issuer_holdings_file",
                title="Vanguard S&P 500 ETF holdings deterministic provider fixture",
                publisher="Vanguard",
                url="https://investor.vanguard.com/investment-products/etfs/profile/voo",
                published_at="2026-04-01",
                as_of_date="2026-04-01",
                freshness_state=FreshnessState.fresh,
                data_category=ProviderDataCategory.etf_holdings_metadata,
                source_rank=2,
            ),
            EtfSourceFixture(
                source_document_id="provider_issuer_voo_exposure_2026",
                source_type="issuer_exposure_file",
                title="Vanguard S&P 500 ETF exposure deterministic provider fixture",
                publisher="Vanguard",
                url="https://investor.vanguard.com/investment-products/etfs/profile/voo",
                published_at="2026-04-01",
                as_of_date="2026-04-01",
                freshness_state=FreshnessState.fresh,
                data_category=ProviderDataCategory.etf_holdings_metadata,
                source_rank=2,
            ),
        ),
        fact_sheet=EtfFactSheetMetadataFixture(
            benchmark="S&P 500 Index",
            expense_ratio=0.03,
            holdings_count=500,
            source_document_id="provider_issuer_voo_fact_sheet_2026",
            citation_id="provider_cite_voo_fact_sheet",
            as_of_date="2026-04-01",
        ),
        prospectus=EtfProspectusReferenceFixture(
            document_type="summary_prospectus",
            publication_date="2026-04-01",
            effective_date="2026-04-01",
            source_document_id="provider_issuer_voo_prospectus_2026",
            citation_id="provider_cite_voo_prospectus",
        ),
        holdings_or_exposures=(
            EtfHoldingExposureFixture(
                field_name="top_holding_apple",
                holding_ticker="AAPL",
                name="Apple Inc.",
                weight=7.0,
                exposure_category="holding",
                unit="percent_weight",
                as_of_date="2026-04-01",
                source_document_id="provider_issuer_voo_holdings_2026",
                citation_id="provider_cite_voo_holdings",
            ),
            EtfHoldingExposureFixture(
                field_name="equity_exposure",
                holding_ticker=None,
                name="U.S. equity exposure",
                weight=100.0,
                exposure_category="asset_class",
                unit="percent_weight",
                as_of_date="2026-04-01",
                source_document_id="provider_issuer_voo_exposure_2026",
                citation_id="provider_cite_voo_exposure",
            ),
        ),
        evidence_gaps=(
            EtfEvidenceGapFixture(
                field_name="premium_discount_or_spread",
                evidence_state=EvidenceState.unavailable,
                freshness_state=FreshnessState.unavailable,
                message="The ETF issuer fixture does not provide current premium, discount, or bid-ask spread data.",
            ),
        ),
    ),
    "QQQ": EtfIssuerFixture(
        identity=EtfIdentityFixture(
            ticker="QQQ",
            fund_name="Invesco QQQ Trust",
            issuer="Invesco",
            exchange="NASDAQ",
            asset_type="etf",
            support_state="supported",
            etf_classification="non_leveraged_us_equity_index_etf",
            eligible_not_cached=False,
        ),
        sources=(
            EtfSourceFixture(
                source_document_id="provider_issuer_qqq_fact_sheet_2026",
                source_type="issuer_fact_sheet",
                title="Invesco QQQ Trust fact sheet deterministic provider fixture",
                publisher="Invesco",
                url="https://www.invesco.com/qqq-etf/en/home.html",
                published_at="2026-04-01",
                as_of_date="2026-04-01",
                freshness_state=FreshnessState.fresh,
                data_category=ProviderDataCategory.etf_issuer_facts,
                source_rank=1,
            ),
            EtfSourceFixture(
                source_document_id="provider_issuer_qqq_prospectus_2026",
                source_type="summary_prospectus",
                title="Invesco QQQ Trust summary prospectus deterministic provider fixture",
                publisher="Invesco",
                url="https://www.invesco.com/qqq-etf/en/home.html",
                published_at="2026-04-01",
                as_of_date="2026-04-01",
                freshness_state=FreshnessState.fresh,
                data_category=ProviderDataCategory.etf_issuer_facts,
                source_rank=2,
            ),
            EtfSourceFixture(
                source_document_id="provider_issuer_qqq_holdings_2026",
                source_type="issuer_holdings_file",
                title="Invesco QQQ Trust holdings deterministic provider fixture",
                publisher="Invesco",
                url="https://www.invesco.com/qqq-etf/en/home.html",
                published_at="2026-04-01",
                as_of_date="2026-04-01",
                freshness_state=FreshnessState.fresh,
                data_category=ProviderDataCategory.etf_holdings_metadata,
                source_rank=2,
            ),
            EtfSourceFixture(
                source_document_id="provider_issuer_qqq_exposure_2026",
                source_type="issuer_exposure_file",
                title="Invesco QQQ Trust exposure deterministic provider fixture",
                publisher="Invesco",
                url="https://www.invesco.com/qqq-etf/en/home.html",
                published_at="2026-04-01",
                as_of_date="2026-04-01",
                freshness_state=FreshnessState.fresh,
                data_category=ProviderDataCategory.etf_holdings_metadata,
                source_rank=2,
            ),
        ),
        fact_sheet=EtfFactSheetMetadataFixture(
            benchmark="Nasdaq-100 Index",
            expense_ratio=0.20,
            holdings_count=100,
            source_document_id="provider_issuer_qqq_fact_sheet_2026",
            citation_id="provider_cite_qqq_fact_sheet",
            as_of_date="2026-04-01",
        ),
        prospectus=EtfProspectusReferenceFixture(
            document_type="summary_prospectus",
            publication_date="2026-04-01",
            effective_date="2026-04-01",
            source_document_id="provider_issuer_qqq_prospectus_2026",
            citation_id="provider_cite_qqq_prospectus",
        ),
        holdings_or_exposures=(
            EtfHoldingExposureFixture(
                field_name="top_holding_apple",
                holding_ticker="AAPL",
                name="Apple Inc.",
                weight=8.8,
                exposure_category="holding",
                unit="percent_weight",
                as_of_date="2026-04-01",
                source_document_id="provider_issuer_qqq_holdings_2026",
                citation_id="provider_cite_qqq_holdings",
            ),
            EtfHoldingExposureFixture(
                field_name="equity_exposure",
                holding_ticker=None,
                name="U.S. equity exposure",
                weight=100.0,
                exposure_category="asset_class",
                unit="percent_weight",
                as_of_date="2026-04-01",
                source_document_id="provider_issuer_qqq_exposure_2026",
                citation_id="provider_cite_qqq_exposure",
            ),
        ),
        evidence_gaps=(
            EtfEvidenceGapFixture(
                field_name="premium_discount_or_spread",
                evidence_state=EvidenceState.unavailable,
                freshness_state=FreshnessState.unavailable,
                message="The ETF issuer fixture does not provide current premium, discount, or bid-ask spread data.",
            ),
        ),
    ),
}


def etf_issuer_fixture_for_ticker(ticker: str) -> EtfIssuerFixture | None:
    return ETF_ISSUER_FIXTURES.get(normalize_ticker(ticker))


def build_etf_issuer_acquisition_result(
    adapter: EtfIssuerAdapterLike,
    request: ProviderRequestMetadata,
    licensing: ProviderLicensing,
) -> EtfIssuerAcquisitionResult:
    ticker = normalize_ticker(request.normalized_ticker)
    fixture = etf_issuer_fixture_for_ticker(ticker)
    if fixture is None:
        return _blocked_or_unavailable_acquisition_result(ticker)

    try:
        response = build_etf_issuer_provider_response(adapter, request, licensing)
    except EtfIssuerFixtureContractError as exc:
        return _contract_error_acquisition_result(ticker, str(exc))

    source_records = tuple(_acquisition_source_record(source) for source in response.source_attributions)
    evidence_gap_states = {
        fact.field_name: fact.evidence_state.value
        for fact in response.facts
        if fact.evidence_state is not EvidenceState.supported
    }
    diagnostics = tuple(
        EtfIssuerAcquisitionDiagnostic(
            code=f"etf_issuer_evidence_gap_{gap.field_name}",
            message=gap.message,
            evidence_state=gap.evidence_state,
            freshness_state=gap.freshness_state,
            retryable=gap.evidence_state in {EvidenceState.stale, EvidenceState.unavailable, EvidenceState.unknown},
        )
        for gap in fixture.evidence_gaps
    )
    return EtfIssuerAcquisitionResult(
        boundary=ETF_ISSUER_ACQUISITION_BOUNDARY,
        ticker=ticker,
        issuer=fixture.identity.issuer,
        response_state=response.state,
        provider_response=response,
        configuration_readiness=_configuration_readiness(),
        source_records=source_records,
        diagnostics=diagnostics,
        evidence_gap_states=evidence_gap_states,
        checksum=_combined_checksum(source_records),
    )


def build_etf_issuer_provider_response(
    adapter: EtfIssuerAdapterLike,
    request: ProviderRequestMetadata,
    licensing: ProviderLicensing,
) -> ProviderResponse:
    ticker = normalize_ticker(request.normalized_ticker)
    fixture = etf_issuer_fixture_for_ticker(ticker)
    if fixture is None:
        raise EtfIssuerFixtureContractError(f"No deterministic ETF issuer fixture is registered for {ticker}.")

    _validate_fixture_binding(fixture, ticker)
    sources = [_source_attribution(adapter, source, licensing) for source in fixture.sources]
    facts = _facts_from_fixture(fixture)
    _validate_response_contract(fixture, sources, facts)

    return ProviderResponse(
        request_metadata=request,
        provider_name=adapter.provider_name,
        provider_kind=adapter.provider_kind,
        data_category=request.data_category,
        state=ProviderResponseState.supported,
        capability=adapter.capability,
        asset=_asset_identity(fixture.identity),
        source_attributions=sources,
        facts=facts,
        recent_developments=[],
        freshness=ProviderResponseFreshness(
            as_of_date=fixture.fact_sheet.as_of_date,
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
        ),
        licensing=licensing,
        errors=[],
        no_live_external_calls=True,
        message=(
            f"Deterministic ETF issuer fixture contract for {ticker}: identity, fact sheet, prospectus, "
            "holdings, exposure rows, and evidence gaps only; no generated output was created."
        ),
    )


def _asset_identity(identity: EtfIdentityFixture) -> AssetIdentity:
    return ASSETS[identity.ticker]["identity"].model_copy(deep=True)


def _configuration_readiness() -> EtfIssuerConfigurationReadiness:
    return EtfIssuerConfigurationReadiness(
        issuer_source_configured=True,
        rate_limit_ready=True,
        live_call_disabled=True,
    )


def _acquisition_source_record(source: ProviderSourceAttribution) -> EtfIssuerAcquisitionSourceRecord:
    return EtfIssuerAcquisitionSourceRecord(
        source_document_id=source.source_document_id,
        source_type=source.source_type,
        checksum=_source_checksum(source.source_document_id),
        source_use_policy=source.source_use_policy,
        allowlist_status=source.allowlist_status,
        source_quality=source.source_quality,
        freshness_state=source.freshness_state,
        retrieved_at=source.retrieved_at,
        as_of_date=source.as_of_date,
    )


def _blocked_or_unavailable_acquisition_result(ticker: str) -> EtfIssuerAcquisitionResult:
    cached_asset = ASSETS.get(ticker)
    eligible_asset = ELIGIBLE_NOT_CACHED_ASSETS.get(ticker)
    cached_asset_type = cached_asset["identity"].asset_type.value if cached_asset else None
    eligible_asset_type = str(eligible_asset["asset_type"]) if eligible_asset else None

    if cached_asset_type and cached_asset_type != "etf":
        state = ProviderResponseState.out_of_scope
        code = "blocked_wrong_asset_type_for_etf_issuer_acquisition"
        message = "ETF issuer acquisition is limited to supported non-leveraged U.S. equity ETFs; this cached asset is not an ETF."
        evidence = EvidenceState.unsupported
        freshness = FreshnessState.unavailable
    elif eligible_asset_type and eligible_asset_type != "etf":
        state = ProviderResponseState.out_of_scope
        code = "blocked_wrong_asset_type_for_etf_issuer_acquisition"
        message = "ETF issuer acquisition is limited to supported non-leveraged U.S. equity ETFs; this pending asset is not an ETF."
        evidence = EvidenceState.unsupported
        freshness = FreshnessState.unavailable
    elif ticker in ASSETS:
        state = ProviderResponseState.unavailable
        code = "fixture_not_registered_for_etf_golden_path"
        message = "Cached asset has no deterministic ETF issuer golden-path fixture for this task."
        evidence = EvidenceState.partial
        freshness = FreshnessState.unknown
    elif ticker in ELIGIBLE_NOT_CACHED_ASSETS:
        state = ProviderResponseState.eligible_not_cached
        code = "fixture_not_registered_for_etf_golden_path"
        message = "Asset is eligible but no deterministic ETF issuer golden-path fixture is registered for this task."
        evidence = EvidenceState.partial
        freshness = FreshnessState.unknown
    elif ticker in UNSUPPORTED_ASSETS:
        state = ProviderResponseState.unsupported
        code = "blocked_unsupported_asset"
        message = "Recognized unsupported ETF class; issuer acquisition is blocked and no generated output was created."
        evidence = EvidenceState.unsupported
        freshness = FreshnessState.unavailable
    elif ticker in OUT_OF_SCOPE_COMMON_STOCKS:
        state = ProviderResponseState.out_of_scope
        code = "blocked_out_of_scope_asset"
        message = "Recognized asset outside the current ETF issuer acquisition scope; no generated output was created."
        evidence = EvidenceState.unsupported
        freshness = FreshnessState.unavailable
    else:
        state = ProviderResponseState.unknown
        code = "unknown_or_unavailable_asset"
        message = "No deterministic ETF issuer acquisition fixture matched the requested ticker."
        evidence = EvidenceState.unknown
        freshness = FreshnessState.unknown

    return EtfIssuerAcquisitionResult(
        boundary=ETF_ISSUER_ACQUISITION_BOUNDARY,
        ticker=ticker,
        issuer=None,
        response_state=state,
        provider_response=None,
        configuration_readiness=_configuration_readiness(),
        source_records=(),
        diagnostics=(
            EtfIssuerAcquisitionDiagnostic(
                code=code,
                message=message,
                evidence_state=evidence,
                freshness_state=freshness,
                retryable=state in {ProviderResponseState.unavailable, ProviderResponseState.unknown},
            ),
        ),
        evidence_gap_states={"etf_issuer_acquisition": evidence.value},
        checksum=None,
    )


def _contract_error_acquisition_result(ticker: str, error_message: str) -> EtfIssuerAcquisitionResult:
    source_policy_blocked = any(
        marker in error_message.lower()
        for marker in ("source policy", "source-use", "allowlisted", "rejected", "generated claims")
    )
    code = "source_policy_blocked" if source_policy_blocked else "etf_issuer_fixture_validation_failed"
    return EtfIssuerAcquisitionResult(
        boundary=ETF_ISSUER_ACQUISITION_BOUNDARY,
        ticker=ticker,
        issuer=None,
        response_state=ProviderResponseState.permission_limited if source_policy_blocked else ProviderResponseState.unavailable,
        provider_response=None,
        configuration_readiness=_configuration_readiness(),
        source_records=(),
        diagnostics=(
            EtfIssuerAcquisitionDiagnostic(
                code=code,
                message="Sanitized ETF issuer acquisition diagnostic.",
                evidence_state=EvidenceState.unavailable,
                freshness_state=FreshnessState.unavailable,
                retryable=not source_policy_blocked,
            ),
        ),
        evidence_gap_states={"etf_issuer_acquisition": EvidenceState.unavailable.value},
        checksum=None,
    )


def _source_checksum(source_document_id: str) -> str:
    ticker = _ticker_from_source_id(source_document_id)
    fixture = ETF_ISSUER_FIXTURES.get(ticker)
    if fixture:
        for source in fixture.sources:
            if source.source_document_id == source_document_id:
                return f"sha256:issuer-{ticker.lower()}-{source.source_type}-2026-fixture"
    raise EtfIssuerFixtureContractError(f"ETF issuer fixture references missing checksum for {source_document_id}.")


def _combined_checksum(source_records: tuple[EtfIssuerAcquisitionSourceRecord, ...]) -> str:
    checksums = "|".join(record.checksum for record in source_records)
    return f"sha256:etf-issuer-acquisition:{checksums}"


def _source_attribution(
    adapter: EtfIssuerAdapterLike,
    source: EtfSourceFixture,
    licensing: ProviderLicensing,
) -> ProviderSourceAttribution:
    decision = resolve_source_policy(url=source.url)
    if not source_can_support_generated_output(decision):
        raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} cannot support generated claims.")
    if not decision.canonical_facts_allowed:
        raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} cannot support canonical facts.")

    return ProviderSourceAttribution(
        source_document_id=source.source_document_id,
        asset_ticker=_ticker_from_source_id(source.source_document_id),
        source_type=source.source_type,
        title=source.title,
        publisher=source.publisher,
        url=source.url,
        published_at=source.published_at,
        as_of_date=source.as_of_date,
        retrieved_at=STUB_TIMESTAMP,
        freshness_state=source.freshness_state,
        is_official=True,
        provider_name=adapter.provider_name,
        provider_kind=adapter.provider_kind,
        data_category=source.data_category,
        usage=source.usage,
        source_rank=source.source_rank,
        can_support_canonical_facts=source.can_support_canonical_facts,
        can_support_recent_developments=source.can_support_recent_developments,
        licensing=licensing.model_copy(
            update={
                "source_use_policy": decision.source_use_policy,
                "allowlist_status": decision.allowlist_status,
                "permitted_operations": decision.permitted_operations,
            },
            deep=True,
        ),
        source_quality=decision.source_quality,
        allowlist_status=decision.allowlist_status,
        source_use_policy=decision.source_use_policy,
        permitted_operations=decision.permitted_operations,
    )


def _facts_from_fixture(fixture: EtfIssuerFixture) -> list[ProviderFact]:
    identity = fixture.identity
    fact_sheet_source = _source_by_id(fixture, fixture.fact_sheet.source_document_id)
    prospectus_source = _source_by_id(fixture, fixture.prospectus.source_document_id)
    blocked_indicators = {
        "leveraged": identity.leveraged,
        "inverse": identity.inverse,
        "etn": identity.etn,
        "active": identity.active,
        "fixed_income": identity.fixed_income,
        "commodity": identity.commodity,
        "multi_asset": identity.multi_asset,
    }
    facts = [
        ProviderFact(
            fact_id=f"provider_fact_{identity.ticker.lower()}_etf_identity",
            asset_ticker=identity.ticker,
            data_category=ProviderDataCategory.etf_issuer_facts,
            field_name="etf_identity",
            value={
                "ticker": identity.ticker,
                "fund_name": identity.fund_name,
                "issuer": identity.issuer,
                "exchange": identity.exchange,
                "asset_type": identity.asset_type,
                "support_state": identity.support_state,
                "etf_classification": identity.etf_classification,
                "eligible_not_cached": identity.eligible_not_cached,
                "blocked_state_indicators": blocked_indicators,
            },
            as_of_date=fixture.fact_sheet.as_of_date,
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            source_document_ids=[fixture.fact_sheet.source_document_id],
            citation_ids=[fixture.fact_sheet.citation_id],
            fact_layer="canonical",
            uses_glossary_as_support=False,
        ),
        ProviderFact(
            fact_id=f"provider_fact_{identity.ticker.lower()}_fact_sheet_metadata",
            asset_ticker=identity.ticker,
            data_category=ProviderDataCategory.etf_issuer_facts,
            field_name="etf_fact_sheet_metadata",
            value={
                "benchmark": fixture.fact_sheet.benchmark,
                "expense_ratio": fixture.fact_sheet.expense_ratio,
                "holdings_count": fixture.fact_sheet.holdings_count,
                "source_document_id": fixture.fact_sheet.source_document_id,
                "official_publisher": fact_sheet_source.publisher,
                "official_title": fact_sheet_source.title,
                "official_url": fact_sheet_source.url,
                "retrieved_at": STUB_TIMESTAMP,
                "as_of_date": fixture.fact_sheet.as_of_date,
                "freshness_state": fact_sheet_source.freshness_state.value,
            },
            as_of_date=fixture.fact_sheet.as_of_date,
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            source_document_ids=[fixture.fact_sheet.source_document_id],
            citation_ids=[fixture.fact_sheet.citation_id],
            fact_layer="canonical",
            uses_glossary_as_support=False,
        ),
        ProviderFact(
            fact_id=f"provider_fact_{identity.ticker.lower()}_benchmark",
            asset_ticker=identity.ticker,
            data_category=ProviderDataCategory.etf_issuer_facts,
            field_name="benchmark",
            value=fixture.fact_sheet.benchmark,
            as_of_date=fixture.fact_sheet.as_of_date,
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            source_document_ids=[fixture.fact_sheet.source_document_id],
            citation_ids=[fixture.fact_sheet.citation_id],
            fact_layer="canonical",
            uses_glossary_as_support=False,
        ),
        ProviderFact(
            fact_id=f"provider_fact_{identity.ticker.lower()}_expense_ratio",
            asset_ticker=identity.ticker,
            data_category=ProviderDataCategory.etf_issuer_facts,
            field_name="expense_ratio",
            value=fixture.fact_sheet.expense_ratio,
            unit="%",
            as_of_date=fixture.fact_sheet.as_of_date,
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            source_document_ids=[fixture.fact_sheet.source_document_id],
            citation_ids=[fixture.fact_sheet.citation_id],
            fact_layer="canonical",
            uses_glossary_as_support=False,
        ),
        ProviderFact(
            fact_id=f"provider_fact_{identity.ticker.lower()}_holdings_count",
            asset_ticker=identity.ticker,
            data_category=ProviderDataCategory.etf_holdings_metadata,
            field_name="holdings_count",
            value=fixture.fact_sheet.holdings_count,
            unit="approximate holdings",
            as_of_date=fixture.fact_sheet.as_of_date,
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            source_document_ids=[fixture.fact_sheet.source_document_id],
            citation_ids=[fixture.fact_sheet.citation_id],
            fact_layer="canonical",
            uses_glossary_as_support=False,
        ),
        ProviderFact(
            fact_id=f"provider_fact_{identity.ticker.lower()}_prospectus_reference",
            asset_ticker=identity.ticker,
            data_category=ProviderDataCategory.etf_issuer_facts,
            field_name="prospectus_reference",
            value={
                "document_type": fixture.prospectus.document_type,
                "publication_date": fixture.prospectus.publication_date,
                "effective_date": fixture.prospectus.effective_date,
                "source_document_id": fixture.prospectus.source_document_id,
                "official_publisher": prospectus_source.publisher,
                "official_title": prospectus_source.title,
                "official_url": prospectus_source.url,
                "retrieved_at": STUB_TIMESTAMP,
                "source_use_policy": SourceUsePolicy.full_text_allowed.value,
                "freshness_state": prospectus_source.freshness_state.value,
            },
            as_of_date=fixture.prospectus.publication_date,
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            source_document_ids=[fixture.prospectus.source_document_id],
            citation_ids=[fixture.prospectus.citation_id],
            fact_layer="canonical",
            uses_glossary_as_support=False,
        ),
    ]

    for item in fixture.holdings_or_exposures:
        facts.append(
            ProviderFact(
                fact_id=f"provider_fact_{identity.ticker.lower()}_{item.field_name}",
                asset_ticker=identity.ticker,
                data_category=ProviderDataCategory.etf_holdings_metadata,
                field_name=item.field_name,
                value={
                    "holding_ticker": item.holding_ticker,
                    "name": item.name,
                    "weight": item.weight,
                    "exposure_category": item.exposure_category,
                    "unit": item.unit,
                    "as_of_date": item.as_of_date,
                    "source_document_ids": [item.source_document_id],
                    "citation_ids": [item.citation_id],
                },
                unit=item.unit,
                as_of_date=item.as_of_date,
                retrieved_at=STUB_TIMESTAMP,
                freshness_state=FreshnessState.fresh,
                evidence_state=EvidenceState.supported,
                source_document_ids=[item.source_document_id],
                citation_ids=[item.citation_id],
                fact_layer="canonical",
                uses_glossary_as_support=False,
            )
        )

    for gap in fixture.evidence_gaps:
        facts.append(
            ProviderFact(
                fact_id=f"provider_gap_{identity.ticker.lower()}_{gap.field_name}",
                asset_ticker=identity.ticker,
                data_category=ProviderDataCategory.etf_issuer_facts,
                field_name=gap.field_name,
                value=gap.message,
                as_of_date=None,
                retrieved_at=STUB_TIMESTAMP,
                freshness_state=gap.freshness_state,
                evidence_state=gap.evidence_state,
                source_document_ids=[],
                citation_ids=[],
                fact_layer="canonical",
                uses_glossary_as_support=False,
            )
        )

    return facts


def _validate_fixture_binding(fixture: EtfIssuerFixture, requested_ticker: str) -> None:
    identity = fixture.identity
    asset = ASSETS.get(identity.ticker, {}).get("identity")
    if identity.ticker != requested_ticker:
        raise EtfIssuerFixtureContractError("ETF issuer fixture ticker does not match the requested ticker.")
    if asset is None:
        raise EtfIssuerFixtureContractError(f"{identity.ticker} is not present in deterministic cached ETF fixtures.")
    if asset.asset_type is not AssetType.etf or not asset.supported:
        raise EtfIssuerFixtureContractError("ETF issuer fixture can only represent supported ETF identity.")
    if identity.asset_type != "etf" or identity.support_state != "supported":
        raise EtfIssuerFixtureContractError("ETF issuer fixture has an invalid ETF support state.")
    if identity.fund_name != asset.name or identity.exchange != asset.exchange or identity.issuer != asset.issuer:
        raise EtfIssuerFixtureContractError(f"{identity.ticker} ETF identity disagrees with the cached asset fixture.")
    if identity.eligible_not_cached:
        raise EtfIssuerFixtureContractError("ETF issuer fixture cannot create evidence for eligible-not-cached ETFs.")
    blocked = [
        identity.leveraged,
        identity.inverse,
        identity.etn,
        identity.active,
        identity.fixed_income,
        identity.commodity,
        identity.multi_asset,
    ]
    if any(blocked):
        raise EtfIssuerFixtureContractError("ETF issuer fixture cannot represent blocked ETF classes.")


def _validate_response_contract(
    fixture: EtfIssuerFixture,
    sources: list[ProviderSourceAttribution],
    facts: list[ProviderFact],
) -> None:
    ticker = fixture.identity.ticker
    source_by_id = {source.source_document_id: source for source in sources}
    if len(source_by_id) != len(sources):
        raise EtfIssuerFixtureContractError("ETF issuer fixture contains duplicate source document IDs.")

    for source in sources:
        if source.asset_ticker != ticker:
            raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} is bound to the wrong asset.")
        if source.publisher != fixture.identity.issuer:
            raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} is bound to the wrong issuer.")
        if source.provider_kind is not ProviderKind.etf_issuer or not source.is_official:
            raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} must be official issuer evidence.")
        if source.source_quality is not SourceQuality.issuer:
            raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} must have issuer quality.")
        if source.allowlist_status is not SourceAllowlistStatus.allowed:
            raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} is not allowlisted.")
        if source.source_use_policy is SourceUsePolicy.rejected:
            raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} is rejected.")
        if not source.permitted_operations.can_support_generated_output:
            raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} cannot support generated output.")
        if not source.permitted_operations.can_support_citations:
            raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} cannot support citations.")
        if not source.permitted_operations.can_support_canonical_facts:
            raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} cannot support canonical facts.")
        if source.source_rank >= 4:
            raise EtfIssuerFixtureContractError(f"ETF issuer source {source.source_document_id} must rank before reference data.")

    for fact in facts:
        if fact.asset_ticker != ticker:
            raise EtfIssuerFixtureContractError(f"ETF issuer fact {fact.fact_id} is bound to the wrong asset.")
        if fact.uses_glossary_as_support:
            raise EtfIssuerFixtureContractError(f"ETF issuer fact {fact.fact_id} cannot use glossary as evidence.")
        if fact.evidence_state is EvidenceState.supported and not fact.source_document_ids:
            raise EtfIssuerFixtureContractError(f"ETF issuer fact {fact.fact_id} lacks source documents.")
        for source_document_id in fact.source_document_ids:
            source = source_by_id.get(source_document_id)
            if source is None or source.asset_ticker != ticker:
                raise EtfIssuerFixtureContractError(f"ETF issuer fact {fact.fact_id} references invalid source evidence.")
            if source.publisher != fixture.identity.issuer:
                raise EtfIssuerFixtureContractError(f"ETF issuer fact {fact.fact_id} references wrong-issuer evidence.")
            if source.source_use_policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only, SourceUsePolicy.rejected}:
                raise EtfIssuerFixtureContractError(f"ETF issuer fact {fact.fact_id} references source-use-blocked evidence.")


def _source_by_id(fixture: EtfIssuerFixture, source_document_id: str) -> EtfSourceFixture:
    for source in fixture.sources:
        if source.source_document_id == source_document_id:
            return source
    raise EtfIssuerFixtureContractError(f"ETF issuer fixture references missing source {source_document_id}.")


def _ticker_from_source_id(source_document_id: str) -> str:
    parts = source_document_id.split("_")
    if len(parts) < 4 or parts[0] != "provider" or parts[1] != "issuer":
        raise EtfIssuerFixtureContractError(f"ETF issuer source ID has an invalid deterministic shape: {source_document_id}.")
    return parts[2].upper()
