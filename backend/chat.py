from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable, Protocol

from backend.cache import (
    build_generated_output_freshness_input,
    build_knowledge_pack_freshness_input,
    compute_generated_output_freshness_hash,
    compute_knowledge_pack_freshness_hash,
)
from backend.citations import (
    CitationEvidence,
    CitationValidationClaim,
    CitationValidationContext,
    CitationValidationIssue,
    CitationValidationReport,
    CitationValidationResult,
    CitationValidationStatus,
    EvidenceKind,
    validate_claims,
)
from backend.comparison import generate_comparison
from backend.generated_output_cache_repository import (
    GeneratedOutputArtifactCategory,
    GeneratedOutputCacheContractError,
    GeneratedOutputCacheRepositoryRecords,
    build_deterministic_generated_output_cache_records,
    persist_generated_output_cache_records,
    validate_generated_output_cache_records,
)
from backend.generation_evidence import evidence_pack_from_citation_evidence
from backend.models import (
    AssetIdentity,
    AssetStatus,
    AssetType,
    CacheEntryKind,
    CacheScope,
    ChatCitation,
    ChatCompareRouteSuggestion,
    ChatResponse,
    EvidenceState,
    Freshness,
    ChatSourceDocument,
    FreshnessState,
    LightweightFetchFact,
    LightweightFetchResponse,
    LightweightFetchSource,
    SafetyClassification,
    SectionFreshnessInput,
    SourceExportRights,
    SourceParserStatus,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
)
from backend.retrieval import (
    AssetKnowledgePack,
    RetrievedFact,
    RetrievedRecentDevelopment,
    RetrievedSourceChunk,
    EvidenceGap,
    NormalizedFactFixture,
    RecentDevelopmentFixture,
    SourceChunkFixture,
    SourceDocumentFixture,
    build_asset_knowledge_pack,
)
from backend.repositories.knowledge_packs import KnowledgePackRepositoryContractError, KnowledgePackRepositoryRecords
from backend.retrieval_repository import KnowledgePackRecordReader, read_persisted_knowledge_pack_response
from backend.safety import classify_question, educational_redirect, find_forbidden_output_phrases
from backend.search import search_assets
from backend.source_policy import resolve_source_policy
from backend.summary_generation import (
    SummaryGenerationContractError,
    SummaryGenerationService,
    build_default_summary_generation_service,
)
from backend.weekly_news_sources import LIGHTWEIGHT_WEEKLY_NEWS_FACT_FIELD


class ChatGenerationError(ValueError):
    """Raised when deterministic chat generation violates project contracts."""


CHAT_PERSISTED_READ_BOUNDARY = "chat-persisted-read-boundary-v1"


class GeneratedOutputChatCacheRecordReader(Protocol):
    def read_chat_answer_records(self, ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        ...


@dataclass(frozen=True)
class PersistedChatReadResult:
    status: str
    ticker: str
    chat_response: ChatResponse | None = None
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def found(self) -> bool:
        return self.status == "found" and self.chat_response is not None


@dataclass(frozen=True)
class ChatCitationBinding:
    citation: ChatCitation
    source_document: ChatSourceDocument
    evidence: CitationEvidence


@dataclass(frozen=True)
class PlannedChatClaim:
    claim_id: str
    claim_text: str
    citation_ids: list[str]
    claim_type: str = "factual"
    freshness_label: FreshnessState | None = None


@dataclass(frozen=True)
class _ChatPlan:
    direct_answer: str
    why_it_matters: str
    planned_claims: list[PlannedChatClaim]
    uncertainty: list[str]


COMPARISON_INTENT_PATTERNS = (
    r"\bcompare\b",
    r"\bcompared\b",
    r"\bcomparison\b",
    r"\bvs\.?\b",
    r"\bversus\b",
    r"\bdifferent\b",
    r"\bdifference\b",
    r"\binstead of\b",
    r"\bthan\b",
)
TICKER_TOKEN_PATTERN = re.compile(r"\b[A-Za-z]{1,5}(?:\.[A-Za-z])?\b")
COMPARISON_CONNECTOR_TOKENS = frozenset({"AND", "VS", "VERSUS", "WITH"})


def generate_asset_chat(
    ticker: str,
    question: str,
    *,
    persisted_pack_reader: KnowledgePackRecordReader | Any | None = None,
    generated_output_cache_reader: GeneratedOutputChatCacheRecordReader | Any | None = None,
    generated_output_cache_writer: Any | None = None,
) -> ChatResponse:
    """Build a ChatResponse-compatible payload from a selected asset knowledge pack."""

    fixture_pack = build_asset_knowledge_pack(ticker)
    safety_classification = classify_question(question, supported=fixture_pack.asset.supported)
    if safety_classification is SafetyClassification.personalized_advice_redirect:
        return generate_chat_from_pack(fixture_pack, question)

    compare_route_redirect = _compare_route_redirect(fixture_pack, question)
    if compare_route_redirect is not None:
        return compare_route_redirect

    persisted = read_persisted_chat_response(
        ticker,
        question,
        persisted_pack_reader=persisted_pack_reader,
        generated_output_cache_reader=generated_output_cache_reader,
    )
    if persisted.found and persisted.chat_response is not None:
        return persisted.chat_response

    lightweight_response = generate_lightweight_asset_chat_if_available(ticker, question)
    if lightweight_response is not None:
        return lightweight_response

    if safety_classification is SafetyClassification.unsupported_asset_redirect:
        return generate_chat_from_pack(fixture_pack, question)

    response = generate_chat_from_pack(fixture_pack, question)
    _maybe_write_chat_generated_output_cache(response, fixture_pack, generated_output_cache_writer)
    return response


def generate_lightweight_asset_chat_if_available(ticker: str, question: str) -> ChatResponse | None:
    """Generate chat from already-renderable lightweight page evidence without persistence or cache writes."""

    from backend.lightweight_page import fetch_lightweight_page_data_if_enabled

    response = fetch_lightweight_page_data_if_enabled(ticker)
    if response is None:
        return None

    try:
        pack = build_lightweight_chat_knowledge_pack(response)
        chat = generate_chat_from_pack(pack, question)
        if chat.safety_classification is SafetyClassification.educational:
            report = validate_chat_response(chat, pack)
            if not report.valid:
                return _lightweight_insufficient_chat(pack, question, "Lightweight chat citation validation failed.")
        return chat
    except (ChatGenerationError, LookupError, StopIteration, ValueError, TypeError):
        fallback_asset = response.asset.model_copy(update={"status": AssetStatus.supported, "supported": True})
        pack = AssetKnowledgePack(
            asset=fallback_asset,
            freshness=response.freshness,
            evidence_gaps=_lightweight_evidence_gaps(response),
        )
        return _lightweight_insufficient_chat(
            pack,
            question,
            "Lightweight normalized evidence was renderable for the page but insufficient for this chat answer.",
        )


def build_lightweight_chat_knowledge_pack(response: LightweightFetchResponse) -> AssetKnowledgePack:
    """Shape renderable lightweight page evidence into the existing in-memory chat pack contract."""

    if (
        not response.generated_output_eligible
        or not response.asset.supported
        or response.fetch_state.value not in {"supported", "partial"}
        or not response.sources
        or not response.facts
        or response.raw_payload_exposed
    ):
        raise ChatGenerationError("Lightweight response is not eligible for grounded chat.")

    source_fixtures = [_lightweight_source_fixture(source, response.asset.ticker) for source in response.sources]
    source_by_id = {source.source_document_id: source for source in source_fixtures}
    chunks: list[RetrievedSourceChunk] = []
    facts: list[RetrievedFact] = []
    recent_developments: list[RetrievedRecentDevelopment] = []

    for fact in _lightweight_chat_facts(response):
        source = _preferred_lightweight_fact_source(fact, response.sources)
        if source is None:
            continue
        source_fixture = source_by_id[source.source_document_id]
        chunk = _lightweight_fact_chunk(fact, response, source)
        chunks.append(RetrievedSourceChunk(chunk=chunk, source_document=source_fixture))
        if fact.field_name == LIGHTWEIGHT_WEEKLY_NEWS_FACT_FIELD and isinstance(fact.value, dict):
            recent = _lightweight_recent_development(fact, response, source, chunk)
            if recent is not None:
                recent_developments.append(
                    RetrievedRecentDevelopment(
                        recent_development=recent,
                        source_document=source_fixture,
                        source_chunk=chunk,
                    )
                )
        facts.append(
            RetrievedFact(
                fact=NormalizedFactFixture(
                    fact_id=fact.fact_id,
                    asset_ticker=response.asset.ticker,
                    fact_type="lightweight_normalized_fact",
                    field_name=fact.field_name,
                    value=fact.value,
                    unit=_lightweight_fact_unit(fact),
                    period=None,
                    as_of_date=fact.as_of_date,
                    source_document_id=source.source_document_id,
                    source_chunk_id=chunk.chunk_id,
                    extraction_method="lightweight_fresh_data_normalized_fact",
                    confidence=0.8 if fact.evidence_state is EvidenceState.supported else 0.55,
                    freshness_state=fact.freshness_state,
                    evidence_state=fact.evidence_state.value,
                ),
                source_document=source_fixture,
                source_chunk=chunk,
            )
        )

    return AssetKnowledgePack(
        asset=response.asset.model_copy(update={"status": AssetStatus.supported, "supported": True}),
        freshness=response.freshness,
        source_documents=source_fixtures,
        normalized_facts=facts,
        source_chunks=chunks,
        recent_developments=recent_developments,
        evidence_gaps=_lightweight_evidence_gaps(response),
    )


def _lightweight_source_fixture(source: LightweightFetchSource, ticker: str) -> SourceDocumentFixture:
    return SourceDocumentFixture(
        source_document_id=source.source_document_id,
        asset_ticker=ticker,
        source_type=_lightweight_chat_source_type(source),
        source_rank=_lightweight_source_rank(source),
        title=source.title,
        publisher=source.publisher,
        url=source.url or "",
        published_at=source.published_at,
        retrieved_at=source.retrieved_at,
        content_type="normalized_metadata",
        is_official=source.is_official,
        freshness_state=source.freshness_state,
        as_of_date=source.as_of_date,
        source_quality=source.source_quality,
        allowlist_status=source.allowlist_status,
        source_use_policy=source.source_use_policy,
    )


def _lightweight_chat_source_type(source: LightweightFetchSource) -> str:
    if source.source_type in {"sec_company_tickers_exchange", "sec_submissions", "sec_companyfacts"}:
        return "sec_filing"
    if source.source_type == "yahoo_finance_weekly_news_metadata":
        return "recent_development"
    if source.source_type == "provider_market_reference":
        return "structured_market_data"
    return source.source_type


def _lightweight_source_rank(source: LightweightFetchSource) -> int:
    if source.is_official:
        return 1
    if source.source_use_policy is SourceUsePolicy.summary_allowed:
        return 20
    return 50


def _lightweight_chat_facts(response: LightweightFetchResponse) -> list[LightweightFetchFact]:
    facts = list(response.facts)
    canonical = _canonical_lightweight_identity_fact(response)
    if canonical is not None:
        facts.insert(0, canonical)

    if response.asset.asset_type is AssetType.stock:
        primary_business = _stock_primary_business_fact(response)
        if primary_business is not None:
            facts.append(primary_business)
    elif response.asset.asset_type is AssetType.etf:
        beginner_role = _etf_beginner_role_fact(response)
        if beginner_role is not None:
            facts.append(beginner_role)

    return facts


def _canonical_lightweight_identity_fact(response: LightweightFetchResponse) -> LightweightFetchFact | None:
    for field_name in ("sec_identity", "etf_identity", "etf_fact_sheet_metadata", "provider_identity_or_market_reference"):
        fact = _lightweight_fact_by_field(response, field_name)
        source_ids = _generated_claim_source_ids(fact, response.sources) if fact is not None else []
        if fact is not None and source_ids:
            return LightweightFetchFact(
                fact_id=f"lw_chat_{response.asset.ticker.lower()}_canonical_identity",
                field_name="canonical_asset_identity",
                value={
                    "ticker": response.asset.ticker,
                    "name": response.asset.name,
                    "asset_type": response.asset.asset_type.value,
                    "exchange": response.asset.exchange,
                    "issuer": response.asset.issuer,
                    "source_label": "lightweight_fresh_data",
                },
                evidence_state=EvidenceState.supported,
                freshness_state=fact.freshness_state,
                as_of_date=fact.as_of_date,
                retrieved_at=fact.retrieved_at,
                source_document_ids=source_ids,
                source_labels=fact.source_labels,
                fallback_used=fact.fallback_used,
                limitations=fact.limitations,
            )
    return None


def _stock_primary_business_fact(response: LightweightFetchResponse) -> LightweightFetchFact | None:
    profile = _lightweight_fact_by_field(response, "provider_profile_overview")
    source_ids = _generated_claim_source_ids(profile, response.sources) if profile is not None else []
    if profile is None or not source_ids or not isinstance(profile.value, dict):
        return None
    sector = profile.value.get("sector")
    industry = profile.value.get("industry")
    business_summary = (
        profile.value.get("business_summary")
        or profile.value.get("long_business_summary")
        or profile.value.get("longBusinessSummary")
    )
    parts: list[str] = []
    if sector and industry:
        parts.append(f"sector: {sector}; industry: {industry}")
    elif sector:
        parts.append(f"sector: {sector}")
    elif industry:
        parts.append(f"industry: {industry}")
    if business_summary:
        parts.append(f"business summary: {_short_chat_value(business_summary)}")
    if not parts:
        return None
    return LightweightFetchFact(
        fact_id=f"lw_chat_{response.asset.ticker.lower()}_primary_business",
        field_name="primary_business",
        value="; ".join(parts),
        evidence_state=EvidenceState.supported,
        freshness_state=profile.freshness_state,
        as_of_date=profile.as_of_date,
        retrieved_at=profile.retrieved_at,
        source_document_ids=source_ids,
        source_labels=profile.source_labels,
        fallback_used=True,
        limitations=profile.limitations,
    )


def _etf_beginner_role_fact(response: LightweightFetchResponse) -> LightweightFetchFact | None:
    benchmark = _lightweight_fact_by_field(response, "benchmark")
    holdings = _lightweight_fact_by_field(response, "holdings_count")
    source_fact = benchmark or holdings or _lightweight_fact_by_field(response, "etf_identity")
    source_ids = _generated_claim_source_ids(source_fact, response.sources) if source_fact is not None else []
    if source_fact is None or not source_ids:
        return None
    benchmark_text = f" tracking {benchmark.value}" if benchmark is not None and benchmark.value else ""
    holdings_text = f" with about {holdings.value} holdings" if holdings is not None and holdings.value else ""
    return LightweightFetchFact(
        fact_id=f"lw_chat_{response.asset.ticker.lower()}_beginner_role",
        field_name="beginner_role",
        value=f"a U.S.-listed ETF{benchmark_text}{holdings_text}",
        evidence_state=EvidenceState.supported,
        freshness_state=source_fact.freshness_state,
        as_of_date=source_fact.as_of_date,
        retrieved_at=source_fact.retrieved_at,
        source_document_ids=source_ids,
        source_labels=source_fact.source_labels,
        fallback_used=source_fact.fallback_used,
        limitations=source_fact.limitations,
    )


def _lightweight_fact_by_field(response: LightweightFetchResponse, field_name: str) -> LightweightFetchFact | None:
    return next((fact for fact in response.facts if fact.field_name == field_name), None)


def _preferred_lightweight_fact_source(
    fact: LightweightFetchFact,
    sources: list[LightweightFetchSource],
) -> LightweightFetchSource | None:
    source_by_id = {source.source_document_id: source for source in sources}
    candidates = [source_by_id[source_id] for source_id in fact.source_document_ids if source_id in source_by_id]
    eligible = [source for source in candidates if _lightweight_source_can_support_chat(source)]
    if not eligible:
        return None
    return sorted(eligible, key=_lightweight_source_rank)[0]


def _generated_claim_source_ids(
    fact: LightweightFetchFact | None,
    sources: list[LightweightFetchSource],
) -> list[str]:
    if fact is None:
        return []
    source_by_id = {source.source_document_id: source for source in sources}
    return [
        source_id
        for source_id in fact.source_document_ids
        if source_id in source_by_id and _lightweight_source_can_support_chat(source_by_id[source_id])
    ]


def _lightweight_source_can_support_chat(source: LightweightFetchSource) -> bool:
    return (
        source.allowlist_status.value == "allowed"
        and source.source_use_policy not in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only, SourceUsePolicy.rejected}
        and source.freshness_state not in {FreshnessState.unavailable, FreshnessState.unknown}
        and not source.raw_payload_exposed
    )


def _lightweight_fact_chunk(
    fact: LightweightFetchFact,
    response: LightweightFetchResponse,
    source: LightweightFetchSource,
) -> SourceChunkFixture:
    text = _lightweight_supporting_text(fact, response, source)
    return SourceChunkFixture(
        chunk_id=f"chk_{fact.fact_id}",
        asset_ticker=response.asset.ticker,
        source_document_id=source.source_document_id,
        section_name=f"lightweight_{fact.field_name}",
        chunk_order=0,
        text=text,
        token_count=max(1, len(text.split())),
        char_start=0,
        char_end=len(text),
        supported_claim_types=_lightweight_supported_claim_types(fact),
    )


def _lightweight_supporting_text(
    fact: LightweightFetchFact,
    response: LightweightFetchResponse,
    source: LightweightFetchSource,
) -> str:
    value = fact.value
    if isinstance(value, dict):
        value_text = ", ".join(f"{key}: {_short_chat_value(item)}" for key, item in sorted(value.items())[:8])
    elif isinstance(value, list):
        value_text = "; ".join(_short_chat_value(item) for item in value[:5])
    else:
        value_text = _short_chat_value(value)
    labels = ", ".join(label.value for label in fact.source_labels) or source.source_label.value
    limitations = f" Limitations: {fact.limitations}" if fact.limitations else ""
    return (
        f"{response.asset.ticker} lightweight normalized fact {fact.field_name}: {value_text}. "
        f"Source label: {labels}; source-use policy: {source.source_use_policy.value}; "
        f"as of: {fact.as_of_date or source.as_of_date or 'unknown'}; retrieved at: {fact.retrieved_at or source.retrieved_at}."
        f"{limitations}"
    )


def _short_chat_value(value: Any) -> str:
    text = str(value)
    return text if len(text) <= 240 else f"{text[:237]}..."


def _lightweight_supported_claim_types(fact: LightweightFetchFact) -> list[str]:
    field = fact.field_name
    if field == LIGHTWEIGHT_WEEKLY_NEWS_FACT_FIELD:
        return ["recent", "factual", "interpretation"]
    if field in {"canonical_asset_identity", "sec_identity", "etf_identity", "benchmark", "expense_ratio", "holdings_count"}:
        return ["factual", "interpretation"]
    if field == "primary_business":
        return ["factual", "risk", "suitability", "interpretation"]
    if field == "beginner_role":
        return ["interpretation", "suitability", "factual"]
    if field in {"latest_sec_filing", "latest_revenue_fact", "latest_net_income_fact", "latest_assets_fact"}:
        return ["factual", "risk", "interpretation"]
    if field.startswith("provider_"):
        return ["factual", "interpretation"]
    return ["factual", "interpretation", "risk"]


def _lightweight_recent_development(
    fact: LightweightFetchFact,
    response: LightweightFetchResponse,
    source: LightweightFetchSource,
    chunk: SourceChunkFixture,
) -> RecentDevelopmentFixture | None:
    if not isinstance(fact.value, dict):
        return None
    title = _clean_chat_text(fact.value.get("title")) or source.title
    summary = _clean_chat_text(fact.value.get("summary"))
    if not title or not summary:
        return None
    return RecentDevelopmentFixture(
        event_id=_clean_chat_text(fact.value.get("event_id")) or fact.fact_id,
        asset_ticker=response.asset.ticker,
        event_type=_clean_chat_text(fact.value.get("event_type")) or "other",
        title=title,
        summary=summary,
        event_date=_clean_chat_text(fact.value.get("event_date")) or fact.as_of_date or source.as_of_date,
        source_document_id=source.source_document_id,
        source_chunk_id=chunk.chunk_id,
        importance_score=10.0 if fact.evidence_state is EvidenceState.supported else 5.0,
        freshness_state=fact.freshness_state,
        evidence_state=fact.evidence_state.value,
    )


def _clean_chat_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _lightweight_fact_unit(fact: LightweightFetchFact) -> str | None:
    value = fact.value
    if isinstance(value, dict):
        unit = value.get("unit")
        return str(unit) if unit else None
    if fact.field_name == "expense_ratio":
        return "%"
    return None


def _lightweight_evidence_gaps(response: LightweightFetchResponse) -> list[EvidenceGap]:
    gaps = [
        EvidenceGap(
            gap_id=gap.fact_id,
            asset_ticker=response.asset.ticker,
            field_name=gap.field_name,
            evidence_state=gap.evidence_state.value,
            message=str(gap.limitations or gap.value or "Lightweight evidence is partial or unavailable for this field."),
            freshness_state=gap.freshness_state,
        )
        for gap in response.gaps
    ]
    diagnostics = response.fallback_diagnostics
    if diagnostics is not None:
        gaps.append(
            EvidenceGap(
                gap_id=f"lw_chat_{response.asset.ticker.lower()}_fallback_diagnostics",
                asset_ticker=response.asset.ticker,
                field_name="lightweight_fallback_diagnostics",
                evidence_state=response.page_render_state.value,
                message=(
                    f"Lightweight fallback diagnostics: source_path={diagnostics.source_path}; "
                    f"reason_codes={', '.join(diagnostics.reason_codes)}; "
                    f"official_sources={diagnostics.official_source_count}; "
                    f"provider_fallback_sources={diagnostics.provider_fallback_source_count}; "
                    f"raw_payload_exposed={diagnostics.raw_payload_exposed}."
                ),
                freshness_state=diagnostics.freshness.freshness_state,
            )
        )
    return gaps


def _lightweight_insufficient_chat(pack: AssetKnowledgePack, question: str, message: str) -> ChatResponse:
    safety_classification = classify_question(question, supported=pack.asset.supported)
    if safety_classification is SafetyClassification.personalized_advice_redirect:
        return _advice_redirect_chat(pack, safety_classification)
    compare_route_redirect = _compare_route_redirect(pack, question)
    if compare_route_redirect is not None:
        return compare_route_redirect
    response = ChatResponse(
        asset=pack.asset,
        direct_answer=f"Insufficient evidence: {message}",
        why_it_matters=(
            "The local lightweight page can show partial source-labeled facts, but chat only answers when the "
            "selected asset evidence can be bound to same-asset citations."
        ),
        citations=[],
        source_documents=[],
        uncertainty=[*_fixture_limits(pack), _gap_message(pack, "lightweight_fallback_diagnostics")],
        safety_classification=safety_classification,
    )
    _assert_safe_copy(response)
    return response


def read_persisted_chat_response(
    ticker: str,
    question: str,
    *,
    persisted_pack_reader: KnowledgePackRecordReader | Any | None = None,
    generated_output_cache_reader: GeneratedOutputChatCacheRecordReader | Any | None = None,
) -> PersistedChatReadResult:
    normalized = ticker.strip().upper()
    fixture_pack = build_asset_knowledge_pack(normalized)
    safety_classification = classify_question(question, supported=fixture_pack.asset.supported)
    if safety_classification is SafetyClassification.unsupported_asset_redirect:
        return PersistedChatReadResult(
            status="blocked_state",
            ticker=normalized,
            diagnostics=("chat:unsupported_or_unavailable_asset",),
        )
    if safety_classification is SafetyClassification.personalized_advice_redirect:
        return PersistedChatReadResult(
            status="blocked_state",
            ticker=normalized,
            diagnostics=("chat:advice_redirect_precedence",),
        )
    if _compare_route_redirect(fixture_pack, question) is not None:
        return PersistedChatReadResult(
            status="blocked_state",
            ticker=normalized,
            diagnostics=("chat:compare_redirect_precedence",),
        )
    if persisted_pack_reader is None or generated_output_cache_reader is None:
        return PersistedChatReadResult(
            status="not_configured",
            ticker=normalized,
            diagnostics=("reader:not_configured",),
        )

    pack_read = read_persisted_knowledge_pack_response(normalized, reader=persisted_pack_reader)
    if not pack_read.found or pack_read.response is None or pack_read.records is None:
        return PersistedChatReadResult(
            status=pack_read.status,
            ticker=normalized,
            diagnostics=(f"knowledge_pack:{pack_read.status}",),
        )
    if not pack_read.response.asset.supported or not pack_read.response.generated_output_available:
        return PersistedChatReadResult(
            status="blocked_state",
            ticker=normalized,
            diagnostics=(f"knowledge_pack:blocked:{pack_read.response.build_state.value}",),
        )

    cache_read = _read_generated_chat_cache_records(generated_output_cache_reader, normalized)
    if cache_read.status != "found" or cache_read.records is None:
        return PersistedChatReadResult(
            status=cache_read.status,
            ticker=normalized,
            diagnostics=cache_read.diagnostics,
        )

    try:
        pack = _asset_knowledge_pack_from_repository_records(pack_read.records)
        _validate_generated_output_cache_for_chat(
            normalized,
            cache_read.records,
            pack=pack,
        )
        response = generate_chat_from_pack(pack, question)
        if response.safety_classification is not SafetyClassification.educational:
            return PersistedChatReadResult(
                status="blocked_state",
                ticker=normalized,
                diagnostics=("chat:non_factual_response",),
            )
        report = validate_chat_response(response, pack)
        if not report.valid:
            return PersistedChatReadResult(
                status="validation_error",
                ticker=normalized,
                diagnostics=("chat:citation_validation_failed",),
            )
        _validate_chat_cache_covers_response(cache_read.records, response)
    except (
        GeneratedOutputCacheContractError,
        KnowledgePackRepositoryContractError,
        ChatGenerationError,
        LookupError,
        StopIteration,
        ValueError,
        TypeError,
    ) as exc:
        return PersistedChatReadResult(
            status="contract_error",
            ticker=normalized,
            diagnostics=(f"chat:{exc.__class__.__name__}",),
        )

    return PersistedChatReadResult(
        status="found",
        ticker=normalized,
        chat_response=response,
        diagnostics=("chat:persisted_hit",),
    )


@dataclass(frozen=True)
class _GeneratedOutputChatCacheReadResult:
    status: str
    ticker: str
    records: GeneratedOutputCacheRepositoryRecords | None = None
    diagnostics: tuple[str, ...] = field(default_factory=tuple)


def _read_generated_chat_cache_records(
    reader: GeneratedOutputChatCacheRecordReader | Any,
    ticker: str,
) -> _GeneratedOutputChatCacheReadResult:
    try:
        raw_records = _read_generated_chat_cache_reader(reader, ticker)
        if raw_records is None:
            return _GeneratedOutputChatCacheReadResult(
                status="miss",
                ticker=ticker,
                diagnostics=("generated_output_cache:miss",),
            )
        records = (
            raw_records
            if isinstance(raw_records, GeneratedOutputCacheRepositoryRecords)
            else GeneratedOutputCacheRepositoryRecords.model_validate(raw_records)
        )
        validated = validate_generated_output_cache_records(records)
    except GeneratedOutputCacheContractError as exc:
        return _GeneratedOutputChatCacheReadResult(
            status="contract_error",
            ticker=ticker,
            diagnostics=(f"generated_output_cache:{exc.__class__.__name__}",),
        )
    except Exception as exc:  # pragma: no cover - caller observes sanitized status only.
        return _GeneratedOutputChatCacheReadResult(
            status="reader_error",
            ticker=ticker,
            diagnostics=(f"generated_output_cache:{exc.__class__.__name__}",),
        )
    return _GeneratedOutputChatCacheReadResult(
        status="found",
        ticker=ticker,
        records=validated,
        diagnostics=("generated_output_cache:found",),
    )


def _read_generated_chat_cache_reader(
    reader: GeneratedOutputChatCacheRecordReader | Any,
    ticker: str,
) -> GeneratedOutputCacheRepositoryRecords | None:
    if isinstance(reader, dict):
        return reader.get(ticker) or reader.get(f"{ticker}:chat") or reader.get(f"asset:{ticker}:chat-safe-answer-metadata")
    if hasattr(reader, "read_chat_answer_records"):
        return reader.read_chat_answer_records(ticker)
    if hasattr(reader, "read_generated_chat_answer_records"):
        return reader.read_generated_chat_answer_records(ticker)
    if hasattr(reader, "read_generated_output_cache_records"):
        return reader.read_generated_output_cache_records(ticker)
    if hasattr(reader, "read"):
        return reader.read(ticker)
    if hasattr(reader, "get"):
        return reader.get(ticker)
    raise GeneratedOutputCacheContractError(
        "Injected generated-output chat reader must expose read_chat_answer_records(ticker), "
        "read_generated_chat_answer_records(ticker), read_generated_output_cache_records(ticker), "
        "read(ticker), or get(ticker)."
    )


def _asset_knowledge_pack_from_repository_records(records: KnowledgePackRepositoryRecords) -> AssetKnowledgePack:
    source_rows = sorted(
        records.source_documents,
        key=lambda row: (row.asset_ticker, row.source_rank, row.source_document_id),
    )
    source_by_id = {row.source_document_id: row for row in source_rows}
    sources = [
        SourceDocumentFixture(
            source_document_id=row.source_document_id,
            asset_ticker=row.asset_ticker,
            source_type=row.source_type,
            source_rank=row.source_rank,
            title=row.title,
            publisher=row.publisher,
            url=row.url,
            published_at=row.published_at,
            retrieved_at=row.retrieved_at,
            content_type="text",
            is_official=row.is_official,
            freshness_state=FreshnessState(row.freshness_state),
            as_of_date=row.as_of_date,
            source_quality=row.source_quality,
            allowlist_status=row.allowlist_status,
            source_use_policy=row.source_use_policy,
        )
        for row in source_rows
    ]
    source_fixtures_by_id = {source.source_document_id: source for source in sources}

    chunks = []
    for row in sorted(records.source_chunks, key=lambda item: (item.source_document_id, item.chunk_order, item.chunk_id)):
        if not row.stored_text:
            raise KnowledgePackRepositoryContractError(
                f"Chunk {row.chunk_id} has no persisted text for chat generation."
            )
        chunks.append(
            RetrievedSourceChunk(
                chunk=SourceChunkFixture(
                    chunk_id=row.chunk_id,
                    asset_ticker=row.asset_ticker,
                    source_document_id=row.source_document_id,
                    section_name=row.section_name,
                    chunk_order=row.chunk_order,
                    text=row.stored_text,
                    token_count=row.token_count,
                    char_start=0,
                    char_end=len(row.stored_text),
                    supported_claim_types=row.supported_claim_types,
                ),
                source_document=source_fixtures_by_id[row.source_document_id],
            )
        )
    chunks_by_id = {item.chunk.chunk_id: item for item in chunks}

    facts = []
    for row in sorted(records.normalized_facts, key=lambda item: item.fact_id):
        if row.value is None:
            raise KnowledgePackRepositoryContractError(f"Fact {row.fact_id} has no persisted value for chat generation.")
        source = source_by_id[row.source_document_id]
        facts.append(
            RetrievedFact(
                fact=NormalizedFactFixture(
                    fact_id=row.fact_id,
                    asset_ticker=row.asset_ticker,
                    fact_type=row.fact_type,
                    field_name=row.field_name,
                    value=row.value,
                    unit=row.unit,
                    period=row.period,
                    as_of_date=row.as_of_date,
                    source_document_id=row.source_document_id,
                    source_chunk_id=row.source_chunk_id,
                    extraction_method=row.extraction_method,
                    confidence=float(row.confidence or 0.0),
                    freshness_state=FreshnessState(row.freshness_state),
                    evidence_state=row.evidence_state,
                ),
                source_document=source_fixtures_by_id[source.source_document_id],
                source_chunk=chunks_by_id[row.source_chunk_id].chunk,
            )
        )

    recent_developments = []
    for row in sorted(records.recent_developments, key=lambda item: item.event_id):
        if row.title is None or row.summary is None:
            raise KnowledgePackRepositoryContractError(
                f"Recent development {row.event_id} has no persisted title or summary for chat generation."
            )
        source = source_by_id[row.source_document_id]
        recent_developments.append(
            RetrievedRecentDevelopment(
                recent_development=RecentDevelopmentFixture(
                    event_id=row.event_id,
                    asset_ticker=row.asset_ticker,
                    event_type=row.event_type,
                    title=row.title,
                    summary=row.summary,
                    event_date=row.event_date,
                    source_document_id=row.source_document_id,
                    source_chunk_id=row.source_chunk_id,
                    importance_score=row.importance_score,
                    freshness_state=FreshnessState(row.freshness_state),
                    evidence_state=row.evidence_state,
                ),
                source_document=source_fixtures_by_id[source.source_document_id],
                source_chunk=chunks_by_id[row.source_chunk_id].chunk,
            )
        )

    return AssetKnowledgePack(
        asset=AssetIdentity.model_validate(records.envelope.asset),
        freshness=Freshness.model_validate(records.envelope.freshness),
        source_documents=sources,
        normalized_facts=facts,
        source_chunks=chunks,
        recent_developments=recent_developments,
        evidence_gaps=[
            EvidenceGap(
                gap_id=row.gap_id,
                asset_ticker=row.asset_ticker,
                field_name=row.field_name,
                evidence_state=row.evidence_state,
                message=row.message or "",
                freshness_state=FreshnessState(row.freshness_state),
                source_document_id=row.source_document_id,
                source_chunk_id=row.source_chunk_id,
            )
            for row in sorted(records.evidence_gaps, key=lambda item: item.gap_id)
        ],
    )


def _validate_generated_output_cache_for_chat(
    ticker: str,
    records: GeneratedOutputCacheRepositoryRecords,
    *,
    pack: AssetKnowledgePack,
) -> None:
    if len(records.envelopes) != 1:
        raise GeneratedOutputCacheContractError("Chat reuse requires exactly one generated-output cache envelope.")
    envelope = records.envelopes[0]
    if envelope.asset_ticker != ticker or pack.asset.ticker != ticker:
        raise GeneratedOutputCacheContractError("Chat cache and knowledge pack must bind to the requested asset.")
    if envelope.entry_kind != CacheEntryKind.chat_answer.value or envelope.cache_scope != CacheScope.chat.value:
        raise GeneratedOutputCacheContractError("Chat cache records must be chat-answer scoped.")
    if envelope.artifact_category != GeneratedOutputArtifactCategory.grounded_chat_answer_artifact.value:
        raise GeneratedOutputCacheContractError("Chat cache records must use the grounded chat answer artifact category.")
    if envelope.output_identity != f"asset:{ticker}:chat-safe-answer-metadata":
        raise GeneratedOutputCacheContractError("Chat cache output identity must match the requested asset.")
    if envelope.comparison_id or envelope.comparison_left_ticker or envelope.comparison_right_ticker:
        raise GeneratedOutputCacheContractError("Chat cache records must not bind a comparison pack.")
    if not envelope.cacheable or not envelope.generated_output_available:
        raise GeneratedOutputCacheContractError("Chat cache records must be cacheable and generated-output available.")

    pack_source_ids = {source.source_document_id for source in pack.source_documents}
    pack_citation_ids = {_citation_id(item.source_document.source_document_id, item.chunk.chunk_id) for item in pack.source_chunks}
    if not set(envelope.source_document_ids) <= pack_source_ids:
        raise GeneratedOutputCacheContractError("Chat cache source IDs must belong to the same selected-asset pack.")
    if not set(envelope.citation_ids) <= pack_citation_ids:
        raise GeneratedOutputCacheContractError("Chat cache citation IDs must belong to the same selected-asset pack.")

    section_freshness_labels = [
        SectionFreshnessInput(
            section_id=section_id,
            freshness_state=FreshnessState(freshness_state),
            evidence_state=envelope.evidence_state_labels.get(section_id),
        )
        for section_id, freshness_state in sorted(envelope.section_freshness_labels.items())
    ]
    knowledge_input = build_knowledge_pack_freshness_input(
        pack,
        section_freshness_labels=section_freshness_labels,
    )
    if envelope.source_document_ids:
        knowledge_input = knowledge_input.model_copy(
            update={
                "source_checksums": [
                    checksum
                    for checksum in knowledge_input.source_checksums
                    if checksum.source_document_id in set(envelope.source_document_ids)
                ]
            }
        )
    expected_knowledge_hash = compute_knowledge_pack_freshness_hash(knowledge_input)
    if envelope.knowledge_pack_freshness_hash != expected_knowledge_hash:
        raise GeneratedOutputCacheContractError("Chat cache knowledge-pack freshness hash does not match current evidence.")
    generated_input = build_generated_output_freshness_input(
        output_identity=envelope.output_identity,
        entry_kind=CacheEntryKind.chat_answer,
        scope=CacheScope.chat,
        schema_version=envelope.schema_version,
        prompt_version=envelope.prompt_version,
        model_name=envelope.model_name,
        knowledge_input=knowledge_input,
    )
    if envelope.generated_output_freshness_hash != compute_generated_output_freshness_hash(generated_input):
        raise GeneratedOutputCacheContractError("Chat cache generated-output freshness hash does not match current evidence.")


def _validate_chat_cache_covers_response(
    records: GeneratedOutputCacheRepositoryRecords,
    response: ChatResponse,
) -> None:
    envelope = records.envelopes[0]
    response_source_ids = {source.source_document_id for source in response.source_documents}
    response_citation_ids = {citation.citation_id for citation in response.citations}
    if not response_source_ids <= set(envelope.source_document_ids):
        raise GeneratedOutputCacheContractError("Chat cache source bindings do not cover generated response sources.")
    if envelope.citation_ids and not response_citation_ids <= set(envelope.citation_ids):
        raise GeneratedOutputCacheContractError("Chat cache citation bindings do not cover generated response citations.")


def generate_chat_from_pack(
    pack: AssetKnowledgePack,
    question: str,
    *,
    summary_generation_service: SummaryGenerationService | None = None,
) -> ChatResponse:
    safety_classification = classify_question(question, supported=pack.asset.supported)

    if safety_classification is SafetyClassification.unsupported_asset_redirect:
        return _unsupported_chat(pack, safety_classification)

    if safety_classification is SafetyClassification.personalized_advice_redirect:
        return _advice_redirect_chat(pack, safety_classification)

    compare_route_redirect = _compare_route_redirect(pack, question)
    if compare_route_redirect is not None:
        return compare_route_redirect

    plan, bindings = _plan_supported_chat(pack, question)
    plan = _maybe_generate_chat_plan(
        pack,
        question,
        plan,
        bindings,
        summary_generation_service=summary_generation_service,
    )
    evidence = bindings.evidence()
    report = validate_generated_chat_claims(pack, plan.planned_claims, evidence)
    if not report.valid:
        first_issue = report.issues[0]
        raise ChatGenerationError(
            f"Generated chat citation validation failed for {pack.asset.ticker}: "
            f"{first_issue.status.value} on {first_issue.claim_id}"
        )

    response = ChatResponse(
        asset=pack.asset,
        direct_answer=plan.direct_answer,
        why_it_matters=plan.why_it_matters,
        citations=bindings.citations_for_claims(plan.planned_claims),
        source_documents=bindings.source_documents_for_claims(plan.planned_claims),
        uncertainty=plan.uncertainty,
        safety_classification=safety_classification,
    )
    _assert_safe_copy(response)
    return response


def validate_chat_response(response: ChatResponse, pack: AssetKnowledgePack) -> CitationValidationReport:
    evidence = _evidence_from_chat_response(pack, response)
    claims = _claims_from_chat_response(response, pack)
    report = validate_claims(claims, evidence, CitationValidationContext(allowed_asset_tickers=[pack.asset.ticker]))
    if not report.valid:
        return report
    return _validate_chat_source_documents(response, pack)


def _maybe_write_chat_generated_output_cache(
    response: ChatResponse,
    pack: AssetKnowledgePack,
    writer: Any | None,
) -> None:
    if (
        writer is None
        or response.safety_classification is not SafetyClassification.educational
        or not response.asset.supported
        or not response.citations
    ):
        return
    try:
        report = validate_chat_response(response, pack)
        if not report.valid or find_forbidden_output_phrases(str(response.model_dump(mode="json"))):
            return
        source_ids = {source.source_document_id for source in response.source_documents}
        citation_ids = [citation.citation_id for citation in response.citations]
        citations_by_source: dict[str, list[str]] = {}
        for citation in response.citations:
            citations_by_source.setdefault(citation.source_document_id, []).append(citation.citation_id)
        knowledge_input = build_knowledge_pack_freshness_input(
            pack,
            section_freshness_labels=[
                SectionFreshnessInput(
                    section_id="chat_answer",
                    freshness_state=FreshnessState.fresh,
                    evidence_state="supported",
                )
            ],
        )
        knowledge_input = knowledge_input.model_copy(
            update={
                "source_checksums": [
                    checksum.model_copy(
                        update={"citation_ids": sorted(citations_by_source.get(checksum.source_document_id, []))}
                    )
                    for checksum in knowledge_input.source_checksums
                    if checksum.source_document_id in source_ids
                ]
            }
        )
        records = build_deterministic_generated_output_cache_records(
            cache_entry_id=f"generated-output-{response.asset.ticker.lower()}-chat-answer",
            output_identity=f"asset:{response.asset.ticker}:chat-safe-answer-metadata",
            mode_or_output_type="grounded-chat-safe-answer",
            artifact_category=GeneratedOutputArtifactCategory.grounded_chat_answer_artifact,
            entry_kind=CacheEntryKind.chat_answer,
            scope=CacheScope.chat,
            schema_version="chat-answer-v1",
            prompt_version="chat-answer-prompt-v1",
            knowledge_input=knowledge_input,
            citation_ids=citation_ids,
            created_at="2026-04-25T18:33:44Z",
            ttl_seconds=604800,
            asset_ticker=response.asset.ticker,
        )
        persist_generated_output_cache_records(writer, records)
    except Exception:
        return


def validate_generated_chat_claims(
    pack: AssetKnowledgePack,
    planned_claims: Iterable[PlannedChatClaim],
    evidence: list[CitationEvidence],
) -> CitationValidationReport:
    claims = [
        CitationValidationClaim(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            claim_type=claim.claim_type,
            citation_ids=claim.citation_ids,
            freshness_label=claim.freshness_label,
        )
        for claim in planned_claims
    ]
    return validate_claims(claims, evidence, CitationValidationContext(allowed_asset_tickers=[pack.asset.ticker]))


class _ChatCitationRegistry:
    def __init__(self, pack: AssetKnowledgePack) -> None:
        self._pack = pack
        self._bindings_by_citation_id: dict[str, ChatCitationBinding] = {}

    def for_fact(self, retrieved_fact: RetrievedFact, claim_text: str) -> str:
        return self.for_chunk(
            RetrievedSourceChunk(chunk=retrieved_fact.source_chunk, source_document=retrieved_fact.source_document),
            claim_text,
            supports_claim=retrieved_fact.fact.evidence_state in {"supported", "partial"},
            freshness_state=retrieved_fact.fact.freshness_state,
        )

    def for_chunk(
        self,
        retrieved_chunk: RetrievedSourceChunk,
        claim_text: str,
        *,
        supports_claim: bool = True,
        freshness_state: FreshnessState | None = None,
        is_recent: bool | None = None,
    ) -> str:
        citation_id = _citation_id(retrieved_chunk.source_document.source_document_id, retrieved_chunk.chunk.chunk_id)
        evidence = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=self._pack.asset.ticker,
            source_document_id=retrieved_chunk.source_document.source_document_id,
            source_type=retrieved_chunk.source_document.source_type,
            evidence_kind=EvidenceKind.document_chunk,
            freshness_state=freshness_state or retrieved_chunk.source_document.freshness_state,
            retrieved_at=retrieved_chunk.source_document.retrieved_at,
            as_of_date=retrieved_chunk.source_document.as_of_date,
            published_at=retrieved_chunk.source_document.published_at,
            supported_claim_types=retrieved_chunk.chunk.supported_claim_types,
            supporting_text=retrieved_chunk.chunk.text,
            supports_claim=supports_claim,
            is_recent=is_recent
            if is_recent is not None
            else retrieved_chunk.source_document.source_type == "recent_development",
            allowlist_status=retrieved_chunk.source_document.allowlist_status,
            source_use_policy=retrieved_chunk.source_document.source_use_policy,
            source_identity=retrieved_chunk.source_document.url or retrieved_chunk.source_document.source_document_id,
            is_official=retrieved_chunk.source_document.is_official,
            source_quality=retrieved_chunk.source_document.source_quality,
            storage_rights=_storage_rights_for_chat_source(retrieved_chunk.source_document.source_use_policy),
            export_rights=_export_rights_for_chat_source(retrieved_chunk.source_document.source_use_policy),
            review_status=SourceReviewStatus.approved,
            approval_rationale=_chat_source_approval_rationale(retrieved_chunk.source_document),
            parser_status=(
                SourceParserStatus.parsed
                if retrieved_chunk.source_document.is_official
                else SourceParserStatus.partial
            ),
        )
        return self._add_binding(citation_id, claim_text, retrieved_chunk, evidence)

    def for_recent_development(self, item: RetrievedRecentDevelopment, claim_text: str) -> str:
        return self.for_chunk(
            RetrievedSourceChunk(chunk=item.source_chunk, source_document=item.source_document),
            claim_text,
            supports_claim=item.recent_development.evidence_state in {"supported", "partial"},
            freshness_state=item.recent_development.freshness_state,
            is_recent=True,
        )

    def evidence(self) -> list[CitationEvidence]:
        return [binding.evidence for binding in self._sorted_bindings()]

    def citations_for_claims(self, planned_claims: Iterable[PlannedChatClaim]) -> list[ChatCitation]:
        citations: list[ChatCitation] = []
        for claim in planned_claims:
            for citation_id in claim.citation_ids:
                binding = self._bindings_by_citation_id[citation_id]
                citations.append(
                    ChatCitation(
                        citation_id=citation_id,
                        claim=claim.claim_text,
                        source_document_id=binding.citation.source_document_id,
                        chunk_id=binding.citation.chunk_id,
                    )
                )
        return citations

    def source_documents_for_claims(self, planned_claims: Iterable[PlannedChatClaim]) -> list[ChatSourceDocument]:
        source_documents: list[ChatSourceDocument] = []
        seen_citation_ids: set[str] = set()
        for claim in planned_claims:
            for citation_id in claim.citation_ids:
                if citation_id in seen_citation_ids:
                    continue
                source_documents.append(self._bindings_by_citation_id[citation_id].source_document)
                seen_citation_ids.add(citation_id)
        return source_documents

    def _add_binding(
        self,
        citation_id: str,
        claim_text: str,
        retrieved_chunk: RetrievedSourceChunk,
        evidence: CitationEvidence,
    ) -> str:
        if citation_id not in self._bindings_by_citation_id:
            source_document = _chat_source_document_from_chunk(citation_id, retrieved_chunk)
            self._bindings_by_citation_id[citation_id] = ChatCitationBinding(
                citation=ChatCitation(
                    citation_id=citation_id,
                    claim=claim_text,
                    source_document_id=retrieved_chunk.source_document.source_document_id,
                    chunk_id=retrieved_chunk.chunk.chunk_id,
                ),
                source_document=source_document,
                evidence=evidence,
            )
        return citation_id

    def _sorted_bindings(self) -> list[ChatCitationBinding]:
        return sorted(self._bindings_by_citation_id.values(), key=lambda binding: binding.evidence.citation_id)


def _unsupported_chat(pack: AssetKnowledgePack, safety_classification: SafetyClassification) -> ChatResponse:
    message = _unsupported_message(pack)
    response = ChatResponse(
        asset=pack.asset,
        direct_answer=message,
        why_it_matters="The product currently focuses on U.S.-listed common stocks and plain-vanilla ETFs.",
        citations=[],
        uncertainty=["No local asset knowledge pack is available for this ticker."],
        safety_classification=safety_classification,
    )
    _assert_safe_copy(response)
    return response


def _advice_redirect_chat(pack: AssetKnowledgePack, safety_classification: SafetyClassification) -> ChatResponse:
    direct_answer, why_it_matters = educational_redirect()
    response = ChatResponse(
        asset=pack.asset,
        direct_answer=direct_answer,
        why_it_matters=why_it_matters,
        citations=[],
        uncertainty=["This response does not use personal circumstances, live prices, tax details, or trading instructions."],
        safety_classification=safety_classification,
    )
    _assert_safe_copy(response)
    return response


def _compare_route_redirect(pack: AssetKnowledgePack, question: str) -> ChatResponse | None:
    detected_pair = _detected_comparison_pair(question, pack.asset.ticker)
    if detected_pair is None:
        return None

    left_ticker, right_ticker, comparison_ticker = detected_pair
    comparison = generate_comparison(left_ticker, right_ticker)
    availability = (
        comparison.evidence_availability.availability_state
        if comparison.evidence_availability is not None
        else None
    )
    if availability is None:
        return None

    direct_answer = (
        f"This question compares {left_ticker} with {right_ticker}, so use the comparison workflow "
        "instead of a multi-asset answer inside single-asset chat."
    )
    why_it_matters = (
        "Single-asset chat stays grounded in the selected asset pack only. The comparison workflow can "
        "use the current local comparison availability state for both tickers without mixing cross-asset "
        "facts or citations into this chat turn."
    )
    response = ChatResponse(
        asset=pack.asset,
        direct_answer=direct_answer,
        why_it_matters=why_it_matters,
        citations=[],
        source_documents=[],
        uncertainty=[
            "This redirect is workflow guidance only and does not provide a multi-asset factual comparison inside single-asset chat.",
            comparison.state.message,
            *_fixture_limits(pack),
        ],
        safety_classification=SafetyClassification.compare_route_redirect,
        compare_route_suggestion=ChatCompareRouteSuggestion(
            selected_ticker=pack.asset.ticker,
            comparison_ticker=comparison_ticker,
            left_ticker=left_ticker,
            right_ticker=right_ticker,
            route=f"/compare?left={left_ticker}&right={right_ticker}",
            comparison_availability_state=availability,
            comparison_state_message=comparison.state.message,
            workflow_guidance=direct_answer,
            grounding_explanation=why_it_matters,
        ),
    )
    _assert_safe_copy(response)
    return response


def _plan_supported_chat(pack: AssetKnowledgePack, question: str) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    facts_by_field = {
        item.fact.field_name: item
        for item in pack.normalized_facts
        if item.fact.evidence_state in {"supported", "partial"}
    }
    chunks_by_claim_type = _chunks_by_claim_type(pack)
    bindings = _ChatCitationRegistry(pack)
    intent = _classify_intent(question)

    if intent == "recent":
        return _recent_plan(pack, facts_by_field, bindings)
    if intent == "risk":
        return _risk_plan(pack, facts_by_field, bindings, chunks_by_claim_type)
    if intent == "suitability":
        return _suitability_plan(pack, facts_by_field, bindings, chunks_by_claim_type)
    if intent == "business":
        if pack.asset.asset_type is AssetType.stock:
            return _stock_business_plan(pack, facts_by_field, bindings)
        return _insufficient_plan(pack, "business_model", "This local ETF fixture does not contain stock-style business-model evidence.")
    if intent in {"holdings", "benchmark", "cost", "breadth"}:
        if pack.asset.asset_type is AssetType.etf:
            return _etf_basics_plan(pack, facts_by_field, bindings, intent)
        return _insufficient_plan(pack, "etf_profile", "This local stock fixture does not contain ETF holdings, benchmark, breadth, or cost evidence.")
    if intent == "price_position":
        return _price_position_plan(pack, facts_by_field, bindings)
    if intent == "trading_volume":
        return _quote_stat_plan(pack, facts_by_field, bindings, "average_volume")
    if intent == "performance":
        return _performance_plan(pack, facts_by_field, bindings)
    if intent == "methodology":
        if pack.asset.asset_type is AssetType.etf:
            return _methodology_plan(pack, facts_by_field, bindings)
        return _insufficient_plan(pack, "methodology", "Methodology and index-construction evidence is an ETF concept; this stock pack does not contain that evidence.")
    if intent == "evidence_gap":
        return _evidence_gap_plan(pack, facts_by_field, bindings)
    if intent == "valuation":
        return _valuation_plan(pack, facts_by_field, bindings)

    return _identity_plan(pack, facts_by_field, bindings)


def _maybe_generate_chat_plan(
    pack: AssetKnowledgePack,
    question: str,
    plan: _ChatPlan,
    bindings: _ChatCitationRegistry,
    *,
    summary_generation_service: SummaryGenerationService | None = None,
) -> _ChatPlan:
    if not plan.planned_claims or plan.direct_answer.lower().startswith("insufficient evidence"):
        return plan

    service = summary_generation_service or build_default_summary_generation_service()
    citation_ids = _dedupe(citation_id for claim in plan.planned_claims for citation_id in claim.citation_ids)
    required_claim_texts = [claim.claim_text for claim in plan.planned_claims if claim.claim_text]
    citation_evidence = bindings.evidence()
    evidence_summaries = [_chat_evidence_summary(evidence) for evidence in citation_evidence]
    generation_evidence_pack = evidence_pack_from_citation_evidence(
        asset=pack.asset,
        evidence=citation_evidence,
        evidence_summaries=evidence_summaries,
        evidence_notes=plan.uncertainty,
    )
    try:
        generated = service.generate_chat_answer(
            asset=pack.asset,
            question=question,
            intent=_classify_intent(question),
            base_direct_answer=plan.direct_answer,
            base_why_it_matters=plan.why_it_matters,
            citation_ids=citation_ids,
            required_claim_texts=required_claim_texts,
            evidence_summaries=evidence_summaries,
            uncertainty=plan.uncertainty,
            generation_evidence_pack=generation_evidence_pack,
        )
    except SummaryGenerationContractError:
        return _ChatPlan(
            direct_answer=plan.direct_answer,
            why_it_matters=plan.why_it_matters,
            planned_claims=plan.planned_claims,
            uncertainty=[
                *plan.uncertainty,
                "Hybrid chat synthesis failed validation, so the deterministic citation-bound answer was used.",
            ],
        )

    return _ChatPlan(
        direct_answer=generated.direct_answer,
        why_it_matters=generated.why_it_matters,
        planned_claims=plan.planned_claims,
        uncertainty=generated.uncertainty,
    )


def _chat_evidence_summary(evidence: CitationEvidence) -> str:
    text = " ".join(str(evidence.supporting_text or "").split())
    if len(text) > 180:
        text = f"{text[:177]}..."
    return (
        f"{evidence.citation_id}: {evidence.source_type}; "
        f"freshness={evidence.freshness_state.value}; text={text}"
    )


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _identity_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)

    if pack.asset.asset_type is AssetType.etf:
        benchmark = facts_by_field.get("benchmark")
        if benchmark is not None:
            claim_text = (
                f"{identity_claim.claim_text} It seeks to track the {benchmark.fact.value}."
            )
            citation_id = bindings.for_fact(benchmark, claim_text)
        else:
            claim_text = identity_claim.claim_text
            citation_id = identity_claim.citation_ids[0]
    else:
        business = facts_by_field.get("primary_business")
        if business is not None:
            claim_text = (
                f"{identity_claim.claim_text} Source-labeled evidence describes its primary business as: {business.fact.value}"
            )
            citation_id = bindings.for_fact(business, claim_text)
        else:
            claim_text = identity_claim.claim_text
            citation_id = identity_claim.citation_ids[0]

    planned_claims = [identity_claim]
    if claim_text != identity_claim.claim_text:
        planned_claims.append(
            PlannedChatClaim(
                claim_id="chat_identity_detail",
                claim_text=claim_text,
                citation_ids=[citation_id],
                claim_type="factual",
            )
        )

    return (
        _ChatPlan(
            direct_answer=claim_text,
            why_it_matters=(
                "Starting with canonical identity helps a beginner separate stable asset facts from recent developments "
                "or personal decision-making."
            ),
            planned_claims=planned_claims,
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _stock_business_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    business = _require_fact(facts_by_field, "primary_business")
    claim_text = f"{pack.asset.name}'s source-labeled evidence describes its primary business as: {business.fact.value}"
    citation_id = bindings.for_fact(business, claim_text)
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters="For a stock, business basics are the starting point for understanding what company-specific risks can affect it.",
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id="chat_stock_business",
                    claim_text=claim_text,
                    citation_ids=[citation_id],
                    claim_type="factual",
                )
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _etf_basics_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
    intent: str,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    field_names_by_intent = {
        "benchmark": ["benchmark"],
        "cost": ["expense_ratio"],
        "holdings": ["holdings_count"],
        "breadth": ["beginner_role", "holdings_count", "benchmark"],
    }
    fields = [field for field in field_names_by_intent[intent] if field in facts_by_field]
    if not fields:
        return _insufficient_plan(pack, intent, f"The local fixture does not contain supported {intent} evidence for this asset.")

    facts = [facts_by_field[field] for field in fields]
    if intent == "benchmark":
        claim_text = f"{pack.asset.ticker} seeks to track the {facts[0].fact.value}."
    elif intent == "cost":
        claim_text = f"The local fixture records {pack.asset.ticker}'s expense ratio as {_format_metric(facts[0].fact.value, facts[0].fact.unit)}."
    elif intent == "holdings":
        claim_text = (
            f"The local fixture records {pack.asset.ticker} as having about "
            f"{_format_metric(facts[0].fact.value, facts[0].fact.unit)}."
        )
    else:
        role = facts_by_field.get("beginner_role")
        holdings = facts_by_field.get("holdings_count")
        benchmark = facts_by_field.get("benchmark")
        claim_text = (
            f"The local fixture frames {pack.asset.ticker} as {str(role.fact.value).lower()}; "
            f"it records about {_format_metric(holdings.fact.value, holdings.fact.unit)} and the {benchmark.fact.value} benchmark."
        )

    citation_ids = [bindings.for_fact(fact, claim_text) for fact in facts]
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters=(
                "ETF basics such as benchmark, holdings breadth, and cost help beginners understand what exposure the fund is designed to provide."
            ),
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id=f"chat_etf_{intent}",
                    claim_text=claim_text,
                    citation_ids=sorted(set(citation_ids)),
                    claim_type="factual" if intent != "breadth" else "interpretation",
                )
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _price_position_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    price_fact = facts_by_field.get("provider_market_price")
    quote_fact = facts_by_field.get("provider_quote_stats")
    chart_fact = facts_by_field.get("provider_price_chart")
    price = _provider_market_price_value(price_fact)
    range_text = _quote_stat_value(quote_fact, "fifty_two_week_range")
    if price is None and not range_text:
        return _insufficient_plan(pack, "provider_market_price", "The selected asset pack does not contain provider price or 52-week range evidence.")

    claim_parts = []
    if price is not None:
        claim_parts.append(f"provider market price is {_format_metric(price, _provider_market_price_unit(price_fact))}")
    if range_text:
        claim_parts.append(f"52-week range is {range_text}")
    chart_phrase = _chart_position_phrase(chart_fact)
    if chart_phrase:
        claim_parts.append(chart_phrase)
    claim_text = (
        f"For {pack.asset.ticker}, the selected evidence says the "
        + "; ".join(claim_parts)
        + ". This can help frame whether the current quote is near a cited range, but it is not a buy/sell signal."
    )
    citation_ids: list[str] = []
    for fact in [item for item in [price_fact, quote_fact, chart_fact] if item is not None]:
        citation_ids.append(bindings.for_fact(fact, claim_text))
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters=(
                "A high-point question is safest when framed against cited price, 52-week range, and chart evidence, not as a prediction or recommendation."
            ),
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id="chat_price_position",
                    claim_text=claim_text,
                    citation_ids=sorted(set(citation_ids)),
                    claim_type="factual",
                ),
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _quote_stat_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
    metric_id: str,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    quote_fact = facts_by_field.get("provider_quote_stats")
    value = _quote_stat_value(quote_fact, metric_id)
    label = _quote_stat_label(quote_fact, metric_id) or metric_id.replace("_", " ")
    if value is None:
        return _insufficient_plan(pack, metric_id, f"The selected asset pack does not contain supported {label} evidence.")
    claim_text = (
        f"The provider quote-stat evidence lists {pack.asset.ticker}'s {label} as {value}. "
        "This is trading-context evidence, not a liquidity recommendation or instruction."
    )
    citation_id = bindings.for_fact(_require_fact(facts_by_field, "provider_quote_stats"), claim_text)
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters="Volume fields help beginners understand trading context, but provider-derived rows should stay separate from official issuer or company facts.",
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id=f"chat_quote_stat_{metric_id}",
                    claim_text=claim_text,
                    citation_ids=[citation_id],
                    claim_type="factual",
                ),
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _valuation_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    valuation_fact = facts_by_field.get("provider_stock_metric_groups")
    profile_fact = facts_by_field.get("provider_profile_overview")
    if valuation_fact is None and profile_fact is None:
        return _insufficient_plan(pack, "valuation_context", _gap_message(pack, "valuation_context"))
    valuation_rows = _provider_metric_values(valuation_fact, "valuation_ratios", limit=4)
    profile_values = _profile_valuation_values(profile_fact)
    parts = [*valuation_rows, *profile_values]
    if not parts:
        return _insufficient_plan(pack, "valuation_context", "The selected asset pack has provider valuation sources but no supported valuation rows.")
    claim_text = (
        f"For {pack.asset.ticker}, provider valuation context includes {_join_human(parts)}. "
        "That gives vocabulary and current context, but this answer does not label the stock cheap or expensive."
    )
    citation_ids = [
        bindings.for_fact(fact, claim_text)
        for fact in [valuation_fact, profile_fact]
        if fact is not None
    ]
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters="Valuation questions need cited ratios, business context, and comparisons; a single provider snapshot is not enough for a personal decision.",
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id="chat_valuation_context",
                    claim_text=claim_text,
                    citation_ids=sorted(set(citation_ids)),
                    claim_type="factual",
                ),
            ],
            uncertainty=[*_fixture_limits(pack), "Provider valuation rows are educational context, not a cheap-or-expensive conclusion."],
        ),
        bindings,
    )


def _performance_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    performance_fact = facts_by_field.get("provider_fund_performance")
    price_performance = _provider_metric_values(facts_by_field.get("provider_stock_metric_groups"), "price_performance", limit=4)
    if performance_fact is not None and isinstance(performance_fact.fact.value, dict):
        returns = [
            f"{item.get('period')}: {_format_metric(item.get('return'), '%')}"
            for item in performance_fact.fact.value.get("trailing_returns") or []
            if isinstance(item, dict) and item.get("return") not in (None, "")
        ][:4]
        if returns:
            claim_text = (
                f"Provider performance evidence for {pack.asset.ticker} lists {_join_human(returns)}. "
                "These are historical return fields, not a return estimate."
            )
            citation_id = bindings.for_fact(performance_fact, claim_text)
            return (
                _ChatPlan(
                    direct_answer=f"{identity_claim.claim_text} {claim_text}",
                    why_it_matters="Historical performance can help beginners read context, but it does not predict future returns.",
                    planned_claims=[
                        identity_claim,
                        PlannedChatClaim("chat_performance", claim_text, [citation_id], "factual"),
                    ],
                    uncertainty=_fixture_limits(pack),
                ),
                bindings,
            )
    if price_performance:
        fact = _require_fact(facts_by_field, "provider_stock_metric_groups")
        claim_text = (
            f"Provider price-performance rows for {pack.asset.ticker} include {_join_human(price_performance)}. "
            "These rows describe past or current context and do not estimate what comes next."
        )
        citation_id = bindings.for_fact(fact, claim_text)
        return (
            _ChatPlan(
                direct_answer=f"{identity_claim.claim_text} {claim_text}",
                why_it_matters="Performance rows are useful for context only when their date, period, and source are clear.",
                planned_claims=[identity_claim, PlannedChatClaim("chat_performance", claim_text, [citation_id], "factual")],
                uncertainty=_fixture_limits(pack),
            ),
            bindings,
        )
    return _insufficient_plan(pack, "performance", "The selected asset pack does not contain supported historical performance evidence.")


def _methodology_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    benchmark = facts_by_field.get("benchmark")
    prospectus = facts_by_field.get("prospectus_reference")
    if benchmark is None and prospectus is None:
        return _insufficient_plan(pack, "methodology", "The selected ETF pack does not contain supported benchmark or prospectus evidence.")
    parts = []
    if benchmark is not None:
        parts.append(f"tracks {benchmark.fact.value}")
    if prospectus is not None:
        parts.append(f"has prospectus reference {prospectus.fact.value}")
    claim_text = (
        f"{pack.asset.ticker}'s methodology context says it {_join_human(parts)}. "
        "Full screening, rebalancing, and methodology rules may still be partial unless the source pack includes them."
    )
    citation_ids = [bindings.for_fact(fact, claim_text) for fact in [benchmark, prospectus] if fact is not None]
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters="ETF methodology tells beginners what the fund is designed to follow and what details remain missing.",
            planned_claims=[
                identity_claim,
                PlannedChatClaim("chat_methodology", claim_text, sorted(set(citation_ids)), "factual"),
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _evidence_gap_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    gaps = [gap for gap in pack.evidence_gaps[:4] if gap.message]
    if not gaps:
        claim_text = f"The selected {pack.asset.ticker} pack has no explicit evidence-gap rows in the current response."
    else:
        claim_text = f"The selected {pack.asset.ticker} pack labels these evidence gaps: " + "; ".join(
            f"{gap.field_name}: {gap.message}" for gap in gaps
        )
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters="Evidence gaps tell beginners where the page is intentionally saying unknown, unavailable, or partial instead of inventing detail.",
            planned_claims=[identity_claim],
            uncertainty=[*_fixture_limits(pack), claim_text],
        ),
        bindings,
    )


def _risk_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
    chunks_by_claim_type: dict[str, list[RetrievedSourceChunk]],
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    risk_chunk = _first_chunk(chunks_by_claim_type, "risk")
    if risk_chunk is None:
        return _insufficient_plan(pack, "risk", "The local fixture does not contain supported risk evidence for this asset.")

    if pack.asset.ticker == "AAPL":
        claim_text = "A key beginner risk is company-specific risk: Apple can be affected by product demand, competition, supply chain disruption, regulation, and other company-specific issues."
    elif pack.asset.ticker == "QQQ":
        claim_text = "A key beginner risk is concentration: QQQ can be more concentrated than broader equity funds, so fewer companies or sectors can drive more of the result."
    else:
        claim_text = "A key beginner risk is market risk: VOO can lose value when U.S. large-company stocks decline, and index tracking does not remove that risk."

    citation_id = bindings.for_chunk(risk_chunk, claim_text)
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters="Risk evidence helps a beginner understand what can go wrong before comparing an asset with broader or narrower alternatives.",
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id="chat_top_risk",
                    claim_text=claim_text,
                    citation_ids=[citation_id],
                    claim_type="risk",
                )
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _recent_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    if not pack.recent_developments:
        return _insufficient_plan(pack, "recent_development", "The local fixture does not contain recent-development evidence for this asset.")

    supported_recent = [
        item
        for item in pack.recent_developments
        if item.recent_development.evidence_state in {"supported", "partial"}
    ]
    if not supported_recent:
        return _insufficient_plan(
            pack,
            "recent_development",
            "The selected asset pack records no supported recent-development evidence for this asset.",
        )

    recent = supported_recent[0]
    claim_text = f"{recent.recent_development.title}: {recent.recent_development.summary}"
    citation_id = bindings.for_recent_development(recent, claim_text)
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters="Recent developments are kept separate from stable identity so a short-term update does not redefine what the asset is.",
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id="chat_recent_development",
                    claim_text=claim_text,
                    citation_ids=[citation_id],
                    claim_type="recent",
                )
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _suitability_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
    chunks_by_claim_type: dict[str, list[RetrievedSourceChunk]],
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    if pack.asset.asset_type is AssetType.etf:
        role = facts_by_field.get("beginner_role")
        if role is None:
            return _insufficient_plan(pack, "beginner_role", "The local fixture does not contain supported beginner-role evidence for this ETF.")
        if pack.asset.ticker == "QQQ":
            claim_text = (
                "Beginners may study QQQ to learn how narrower, growth-oriented ETF exposure differs from a broader market ETF."
            )
        else:
            claim_text = "Beginners may study VOO to learn how a broad U.S. large-company index ETF works."
        citation_id = bindings.for_fact(role, claim_text)
        claim_type = "interpretation"
    else:
        risk_chunk = _first_chunk(chunks_by_claim_type, "risk")
        if risk_chunk is None:
            return _insufficient_plan(pack, "suitability", "The local fixture does not contain supported suitability evidence for this stock.")
        claim_text = (
            "Beginners may study Apple to learn how a familiar single-company business differs from diversified fund exposure."
        )
        citation_id = bindings.for_chunk(risk_chunk, claim_text)
        claim_type = "risk"

    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters=(
                "This is educational framing, not a personal recommendation; beginners can use it to decide what facts and risks to study next."
            ),
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id="chat_educational_suitability",
                    claim_text=claim_text,
                    citation_ids=[citation_id],
                    claim_type=claim_type,
                )
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _insufficient_plan(
    pack: AssetKnowledgePack,
    field_name: str,
    message: str,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    return (
        _ChatPlan(
            direct_answer=f"Insufficient evidence: {message}",
            why_it_matters=(
                "When the selected asset knowledge pack is missing evidence, the safer answer is to say what is unknown instead of filling the gap."
            ),
            planned_claims=[],
            uncertainty=[*_fixture_limits(pack), _gap_message(pack, field_name)],
        ),
        _ChatCitationRegistry(pack),
    )


def _canonical_identity_claim(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> PlannedChatClaim:
    identity = _require_fact(facts_by_field, "canonical_asset_identity")
    if pack.asset.asset_type is AssetType.etf:
        issuer = f" from {pack.asset.issuer}" if pack.asset.issuer else ""
        claim_text = f"{pack.asset.ticker} is {pack.asset.name}, a plain-vanilla ETF listed in the U.S.{issuer}."
    else:
        claim_text = f"{pack.asset.ticker} is {pack.asset.name}, a U.S.-listed stock."
    citation_id = bindings.for_fact(identity, claim_text)
    return PlannedChatClaim(
        claim_id="chat_canonical_identity",
        claim_text=claim_text,
        citation_ids=[citation_id],
        claim_type="factual",
    )


def _classify_intent(question: str) -> str:
    text = " ".join(question.lower().split())
    if any(term in text for term in ["high point", "near high", "at a high", "52-week", "52 week", "range", "current price", "price now", "right now"]):
        return "price_position"
    if any(term in text for term in ["average daily trading volume", "average volume", "trading volume", "volume", "liquidity"]):
        return "trading_volume"
    if any(term in text for term in ["recent", "changed", "change", "news", "latest", "new development", "development"]):
        return "recent"
    if any(term in text for term in ["risk", "risks", "biggest catch", "main catch", "what can go wrong", "downside"]):
        return "risk"
    if any(term in text for term in ["beginner", "beginners", "why people", "why consider", "suitable", "fit", "use this", "use it"]):
        return "suitability"
    if any(term in text for term in ["business", "make money", "does apple do", "company do", "sells", "products", "services"]):
        return "business"
    if any(term in text for term in ["holding", "holdings", "hold", "holds", "owns", "own", "how many companies"]):
        return "holdings"
    if any(term in text for term in ["benchmark", "index", "track", "tracks"]):
        return "benchmark"
    if any(term in text for term in ["fee", "cost", "expense ratio", "expenses"]):
        return "cost"
    if any(term in text for term in ["broad", "breadth", "diversified", "narrow", "concentrated", "concentration"]):
        return "breadth"
    if any(term in text for term in ["performance", "return", "returns", "up", "down", "ytd", "past year"]):
        return "performance"
    if any(term in text for term in ["methodology", "construction", "rebalance", "rebalancing", "screening", "rules"]):
        return "methodology"
    if any(term in text for term in ["missing", "unknown", "unavailable", "evidence gap", "source gap", "why can't", "cannot answer"]):
        return "evidence_gap"
    if any(term in text for term in ["valuation", "valued", "p/e", "pe ratio", "multiple", "expensive", "cheap"]):
        return "valuation"
    return "identity"


def _detected_comparison_pair(question: str, selected_ticker: str) -> tuple[str, str, str] | None:
    if not _looks_like_comparison_question(question):
        return None

    mentions = _mentioned_tickers(question)
    distinct_mentions: list[str] = []
    for ticker in mentions:
        if ticker not in distinct_mentions:
            distinct_mentions.append(ticker)

    selected_ticker = selected_ticker.upper()
    if len(distinct_mentions) > 2:
        return None

    if len(distinct_mentions) == 2:
        left_ticker, right_ticker = distinct_mentions
        if selected_ticker not in {left_ticker, right_ticker}:
            return None
        comparison_ticker = right_ticker if left_ticker == selected_ticker else left_ticker
        return left_ticker, right_ticker, comparison_ticker

    if len(distinct_mentions) == 1:
        comparison_ticker = distinct_mentions[0]
        if comparison_ticker == selected_ticker:
            return None
        return selected_ticker, comparison_ticker, comparison_ticker

    return None


def _looks_like_comparison_question(question: str) -> bool:
    normalized = " ".join(question.lower().split())
    return any(re.search(pattern, normalized) for pattern in COMPARISON_INTENT_PATTERNS)


def _mentioned_tickers(question: str) -> list[str]:
    mentions: list[str] = []
    for match in TICKER_TOKEN_PATTERN.finditer(question):
        token = match.group(0)
        if token.upper() in COMPARISON_CONNECTOR_TOKENS:
            continue
        resolved_ticker = _resolved_ticker_token(token)
        if resolved_ticker is None:
            continue
        mentions.append(resolved_ticker)
    return mentions


def _resolved_ticker_token(token: str) -> str | None:
    response = search_assets(token)
    if len(response.results) != 1 or response.state.status.value == "ambiguous":
        return None

    result = response.results[0]
    normalized_token = token.upper()
    if result.support_classification.value != "unknown" and result.ticker == normalized_token:
        return result.ticker

    if result.support_classification.value == "unknown" and token == normalized_token:
        return normalized_token

    return None


def _chunks_by_claim_type(pack: AssetKnowledgePack) -> dict[str, list[RetrievedSourceChunk]]:
    chunks: dict[str, list[RetrievedSourceChunk]] = {}
    for item in pack.source_chunks:
        for claim_type in item.chunk.supported_claim_types:
            chunks.setdefault(claim_type, []).append(item)
    return chunks


def _first_chunk(
    chunks_by_claim_type: dict[str, list[RetrievedSourceChunk]],
    claim_type: str,
) -> RetrievedSourceChunk | None:
    chunks = chunks_by_claim_type.get(claim_type)
    if not chunks:
        return None
    return sorted(chunks, key=lambda item: (item.source_document.source_rank, item.chunk.chunk_order))[0]


def _provider_market_price_value(fact: RetrievedFact | None) -> Any | None:
    if fact is None or not isinstance(fact.fact.value, dict):
        return None
    return fact.fact.value.get("regularMarketPrice") or fact.fact.value.get("chartPreviousClose")


def _provider_market_price_unit(fact: RetrievedFact | None) -> str | None:
    if fact is None or not isinstance(fact.fact.value, dict):
        return None
    currency = fact.fact.value.get("currency")
    return f" {currency}" if currency else None


def _quote_stat_value(fact: RetrievedFact | None, metric_id: str) -> str | None:
    row = _quote_stat_row(fact, metric_id)
    if row is None or row.get("value") in (None, ""):
        return None
    return str(row.get("value"))


def _quote_stat_label(fact: RetrievedFact | None, metric_id: str) -> str | None:
    row = _quote_stat_row(fact, metric_id)
    if row is None:
        return None
    return str(row.get("label") or metric_id.replace("_", " "))


def _quote_stat_row(fact: RetrievedFact | None, metric_id: str) -> dict[str, Any] | None:
    if fact is None or not isinstance(fact.fact.value, dict):
        return None
    rows = fact.fact.value.get("rows")
    if not isinstance(rows, list):
        return None
    return next(
        (
            row
            for row in rows
            if isinstance(row, dict) and str(row.get("metric_id") or "") == metric_id
        ),
        None,
    )


def _chart_position_phrase(fact: RetrievedFact | None) -> str | None:
    if fact is None or not isinstance(fact.fact.value, dict):
        return None
    points = [
        point
        for point in fact.fact.value.get("points") or []
        if isinstance(point, dict) and isinstance(point.get("close"), (int, float))
    ]
    if len(points) < 2:
        return None
    first = points[0]["close"]
    last = points[-1]["close"]
    return f"{fact.fact.value.get('range') or 'recent'} chart closes moved from {first} to {last}"


def _provider_metric_values(fact: RetrievedFact | None, group_id: str, *, limit: int) -> list[str]:
    if fact is None or not isinstance(fact.fact.value, dict):
        return []
    groups = fact.fact.value.get("groups")
    if not isinstance(groups, list):
        return []
    group = next((item for item in groups if isinstance(item, dict) and item.get("group_id") == group_id), None)
    if not isinstance(group, dict):
        return []
    values: list[str] = []
    for metric in group.get("metrics") or []:
        if not isinstance(metric, dict) or metric.get("value") in (None, ""):
            continue
        values.append(f"{metric.get('label') or metric.get('metric_id')}: {metric.get('value')}")
        if len(values) >= limit:
            break
    return values


def _profile_valuation_values(fact: RetrievedFact | None) -> list[str]:
    if fact is None or not isinstance(fact.fact.value, dict):
        return []
    labels = (
        ("trailing_pe", "trailing P/E"),
        ("forward_pe", "forward P/E"),
        ("market_cap", "market cap"),
        ("enterprise_value", "enterprise value"),
    )
    return [
        f"{label}: {fact.fact.value[key]}"
        for key, label in labels
        if fact.fact.value.get(key) not in (None, "")
    ]


def _join_human(values: list[str]) -> str:
    values = [value for value in values if value]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def _require_fact(facts_by_field: dict[str, RetrievedFact], field_name: str) -> RetrievedFact:
    fact = facts_by_field.get(field_name)
    if fact is None:
        raise ChatGenerationError(f"Required fact is missing from retrieval pack: {field_name}.")
    return fact


def _fixture_limits(pack: AssetKnowledgePack) -> list[str]:
    lightweight = any(source.source_document_id.startswith("lw_") for source in pack.source_documents) or any(
        gap.field_name == "lightweight_fallback_diagnostics" for gap in pack.evidence_gaps
    )
    if lightweight:
        notes = [
            "This answer is bounded to the lightweight local-MVP normalized facts that rendered the selected asset page.",
            "Lightweight chat does not approve sources, promote manifests, write generated-output cache records, or create durable knowledge-pack records.",
        ]
    else:
        notes = ["This answer is bounded to the local fixture-backed asset knowledge pack and does not use live market data."]
    if pack.freshness.facts_as_of:
        notes.append(f"Stable facts are as of {pack.freshness.facts_as_of}.")
    if pack.freshness.recent_events_as_of:
        notes.append(f"Recent-development evidence is as of {pack.freshness.recent_events_as_of}.")
    if lightweight:
        for gap in pack.evidence_gaps:
            if gap.field_name == "lightweight_fallback_diagnostics":
                notes.append(gap.message)
                break
    return notes


def _gap_message(pack: AssetKnowledgePack, field_name: str) -> str:
    for gap in pack.evidence_gaps:
        if gap.field_name == field_name:
            return gap.message
    return f"No local fixture evidence is available for {field_name}."


def _unsupported_message(pack: AssetKnowledgePack) -> str:
    if pack.asset.status is AssetStatus.unknown:
        return "This ticker is not available in the local skeleton data yet."
    if pack.evidence_gaps:
        return pack.evidence_gaps[0].message
    return "This asset is outside the current U.S. stock and plain-vanilla ETF scope."


def _format_metric(value: Any, unit: str | None) -> str:
    if unit:
        return f"{value}{unit}"
    return str(value)


def _chat_source_document_from_chunk(citation_id: str, retrieved_chunk: RetrievedSourceChunk) -> ChatSourceDocument:
    source = retrieved_chunk.source_document
    decision = resolve_source_policy(
        url=source.url,
        source_identifier=source.url if source.url.startswith("local://") else None,
    )
    return ChatSourceDocument(
        citation_id=citation_id,
        source_document_id=source.source_document_id,
        chunk_id=retrieved_chunk.chunk.chunk_id,
        title=source.title,
        source_type=source.source_type,
        publisher=source.publisher,
        url=source.url,
        published_at=source.published_at,
        as_of_date=source.as_of_date,
        retrieved_at=source.retrieved_at,
        freshness_state=source.freshness_state,
        is_official=source.is_official,
        supporting_passage=retrieved_chunk.chunk.text,
        source_quality=source.source_quality,
        allowlist_status=source.allowlist_status,
        source_use_policy=source.source_use_policy,
        permitted_operations=decision.permitted_operations
        if decision.allowlist_status is source.allowlist_status and decision.source_use_policy is source.source_use_policy
        else _operations_for_chat_source_policy(source.source_use_policy),
        source_identity=source.url or source.source_document_id,
        storage_rights=_storage_rights_for_chat_source(source.source_use_policy),
        export_rights=_export_rights_for_chat_source(source.source_use_policy),
        review_status=SourceReviewStatus.approved,
        approval_rationale=_chat_source_approval_rationale(source),
        parser_status=SourceParserStatus.parsed if source.is_official else SourceParserStatus.partial,
    )


def _operations_for_chat_source_policy(policy: SourceUsePolicy):
    if policy is SourceUsePolicy.full_text_allowed:
        from backend.models import DEFAULT_ALLOWED_SOURCE_OPERATIONS

        return DEFAULT_ALLOWED_SOURCE_OPERATIONS.model_copy()
    from backend.models import SourceOperationPermissions

    return SourceOperationPermissions(
        can_store_metadata=True,
        can_store_raw_text=False,
        can_display_metadata=True,
        can_display_excerpt=policy is SourceUsePolicy.summary_allowed,
        can_summarize=policy is SourceUsePolicy.summary_allowed,
        can_cache=policy is SourceUsePolicy.summary_allowed,
        can_export_metadata=True,
        can_export_excerpt=False,
        can_export_full_text=False,
        can_support_generated_output=policy is SourceUsePolicy.summary_allowed,
        can_support_citations=policy is SourceUsePolicy.summary_allowed,
        can_support_canonical_facts=policy is SourceUsePolicy.summary_allowed,
        can_support_recent_developments=False,
    )


def _storage_rights_for_chat_source(policy: SourceUsePolicy) -> SourceStorageRights:
    if policy is SourceUsePolicy.full_text_allowed:
        return SourceStorageRights.raw_snapshot_allowed
    if policy is SourceUsePolicy.summary_allowed:
        return SourceStorageRights.summary_allowed
    if policy is SourceUsePolicy.link_only:
        return SourceStorageRights.link_only
    if policy is SourceUsePolicy.rejected:
        return SourceStorageRights.rejected
    return SourceStorageRights.metadata_only


def _export_rights_for_chat_source(policy: SourceUsePolicy) -> SourceExportRights:
    if policy is SourceUsePolicy.full_text_allowed:
        return SourceExportRights.excerpts_allowed
    if policy is SourceUsePolicy.link_only:
        return SourceExportRights.link_only
    if policy is SourceUsePolicy.rejected:
        return SourceExportRights.rejected
    return SourceExportRights.metadata_only


def _chat_source_approval_rationale(source: SourceDocumentFixture) -> str:
    if source.source_document_id.startswith("lw_") or source.source_document_id.startswith("provider_"):
        return (
            "Lightweight local-MVP normalized evidence reused from the renderable page response; "
            "this is not strict audit-quality source approval or generated-output cache promotion."
        )
    return "Deterministic fixture source passed local source-use policy review."


def _validate_chat_source_documents(response: ChatResponse, pack: AssetKnowledgePack) -> CitationValidationReport:
    citation_ids = {citation.citation_id for citation in response.citations}
    if not citation_ids and not response.source_documents:
        return _valid_chat_validation_report()

    source_documents_by_citation_id = {source.citation_id: source for source in response.source_documents}
    source_chunks_by_key = {
        (item.source_document.source_document_id, item.chunk.chunk_id): item for item in pack.source_chunks
    }

    issues: list[CitationValidationIssue] = []
    for citation in response.citations:
        source_document = source_documents_by_citation_id.get(citation.citation_id)
        if source_document is None:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.citation_not_found,
                    claim_id="chat_source_metadata",
                    citation_id=citation.citation_id,
                    source_document_id=citation.source_document_id,
                    message="Chat citation is missing source-document metadata.",
                )
            )
            continue

        if source_document.source_document_id != citation.source_document_id or source_document.chunk_id != citation.chunk_id:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.citation_not_found,
                    claim_id="chat_source_metadata",
                    citation_id=citation.citation_id,
                    source_document_id=source_document.source_document_id,
                    message="Chat source-document metadata does not match the citation binding.",
                )
            )
            continue

        expected = source_chunks_by_key.get((source_document.source_document_id, source_document.chunk_id))
        if expected is None:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.citation_not_found,
                    claim_id="chat_source_metadata",
                    citation_id=source_document.citation_id,
                    source_document_id=source_document.source_document_id,
                    message="Chat source-document metadata is not present in the selected asset knowledge pack.",
                )
            )
            continue

        if expected.chunk.asset_ticker != pack.asset.ticker or expected.source_document.asset_ticker != pack.asset.ticker:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.wrong_asset,
                    claim_id="chat_source_metadata",
                    citation_id=source_document.citation_id,
                    source_document_id=source_document.source_document_id,
                    message="Chat source-document metadata belongs to an asset outside the selected pack.",
                )
            )
            continue

        expected_source = expected.source_document
        metadata_matches_pack = (
            source_document.title == expected_source.title
            and source_document.source_type == expected_source.source_type
            and source_document.url == expected_source.url
            and source_document.published_at == expected_source.published_at
            and source_document.as_of_date == expected_source.as_of_date
            and source_document.retrieved_at == expected_source.retrieved_at
            and source_document.freshness_state is expected_source.freshness_state
            and source_document.supporting_passage == expected.chunk.text
        )
        if not metadata_matches_pack:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.insufficient_evidence,
                    claim_id="chat_source_metadata",
                    citation_id=source_document.citation_id,
                    source_document_id=source_document.source_document_id,
                    message="Chat source-document metadata does not match the selected asset knowledge pack.",
                )
            )

    extra_metadata_ids = set(source_documents_by_citation_id) - citation_ids
    for citation_id in sorted(extra_metadata_ids):
        source_document = source_documents_by_citation_id[citation_id]
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.citation_not_found,
                claim_id="chat_source_metadata",
                citation_id=citation_id,
                source_document_id=source_document.source_document_id,
                message="Chat source-document metadata has no matching chat citation.",
            )
        )

    if not issues:
        return _valid_chat_validation_report()

    return CitationValidationReport(
        status=issues[0].status,
        results=[
            CitationValidationResult(
                claim_id="chat_source_metadata",
                status=issues[0].status,
                issues=issues,
            )
        ],
    )


def _valid_chat_validation_report() -> CitationValidationReport:
    return CitationValidationReport(
        status=CitationValidationStatus.valid,
        results=[CitationValidationResult(claim_id="chat_source_metadata", status=CitationValidationStatus.valid)],
    )


def _evidence_from_chat_response(pack: AssetKnowledgePack, response: ChatResponse) -> list[CitationEvidence]:
    source_chunks_by_key = {
        (item.source_document.source_document_id, item.chunk.chunk_id): item for item in pack.source_chunks
    }
    evidence_by_id: dict[str, CitationEvidence] = {}
    for citation in response.citations:
        key = (citation.source_document_id, citation.chunk_id)
        item = source_chunks_by_key.get(key)
        if item is None:
            continue
        citation_id = _citation_id(citation.source_document_id, citation.chunk_id)
        evidence_by_id[citation_id] = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=item.chunk.asset_ticker,
            source_document_id=item.source_document.source_document_id,
            source_type=item.source_document.source_type,
            evidence_kind=EvidenceKind.document_chunk,
            freshness_state=item.source_document.freshness_state,
            supported_claim_types=item.chunk.supported_claim_types,
            supporting_text=item.chunk.text,
            supports_claim=True,
            is_recent=item.source_document.source_type == "recent_development",
            allowlist_status=item.source_document.allowlist_status,
            source_use_policy=item.source_document.source_use_policy,
        )
    return list(evidence_by_id.values())


def _claims_from_chat_response(
    response: ChatResponse,
    pack: AssetKnowledgePack,
) -> list[CitationValidationClaim]:
    if not response.citations:
        return [
            CitationValidationClaim(
                claim_id="chat_response_direct_answer",
                claim_text=response.direct_answer,
                claim_type="factual",
                citation_ids=[],
                citation_required=_requires_citations(response, pack),
                important=_requires_citations(response, pack),
            )
        ]

    source_chunks_by_key = {
        (item.source_document.source_document_id, item.chunk.chunk_id): item for item in pack.source_chunks
    }
    claims: list[CitationValidationClaim] = []
    for index, citation in enumerate(response.citations, start=1):
        key = (citation.source_document_id, citation.chunk_id)
        chunk = source_chunks_by_key.get(key)
        claims.append(
            CitationValidationClaim(
                claim_id=f"chat_response_claim_{index}",
                claim_text=citation.claim,
                claim_type=_infer_claim_type(citation.claim, chunk),
                citation_ids=[_citation_id(citation.source_document_id, citation.chunk_id)],
            )
        )
    return claims


def _requires_citations(response: ChatResponse, pack: AssetKnowledgePack) -> bool:
    if response.safety_classification is not SafetyClassification.educational:
        return False
    if not pack.asset.supported:
        return False
    return "insufficient evidence" not in response.direct_answer.lower()


def _infer_claim_type(claim_text: str, chunk: RetrievedSourceChunk | None) -> str:
    text = claim_text.lower()
    supported = set(chunk.chunk.supported_claim_types) if chunk is not None else set()
    if "recent" in supported:
        return "recent"
    if "risk" in supported and any(term in text for term in ["risk", "concentration", "lose value", "company-specific"]):
        return "risk"
    if "suitability" in supported and any(term in text for term in ["beginner", "educational", "study"]):
        return "suitability"
    if "interpretation" in supported and any(term in text for term in ["beginner", "broad", "narrower", "exposure"]):
        return "interpretation"
    return "factual"


def _citation_id(source_document_id: str, chunk_id: str) -> str:
    return f"chat_{source_document_id}_{chunk_id}"


def _assert_safe_copy(response: ChatResponse) -> None:
    dumped = response.model_dump(mode="json")
    hits = find_forbidden_output_phrases(_flatten_text(dumped))
    if hits:
        raise ChatGenerationError(f"Generated chat leaked forbidden output phrases: {hits}")


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return ""
