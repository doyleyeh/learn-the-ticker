from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models import (
    AssetIdentity,
    AssetStatus,
    AssetType,
    EvidenceState,
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
    SourceExportRights,
    SourceChecksumRecord,
    SourceOperationPermissions,
    SourceParserStatus,
    SourceQuality,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
    StateMessage,
)
from backend.source_policy import SourcePolicyAction, validate_source_handoff


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
_SOURCE_POLICY_BLOCKED_POLICIES = {
    SourceUsePolicy.metadata_only,
    SourceUsePolicy.link_only,
    SourceUsePolicy.rejected,
}
_SUPPORTED_RESPONSE_STATE = "supported"
_NON_GENERATED_STATE_BY_RESPONSE_STATE = {
    "eligible_not_cached": KnowledgePackBuildState.eligible_not_cached,
    "unsupported": KnowledgePackBuildState.unsupported,
    "out_of_scope": KnowledgePackBuildState.unsupported,
    "unknown": KnowledgePackBuildState.unknown,
    "unavailable": KnowledgePackBuildState.unavailable,
}
_GAP_STATES = {"partial", "stale", "unknown", "unavailable", "insufficient_evidence"}


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
    source_identity: str | None = None
    storage_rights: str = SourceStorageRights.raw_snapshot_allowed.value
    export_rights: str = SourceExportRights.excerpts_allowed.value
    review_status: str = SourceReviewStatus.approved.value
    approval_rationale: str = "Deterministic fixture source passed local source-use policy review."
    parser_status: str = SourceParserStatus.parsed.value
    parser_failure_diagnostics: str | None = None
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
    source_identity: str | None = None
    retrieved_at: str | None = None
    as_of_date: str | None = None
    published_at: str | None = None
    is_official: bool | None = False
    source_quality: str = SourceQuality.fixture.value
    storage_rights: str = SourceStorageRights.raw_snapshot_allowed.value
    export_rights: str = SourceExportRights.excerpts_allowed.value
    review_status: str = SourceReviewStatus.approved.value
    approval_rationale: str = "Deterministic fixture source passed local source-use policy review."
    parser_status: str = SourceParserStatus.parsed.value
    parser_failure_diagnostics: str | None = None
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
    commit_on_write: bool = False

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
        _validate_records(records)
        if self.session is None:
            return records
        _persist_records(
            self.session,
            collection="asset_knowledge_pack",
            key=records.envelope.ticker,
            records=records,
            rows=records_to_row_list(records),
            commit_on_write=self.commit_on_write,
        )
        return records

    def read_knowledge_pack_records(self, ticker: str) -> KnowledgePackRepositoryRecords | None:
        if self.session is None:
            return None
        raw = _read_records(self.session, "asset_knowledge_pack", ticker.strip().upper())
        if raw is None:
            return None
        records = raw if isinstance(raw, KnowledgePackRepositoryRecords) else KnowledgePackRepositoryRecords.model_validate(raw)
        _validate_records(records)
        return records

    def read(self, ticker: str) -> KnowledgePackRepositoryRecords | None:
        return self.read_knowledge_pack_records(ticker)

    def get(self, ticker: str) -> KnowledgePackRepositoryRecords | None:
        return self.read_knowledge_pack_records(ticker)


@dataclass
class InMemoryAssetKnowledgePackRepository:
    records_by_ticker: dict[str, KnowledgePackRepositoryRecords] = field(default_factory=dict)

    def persist(self, records: KnowledgePackRepositoryRecords) -> KnowledgePackRepositoryRecords:
        _validate_records(records)
        self.records_by_ticker[records.envelope.ticker] = records.model_copy(deep=True)
        return records

    def read_knowledge_pack_records(self, ticker: str) -> KnowledgePackRepositoryRecords | None:
        records = self.records_by_ticker.get(ticker.strip().upper())
        return records.model_copy(deep=True) if records else None

    def read(self, ticker: str) -> KnowledgePackRepositoryRecords | None:
        return self.read_knowledge_pack_records(ticker)

    def get(self, ticker: str) -> KnowledgePackRepositoryRecords | None:
        return self.read_knowledge_pack_records(ticker)

    def records(self) -> list[KnowledgePackRepositoryRecords]:
        return [record.model_copy(deep=True) for record in self.records_by_ticker.values()]


def knowledge_pack_records_from_acquisition_result(
    acquisition: Any,
    source_snapshot_records: Any,
    *,
    created_at: str = "2026-04-20T00:00:00Z",
) -> KnowledgePackRepositoryRecords:
    """Build normalized, non-generated repository records from deterministic acquisition artifacts."""

    ticker = str(getattr(acquisition, "ticker", "")).upper()
    if not ticker:
        raise KnowledgePackRepositoryContractError("Acquisition knowledge-pack records require a ticker binding.")
    _validate_snapshot_artifacts_for_acquisition(acquisition, source_snapshot_records)

    response_state = _enum_value(getattr(acquisition, "response_state", None))
    if response_state != _SUPPORTED_RESPONSE_STATE:
        records = _non_generated_acquisition_records(acquisition, created_at=created_at)
        _validate_records(records)
        return records

    response = getattr(acquisition, "provider_response", None)
    if response is None:
        raise KnowledgePackRepositoryContractError("Supported acquisition knowledge packs require a provider response.")
    if response.asset is None or response.asset.ticker != ticker:
        raise KnowledgePackRepositoryContractError("Acquisition provider response must bind to the same asset ticker.")
    if _enum_value(getattr(response, "state", None)) != _SUPPORTED_RESPONSE_STATE:
        raise KnowledgePackRepositoryContractError("Provider response must be supported before knowledge-pack writing.")
    if getattr(response, "no_live_external_calls", True) is not True:
        raise KnowledgePackRepositoryContractError("Knowledge-pack acquisition writes must not depend on live calls.")

    source_records_by_id = {record.source_document_id: record for record in getattr(acquisition, "source_records", ())}
    provider_sources_by_id = {source.source_document_id: source for source in response.source_attributions}
    if set(source_records_by_id) != set(provider_sources_by_id):
        raise KnowledgePackRepositoryContractError("Acquisition source records must match provider source documents.")

    source_rows: list[KnowledgePackSourceDocumentRow] = []
    chunk_rows: list[KnowledgePackSourceChunkRow] = []
    fact_rows: list[KnowledgePackFactRow] = []
    recent_rows: list[KnowledgePackRecentDevelopmentRow] = []
    gap_rows: list[KnowledgePackEvidenceGapRow] = []
    checksum_rows: list[KnowledgePackSourceChecksumRow] = []
    source_bindings: dict[str, dict[str, set[str]]] = {
        source_id: {"citations": set(), "facts": set(), "recents": set(), "chunks": set()}
        for source_id in provider_sources_by_id
    }

    for source_id, source in sorted(provider_sources_by_id.items(), key=lambda item: (item[1].source_rank, item[0])):
        source_record = source_records_by_id[source_id]
        _validate_provider_source_for_write(acquisition, source, source_record)
        source_rows.append(_source_row_from_provider(ticker, source))
        checksum_rows.append(_checksum_row_from_acquisition_source(ticker, source, source_record))

    for fact in sorted(response.facts, key=lambda item: item.fact_id):
        if fact.asset_ticker != ticker:
            raise KnowledgePackRepositoryContractError(f"Provider fact {fact.fact_id} is bound to the wrong asset.")
        evidence_state = _enum_value(fact.evidence_state)
        if evidence_state != EvidenceState.supported.value or not fact.source_document_ids:
            gap_rows.append(_gap_row_from_provider_fact(ticker, fact))
            continue
        source_id = _primary_source_id(fact.fact_id, fact.source_document_ids, provider_sources_by_id)
        source = provider_sources_by_id[source_id]
        chunk_id = f"chunk_{fact.fact_id}"
        citations = list(fact.citation_ids)
        chunk_rows.append(_chunk_row_from_provider_fact(ticker, fact, source, chunk_id))
        fact_rows.append(_fact_row_from_provider_fact(ticker, fact, source_id, chunk_id))
        source_bindings[source_id]["facts"].add(fact.fact_id)
        source_bindings[source_id]["chunks"].add(chunk_id)
        source_bindings[source_id]["citations"].update(citations)

    for recent in sorted(response.recent_developments, key=lambda item: item.event_id):
        if recent.asset_ticker != ticker:
            raise KnowledgePackRepositoryContractError(
                f"Provider recent development {recent.event_id} is bound to the wrong asset."
            )
        evidence_state = "supported" if recent.is_high_signal else "insufficient_evidence"
        source_id = _primary_source_id(recent.event_id, [recent.source_document_id], provider_sources_by_id)
        source = provider_sources_by_id[source_id]
        chunk_id = f"chunk_{recent.event_id}"
        chunk_rows.append(_chunk_row_from_provider_recent(ticker, recent, source, chunk_id))
        recent_rows.append(_recent_row_from_provider_recent(ticker, recent, chunk_id, evidence_state))
        source_bindings[source_id]["recents"].add(recent.event_id)
        source_bindings[source_id]["chunks"].add(chunk_id)
        source_bindings[source_id]["citations"].update(recent.citation_ids)

    gap_rows.extend(_gap_rows_from_acquisition_diagnostics(ticker, acquisition))
    citation_ids = sorted(
        {
            *[citation for row in fact_rows for citation in row.citation_ids],
            *[citation for row in chunk_rows for citation in row.citation_ids],
            *[citation for row in recent_rows for citation in row.citation_ids],
        }
    )
    source_document_ids = sorted(source.source_document_id for source in source_rows)
    source_rows = [
        row.model_copy(
            update={
                "citation_ids": sorted(source_bindings[row.source_document_id]["citations"]),
                "fact_ids": sorted(source_bindings[row.source_document_id]["facts"]),
                "recent_event_ids": sorted(source_bindings[row.source_document_id]["recents"]),
                "chunk_ids": sorted(source_bindings[row.source_document_id]["chunks"]),
            }
        )
        for row in source_rows
    ]
    checksum_rows = [
        row.model_copy(
            update={
                "citation_ids": sorted(source_bindings[row.source_document_id]["citations"]),
                "fact_bindings": sorted(source_bindings[row.source_document_id]["facts"]),
                "recent_event_bindings": sorted(source_bindings[row.source_document_id]["recents"]),
            }
        )
        for row in checksum_rows
    ]
    section_rows = _section_rows_from_acquisition(
        ticker,
        freshness=response.freshness,
        source_rows=source_rows,
        fact_rows=fact_rows,
        recent_rows=recent_rows,
        gap_rows=gap_rows,
    )
    freshness_hash = _acquisition_pack_freshness_hash(
        ticker,
        checksum_rows=checksum_rows,
        fact_rows=fact_rows,
        recent_rows=recent_rows,
        gap_rows=gap_rows,
        section_rows=section_rows,
    )
    records = KnowledgePackRepositoryRecords(
        envelope=KnowledgePackEnvelopeRow(
            pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-v1",
            schema_version="asset-knowledge-pack-build-v1",
            ticker=ticker,
            asset=response.asset.model_dump(mode="json"),
            asset_type=response.asset.asset_type.value,
            build_state=KnowledgePackBuildState.available.value,
            support_status=response.asset.status.value,
            state=StateMessage(
                status=response.asset.status,
                message=(
                    "Normalized acquisition-backed knowledge-pack metadata is persisted; generated pages, "
                    "chat answers, comparisons, risk summaries, and generated-output cache writes remain unavailable."
                ),
            ).model_dump(mode="json"),
            generated_output_available=False,
            reusable_generated_output_cache_hit=False,
            generated_route=None,
            capabilities=IngestionCapabilities().model_dump(mode="json"),
            freshness=Freshness(
                page_last_updated_at=response.freshness.retrieved_at,
                facts_as_of=response.freshness.as_of_date,
                holdings_as_of=response.freshness.as_of_date if response.asset.asset_type is AssetType.etf else None,
                recent_events_as_of=None,
                freshness_state=response.freshness.freshness_state,
            ).model_dump(mode="json"),
            counts=KnowledgePackCounts(
                source_document_count=len(source_rows),
                citation_count=len(citation_ids),
                normalized_fact_count=len(fact_rows),
                source_chunk_count=len(chunk_rows),
                recent_development_count=len(recent_rows),
                evidence_gap_count=len(gap_rows),
            ).model_dump(mode="json"),
            source_document_ids=source_document_ids,
            citation_ids=citation_ids,
            knowledge_pack_freshness_hash=freshness_hash,
            cache_key=None,
            no_live_external_calls=True,
            exports_full_source_documents=False,
            message="Knowledge-pack record was built from deterministic official-source acquisition metadata only.",
        ),
        source_documents=source_rows,
        source_chunks=chunk_rows,
        normalized_facts=fact_rows,
        recent_developments=recent_rows,
        evidence_gaps=gap_rows,
        section_freshness_inputs=section_rows,
        source_checksums=checksum_rows,
    )
    _validate_records(records)
    return records


def _non_generated_acquisition_records(acquisition: Any, *, created_at: str) -> KnowledgePackRepositoryRecords:
    ticker = str(getattr(acquisition, "ticker", "")).upper()
    response_state = _enum_value(getattr(acquisition, "response_state", None)) or "unavailable"
    build_state = _NON_GENERATED_STATE_BY_RESPONSE_STATE.get(response_state, KnowledgePackBuildState.unavailable)
    asset = _asset_from_non_generated_acquisition(ticker, acquisition, build_state)
    evidence_state = "unsupported" if build_state is KnowledgePackBuildState.unsupported else response_state
    message = (
        "Acquisition did not produce supported official-source evidence; no generated page, chat answer, "
        "comparison, risk summary, or generated-output cache write is available."
    )
    gap_rows = [
        KnowledgePackEvidenceGapRow(
            pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-{build_state.value}-v1",
            gap_id=f"gap_{ticker.lower()}_{evidence_state}",
            asset_ticker=ticker,
            field_name="asset_knowledge_pack",
            evidence_state=evidence_state,
            freshness_state=FreshnessState.unavailable.value,
            message=message,
        )
    ]
    records = KnowledgePackRepositoryRecords(
        envelope=KnowledgePackEnvelopeRow(
            pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-{build_state.value}-v1",
            schema_version="asset-knowledge-pack-build-v1",
            ticker=ticker,
            asset=asset.model_dump(mode="json"),
            asset_type=asset.asset_type.value,
            build_state=build_state.value,
            support_status=asset.status.value,
            state=StateMessage(status=asset.status, message=message).model_dump(mode="json"),
            generated_output_available=False,
            reusable_generated_output_cache_hit=False,
            capabilities=IngestionCapabilities(
                can_request_ingestion=build_state is KnowledgePackBuildState.eligible_not_cached
            ).model_dump(mode="json"),
            freshness=Freshness(
                page_last_updated_at=created_at,
                facts_as_of=None,
                holdings_as_of=None,
                recent_events_as_of=None,
                freshness_state=FreshnessState.unavailable,
            ).model_dump(mode="json"),
            counts=KnowledgePackCounts(evidence_gap_count=1).model_dump(mode="json"),
            no_live_external_calls=True,
            exports_full_source_documents=False,
            message=message,
        ),
        evidence_gaps=gap_rows,
        section_freshness_inputs=[
            KnowledgePackSectionFreshnessRow(
                pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-{build_state.value}-v1",
                section_id="asset_knowledge_pack",
                freshness_state=FreshnessState.unavailable.value,
                evidence_state=evidence_state,
                retrieved_at=created_at,
            )
        ],
    )
    return records


def _asset_from_non_generated_acquisition(
    ticker: str,
    acquisition: Any,
    build_state: KnowledgePackBuildState,
) -> AssetIdentity:
    response = getattr(acquisition, "provider_response", None)
    if response is not None and getattr(response, "asset", None) is not None:
        return response.asset
    if build_state is KnowledgePackBuildState.unsupported:
        status = AssetStatus.unsupported
        asset_type = AssetType.unsupported
    elif build_state is KnowledgePackBuildState.unknown:
        status = AssetStatus.unknown
        asset_type = AssetType.unknown
    else:
        status = AssetStatus.unknown
        asset_type = AssetType.unknown
    return AssetIdentity(
        ticker=ticker,
        name=ticker,
        asset_type=asset_type,
        exchange=None,
        issuer=None,
        status=status,
        supported=False,
    )


def _validate_snapshot_artifacts_for_acquisition(acquisition: Any, source_snapshot_records: Any) -> None:
    ticker = str(getattr(acquisition, "ticker", "")).upper()
    artifacts = list(getattr(source_snapshot_records, "artifacts", []))
    diagnostics = list(getattr(source_snapshot_records, "diagnostics", []))
    text = repr([getattr(item, "compact_diagnostics", {}) for item in [*artifacts, *diagnostics]]).lower()
    forbidden = (
        "api" + "_key",
        "authorization",
        "bearer ",
        "secret",
        "raw_provider_payload",
        "raw_source_text",
        "raw_article_text",
        "raw_prompt",
        "raw_model_reasoning",
        "user_question",
        "transcript",
    )
    if any(marker in text for marker in forbidden):
        raise KnowledgePackRepositoryContractError("Source snapshot diagnostics must remain compact and sanitized.")

    response_state = _enum_value(getattr(acquisition, "response_state", None))
    if response_state != _SUPPORTED_RESPONSE_STATE:
        if artifacts:
            raise KnowledgePackRepositoryContractError("Unsupported acquisition states cannot create knowledge-pack evidence.")
        return

    provider_response = getattr(acquisition, "provider_response", None)
    if provider_response is None:
        raise KnowledgePackRepositoryContractError("Supported acquisition snapshots require a provider response.")
    source_records_by_id = {record.source_document_id: record for record in getattr(acquisition, "source_records", ())}
    artifacts_by_source: dict[str, list[Any]] = {}
    for artifact in artifacts:
        if getattr(artifact, "asset_ticker", None) != ticker:
            raise KnowledgePackRepositoryContractError("Source snapshot artifact ticker must match the acquisition ticker.")
        source_document_id = getattr(artifact, "source_document_id", None)
        if not source_document_id:
            raise KnowledgePackRepositoryContractError("Source snapshot artifacts require source document IDs.")
        if getattr(artifact, "source_asset_ticker", ticker) != ticker:
            raise KnowledgePackRepositoryContractError("Source snapshot source ticker must match the acquisition ticker.")
        if getattr(artifact, "source_use_policy", None) == SourceUsePolicy.rejected.value:
            raise KnowledgePackRepositoryContractError("Rejected source snapshots cannot feed knowledge-pack evidence.")
        if not str(getattr(artifact, "checksum", "")).startswith("sha256:"):
            raise KnowledgePackRepositoryContractError("Source snapshot artifacts require sha256 checksum metadata.")
        if getattr(artifact, "signed_url_created", False) or getattr(artifact, "browser_readable_storage_path", False):
            raise KnowledgePackRepositoryContractError("Source snapshot references must remain private.")
        if getattr(artifact, "raw_provider_payload_stored", False) or getattr(artifact, "secrets_stored", False):
            raise KnowledgePackRepositoryContractError("Source snapshot artifacts cannot persist raw payloads or secrets.")
        artifacts_by_source.setdefault(source_document_id, []).append(artifact)

    for source in provider_response.source_attributions:
        source_record = source_records_by_id.get(source.source_document_id)
        if source_record is None:
            raise KnowledgePackRepositoryContractError("Every provider source must have acquisition checksum metadata.")
        if not str(source_record.checksum).startswith("sha256:"):
            raise KnowledgePackRepositoryContractError("Acquisition source records require sha256 checksums.")
        if source.source_use_policy is SourceUsePolicy.rejected or source.allowlist_status is SourceAllowlistStatus.rejected:
            raise KnowledgePackRepositoryContractError("Rejected sources cannot create knowledge-pack evidence.")
        source_artifacts = artifacts_by_source.get(source.source_document_id, [])
        if not source_artifacts:
            raise KnowledgePackRepositoryContractError("Every provider source must have source snapshot artifact metadata.")
        for artifact in source_artifacts:
            source_record_checksum = getattr(artifact, "compact_diagnostics", {}).get("source_record_checksum")
            if source_record_checksum and source_record_checksum != source_record.checksum:
                raise KnowledgePackRepositoryContractError("Source snapshot checksum binding does not match acquisition metadata.")


def _validate_provider_source_for_write(acquisition: Any, source: Any, source_record: Any) -> None:
    ticker = str(getattr(acquisition, "ticker", "")).upper()
    if source.asset_ticker != ticker:
        raise KnowledgePackRepositoryContractError("Provider source ticker must match acquisition ticker.")
    if source_record.source_document_id != source.source_document_id:
        raise KnowledgePackRepositoryContractError("Provider source document must match acquisition source record.")
    if source_record.source_use_policy != source.source_use_policy:
        raise KnowledgePackRepositoryContractError("Provider source-use policy must match acquisition source record.")
    if source_record.allowlist_status != source.allowlist_status:
        raise KnowledgePackRepositoryContractError("Provider allowlist status must match acquisition source record.")
    if source_record.source_quality != source.source_quality:
        raise KnowledgePackRepositoryContractError("Provider source quality must match acquisition source record.")
    if source_record.freshness_state != source.freshness_state:
        raise KnowledgePackRepositoryContractError("Provider source freshness must match acquisition source record.")
    if source.source_use_policy in _SOURCE_POLICY_BLOCKED_POLICIES:
        raise KnowledgePackRepositoryContractError("Metadata-only, link-only, and rejected sources cannot create evidence rows.")
    if source.allowlist_status is not SourceAllowlistStatus.allowed:
        raise KnowledgePackRepositoryContractError("Only allowlisted sources can create acquisition-backed evidence rows.")
    if not source.permitted_operations.can_store_metadata:
        raise KnowledgePackRepositoryContractError("Acquisition-backed source rows require metadata storage permission.")
    if not source.permitted_operations.can_support_citations:
        raise KnowledgePackRepositoryContractError("Acquisition-backed source rows require citation support permission.")
    issuer = getattr(acquisition, "issuer", None)
    if issuer and source.publisher != issuer:
        raise KnowledgePackRepositoryContractError("ETF issuer source must bind to the acquisition issuer.")
    cik = getattr(acquisition, "cik", None)
    if cik and source.source_type == "sec_submissions":
        identity_facts = [
            fact for fact in getattr(acquisition.provider_response, "facts", []) if fact.field_name == "sec_stock_identity"
        ]
        if identity_facts and identity_facts[0].value.get("cik") != cik:
            raise KnowledgePackRepositoryContractError("Stock identity fact must bind to the acquisition CIK.")


def _source_row_from_provider(ticker: str, source: Any) -> KnowledgePackSourceDocumentRow:
    return KnowledgePackSourceDocumentRow(
        pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-v1",
        source_document_id=source.source_document_id,
        asset_ticker=ticker,
        source_type=source.source_type,
        source_rank=source.source_rank,
        title=source.title,
        publisher=source.publisher,
        url=source.url or "",
        published_at=source.published_at,
        as_of_date=source.as_of_date,
        retrieved_at=source.retrieved_at,
        freshness_state=source.freshness_state.value,
        is_official=source.is_official,
        source_quality=source.source_quality.value,
        allowlist_status=source.allowlist_status.value,
        source_use_policy=source.source_use_policy.value,
        permitted_operations=source.permitted_operations.model_dump(mode="json"),
        source_identity=getattr(source, "source_identity", None) or source.url or source.source_document_id,
        storage_rights=getattr(source, "storage_rights", SourceStorageRights.raw_snapshot_allowed).value,
        export_rights=getattr(source, "export_rights", SourceExportRights.excerpts_allowed).value,
        review_status=getattr(source, "review_status", SourceReviewStatus.approved).value,
        approval_rationale=getattr(
            source,
            "approval_rationale",
            "Deterministic fixture source passed local source-use policy review.",
        ),
        parser_status=getattr(source, "parser_status", SourceParserStatus.parsed).value,
        parser_failure_diagnostics=getattr(source, "parser_failure_diagnostics", None),
    )


def _checksum_row_from_acquisition_source(ticker: str, source: Any, source_record: Any) -> KnowledgePackSourceChecksumRow:
    return KnowledgePackSourceChecksumRow(
        pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-v1",
        source_document_id=source.source_document_id,
        asset_ticker=ticker,
        checksum=source_record.checksum,
        freshness_state=source_record.freshness_state.value,
        cache_allowed=source.permitted_operations.can_cache,
        export_allowed=source.permitted_operations.can_export_metadata,
        allowlist_status=source.allowlist_status.value,
        source_use_policy=source.source_use_policy.value,
        source_type=source.source_type,
        source_rank=source.source_rank,
        source_identity=getattr(source, "source_identity", None) or source.url or source.source_document_id,
        retrieved_at=source.retrieved_at,
        as_of_date=source.as_of_date,
        published_at=source.published_at,
        is_official=source.is_official,
        source_quality=source.source_quality.value,
        storage_rights=getattr(source, "storage_rights", SourceStorageRights.raw_snapshot_allowed).value,
        export_rights=getattr(source, "export_rights", SourceExportRights.excerpts_allowed).value,
        review_status=getattr(source, "review_status", SourceReviewStatus.approved).value,
        approval_rationale=getattr(
            source,
            "approval_rationale",
            "Deterministic fixture source passed local source-use policy review.",
        ),
        parser_status=getattr(source, "parser_status", SourceParserStatus.parsed).value,
        parser_failure_diagnostics=getattr(source, "parser_failure_diagnostics", None),
    )


def _chunk_row_from_provider_fact(
    ticker: str,
    fact: Any,
    source: Any,
    chunk_id: str,
) -> KnowledgePackSourceChunkRow:
    stored_text, text_storage_policy = _stored_provider_excerpt(
        source.source_use_policy,
        f"{fact.field_name}: {_json_safe(fact.value)}",
    )
    return KnowledgePackSourceChunkRow(
        pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-v1",
        chunk_id=chunk_id,
        asset_ticker=ticker,
        source_document_id=source.source_document_id,
        section_name=fact.data_category.value,
        chunk_order=0,
        token_count=len((stored_text or fact.field_name).split()),
        supported_claim_types=[fact.field_name],
        citation_ids=list(fact.citation_ids),
        source_use_policy=source.source_use_policy.value,
        text_storage_policy=text_storage_policy,
        stored_text=stored_text,
    )


def _chunk_row_from_provider_recent(ticker: str, recent: Any, source: Any, chunk_id: str) -> KnowledgePackSourceChunkRow:
    stored_text, text_storage_policy = _stored_provider_excerpt(
        source.source_use_policy,
        f"{recent.event_type}: {recent.title}. {recent.summary}",
    )
    return KnowledgePackSourceChunkRow(
        pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-v1",
        chunk_id=chunk_id,
        asset_ticker=ticker,
        source_document_id=source.source_document_id,
        section_name="weekly_news_focus",
        chunk_order=0,
        token_count=len((stored_text or recent.event_type).split()),
        supported_claim_types=[recent.event_type],
        citation_ids=list(recent.citation_ids),
        source_use_policy=source.source_use_policy.value,
        text_storage_policy=text_storage_policy,
        stored_text=stored_text,
    )


def _fact_row_from_provider_fact(
    ticker: str,
    fact: Any,
    source_document_id: str,
    chunk_id: str,
) -> KnowledgePackFactRow:
    return KnowledgePackFactRow(
        pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-v1",
        fact_id=fact.fact_id,
        asset_ticker=ticker,
        fact_type=fact.data_category.value,
        field_name=fact.field_name,
        value=fact.value,
        unit=fact.unit,
        period=None,
        as_of_date=fact.as_of_date,
        source_document_id=source_document_id,
        source_chunk_id=chunk_id,
        extraction_method="deterministic_provider_fixture",
        confidence=1.0,
        freshness_state=fact.freshness_state.value,
        evidence_state=fact.evidence_state.value,
        citation_ids=list(fact.citation_ids),
    )


def _recent_row_from_provider_recent(
    ticker: str,
    recent: Any,
    chunk_id: str,
    evidence_state: str,
) -> KnowledgePackRecentDevelopmentRow:
    return KnowledgePackRecentDevelopmentRow(
        pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-v1",
        event_id=recent.event_id,
        asset_ticker=ticker,
        event_type=recent.event_type,
        title=recent.title,
        summary=recent.summary,
        event_date=recent.event_date,
        source_document_id=recent.source_document_id,
        source_chunk_id=chunk_id,
        importance_score=1.0 if recent.is_high_signal else 0.0,
        freshness_state=recent.freshness_state.value,
        evidence_state=evidence_state,
        citation_ids=list(recent.citation_ids),
    )


def _gap_row_from_provider_fact(ticker: str, fact: Any) -> KnowledgePackEvidenceGapRow:
    evidence_state = _enum_value(fact.evidence_state)
    if evidence_state not in _GAP_STATES:
        evidence_state = "insufficient_evidence"
    source_document_id = fact.source_document_ids[0] if fact.source_document_ids else None
    return KnowledgePackEvidenceGapRow(
        pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-v1",
        gap_id=f"gap_{fact.fact_id}",
        asset_ticker=ticker,
        field_name=fact.field_name,
        evidence_state=evidence_state,
        freshness_state=fact.freshness_state.value,
        source_document_id=source_document_id,
        message="Acquisition metadata did not verify this field as supported evidence.",
    )


def _gap_rows_from_acquisition_diagnostics(ticker: str, acquisition: Any) -> list[KnowledgePackEvidenceGapRow]:
    rows: list[KnowledgePackEvidenceGapRow] = []
    for index, diagnostic in enumerate(getattr(acquisition, "diagnostics", ())):
        evidence_state = _enum_value(getattr(diagnostic, "evidence_state", None))
        if evidence_state not in _GAP_STATES:
            evidence_state = "partial"
        code = str(getattr(diagnostic, "code", f"diagnostic_{index + 1}"))
        rows.append(
            KnowledgePackEvidenceGapRow(
                pack_id=f"asset-knowledge-pack-{ticker.lower()}-acquisition-v1",
                gap_id=f"gap_{ticker.lower()}_{code}_{index + 1}",
                asset_ticker=ticker,
                field_name=code,
                evidence_state=evidence_state,
                freshness_state=_enum_value(getattr(diagnostic, "freshness_state", None)) or FreshnessState.unknown.value,
                message=_sanitize_gap_message(str(getattr(diagnostic, "message", "Evidence gap reported."))),
            )
        )
    return rows


def _section_rows_from_acquisition(
    ticker: str,
    *,
    freshness: Any,
    source_rows: list[KnowledgePackSourceDocumentRow],
    fact_rows: list[KnowledgePackFactRow],
    recent_rows: list[KnowledgePackRecentDevelopmentRow],
    gap_rows: list[KnowledgePackEvidenceGapRow],
) -> list[KnowledgePackSectionFreshnessRow]:
    pack_id = f"asset-knowledge-pack-{ticker.lower()}-acquisition-v1"
    facts_as_of = freshness.as_of_date
    retrieved_at = freshness.retrieved_at
    rows = [
        KnowledgePackSectionFreshnessRow(
            pack_id=pack_id,
            section_id="page",
            freshness_state=freshness.freshness_state.value,
            evidence_state="supported",
            as_of_date=facts_as_of,
            retrieved_at=retrieved_at,
        ),
        KnowledgePackSectionFreshnessRow(
            pack_id=pack_id,
            section_id="source_documents",
            freshness_state=_combined_row_freshness([row.freshness_state for row in source_rows]),
            evidence_state="supported" if source_rows else "unavailable",
            retrieved_at=retrieved_at,
        ),
        KnowledgePackSectionFreshnessRow(
            pack_id=pack_id,
            section_id="canonical_facts",
            freshness_state=_combined_row_freshness([row.freshness_state for row in fact_rows]),
            evidence_state="supported" if fact_rows else "unavailable",
            as_of_date=facts_as_of,
            retrieved_at=retrieved_at,
        ),
        KnowledgePackSectionFreshnessRow(
            pack_id=pack_id,
            section_id="weekly_news_focus",
            freshness_state=_combined_row_freshness([row.freshness_state for row in recent_rows]),
            evidence_state="supported" if recent_rows else "no_high_signal",
            retrieved_at=retrieved_at,
        ),
        KnowledgePackSectionFreshnessRow(
            pack_id=pack_id,
            section_id="ai_comprehensive_analysis",
            freshness_state=freshness.freshness_state.value,
            evidence_state="insufficient_evidence",
            retrieved_at=retrieved_at,
        ),
    ]
    if gap_rows:
        rows.append(
            KnowledgePackSectionFreshnessRow(
                pack_id=pack_id,
                section_id="evidence_gaps",
                freshness_state=_combined_row_freshness([row.freshness_state for row in gap_rows]),
                evidence_state="mixed",
                retrieved_at=retrieved_at,
            )
        )
    return sorted(rows, key=lambda row: row.section_id)


def _acquisition_pack_freshness_hash(
    ticker: str,
    *,
    checksum_rows: list[KnowledgePackSourceChecksumRow],
    fact_rows: list[KnowledgePackFactRow],
    recent_rows: list[KnowledgePackRecentDevelopmentRow],
    gap_rows: list[KnowledgePackEvidenceGapRow],
    section_rows: list[KnowledgePackSectionFreshnessRow],
) -> str:
    payload = {
        "ticker": ticker,
        "checksums": [
            {
                "source_document_id": row.source_document_id,
                "checksum": row.checksum,
                "source_use_policy": row.source_use_policy,
                "freshness_state": row.freshness_state,
            }
            for row in checksum_rows
        ],
        "facts": [
            {
                "fact_id": row.fact_id,
                "field_name": row.field_name,
                "as_of_date": row.as_of_date,
                "source_document_id": row.source_document_id,
                "citation_ids": row.citation_ids,
            }
            for row in fact_rows
        ],
        "recents": [row.model_dump(mode="json") for row in recent_rows],
        "gaps": [row.model_dump(mode="json") for row in gap_rows],
        "sections": [row.model_dump(mode="json") for row in section_rows],
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}"


def _primary_source_id(item_id: str, source_document_ids: list[str], source_by_id: dict[str, Any]) -> str:
    source_id = source_document_ids[0]
    if source_id not in source_by_id:
        raise KnowledgePackRepositoryContractError(f"{item_id} references an unknown provider source document.")
    return source_id


def _stored_provider_excerpt(source_use_policy: SourceUsePolicy, text: str) -> tuple[str | None, str]:
    if source_use_policy in _TEXT_BLOCKED_POLICIES:
        return None, source_use_policy.value
    if source_use_policy is SourceUsePolicy.rejected:
        return None, "rejected"
    if source_use_policy is SourceUsePolicy.summary_allowed:
        return _truncate_words(text, 80), "allowed_excerpt"
    return text, "raw_text_allowed"


def _combined_row_freshness(states: list[str]) -> str:
    if not states:
        return FreshnessState.unavailable.value
    for state in [FreshnessState.unavailable.value, FreshnessState.unknown.value, FreshnessState.stale.value]:
        if state in states:
            return state
    return FreshnessState.fresh.value


def _json_safe(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sanitize_gap_message(message: str) -> str:
    lowered = message.lower()
    forbidden = ("secret", "password", "token", "provider payload", "raw text", "raw source")
    if any(marker in lowered for marker in forbidden):
        return "Sanitized acquisition evidence gap."
    return message[:240]


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", value)


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
        source_identity=source.source_identity,
        storage_rights=source.storage_rights.value,
        export_rights=source.export_rights.value,
        review_status=source.review_status.value,
        approval_rationale=source.approval_rationale,
        parser_status=source.parser_status.value,
        parser_failure_diagnostics=source.parser_failure_diagnostics,
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
        source_identity=checksum.source_identity or checksum.source_document_id,
        retrieved_at=checksum.retrieved_at,
        as_of_date=checksum.as_of_date,
        published_at=checksum.published_at,
        is_official=checksum.is_official,
        source_quality=checksum.source_quality.value,
        storage_rights=checksum.storage_rights.value,
        export_rights=checksum.export_rights.value,
        review_status=checksum.review_status.value,
        approval_rationale=checksum.approval_rationale,
        parser_status=checksum.parser_status.value,
        parser_failure_diagnostics=checksum.parser_failure_diagnostics,
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
        source_identity=row.source_identity,
        storage_rights=SourceStorageRights(row.storage_rights),
        export_rights=SourceExportRights(row.export_rights),
        review_status=SourceReviewStatus(row.review_status),
        approval_rationale=row.approval_rationale,
        parser_status=SourceParserStatus(row.parser_status),
        parser_failure_diagnostics=row.parser_failure_diagnostics,
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
        source_identity=row.source_identity,
        retrieved_at=row.retrieved_at,
        as_of_date=row.as_of_date,
        published_at=row.published_at,
        is_official=row.is_official,
        source_quality=SourceQuality(row.source_quality),
        storage_rights=SourceStorageRights(row.storage_rights),
        export_rights=SourceExportRights(row.export_rights),
        review_status=SourceReviewStatus(row.review_status),
        approval_rationale=row.approval_rationale,
        parser_status=SourceParserStatus(row.parser_status),
        parser_failure_diagnostics=row.parser_failure_diagnostics,
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

    for source in records.source_documents:
        _require_same_asset(ticker, source.asset_ticker, source.source_document_id)
        if source.source_type.lower() in {"hidden", "internal", "hidden_internal"}:
            raise KnowledgePackRepositoryContractError("Hidden/internal sources cannot create knowledge-pack evidence.")

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
            handoff = validate_source_handoff(source, action=SourcePolicyAction.generated_claim_support)
            if not handoff.allowed:
                raise KnowledgePackRepositoryContractError(
                    f"Source {source.source_document_id} failed Golden Asset Source Handoff: "
                    + ", ".join(handoff.reason_codes)
                )

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
        handoff = validate_source_handoff(checksum, action=SourcePolicyAction.cacheable_generated_output)
        if records.envelope.generated_output_available and not handoff.allowed:
            raise KnowledgePackRepositoryContractError(
                f"Checksum {checksum.source_document_id} failed Golden Asset Source Handoff: "
                + ", ".join(handoff.reason_codes)
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


def _persist_records(
    session: Any,
    *,
    collection: str,
    key: str,
    records: KnowledgePackRepositoryRecords,
    rows: list[StrictRow],
    commit_on_write: bool,
) -> None:
    if hasattr(session, "save_repository_record"):
        session.save_repository_record(collection, key, records.model_copy(deep=True))
    elif hasattr(session, "save"):
        session.save(collection, key, records.model_copy(deep=True))
    elif hasattr(session, "add_all"):
        session.add_all(rows)
    else:
        raise KnowledgePackRepositoryContractError(
            "Injected repository session must expose save_repository_record(collection, key, records), save(...), or add_all(records)."
        )
    if commit_on_write and hasattr(session, "commit"):
        session.commit()


def _read_records(session: Any, collection: str, key: str) -> Any | None:
    if hasattr(session, "get_repository_record"):
        return session.get_repository_record(collection, key)
    if hasattr(session, "read_repository_record"):
        return session.read_repository_record(collection, key)
    if hasattr(session, "get"):
        return session.get(collection, key)
    return None
