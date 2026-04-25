from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.data import ASSETS, STUB_TIMESTAMP, normalize_ticker, top500_stock_universe_entry
from backend.models import (
    AssetIdentity,
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


SEC_STOCK_FIXTURE_CONTRACT_VERSION = "sec-stock-fixture-adapter-v1"


class SecStockFixtureContractError(ValueError):
    """Raised when a deterministic SEC stock fixture violates the provider contract."""


class SecProviderAdapterLike(Protocol):
    provider_name: str
    provider_kind: ProviderKind
    capability: ProviderCapability


@dataclass(frozen=True)
class SecStockIdentityFixture:
    ticker: str
    company_name: str
    cik: str
    exchange: str
    asset_type: str
    support_state: str
    top500_manifest_member: bool
    eligible_not_cached: bool
    submissions_source_document_id: str


@dataclass(frozen=True)
class SecStockSourceFixture:
    source_document_id: str
    source_type: str
    title: str
    publisher: str
    url: str
    published_at: str | None
    as_of_date: str | None
    freshness_state: FreshnessState
    usage: ProviderSourceUsage = ProviderSourceUsage.canonical
    source_rank: int = 1
    can_support_canonical_facts: bool = True
    can_support_recent_developments: bool = False


@dataclass(frozen=True)
class SecFilingMetadataFixture:
    form_type: str
    accession_or_fixture_id: str
    filing_date: str
    report_date: str
    source_document_id: str
    citation_id: str


@dataclass(frozen=True)
class SecXbrlCompanyFactFixture:
    field_name: str
    label: str
    value: object
    unit: str | None
    period: str
    as_of_date: str
    source_document_id: str
    citation_id: str
    fact_layer: str = "canonical"


@dataclass(frozen=True)
class SecEvidenceGapFixture:
    field_name: str
    evidence_state: EvidenceState
    freshness_state: FreshnessState
    message: str


@dataclass(frozen=True)
class SecStockFixture:
    identity: SecStockIdentityFixture
    sources: tuple[SecStockSourceFixture, ...]
    selected_filings: tuple[SecFilingMetadataFixture, ...]
    xbrl_company_facts: tuple[SecXbrlCompanyFactFixture, ...]
    evidence_gaps: tuple[SecEvidenceGapFixture, ...] = ()


SEC_STOCK_FIXTURES: dict[str, SecStockFixture] = {
    "AAPL": SecStockFixture(
        identity=SecStockIdentityFixture(
            ticker="AAPL",
            company_name="Apple Inc.",
            cik="0000320193",
            exchange="NASDAQ",
            asset_type="stock",
            support_state="supported",
            top500_manifest_member=True,
            eligible_not_cached=False,
            submissions_source_document_id="provider_sec_aapl_submissions_2026",
        ),
        sources=(
            SecStockSourceFixture(
                source_document_id="provider_sec_aapl_submissions_2026",
                source_type="sec_submissions",
                title="Apple Inc. SEC submissions deterministic provider fixture",
                publisher="U.S. SEC",
                url="https://data.sec.gov/submissions/CIK0000320193.json",
                published_at=None,
                as_of_date="2026-04-01",
                freshness_state=FreshnessState.fresh,
            ),
            SecStockSourceFixture(
                source_document_id="provider_sec_aapl_10k_2026",
                source_type="sec_filing",
                title="Apple Inc. Form 10-K deterministic provider fixture",
                publisher="U.S. SEC",
                url="https://www.sec.gov/Archives/edgar/data/320193/provider-fixture",
                published_at="2026-04-01",
                as_of_date=None,
                freshness_state=FreshnessState.fresh,
            ),
            SecStockSourceFixture(
                source_document_id="provider_sec_aapl_xbrl_2026",
                source_type="sec_xbrl_company_facts",
                title="Apple Inc. SEC XBRL company facts deterministic provider fixture",
                publisher="U.S. SEC",
                url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
                published_at=None,
                as_of_date="2026-04-01",
                freshness_state=FreshnessState.fresh,
            ),
        ),
        selected_filings=(
            SecFilingMetadataFixture(
                form_type="10-K",
                accession_or_fixture_id="aapl-2026-10k-provider-fixture",
                filing_date="2026-04-01",
                report_date="2025-09-27",
                source_document_id="provider_sec_aapl_10k_2026",
                citation_id="provider_cite_aapl_10k_metadata",
            ),
        ),
        xbrl_company_facts=(
            SecXbrlCompanyFactFixture(
                field_name="net_sales_2024",
                label="Net sales",
                value=391_000_000_000,
                unit="USD",
                period="FY2024",
                as_of_date="2025-09-27",
                source_document_id="provider_sec_aapl_xbrl_2026",
                citation_id="provider_cite_aapl_xbrl_sales",
            ),
            SecXbrlCompanyFactFixture(
                field_name="net_sales_2023",
                label="Net sales",
                value=383_300_000_000,
                unit="USD",
                period="FY2023",
                as_of_date="2024-09-28",
                source_document_id="provider_sec_aapl_xbrl_2026",
                citation_id="provider_cite_aapl_xbrl_sales",
            ),
        ),
        evidence_gaps=(
            SecEvidenceGapFixture(
                field_name="current_valuation_metrics",
                evidence_state=EvidenceState.unavailable,
                freshness_state=FreshnessState.unavailable,
                message="The SEC fixture does not provide current market valuation metrics.",
            ),
        ),
    )
}


def sec_stock_fixture_for_ticker(ticker: str) -> SecStockFixture | None:
    return SEC_STOCK_FIXTURES.get(normalize_ticker(ticker))


def build_sec_stock_provider_response(
    adapter: SecProviderAdapterLike,
    request: ProviderRequestMetadata,
    licensing: ProviderLicensing,
) -> ProviderResponse:
    ticker = normalize_ticker(request.normalized_ticker)
    fixture = sec_stock_fixture_for_ticker(ticker)
    if fixture is None:
        raise SecStockFixtureContractError(f"No deterministic SEC stock fixture is registered for {ticker}.")

    _validate_fixture_binding(fixture, ticker)
    sources = [_source_attribution(adapter, request.data_category, source, licensing) for source in fixture.sources]
    facts = _facts_from_fixture(fixture, request.data_category)
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
            as_of_date="2026-04-01",
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
        ),
        licensing=licensing,
        errors=[],
        no_live_external_calls=True,
        message=(
            f"Deterministic SEC fixture contract for {ticker}: submissions, selected filing metadata, "
            "XBRL company facts, and evidence gaps only; no generated output was created."
        ),
    )


def _asset_identity(identity: SecStockIdentityFixture) -> AssetIdentity:
    return ASSETS[identity.ticker]["identity"].model_copy(deep=True)


def _source_attribution(
    adapter: SecProviderAdapterLike,
    data_category: ProviderDataCategory,
    source: SecStockSourceFixture,
    licensing: ProviderLicensing,
) -> ProviderSourceAttribution:
    decision = resolve_source_policy(url=source.url)
    if not source_can_support_generated_output(decision):
        raise SecStockFixtureContractError(f"SEC source {source.source_document_id} cannot support generated claims.")
    if not decision.canonical_facts_allowed:
        raise SecStockFixtureContractError(f"SEC source {source.source_document_id} cannot support canonical facts.")

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
        data_category=data_category,
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


def _facts_from_fixture(fixture: SecStockFixture, data_category: ProviderDataCategory) -> list[ProviderFact]:
    identity = fixture.identity
    facts = [
        ProviderFact(
            fact_id=f"provider_fact_{identity.ticker.lower()}_sec_identity",
            asset_ticker=identity.ticker,
            data_category=data_category,
            field_name="sec_stock_identity",
            value={
                "ticker": identity.ticker,
                "company_name": identity.company_name,
                "cik": identity.cik,
                "exchange": identity.exchange,
                "asset_type": identity.asset_type,
                "support_state": identity.support_state,
                "top500_manifest_member": identity.top500_manifest_member,
                "eligible_not_cached": identity.eligible_not_cached,
            },
            as_of_date="2026-04-01",
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            source_document_ids=[identity.submissions_source_document_id],
            citation_ids=[f"provider_cite_{identity.ticker.lower()}_sec_identity"],
            fact_layer="canonical",
            uses_glossary_as_support=False,
        ),
        ProviderFact(
            fact_id=f"provider_fact_{identity.ticker.lower()}_primary_business",
            asset_ticker=identity.ticker,
            data_category=data_category,
            field_name="primary_business",
            value="Designs, manufactures, and markets consumer technology products and services.",
            as_of_date="2026-04-01",
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            source_document_ids=["provider_sec_aapl_10k_2026"],
            citation_ids=["provider_cite_aapl_primary_business"],
            fact_layer="canonical",
            uses_glossary_as_support=False,
        ),
        ProviderFact(
            fact_id=f"provider_fact_{identity.ticker.lower()}_net_sales_trend",
            asset_ticker=identity.ticker,
            data_category=data_category,
            field_name="net_sales_trend_available",
            value=True,
            as_of_date="2026-04-01",
            retrieved_at=STUB_TIMESTAMP,
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            source_document_ids=["provider_sec_aapl_xbrl_2026"],
            citation_ids=["provider_cite_aapl_xbrl_sales"],
            fact_layer="canonical",
            uses_glossary_as_support=False,
        ),
    ]

    for filing in fixture.selected_filings:
        source = _source_by_id(fixture, filing.source_document_id)
        facts.append(
            ProviderFact(
                fact_id=f"provider_fact_{identity.ticker.lower()}_{filing.form_type.lower().replace('-', '')}_metadata",
                asset_ticker=identity.ticker,
                data_category=data_category,
                field_name="selected_sec_filing_metadata",
                value={
                    "form_type": filing.form_type,
                    "accession_or_fixture_id": filing.accession_or_fixture_id,
                    "filing_date": filing.filing_date,
                    "report_date": filing.report_date,
                    "source_document_id": filing.source_document_id,
                    "official_publisher": source.publisher,
                    "official_title": source.title,
                    "official_url": source.url,
                    "retrieved_at": STUB_TIMESTAMP,
                    "freshness_state": source.freshness_state.value,
                },
                as_of_date=filing.filing_date,
                retrieved_at=STUB_TIMESTAMP,
                freshness_state=FreshnessState.fresh,
                evidence_state=EvidenceState.supported,
                source_document_ids=[filing.source_document_id],
                citation_ids=[filing.citation_id],
                fact_layer="canonical",
                uses_glossary_as_support=False,
            )
        )

    for fact in fixture.xbrl_company_facts:
        facts.append(
            ProviderFact(
                fact_id=f"provider_fact_{identity.ticker.lower()}_xbrl_{fact.field_name}",
                asset_ticker=identity.ticker,
                data_category=data_category,
                field_name=f"xbrl_company_fact_{fact.field_name}",
                value={
                    "field_name": fact.field_name,
                    "label": fact.label,
                    "value": fact.value,
                    "unit": fact.unit,
                    "period": fact.period,
                    "as_of_date": fact.as_of_date,
                    "fact_layer": fact.fact_layer,
                    "source_document_ids": [fact.source_document_id],
                    "citation_ids": [fact.citation_id],
                },
                unit=fact.unit,
                as_of_date=fact.as_of_date,
                retrieved_at=STUB_TIMESTAMP,
                freshness_state=FreshnessState.fresh,
                evidence_state=EvidenceState.supported,
                source_document_ids=[fact.source_document_id],
                citation_ids=[fact.citation_id],
                fact_layer="canonical",
                uses_glossary_as_support=False,
            )
        )

    for gap in fixture.evidence_gaps:
        facts.append(
            ProviderFact(
                fact_id=f"provider_gap_{identity.ticker.lower()}_{gap.field_name}",
                asset_ticker=identity.ticker,
                data_category=data_category,
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


def _validate_fixture_binding(fixture: SecStockFixture, requested_ticker: str) -> None:
    identity = fixture.identity
    manifest_entry = top500_stock_universe_entry(identity.ticker)
    if identity.ticker != requested_ticker:
        raise SecStockFixtureContractError("SEC fixture ticker does not match the requested ticker.")
    if manifest_entry is None:
        raise SecStockFixtureContractError(f"{identity.ticker} is not present in the Top-500 manifest.")
    if identity.cik != manifest_entry.cik:
        raise SecStockFixtureContractError(f"{identity.ticker} SEC CIK does not match the Top-500 manifest.")
    if identity.company_name != manifest_entry.name or identity.exchange != manifest_entry.exchange:
        raise SecStockFixtureContractError(f"{identity.ticker} SEC identity disagrees with the Top-500 manifest.")
    if identity.asset_type != "stock" or identity.support_state != "supported":
        raise SecStockFixtureContractError("SEC fixture can only represent supported common-stock identity.")
    if identity.eligible_not_cached or not identity.top500_manifest_member:
        raise SecStockFixtureContractError("SEC fixture cannot create generated evidence for eligible-not-cached stocks.")


def _validate_response_contract(
    fixture: SecStockFixture,
    sources: list[ProviderSourceAttribution],
    facts: list[ProviderFact],
) -> None:
    ticker = fixture.identity.ticker
    source_by_id = {source.source_document_id: source for source in sources}
    if len(source_by_id) != len(sources):
        raise SecStockFixtureContractError("SEC fixture contains duplicate source document IDs.")

    for source in sources:
        if source.asset_ticker != ticker:
            raise SecStockFixtureContractError(f"SEC source {source.source_document_id} is bound to the wrong asset.")
        if source.provider_kind is not ProviderKind.sec or not source.is_official:
            raise SecStockFixtureContractError(f"SEC source {source.source_document_id} must be official SEC evidence.")
        if source.source_quality is not SourceQuality.official:
            raise SecStockFixtureContractError(f"SEC source {source.source_document_id} must have official quality.")
        if source.allowlist_status is not SourceAllowlistStatus.allowed:
            raise SecStockFixtureContractError(f"SEC source {source.source_document_id} is not allowlisted.")
        if source.source_use_policy is SourceUsePolicy.rejected:
            raise SecStockFixtureContractError(f"SEC source {source.source_document_id} is rejected.")
        if not source.permitted_operations.can_support_generated_output:
            raise SecStockFixtureContractError(f"SEC source {source.source_document_id} cannot support generated output.")
        if not source.permitted_operations.can_support_citations:
            raise SecStockFixtureContractError(f"SEC source {source.source_document_id} cannot support citations.")
        if not source.permitted_operations.can_support_canonical_facts:
            raise SecStockFixtureContractError(f"SEC source {source.source_document_id} cannot support canonical facts.")

    for fact in facts:
        if fact.asset_ticker != ticker:
            raise SecStockFixtureContractError(f"SEC fact {fact.fact_id} is bound to the wrong asset.")
        if fact.uses_glossary_as_support:
            raise SecStockFixtureContractError(f"SEC fact {fact.fact_id} cannot use glossary as evidence.")
        if fact.evidence_state is EvidenceState.supported and not fact.source_document_ids:
            raise SecStockFixtureContractError(f"SEC fact {fact.fact_id} lacks source documents.")
        for source_document_id in fact.source_document_ids:
            source = source_by_id.get(source_document_id)
            if source is None or source.asset_ticker != ticker:
                raise SecStockFixtureContractError(f"SEC fact {fact.fact_id} references invalid source evidence.")
            if source.source_use_policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only, SourceUsePolicy.rejected}:
                raise SecStockFixtureContractError(f"SEC fact {fact.fact_id} references source-use-blocked evidence.")


def _source_by_id(fixture: SecStockFixture, source_document_id: str) -> SecStockSourceFixture:
    for source in fixture.sources:
        if source.source_document_id == source_document_id:
            return source
    raise SecStockFixtureContractError(f"SEC fixture references missing source {source_document_id}.")


def _ticker_from_source_id(source_document_id: str) -> str:
    parts = source_document_id.split("_")
    if len(parts) < 3 or parts[0] != "provider" or parts[1] != "sec":
        raise SecStockFixtureContractError(f"SEC source ID has an invalid deterministic shape: {source_document_id}.")
    return parts[2].upper()

