from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from backend.knowledge_pack_repository import (
    KNOWLEDGE_PACK_REPOSITORY_TABLES,
    AssetKnowledgePackRepository,
    KnowledgePackRepositoryContractError,
    knowledge_pack_repository_metadata,
)
from backend.models import SourceUsePolicy
from backend.retrieval import build_asset_knowledge_pack, build_asset_knowledge_pack_result


ROOT = Path(__file__).resolve().parents[2]


def test_knowledge_pack_repository_metadata_is_dormant_and_explicit():
    metadata = knowledge_pack_repository_metadata()

    assert metadata.boundary == "asset-knowledge-pack-repository-contract-v1"
    assert metadata.opens_connection_on_import is False
    assert metadata.creates_runtime_tables is False
    assert tuple(metadata.tables) == KNOWLEDGE_PACK_REPOSITORY_TABLES
    assert set(KNOWLEDGE_PACK_REPOSITORY_TABLES) == {
        "asset_knowledge_pack_envelopes",
        "asset_knowledge_pack_source_documents",
        "asset_knowledge_pack_source_chunks",
        "asset_knowledge_pack_facts",
        "asset_knowledge_pack_recent_developments",
        "asset_knowledge_pack_evidence_gaps",
        "asset_knowledge_pack_section_freshness_inputs",
        "asset_knowledge_pack_source_checksums",
    }
    assert "asset" in metadata.tables["asset_knowledge_pack_envelopes"].columns
    assert "source_use_policy" in metadata.tables["asset_knowledge_pack_source_documents"].columns
    assert "stored_text" in metadata.tables["asset_knowledge_pack_source_chunks"].columns
    assert "source_document_id" in metadata.tables["asset_knowledge_pack_facts"].columns


def test_migration_revision_is_importable_and_limited_to_knowledge_pack_tables():
    revision_path = ROOT / "alembic" / "versions" / "20260425_0002_knowledge_pack_repository_contracts.py"
    source = revision_path.read_text(encoding="utf-8")
    spec = importlib.util.spec_from_file_location("knowledge_pack_contract_revision", revision_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.revision == "20260425_0002"
    assert module.down_revision == "20260425_0001"
    assert module.KNOWLEDGE_PACK_TABLE_NAMES == KNOWLEDGE_PACK_REPOSITORY_TABLES
    for table_name in KNOWLEDGE_PACK_REPOSITORY_TABLES:
        assert f'"{table_name}"' in source

    forbidden_table_markers = [
        "ingestion_jobs",
        "chat_sessions",
        "chat_messages",
        "trust_metrics",
        "generated_output_cache",
        "user_accounts",
        "provider_secrets",
        "deployment",
    ]
    for marker in forbidden_table_markers:
        assert marker not in module.KNOWLEDGE_PACK_TABLE_NAMES
        assert f'op.create_table("{marker}"' not in source


def test_repository_serializes_and_reconstructs_supported_voo_contract():
    response = build_asset_knowledge_pack_result("VOO")
    retrieval_pack = build_asset_knowledge_pack("VOO")
    repository = AssetKnowledgePackRepository()

    records = repository.serialize(response, retrieval_pack=retrieval_pack)
    restored = repository.deserialize(records)

    assert records.envelope.ticker == "VOO"
    assert records.envelope.generated_output_available is True
    assert records.envelope.knowledge_pack_freshness_hash == response.knowledge_pack_freshness_hash
    assert records.envelope.source_document_ids == response.source_document_ids
    assert records.envelope.citation_ids == response.citation_ids
    assert len(records.source_documents) == response.counts.source_document_count
    assert len(records.normalized_facts) == response.counts.normalized_fact_count
    assert len(records.source_chunks) == response.counts.source_chunk_count
    assert len(records.recent_developments) == response.counts.recent_development_count
    assert len(records.evidence_gaps) == response.counts.evidence_gap_count
    assert len(records.source_checksums) == len(response.source_checksums)
    assert {row.asset_ticker for row in records.source_documents} == {"VOO"}
    assert {row.asset_ticker for row in records.source_chunks} == {"VOO"}
    assert {row.asset_ticker for row in records.normalized_facts} == {"VOO"}
    assert {row.asset_ticker for row in records.recent_developments} == {"VOO"}
    assert all(row.allowlist_status == "allowed" for row in records.source_documents)
    assert {row.source_use_policy for row in records.source_documents} <= {"full_text_allowed", "summary_allowed"}
    assert all(row.source_document_id in response.source_document_ids for row in records.normalized_facts)
    assert all(row.source_chunk_id in {chunk.chunk_id for chunk in records.source_chunks} for row in records.normalized_facts)
    assert all(row.stored_text for row in records.source_chunks)
    assert any(row.text_storage_policy == "raw_text_allowed" for row in records.source_chunks)
    assert any(row.text_storage_policy == "allowed_excerpt" for row in records.source_chunks)

    assert restored.ticker == response.ticker
    assert restored.asset.model_dump(mode="json") == response.asset.model_dump(mode="json")
    assert restored.build_state == response.build_state
    assert restored.generated_output_available == response.generated_output_available
    assert restored.source_document_ids == response.source_document_ids
    assert restored.citation_ids == response.citation_ids
    assert restored.counts == response.counts
    assert restored.knowledge_pack_freshness_hash == response.knowledge_pack_freshness_hash
    assert {source.source_use_policy for source in restored.source_documents} == {
        source.source_use_policy for source in response.source_documents
    }
    assert {fact.source_document_id for fact in restored.normalized_facts} == {
        fact.source_document_id for fact in response.normalized_facts
    }
    assert {gap.evidence_state for gap in restored.evidence_gaps} == {
        gap.evidence_state for gap in response.evidence_gaps
    }


def test_non_generated_states_remain_metadata_only_without_fake_evidence():
    repository = AssetKnowledgePackRepository()

    for ticker, state in [("SPY", "eligible_not_cached"), ("TQQQ", "unsupported"), ("ZZZZ", "unknown")]:
        response = build_asset_knowledge_pack_result(ticker)
        records = repository.serialize(response)
        restored = repository.deserialize(records)

        assert records.envelope.ticker == ticker
        assert records.envelope.build_state == state
        assert records.envelope.generated_output_available is False
        assert records.source_documents == []
        assert records.source_chunks == []
        assert records.normalized_facts == []
        assert records.recent_developments == []
        assert records.source_checksums == []
        assert len(records.evidence_gaps) == 1
        assert records.evidence_gaps[0].field_name == "asset_knowledge_pack"
        assert restored.generated_output_available is False
        assert restored.source_documents == []
        assert restored.normalized_facts == []
        assert restored.source_chunks == []
        assert restored.recent_developments == []


def test_source_use_restrictions_block_disallowed_generated_output_sources():
    response = build_asset_knowledge_pack_result("VOO")
    source = response.source_documents[0].model_copy(
        update={
            "source_use_policy": SourceUsePolicy.metadata_only,
            "permitted_operations": response.source_documents[0].permitted_operations.model_copy(
                update={"can_support_generated_output": False, "can_support_citations": False}
            ),
        }
    )
    disallowed = response.model_copy(update={"source_documents": [source, *response.source_documents[1:]]})

    with pytest.raises(KnowledgePackRepositoryContractError, match="cannot support generated-output use"):
        AssetKnowledgePackRepository().serialize(disallowed, retrieval_pack=build_asset_knowledge_pack("VOO"))


def test_metadata_and_link_only_sources_do_not_persist_raw_chunk_text_when_not_generated():
    response = build_asset_knowledge_pack_result("VOO")
    retrieval_pack = build_asset_knowledge_pack("VOO")
    source = response.source_documents[0].model_copy(update={"source_use_policy": SourceUsePolicy.link_only})
    link_limited = response.model_copy(
        update={
            "generated_output_available": False,
            "source_documents": [source, *response.source_documents[1:]],
        }
    )

    records = AssetKnowledgePackRepository().serialize(link_limited, retrieval_pack=retrieval_pack)
    limited_chunk_rows = [
        row for row in records.source_chunks if row.source_document_id == source.source_document_id
    ]

    assert limited_chunk_rows
    assert all(row.source_use_policy == "link_only" for row in limited_chunk_rows)
    assert all(row.stored_text is None for row in limited_chunk_rows)
    assert all(row.text_storage_policy == "link_only" for row in limited_chunk_rows)


def test_wrong_asset_source_bindings_are_rejected():
    response = build_asset_knowledge_pack_result("VOO")
    wrong_asset_source = response.source_documents[0].model_copy(update={"asset_ticker": "QQQ"})
    wrong_asset = response.model_copy(update={"source_documents": [wrong_asset_source, *response.source_documents[1:]]})

    with pytest.raises(KnowledgePackRepositoryContractError, match="not knowledge-pack asset VOO"):
        AssetKnowledgePackRepository().serialize(wrong_asset, retrieval_pack=build_asset_knowledge_pack("VOO"))


def test_repository_imports_do_not_open_database_or_live_provider_paths():
    repository_source = (ROOT / "backend" / "repositories" / "knowledge_packs.py").read_text(encoding="utf-8")

    forbidden = [
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "requests",
        "httpx",
        "OPENROUTER",
        "api_key",
        "SEC",
    ]
    for marker in forbidden:
        assert marker not in repository_source
