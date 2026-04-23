from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    out_of_scope = "out_of_scope"
    unknown = "unknown"
    ingestion_needed = "ingestion_needed"


class SearchResponseStatus(str, Enum):
    supported = "supported"
    ambiguous = "ambiguous"
    unsupported = "unsupported"
    out_of_scope = "out_of_scope"
    unknown = "unknown"
    ingestion_needed = "ingestion_needed"


class SearchSupportClassification(str, Enum):
    cached_supported = "cached_supported"
    recognized_unsupported = "recognized_unsupported"
    out_of_scope = "out_of_scope"
    unknown = "unknown"
    eligible_not_cached = "eligible_not_cached"


class FreshnessState(str, Enum):
    fresh = "fresh"
    stale = "stale"
    unknown = "unknown"
    unavailable = "unavailable"


class EvidenceState(str, Enum):
    supported = "supported"
    partial = "partial"
    no_major_recent_development = "no_major_recent_development"
    no_high_signal = "no_high_signal"
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
    weekly_news_focus = "weekly_news_focus"
    ai_comprehensive_analysis = "ai_comprehensive_analysis"
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
    out_of_scope = "out_of_scope"
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


class ChatSessionLifecycleState(str, Enum):
    active = "active"
    expired = "expired"
    deleted = "deleted"
    ticker_mismatch = "ticker_mismatch"
    unavailable = "unavailable"


class ChatSessionDeletionStatus(str, Enum):
    active = "active"
    user_deleted = "user_deleted"
    expired = "expired"
    unavailable = "unavailable"


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
    out_of_scope = "out_of_scope"
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


class SourceUsePolicy(str, Enum):
    metadata_only = "metadata_only"
    link_only = "link_only"
    summary_allowed = "summary_allowed"
    full_text_allowed = "full_text_allowed"
    rejected = "rejected"


class SourceAllowlistStatus(str, Enum):
    allowed = "allowed"
    rejected = "rejected"
    pending_review = "pending_review"
    not_allowlisted = "not_allowlisted"


class SourceQuality(str, Enum):
    official = "official"
    issuer = "issuer"
    provider = "provider"
    fixture = "fixture"
    allowlisted = "allowlisted"
    rejected = "rejected"
    unknown = "unknown"


class SourcePolicyDecisionState(str, Enum):
    allowed = "allowed"
    rejected = "rejected"
    pending_review = "pending_review"
    not_allowlisted = "not_allowlisted"


class SourceOperationPermissions(BaseModel):
    can_store_metadata: bool
    can_store_raw_text: bool = False
    can_display_metadata: bool
    can_display_excerpt: bool = False
    can_summarize: bool = False
    can_cache: bool = False
    can_export_metadata: bool = False
    can_export_excerpt: bool = False
    can_export_full_text: bool = False
    can_support_generated_output: bool = False
    can_support_citations: bool = False
    can_support_canonical_facts: bool = False
    can_support_recent_developments: bool = False


class SourceAllowedExcerptBehavior(BaseModel):
    allowed: bool
    max_words: int = 0
    requires_attribution: bool = True
    note: str


class SourceAllowlistReviewMetadata(BaseModel):
    reviewed_by: str
    reviewed_at: str
    approval_reference: str
    rationale: str

    @field_validator("reviewed_at", mode="before")
    @classmethod
    def _coerce_review_date(cls, value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return value


class SourceAllowlistRecord(BaseModel):
    source_id: str
    display_name: str
    match_kind: Literal["domain", "local_fixture", "provider"]
    domain: str | None = None
    fixture_identifier: str | None = None
    provider_name: str | None = None
    source_type: str
    source_quality: SourceQuality
    allowlist_status: SourceAllowlistStatus
    source_use_policy: SourceUsePolicy
    permitted_operations: SourceOperationPermissions
    allowed_excerpt: SourceAllowedExcerptBehavior
    recent_context_only: bool = False
    canonical_facts_allowed: bool = False
    review: SourceAllowlistReviewMetadata


class SourceAllowlistManifest(BaseModel):
    schema_version: Literal["source-allowlist-v1"]
    policy_version: str
    generated_at: str
    no_live_external_calls: bool = True
    source_records: list[SourceAllowlistRecord]

    @field_validator("generated_at", mode="before")
    @classmethod
    def _coerce_generated_at(cls, value: Any) -> str:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value


class SourcePolicyDecision(BaseModel):
    decision: SourcePolicyDecisionState
    source_id: str | None = None
    matched_by: Literal["domain", "local_fixture", "provider", "none"] = "none"
    source_quality: SourceQuality = SourceQuality.unknown
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.not_allowlisted
    source_use_policy: SourceUsePolicy = SourceUsePolicy.rejected
    permitted_operations: SourceOperationPermissions
    allowed_excerpt: SourceAllowedExcerptBehavior
    recent_context_only: bool = False
    canonical_facts_allowed: bool = False
    reason: str


DEFAULT_ALLOWED_SOURCE_OPERATIONS = SourceOperationPermissions(
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
    can_support_recent_developments=False,
)

DEFAULT_ALLOWED_EXCERPT_BEHAVIOR = SourceAllowedExcerptBehavior(
    allowed=True,
    max_words=80,
    requires_attribution=True,
    note="Short supporting passages may be displayed or exported with source attribution; full source text is not exported.",
)

DEFAULT_BLOCKED_SOURCE_OPERATIONS = SourceOperationPermissions(
    can_store_metadata=False,
    can_store_raw_text=False,
    can_display_metadata=False,
    can_display_excerpt=False,
    can_summarize=False,
    can_cache=False,
    can_export_metadata=False,
    can_export_excerpt=False,
    can_export_full_text=False,
    can_support_generated_output=False,
    can_support_citations=False,
    can_support_canonical_facts=False,
    can_support_recent_developments=False,
)

DEFAULT_BLOCKED_EXCERPT_BEHAVIOR = SourceAllowedExcerptBehavior(
    allowed=False,
    max_words=0,
    requires_attribution=True,
    note="No excerpt is permitted because the source is rejected, unrecognized, or not licensed for this use.",
)


class AssetIdentity(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType
    exchange: str | None = None
    issuer: str | None = None
    status: AssetStatus
    supported: bool


class Top500StockUniverseEntry(BaseModel):
    ticker: str
    name: str
    asset_type: Literal["stock"]
    security_type: str
    cik: str | None = None
    exchange: str
    rank: int
    rank_basis: str
    source_provenance: str
    snapshot_date: str
    checksum_input: str
    generated_checksum: str
    approval_timestamp: str
    launch_group: str = "large_stock"
    aliases: list[str] = Field(default_factory=list)


class Top500StockUniverseManifest(BaseModel):
    schema_version: str
    manifest_id: str
    universe_name: str
    local_path: str
    production_mirror_env_var: str
    coverage_purpose: str
    policy_note: str
    refresh_cadence: str
    snapshot_date: str
    generated_at: str
    approved_at: str
    rank_limit: int
    rank_basis: str
    source_provenance: str
    manifest_checksum_input: str
    generated_checksum: str
    entries: list[Top500StockUniverseEntry]


class StateMessage(BaseModel):
    status: AssetStatus
    message: str


class SearchBlockedCapabilityFlags(BaseModel):
    can_open_generated_page: bool = False
    can_answer_chat: bool = False
    can_compare: bool = False
    can_request_ingestion: bool = False


class SearchBlockedExplanationDiagnostics(BaseModel):
    deterministic_contract: bool = True
    generated_asset_analysis: bool = False
    includes_citations: bool = False
    includes_source_documents: bool = False
    includes_freshness: bool = False
    uses_live_calls: bool = False


class SearchBlockedExplanation(BaseModel):
    schema_version: Literal["search-blocked-explanation-v1"] = "search-blocked-explanation-v1"
    status: SearchResponseStatus | SearchResultStatus
    support_classification: SearchSupportClassification
    explanation_kind: Literal["scope_blocked_search_result"] = "scope_blocked_search_result"
    explanation_category: str
    summary: str
    scope_rationale: str
    supported_v1_scope: str
    blocked_capabilities: SearchBlockedCapabilityFlags = Field(default_factory=SearchBlockedCapabilityFlags)
    ingestion_eligible: bool = False
    ingestion_request_route: str | None = None
    diagnostics: SearchBlockedExplanationDiagnostics = Field(default_factory=SearchBlockedExplanationDiagnostics)


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
    blocked_explanation: SearchBlockedExplanation | None = None


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
    blocked_explanation: SearchBlockedExplanation | None = None


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
    source_use_policy: SourceUsePolicy = SourceUsePolicy.full_text_allowed
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
    permitted_operations: SourceOperationPermissions = Field(default_factory=lambda: DEFAULT_ALLOWED_SOURCE_OPERATIONS.model_copy())


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
    source_quality: SourceQuality = SourceQuality.provider
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
    source_use_policy: SourceUsePolicy = SourceUsePolicy.full_text_allowed
    permitted_operations: SourceOperationPermissions = Field(default_factory=lambda: DEFAULT_ALLOWED_SOURCE_OPERATIONS.model_copy())


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


class LlmProviderKind(str, Enum):
    mock = "mock"
    openrouter = "openrouter"


class LlmRuntimeMode(str, Enum):
    deterministic_mock = "deterministic_mock"
    gated_live = "gated_live"


class LlmModelTier(str, Enum):
    mock = "mock"
    free = "free"
    paid = "paid"
    unavailable = "unavailable"


class LlmLiveGateState(str, Enum):
    disabled = "disabled"
    unavailable = "unavailable"
    enabled = "enabled"


class LlmGenerationAttemptStatus(str, Enum):
    not_attempted = "not_attempted"
    mock_succeeded = "mock_succeeded"
    provider_error = "provider_error"
    rate_limited = "rate_limited"
    structured_output_failed = "structured_output_failed"
    validation_failed = "validation_failed"
    validation_succeeded = "validation_succeeded"


class LlmValidationStatus(str, Enum):
    valid = "valid"
    invalid_schema = "invalid_schema"
    invalid_citation = "invalid_citation"
    invalid_source_policy = "invalid_source_policy"
    invalid_safety = "invalid_safety"
    invalid_hidden_prompt = "invalid_hidden_prompt"
    invalid_raw_reasoning = "invalid_raw_reasoning"
    invalid_unrestricted_source_text = "invalid_unrestricted_source_text"


class LlmFallbackTrigger(str, Enum):
    none = "none"
    free_chain_error = "free_chain_error"
    rate_limit = "rate_limit"
    structured_output_failure = "structured_output_failure"
    validation_failed_after_repair = "validation_failed_after_repair"


class LlmAnswerState(str, Enum):
    complete = "complete"
    partial = "partial"
    unavailable = "unavailable"


class LlmModelDescriptor(BaseModel):
    provider_kind: LlmProviderKind
    model_name: str
    tier: LlmModelTier
    order: int


class LlmRuntimeConfig(BaseModel):
    provider_kind: LlmProviderKind = LlmProviderKind.mock
    runtime_mode: LlmRuntimeMode = LlmRuntimeMode.deterministic_mock
    live_generation_enabled: bool = False
    live_gate_state: LlmLiveGateState = LlmLiveGateState.disabled
    server_side_key_present: bool = False
    endpoint_configured: bool = False
    configured_model_chain: list[LlmModelDescriptor] = Field(default_factory=list)
    paid_fallback_model: LlmModelDescriptor | None = None
    paid_fallback_enabled: bool = False
    validation_retry_count: int = 1
    reasoning_summary_only: bool = True
    live_network_calls_allowed: bool = False
    unavailable_reasons: list[str] = Field(default_factory=list)


class LlmGenerationRequestMetadata(BaseModel):
    task_name: str
    output_kind: Literal["asset_page", "comparison", "chat_answer", "export_payload", "weekly_news_analysis"]
    prompt_version: str
    schema_version: str
    safety_policy_version: str
    asset_ticker: str | None = None
    comparison_left_ticker: str | None = None
    comparison_right_ticker: str | None = None
    knowledge_pack_hash: str | None = None
    source_freshness_hash: str | None = None
    request_id: str = "deterministic-llm-request"


class LlmValidationResult(BaseModel):
    status: LlmValidationStatus
    schema_valid: bool
    citations_valid: bool
    source_policy_valid: bool
    safety_valid: bool
    hidden_prompt_absent: bool
    raw_reasoning_absent: bool
    unrestricted_source_text_absent: bool
    validation_errors: list[str] = Field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.status is LlmValidationStatus.valid


class LlmGenerationAttemptMetadata(BaseModel):
    attempt_index: int
    provider_kind: LlmProviderKind
    model_name: str
    model_tier: LlmModelTier
    status: LlmGenerationAttemptStatus
    validation_status: LlmValidationStatus
    repair_attempt: bool = False
    latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None


class LlmFallbackDecision(BaseModel):
    should_fallback: bool
    trigger: LlmFallbackTrigger
    from_model_tier: LlmModelTier | None = None
    to_model: LlmModelDescriptor | None = None
    after_repair_retry: bool = False
    reason: str


class LlmPublicResponseMetadata(BaseModel):
    provider_kind: LlmProviderKind
    live_enabled: bool
    model_name: str
    model_tier: LlmModelTier
    validation_status: LlmValidationStatus
    attempt_count: int
    answer_state: LlmAnswerState
    cached: bool = False
    latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    reasoning_summary: str | None = None


class LlmCacheEligibilityDecision(BaseModel):
    cacheable: bool
    validation_status: LlmValidationStatus
    model_name: str
    model_tier: LlmModelTier
    prompt_version: str
    schema_version: str
    freshness_hash: str | None = None
    input_hash: str | None = None
    attempt_count: int
    rejection_reasons: list[str] = Field(default_factory=list)


class LlmOrchestrationResult(BaseModel):
    request: LlmGenerationRequestMetadata
    runtime: LlmRuntimeConfig
    attempts: list[LlmGenerationAttemptMetadata]
    validation: LlmValidationResult
    fallback_decision: LlmFallbackDecision
    public_metadata: LlmPublicResponseMetadata
    cache_decision: LlmCacheEligibilityDecision
    no_live_external_calls: bool = True


class LlmRuntimeDiagnosticsResponse(BaseModel):
    schema_version: Literal["llm-runtime-contract-v1"] = "llm-runtime-contract-v1"
    runtime: LlmRuntimeConfig
    public_metadata_fields: list[str]
    credential_values_exposed: bool = False
    private_prompt_fields_exposed: bool = False
    model_reasoning_payload_exposed: bool = False
    restricted_source_payload_exposed: bool = False
    no_live_external_calls: bool = True


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
    export_allowed: bool = False
    redistribution_allowed: bool = False
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
    source_use_policy: SourceUsePolicy = SourceUsePolicy.full_text_allowed


class SourceChecksumRecord(BaseModel):
    source_document_id: str
    asset_ticker: str
    checksum: str
    freshness_state: FreshnessState
    cache_allowed: bool
    export_allowed: bool = False
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
    source_use_policy: SourceUsePolicy = SourceUsePolicy.full_text_allowed
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
    model_tier: LlmModelTier | None = None
    validation_status: LlmValidationStatus | None = None
    generation_attempt_count: int | None = None


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
    source_quality: SourceQuality = SourceQuality.fixture
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
    source_use_policy: SourceUsePolicy = SourceUsePolicy.full_text_allowed
    permitted_operations: SourceOperationPermissions = Field(default_factory=lambda: DEFAULT_ALLOWED_SOURCE_OPERATIONS.model_copy())
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


class TrustMetricWorkflowArea(str, Enum):
    search = "search"
    asset_page = "asset_page"
    comparison = "comparison"
    source_drawer = "source_drawer"
    glossary = "glossary"
    export = "export"
    chat = "chat"
    citation = "citation"
    freshness = "freshness"
    generated_output = "generated_output"
    retrieval = "retrieval"
    safety = "safety"


class TrustMetricEventType(str, Enum):
    search_success = "search_success"
    unsupported_asset_outcome = "unsupported_asset_outcome"
    asset_page_view = "asset_page_view"
    comparison_usage = "comparison_usage"
    source_drawer_usage = "source_drawer_usage"
    glossary_usage = "glossary_usage"
    export_usage = "export_usage"
    chat_follow_up = "chat_follow_up"
    chat_answer_outcome = "chat_answer_outcome"
    chat_safety_redirect = "chat_safety_redirect"
    latency_to_first_meaningful_result = "latency_to_first_meaningful_result"
    citation_coverage = "citation_coverage"
    unsupported_claim_drop = "unsupported_claim_drop"
    weak_citation_count = "weak_citation_count"
    generated_output_validation_failure = "generated_output_validation_failure"
    safety_redirect_rate = "safety_redirect_rate"
    freshness_accuracy = "freshness_accuracy"
    source_retrieval_failure = "source_retrieval_failure"
    hallucination_unsupported_fact_incident = "hallucination_unsupported_fact_incident"
    stale_data_incident = "stale_data_incident"


class TrustMetricKind(str, Enum):
    product = "product"
    trust = "trust"


class TrustMetricValidationStatus(str, Enum):
    accepted = "accepted"
    rejected = "rejected"


class TrustMetricAssetSupportState(str, Enum):
    cached_supported = "cached_supported"
    eligible_not_cached = "eligible_not_cached"
    recognized_unsupported = "recognized_unsupported"
    unknown = "unknown"
    unavailable = "unavailable"


class TrustMetricOutputKind(str, Enum):
    asset_page = "asset_page"
    comparison = "comparison"
    chat_answer = "chat_answer"
    export_payload = "export_payload"
    source_list = "source_list"


class TrustMetricSafetyStatus(str, Enum):
    educational = "educational"
    safety_redirect = "safety_redirect"
    unsupported_asset_redirect = "unsupported_asset_redirect"
    insufficient_evidence = "insufficient_evidence"


class TrustMetricGeneratedOutputMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_kind: TrustMetricOutputKind
    prompt_version: str | None = None
    model_name: str | None = None
    schema_valid: bool | None = None
    citation_coverage_rate: float | None = None
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    freshness_hash: str | None = None
    freshness_state: FreshnessState | None = None
    safety_status: TrustMetricSafetyStatus | None = None
    unsupported_claim_count: int = 0
    weak_citation_count: int = 0
    stale_source_count: int = 0
    latency_ms: int | None = None


class TrustMetricEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["trust-metrics-event-v1"] = "trust-metrics-event-v1"
    event_type: TrustMetricEventType
    workflow_area: TrustMetricWorkflowArea
    occurred_at: str = "1970-01-01T00:00:00Z"
    client_event_id: str | None = Field(default=None, max_length=100)
    asset_ticker: str | None = Field(default=None, max_length=12)
    asset_support_state: TrustMetricAssetSupportState | None = None
    comparison_left_ticker: str | None = Field(default=None, max_length=12)
    comparison_right_ticker: str | None = Field(default=None, max_length=12)
    generated_output_available: bool = False
    output_metadata: TrustMetricGeneratedOutputMetadata | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class TrustMetricValidatedEvent(BaseModel):
    validation_status: TrustMetricValidationStatus
    rejection_reasons: list[str] = Field(default_factory=list)
    rejected_field_paths: list[str] = Field(default_factory=list)
    normalized_event: TrustMetricEvent | None = None


class TrustMetricCatalogEvent(BaseModel):
    event_type: TrustMetricEventType
    workflow_area: TrustMetricWorkflowArea
    metric_kind: TrustMetricKind
    description: str
    allowed_metadata_fields: list[str] = Field(default_factory=list)
    allows_generated_output_metadata: bool = False
    requires_freshness_state: bool = False


class TrustMetricCatalogResponse(BaseModel):
    schema_version: Literal["trust-metrics-event-v1"] = "trust-metrics-event-v1"
    product_events: list[TrustMetricCatalogEvent]
    trust_events: list[TrustMetricCatalogEvent]
    forbidden_field_names: list[str]
    deterministic_timestamp_default: str = "1970-01-01T00:00:00Z"
    validation_only: bool = True
    persistence_enabled: bool = False
    external_analytics_enabled: bool = False
    no_live_external_calls: bool = True


class TrustMetricValidationRequest(BaseModel):
    events: list[dict[str, Any]]


class TrustMetricSummary(BaseModel):
    schema_version: Literal["trust-metrics-event-v1"] = "trust-metrics-event-v1"
    accepted_event_count: int
    event_type_counts: dict[str, int] = Field(default_factory=dict)
    workflow_area_counts: dict[str, int] = Field(default_factory=dict)
    product_metric_counts: dict[str, int] = Field(default_factory=dict)
    trust_metric_counts: dict[str, int] = Field(default_factory=dict)
    rates: dict[str, float] = Field(default_factory=dict)
    latency_ms: dict[str, int | float | None] = Field(default_factory=dict)


class TrustMetricValidationResponse(BaseModel):
    schema_version: Literal["trust-metrics-event-v1"] = "trust-metrics-event-v1"
    accepted_count: int
    rejected_count: int
    events: list[TrustMetricValidatedEvent]
    summary: TrustMetricSummary
    validation_only: bool = True
    stored: bool = False
    forwarded: bool = False
    enriched_from_live_services: bool = False


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
    source_quality: SourceQuality = SourceQuality.fixture
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
    source_use_policy: SourceUsePolicy = SourceUsePolicy.full_text_allowed
    permitted_operations: SourceOperationPermissions = Field(default_factory=lambda: DEFAULT_ALLOWED_SOURCE_OPERATIONS.model_copy())


class SourceDrawerState(str, Enum):
    available = "available"
    unsupported = "unsupported"
    out_of_scope = "out_of_scope"
    unknown = "unknown"
    eligible_not_cached = "eligible_not_cached"
    deleted = "deleted"
    stale = "stale"
    partial = "partial"
    unavailable = "unavailable"


class SourceDrawerExcerpt(BaseModel):
    excerpt_id: str
    source_document_id: str
    citation_id: str | None = None
    chunk_id: str | None = None
    text: str | None = None
    source_use_policy: SourceUsePolicy
    allowlist_status: SourceAllowlistStatus
    freshness_state: FreshnessState
    excerpt_allowed: bool
    suppression_reason: str | None = None
    note: str


class SourceDrawerRelatedClaim(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: str
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    section_id: str | None = None
    section_title: str | None = None
    section_type: OverviewSectionType | None = None
    freshness_state: FreshnessState
    evidence_state: EvidenceState
    timely_context: bool = False


class SourceDrawerSectionReference(BaseModel):
    section_id: str
    section_title: str
    section_type: OverviewSectionType
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    freshness_state: FreshnessState
    evidence_state: EvidenceState
    as_of_date: str | None = None
    retrieved_at: str | None = None
    timely_context: bool = False


class SourceDrawerCitationBinding(BaseModel):
    citation_id: str
    source_document_id: str
    asset_ticker: str
    source_type: str
    claim_ids: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    chunk_id: str | None = None
    freshness_state: FreshnessState
    source_use_policy: SourceUsePolicy
    allowlist_status: SourceAllowlistStatus
    excerpt_id: str | None = None
    evidence_layer: Literal["canonical_fact", "source_chunk", "timely_context", "unknown"]
    supports_generated_claim: bool = True


class SourceDrawerSourceGroup(BaseModel):
    group_id: str
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
    source_quality: SourceQuality
    allowlist_status: SourceAllowlistStatus
    source_use_policy: SourceUsePolicy
    permitted_operations: SourceOperationPermissions
    citation_ids: list[str] = Field(default_factory=list)
    related_claim_ids: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    allowed_excerpts: list[SourceDrawerExcerpt] = Field(default_factory=list)
    excerpt_suppression_reasons: list[str] = Field(default_factory=list)


class SourceDrawerDiagnostics(BaseModel):
    no_live_external_calls: bool = True
    generated_output_created: bool = False
    unsupported_generated_output_suppressed: bool = True
    wrong_asset_sources_suppressed: bool = True
    filters_applied: dict[str, str] = Field(default_factory=dict)
    unavailable_reasons: list[str] = Field(default_factory=list)
    omitted_source_document_ids: list[str] = Field(default_factory=list)
    omitted_citation_ids: list[str] = Field(default_factory=list)


class GlossaryResponseState(str, Enum):
    available = "available"
    unsupported = "unsupported"
    out_of_scope = "out_of_scope"
    unknown = "unknown"
    eligible_not_cached = "eligible_not_cached"
    stale = "stale"
    partial = "partial"
    unavailable = "unavailable"
    insufficient_evidence = "insufficient_evidence"


class GlossaryAssetContextState(str, Enum):
    available = "available"
    generic_only = "generic_only"
    unavailable = "unavailable"
    stale = "stale"
    partial = "partial"
    unknown = "unknown"
    suppressed = "suppressed"
    insufficient_evidence = "insufficient_evidence"


class GlossaryEvidenceReferenceType(str, Enum):
    normalized_fact = "normalized_fact"
    source_chunk = "source_chunk"
    recent_development = "recent_development"
    evidence_gap = "evidence_gap"
    section = "section"


class GlossaryTermIdentity(BaseModel):
    term: str
    slug: str
    aliases: list[str] = Field(default_factory=list)
    applies_to: list[AssetType] = Field(default_factory=list)


class GlossaryGenericDefinition(BaseModel):
    simple_definition: str
    why_it_matters: str
    common_beginner_mistake: str
    beginner_category: str
    generic_definition_requires_citation: bool = False


class GlossaryEvidenceReference(BaseModel):
    reference_id: str
    reference_type: GlossaryEvidenceReferenceType
    term_slug: str
    asset_ticker: str
    section_id: str | None = None
    field_name: str | None = None
    fact_id: str | None = None
    source_chunk_id: str | None = None
    recent_event_id: str | None = None
    evidence_gap_id: str | None = None
    source_document_id: str | None = None
    citation_ids: list[str] = Field(default_factory=list)
    evidence_state: EvidenceState
    freshness_state: FreshnessState
    as_of_date: str | None = None
    retrieved_at: str | None = None
    unavailable_reason: str | None = None


class GlossaryCitationBinding(BaseModel):
    binding_id: str
    term_slug: str
    citation_id: str
    source_document_id: str
    asset_ticker: str
    evidence_reference_id: str
    evidence_reference_type: GlossaryEvidenceReferenceType
    freshness_state: FreshnessState
    source_quality: SourceQuality
    allowlist_status: SourceAllowlistStatus
    source_use_policy: SourceUsePolicy
    permitted_operations: SourceOperationPermissions
    supports_asset_specific_context: bool


class GlossarySourceReference(BaseModel):
    source_document_id: str
    asset_ticker: str
    source_type: str
    title: str
    publisher: str
    url: str
    published_at: str | None = None
    as_of_date: str | None = None
    retrieved_at: str
    freshness_state: FreshnessState
    is_official: bool
    source_quality: SourceQuality
    allowlist_status: SourceAllowlistStatus
    source_use_policy: SourceUsePolicy
    permitted_operations: SourceOperationPermissions


class GlossaryAssetContext(BaseModel):
    availability_state: GlossaryAssetContextState
    evidence_state: EvidenceState
    freshness_state: FreshnessState
    context_note: str | None = None
    evidence_reference_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    uncertainty_labels: list[str] = Field(default_factory=list)
    suppression_reasons: list[str] = Field(default_factory=list)


class GlossaryTermResponse(BaseModel):
    term_identity: GlossaryTermIdentity
    generic_definition: GlossaryGenericDefinition
    asset_context: GlossaryAssetContext


class GlossaryDiagnostics(BaseModel):
    no_live_external_calls: bool = True
    live_provider_calls_attempted: bool = False
    live_llm_calls_attempted: bool = False
    no_new_generated_output: bool = True
    no_frontend_change_required: bool = True
    generic_definitions_are_not_evidence: bool = True
    source_policy_enforced: bool = True
    same_asset_evidence_only: bool = True
    restricted_text_exposed: bool = False
    filters_applied: dict[str, str] = Field(default_factory=dict)
    unavailable_reasons: list[str] = Field(default_factory=list)
    omitted_term_slugs: list[str] = Field(default_factory=list)


class GlossaryResponse(BaseModel):
    schema_version: Literal["glossary-asset-context-v1"] = "glossary-asset-context-v1"
    selected_asset: AssetIdentity
    state: StateMessage
    glossary_state: GlossaryResponseState
    terms: list[GlossaryTermResponse] = Field(default_factory=list)
    evidence_references: list[GlossaryEvidenceReference] = Field(default_factory=list)
    citation_bindings: list[GlossaryCitationBinding] = Field(default_factory=list)
    source_references: list[GlossarySourceReference] = Field(default_factory=list)
    diagnostics: GlossaryDiagnostics = Field(default_factory=GlossaryDiagnostics)


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


class WeeklyNewsPeriodBucket(str, Enum):
    previous_market_week = "previous_market_week"
    current_week_to_date = "current_week_to_date"


class WeeklyNewsEventType(str, Enum):
    earnings = "earnings"
    guidance = "guidance"
    product_announcement = "product_announcement"
    merger_acquisition = "merger_acquisition"
    leadership_change = "leadership_change"
    regulatory_event = "regulatory_event"
    legal_event = "legal_event"
    capital_allocation = "capital_allocation"
    fee_change = "fee_change"
    methodology_change = "methodology_change"
    index_change = "index_change"
    fund_merger = "fund_merger"
    fund_liquidation = "fund_liquidation"
    sponsor_update = "sponsor_update"
    large_flow_event = "large_flow_event"
    no_major_recent_development = "no_major_recent_development"
    other = "other"


class WeeklyNewsContractState(str, Enum):
    available = "available"
    no_high_signal = "no_high_signal"
    insufficient_evidence = "insufficient_evidence"
    unavailable = "unavailable"
    suppressed = "suppressed"


class MarketWeekPeriod(BaseModel):
    start: str | None = None
    end: str | None = None


class WeeklyNewsWindow(BaseModel):
    as_of_date: str
    timezone: Literal["America/New_York"] = "America/New_York"
    previous_market_week: MarketWeekPeriod
    current_week_to_date: MarketWeekPeriod
    news_window_start: str
    news_window_end: str
    includes_current_week_to_date: bool


class WeeklyNewsDeduplicationMetadata(BaseModel):
    canonical_event_key: str
    duplicate_group_id: str | None = None
    duplicate_of_event_id: str | None = None
    is_duplicate: bool = False


class WeeklyNewsSelectionRationale(BaseModel):
    source_priority: int
    source_quality_weight: int
    event_type_weight: int
    recency_weight: int
    asset_relevance_weight: int
    duplicate_penalty: int
    total_score: int
    minimum_display_score: int
    selected: bool
    exclusion_reasons: list[str] = Field(default_factory=list)


class WeeklyNewsSourceMetadata(BaseModel):
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
    source_quality: SourceQuality
    allowlist_status: SourceAllowlistStatus
    source_use_policy: SourceUsePolicy


class WeeklyNewsItem(BaseModel):
    event_id: str
    asset_ticker: str
    event_type: WeeklyNewsEventType
    title: str
    summary: str
    event_date: str | None = None
    published_at: str | None = None
    period_bucket: WeeklyNewsPeriodBucket
    citation_ids: list[str]
    source: WeeklyNewsSourceMetadata
    freshness_state: FreshnessState
    importance_score: int
    deduplication: WeeklyNewsDeduplicationMetadata
    selection_rationale: WeeklyNewsSelectionRationale


class WeeklyNewsEmptyState(BaseModel):
    state: WeeklyNewsContractState
    message: str
    evidence_state: EvidenceState
    selected_item_count: int = 0
    suppressed_candidate_count: int = 0


class WeeklyNewsFocusResponse(BaseModel):
    schema_version: Literal["weekly-news-focus-v1"] = "weekly-news-focus-v1"
    asset: AssetIdentity
    state: WeeklyNewsContractState
    window: WeeklyNewsWindow
    items: list[WeeklyNewsItem] = Field(default_factory=list)
    empty_state: WeeklyNewsEmptyState | None = None
    citations: list[Citation] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    no_live_external_calls: bool = True
    stable_facts_are_separate: bool = True


class AIComprehensiveAnalysisSection(BaseModel):
    section_id: Literal[
        "what_changed_this_week",
        "market_context",
        "business_or_fund_context",
        "risk_context",
    ]
    label: Literal[
        "What Changed This Week",
        "Market Context",
        "Business/Fund Context",
        "Risk Context",
    ]
    analysis: str
    bullets: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)


class AIComprehensiveAnalysisResponse(BaseModel):
    schema_version: Literal["ai-comprehensive-analysis-v1"] = "ai-comprehensive-analysis-v1"
    asset: AssetIdentity
    state: WeeklyNewsContractState
    analysis_available: bool
    suppression_reason: str | None = None
    sections: list[AIComprehensiveAnalysisSection] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    weekly_news_event_ids: list[str] = Field(default_factory=list)
    canonical_fact_citation_ids: list[str] = Field(default_factory=list)
    no_live_external_calls: bool = True
    stable_facts_are_separate: bool = True


class WeeklyNewsResponse(BaseModel):
    asset: AssetIdentity
    state: StateMessage
    weekly_news_focus: WeeklyNewsFocusResponse
    ai_comprehensive_analysis: AIComprehensiveAnalysisResponse


class SuitabilitySummary(BaseModel):
    may_fit: str
    may_not_fit: str
    learn_next: str


class Claim(BaseModel):
    claim_id: str
    claim_text: str
    citation_ids: list[str]


class OverviewSectionFreshnessValidationOutcome(str, Enum):
    validated = "validated"
    validated_with_limitations = "validated_with_limitations"
    mismatch = "mismatch"


class OverviewSectionFreshnessCitationBinding(BaseModel):
    citation_id: str
    source_document_id: str
    asset_ticker: str
    freshness_state: FreshnessState
    evidence_state: EvidenceState | None = None


class OverviewSectionFreshnessSourceBinding(BaseModel):
    source_document_id: str
    asset_ticker: str
    source_type: str
    freshness_state: FreshnessState
    as_of_date: str | None = None
    retrieved_at: str | None = None


class OverviewSectionFreshnessDiagnostics(BaseModel):
    derived_from_existing_local_evidence_only: bool = True
    used_knowledge_pack_freshness_inputs: bool = True
    no_live_external_calls: bool = True
    same_asset_citation_bindings_only: bool = True
    same_asset_source_bindings_only: bool = True
    matched_knowledge_pack_section_ids: list[str] = Field(default_factory=list)
    missing_citation_ids: list[str] = Field(default_factory=list)
    missing_source_document_ids: list[str] = Field(default_factory=list)
    mismatch_reasons: list[str] = Field(default_factory=list)


class OverviewSectionFreshnessValidation(BaseModel):
    schema_version: Literal["overview-section-freshness-validation-v1"] = "overview-section-freshness-validation-v1"
    section_id: str
    section_type: OverviewSectionType
    displayed_freshness_state: FreshnessState
    displayed_evidence_state: EvidenceState
    displayed_as_of_date: str | None = None
    displayed_retrieved_at: str | None = None
    validated_freshness_state: FreshnessState
    validated_as_of_date: str | None = None
    validated_retrieved_at: str | None = None
    validation_outcome: OverviewSectionFreshnessValidationOutcome
    limitation_message: str | None = None
    mismatch_message: str | None = None
    citation_bindings: list[OverviewSectionFreshnessCitationBinding] = Field(default_factory=list)
    source_bindings: list[OverviewSectionFreshnessSourceBinding] = Field(default_factory=list)
    knowledge_pack_freshness_inputs: list[SectionFreshnessInput] = Field(default_factory=list)
    diagnostics: OverviewSectionFreshnessDiagnostics = Field(default_factory=OverviewSectionFreshnessDiagnostics)


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
    weekly_news_focus: WeeklyNewsFocusResponse | None = None
    ai_comprehensive_analysis: AIComprehensiveAnalysisResponse | None = None
    suitability_summary: SuitabilitySummary | None = None
    claims: list[Claim] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    sections: list[OverviewSection] = Field(default_factory=list)
    section_freshness_validation: list[OverviewSectionFreshnessValidation] = Field(default_factory=list)


class DetailsResponse(BaseModel):
    asset: AssetIdentity
    state: StateMessage
    freshness: Freshness
    facts: dict[str, MetricValue | str | int | float | list[Any] | None]
    citations: list[Citation] = Field(default_factory=list)


class SourcesResponse(BaseModel):
    schema_version: str = "asset-source-drawer-v1"
    asset: AssetIdentity
    state: StateMessage
    sources: list[SourceDocument] = Field(default_factory=list)
    selected_asset: AssetIdentity | None = None
    drawer_state: SourceDrawerState = SourceDrawerState.unavailable
    source_groups: list[SourceDrawerSourceGroup] = Field(default_factory=list)
    citation_bindings: list[SourceDrawerCitationBinding] = Field(default_factory=list)
    related_claims: list[SourceDrawerRelatedClaim] = Field(default_factory=list)
    section_references: list[SourceDrawerSectionReference] = Field(default_factory=list)
    diagnostics: SourceDrawerDiagnostics = Field(default_factory=SourceDrawerDiagnostics)


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


class ComparisonEvidenceAvailabilityState(str, Enum):
    available = "available"
    unsupported = "unsupported"
    out_of_scope = "out_of_scope"
    unknown = "unknown"
    eligible_not_cached = "eligible_not_cached"
    no_local_pack = "no_local_pack"
    stale = "stale"
    partial = "partial"
    unavailable = "unavailable"
    insufficient_evidence = "insufficient_evidence"


class ComparisonEvidenceSide(str, Enum):
    left = "left"
    right = "right"
    shared = "shared"


class ComparisonEvidenceSideRole(str, Enum):
    left_side_support = "left_side_support"
    right_side_support = "right_side_support"
    shared_comparison_support = "shared_comparison_support"


class ComparisonEvidenceDiagnostics(BaseModel):
    no_live_external_calls: bool = True
    live_provider_calls_attempted: bool = False
    live_llm_calls_attempted: bool = False
    availability_contract_created_generated_output: bool = False
    no_new_generated_output: bool = True
    generated_comparison_available: bool = False
    source_policy_enforced: bool = True
    same_comparison_pack_sources_only: bool = True
    unavailable_reasons: list[str] = Field(default_factory=list)
    empty_state_reason: str | None = None


class ComparisonEvidenceSourceReference(BaseModel):
    source_document_id: str
    asset_ticker: str
    source_type: str
    title: str
    publisher: str
    url: str
    published_at: str | None = None
    as_of_date: str | None = None
    retrieved_at: str
    freshness_state: FreshnessState
    is_official: bool
    source_quality: SourceQuality
    allowlist_status: SourceAllowlistStatus
    source_use_policy: SourceUsePolicy
    permitted_operations: SourceOperationPermissions


class ComparisonEvidenceItem(BaseModel):
    evidence_item_id: str
    dimension: str
    side: ComparisonEvidenceSide
    side_role: ComparisonEvidenceSideRole
    asset_ticker: str
    field_name: str | None = None
    fact_id: str | None = None
    source_chunk_id: str | None = None
    source_document_id: str | None = None
    citation_ids: list[str] = Field(default_factory=list)
    evidence_state: EvidenceState
    freshness_state: FreshnessState
    as_of_date: str | None = None
    retrieved_at: str | None = None
    is_official: bool = False
    source_quality: SourceQuality = SourceQuality.unknown
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.not_allowlisted
    source_use_policy: SourceUsePolicy = SourceUsePolicy.rejected
    permitted_operations: SourceOperationPermissions = Field(default_factory=lambda: DEFAULT_BLOCKED_SOURCE_OPERATIONS.model_copy())
    unavailable_reason: str | None = None


class ComparisonEvidenceDimension(BaseModel):
    dimension: str
    required: bool = True
    availability_state: ComparisonEvidenceAvailabilityState
    evidence_state: EvidenceState
    freshness_state: FreshnessState
    left_evidence_item_ids: list[str] = Field(default_factory=list)
    right_evidence_item_ids: list[str] = Field(default_factory=list)
    shared_evidence_item_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    generated_claim_ids: list[str] = Field(default_factory=list)
    unavailable_reason: str | None = None


class ComparisonEvidenceCitationBinding(BaseModel):
    binding_id: str
    claim_id: str
    dimension: str
    citation_id: str
    source_document_id: str
    asset_ticker: str
    side_role: ComparisonEvidenceSideRole
    freshness_state: FreshnessState
    source_quality: SourceQuality
    allowlist_status: SourceAllowlistStatus
    source_use_policy: SourceUsePolicy
    permitted_operations: SourceOperationPermissions
    supports_generated_claim: bool


class ComparisonEvidenceClaimBinding(BaseModel):
    claim_id: str
    claim_kind: Literal["key_difference", "beginner_bottom_line"]
    dimension: str
    side_role: ComparisonEvidenceSideRole
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    evidence_item_ids: list[str] = Field(default_factory=list)
    availability_state: ComparisonEvidenceAvailabilityState


class ComparisonEvidenceAvailability(BaseModel):
    schema_version: Literal["comparison-evidence-availability-v1"] = "comparison-evidence-availability-v1"
    comparison_id: str
    comparison_type: str
    left_asset: AssetIdentity
    right_asset: AssetIdentity
    availability_state: ComparisonEvidenceAvailabilityState
    required_dimensions: list[str] = Field(default_factory=list)
    required_evidence_dimensions: list[ComparisonEvidenceDimension] = Field(default_factory=list)
    evidence_items: list[ComparisonEvidenceItem] = Field(default_factory=list)
    claim_bindings: list[ComparisonEvidenceClaimBinding] = Field(default_factory=list)
    citation_bindings: list[ComparisonEvidenceCitationBinding] = Field(default_factory=list)
    source_references: list[ComparisonEvidenceSourceReference] = Field(default_factory=list)
    diagnostics: ComparisonEvidenceDiagnostics = Field(default_factory=ComparisonEvidenceDiagnostics)


class CompareResponse(BaseModel):
    left_asset: AssetIdentity
    right_asset: AssetIdentity
    state: StateMessage
    comparison_type: str
    key_differences: list[KeyDifference] = Field(default_factory=list)
    bottom_line_for_beginners: BeginnerBottomLine | None = None
    citations: list[Citation] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    evidence_availability: ComparisonEvidenceAvailability | None = None


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
    source_quality: SourceQuality = SourceQuality.fixture
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
    source_use_policy: SourceUsePolicy = SourceUsePolicy.full_text_allowed
    permitted_operations: SourceOperationPermissions = Field(default_factory=lambda: DEFAULT_ALLOWED_SOURCE_OPERATIONS.model_copy())


class ChatTurnRecord(BaseModel):
    turn_id: str
    submitted_at: str
    selected_ticker: str
    safety_classification: SafetyClassification
    evidence_state: EvidenceState
    freshness_state: FreshnessState
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    uncertainty_labels: list[str] = Field(default_factory=list)
    direct_answer: str
    why_it_matters: str
    citations: list[ChatCitation] = Field(default_factory=list)
    source_documents: list[ChatSourceDocument] = Field(default_factory=list)


class ChatSessionTurnSummary(BaseModel):
    turn_id: str
    submitted_at: str
    selected_ticker: str
    safety_classification: SafetyClassification
    evidence_state: EvidenceState
    freshness_state: FreshnessState
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    uncertainty_labels: list[str] = Field(default_factory=list)


class ChatSessionPublicMetadata(BaseModel):
    schema_version: str = "chat-session-contract-v1"
    session_id: str | None = None
    conversation_id: str | None = None
    lifecycle_state: ChatSessionLifecycleState
    selected_asset: AssetIdentity | None = None
    created_at: str | None = None
    last_activity_at: str | None = None
    expires_at: str | None = None
    deleted_at: str | None = None
    turn_count: int = 0
    latest_safety_classification: SafetyClassification | None = None
    latest_evidence_state: EvidenceState | None = None
    latest_freshness_state: FreshnessState | None = None
    export_available: bool = False
    deletion_status: ChatSessionDeletionStatus = ChatSessionDeletionStatus.unavailable


class ChatSessionStatusResponse(BaseModel):
    session: ChatSessionPublicMetadata
    turn_summaries: list[ChatSessionTurnSummary] = Field(default_factory=list)
    message: str


class ChatSessionDeleteResponse(BaseModel):
    session: ChatSessionPublicMetadata
    deleted: bool
    message: str


class ChatResponse(BaseModel):
    asset: AssetIdentity
    direct_answer: str
    why_it_matters: str
    citations: list[ChatCitation] = Field(default_factory=list)
    source_documents: list[ChatSourceDocument] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    safety_classification: SafetyClassification
    session: ChatSessionPublicMetadata | None = None


class ExportExcerpt(BaseModel):
    excerpt_id: str
    kind: Literal["supporting_passage", "excerpt_metadata"] = "supporting_passage"
    text: str | None = None
    citation_id: str | None = None
    chunk_id: str | None = None
    redistribution_allowed: bool = True
    source_use_policy: SourceUsePolicy = SourceUsePolicy.full_text_allowed
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
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
    source_quality: SourceQuality = SourceQuality.fixture
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
    source_use_policy: SourceUsePolicy = SourceUsePolicy.full_text_allowed
    permitted_operations: SourceOperationPermissions = Field(default_factory=lambda: DEFAULT_ALLOWED_SOURCE_OPERATIONS.model_copy())
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
