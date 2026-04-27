from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from backend.data import STUB_TIMESTAMP
from backend.models import (
    DEFAULT_ALLOWED_EXCERPT_BEHAVIOR,
    FreshnessState,
    KnowledgePackSourceMetadata,
    SourceAllowlistStatus,
    SourceExportRights,
    SourceOperationPermissions,
    SourceParserStatus,
    SourcePolicyDecision,
    SourcePolicyDecisionState,
    SourceQuality,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
)
from backend.repositories.knowledge_packs import RepositoryMetadata, RepositoryTableDefinition, StrictRow
from backend.source_policy import SourcePolicyAction, source_can_support_generated_output, validate_source_handoff


SOURCE_SNAPSHOT_REPOSITORY_BOUNDARY = "source-snapshot-artifact-repository-contract-v1"
SOURCE_SNAPSHOT_TABLES = (
    "source_snapshot_artifacts",
    "source_snapshot_diagnostics",
)

_RAW_OR_PARSED_CATEGORIES = {"raw_source", "parsed_text"}
_SUMMARY_CATEGORIES = {"metadata", "allowed_excerpt", "summary", "diagnostics_metadata", "generated_artifact_reference"}
_METADATA_ONLY_CATEGORIES = {"metadata", "checksum_metadata", "diagnostics_metadata"}
_BLOCKED_GENERATED_OUTPUT_STATES = {
    "unsupported",
    "out_of_scope",
    "unknown",
    "unavailable",
    "unapproved_pending_ingestion",
    "validation_failed",
    "source_policy_blocked",
    "rejected_source",
}
_SUPPORTED_ACQUISITION_STATE = "supported"


class SourceSnapshotContractError(ValueError):
    """Raised when a source snapshot artifact would break source-use or storage boundaries."""


class SourceSnapshotScopeKind(str, Enum):
    asset = "asset"
    comparison = "comparison"


class SourceSnapshotArtifactCategory(str, Enum):
    raw_source = "raw_source"
    parsed_text = "parsed_text"
    normalized_facts_input = "normalized_facts_input"
    generated_artifact_reference = "generated_artifact_reference"
    diagnostics_metadata = "diagnostics_metadata"
    metadata = "metadata"
    checksum_metadata = "checksum_metadata"
    allowed_excerpt = "allowed_excerpt"
    summary = "summary"


class SourceSnapshotDiagnosticCategory(str, Enum):
    source_policy_blocked = "source_policy_blocked"
    retrieval_unavailable = "retrieval_unavailable"
    checksum_mismatch = "checksum_mismatch"
    parser_failed = "parser_failed"
    validation_failed = "validation_failed"
    unknown = "unknown"


class SourceSnapshotArtifactRow(StrictRow):
    artifact_id: str
    schema_version: str = "source-snapshot-artifact-v1"
    scope_kind: str
    asset_ticker: str | None = None
    comparison_id: str | None = None
    comparison_left_ticker: str | None = None
    comparison_right_ticker: str | None = None
    ingestion_job_id: str | None = None
    source_document_id: str | None = None
    source_reference_id: str | None = None
    source_asset_ticker: str | None = None
    source_comparison_id: str | None = None
    artifact_category: str
    private_object_uri: str | None = None
    storage_key: str | None = None
    checksum: str
    byte_size: int = 0
    content_type: str
    retrieved_at: str | None = None
    created_at: str
    source_use_policy: str
    allowlist_status: str
    source_quality: str
    permitted_operations: dict[str, Any]
    source_type: str = "fixture_source"
    source_identity: str | None = None
    is_official: bool | None = False
    storage_rights: str = SourceStorageRights.raw_snapshot_allowed.value
    export_rights: str = SourceExportRights.excerpts_allowed.value
    review_status: str = SourceReviewStatus.approved.value
    approval_rationale: str = "Deterministic fixture source passed local source-use policy review."
    parser_status: str = SourceParserStatus.parsed.value
    parser_failure_diagnostics: str | None = None
    freshness_state: str
    evidence_state: str
    support_status: str = "supported"
    approval_state: str = "cached_supported"
    validation_state: str = "valid"
    source_policy_state: str = "allowed"
    can_feed_generated_output: bool = False
    can_support_citations: bool = False
    cache_allowed: bool = False
    export_allowed: bool = False
    generated_output_available: bool = False
    no_public_snapshot_access: bool = True
    signed_url_created: bool = False
    browser_readable_storage_path: bool = False
    external_fetch_url_as_storage: bool = False
    raw_text_stored_in_contract: bool = False
    raw_provider_payload_stored: bool = False
    raw_article_text_stored: bool = False
    raw_user_text_stored: bool = False
    unrestricted_source_excerpt_stored: bool = False
    hidden_prompt_stored: bool = False
    raw_model_reasoning_stored: bool = False
    secrets_stored: bool = False
    compact_diagnostics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_category")
    @classmethod
    def _valid_artifact_category(cls, value: str) -> str:
        SourceSnapshotArtifactCategory(value)
        return value

    @field_validator("scope_kind")
    @classmethod
    def _valid_scope_kind(cls, value: str) -> str:
        SourceSnapshotScopeKind(value)
        return value


class SourceSnapshotDiagnosticRow(StrictRow):
    diagnostic_id: str
    artifact_id: str | None = None
    ingestion_job_id: str | None = None
    category: str
    retrieval_status: str | None = None
    retryable: bool = False
    source_policy_ref: str | None = None
    checksum: str | None = None
    occurred_at: str | None = None
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
        SourceSnapshotDiagnosticCategory(value)
        return value


class SourceSnapshotRepositoryRecords(StrictRow):
    artifacts: list[SourceSnapshotArtifactRow] = Field(default_factory=list)
    diagnostics: list[SourceSnapshotDiagnosticRow] = Field(default_factory=list)

    @property
    def table_names(self) -> tuple[str, ...]:
        return SOURCE_SNAPSHOT_TABLES


def source_snapshot_repository_metadata() -> RepositoryMetadata:
    return RepositoryMetadata(
        boundary=SOURCE_SNAPSHOT_REPOSITORY_BOUNDARY,
        table_definitions=(
            RepositoryTableDefinition(
                name="source_snapshot_artifacts",
                primary_key=("artifact_id",),
                columns=tuple(SourceSnapshotArtifactRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="source_snapshot_diagnostics",
                primary_key=("diagnostic_id",),
                columns=tuple(SourceSnapshotDiagnosticRow.model_fields),
            ),
        ),
    )


@dataclass
class SourceSnapshotArtifactRepository:
    session: Any | None = None
    commit_on_write: bool = False

    def validate(self, records: SourceSnapshotRepositoryRecords) -> SourceSnapshotRepositoryRecords:
        return validate_source_snapshot_records(records)

    def persist(self, records: SourceSnapshotRepositoryRecords) -> SourceSnapshotRepositoryRecords:
        validated = validate_source_snapshot_records(records)
        if self.session is None:
            return validated
        _persist_records(
            self.session,
            collection="source_snapshot_artifacts",
            key="source_snapshot_artifacts",
            records=validated,
            rows=records_to_row_list(validated),
            commit_on_write=self.commit_on_write,
        )
        return validated

    def records(self) -> SourceSnapshotRepositoryRecords | None:
        if self.session is None:
            return None
        raw = _read_records(self.session, "source_snapshot_artifacts", "source_snapshot_artifacts")
        if raw is None:
            return None
        records = raw if isinstance(raw, SourceSnapshotRepositoryRecords) else SourceSnapshotRepositoryRecords.model_validate(raw)
        return validate_source_snapshot_records(records)


@dataclass
class InMemorySourceSnapshotArtifactRepository:
    artifacts_by_id: dict[str, SourceSnapshotArtifactRow] = field(default_factory=dict)
    diagnostics_by_id: dict[str, SourceSnapshotDiagnosticRow] = field(default_factory=dict)

    def persist(self, records: SourceSnapshotRepositoryRecords) -> SourceSnapshotRepositoryRecords:
        validated = validate_source_snapshot_records(records)
        for artifact in validated.artifacts:
            self.artifacts_by_id[artifact.artifact_id] = artifact.model_copy(deep=True)
        for diagnostic in validated.diagnostics:
            self.diagnostics_by_id[diagnostic.diagnostic_id] = diagnostic.model_copy(deep=True)
        return validated

    def records(self) -> SourceSnapshotRepositoryRecords:
        return SourceSnapshotRepositoryRecords(
            artifacts=list(self.artifacts_by_id.values()),
            diagnostics=list(self.diagnostics_by_id.values()),
        )


def source_snapshot_records_from_acquisition_result(
    acquisition: Any,
    *,
    ingestion_job_id: str | None = None,
    created_at: str = STUB_TIMESTAMP,
    storage_prefix: str = "snapshots",
) -> SourceSnapshotRepositoryRecords:
    """Build private source snapshot metadata records from a deterministic acquisition result."""

    ticker = str(getattr(acquisition, "ticker", "")).upper()
    if not ticker:
        raise SourceSnapshotContractError("Acquisition source snapshots require a ticker binding.")

    response_state = _enum_value(getattr(acquisition, "response_state", None))
    diagnostics = _diagnostics_from_acquisition(acquisition, created_at=created_at)
    if response_state != _SUPPORTED_ACQUISITION_STATE:
        return validate_source_snapshot_records(SourceSnapshotRepositoryRecords(diagnostics=diagnostics))

    response = getattr(acquisition, "provider_response", None)
    if response is None:
        raise SourceSnapshotContractError("Supported acquisition snapshots require a provider response.")
    if getattr(response, "asset", None) is None or response.asset.ticker != ticker:
        raise SourceSnapshotContractError("Acquisition provider response must bind to the same asset ticker.")
    if _enum_value(getattr(response, "state", None)) != _SUPPORTED_ACQUISITION_STATE:
        raise SourceSnapshotContractError("Acquisition provider response must be supported before snapshot persistence.")

    source_record_by_id = {
        record.source_document_id: record for record in getattr(acquisition, "source_records", ())
    }
    artifacts: list[SourceSnapshotArtifactRow] = []
    for source in response.source_attributions:
        source_record = source_record_by_id.get(source.source_document_id)
        if source_record is None:
            raise SourceSnapshotContractError("Acquisition source records must bind every provider source document.")
        _validate_acquisition_source_binding(acquisition, source, source_record)
        if source.source_use_policy is SourceUsePolicy.rejected or source.allowlist_status is SourceAllowlistStatus.rejected:
            continue
        for category in _artifact_categories_for_source(source):
            artifacts.append(
                _artifact_from_provider_source(
                    source,
                    artifact_category=category,
                    checksum=_artifact_checksum(source_record.checksum, category),
                    byte_size=0,
                    content_type=_content_type_for_category(category),
                    created_at=created_at,
                    storage_key=_artifact_storage_key(storage_prefix, ticker, source.source_document_id, category),
                    ingestion_job_id=ingestion_job_id,
                    acquisition=acquisition,
                    source_record_checksum=source_record.checksum,
                )
            )

    return validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=artifacts, diagnostics=diagnostics))


def artifact_from_knowledge_pack_source(
    source: KnowledgePackSourceMetadata,
    *,
    artifact_id: str,
    artifact_category: SourceSnapshotArtifactCategory | str,
    checksum: str,
    byte_size: int,
    content_type: str,
    created_at: str,
    private_object_uri: str | None = None,
    storage_key: str | None = None,
    ingestion_job_id: str | None = None,
    evidence_state: str = "supported",
) -> SourceSnapshotArtifactRow:
    category = SourceSnapshotArtifactCategory(artifact_category)
    can_feed_generated_output = _source_metadata_can_support_generated_output(source)
    return SourceSnapshotArtifactRow(
        artifact_id=artifact_id,
        scope_kind=SourceSnapshotScopeKind.asset.value,
        asset_ticker=source.asset_ticker,
        ingestion_job_id=ingestion_job_id,
        source_document_id=source.source_document_id,
        source_reference_id=source.source_document_id,
        source_asset_ticker=source.asset_ticker,
        artifact_category=category.value,
        private_object_uri=private_object_uri,
        storage_key=storage_key,
        checksum=checksum,
        byte_size=byte_size,
        content_type=content_type,
        retrieved_at=source.retrieved_at,
        created_at=created_at,
        source_use_policy=source.source_use_policy.value,
        allowlist_status=source.allowlist_status.value,
        source_quality=source.source_quality.value,
        permitted_operations=source.permitted_operations.model_dump(mode="json"),
        source_type=source.source_type,
        source_identity=getattr(source, "source_identity", None) or source.url or source.source_document_id,
        is_official=source.is_official,
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
        freshness_state=source.freshness_state.value,
        evidence_state=evidence_state,
        can_feed_generated_output=can_feed_generated_output,
        can_support_citations=source.permitted_operations.can_support_citations,
        cache_allowed=source.permitted_operations.can_cache,
        export_allowed=source.permitted_operations.can_export_metadata,
    )


def _artifact_from_provider_source(
    source: Any,
    *,
    artifact_category: SourceSnapshotArtifactCategory,
    checksum: str,
    byte_size: int,
    content_type: str,
    created_at: str,
    storage_key: str,
    ingestion_job_id: str | None,
    acquisition: Any,
    source_record_checksum: str,
) -> SourceSnapshotArtifactRow:
    can_feed_generated_output = _provider_source_can_support_generated_output(source)
    return SourceSnapshotArtifactRow(
        artifact_id=f"snapshot-{source.asset_ticker.lower()}-{source.source_document_id}-{artifact_category.value}",
        scope_kind=SourceSnapshotScopeKind.asset.value,
        asset_ticker=source.asset_ticker,
        ingestion_job_id=ingestion_job_id,
        source_document_id=source.source_document_id,
        source_reference_id=source.source_document_id,
        source_asset_ticker=source.asset_ticker,
        artifact_category=artifact_category.value,
        storage_key=storage_key,
        checksum=checksum,
        byte_size=byte_size,
        content_type=content_type,
        retrieved_at=source.retrieved_at,
        created_at=created_at,
        source_use_policy=source.source_use_policy.value,
        allowlist_status=source.allowlist_status.value,
        source_quality=source.source_quality.value,
        permitted_operations=source.permitted_operations.model_dump(mode="json"),
        source_type=source.source_type,
        source_identity=getattr(source, "source_identity", None) or source.url or source.source_document_id,
        is_official=source.is_official,
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
        freshness_state=source.freshness_state.value,
        evidence_state=_source_evidence_state(acquisition),
        can_feed_generated_output=can_feed_generated_output,
        can_support_citations=source.permitted_operations.can_support_citations,
        cache_allowed=source.permitted_operations.can_cache,
        export_allowed=source.permitted_operations.can_export_metadata,
        compact_diagnostics={
            "acquisition_boundary": getattr(acquisition, "boundary", None),
            "source_policy_ref": getattr(acquisition, "source_policy_ref", None),
            "source_document_id": source.source_document_id,
            "source_type": source.source_type,
            "provider_kind": _enum_value(source.provider_kind),
            "data_category": _enum_value(source.data_category),
            "as_of_date": source.as_of_date,
            "source_record_checksum": source_record_checksum,
            "evidence_gap_states": dict(getattr(acquisition, "evidence_gap_states", {})),
            "no_live_external_calls": bool(getattr(acquisition, "no_live_external_calls", True)),
        },
    )


def validate_source_snapshot_records(records: SourceSnapshotRepositoryRecords) -> SourceSnapshotRepositoryRecords:
    artifact_ids = {artifact.artifact_id for artifact in records.artifacts}
    if len(artifact_ids) != len(records.artifacts):
        raise SourceSnapshotContractError("Source snapshot artifact IDs must be unique.")

    for artifact in records.artifacts:
        _validate_artifact(artifact)

    for diagnostic in records.diagnostics:
        _validate_diagnostic(diagnostic, artifact_ids)

    return records


def records_to_row_list(records: SourceSnapshotRepositoryRecords) -> list[StrictRow]:
    validate_source_snapshot_records(records)
    return [*records.artifacts, *records.diagnostics]


def _validate_artifact(artifact: SourceSnapshotArtifactRow) -> None:
    policy = SourceUsePolicy(artifact.source_use_policy)
    allowlist_status = SourceAllowlistStatus(artifact.allowlist_status)
    operations = SourceOperationPermissions.model_validate(artifact.permitted_operations)
    category = SourceSnapshotArtifactCategory(artifact.artifact_category)

    _validate_scope_binding(artifact)
    _validate_private_reference(artifact)
    _validate_compact_metadata(artifact.compact_diagnostics)

    if artifact.byte_size < 0:
        raise SourceSnapshotContractError("Source snapshot byte size cannot be negative.")
    if not artifact.source_document_id or not artifact.source_reference_id:
        raise SourceSnapshotContractError("Source snapshot artifacts require source document bindings.")
    if artifact.source_document_id != artifact.source_reference_id:
        raise SourceSnapshotContractError("Source snapshot source document and source reference bindings must match.")
    if not artifact.checksum:
        raise SourceSnapshotContractError("Source snapshot artifacts require checksum metadata.")
    if not artifact.checksum.startswith("sha256:"):
        raise SourceSnapshotContractError("Source snapshot artifacts require deterministic sha256 checksum metadata.")

    if policy is SourceUsePolicy.rejected or allowlist_status is SourceAllowlistStatus.rejected:
        raise SourceSnapshotContractError("Rejected sources cannot create source snapshot artifacts.")
    if not operations.can_store_metadata:
        raise SourceSnapshotContractError("Source snapshot artifacts require metadata storage permission.")
    handoff = validate_source_handoff(
        artifact,
        action=(
            SourcePolicyAction.cacheable_generated_output
            if artifact.can_feed_generated_output
            else SourcePolicyAction.diagnostics
        ),
    )
    if not handoff.allowed:
        raise SourceSnapshotContractError(
            "Source snapshot artifact failed Golden Asset Source Handoff: " + ", ".join(handoff.reason_codes)
        )

    if category.value in _RAW_OR_PARSED_CATEGORIES:
        if policy is not SourceUsePolicy.full_text_allowed or not operations.can_store_raw_text:
            raise SourceSnapshotContractError("Raw and parsed source snapshot artifacts require full-text storage rights.")
    elif policy is SourceUsePolicy.summary_allowed:
        if category.value not in _SUMMARY_CATEGORIES:
            raise SourceSnapshotContractError("Summary-allowed sources may only reference summary, excerpt, or metadata artifacts.")
    elif policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only}:
        if category.value not in _METADATA_ONLY_CATEGORIES:
            raise SourceSnapshotContractError("Metadata-only and link-only sources may only reference metadata artifacts.")

    blocked_state = (
        artifact.support_status in _BLOCKED_GENERATED_OUTPUT_STATES
        or artifact.approval_state in _BLOCKED_GENERATED_OUTPUT_STATES
        or artifact.validation_state in _BLOCKED_GENERATED_OUTPUT_STATES
        or artifact.source_policy_state in _BLOCKED_GENERATED_OUTPUT_STATES
    )
    if blocked_state or policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only}:
        _assert_no_generated_output_surface(artifact)
    if category is SourceSnapshotArtifactCategory.generated_artifact_reference and not artifact.can_feed_generated_output:
        raise SourceSnapshotContractError("Generated artifact references require sources that can feed generated output.")

    if (
        artifact.no_public_snapshot_access is not True
        or artifact.signed_url_created
        or artifact.browser_readable_storage_path
        or artifact.external_fetch_url_as_storage
    ):
        raise SourceSnapshotContractError("Source snapshot references must remain private and non-public.")
    if (
        artifact.raw_text_stored_in_contract
        or artifact.raw_provider_payload_stored
        or artifact.raw_article_text_stored
        or artifact.raw_user_text_stored
        or artifact.unrestricted_source_excerpt_stored
        or artifact.hidden_prompt_stored
        or artifact.raw_model_reasoning_stored
        or artifact.secrets_stored
    ):
        raise SourceSnapshotContractError("Source snapshot records may store only metadata, not raw payloads or secrets.")


def _validate_scope_binding(artifact: SourceSnapshotArtifactRow) -> None:
    if artifact.scope_kind == SourceSnapshotScopeKind.asset.value:
        if not artifact.asset_ticker or artifact.comparison_id:
            raise SourceSnapshotContractError("Asset-scoped snapshots require one asset ticker and no comparison ID.")
        if artifact.source_asset_ticker and artifact.source_asset_ticker != artifact.asset_ticker:
            raise SourceSnapshotContractError("Source snapshot artifact source ticker must match the asset scope.")
    else:
        if not artifact.comparison_id or not artifact.comparison_left_ticker or not artifact.comparison_right_ticker:
            raise SourceSnapshotContractError("Comparison-scoped snapshots require a comparison pack and both tickers.")
        if artifact.asset_ticker:
            raise SourceSnapshotContractError("Comparison-scoped snapshots cannot also claim a single asset scope.")
        if artifact.source_comparison_id and artifact.source_comparison_id != artifact.comparison_id:
            raise SourceSnapshotContractError("Source snapshot artifact source pack must match the comparison scope.")
        allowed_tickers = {artifact.comparison_left_ticker, artifact.comparison_right_ticker}
        if artifact.source_asset_ticker and artifact.source_asset_ticker not in allowed_tickers:
            raise SourceSnapshotContractError("Comparison source ticker must belong to the comparison pack.")


def _validate_private_reference(artifact: SourceSnapshotArtifactRow) -> None:
    references = [value for value in (artifact.private_object_uri, artifact.storage_key) if value]
    if len(references) != 1:
        raise SourceSnapshotContractError("Source snapshot artifacts require exactly one private object URI or storage key.")
    value = references[0]
    lowered = value.lower()
    if lowered.startswith(("http://", "https://", "ftp://", "file://", "data:", "blob:")):
        raise SourceSnapshotContractError("Source snapshot storage references cannot be public, browser, or fetch URLs.")
    signed_markers = ("x-goog-signature", "x-amz-signature", "signature=", "expires=", "token=", "x-goog-credential")
    if any(marker in lowered for marker in signed_markers):
        raise SourceSnapshotContractError("Source snapshot storage references cannot be signed URLs or tokenized paths.")
    public_markers = ("/public/", "public/", "apps/web/public", "_next/static", "next_public")
    if any(marker in lowered for marker in public_markers):
        raise SourceSnapshotContractError("Source snapshot storage references cannot use frontend-readable paths.")
    if artifact.storage_key and (artifact.storage_key.startswith("/") or ".." in artifact.storage_key.split("/")):
        raise SourceSnapshotContractError("Source snapshot storage keys must be relative private object keys.")
    if artifact.private_object_uri and not lowered.startswith(("gs://", "s3://", "r2://", "minio://")):
        raise SourceSnapshotContractError("Source snapshot object URIs must use private object-storage schemes.")


def _validate_diagnostic(diagnostic: SourceSnapshotDiagnosticRow, artifact_ids: set[str]) -> None:
    _validate_compact_metadata(diagnostic.compact_metadata)
    if diagnostic.artifact_id and diagnostic.artifact_id not in artifact_ids:
        raise SourceSnapshotContractError("Source snapshot diagnostics must reference known artifact IDs.")
    if (
        diagnostic.stores_secret
        or diagnostic.stores_user_text
        or diagnostic.stores_provider_payload
        or diagnostic.stores_raw_source_text
        or diagnostic.stores_unrestricted_excerpt
        or diagnostic.stores_hidden_prompt
        or diagnostic.stores_raw_model_reasoning
    ):
        raise SourceSnapshotContractError("Source snapshot diagnostics must store compact sanitized metadata only.")


def _validate_acquisition_source_binding(acquisition: Any, source: Any, source_record: Any) -> None:
    ticker = str(getattr(acquisition, "ticker", "")).upper()
    if source.asset_ticker != ticker:
        raise SourceSnapshotContractError("Acquisition source snapshot source ticker must match the asset.")
    if source_record.source_document_id != source.source_document_id:
        raise SourceSnapshotContractError("Acquisition source snapshot source document binding must match.")
    if _enum_value(source_record.source_use_policy) != source.source_use_policy.value:
        raise SourceSnapshotContractError("Acquisition source-use metadata must match the provider source.")
    if _enum_value(source_record.allowlist_status) != source.allowlist_status.value:
        raise SourceSnapshotContractError("Acquisition allowlist metadata must match the provider source.")
    if _enum_value(source_record.source_quality) != source.source_quality.value:
        raise SourceSnapshotContractError("Acquisition source quality metadata must match the provider source.")
    if _enum_value(source_record.freshness_state) != source.freshness_state.value:
        raise SourceSnapshotContractError("Acquisition freshness metadata must match the provider source.")
    if not str(source_record.checksum).startswith("sha256:"):
        raise SourceSnapshotContractError("Acquisition source records require deterministic sha256 checksums.")
    issuer = getattr(acquisition, "issuer", None)
    if issuer and source.publisher != issuer:
        raise SourceSnapshotContractError("ETF issuer source snapshots must bind to the same issuer.")


def _artifact_categories_for_source(source: Any) -> tuple[SourceSnapshotArtifactCategory, ...]:
    policy = SourceUsePolicy(source.source_use_policy)
    if policy is SourceUsePolicy.full_text_allowed:
        return (SourceSnapshotArtifactCategory.raw_source, SourceSnapshotArtifactCategory.parsed_text)
    if policy is SourceUsePolicy.summary_allowed:
        return (SourceSnapshotArtifactCategory.summary,)
    if policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only}:
        return (SourceSnapshotArtifactCategory.checksum_metadata,)
    return ()


def _artifact_checksum(source_checksum: str, category: SourceSnapshotArtifactCategory) -> str:
    if not source_checksum.startswith("sha256:"):
        raise SourceSnapshotContractError("Source snapshot artifact inputs require deterministic sha256 checksums.")
    checksum_body = source_checksum.split(":", 1)[1]
    if category is SourceSnapshotArtifactCategory.raw_source:
        return source_checksum
    return f"sha256:{category.value}:{checksum_body}"


def _artifact_storage_key(
    storage_prefix: str,
    ticker: str,
    source_document_id: str,
    category: SourceSnapshotArtifactCategory,
) -> str:
    prefix = storage_prefix.strip("/")
    return f"{prefix}/{ticker.lower()}/{source_document_id}/{category.value}.json"


def _content_type_for_category(category: SourceSnapshotArtifactCategory) -> str:
    if category is SourceSnapshotArtifactCategory.raw_source:
        return "application/octet-stream"
    return "application/json"


def _diagnostics_from_acquisition(acquisition: Any, *, created_at: str) -> list[SourceSnapshotDiagnosticRow]:
    ticker = str(getattr(acquisition, "ticker", "")).lower() or "unknown"
    rows: list[SourceSnapshotDiagnosticRow] = []
    for index, diagnostic in enumerate(getattr(acquisition, "diagnostics", ())):
        code = str(getattr(diagnostic, "code", "unknown"))
        rows.append(
            SourceSnapshotDiagnosticRow(
                diagnostic_id=f"snapshot-{ticker}-{code}-{index + 1}",
                category=_diagnostic_category(code).value,
                retrieval_status=_enum_value(getattr(diagnostic, "freshness_state", None)),
                retryable=bool(getattr(diagnostic, "retryable", False)),
                source_policy_ref=getattr(acquisition, "source_policy_ref", None),
                checksum=getattr(acquisition, "checksum", None),
                occurred_at=created_at,
                created_at=created_at,
                compact_metadata={
                    "acquisition_boundary": getattr(acquisition, "boundary", None),
                    "diagnostic_code": code,
                    "evidence_state": _enum_value(getattr(diagnostic, "evidence_state", None)),
                    "freshness_state": _enum_value(getattr(diagnostic, "freshness_state", None)),
                    "response_state": _enum_value(getattr(acquisition, "response_state", None)),
                },
                stores_secret=bool(getattr(diagnostic, "stores_secret", False)),
                stores_provider_payload=bool(getattr(diagnostic, "stores_raw_provider_payload", False)),
                stores_raw_source_text=bool(getattr(diagnostic, "stores_raw_source_text", False)),
            )
        )
    return rows


def _diagnostic_category(code: str) -> SourceSnapshotDiagnosticCategory:
    lowered = code.lower()
    if "source_policy" in lowered or "rejected" in lowered:
        return SourceSnapshotDiagnosticCategory.source_policy_blocked
    if "checksum" in lowered:
        return SourceSnapshotDiagnosticCategory.checksum_mismatch
    if "parser" in lowered:
        return SourceSnapshotDiagnosticCategory.parser_failed
    if "validation" in lowered or "fixture" in lowered:
        return SourceSnapshotDiagnosticCategory.validation_failed
    if "unavailable" in lowered or "unknown" in lowered or "evidence_gap" in lowered:
        return SourceSnapshotDiagnosticCategory.retrieval_unavailable
    return SourceSnapshotDiagnosticCategory.unknown


def _source_evidence_state(acquisition: Any) -> str:
    gap_states = set(getattr(acquisition, "evidence_gap_states", {}).values())
    if "stale" in gap_states:
        return "stale"
    if "partial" in gap_states:
        return "partial"
    if "unknown" in gap_states:
        return "unknown"
    if "unavailable" in gap_states:
        return "partial"
    if "insufficient_evidence" in gap_states:
        return "insufficient_evidence"
    return "supported"


def _provider_source_can_support_generated_output(source: Any) -> bool:
    decision = SourcePolicyDecision(
        decision=SourcePolicyDecisionState.allowed,
        source_id=source.source_document_id,
        matched_by="local_fixture",
        source_quality=source.source_quality,
        allowlist_status=source.allowlist_status,
        source_use_policy=source.source_use_policy,
        permitted_operations=source.permitted_operations,
        allowed_excerpt=DEFAULT_ALLOWED_EXCERPT_BEHAVIOR.model_copy(),
        reason="Deterministic source snapshot persistence reused source-use generated-output policy helper.",
    )
    return source_can_support_generated_output(decision)


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", value)


def _validate_compact_metadata(metadata: dict[str, Any]) -> None:
    text = repr(metadata).lower()
    forbidden_markers = (
        "api" + "_key",
        "authorization",
        "bearer ",
        "secret",
        "private key",
        "raw_prompt",
        "raw_model_reasoning",
        "raw_article_text",
        "raw_provider_payload",
        "user_question",
        "transcript",
    )
    if any(marker in text for marker in forbidden_markers):
        raise SourceSnapshotContractError("Compact snapshot metadata cannot contain secrets, prompts, payloads, or raw text.")


def _assert_no_generated_output_surface(artifact: SourceSnapshotArtifactRow) -> None:
    if (
        artifact.generated_output_available
        or artifact.can_feed_generated_output
        or artifact.can_support_citations
        or artifact.cache_allowed
        or artifact.export_allowed
    ):
        raise SourceSnapshotContractError(
            "Blocked, metadata-only, link-only, and rejected-source snapshots cannot feed generated output, citations, caches, or exports."
        )


def _source_metadata_can_support_generated_output(source: KnowledgePackSourceMetadata) -> bool:
    decision = SourcePolicyDecision(
        decision=SourcePolicyDecisionState.allowed,
        source_id=source.source_document_id,
        matched_by="local_fixture",
        source_quality=source.source_quality,
        allowlist_status=source.allowlist_status,
        source_use_policy=source.source_use_policy,
        permitted_operations=source.permitted_operations,
        allowed_excerpt=DEFAULT_ALLOWED_EXCERPT_BEHAVIOR.model_copy(),
        reason="Dormant source snapshot contract reuses source-use generated-output policy helper.",
    )
    return source_can_support_generated_output(decision)


def _persist_records(
    session: Any,
    *,
    collection: str,
    key: str,
    records: SourceSnapshotRepositoryRecords,
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
        raise SourceSnapshotContractError(
            "Injected source snapshot session must expose save_repository_record(collection, key, records), save(...), or add_all(records)."
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
