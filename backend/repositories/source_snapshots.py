from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from backend.models import (
    DEFAULT_ALLOWED_EXCERPT_BEHAVIOR,
    FreshnessState,
    KnowledgePackSourceMetadata,
    SourceAllowlistStatus,
    SourceOperationPermissions,
    SourcePolicyDecision,
    SourcePolicyDecisionState,
    SourceQuality,
    SourceUsePolicy,
)
from backend.repositories.knowledge_packs import RepositoryMetadata, RepositoryTableDefinition, StrictRow
from backend.source_policy import source_can_support_generated_output


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

    def validate(self, records: SourceSnapshotRepositoryRecords) -> SourceSnapshotRepositoryRecords:
        return validate_source_snapshot_records(records)

    def persist(self, records: SourceSnapshotRepositoryRecords) -> SourceSnapshotRepositoryRecords:
        validated = validate_source_snapshot_records(records)
        if self.session is None:
            return validated
        if not hasattr(self.session, "add_all"):
            raise SourceSnapshotContractError("Injected source snapshot session must expose add_all(records).")
        self.session.add_all(records_to_row_list(validated))
        return validated


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
        freshness_state=source.freshness_state.value,
        evidence_state=evidence_state,
        can_feed_generated_output=can_feed_generated_output,
        can_support_citations=source.permitted_operations.can_support_citations,
        cache_allowed=source.permitted_operations.can_cache,
        export_allowed=source.permitted_operations.can_export_metadata,
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
    if not artifact.checksum:
        raise SourceSnapshotContractError("Source snapshot artifacts require checksum metadata.")

    if policy is SourceUsePolicy.rejected or allowlist_status is SourceAllowlistStatus.rejected:
        raise SourceSnapshotContractError("Rejected sources cannot create source snapshot artifacts.")
    if not operations.can_store_metadata:
        raise SourceSnapshotContractError("Source snapshot artifacts require metadata storage permission.")

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
