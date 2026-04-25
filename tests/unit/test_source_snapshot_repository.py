from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from backend.models import SourceUsePolicy
from backend.retrieval import build_asset_knowledge_pack_result
from backend.source_snapshot_repository import (
    SOURCE_SNAPSHOT_REPOSITORY_BOUNDARY,
    SOURCE_SNAPSHOT_TABLES,
    SourceSnapshotArtifactCategory,
    SourceSnapshotArtifactRow,
    SourceSnapshotContractError,
    SourceSnapshotDiagnosticRow,
    SourceSnapshotRepositoryRecords,
    artifact_from_knowledge_pack_source,
    source_snapshot_repository_metadata,
    validate_source_snapshot_records,
)


ROOT = Path(__file__).resolve().parents[2]


def _source(policy: SourceUsePolicy | None = None):
    source = build_asset_knowledge_pack_result("VOO").source_documents[0]
    if policy is None:
        return source
    operations = source.permitted_operations
    if policy is SourceUsePolicy.full_text_allowed:
        operations = operations.model_copy(update={"can_store_metadata": True, "can_store_raw_text": True})
    elif policy is SourceUsePolicy.summary_allowed:
        operations = operations.model_copy(
            update={
                "can_store_metadata": True,
                "can_store_raw_text": False,
                "can_display_excerpt": True,
                "can_summarize": True,
                "can_support_generated_output": True,
                "can_support_citations": True,
            }
        )
    elif policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only}:
        operations = operations.model_copy(
            update={
                "can_store_metadata": True,
                "can_store_raw_text": False,
                "can_display_excerpt": False,
                "can_summarize": False,
                "can_cache": False,
                "can_export_metadata": False,
                "can_export_excerpt": False,
                "can_support_generated_output": False,
                "can_support_citations": False,
                "can_support_canonical_facts": False,
                "can_support_recent_developments": False,
            }
        )
    elif policy is SourceUsePolicy.rejected:
        operations = operations.model_copy(
            update={
                "can_store_metadata": False,
                "can_store_raw_text": False,
                "can_display_metadata": False,
                "can_display_excerpt": False,
                "can_summarize": False,
                "can_cache": False,
                "can_export_metadata": False,
                "can_export_excerpt": False,
                "can_support_generated_output": False,
                "can_support_citations": False,
                "can_support_canonical_facts": False,
                "can_support_recent_developments": False,
            }
        )
    return source.model_copy(update={"source_use_policy": policy, "permitted_operations": operations})


def _artifact(**updates):
    source = updates.pop("source", _source())
    defaults = {
        "artifact_id": "snapshot-voo-raw-1",
        "artifact_category": SourceSnapshotArtifactCategory.raw_source,
        "checksum": "sha256:fixture-raw",
        "byte_size": 1024,
        "content_type": "text/html",
        "created_at": "2026-04-25T05:35:55Z",
        "private_object_uri": "gs://ltt-private-source-snapshots/voo/raw/sec-source.html",
    }
    defaults.update(updates)
    return artifact_from_knowledge_pack_source(source, **defaults)


def test_source_snapshot_metadata_is_dormant_and_explicit():
    metadata = source_snapshot_repository_metadata()

    assert metadata.boundary == SOURCE_SNAPSHOT_REPOSITORY_BOUNDARY
    assert metadata.opens_connection_on_import is False
    assert metadata.creates_runtime_tables is False
    assert tuple(metadata.tables) == SOURCE_SNAPSHOT_TABLES
    assert set(SOURCE_SNAPSHOT_TABLES) == {
        "source_snapshot_artifacts",
        "source_snapshot_diagnostics",
    }
    assert "artifact_category" in metadata.tables["source_snapshot_artifacts"].columns
    assert "private_object_uri" in metadata.tables["source_snapshot_artifacts"].columns
    assert "source_use_policy" in metadata.tables["source_snapshot_artifacts"].columns
    assert "permitted_operations" in metadata.tables["source_snapshot_artifacts"].columns
    assert "compact_metadata" in metadata.tables["source_snapshot_diagnostics"].columns


def test_snapshot_categories_cover_required_artifact_types():
    assert {category.value for category in SourceSnapshotArtifactCategory} >= {
        "raw_source",
        "parsed_text",
        "normalized_facts_input",
        "generated_artifact_reference",
        "diagnostics_metadata",
    }


def test_migration_revision_is_importable_and_limited_to_snapshot_tables():
    revision_path = ROOT / "alembic" / "versions" / "20260425_0004_source_snapshot_artifact_contracts.py"
    source = revision_path.read_text(encoding="utf-8")
    spec = importlib.util.spec_from_file_location("source_snapshot_contract_revision", revision_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.revision == "20260425_0004"
    assert module.down_revision == "20260425_0003"
    assert module.SOURCE_SNAPSHOT_TABLE_NAMES == SOURCE_SNAPSHOT_TABLES
    for table_name in SOURCE_SNAPSHOT_TABLES:
        assert f'"{table_name}"' in source

    forbidden_table_markers = [
        "chat_sessions",
        "chat_messages",
        "user_accounts",
        "provider_secrets",
        "generated_output_cache",
        "public_snapshot_urls",
        "signed_urls",
    ]
    for marker in forbidden_table_markers:
        assert marker not in module.SOURCE_SNAPSHOT_TABLE_NAMES
        assert f'op.create_table("{marker}"' not in source


def test_full_text_allowed_sources_can_reference_private_raw_and_parsed_artifacts():
    raw = _artifact()
    parsed = _artifact(
        artifact_id="snapshot-voo-parsed-1",
        artifact_category=SourceSnapshotArtifactCategory.parsed_text,
        checksum="sha256:fixture-parsed",
        storage_key="snapshots/voo/parsed/sec-source.txt",
        private_object_uri=None,
    )
    records = validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[raw, parsed]))

    assert records.table_names == SOURCE_SNAPSHOT_TABLES
    assert {artifact.artifact_category for artifact in records.artifacts} == {"raw_source", "parsed_text"}
    assert all(artifact.no_public_snapshot_access for artifact in records.artifacts)
    assert all(artifact.raw_text_stored_in_contract is False for artifact in records.artifacts)
    assert all(artifact.can_feed_generated_output is True for artifact in records.artifacts)


def test_summary_allowed_sources_cannot_reference_unrestricted_raw_or_parsed_artifacts():
    summary_source = _source(SourceUsePolicy.summary_allowed)
    summary = _artifact(
        source=summary_source,
        artifact_id="snapshot-voo-summary-1",
        artifact_category=SourceSnapshotArtifactCategory.summary,
        checksum="sha256:fixture-summary",
        storage_key="snapshots/voo/summary/source-summary.json",
        private_object_uri=None,
    )
    validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[summary]))

    raw = _artifact(source=summary_source)
    with pytest.raises(SourceSnapshotContractError, match="full-text storage rights"):
        validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[raw]))


def test_metadata_and_link_only_sources_reference_metadata_artifacts_only():
    metadata_source = _source(SourceUsePolicy.metadata_only)
    metadata = _artifact(
        source=metadata_source,
        artifact_id="snapshot-voo-metadata-1",
        artifact_category=SourceSnapshotArtifactCategory.checksum_metadata,
        checksum="sha256:fixture-metadata",
        content_type="application/json",
        storage_key="snapshots/voo/metadata/source-checksum.json",
        private_object_uri=None,
    )
    validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[metadata]))

    normalized_input = _artifact(
        source=metadata_source,
        artifact_id="snapshot-voo-facts-input-1",
        artifact_category=SourceSnapshotArtifactCategory.normalized_facts_input,
        checksum="sha256:fixture-facts-input",
    )
    with pytest.raises(SourceSnapshotContractError, match="metadata artifacts"):
        validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[normalized_input]))


def test_rejected_sources_cannot_create_snapshot_artifacts():
    rejected = _artifact(source=_source(SourceUsePolicy.rejected), artifact_category=SourceSnapshotArtifactCategory.metadata)

    with pytest.raises(SourceSnapshotContractError, match="Rejected sources"):
        validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[rejected]))


def test_private_object_references_reject_public_signed_or_browser_paths():
    validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[_artifact()]))

    invalid_references = [
        {"private_object_uri": "https://storage.example/snapshots/voo/raw.html"},
        {"private_object_uri": "gs://ltt-private/snapshots/voo/raw.html?X-Goog-Signature=abc"},
        {"storage_key": "public/snapshots/voo/raw.html", "private_object_uri": None},
        {"storage_key": "apps/web/public/snapshots/voo/raw.html", "private_object_uri": None},
    ]
    for index, update in enumerate(invalid_references):
        artifact = _artifact(artifact_id=f"snapshot-invalid-{index}", **update)
        with pytest.raises(SourceSnapshotContractError, match="public|signed|frontend-readable|URLs"):
            validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[artifact]))


def test_wrong_asset_and_wrong_comparison_pack_bindings_are_rejected():
    wrong_asset = _artifact().model_copy(update={"source_asset_ticker": "QQQ"})
    with pytest.raises(SourceSnapshotContractError, match="source ticker must match"):
        validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[wrong_asset]))

    comparison = SourceSnapshotArtifactRow(
        artifact_id="snapshot-compare-1",
        scope_kind="comparison",
        comparison_id="compare-voo-qqq",
        comparison_left_ticker="VOO",
        comparison_right_ticker="QQQ",
        source_asset_ticker="AAPL",
        source_comparison_id="compare-voo-qqq",
        source_document_id="source-voo-1",
        source_reference_id="source-voo-1",
        artifact_category="metadata",
        storage_key="snapshots/compare/voo-qqq/source-metadata.json",
        checksum="sha256:compare",
        byte_size=80,
        content_type="application/json",
        created_at="2026-04-25T05:35:55Z",
        source_use_policy="full_text_allowed",
        allowlist_status="allowed",
        source_quality="fixture",
        permitted_operations=_source().permitted_operations.model_dump(mode="json"),
        freshness_state="fresh",
        evidence_state="supported",
    )
    with pytest.raises(SourceSnapshotContractError, match="belong to the comparison pack"):
        validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[comparison]))


def test_diagnostics_store_only_redacted_compact_metadata():
    artifact = _artifact()
    diagnostic = SourceSnapshotDiagnosticRow(
        diagnostic_id="snapshot-diagnostic-1",
        artifact_id=artifact.artifact_id,
        category="retrieval_unavailable",
        retrieval_status="not_modified",
        retryable=True,
        source_policy_ref="source-policy-v1",
        checksum=artifact.checksum,
        occurred_at="2026-04-25T05:35:55Z",
        created_at="2026-04-25T05:35:56Z",
        compact_metadata={"retry_after_seconds": 60, "error_category": "retrieval_unavailable"},
    )
    validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[artifact], diagnostics=[diagnostic]))

    raw_diagnostic = diagnostic.model_copy(update={"diagnostic_id": "raw-diagnostic", "stores_provider_payload": True})
    with pytest.raises(SourceSnapshotContractError, match="compact sanitized metadata"):
        validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[artifact], diagnostics=[raw_diagnostic]))

    secret_diagnostic = diagnostic.model_copy(
        update={"diagnostic_id": "secret-diagnostic", "compact_metadata": {"authorization": "Bearer redacted"}}
    )
    with pytest.raises(SourceSnapshotContractError, match="cannot contain secrets"):
        validate_source_snapshot_records(
            SourceSnapshotRepositoryRecords(artifacts=[artifact], diagnostics=[secret_diagnostic])
        )


def test_blocked_states_cannot_feed_generated_output_citations_caches_or_exports():
    blocked = _artifact().model_copy(
        update={
            "support_status": "unsupported",
            "generated_output_available": True,
        }
    )

    with pytest.raises(SourceSnapshotContractError, match="cannot feed generated output"):
        validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=[blocked]))


def test_repository_imports_do_not_open_storage_network_or_database_paths():
    repository_source = (ROOT / "backend" / "repositories" / "source_snapshots.py").read_text(encoding="utf-8")

    forbidden = [
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "requests",
        "httpx",
        "boto3",
        "google.cloud.storage",
        "generate_signed",
        "OPENROUTER",
        "api_key",
        "raw_text =",
    ]
    for marker in forbidden:
        assert marker not in repository_source
