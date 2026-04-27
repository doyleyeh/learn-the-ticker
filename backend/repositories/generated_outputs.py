from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from backend.models import (
    CacheEntryKind,
    CacheEntryMetadata,
    CacheScope,
    FreshnessState,
    GeneratedOutputFreshnessInput,
    KnowledgePackFreshnessInput,
    SectionFreshnessInput,
    SourceAllowlistStatus,
    SourceChecksumRecord,
    SourceExportRights,
    SourceParserStatus,
    SourceQuality,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
)
from backend.repositories.knowledge_packs import RepositoryMetadata, RepositoryTableDefinition, StrictRow
from backend.source_policy import SourcePolicyAction, validate_source_handoff


GENERATED_OUTPUT_CACHE_REPOSITORY_BOUNDARY = "generated-output-cache-repository-contract-v1"
GENERATED_OUTPUT_CACHE_TABLES = (
    "generated_output_cache_envelopes",
    "generated_output_cache_artifacts",
    "generated_output_cache_source_checksums",
    "generated_output_cache_knowledge_pack_hash_inputs",
    "generated_output_cache_freshness_hash_inputs",
    "generated_output_cache_validation_statuses",
    "generated_output_cache_diagnostics",
)

_BLOCKED_SUPPORT_STATES = {
    "unsupported",
    "out_of_scope",
    "eligible_not_cached",
    "unknown",
    "unavailable",
    "pending_ingestion",
}
_BLOCKED_VALIDATION_STATES = {
    "validation_failed",
    "failed",
    "advice_like",
    "source_policy_disallowed",
    "rejected_source",
    "uncited_important_claim",
    "wrong_asset",
    "wrong_pack",
    "wrong_comparison_pack",
    "permission_limited",
}
_ALLOWED_VALIDATION_STATES = {"passed", "valid", "allowed", "educational"}
_TEXT_LIMITED_POLICIES = {
    SourceUsePolicy.metadata_only.value,
    SourceUsePolicy.link_only.value,
    SourceUsePolicy.rejected.value,
}


class GeneratedOutputCacheContractError(ValueError):
    """Raised when a generated-output cache record would break cacheability rules."""


class GeneratedOutputScopeKind(str, Enum):
    asset = "asset"
    comparison = "comparison"


class GeneratedOutputArtifactCategory(str, Enum):
    asset_overview_section = "asset_overview_section"
    comparison_output = "comparison_output"
    grounded_chat_answer_artifact = "grounded_chat_answer_artifact"
    export_payload_metadata = "export_payload_metadata"
    source_list_export_metadata = "source_list_export_metadata"
    source_checksum_record = "source_checksum_record"
    knowledge_pack_hash_input = "knowledge_pack_hash_input"
    generated_output_hash_input = "generated_output_hash_input"
    diagnostics_metadata = "diagnostics_metadata"
    weekly_news_focus_section = "weekly_news_focus_section"
    ai_comprehensive_analysis_artifact = "ai_comprehensive_analysis_artifact"


class GeneratedOutputDiagnosticCategory(str, Enum):
    invalidation = "invalidation"
    validation = "validation"
    source_policy = "source_policy"
    freshness = "freshness"
    citation_binding = "citation_binding"
    safety = "safety"


class GeneratedOutputCacheEnvelopeRow(StrictRow):
    cache_entry_id: str
    cache_key: str
    schema_version: str
    entry_kind: str
    cache_scope: str
    scope_kind: str
    artifact_category: str
    output_identity: str
    mode_or_output_type: str
    asset_ticker: str | None = None
    comparison_id: str | None = None
    comparison_left_ticker: str | None = None
    comparison_right_ticker: str | None = None
    prompt_version: str | None = None
    model_name: str | None = None
    deterministic_mock_marker: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    source_checksum_ids: list[str] = Field(default_factory=list)
    knowledge_pack_freshness_hash: str | None = None
    generated_output_freshness_hash: str
    validation_status: str
    citation_validation_status: str
    safety_status: str
    source_use_status: str
    citation_coverage_status: str
    source_freshness_states: dict[str, str] = Field(default_factory=dict)
    section_freshness_labels: dict[str, str] = Field(default_factory=dict)
    evidence_state_labels: dict[str, str] = Field(default_factory=dict)
    support_status: str = "supported"
    evidence_state: str = "supported"
    cache_state: str = "available"
    cacheable: bool
    generated_output_available: bool
    created_at: str
    expires_at: str | None = None
    ttl_seconds: int | None = None
    invalidation_reasons: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    no_live_external_calls: bool = True
    live_database_execution: bool = False
    live_cache_execution: bool = False
    provider_or_llm_call_required: bool = False
    stores_generated_payload: bool = False
    stores_raw_source_text: bool = False
    stores_raw_provider_payload: bool = False
    stores_hidden_prompt: bool = False
    stores_raw_model_reasoning: bool = False
    stores_raw_user_text: bool = False
    stores_chat_transcript: bool = False
    stores_secret: bool = False

    @field_validator("entry_kind")
    @classmethod
    def _valid_entry_kind(cls, value: str) -> str:
        CacheEntryKind(value)
        return value

    @field_validator("cache_scope")
    @classmethod
    def _valid_cache_scope(cls, value: str) -> str:
        CacheScope(value)
        return value

    @field_validator("scope_kind")
    @classmethod
    def _valid_scope_kind(cls, value: str) -> str:
        GeneratedOutputScopeKind(value)
        return value

    @field_validator("artifact_category")
    @classmethod
    def _valid_artifact_category(cls, value: str) -> str:
        GeneratedOutputArtifactCategory(value)
        return value


class GeneratedOutputArtifactRecordRow(StrictRow):
    artifact_id: str
    cache_entry_id: str
    artifact_category: str
    content_format: str
    output_checksum: str
    byte_size: int = 0
    source_document_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    section_freshness_labels: dict[str, str] = Field(default_factory=dict)
    payload_metadata: dict[str, Any] = Field(default_factory=dict)
    stores_payload_text: bool = False
    stores_raw_user_text: bool = False
    stores_chat_transcript: bool = False
    stores_hidden_prompt: bool = False
    stores_raw_model_reasoning: bool = False
    stores_raw_source_text: bool = False
    stores_raw_provider_payload: bool = False
    stores_secret: bool = False

    @field_validator("artifact_category")
    @classmethod
    def _valid_artifact_category(cls, value: str) -> str:
        GeneratedOutputArtifactCategory(value)
        return value


class GeneratedOutputSourceChecksumRow(StrictRow):
    cache_entry_id: str
    source_document_id: str
    asset_ticker: str
    checksum: str
    freshness_state: str
    cache_allowed: bool
    export_allowed: bool = False
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


class GeneratedOutputKnowledgePackHashInputRow(StrictRow):
    cache_entry_id: str
    input_id: str
    asset_ticker: str | None = None
    comparison_id: str | None = None
    comparison_left_ticker: str | None = None
    comparison_right_ticker: str | None = None
    pack_identity: str | None = None
    knowledge_pack_freshness_hash: str
    page_freshness_state: str
    source_checksum_hashes: list[str] = Field(default_factory=list)
    canonical_fact_ids: list[str] = Field(default_factory=list)
    recent_event_ids: list[str] = Field(default_factory=list)
    evidence_gap_ids: list[str] = Field(default_factory=list)
    section_freshness_labels: dict[str, str] = Field(default_factory=dict)
    evidence_state_labels: dict[str, str] = Field(default_factory=dict)


class GeneratedOutputFreshnessHashInputRow(StrictRow):
    cache_entry_id: str
    input_id: str
    output_identity: str
    entry_kind: str
    cache_scope: str
    schema_version: str
    prompt_version: str | None = None
    model_name: str | None = None
    generated_output_freshness_hash: str
    source_freshness_state: str
    source_checksum_hashes: list[str] = Field(default_factory=list)
    canonical_fact_ids: list[str] = Field(default_factory=list)
    recent_event_ids: list[str] = Field(default_factory=list)
    evidence_gap_ids: list[str] = Field(default_factory=list)
    section_freshness_labels: dict[str, str] = Field(default_factory=dict)
    evidence_state_labels: dict[str, str] = Field(default_factory=dict)


class GeneratedOutputValidationStatusRow(StrictRow):
    cache_entry_id: str
    validation_id: str
    validation_status: str
    citation_validation_status: str
    safety_status: str
    source_use_status: str
    freshness_status: str
    important_claim_count: int = 0
    cited_important_claim_count: int = 0
    unsupported_claim_count: int = 0
    wrong_asset_citation_count: int = 0
    wrong_pack_citation_count: int = 0
    rejected_source_count: int = 0
    permission_limited_source_count: int = 0
    advice_like_detected: bool = False
    validated_at: str | None = None
    rejection_reason_codes: list[str] = Field(default_factory=list)


class GeneratedOutputDiagnosticRow(StrictRow):
    diagnostic_id: str
    cache_entry_id: str | None = None
    category: str
    code: str
    invalidation_reason: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    checksum_values: list[str] = Field(default_factory=list)
    freshness_states: dict[str, str] = Field(default_factory=dict)
    created_at: str
    compact_metadata: dict[str, Any] = Field(default_factory=dict)
    stores_secret: bool = False
    stores_user_text: bool = False
    stores_provider_payload: bool = False
    stores_raw_source_text: bool = False
    stores_unrestricted_excerpt: bool = False
    stores_hidden_prompt: bool = False
    stores_raw_model_reasoning: bool = False

    @field_validator("category")
    @classmethod
    def _valid_category(cls, value: str) -> str:
        GeneratedOutputDiagnosticCategory(value)
        return value


class GeneratedOutputCacheRepositoryRecords(StrictRow):
    envelopes: list[GeneratedOutputCacheEnvelopeRow] = Field(default_factory=list)
    artifacts: list[GeneratedOutputArtifactRecordRow] = Field(default_factory=list)
    source_checksums: list[GeneratedOutputSourceChecksumRow] = Field(default_factory=list)
    knowledge_pack_hash_inputs: list[GeneratedOutputKnowledgePackHashInputRow] = Field(default_factory=list)
    generated_output_hash_inputs: list[GeneratedOutputFreshnessHashInputRow] = Field(default_factory=list)
    validation_statuses: list[GeneratedOutputValidationStatusRow] = Field(default_factory=list)
    diagnostics: list[GeneratedOutputDiagnosticRow] = Field(default_factory=list)

    @property
    def table_names(self) -> tuple[str, ...]:
        return GENERATED_OUTPUT_CACHE_TABLES


def generated_output_cache_repository_metadata() -> RepositoryMetadata:
    return RepositoryMetadata(
        boundary=GENERATED_OUTPUT_CACHE_REPOSITORY_BOUNDARY,
        table_definitions=(
            RepositoryTableDefinition(
                name="generated_output_cache_envelopes",
                primary_key=("cache_entry_id",),
                columns=tuple(GeneratedOutputCacheEnvelopeRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="generated_output_cache_artifacts",
                primary_key=("artifact_id",),
                columns=tuple(GeneratedOutputArtifactRecordRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="generated_output_cache_source_checksums",
                primary_key=("cache_entry_id", "source_document_id"),
                columns=tuple(GeneratedOutputSourceChecksumRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="generated_output_cache_knowledge_pack_hash_inputs",
                primary_key=("cache_entry_id", "input_id"),
                columns=tuple(GeneratedOutputKnowledgePackHashInputRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="generated_output_cache_freshness_hash_inputs",
                primary_key=("cache_entry_id", "input_id"),
                columns=tuple(GeneratedOutputFreshnessHashInputRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="generated_output_cache_validation_statuses",
                primary_key=("cache_entry_id", "validation_id"),
                columns=tuple(GeneratedOutputValidationStatusRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="generated_output_cache_diagnostics",
                primary_key=("diagnostic_id",),
                columns=tuple(GeneratedOutputDiagnosticRow.model_fields),
            ),
        ),
    )


@dataclass
class GeneratedOutputCacheRepository:
    session: Any | None = None
    commit_on_write: bool = False

    def validate(self, records: GeneratedOutputCacheRepositoryRecords) -> GeneratedOutputCacheRepositoryRecords:
        return validate_generated_output_cache_records(records)

    def persist(self, records: GeneratedOutputCacheRepositoryRecords) -> GeneratedOutputCacheRepositoryRecords:
        validated = validate_generated_output_cache_records(records)
        if self.session is None:
            return validated
        envelope = validated.envelopes[0]
        for collection, key in _cache_record_keys(envelope):
            _persist_records(
                self.session,
                collection=collection,
                key=key,
                records=validated,
                rows=records_to_row_list(validated),
                commit_on_write=self.commit_on_write,
            )
        return validated

    def read_asset_overview_records(self, ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        return self._asset_record(ticker, GeneratedOutputArtifactCategory.asset_overview_section)

    def read_chat_answer_records(self, ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        return self._asset_record(ticker, GeneratedOutputArtifactCategory.grounded_chat_answer_artifact)

    def read_export_records(self, ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        return self._asset_record(ticker, GeneratedOutputArtifactCategory.export_payload_metadata)

    def read_source_list_records(self, ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        return self._asset_record(ticker, GeneratedOutputArtifactCategory.source_list_export_metadata)

    def read_comparison_records(self, left_ticker: str, right_ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        return self._comparison_record(left_ticker, right_ticker, GeneratedOutputArtifactCategory.comparison_output)

    def read_generated_output_cache_records(self, *args: str) -> GeneratedOutputCacheRepositoryRecords | None:
        if len(args) == 1:
            return self.read_asset_overview_records(args[0]) or self.read_chat_answer_records(args[0])
        if len(args) == 2:
            return self.read_comparison_records(args[0], args[1])
        raise GeneratedOutputCacheContractError("Generated-output cache reads require one asset or two comparison tickers.")

    def _asset_record(
        self,
        ticker: str,
        category: GeneratedOutputArtifactCategory,
    ) -> GeneratedOutputCacheRepositoryRecords | None:
        return _read_cache_records(self.session, _asset_key(ticker, category)) if self.session is not None else None

    def _comparison_record(
        self,
        left_ticker: str,
        right_ticker: str,
        category: GeneratedOutputArtifactCategory,
    ) -> GeneratedOutputCacheRepositoryRecords | None:
        return (
            _read_cache_records(self.session, _comparison_key(left_ticker, right_ticker, category))
            if self.session is not None
            else None
        )


@dataclass
class InMemoryGeneratedOutputCacheRepository:
    records_by_entry_id: dict[str, GeneratedOutputCacheRepositoryRecords] = Field(default_factory=dict)
    records_by_asset_category: dict[tuple[str, str], GeneratedOutputCacheRepositoryRecords] = Field(default_factory=dict)
    records_by_comparison_category: dict[tuple[str, str, str], GeneratedOutputCacheRepositoryRecords] = Field(default_factory=dict)

    def __init__(self) -> None:
        self.records_by_entry_id = {}
        self.records_by_asset_category = {}
        self.records_by_comparison_category = {}

    def persist(self, records: GeneratedOutputCacheRepositoryRecords) -> GeneratedOutputCacheRepositoryRecords:
        validated = validate_generated_output_cache_records(records).model_copy(deep=True)
        envelope = validated.envelopes[0]
        self.records_by_entry_id[envelope.cache_entry_id] = validated
        if envelope.scope_kind == GeneratedOutputScopeKind.asset.value and envelope.asset_ticker:
            self.records_by_asset_category[(envelope.asset_ticker, envelope.artifact_category)] = validated
        if envelope.scope_kind == GeneratedOutputScopeKind.comparison.value:
            self.records_by_comparison_category[
                (envelope.comparison_left_ticker or "", envelope.comparison_right_ticker or "", envelope.artifact_category)
            ] = validated
        return validated.model_copy(deep=True)

    def read_asset_overview_records(self, ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        return self._asset_record(ticker, GeneratedOutputArtifactCategory.asset_overview_section)

    def read_chat_answer_records(self, ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        return self._asset_record(ticker, GeneratedOutputArtifactCategory.grounded_chat_answer_artifact)

    def read_export_records(self, ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        return self._asset_record(ticker, GeneratedOutputArtifactCategory.export_payload_metadata)

    def read_source_list_records(self, ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        return self._asset_record(ticker, GeneratedOutputArtifactCategory.source_list_export_metadata)

    def read_comparison_records(self, left_ticker: str, right_ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        return self._comparison_record(left_ticker, right_ticker, GeneratedOutputArtifactCategory.comparison_output)

    def read_generated_output_cache_records(self, *args: str) -> GeneratedOutputCacheRepositoryRecords | None:
        if len(args) == 1:
            return self.read_asset_overview_records(args[0]) or self.read_chat_answer_records(args[0])
        if len(args) == 2:
            return self.read_comparison_records(args[0], args[1])
        raise GeneratedOutputCacheContractError("In-memory generated-output cache reads require one asset or two comparison tickers.")

    def _asset_record(
        self,
        ticker: str,
        category: GeneratedOutputArtifactCategory,
    ) -> GeneratedOutputCacheRepositoryRecords | None:
        records = self.records_by_asset_category.get((ticker.strip().upper(), category.value))
        return records.model_copy(deep=True) if records else None

    def _comparison_record(
        self,
        left_ticker: str,
        right_ticker: str,
        category: GeneratedOutputArtifactCategory,
    ) -> GeneratedOutputCacheRepositoryRecords | None:
        records = self.records_by_comparison_category.get(
            (left_ticker.strip().upper(), right_ticker.strip().upper(), category.value)
        )
        return records.model_copy(deep=True) if records else None


def persist_generated_output_cache_records(
    writer: Any,
    records: GeneratedOutputCacheRepositoryRecords,
) -> GeneratedOutputCacheRepositoryRecords:
    validated = validate_generated_output_cache_records(records)
    if hasattr(writer, "persist"):
        persisted = writer.persist(validated)
    elif hasattr(writer, "write_generated_output_cache_records"):
        persisted = writer.write_generated_output_cache_records(validated)
    elif hasattr(writer, "save"):
        persisted = writer.save(validated)
    else:
        raise GeneratedOutputCacheContractError(
            "Injected generated-output cache writer must expose persist(records), "
            "write_generated_output_cache_records(records), or save(records)."
        )
    if persisted is None:
        return validated
    return validate_generated_output_cache_records(
        persisted
        if isinstance(persisted, GeneratedOutputCacheRepositoryRecords)
        else GeneratedOutputCacheRepositoryRecords.model_validate(persisted)
    )


def build_generated_output_cache_records(
    *,
    cache_entry_id: str,
    output_identity: str,
    mode_or_output_type: str,
    artifact_category: GeneratedOutputArtifactCategory | str,
    cache_metadata: CacheEntryMetadata,
    generated_freshness_input: GeneratedOutputFreshnessInput,
    knowledge_freshness_input: KnowledgePackFreshnessInput,
    knowledge_pack_freshness_hash: str,
    created_at: str,
    expires_at: str | None = None,
    ttl_seconds: int | None = None,
    asset_ticker: str | None = None,
    comparison_id: str | None = None,
    comparison_left_ticker: str | None = None,
    comparison_right_ticker: str | None = None,
    deterministic_mock_marker: str | None = "deterministic-fixture-model",
) -> GeneratedOutputCacheRepositoryRecords:
    category = GeneratedOutputArtifactCategory(artifact_category)
    scope_kind = (
        GeneratedOutputScopeKind.comparison
        if generated_freshness_input.scope is CacheScope.comparison
        else GeneratedOutputScopeKind.asset
    )
    envelope = GeneratedOutputCacheEnvelopeRow(
        cache_entry_id=cache_entry_id,
        cache_key=cache_metadata.cache_key,
        schema_version=cache_metadata.schema_version,
        entry_kind=cache_metadata.entry_kind.value,
        cache_scope=cache_metadata.scope.value,
        scope_kind=scope_kind.value,
        artifact_category=category.value,
        output_identity=output_identity,
        mode_or_output_type=mode_or_output_type,
        asset_ticker=(asset_ticker or knowledge_freshness_input.asset_ticker or None),
        comparison_id=(comparison_id or knowledge_freshness_input.pack_identity)
        if scope_kind is GeneratedOutputScopeKind.comparison
        else None,
        comparison_left_ticker=comparison_left_ticker or knowledge_freshness_input.comparison_left_ticker,
        comparison_right_ticker=comparison_right_ticker or knowledge_freshness_input.comparison_right_ticker,
        prompt_version=cache_metadata.prompt_version,
        model_name=cache_metadata.model_name,
        deterministic_mock_marker=deterministic_mock_marker,
        source_document_ids=cache_metadata.source_document_ids,
        citation_ids=cache_metadata.citation_ids,
        section_ids=sorted(cache_metadata.section_freshness_labels),
        source_checksum_ids=sorted(cache_metadata.source_checksum_hashes),
        knowledge_pack_freshness_hash=knowledge_pack_freshness_hash,
        generated_output_freshness_hash=cache_metadata.generated_output_freshness_hash or "",
        validation_status="passed",
        citation_validation_status="passed",
        safety_status="educational",
        source_use_status="allowed",
        citation_coverage_status="complete",
        source_freshness_states=_enum_map_to_text(cache_metadata.source_freshness_states),
        section_freshness_labels=_enum_map_to_text(cache_metadata.section_freshness_labels),
        evidence_state_labels=_section_evidence_labels(generated_freshness_input.section_freshness_labels),
        cacheable=cache_metadata.cache_allowed,
        generated_output_available=cache_metadata.cache_allowed,
        created_at=created_at,
        expires_at=expires_at or cache_metadata.expires_at,
        ttl_seconds=ttl_seconds,
        invalidation_reasons=[],
        blocked_reasons=[],
    )
    records = GeneratedOutputCacheRepositoryRecords(
        envelopes=[envelope],
        artifacts=[
            GeneratedOutputArtifactRecordRow(
                artifact_id=f"{cache_entry_id}:metadata",
                cache_entry_id=cache_entry_id,
                artifact_category=category.value,
                content_format="metadata",
                output_checksum=cache_metadata.generated_output_freshness_hash or "",
                source_document_ids=cache_metadata.source_document_ids,
                citation_ids=cache_metadata.citation_ids,
                section_freshness_labels=_enum_map_to_text(cache_metadata.section_freshness_labels),
                payload_metadata={
                    "entry_kind": cache_metadata.entry_kind.value,
                    "scope": cache_metadata.scope.value,
                    "schema_version": cache_metadata.schema_version,
                },
            )
        ],
        source_checksums=[
            _source_checksum_row(cache_entry_id, checksum) for checksum in generated_freshness_input.source_checksums
        ],
        knowledge_pack_hash_inputs=[
            _knowledge_hash_row(cache_entry_id, "knowledge-pack-input", knowledge_freshness_input, knowledge_pack_freshness_hash)
        ],
        generated_output_hash_inputs=[
            _generated_hash_row(
                cache_entry_id,
                "generated-output-input",
                generated_freshness_input,
                cache_metadata.generated_output_freshness_hash or "",
            )
        ],
        validation_statuses=[
            GeneratedOutputValidationStatusRow(
                cache_entry_id=cache_entry_id,
                validation_id=f"{cache_entry_id}:validation",
                validation_status="passed",
                citation_validation_status="passed",
                safety_status="educational",
                source_use_status="allowed",
                freshness_status="labeled",
                important_claim_count=len(cache_metadata.citation_ids),
                cited_important_claim_count=len(cache_metadata.citation_ids),
                unsupported_claim_count=0,
                validated_at=created_at,
            )
        ],
    )
    return validate_generated_output_cache_records(records)


def validate_generated_output_cache_records(
    records: GeneratedOutputCacheRepositoryRecords,
) -> GeneratedOutputCacheRepositoryRecords:
    envelope_ids = _unique("generated-output cache entry IDs", [row.cache_entry_id for row in records.envelopes])
    artifact_ids = _unique("generated-output artifact IDs", [row.artifact_id for row in records.artifacts])
    _unique("generated-output diagnostics IDs", [row.diagnostic_id for row in records.diagnostics])

    for artifact in records.artifacts:
        if artifact.cache_entry_id not in envelope_ids:
            raise GeneratedOutputCacheContractError("Generated-output artifacts must reference known cache entries.")
        _validate_artifact(artifact)

    for diagnostic in records.diagnostics:
        if diagnostic.cache_entry_id and diagnostic.cache_entry_id not in envelope_ids:
            raise GeneratedOutputCacheContractError("Generated-output diagnostics must reference known cache entries.")
        _validate_diagnostic(diagnostic)

    rows_by_entry = {
        entry_id: _RowsForEntry(
            envelope=_envelope_by_id(records, entry_id),
            source_checksums=[row for row in records.source_checksums if row.cache_entry_id == entry_id],
            knowledge_inputs=[row for row in records.knowledge_pack_hash_inputs if row.cache_entry_id == entry_id],
            generated_inputs=[row for row in records.generated_output_hash_inputs if row.cache_entry_id == entry_id],
            validations=[row for row in records.validation_statuses if row.cache_entry_id == entry_id],
        )
        for entry_id in envelope_ids
    }

    for row_group in rows_by_entry.values():
        _validate_envelope_group(row_group)

    if artifact_ids:
        pass
    return records


def records_to_row_list(records: GeneratedOutputCacheRepositoryRecords) -> list[StrictRow]:
    validate_generated_output_cache_records(records)
    return [
        *records.envelopes,
        *records.artifacts,
        *records.source_checksums,
        *records.knowledge_pack_hash_inputs,
        *records.generated_output_hash_inputs,
        *records.validation_statuses,
        *records.diagnostics,
    ]


@dataclass(frozen=True)
class _RowsForEntry:
    envelope: GeneratedOutputCacheEnvelopeRow
    source_checksums: list[GeneratedOutputSourceChecksumRow]
    knowledge_inputs: list[GeneratedOutputKnowledgePackHashInputRow]
    generated_inputs: list[GeneratedOutputFreshnessHashInputRow]
    validations: list[GeneratedOutputValidationStatusRow]


def _validate_envelope_group(rows: _RowsForEntry) -> None:
    envelope = rows.envelope
    _validate_scope_binding(envelope)
    _validate_no_live_or_raw_payload_surface(envelope)
    _validate_compact_metadata({"blocked_reasons": envelope.blocked_reasons, "invalidation_reasons": envelope.invalidation_reasons})

    if not envelope.generated_output_freshness_hash:
        raise GeneratedOutputCacheContractError("Generated-output cache records require a freshness hash.")
    if envelope.ttl_seconds is not None and envelope.ttl_seconds < 0:
        raise GeneratedOutputCacheContractError("Generated-output TTL metadata cannot be negative.")

    source_ids = {row.source_document_id for row in rows.source_checksums}
    if set(envelope.source_document_ids) != source_ids:
        raise GeneratedOutputCacheContractError("Generated-output source checksum rows must match envelope source IDs.")
    if envelope.source_checksum_ids and envelope.source_checksum_ids != sorted({row.checksum for row in rows.source_checksums}):
        raise GeneratedOutputCacheContractError("Generated-output checksum IDs must match source checksum rows.")

    validation = _single_validation(rows.validations, envelope.cache_entry_id)
    _validate_validation_status(validation)
    _validate_hash_inputs(rows, envelope)
    _validate_sources(rows.source_checksums, envelope)
    _validate_freshness_labels(rows, envelope)
    _validate_citation_bindings(rows.source_checksums, envelope, validation)
    _validate_cacheability(envelope, validation)


def _validate_scope_binding(envelope: GeneratedOutputCacheEnvelopeRow) -> None:
    if envelope.scope_kind == GeneratedOutputScopeKind.asset.value:
        if not envelope.asset_ticker:
            raise GeneratedOutputCacheContractError("Asset-scoped generated-output cache rows require one asset ticker.")
        if envelope.comparison_id or envelope.comparison_left_ticker or envelope.comparison_right_ticker:
            raise GeneratedOutputCacheContractError("Asset-scoped generated-output cache rows cannot also bind a comparison pack.")
    else:
        if not envelope.comparison_id or not envelope.comparison_left_ticker or not envelope.comparison_right_ticker:
            raise GeneratedOutputCacheContractError("Comparison-scoped generated-output cache rows require a comparison pack and both tickers.")
        if envelope.asset_ticker:
            raise GeneratedOutputCacheContractError("Comparison-scoped generated-output cache rows cannot also bind one asset.")
        if envelope.comparison_left_ticker == envelope.comparison_right_ticker:
            raise GeneratedOutputCacheContractError("Comparison cache rows require distinct left and right tickers.")


def _validate_cacheability(
    envelope: GeneratedOutputCacheEnvelopeRow,
    validation: GeneratedOutputValidationStatusRow,
) -> None:
    blocked_status = {
        envelope.support_status,
        envelope.evidence_state,
        envelope.cache_state,
        *envelope.blocked_reasons,
        *validation.rejection_reason_codes,
    }
    if blocked_status & (_BLOCKED_SUPPORT_STATES | _BLOCKED_VALIDATION_STATES):
        if envelope.cacheable or envelope.generated_output_available:
            raise GeneratedOutputCacheContractError("Blocked states cannot expose cacheable generated output.")
        return

    if envelope.cacheable:
        if not envelope.generated_output_available:
            raise GeneratedOutputCacheContractError("Cacheable generated-output records must mark generated output available.")
        for status in (
            envelope.validation_status,
            envelope.citation_validation_status,
            envelope.safety_status,
            envelope.source_use_status,
            envelope.citation_coverage_status,
            validation.validation_status,
            validation.citation_validation_status,
            validation.safety_status,
            validation.source_use_status,
        ):
            if status not in _ALLOWED_VALIDATION_STATES and status != "complete":
                raise GeneratedOutputCacheContractError("Cacheability requires passed validation, safety, source-use, and citation checks.")


def _validate_validation_status(validation: GeneratedOutputValidationStatusRow) -> None:
    if validation.important_claim_count < 0 or validation.cited_important_claim_count < 0:
        raise GeneratedOutputCacheContractError("Generated-output claim counts cannot be negative.")
    if validation.cited_important_claim_count < validation.important_claim_count:
        raise GeneratedOutputCacheContractError("Important factual claims require successful citation validation.")
    if (
        validation.unsupported_claim_count
        or validation.wrong_asset_citation_count
        or validation.wrong_pack_citation_count
        or validation.rejected_source_count
        or validation.permission_limited_source_count
        or validation.advice_like_detected
    ):
        raise GeneratedOutputCacheContractError("Generated-output cacheability requires no unsupported, wrong-boundary, rejected-source, or advice-like output.")


def _validate_hash_inputs(_rows: _RowsForEntry, envelope: GeneratedOutputCacheEnvelopeRow) -> None:
    if not _rows.knowledge_inputs:
        raise GeneratedOutputCacheContractError("Generated-output cache rows require knowledge-pack hash input metadata.")
    if not _rows.generated_inputs:
        raise GeneratedOutputCacheContractError("Generated-output cache rows require generated-output hash input metadata.")
    for knowledge in _rows.knowledge_inputs:
        if knowledge.knowledge_pack_freshness_hash != envelope.knowledge_pack_freshness_hash:
            raise GeneratedOutputCacheContractError("Knowledge-pack hash input rows must match the cache envelope.")
        _validate_hash_scope(knowledge, envelope)
    for generated in _rows.generated_inputs:
        if generated.generated_output_freshness_hash != envelope.generated_output_freshness_hash:
            raise GeneratedOutputCacheContractError("Generated-output hash input rows must match the cache envelope.")
        if generated.entry_kind != envelope.entry_kind or generated.cache_scope != envelope.cache_scope:
            raise GeneratedOutputCacheContractError("Generated-output hash input rows must preserve entry kind and scope.")


def _validate_hash_scope(row: GeneratedOutputKnowledgePackHashInputRow, envelope: GeneratedOutputCacheEnvelopeRow) -> None:
    if envelope.scope_kind == GeneratedOutputScopeKind.asset.value:
        if row.asset_ticker != envelope.asset_ticker:
            raise GeneratedOutputCacheContractError("Knowledge-pack hash asset ticker must match the cache envelope.")
    else:
        if row.comparison_id != envelope.comparison_id:
            raise GeneratedOutputCacheContractError("Knowledge-pack hash comparison pack must match the cache envelope.")
        if row.comparison_left_ticker != envelope.comparison_left_ticker or row.comparison_right_ticker != envelope.comparison_right_ticker:
            raise GeneratedOutputCacheContractError("Knowledge-pack hash rows must preserve comparison left/right identity.")


def _validate_sources(source_rows: list[GeneratedOutputSourceChecksumRow], envelope: GeneratedOutputCacheEnvelopeRow) -> None:
    allowed_tickers = (
        {envelope.asset_ticker}
        if envelope.scope_kind == GeneratedOutputScopeKind.asset.value
        else {envelope.comparison_left_ticker, envelope.comparison_right_ticker}
    )
    for source in source_rows:
        if source.asset_ticker not in allowed_tickers:
            raise GeneratedOutputCacheContractError("Generated-output source rows must bind to the same asset or comparison pack.")
        if not source.cache_allowed:
            raise GeneratedOutputCacheContractError("Source checksum rows must permit cache use before generated output is cacheable.")
        if source.allowlist_status != SourceAllowlistStatus.allowed.value:
            raise GeneratedOutputCacheContractError("Source allowlist status must be allowed for generated-output cacheability.")
        if source.source_use_policy in _TEXT_LIMITED_POLICIES:
            raise GeneratedOutputCacheContractError("Source-use policy must allow generated output before cacheability.")
        handoff = validate_source_handoff(source, action=SourcePolicyAction.cacheable_generated_output)
        if not handoff.allowed:
            raise GeneratedOutputCacheContractError(
                "Generated-output source failed Golden Asset Source Handoff: " + ", ".join(handoff.reason_codes)
            )


def _validate_freshness_labels(rows: _RowsForEntry, envelope: GeneratedOutputCacheEnvelopeRow) -> None:
    source_states = set(envelope.source_freshness_states.values())
    section_states = set(envelope.section_freshness_labels.values())
    evidence_states = set(envelope.evidence_state_labels.values())
    if FreshnessState.unknown.value in source_states and (
        FreshnessState.unknown.value not in section_states and "unknown" not in evidence_states
    ):
        raise GeneratedOutputCacheContractError("Unknown or unavailable source freshness requires explicit section or evidence labels.")
    if FreshnessState.unavailable.value in source_states and (
        FreshnessState.unavailable.value not in section_states and "unavailable" not in evidence_states
    ):
        raise GeneratedOutputCacheContractError("Unknown or unavailable source freshness requires explicit section or evidence labels.")
    if FreshnessState.stale.value in source_states and FreshnessState.stale.value not in section_states:
        raise GeneratedOutputCacheContractError("Stale inputs must be preserved with explicit section freshness labels.")
    if envelope.evidence_state == "partial" and "partial" not in evidence_states:
        raise GeneratedOutputCacheContractError("Partial evidence must be preserved with explicit labels.")
    if envelope.evidence_state == "insufficient_evidence" and "insufficient_evidence" not in evidence_states:
        raise GeneratedOutputCacheContractError("Insufficient evidence must be preserved with explicit labels.")
    for knowledge in rows.knowledge_inputs:
        if knowledge.page_freshness_state in {FreshnessState.unknown.value, FreshnessState.unavailable.value}:
            raise GeneratedOutputCacheContractError("Unknown or unavailable knowledge-pack freshness blocks cacheability.")


def _validate_citation_bindings(
    source_rows: list[GeneratedOutputSourceChecksumRow],
    envelope: GeneratedOutputCacheEnvelopeRow,
    validation: GeneratedOutputValidationStatusRow,
) -> None:
    source_citations = {citation for source in source_rows for citation in source.citation_ids}
    if validation.important_claim_count and not envelope.citation_ids:
        raise GeneratedOutputCacheContractError("Important factual claims require citation IDs.")
    missing = set(envelope.citation_ids) - source_citations
    if missing:
        raise GeneratedOutputCacheContractError("Generated-output citations must bind to same-pack source checksum rows.")


def _validate_no_live_or_raw_payload_surface(envelope: GeneratedOutputCacheEnvelopeRow) -> None:
    if (
        not envelope.no_live_external_calls
        or envelope.live_database_execution
        or envelope.live_cache_execution
        or envelope.provider_or_llm_call_required
    ):
        raise GeneratedOutputCacheContractError("Generated-output cache contracts must stay dormant and import-safe.")
    if (
        envelope.stores_generated_payload
        or envelope.stores_raw_source_text
        or envelope.stores_raw_provider_payload
        or envelope.stores_hidden_prompt
        or envelope.stores_raw_model_reasoning
        or envelope.stores_raw_user_text
        or envelope.stores_chat_transcript
        or envelope.stores_secret
    ):
        raise GeneratedOutputCacheContractError("Generated-output cache records may store metadata only in this contract.")


def _validate_artifact(artifact: GeneratedOutputArtifactRecordRow) -> None:
    _validate_compact_metadata(artifact.payload_metadata)
    if artifact.byte_size < 0:
        raise GeneratedOutputCacheContractError("Generated-output artifact metadata byte size cannot be negative.")
    if (
        artifact.stores_payload_text
        or artifact.stores_raw_user_text
        or artifact.stores_chat_transcript
        or artifact.stores_hidden_prompt
        or artifact.stores_raw_model_reasoning
        or artifact.stores_raw_source_text
        or artifact.stores_raw_provider_payload
        or artifact.stores_secret
    ):
        raise GeneratedOutputCacheContractError("Generated-output artifacts must store metadata only, not generated text, prompts, transcripts, or secrets.")


def _validate_diagnostic(diagnostic: GeneratedOutputDiagnosticRow) -> None:
    _validate_compact_metadata(diagnostic.compact_metadata)
    if (
        diagnostic.stores_secret
        or diagnostic.stores_user_text
        or diagnostic.stores_provider_payload
        or diagnostic.stores_raw_source_text
        or diagnostic.stores_unrestricted_excerpt
        or diagnostic.stores_hidden_prompt
        or diagnostic.stores_raw_model_reasoning
    ):
        raise GeneratedOutputCacheContractError("Generated-output diagnostics must store compact sanitized metadata only.")


def _validate_compact_metadata(metadata: dict[str, Any]) -> None:
    text = repr(metadata).lower()
    forbidden_markers = (
        "api" + "_key",
        "authorization",
        "bearer ",
        "secret",
        "private key",
        "raw_prompt",
        "hidden_prompt",
        "raw_model_reasoning",
        "reasoning_payload",
        "raw_article_text",
        "raw_provider_payload",
        "raw_source_text",
        "raw_user_text",
        "user_question",
        "chat_transcript",
        "transcript",
        "signed_url",
    )
    if any(marker in text for marker in forbidden_markers):
        raise GeneratedOutputCacheContractError("Generated-output diagnostics and payload metadata must be compact and sanitized.")


def _single_validation(
    validations: list[GeneratedOutputValidationStatusRow],
    cache_entry_id: str,
) -> GeneratedOutputValidationStatusRow:
    if len(validations) != 1:
        raise GeneratedOutputCacheContractError("Generated-output cache rows require exactly one validation status row.")
    validation = validations[0]
    if validation.cache_entry_id != cache_entry_id:
        raise GeneratedOutputCacheContractError("Generated-output validation rows must match the cache entry.")
    return validation


def _envelope_by_id(
    records: GeneratedOutputCacheRepositoryRecords,
    cache_entry_id: str,
) -> GeneratedOutputCacheEnvelopeRow:
    for envelope in records.envelopes:
        if envelope.cache_entry_id == cache_entry_id:
            return envelope
    raise GeneratedOutputCacheContractError("Generated-output cache entry is missing its envelope.")


def _unique(label: str, values: list[str]) -> set[str]:
    seen = set(values)
    if len(seen) != len(values):
        raise GeneratedOutputCacheContractError(f"{label} must be unique.")
    return seen


def _source_checksum_row(cache_entry_id: str, checksum: SourceChecksumRecord) -> GeneratedOutputSourceChecksumRow:
    return GeneratedOutputSourceChecksumRow(
        cache_entry_id=cache_entry_id,
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


def _knowledge_hash_row(
    cache_entry_id: str,
    input_id: str,
    knowledge_input: KnowledgePackFreshnessInput,
    knowledge_pack_freshness_hash: str,
) -> GeneratedOutputKnowledgePackHashInputRow:
    return GeneratedOutputKnowledgePackHashInputRow(
        cache_entry_id=cache_entry_id,
        input_id=input_id,
        asset_ticker=knowledge_input.asset_ticker,
        comparison_id=knowledge_input.pack_identity,
        comparison_left_ticker=knowledge_input.comparison_left_ticker,
        comparison_right_ticker=knowledge_input.comparison_right_ticker,
        pack_identity=knowledge_input.pack_identity,
        knowledge_pack_freshness_hash=knowledge_pack_freshness_hash,
        page_freshness_state=knowledge_input.page_freshness_state.value,
        source_checksum_hashes=sorted({checksum.checksum for checksum in knowledge_input.source_checksums}),
        canonical_fact_ids=sorted({fact.fact_id for fact in knowledge_input.canonical_facts}),
        recent_event_ids=sorted({event.event_id for event in knowledge_input.recent_events}),
        evidence_gap_ids=sorted({gap.gap_id for gap in knowledge_input.evidence_gaps}),
        section_freshness_labels=_section_freshness_labels(knowledge_input.section_freshness_labels),
        evidence_state_labels=_section_evidence_labels(knowledge_input.section_freshness_labels),
    )


def _generated_hash_row(
    cache_entry_id: str,
    input_id: str,
    generated_input: GeneratedOutputFreshnessInput,
    generated_output_freshness_hash: str,
) -> GeneratedOutputFreshnessHashInputRow:
    return GeneratedOutputFreshnessHashInputRow(
        cache_entry_id=cache_entry_id,
        input_id=input_id,
        output_identity=generated_input.output_identity,
        entry_kind=generated_input.entry_kind.value,
        cache_scope=generated_input.scope.value,
        schema_version=generated_input.schema_version,
        prompt_version=generated_input.prompt_version,
        model_name=generated_input.model_name,
        generated_output_freshness_hash=generated_output_freshness_hash,
        source_freshness_state=generated_input.source_freshness_state.value,
        source_checksum_hashes=sorted({checksum.checksum for checksum in generated_input.source_checksums}),
        canonical_fact_ids=sorted({fact.fact_id for fact in generated_input.canonical_facts}),
        recent_event_ids=sorted({event.event_id for event in generated_input.recent_events}),
        evidence_gap_ids=sorted({gap.gap_id for gap in generated_input.evidence_gaps}),
        section_freshness_labels=_section_freshness_labels(generated_input.section_freshness_labels),
        evidence_state_labels=_section_evidence_labels(generated_input.section_freshness_labels),
    )


def _enum_map_to_text(values: dict[str, Any]) -> dict[str, str]:
    return {key: value.value if isinstance(value, Enum) else str(value) for key, value in values.items()}


def _section_freshness_labels(labels: list[SectionFreshnessInput]) -> dict[str, str]:
    return {label.section_id: label.freshness_state.value for label in labels}


def _section_evidence_labels(labels: list[SectionFreshnessInput]) -> dict[str, str]:
    return {label.section_id: str(label.evidence_state) for label in labels if label.evidence_state}


def _cache_record_keys(envelope: GeneratedOutputCacheEnvelopeRow) -> tuple[tuple[str, str], ...]:
    keys = [("generated_output_cache_entry", envelope.cache_entry_id)]
    if envelope.scope_kind == GeneratedOutputScopeKind.asset.value and envelope.asset_ticker:
        keys.append(("generated_output_cache_lookup", _asset_key(envelope.asset_ticker, envelope.artifact_category)))
    if envelope.scope_kind == GeneratedOutputScopeKind.comparison.value:
        keys.append(
            (
                "generated_output_cache_lookup",
                _comparison_key(
                    envelope.comparison_left_ticker or "",
                    envelope.comparison_right_ticker or "",
                    envelope.artifact_category,
                ),
            )
        )
    return tuple(keys)


def _asset_key(ticker: str, category: GeneratedOutputArtifactCategory | str) -> str:
    value = category.value if isinstance(category, GeneratedOutputArtifactCategory) else str(category)
    return f"asset:{ticker.strip().upper()}:{value}"


def _comparison_key(left_ticker: str, right_ticker: str, category: GeneratedOutputArtifactCategory | str) -> str:
    value = category.value if isinstance(category, GeneratedOutputArtifactCategory) else str(category)
    return f"comparison:{left_ticker.strip().upper()}:{right_ticker.strip().upper()}:{value}"


def _persist_records(
    session: Any,
    *,
    collection: str,
    key: str,
    records: GeneratedOutputCacheRepositoryRecords,
    rows: list[StrictRow],
    commit_on_write: bool,
) -> None:
    if hasattr(session, "save_repository_record"):
        session.save_repository_record(collection, key, records.model_copy(deep=True))
    elif hasattr(session, "save"):
        session.save(collection, key, records.model_copy(deep=True))
    elif hasattr(session, "add_all"):
        if collection != "generated_output_cache_entry":
            return
        session.add_all(rows)
    else:
        raise GeneratedOutputCacheContractError(
            "Injected generated-output cache session must expose save_repository_record(collection, key, records), save(...), or add_all(records)."
        )
    if commit_on_write and hasattr(session, "commit"):
        session.commit()


def _read_cache_records(session: Any, key: str) -> GeneratedOutputCacheRepositoryRecords | None:
    raw = None
    if hasattr(session, "get_repository_record"):
        raw = session.get_repository_record("generated_output_cache_lookup", key)
    elif hasattr(session, "read_repository_record"):
        raw = session.read_repository_record("generated_output_cache_lookup", key)
    elif hasattr(session, "get"):
        raw = session.get("generated_output_cache_lookup", key)
    if raw is None:
        return None
    records = raw if isinstance(raw, GeneratedOutputCacheRepositoryRecords) else GeneratedOutputCacheRepositoryRecords.model_validate(raw)
    return validate_generated_output_cache_records(records)
