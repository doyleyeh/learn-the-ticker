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


class Freshness(BaseModel):
    page_last_updated_at: str
    facts_as_of: str | None = None
    holdings_as_of: str | None = None
    recent_events_as_of: str | None = None
    freshness_state: FreshnessState


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
