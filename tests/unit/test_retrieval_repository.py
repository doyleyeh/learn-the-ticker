from __future__ import annotations

import pytest

from backend.knowledge_pack_repository import AssetKnowledgePackRepository
from backend.knowledge_pack_repository import InMemoryAssetKnowledgePackRepository
from backend.knowledge_pack_repository import knowledge_pack_records_from_acquisition_result
from backend.provider_adapters.etf_issuer import build_etf_issuer_acquisition_result
from backend.providers import fetch_mock_provider_response, mock_etf_issuer_adapter
from backend.retrieval import build_asset_knowledge_pack, build_asset_knowledge_pack_result
from backend.retrieval_repository import (
    RETRIEVAL_REPOSITORY_BOUNDARY,
    read_persisted_knowledge_pack_response,
)
from backend.source_snapshot_repository import source_snapshot_records_from_acquisition_result


class FakeKnowledgePackReader:
    def __init__(self, records_by_ticker):
        self.records_by_ticker = records_by_ticker
        self.requests: list[str] = []

    def read_knowledge_pack_records(self, ticker: str):
        self.requests.append(ticker)
        return self.records_by_ticker.get(ticker)


class FailingKnowledgePackReader:
    def read_knowledge_pack_records(self, ticker: str):
        raise RuntimeError(f"controlled miss for {ticker}")


def _serialized_voo_records():
    repository = AssetKnowledgePackRepository()
    return repository.serialize(
        build_asset_knowledge_pack_result("VOO"),
        retrieval_pack=build_asset_knowledge_pack("VOO"),
    )


def _acquisition_voo_records():
    adapter = mock_etf_issuer_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "VOO").licensing
    acquisition = build_etf_issuer_acquisition_result(adapter, adapter.request("VOO"), licensing)
    snapshots = source_snapshot_records_from_acquisition_result(acquisition, ingestion_job_id="pre-cache-launch-voo")
    return knowledge_pack_records_from_acquisition_result(acquisition, snapshots)


def test_retrieval_repository_boundary_is_dormant_and_persisted_first_for_voo():
    records = _serialized_voo_records()
    reader = FakeKnowledgePackReader({"VOO": records})
    fixture = build_asset_knowledge_pack_result("VOO")

    read_result = read_persisted_knowledge_pack_response("voo", reader=reader)
    persisted = build_asset_knowledge_pack_result("voo", persisted_reader=reader)

    assert RETRIEVAL_REPOSITORY_BOUNDARY == "retrieval-knowledge-pack-read-boundary-v1"
    assert read_result.status == "found"
    assert read_result.found is True
    assert reader.requests == ["VOO", "VOO"]
    assert persisted.ticker == fixture.ticker == "VOO"
    assert persisted.asset.model_dump(mode="json") == fixture.asset.model_dump(mode="json")
    assert persisted.asset_type == fixture.asset_type
    assert persisted.build_state == fixture.build_state
    assert persisted.state == fixture.state
    assert persisted.generated_output_available == fixture.generated_output_available
    assert persisted.reusable_generated_output_cache_hit == fixture.reusable_generated_output_cache_hit
    assert persisted.generated_route == fixture.generated_route
    assert persisted.capabilities == fixture.capabilities
    assert persisted.freshness == fixture.freshness
    assert persisted.section_freshness == fixture.section_freshness
    assert persisted.source_document_ids == fixture.source_document_ids
    assert persisted.citation_ids == fixture.citation_ids
    assert persisted.counts == fixture.counts
    assert persisted.source_documents == fixture.source_documents
    assert persisted.normalized_facts == fixture.normalized_facts
    assert persisted.source_chunks == fixture.source_chunks
    assert persisted.recent_developments == fixture.recent_developments
    assert persisted.evidence_gaps == fixture.evidence_gaps
    assert persisted.source_checksums == fixture.source_checksums
    assert persisted.knowledge_pack_freshness_hash == fixture.knowledge_pack_freshness_hash
    assert persisted.cache_key == fixture.cache_key
    assert persisted.no_live_external_calls is True
    assert persisted.exports_full_source_documents is False


def test_fixture_fallback_is_byte_equivalent_when_reader_is_missing_empty_or_failing():
    fixture = build_asset_knowledge_pack_result("VOO")

    assert build_asset_knowledge_pack_result("VOO").model_dump(mode="json") == fixture.model_dump(mode="json")
    assert (
        build_asset_knowledge_pack_result("VOO", persisted_reader=FakeKnowledgePackReader({})).model_dump(mode="json")
        == fixture.model_dump(mode="json")
    )
    assert (
        build_asset_knowledge_pack_result("VOO", persisted_reader=FailingKnowledgePackReader()).model_dump(mode="json")
        == fixture.model_dump(mode="json")
    )

    miss = read_persisted_knowledge_pack_response("VOO", reader=FakeKnowledgePackReader({}))
    not_configured = read_persisted_knowledge_pack_response("VOO")
    failed = read_persisted_knowledge_pack_response("VOO", reader=FailingKnowledgePackReader())

    assert miss.status == "miss"
    assert not_configured.status == "not_configured"
    assert failed.status == "reader_error"


def test_non_generated_states_still_fall_back_to_metadata_only_fixture_responses():
    for ticker in ["SPY", "TQQQ", "ZZZZ"]:
        fixture = build_asset_knowledge_pack_result(ticker)
        fallback = build_asset_knowledge_pack_result(ticker, persisted_reader=FakeKnowledgePackReader({}))

        assert fallback.model_dump(mode="json") == fixture.model_dump(mode="json")
        assert fallback.generated_output_available is False
        assert fallback.source_document_ids == []
        assert fallback.citation_ids == []
        assert fallback.source_documents == []
        assert fallback.normalized_facts == []
        assert fallback.source_chunks == []
        assert fallback.recent_developments == []
        assert fallback.source_checksums == []
        assert fallback.counts.evidence_gap_count == 1


def test_invalid_source_use_persisted_records_are_rejected_and_do_not_replace_fixture_output():
    records = _serialized_voo_records()
    source = records.source_documents[0]
    invalid_source = source.model_copy(
        update={
            "source_use_policy": "metadata_only",
            "permitted_operations": {
                **source.permitted_operations,
                "can_support_generated_output": False,
                "can_support_citations": False,
            },
        }
    )
    invalid_records = records.model_copy(
        update={"source_documents": [invalid_source, *records.source_documents[1:]]}
    )
    reader = FakeKnowledgePackReader({"VOO": invalid_records})

    read_result = read_persisted_knowledge_pack_response("VOO", reader=reader)
    fallback = build_asset_knowledge_pack_result("VOO", persisted_reader=reader)

    assert read_result.status == "contract_error"
    assert "cannot support generated-output use" in read_result.message
    assert fallback.model_dump(mode="json") == build_asset_knowledge_pack_result("VOO").model_dump(mode="json")


def test_acquisition_pack_reader_is_valid_but_public_fixture_fallback_handles_non_generated_routes():
    repository = InMemoryAssetKnowledgePackRepository()
    repository.persist(_acquisition_voo_records())

    read_result = read_persisted_knowledge_pack_response("VOO", reader=repository)
    response = build_asset_knowledge_pack_result("VOO", persisted_reader=repository)

    assert read_result.status == "found"
    assert response.ticker == "VOO"
    assert response.build_state.value == "available"
    assert response.generated_output_available is False
    assert response.generated_route is None
    assert response.source_documents
    assert response.source_checksums


def test_wrong_asset_persisted_records_are_rejected_and_do_not_replace_fixture_output():
    records = _serialized_voo_records()
    wrong_source = records.source_documents[0].model_copy(update={"asset_ticker": "QQQ"})
    invalid_records = records.model_copy(
        update={"source_documents": [wrong_source, *records.source_documents[1:]]}
    )
    reader = FakeKnowledgePackReader({"VOO": invalid_records})

    read_result = read_persisted_knowledge_pack_response("VOO", reader=reader)
    fallback = build_asset_knowledge_pack_result("VOO", persisted_reader=reader)

    assert read_result.status == "contract_error"
    assert "not knowledge-pack asset VOO" in read_result.message
    assert fallback.model_dump(mode="json") == build_asset_knowledge_pack_result("VOO").model_dump(mode="json")


def test_reader_returning_different_ticker_is_rejected():
    records = _serialized_voo_records()
    reader = FakeKnowledgePackReader({"QQQ": records})

    read_result = read_persisted_knowledge_pack_response("QQQ", reader=reader)

    assert read_result.status == "contract_error"
    assert "not requested ticker QQQ" in read_result.message


def test_retrieval_repository_imports_do_not_open_database_or_live_provider_paths():
    source = __import__("pathlib").Path("backend/retrieval_repository.py").read_text(encoding="utf-8")

    forbidden = [
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "requests",
        "httpx",
        "OPENROUTER",
        "api_key",
        "psycopg",
        "sqlalchemy",
    ]
    for marker in forbidden:
        assert marker not in source


def test_invalid_reader_shape_is_a_controlled_contract_error():
    result = read_persisted_knowledge_pack_response("VOO", reader=object())

    assert result.status == "contract_error"
    assert "must expose read_knowledge_pack_records" in result.message


def test_deserialisation_contract_errors_stay_visible_to_direct_repository_callers():
    records = _serialized_voo_records()
    wrong_source = records.source_documents[0].model_copy(update={"asset_ticker": "QQQ"})
    invalid_records = records.model_copy(
        update={"source_documents": [wrong_source, *records.source_documents[1:]]}
    )

    with pytest.raises(Exception, match="not knowledge-pack asset VOO"):
        AssetKnowledgePackRepository().deserialize(invalid_records)
