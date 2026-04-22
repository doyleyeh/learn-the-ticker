from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AssetType(str, Enum):
    stock = "stock"
    etf = "etf"
    unsupported = "unsupported"
    unknown = "unknown"


class AssetStatus(str, Enum):
    supported = "supported"
    unsupported = "unsupported"
    unknown = "unknown"


class SearchResultStatus(str, Enum):
    supported = "supported"
    unsupported = "unsupported"
    unknown = "unknown"
    ingestion_needed = "ingestion_needed"


class SearchResponseStatus(str, Enum):
    supported = "supported"
    ambiguous = "ambiguous"
    unsupported = "unsupported"
    unknown = "unknown"
    ingestion_needed = "ingestion_needed"


class SearchSupportClassification(str, Enum):
    cached_supported = "cached_supported"
    recognized_unsupported = "recognized_unsupported"
    unknown = "unknown"
    eligible_not_cached = "eligible_not_cached"


class FreshnessState(str, Enum):
    fresh = "fresh"
    stale = "stale"
    unknown = "unknown"
    unavailable = "unavailable"


class EvidenceState(str, Enum):
    supported = "supported"
    no_major_recent_development = "no_major_recent_development"
    unavailable = "unavailable"
    unknown = "unknown"
    stale = "stale"
    mixed = "mixed"
    insufficient_evidence = "insufficient_evidence"
    unsupported = "unsupported"


class OverviewSectionType(str, Enum):
    stable_facts = "stable_facts"
    risk = "risk"
    recent_developments = "recent_developments"
    educational_suitability = "educational_suitability"
    evidence_gap = "evidence_gap"


class IngestionJobType(str, Enum):
    pre_cache = "pre_cache"
    on_demand = "on_demand"
    refresh = "refresh"
    repair = "repair"


class IngestionJobState(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    refresh_needed = "refresh_needed"
    no_ingestion_needed = "no_ingestion_needed"
    unsupported = "unsupported"
    unknown = "unknown"
    unavailable = "unavailable"


class IngestionWorkerStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class SafetyClassification(str, Enum):
    educational = "educational"
    personalized_advice_redirect = "personalized_advice_redirect"
    unsupported_asset_redirect = "unsupported_asset_redirect"
    insufficient_evidence = "insufficient_evidence"


EDUCATIONAL_DISCLAIMER = (
    "This page is for educational and research purposes only. It is not investment, financial, legal, "
    "or tax advice and is not a recommendation to buy, sell, or hold any security. Content is generated "
    "from public filings, issuer materials, market/reference data, and news sources where available. "
    "Data may be delayed, incomplete, inaccurate, or outdated. Please review the cited sources and "
    "consider consulting a qualified professional before making financial decisions."
)


class ExportFormat(str, Enum):
    markdown = "markdown"
    json = "json"


class ExportContentType(str, Enum):
    asset_page = "asset_page"
    asset_source_list = "asset_source_list"
    comparison = "comparison"
    chat_transcript = "chat_transcript"


class ExportState(str, Enum):
    available = "available"
    unsupported = "unsupported"
    unavailable = "unavailable"


class ProviderKind(str, Enum):
    sec = "sec"
    etf_issuer = "etf_issuer"
    market_reference = "market_reference"
    recent_development = "recent_development"


class ProviderDataCategory(str, Enum):
    asset_resolution = "asset_resolution"
    canonical_stock_facts = "canonical_stock_facts"
    etf_issuer_facts = "etf_issuer_facts"
    etf_holdings_metadata = "etf_holdings_metadata"
    market_reference = "market_reference"
    recent_developments = "recent_developments"


class ProviderResponseState(str, Enum):
    supported = "supported"
    eligible_not_cached = "eligible_not_cached"
    unsupported = "unsupported"
    unknown = "unknown"
    unavailable = "unavailable"
    stale = "stale"
    permission_limited = "permission_limited"
    rate_limited = "rate_limited"
    no_high_signal = "no_high_signal"


class ProviderSourceUsage(str, Enum):
    canonical = "canonical"
    structured_reference = "structured_reference"
    recent_context = "recent_context"


class AssetIdentity(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType
    exchange: str | None = None
    issuer: str | None = None
    status: AssetStatus
    supported: bool


class StateMessage(BaseModel):
    status: AssetStatus
    message: str


class SearchState(BaseModel):
    status: SearchResponseStatus
    message: str
    result_count: int
    support_classification: SearchSupportClassification | None = None
    requires_disambiguation: bool = False
    requires_ingestion: bool = False
    can_open_generated_page: bool = False
    generated_route: str | None = None
    can_request_ingestion: bool = False
    ingestion_request_route: str | None = None


class SearchResult(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType
    exchange: str | None = None
    issuer: str | None = None
    supported: bool
    status: SearchResultStatus
    support_classification: SearchSupportClassification
    eligible_for_ingestion: bool = False
    requires_ingestion: bool = False
    can_open_generated_page: bool = False
    can_answer_chat: bool = False
    can_compare: bool = False
    generated_route: str | None = None
    can_request_ingestion: bool = False
    ingestion_request_route: str | None = None
    message: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    state: SearchState


class IngestionErrorMetadata(BaseModel):
    code: str
    message: str
    retryable: bool


class IngestionCapabilities(BaseModel):
    can_open_generated_page: bool = False
    can_answer_chat: bool = False
    can_compare: bool = False
    can_request_ingestion: bool = False


class IngestionJobResponse(BaseModel):
    ticker: str
    asset_type: AssetType
    job_type: IngestionJobType | None = None
    job_id: str | None = None
    job_state: IngestionJobState
    worker_status: IngestionWorkerStatus | None = None
    created_at: str | None = None
    updated_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    status_url: str | None = None
    retryable: bool = False
    error_metadata: IngestionErrorMetadata | None = None
    generated_route: str | None = None
    capabilities: IngestionCapabilities = Field(default_factory=IngestionCapabilities)
    message: str


class PreCacheJobResponse(BaseModel):
    batch_id: str | None = None
    ticker: str
    name: str | None = None
    asset_type: AssetType
    launch_group: str | None = None
    job_type: IngestionJobType = IngestionJobType.pre_cache
    job_id: str
    job_state: IngestionJobState
    worker_status: IngestionWorkerStatus | None = None
    created_at: str | None = None
    updated_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    status_url: str
    retryable: bool = False
    error_metadata: IngestionErrorMetadata | None = None
    generated_route: str | None = None
    capabilities: IngestionCapabilities = Field(default_factory=IngestionCapabilities)
    generated_output_available: bool = False
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    message: str


class PreCacheBatchSummary(BaseModel):
    total_launch_assets: int
    cached_or_already_available_assets: int
    queued_or_pending_assets: int
    running_assets: int
    failed_assets: int
    unsupported_assets: int
    unknown_assets: int
    generated_output_available_assets: int


class PreCacheBatchResponse(BaseModel):
    batch_id: str
    job_type: IngestionJobType = IngestionJobType.pre_cache
    status_url: str
    created_at: str
    updated_at: str
    deterministic: bool = True
    no_live_external_calls: bool = True
    summary: PreCacheBatchSummary
    jobs: list[PreCacheJobResponse]
    message: str


class ProviderRequestMetadata(BaseModel):
    request_id: str
    requested_ticker: str
    normalized_ticker: str
    requested_at: str
    data_category: ProviderDataCategory


class ProviderCapability(BaseModel):
    provider_name: str
    provider_kind: ProviderKind
    data_categories: list[ProviderDataCategory]
    supports_asset_resolution: bool = False
    supports_canonical_facts: bool = False
    supports_recent_developments: bool = False
    requires_credentials: bool = False
    live_calls_allowed: bool = False


class ProviderLicensing(BaseModel):
    provider_name: str
    attribution_required: bool
    display_allowed: bool
    cache_allowed: bool
    export_allowed: bool
    redistribution_allowed: bool
    allowed_export_fields: list[str] = Field(default_factory=list)
    permission_note: str


class ProviderSourceAttribution(BaseModel):
    source_document_id: str
    asset_ticker: str
    source_type: str
    title: str
    publisher: str
    url: str | None = None
    published_at: str | None = None
    as_of_date: str | None = None
    retrieved_at: str
    freshness_state: FreshnessState
    is_official: bool
    provider_name: str
    provider_kind: ProviderKind
    data_category: ProviderDataCategory
    usage: ProviderSourceUsage
    source_rank: int
    can_support_canonical_facts: bool
    can_support_recent_developments: bool
    licensing: ProviderLicensing


class ProviderFact(BaseModel):
    fact_id: str
    asset_ticker: str
    data_category: ProviderDataCategory
    field_name: str
    value: Any
    unit: str | None = None
    as_of_date: str | None = None
    retrieved_at: str
    freshness_state: FreshnessState
    evidence_state: EvidenceState
    source_document_ids: list[str]
    citation_ids: list[str] = Field(default_factory=list)
    fact_layer: Literal["canonical", "structured_reference"] = "canonical"
    uses_glossary_as_support: bool = False


class ProviderRecentDevelopmentCandidate(BaseModel):
    event_id: str
    asset_ticker: str
    event_type: str
    title: str
    summary: str
    event_date: str
    source_date: str | None = None
    as_of_date: str | None = None
    retrieved_at: str
    freshness_state: FreshnessState
    source_document_id: str
    citation_ids: list[str] = Field(default_factory=list)
    is_high_signal: bool
    can_overwrite_canonical_facts: bool = False


class ProviderResponseFreshness(BaseModel):
    as_of_date: str | None = None
    retrieved_at: str
    freshness_state: FreshnessState
    stale_reason: str | None = None


class ProviderError(BaseModel):
    code: str
    message: str
    retryable: bool
    response_state: ProviderResponseState


class ProviderGeneratedOutputFlags(BaseModel):
    creates_generated_asset_page: bool = False
    creates_generated_chat_answer: bool = False
    creates_generated_comparison: bool = False
    creates_overview_sections: bool = False
    creates_export_payload: bool = False
    creates_frontend_route: bool = False


class ProviderResponse(BaseModel):
    request_metadata: ProviderRequestMetadata
    provider_name: str
    provider_kind: ProviderKind
    data_category: ProviderDataCategory
    state: ProviderResponseState
    capability: ProviderCapability
    asset: AssetIdentity | None = None
    source_attributions: list[ProviderSourceAttribution] = Field(default_factory=list)
    facts: list[ProviderFact] = Field(default_factory=list)
    recent_developments: list[ProviderRecentDevelopmentCandidate] = Field(default_factory=list)
    freshness: ProviderResponseFreshness
    licensing: ProviderLicensing
    errors: list[ProviderError] = Field(default_factory=list)
    generated_output: ProviderGeneratedOutputFlags = Field(default_factory=ProviderGeneratedOutputFlags)
    no_live_external_calls: bool = True
    message: str


class CacheEntryKind(str, Enum):
    asset_page = "asset_page"
    comparison = "comparison"
    chat_answer = "chat_answer"
    export_payload = "export_payload"
    source_list = "source_list"
    pre_cache_job = "pre_cache_job"
    refresh_job = "refresh_job"
    knowledge_pack = "knowledge_pack"


class CacheScope(str, Enum):
    asset = "asset"
    comparison = "comparison"
    chat = "chat"
    export = "export"
    job = "job"
    knowledge_pack = "knowledge_pack"


class CacheEntryState(str, Enum):
    available = "available"
    hit = "hit"
    miss = "miss"
    stale = "stale"
    hash_mismatch = "hash_mismatch"
    expired = "expired"
    permission_limited = "permission_limited"
    unsupported = "unsupported"
    unknown = "unknown"
    unavailable = "unavailable"
    eligible_not_cached = "eligible_not_cached"


class KnowledgePackBuildState(str, Enum):
    available = "available"
    eligible_not_cached = "eligible_not_cached"
    unsupported = "unsupported"
    unknown = "unknown"
    unavailable = "unavailable"


class CacheInvalidationReason(str, Enum):
    none = "none"
    no_entry = "no_entry"
    cache_key_mismatch = "cache_key_mismatch"
    stale_input = "stale_input"
    hash_mismatch = "hash_mismatch"
    expired = "expired"
    permission_limited = "permission_limited"
    unsupported = "unsupported"
    unknown = "unknown"
    unavailable = "unavailable"
    eligible_not_cached = "eligible_not_cached"


class CacheKeyMetadata(BaseModel):
    entry_kind: CacheEntryKind
    scope: CacheScope
    schema_version: str
    source_freshness_state: FreshnessState
    mode_or_output_type: str
    asset_ticker: str | None = None
    comparison_left_ticker: str | None = None
    comparison_right_ticker: str | None = None
    pack_identity: str | None = None
    prompt_version: str | None = None
    model_name: str | None = None
    input_freshness_hash: str | None = None


class SourceChecksumInput(BaseModel):
    source_document_id: str
    asset_ticker: str
    source_type: str
    source_rank: int | None = None
    publisher: str
    url: str | None = None
    published_at: str | None = None
    as_of_date: str | None = None
    retrieved_at: str | None = None
    freshness_state: FreshnessState
    content_type: str | None = None
    provider_name: str | None = None
    fact_bindings: list[str] = Field(default_factory=list)
    recent_event_bindings: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    local_chunk_text_fingerprints: list[str] = Field(default_factory=list)
    cache_allowed: bool = True
    redistribution_allowed: bool = False


class SourceChecksumRecord(BaseModel):
    source_document_id: str
    asset_ticker: str
    checksum: str
    freshness_state: FreshnessState
    cache_allowed: bool
    source_type: str
    source_rank: int | None = None
    citation_ids: list[str] = Field(default_factory=list)
    fact_bindings: list[str] = Field(default_factory=list)
    recent_event_bindings: list[str] = Field(default_factory=list)


class FreshnessFactInput(BaseModel):
    fact_id: str
    asset_ticker: str
    field_name: str
    value: Any
    as_of_date: str | None = None
    freshness_state: FreshnessState
    evidence_state: str
    source_document_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)


class FreshnessRecentEventInput(BaseModel):
    event_id: str
    asset_ticker: str
    event_type: str
    event_date: str | None = None
    source_date: str | None = None
    as_of_date: str | None = None
    freshness_state: FreshnessState
    evidence_state: str
    source_document_id: str | None = None
    citation_ids: list[str] = Field(default_factory=list)


class FreshnessEvidenceGapInput(BaseModel):
    gap_id: str
    asset_ticker: str
    field_name: str
    evidence_state: str
    freshness_state: FreshnessState
    source_document_id: str | None = None


class SectionFreshnessInput(BaseModel):
    section_id: str
    freshness_state: FreshnessState
    evidence_state: str | None = None
    as_of_date: str | None = None
    retrieved_at: str | None = None


class KnowledgePackFreshnessInput(BaseModel):
    asset_ticker: str | None = None
    comparison_left_ticker: str | None = None
    comparison_right_ticker: str | None = None
    pack_identity: str | None = None
    source_checksums: list[SourceChecksumRecord] = Field(default_factory=list)
    canonical_facts: list[FreshnessFactInput] = Field(default_factory=list)
    recent_events: list[FreshnessRecentEventInput] = Field(default_factory=list)
    evidence_gaps: list[FreshnessEvidenceGapInput] = Field(default_factory=list)
    page_freshness_state: FreshnessState
    section_freshness_labels: list[SectionFreshnessInput] = Field(default_factory=list)


class GeneratedOutputFreshnessInput(BaseModel):
    output_identity: str
    entry_kind: CacheEntryKind
    scope: CacheScope
    schema_version: str
    source_freshness_state: FreshnessState
    prompt_version: str | None = None
    model_name: str | None = None
    source_checksums: list[SourceChecksumRecord] = Field(default_factory=list)
    canonical_facts: list[FreshnessFactInput] = Field(default_factory=list)
    recent_events: list[FreshnessRecentEventInput] = Field(default_factory=list)
    evidence_gaps: list[FreshnessEvidenceGapInput] = Field(default_factory=list)
    section_freshness_labels: list[SectionFreshnessInput] = Field(default_factory=list)


class CacheEntryMetadata(BaseModel):
    cache_key: str
    entry_kind: CacheEntryKind
    scope: CacheScope
    entry_state: CacheEntryState = CacheEntryState.available
    schema_version: str
    generated_output_freshness_hash: str | None = None
    source_checksum_hashes: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    source_freshness_states: dict[str, FreshnessState] = Field(default_factory=dict)
    section_freshness_labels: dict[str, FreshnessState] = Field(default_factory=dict)
    unknown_states: list[str] = Field(default_factory=list)
    stale_states: list[str] = Field(default_factory=list)
    unavailable_states: list[str] = Field(default_factory=list)
    cache_allowed: bool = True
    export_allowed: bool = False
    created_at: str | None = None
    expires_at: str | None = None
    prompt_version: str | None = None
    model_name: str | None = None


class CacheRevalidationResult(BaseModel):
    state: CacheEntryState
    reusable: bool
    invalidation_reason: CacheInvalidationReason
    cache_key: str | None = None
    expected_freshness_hash: str | None = None
    cached_freshness_hash: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    source_freshness_states: dict[str, FreshnessState] = Field(default_factory=dict)
    section_freshness_labels: dict[str, FreshnessState] = Field(default_factory=dict)
    message: str


class Freshness(BaseModel):
    page_last_updated_at: str
    facts_as_of: str | None = None
    holdings_as_of: str | None = None
    recent_events_as_of: str | None = None
    freshness_state: FreshnessState


class KnowledgePackCounts(BaseModel):
    source_document_count: int = 0
    citation_count: int = 0
    normalized_fact_count: int = 0
    source_chunk_count: int = 0
    recent_development_count: int = 0
    evidence_gap_count: int = 0


class KnowledgePackSourceMetadata(BaseModel):
    source_document_id: str
    asset_ticker: str
    source_type: str
    source_rank: int
    title: str
    publisher: str
    url: str
    published_at: str | None = None
    as_of_date: str | None = None
    retrieved_at: str
    freshness_state: FreshnessState
    is_official: bool
    citation_ids: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    recent_event_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)


class KnowledgePackFactMetadata(BaseModel):
    fact_id: str
    asset_ticker: str
    fact_type: str
    field_name: str
    source_document_id: str
    source_chunk_id: str
    extraction_method: str
    freshness_state: FreshnessState
    evidence_state: str
    as_of_date: str | None = None
    citation_ids: list[str] = Field(default_factory=list)


class KnowledgePackChunkMetadata(BaseModel):
    chunk_id: str
    asset_ticker: str
    source_document_id: str
    section_name: str
    chunk_order: int
    token_count: int
    supported_claim_types: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)


class KnowledgePackRecentDevelopmentMetadata(BaseModel):
    event_id: str
    asset_ticker: str
    event_type: str
    event_date: str | None = None
    source_document_id: str
    source_chunk_id: str
    importance_score: float
    freshness_state: FreshnessState
    evidence_state: str
    citation_ids: list[str] = Field(default_factory=list)


class KnowledgePackEvidenceGapMetadata(BaseModel):
    gap_id: str
    asset_ticker: str
    field_name: str
    evidence_state: str
    freshness_state: FreshnessState
    source_document_id: str | None = None
    source_chunk_id: str | None = None
    message: str | None = None


class KnowledgePackBuildResponse(BaseModel):
    schema_version: str
    ticker: str
    asset: AssetIdentity
    asset_type: AssetType
    pack_id: str
    build_state: KnowledgePackBuildState
    state: StateMessage
    generated_output_available: bool = False
    reusable_generated_output_cache_hit: bool = False
    generated_route: str | None = None
    capabilities: IngestionCapabilities = Field(default_factory=IngestionCapabilities)
    freshness: Freshness
    section_freshness: list[SectionFreshnessInput] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    counts: KnowledgePackCounts = Field(default_factory=KnowledgePackCounts)
    source_documents: list[KnowledgePackSourceMetadata] = Field(default_factory=list)
    normalized_facts: list[KnowledgePackFactMetadata] = Field(default_factory=list)
    source_chunks: list[KnowledgePackChunkMetadata] = Field(default_factory=list)
    recent_developments: list[KnowledgePackRecentDevelopmentMetadata] = Field(default_factory=list)
    evidence_gaps: list[KnowledgePackEvidenceGapMetadata] = Field(default_factory=list)
    source_checksums: list[SourceChecksumRecord] = Field(default_factory=list)
    knowledge_pack_freshness_hash: str | None = None
    cache_key: str | None = None
    cache_revalidation: CacheRevalidationResult | None = None
    no_live_external_calls: bool = True
    exports_full_source_documents: bool = False
    message: str


class Citation(BaseModel):
    citation_id: str
    source_document_id: str
    title: str
    publisher: str
    freshness_state: FreshnessState


class SourceDocument(BaseModel):
    source_document_id: str
    source_type: str
    title: str
    publisher: str
    url: str
    published_at: str | None = None
    as_of_date: str | None = None
    retrieved_at: str
    freshness_state: FreshnessState
    is_official: bool
    supporting_passage: str


class MetricValue(BaseModel):
    value: str | float | int | None
    unit: str | None = None
    citation_ids: list[str] = Field(default_factory=list)


class BeginnerSummary(BaseModel):
    what_it_is: str
    why_people_consider_it: str
    main_catch: str


class RiskItem(BaseModel):
    title: str
    plain_english_explanation: str
    citation_ids: list[str]


class RecentDevelopment(BaseModel):
    title: str
    summary: str
    event_date: str | None = None
    citation_ids: list[str]
    freshness_state: FreshnessState


class SuitabilitySummary(BaseModel):
    may_fit: str
    may_not_fit: str
    learn_next: str


class Claim(BaseModel):
    claim_id: str
    claim_text: str
    citation_ids: list[str]


class OverviewMetric(BaseModel):
    metric_id: str
    label: str
    value: str | float | int | None = None
    unit: str | None = None
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    freshness_state: FreshnessState
    evidence_state: EvidenceState
    as_of_date: str | None = None
    retrieved_at: str | None = None
    limitations: str | None = None


class OverviewSectionItem(BaseModel):
    item_id: str
    title: str
    summary: str
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    freshness_state: FreshnessState
    evidence_state: EvidenceState
    event_date: str | None = None
    as_of_date: str | None = None
    retrieved_at: str | None = None
    limitations: str | None = None


class OverviewSection(BaseModel):
    section_id: str
    title: str
    section_type: OverviewSectionType
    applies_to: list[AssetType]
    beginner_summary: str | None = None
    items: list[OverviewSectionItem] = Field(default_factory=list)
    metrics: list[OverviewMetric] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    freshness_state: FreshnessState
    evidence_state: EvidenceState
    as_of_date: str | None = None
    retrieved_at: str | None = None
    limitations: str | None = None


class OverviewResponse(BaseModel):
    asset: AssetIdentity
    state: StateMessage
    freshness: Freshness
    snapshot: dict[str, MetricValue | str | int | float | None]
    beginner_summary: BeginnerSummary | None = None
    top_risks: list[RiskItem] = Field(default_factory=list)
    recent_developments: list[RecentDevelopment] = Field(default_factory=list)
    suitability_summary: SuitabilitySummary | None = None
    claims: list[Claim] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    sections: list[OverviewSection] = Field(default_factory=list)


class DetailsResponse(BaseModel):
    asset: AssetIdentity
    state: StateMessage
    freshness: Freshness
    facts: dict[str, MetricValue | str | int | float | list[Any] | None]
    citations: list[Citation] = Field(default_factory=list)


class SourcesResponse(BaseModel):
    asset: AssetIdentity
    state: StateMessage
    sources: list[SourceDocument] = Field(default_factory=list)


class RecentResponse(BaseModel):
    asset: AssetIdentity
    state: StateMessage
    recent_developments: list[RecentDevelopment] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class CompareRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    left_ticker: str = Field(min_length=1, max_length=12)
    right_ticker: str = Field(min_length=1, max_length=12)
    mode: Literal["beginner", "deep_dive"] = "beginner"


class KeyDifference(BaseModel):
    dimension: str
    plain_english_summary: str
    citation_ids: list[str]


class BeginnerBottomLine(BaseModel):
    summary: str
    citation_ids: list[str]


class CompareResponse(BaseModel):
    left_asset: AssetIdentity
    right_asset: AssetIdentity
    state: StateMessage
    comparison_type: str
    key_differences: list[KeyDifference] = Field(default_factory=list)
    bottom_line_for_beginners: BeginnerBottomLine | None = None
    citations: list[Citation] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = Field(default=None, max_length=100)


class ChatCitation(BaseModel):
    citation_id: str
    claim: str
    source_document_id: str
    chunk_id: str


class ChatSourceDocument(BaseModel):
    citation_id: str
    source_document_id: str
    chunk_id: str
    title: str
    source_type: str
    publisher: str
    url: str
    published_at: str | None = None
    as_of_date: str | None = None
    retrieved_at: str
    freshness_state: FreshnessState
    is_official: bool
    supporting_passage: str


class ChatResponse(BaseModel):
    asset: AssetIdentity
    direct_answer: str
    why_it_matters: str
    citations: list[ChatCitation] = Field(default_factory=list)
    source_documents: list[ChatSourceDocument] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    safety_classification: SafetyClassification


class ExportExcerpt(BaseModel):
    excerpt_id: str
    kind: Literal["supporting_passage", "excerpt_metadata"] = "supporting_passage"
    text: str | None = None
    citation_id: str | None = None
    chunk_id: str | None = None
    redistribution_allowed: bool = True
    note: str


class ExportSourceMetadata(BaseModel):
    source_document_id: str
    title: str
    source_type: str
    publisher: str
    url: str
    published_at: str | None = None
    as_of_date: str | None = None
    retrieved_at: str
    freshness_state: FreshnessState
    is_official: bool
    allowed_excerpt: ExportExcerpt | None = None


class ExportCitation(BaseModel):
    citation_id: str
    source_document_id: str
    title: str | None = None
    publisher: str | None = None
    freshness_state: FreshnessState | None = None
    claim: str | None = None


class ExportedItem(BaseModel):
    item_id: str
    title: str
    text: str
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    freshness_state: FreshnessState | None = None
    evidence_state: EvidenceState | None = None
    event_date: str | None = None
    as_of_date: str | None = None
    retrieved_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExportedSection(BaseModel):
    section_id: str
    title: str
    section_type: ExportContentType | OverviewSectionType | None = None
    text: str | None = None
    items: list[ExportedItem] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    freshness_state: FreshnessState | None = None
    evidence_state: EvidenceState | None = None
    as_of_date: str | None = None
    retrieved_at: str | None = None
    limitations: str | None = None


class ExportNote(BaseModel):
    note_id: str
    label: str
    text: str


class ComparisonExportRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    left_ticker: str = Field(min_length=1, max_length=12)
    right_ticker: str = Field(min_length=1, max_length=12)
    mode: Literal["beginner", "deep_dive"] = "beginner"
    export_format: ExportFormat = ExportFormat.markdown


class ChatTranscriptExportRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = Field(default=None, max_length=100)
    export_format: ExportFormat = ExportFormat.markdown


class ExportResponse(BaseModel):
    content_type: ExportContentType
    export_format: ExportFormat
    export_state: ExportState
    title: str
    state: StateMessage
    asset: AssetIdentity | None = None
    left_asset: AssetIdentity | None = None
    right_asset: AssetIdentity | None = None
    freshness: Freshness | None = None
    sections: list[ExportedSection] = Field(default_factory=list)
    citations: list[ExportCitation] = Field(default_factory=list)
    source_documents: list[ExportSourceMetadata] = Field(default_factory=list)
    disclaimer: str = EDUCATIONAL_DISCLAIMER
    licensing_note: ExportNote
    rendered_markdown: str
    metadata: dict[str, Any] = Field(default_factory=dict)
