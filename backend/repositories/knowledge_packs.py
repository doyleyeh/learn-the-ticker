from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models import (
    AssetIdentity,
    Freshness,
    FreshnessState,
    IngestionCapabilities,
    KnowledgePackBuildResponse,
    KnowledgePackBuildState,
    KnowledgePackChunkMetadata,
    KnowledgePackCounts,
    KnowledgePackEvidenceGapMetadata,
    KnowledgePackFactMetadata,
    KnowledgePackRecentDevelopmentMetadata,
    KnowledgePackSourceMetadata,
    SectionFreshnessInput,
    SourceAllowlistStatus,
    SourceChecksumRecord,
    SourceOperationPermissions,
    SourceQuality,
    SourceUsePolicy,
    StateMessage,
)


KNOWLEDGE_PACK_REPOSITORY_BOUNDARY = "asset-knowledge-pack-repository-contract-v1"
KNOWLEDGE_PACK_REPOSITORY_TABLES = (
    "asset_knowledge_pack_envelopes",
    "asset_knowledge_pack_source_documents",
    "asset_knowledge_pack_source_chunks",
    "asset_knowledge_pack_facts",
    "asset_knowledge_pack_recent_developments",
    "asset_knowledge_pack_evidence_gaps",
    "asset_knowledge_pack_section_freshness_inputs",
    "asset_knowledge_pack_source_checksums",
)
_TEXT_BLOCKED_POLICIES = {
    SourceUsePolicy.metadata_only,
    SourceUsePolicy.link_only,
}


class KnowledgePackRepositoryContractError(ValueError):
    """Raised when a knowledge-pack record would break source/citation boundaries."""


class RepositoryTableDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    primary_key: tuple[str, ...]
    columns: tuple[str, ...]


class RepositoryMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    boundary: str
    opens_connection_on_import: bool = False
    creates_runtime_tables: bool = False
    table_definitions: tuple[RepositoryTableDefinition, ...]

    @property
    def tables(self) -> dict[str, RepositoryTableDefinition]:
        return {table.name: table for table in self.table_definitions}


class StrictRow(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgePackEnvelopeRow(StrictRow):
    pack_id: str
    schema_version: str
    ticker: str
    asset: dict[str, Any]
    asset_type: str
    build_state: str
    support_status: str
    state: dict[str, Any]
    generated_output_available: bool
    reusable_generated_output_cache_hit: bool
    generated_route: str | None = None
    capabilities: dict[str, Any]
    freshness: dict[str, Any]
    counts: dict[str, Any]
    source_document_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    knowledge_pack_freshness_hash: str | None = None
    cache_key: str | None = None
    no_live_external_calls: bool = True
    exports_full_source_documents: bool = False
    message: str


class KnowledgePackSourceDocumentRow(StrictRow):
    pack_id: str
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
    freshness_state: str
    is_official: bool
    source_quality: str
    allowlist_status: str
    source_use_policy: str
    permitted_operations: dict[str, Any]
    citation_ids: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    recent_event_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)


class KnowledgePackSourceChunkRow(StrictRow):
    pack_id: str
    chunk_id: str
    asset_ticker: str
    source_document_id: str
    section_name: str
    chunk_order: int
    token_count: int
    supported_claim_types: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    source_use_policy: str
    text_storage_policy: str
    stored_text: str | None = None


class KnowledgePackFactRow(StrictRow):
    pack_id: str
    fact_id: str
    asset_ticker: str
    fact_type: str
    field_name: str
    value: Any | None = None
    unit: str | None = None
    period: str | None = None
    as_of_date: str | None = None
    source_document_id: str
    source_chunk_id: str
    extraction_method: str
    confidence: float | None = None
    freshness_state: str
    evidence_state: str
    citation_ids: list[str] = Field(default_factory=list)


class KnowledgePackRecentDevelopmentRow(StrictRow):
    pack_id: str
    event_id: str
    asset_ticker: str
    event_type: str
    title: str | None = None
    summary: str | None = None
    event_date: str | None = None
    source_document_id: str
    source_chunk_id: str
    importance_score: float
    freshness_state: str
    evidence_state: str
    citation_ids: list[str] = Field(default_factory=list)


class KnowledgePackEvidenceGapRow(StrictRow):
    pack_id: str
    gap_id: str
    asset_ticker: str
    field_name: str
    evidence_state: str
    freshness_state: str
    source_document_id: str | None = None
    source_chunk_id: str | None = None
    message: str | None = None


class KnowledgePackSectionFreshnessRow(StrictRow):
    pack_id: str
    section_id: str
    freshness_state: str
    evidence_state: str | None = None
    as_of_date: str | None = None
    retrieved_at: str | None = None


class KnowledgePackSourceChecksumRow(StrictRow):
    pack_id: str
    source_document_id: str
    asset_ticker: str
    checksum: str
    freshness_state: str
    cache_allowed: bool
    export_allowed: bool
    allowlist_status: str
    source_use_policy: str
    source_type: str
    source_rank: int | None = None
    citation_ids: list[str] = Field(default_factory=list)
    fact_bindings: list[str] = Field(default_factory=list)
    recent_event_bindings: list[str] = Field(default_factory=list)


class KnowledgePackRepositoryRecords(StrictRow):
    envelope: KnowledgePackEnvelopeRow
    source_documents: list[KnowledgePackSourceDocumentRow] = Field(default_factory=list)
    source_chunks: list[KnowledgePackSourceChunkRow] = Field(default_factory=list)
    normalized_facts: list[KnowledgePackFactRow] = Field(default_factory=list)
    recent_developments: list[KnowledgePackRecentDevelopmentRow] = Field(default_factory=list)
    evidence_gaps: list[KnowledgePackEvidenceGapRow] = Field(default_factory=list)
    section_freshness_inputs: list[KnowledgePackSectionFreshnessRow] = Field(default_factory=list)
    source_checksums: list[KnowledgePackSourceChecksumRow] = Field(default_factory=list)

    @property
    def table_names(self) -> tuple[str, ...]:
        return KNOWLEDGE_PACK_REPOSITORY_TABLES


def knowledge_pack_repository_metadata() -> RepositoryMetadata:
    return RepositoryMetadata(
        boundary=KNOWLEDGE_PACK_REPOSITORY_BOUNDARY,
        table_definitions=(
            RepositoryTableDefinition(
                name="asset_knowledge_pack_envelopes",
                primary_key=("pack_id",),
                columns=tuple(KnowledgePackEnvelopeRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="asset_knowledge_pack_source_documents",
                primary_key=("pack_id", "source_document_id"),
                columns=tuple(KnowledgePackSourceDocumentRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="asset_knowledge_pack_source_chunks",
                primary_key=("pack_id", "chunk_id"),
                columns=tuple(KnowledgePackSourceChunkRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="asset_knowledge_pack_facts",
                primary_key=("pack_id", "fact_id"),
                columns=tuple(KnowledgePackFactRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="asset_knowledge_pack_recent_developments",
                primary_key=("pack_id", "event_id"),
                columns=tuple(KnowledgePackRecentDevelopmentRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="asset_knowledge_pack_evidence_gaps",
                primary_key=("pack_id", "gap_id"),
                columns=tuple(KnowledgePackEvidenceGapRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="asset_knowledge_pack_section_freshness_inputs",
                primary_key=("pack_id", "section_id"),
                columns=tuple(KnowledgePackSectionFreshnessRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="asset_knowledge_pack_source_checksums",
                primary_key=("pack_id", "source_document_id"),
                columns=tuple(KnowledgePackSourceChecksumRow.model_fields),
            ),
        ),
    )


@dataclass
class AssetKnowledgePackRepository:
    session: Any | None = None

    def serialize(
        self,
        response: KnowledgePackBuildResponse,
        *,
        retrieval_pack: Any | None = None,
    ) -> KnowledgePackRepositoryRecords:
        return serialize_knowledge_pack_response(response, retrieval_pack=retrieval_pack)

    def deserialize(self, records: KnowledgePackRepositoryRecords) -> KnowledgePackBuildResponse:
        return deserialize_knowledge_pack_response(records)

    def persist(self, records: KnowledgePackRepositoryRecords) -> KnowledgePackRepositoryRecords:
        if self.session is None:
            return records
        if not hasattr(self.session, "add_all"):
            raise KnowledgePackRepositoryContractError("Injected repository session must expose add_all(records).")
        self.session.add_all(records_to_row_list(records))
        return records


def serialize_knowledge_pack_response(
    response: KnowledgePackBuildResponse,
    *,
    retrieval_pack: Any | None = None,
) -> KnowledgePackRepositoryRecords:
    envelope = KnowledgePackEnvelopeRow(
        pack_id=response.pack_id,
        schema_version=response.schema_version,
        ticker=response.ticker,
        asset=response.asset.model_dump(mode="json"),
        asset_type=response.asset_type.value,
        build_state=response.build_state.value,
        support_status=response.state.status.value,
        state=response.state.model_dump(mode="json"),
        generated_output_available=response.generated_output_available,
        reusable_generated_output_cache_hit=response.reusable_generated_output_cache_hit,
        generated_route=response.generated_route,
        capabilities=response.capabilities.model_dump(mode="json"),
        freshness=response.freshness.model_dump(mode="json"),
        counts=response.counts.model_dump(mode="json"),
        source_document_ids=response.source_document_ids,
        citation_ids=response.citation_ids,
        knowledge_pack_freshness_hash=response.knowledge_pack_freshness_hash,
        cache_key=response.cache_key,
        no_live_external_calls=response.no_live_external_calls,
        exports_full_source_documents=response.exports_full_source_documents,
        message=response.message,
    )
    records = KnowledgePackRepositoryRecords(
        envelope=envelope,
        source_documents=[_source_row(response.pack_id, source) for source in response.source_documents],
        source_chunks=[
            _chunk_row(response.pack_id, chunk, _source_by_id(response).get(chunk.source_document_id), retrieval_pack)
            for chunk in response.source_chunks
        ],
        normalized_facts=[_fact_row(response.pack_id, fact, retrieval_pack) for fact in response.normalized_facts],
        recent_developments=[
            _recent_row(response.pack_id, recent, retrieval_pack) for recent in response.recent_developments
        ],
        evidence_gaps=[_gap_row(response.pack_id, gap) for gap in response.evidence_gaps],
        section_freshness_inputs=[_section_freshness_row(response.pack_id, section) for section in response.section_freshness],
        source_checksums=[_checksum_row(response.pack_id, checksum) for checksum in response.source_checksums],
    )
    _validate_records(records)
    return records


def deserialize_knowledge_pack_response(records: KnowledgePackRepositoryRecords) -> KnowledgePackBuildResponse:
    _validate_records(records)
    envelope = records.envelope
    return KnowledgePackBuildResponse(
        schema_version=envelope.schema_version,
        ticker=envelope.ticker,
        asset=AssetIdentity.model_validate(envelope.asset),
        asset_type=envelope.asset_type,
        pack_id=envelope.pack_id,
        build_state=KnowledgePackBuildState(envelope.build_state),
        state=StateMessage.model_validate(envelope.state),
        generated_output_available=envelope.generated_output_available,
        reusable_generated_output_cache_hit=envelope.reusable_generated_output_cache_hit,
        generated_route=envelope.generated_route,
        capabilities=IngestionCapabilities.model_validate(envelope.capabilities),
        freshness=Freshness.model_validate(envelope.freshness),
        section_freshness=[
            SectionFreshnessInput(
                section_id=row.section_id,
                freshness_state=FreshnessState(row.freshness_state),
                evidence_state=row.evidence_state,
                as_of_date=row.as_of_date,
                retrieved_at=row.retrieved_at,
            )
            for row in records.section_freshness_inputs
        ],
        source_document_ids=envelope.source_document_ids,
        citation_ids=envelope.citation_ids,
        counts=KnowledgePackCounts.model_validate(envelope.counts),
        source_documents=[_source_model(row) for row in records.source_documents],
        normalized_facts=[_fact_model(row) for row in records.normalized_facts],
        source_chunks=[_chunk_model(row) for row in records.source_chunks],
        recent_developments=[
            _recent_model(row) for row in records.recent_developments
        ],
        evidence_gaps=[_gap_model(row) for row in records.evidence_gaps],
        source_checksums=[_checksum_model(row) for row in records.source_checksums],
        knowledge_pack_freshness_hash=envelope.knowledge_pack_freshness_hash,
        cache_key=envelope.cache_key,
        cache_revalidation=None,
        no_live_external_calls=envelope.no_live_external_calls,
        exports_full_source_documents=envelope.exports_full_source_documents,
        message=envelope.message,
    )


def records_to_row_list(records: KnowledgePackRepositoryRecords) -> list[StrictRow]:
    return [
        records.envelope,
        *records.source_documents,
        *records.source_chunks,
        *records.normalized_facts,
        *records.recent_developments,
        *records.evidence_gaps,
        *records.section_freshness_inputs,
        *records.source_checksums,
    ]


def _source_by_id(response: KnowledgePackBuildResponse) -> dict[str, KnowledgePackSourceMetadata]:
    return {source.source_document_id: source for source in response.source_documents}


def _source_row(pack_id: str, source: KnowledgePackSourceMetadata) -> KnowledgePackSourceDocumentRow:
    return KnowledgePackSourceDocumentRow(
        pack_id=pack_id,
        source_document_id=source.source_document_id,
        asset_ticker=source.asset_ticker,
        source_type=source.source_type,
        source_rank=source.source_rank,
        title=source.title,
        publisher=source.publisher,
        url=source.url,
        published_at=source.published_at,
        as_of_date=source.as_of_date,
        retrieved_at=source.retrieved_at,
        freshness_state=source.freshness_state.value,
        is_official=source.is_official,
        source_quality=source.source_quality.value,
        allowlist_status=source.allowlist_status.value,
        source_use_policy=source.source_use_policy.value,
        permitted_operations=source.permitted_operations.model_dump(mode="json"),
        citation_ids=source.citation_ids,
        fact_ids=source.fact_ids,
        recent_event_ids=source.recent_event_ids,
        chunk_ids=source.chunk_ids,
    )


def _chunk_row(
    pack_id: str,
    chunk: KnowledgePackChunkMetadata,
    source: KnowledgePackSourceMetadata | None,
    retrieval_pack: Any | None,
) -> KnowledgePackSourceChunkRow:
    source_use_policy = source.source_use_policy if source else SourceUsePolicy.rejected
    stored_text, text_storage_policy = _stored_chunk_text(chunk, source_use_policy, retrieval_pack)
    return KnowledgePackSourceChunkRow(
        pack_id=pack_id,
        chunk_id=chunk.chunk_id,
        asset_ticker=chunk.asset_ticker,
        source_document_id=chunk.source_document_id,
        section_name=chunk.section_name,
        chunk_order=chunk.chunk_order,
        token_count=chunk.token_count,
        supported_claim_types=chunk.supported_claim_types,
        citation_ids=chunk.citation_ids,
        source_use_policy=source_use_policy.value,
        text_storage_policy=text_storage_policy,
        stored_text=stored_text,
    )


def _fact_row(pack_id: str, fact: KnowledgePackFactMetadata, retrieval_pack: Any | None) -> KnowledgePackFactRow:
    full_fact = _find_retrieval_fact(retrieval_pack, fact.fact_id)
    return KnowledgePackFactRow(
        pack_id=pack_id,
        fact_id=fact.fact_id,
        asset_ticker=fact.asset_ticker,
        fact_type=fact.fact_type,
        field_name=fact.field_name,
        value=getattr(full_fact, "value", None),
        unit=getattr(full_fact, "unit", None),
        period=getattr(full_fact, "period", None),
        as_of_date=fact.as_of_date,
        source_document_id=fact.source_document_id,
        source_chunk_id=fact.source_chunk_id,
        extraction_method=fact.extraction_method,
        confidence=getattr(full_fact, "confidence", None),
        freshness_state=fact.freshness_state.value,
        evidence_state=fact.evidence_state,
        citation_ids=fact.citation_ids,
    )


def _recent_row(
    pack_id: str,
    recent: KnowledgePackRecentDevelopmentMetadata,
    retrieval_pack: Any | None,
) -> KnowledgePackRecentDevelopmentRow:
    full_recent = _find_retrieval_recent(retrieval_pack, recent.event_id)
    return KnowledgePackRecentDevelopmentRow(
        pack_id=pack_id,
        event_id=recent.event_id,
        asset_ticker=recent.asset_ticker,
        event_type=recent.event_type,
        title=getattr(full_recent, "title", None),
        summary=getattr(full_recent, "summary", None),
        event_date=recent.event_date,
        source_document_id=recent.source_document_id,
        source_chunk_id=recent.source_chunk_id,
        importance_score=recent.importance_score,
        freshness_state=recent.freshness_state.value,
        evidence_state=recent.evidence_state,
        citation_ids=recent.citation_ids,
    )


def _gap_row(pack_id: str, gap: KnowledgePackEvidenceGapMetadata) -> KnowledgePackEvidenceGapRow:
    return KnowledgePackEvidenceGapRow(
        pack_id=pack_id,
        gap_id=gap.gap_id,
        asset_ticker=gap.asset_ticker,
        field_name=gap.field_name,
        evidence_state=gap.evidence_state,
        freshness_state=gap.freshness_state.value,
        source_document_id=gap.source_document_id,
        source_chunk_id=gap.source_chunk_id,
        message=gap.message,
    )


def _section_freshness_row(pack_id: str, section: SectionFreshnessInput) -> KnowledgePackSectionFreshnessRow:
    return KnowledgePackSectionFreshnessRow(
        pack_id=pack_id,
        section_id=section.section_id,
        freshness_state=section.freshness_state.value,
        evidence_state=section.evidence_state,
        as_of_date=section.as_of_date,
        retrieved_at=section.retrieved_at,
    )


def _checksum_row(pack_id: str, checksum: SourceChecksumRecord) -> KnowledgePackSourceChecksumRow:
    return KnowledgePackSourceChecksumRow(
        pack_id=pack_id,
        source_document_id=checksum.source_document_id,
        asset_ticker=checksum.asset_ticker,
        checksum=checksum.checksum,
        freshness_state=checksum.freshness_state.value,
        cache_allowed=checksum.cache_allowed,
        export_allowed=checksum.export_allowed,
        allowlist_status=checksum.allowlist_status.value,
        source_use_policy=checksum.source_use_policy.value,
        source_type=checksum.source_type,
        source_rank=checksum.source_rank,
        citation_ids=checksum.citation_ids,
        fact_bindings=checksum.fact_bindings,
        recent_event_bindings=checksum.recent_event_bindings,
    )


def _source_model(row: KnowledgePackSourceDocumentRow) -> KnowledgePackSourceMetadata:
    return KnowledgePackSourceMetadata(
        source_document_id=row.source_document_id,
        asset_ticker=row.asset_ticker,
        source_type=row.source_type,
        source_rank=row.source_rank,
        title=row.title,
        publisher=row.publisher,
        url=row.url,
        published_at=row.published_at,
        as_of_date=row.as_of_date,
        retrieved_at=row.retrieved_at,
        freshness_state=FreshnessState(row.freshness_state),
        is_official=row.is_official,
        source_quality=SourceQuality(row.source_quality),
        allowlist_status=SourceAllowlistStatus(row.allowlist_status),
        source_use_policy=SourceUsePolicy(row.source_use_policy),
        permitted_operations=SourceOperationPermissions.model_validate(row.permitted_operations),
        citation_ids=row.citation_ids,
        fact_ids=row.fact_ids,
        recent_event_ids=row.recent_event_ids,
        chunk_ids=row.chunk_ids,
    )


def _chunk_model(row: KnowledgePackSourceChunkRow) -> KnowledgePackChunkMetadata:
    return KnowledgePackChunkMetadata(
        chunk_id=row.chunk_id,
        asset_ticker=row.asset_ticker,
        source_document_id=row.source_document_id,
        section_name=row.section_name,
        chunk_order=row.chunk_order,
        token_count=row.token_count,
        supported_claim_types=row.supported_claim_types,
        citation_ids=row.citation_ids,
    )


def _fact_model(row: KnowledgePackFactRow) -> KnowledgePackFactMetadata:
    return KnowledgePackFactMetadata(
        fact_id=row.fact_id,
        asset_ticker=row.asset_ticker,
        fact_type=row.fact_type,
        field_name=row.field_name,
        source_document_id=row.source_document_id,
        source_chunk_id=row.source_chunk_id,
        extraction_method=row.extraction_method,
        freshness_state=FreshnessState(row.freshness_state),
        evidence_state=row.evidence_state,
        as_of_date=row.as_of_date,
        citation_ids=row.citation_ids,
    )


def _recent_model(row: KnowledgePackRecentDevelopmentRow) -> KnowledgePackRecentDevelopmentMetadata:
    return KnowledgePackRecentDevelopmentMetadata(
        event_id=row.event_id,
        asset_ticker=row.asset_ticker,
        event_type=row.event_type,
        event_date=row.event_date,
        source_document_id=row.source_document_id,
        source_chunk_id=row.source_chunk_id,
        importance_score=row.importance_score,
        freshness_state=FreshnessState(row.freshness_state),
        evidence_state=row.evidence_state,
        citation_ids=row.citation_ids,
    )


def _gap_model(row: KnowledgePackEvidenceGapRow) -> KnowledgePackEvidenceGapMetadata:
    return KnowledgePackEvidenceGapMetadata(
        gap_id=row.gap_id,
        asset_ticker=row.asset_ticker,
        field_name=row.field_name,
        evidence_state=row.evidence_state,
        freshness_state=FreshnessState(row.freshness_state),
        source_document_id=row.source_document_id,
        source_chunk_id=row.source_chunk_id,
        message=row.message,
    )


def _checksum_model(row: KnowledgePackSourceChecksumRow) -> SourceChecksumRecord:
    return SourceChecksumRecord(
        source_document_id=row.source_document_id,
        asset_ticker=row.asset_ticker,
        checksum=row.checksum,
        freshness_state=FreshnessState(row.freshness_state),
        cache_allowed=row.cache_allowed,
        export_allowed=row.export_allowed,
        allowlist_status=SourceAllowlistStatus(row.allowlist_status),
        source_use_policy=SourceUsePolicy(row.source_use_policy),
        source_type=row.source_type,
        source_rank=row.source_rank,
        citation_ids=row.citation_ids,
        fact_bindings=row.fact_bindings,
        recent_event_bindings=row.recent_event_bindings,
    )


def _stored_chunk_text(
    chunk: KnowledgePackChunkMetadata,
    source_use_policy: SourceUsePolicy,
    retrieval_pack: Any | None,
) -> tuple[str | None, str]:
    text = _find_retrieval_chunk_text(retrieval_pack, chunk.chunk_id)
    if source_use_policy in _TEXT_BLOCKED_POLICIES:
        return None, source_use_policy.value
    if source_use_policy is SourceUsePolicy.rejected:
        return None, "rejected"
    if text is None:
        return None, "metadata_only"
    if source_use_policy is SourceUsePolicy.summary_allowed:
        return _truncate_words(text, 80), "allowed_excerpt"
    return text, "raw_text_allowed"


def _find_retrieval_chunk_text(retrieval_pack: Any | None, chunk_id: str) -> str | None:
    if retrieval_pack is None:
        return None
    for item in getattr(retrieval_pack, "source_chunks", []):
        chunk = getattr(item, "chunk", item)
        if getattr(chunk, "chunk_id", None) == chunk_id:
            return getattr(chunk, "text", None)
    return None


def _find_retrieval_fact(retrieval_pack: Any | None, fact_id: str) -> Any | None:
    if retrieval_pack is None:
        return None
    for item in getattr(retrieval_pack, "normalized_facts", []):
        fact = getattr(item, "fact", item)
        if getattr(fact, "fact_id", None) == fact_id:
            return fact
    return None


def _find_retrieval_recent(retrieval_pack: Any | None, event_id: str) -> Any | None:
    if retrieval_pack is None:
        return None
    for item in getattr(retrieval_pack, "recent_developments", []):
        recent = getattr(item, "recent_development", item)
        if getattr(recent, "event_id", None) == event_id:
            return recent
    return None


def _truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _validate_records(records: KnowledgePackRepositoryRecords) -> None:
    ticker = records.envelope.ticker
    source_ids = {source.source_document_id for source in records.source_documents}
    chunk_ids = {chunk.chunk_id for chunk in records.source_chunks}
    citation_ids = set(records.envelope.citation_ids)

    if records.envelope.generated_output_available:
        for source in records.source_documents:
            if source.allowlist_status != SourceAllowlistStatus.allowed.value:
                raise KnowledgePackRepositoryContractError(
                    f"Source {source.source_document_id} is not allowlisted for generated-output use."
                )
            if source.source_use_policy in {
                SourceUsePolicy.metadata_only.value,
                SourceUsePolicy.link_only.value,
                SourceUsePolicy.rejected.value,
            }:
                raise KnowledgePackRepositoryContractError(
                    f"Source {source.source_document_id} cannot support generated-output use."
                )
            if not source.permitted_operations.get("can_support_generated_output", False):
                raise KnowledgePackRepositoryContractError(
                    f"Source {source.source_document_id} lacks generated-output permission."
                )

    for source in records.source_documents:
        _require_same_asset(ticker, source.asset_ticker, source.source_document_id)

    for chunk in records.source_chunks:
        _require_same_asset(ticker, chunk.asset_ticker, chunk.chunk_id)
        if chunk.source_document_id not in source_ids:
            raise KnowledgePackRepositoryContractError(f"Chunk {chunk.chunk_id} references unknown source.")
        if chunk.source_use_policy in {SourceUsePolicy.metadata_only.value, SourceUsePolicy.link_only.value}:
            if chunk.stored_text:
                raise KnowledgePackRepositoryContractError(f"Chunk {chunk.chunk_id} cannot persist raw text.")
        if chunk.source_use_policy == SourceUsePolicy.rejected.value:
            raise KnowledgePackRepositoryContractError(f"Chunk {chunk.chunk_id} comes from a rejected source.")
        _require_known_citations(citation_ids, chunk.citation_ids, chunk.chunk_id)

    for fact in records.normalized_facts:
        _require_same_asset(ticker, fact.asset_ticker, fact.fact_id)
        if fact.source_document_id not in source_ids or fact.source_chunk_id not in chunk_ids:
            raise KnowledgePackRepositoryContractError(f"Fact {fact.fact_id} references evidence outside the pack.")
        _require_known_citations(citation_ids, fact.citation_ids, fact.fact_id)

    for recent in records.recent_developments:
        _require_same_asset(ticker, recent.asset_ticker, recent.event_id)
        if recent.source_document_id not in source_ids or recent.source_chunk_id not in chunk_ids:
            raise KnowledgePackRepositoryContractError(
                f"Recent development {recent.event_id} references evidence outside the pack."
            )
        _require_known_citations(citation_ids, recent.citation_ids, recent.event_id)

    for gap in records.evidence_gaps:
        _require_same_asset(ticker, gap.asset_ticker, gap.gap_id)
        if gap.source_document_id and gap.source_document_id not in source_ids:
            raise KnowledgePackRepositoryContractError(f"Evidence gap {gap.gap_id} references unknown source.")
        if gap.source_chunk_id and gap.source_chunk_id not in chunk_ids:
            raise KnowledgePackRepositoryContractError(f"Evidence gap {gap.gap_id} references unknown chunk.")

    for checksum in records.source_checksums:
        _require_same_asset(ticker, checksum.asset_ticker, checksum.source_document_id)
        if checksum.source_document_id not in source_ids:
            raise KnowledgePackRepositoryContractError(
                f"Checksum {checksum.source_document_id} references unknown source."
            )


def _require_same_asset(expected: str, observed: str, row_id: str) -> None:
    if observed != expected:
        raise KnowledgePackRepositoryContractError(
            f"Row {row_id} belongs to {observed}, not knowledge-pack asset {expected}."
        )


def _require_known_citations(known: set[str], citation_ids: list[str], row_id: str) -> None:
    missing = set(citation_ids) - known
    if missing:
        raise KnowledgePackRepositoryContractError(f"Row {row_id} references unknown citations: {sorted(missing)}.")
