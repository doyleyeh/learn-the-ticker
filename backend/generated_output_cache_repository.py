from __future__ import annotations

from backend.repositories.generated_outputs import (
    GENERATED_OUTPUT_CACHE_REPOSITORY_BOUNDARY,
    GENERATED_OUTPUT_CACHE_TABLES,
    GeneratedOutputArtifactCategory,
    GeneratedOutputArtifactRecordRow,
    GeneratedOutputCacheContractError,
    GeneratedOutputCacheEnvelopeRow,
    GeneratedOutputCacheRepository,
    GeneratedOutputCacheRepositoryRecords,
    GeneratedOutputDiagnosticCategory,
    GeneratedOutputDiagnosticRow,
    GeneratedOutputFreshnessHashInputRow,
    GeneratedOutputKnowledgePackHashInputRow,
    GeneratedOutputScopeKind,
    GeneratedOutputSourceChecksumRow,
    GeneratedOutputValidationStatusRow,
    InMemoryGeneratedOutputCacheRepository,
    build_generated_output_cache_records,
    generated_output_cache_repository_metadata,
    persist_generated_output_cache_records,
    validate_generated_output_cache_records,
)


DETERMINISTIC_GENERATED_OUTPUT_MODEL = "deterministic-fixture-model"


def build_deterministic_generated_output_cache_records(
    *,
    cache_entry_id: str,
    output_identity: str,
    mode_or_output_type: str,
    artifact_category,
    entry_kind,
    scope,
    schema_version: str,
    prompt_version: str,
    knowledge_input,
    citation_ids: list[str],
    created_at: str,
    expires_at: str | None = None,
    ttl_seconds: int | None = None,
    asset_ticker: str | None = None,
    comparison_id: str | None = None,
    comparison_left_ticker: str | None = None,
    comparison_right_ticker: str | None = None,
    model_name: str = DETERMINISTIC_GENERATED_OUTPUT_MODEL,
):
    from backend.cache import (
        build_cache_key,
        build_generated_output_freshness_input,
        cache_entry_metadata_from_generated_output,
        compute_generated_output_freshness_hash,
        compute_knowledge_pack_freshness_hash,
    )
    from backend.models import CacheKeyMetadata

    knowledge_hash = compute_knowledge_pack_freshness_hash(knowledge_input)
    generated_input = build_generated_output_freshness_input(
        output_identity=output_identity,
        entry_kind=entry_kind,
        scope=scope,
        schema_version=schema_version,
        prompt_version=prompt_version,
        model_name=model_name,
        knowledge_input=knowledge_input,
    )
    generated_hash = compute_generated_output_freshness_hash(generated_input)
    cache_key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=entry_kind,
            scope=scope,
            asset_ticker=asset_ticker or knowledge_input.asset_ticker,
            comparison_left_ticker=comparison_left_ticker or knowledge_input.comparison_left_ticker,
            comparison_right_ticker=comparison_right_ticker or knowledge_input.comparison_right_ticker,
            pack_identity=comparison_id or knowledge_input.pack_identity,
            mode_or_output_type=mode_or_output_type,
            schema_version=schema_version,
            source_freshness_state=generated_input.source_freshness_state,
            prompt_version=prompt_version,
            model_name=model_name,
            input_freshness_hash=generated_hash,
        )
    )
    cache_metadata = cache_entry_metadata_from_generated_output(
        cache_key=cache_key,
        freshness_input=generated_input,
        freshness_hash=generated_hash,
        citation_ids=citation_ids,
        created_at=created_at,
        expires_at=expires_at,
        cache_allowed=True,
        export_allowed=False,
    )
    return build_generated_output_cache_records(
        cache_entry_id=cache_entry_id,
        output_identity=output_identity,
        mode_or_output_type=mode_or_output_type,
        artifact_category=artifact_category,
        cache_metadata=cache_metadata,
        generated_freshness_input=generated_input,
        knowledge_freshness_input=knowledge_input,
        knowledge_pack_freshness_hash=knowledge_hash,
        created_at=created_at,
        expires_at=expires_at,
        ttl_seconds=ttl_seconds,
        asset_ticker=asset_ticker,
        comparison_id=comparison_id,
        comparison_left_ticker=comparison_left_ticker,
        comparison_right_ticker=comparison_right_ticker,
        deterministic_mock_marker=model_name,
    )

__all__ = [
    "GENERATED_OUTPUT_CACHE_REPOSITORY_BOUNDARY",
    "GENERATED_OUTPUT_CACHE_TABLES",
    "GeneratedOutputArtifactCategory",
    "GeneratedOutputArtifactRecordRow",
    "GeneratedOutputCacheContractError",
    "GeneratedOutputCacheEnvelopeRow",
    "GeneratedOutputCacheRepository",
    "GeneratedOutputCacheRepositoryRecords",
    "GeneratedOutputDiagnosticCategory",
    "GeneratedOutputDiagnosticRow",
    "GeneratedOutputFreshnessHashInputRow",
    "GeneratedOutputKnowledgePackHashInputRow",
    "GeneratedOutputScopeKind",
    "GeneratedOutputSourceChecksumRow",
    "GeneratedOutputValidationStatusRow",
    "InMemoryGeneratedOutputCacheRepository",
    "build_deterministic_generated_output_cache_records",
    "build_generated_output_cache_records",
    "generated_output_cache_repository_metadata",
    "persist_generated_output_cache_records",
    "validate_generated_output_cache_records",
]
