import importlib.util
from pathlib import Path

import pytest

from backend.cache import (
    build_cache_key,
    build_comparison_pack_freshness_input,
    build_generated_output_freshness_input,
    build_knowledge_pack_freshness_input,
    cache_entry_metadata_from_generated_output,
    compute_generated_output_freshness_hash,
    compute_knowledge_pack_freshness_hash,
    compute_source_document_checksum,
    evaluate_cache_revalidation,
    source_checksum_from_provider_attribution,
    source_checksum_from_retrieval_source,
)
from backend.generated_output_cache_repository import (
    GENERATED_OUTPUT_CACHE_REPOSITORY_BOUNDARY,
    GENERATED_OUTPUT_CACHE_TABLES,
    GeneratedOutputArtifactCategory,
    GeneratedOutputArtifactRecordRow,
    GeneratedOutputCacheContractError,
    GeneratedOutputCacheEnvelopeRow,
    GeneratedOutputCacheRepository,
    GeneratedOutputCacheRepositoryRecords,
    GeneratedOutputDiagnosticRow,
    GeneratedOutputSourceChecksumRow,
    GeneratedOutputValidationStatusRow,
    InMemoryGeneratedOutputCacheRepository,
    build_generated_output_cache_records,
    generated_output_cache_repository_metadata,
    validate_generated_output_cache_records,
)
from backend.models import (
    CacheEntryKind,
    CacheEntryMetadata,
    CacheEntryState,
    CacheInvalidationReason,
    CacheKeyMetadata,
    CacheScope,
    FreshnessFactInput,
    FreshnessRecentEventInput,
    FreshnessState,
    GeneratedOutputFreshnessInput,
    KnowledgePackFreshnessInput,
    SectionFreshnessInput,
    SourceAllowlistStatus,
    SourceChecksumInput,
    SourceParserStatus,
    SourceReviewStatus,
    SourceUsePolicy,
)
from backend.providers import fetch_mock_provider_response
from backend.retrieval import build_asset_knowledge_pack, build_comparison_knowledge_pack
from backend.retrieval import build_asset_knowledge_pack_result
from backend.models import ProviderKind, ProviderResponseState


ROOT = Path(__file__).resolve().parents[2]


class FakeDurableSession:
    def __init__(self):
        self.records = {}
        self.rows = []
        self.commits = 0

    def save_repository_record(self, collection, key, records):
        self.records[(collection, key)] = records

    def get_repository_record(self, collection, key):
        return self.records.get((collection, key))

    def add_all(self, rows):
        self.rows.extend(rows)

    def commit(self):
        self.commits += 1


def _generated_cache_records(ticker: str = "VOO") -> GeneratedOutputCacheRepositoryRecords:
    source_checksum = compute_source_document_checksum(
        SourceChecksumInput(
            source_document_id=f"src_{ticker.lower()}_fresh_fixture",
            asset_ticker=ticker,
            source_type="issuer_fact_sheet",
            source_rank=1,
            publisher="Issuer Fixture",
            retrieved_at="2026-04-25T18:04:25Z",
            freshness_state=FreshnessState.fresh,
            citation_ids=[f"c_{ticker.lower()}_overview"],
            fact_bindings=[f"fact_{ticker.lower()}_overview"],
            cache_allowed=True,
            export_allowed=False,
        )
    )
    knowledge_input = KnowledgePackFreshnessInput(
        asset_ticker=ticker,
        pack_identity=ticker,
        source_checksums=[source_checksum],
        canonical_facts=[
            FreshnessFactInput(
                fact_id=f"fact_{ticker.lower()}_overview",
                asset_ticker=ticker,
                field_name="overview",
                value="Fixture overview fact",
                freshness_state=FreshnessState.fresh,
                evidence_state="supported",
                source_document_ids=[source_checksum.source_document_id],
                citation_ids=[f"c_{ticker.lower()}_overview"],
            )
        ],
        recent_events=[],
        evidence_gaps=[],
        page_freshness_state=FreshnessState.fresh,
        section_freshness_labels=[
            SectionFreshnessInput(section_id="beginner_summary", freshness_state=FreshnessState.fresh, evidence_state="supported")
        ],
    )
    knowledge_hash = compute_knowledge_pack_freshness_hash(knowledge_input)
    generated_input = build_generated_output_freshness_input(
        output_identity=f"asset:{ticker}",
        entry_kind=CacheEntryKind.asset_page,
        scope=CacheScope.asset,
        schema_version="asset-page-v1",
        prompt_version="asset-page-prompt-v1",
        model_name="deterministic-fixture-model",
        knowledge_input=knowledge_input,
    )
    generated_hash = compute_generated_output_freshness_hash(generated_input)
    key = build_cache_key(_asset_page_key(ticker, generated_hash))
    metadata = cache_entry_metadata_from_generated_output(
        cache_key=key,
        freshness_input=generated_input,
        freshness_hash=generated_hash,
        citation_ids=[citation for checksum in generated_input.source_checksums for citation in checksum.citation_ids],
        created_at="2026-04-25T18:04:25Z",
        expires_at="2026-05-02T18:04:25Z",
        cache_allowed=True,
        export_allowed=False,
    )
    return build_generated_output_cache_records(
        cache_entry_id=f"generated-output-{ticker.lower()}-overview",
        output_identity=f"asset:{ticker}",
        mode_or_output_type="beginner-overview",
        artifact_category=GeneratedOutputArtifactCategory.asset_overview_section,
        cache_metadata=metadata,
        generated_freshness_input=generated_input,
        knowledge_freshness_input=knowledge_input,
        knowledge_pack_freshness_hash=knowledge_hash,
        created_at="2026-04-25T18:04:25Z",
        ttl_seconds=604800,
    )


def _asset_page_key(ticker: str, input_hash: str = "abc123") -> CacheKeyMetadata:
    return CacheKeyMetadata(
        entry_kind=CacheEntryKind.asset_page,
        scope=CacheScope.asset,
        asset_ticker=ticker,
        mode_or_output_type="beginner",
        schema_version="asset-page-v1",
        source_freshness_state=FreshnessState.fresh,
        prompt_version="asset-page-prompt-v1",
        model_name="deterministic-fixture-model",
        input_freshness_hash=input_hash,
    )


def test_cache_key_generation_is_deterministic_and_contains_identity_metadata():
    first = build_cache_key(_asset_page_key("VOO"))
    second = build_cache_key(_asset_page_key("voo"))

    assert first == second
    assert "asset-voo" in first
    assert "asset-page-v1" in first
    assert "asset-page" in first
    assert "beginner" in first
    assert "freshness-fresh" in first
    assert "prompt-asset-page-prompt-v1" in first
    assert "model-deterministic-fixture-model" in first


def test_comparison_cache_keys_preserve_left_right_direction():
    forward = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.comparison,
            scope=CacheScope.comparison,
            comparison_left_ticker="VOO",
            comparison_right_ticker="QQQ",
            pack_identity="fixture-voo-qqq",
            mode_or_output_type="beginner",
            schema_version="comparison-v1",
            source_freshness_state=FreshnessState.fresh,
            prompt_version="comparison-prompt-v1",
            model_name="deterministic-fixture-model",
        )
    )
    reverse = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.comparison,
            scope=CacheScope.comparison,
            comparison_left_ticker="QQQ",
            comparison_right_ticker="VOO",
            pack_identity="fixture-voo-qqq",
            mode_or_output_type="beginner",
            schema_version="comparison-v1",
            source_freshness_state=FreshnessState.fresh,
            prompt_version="comparison-prompt-v1",
            model_name="deterministic-fixture-model",
        )
    )

    assert forward != reverse
    assert "comparison-voo-to-qqq" in forward
    assert "comparison-qqq-to-voo" in reverse


def test_pre_cache_job_cache_key_is_deterministic_without_storage_or_reuse_for_unavailable_states():
    key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.pre_cache_job,
            scope=CacheScope.job,
            asset_ticker="SPY",
            mode_or_output_type="launch-universe",
            schema_version="pre-cache-job-v1",
            source_freshness_state=FreshnessState.unavailable,
            input_freshness_hash="pre-cache-launch-universe-v1",
        )
    )
    repeated = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.pre_cache_job,
            scope=CacheScope.job,
            asset_ticker="spy",
            mode_or_output_type="launch-universe",
            schema_version="pre-cache-job-v1",
            source_freshness_state=FreshnessState.unavailable,
            input_freshness_hash="pre-cache-launch-universe-v1",
        )
    )
    blocked = evaluate_cache_revalidation(None, key, input_state=CacheEntryState.unavailable)

    assert key == repeated
    assert "job" in key
    assert "pre-cache-job" in key
    assert "asset-spy" in key
    assert blocked.reusable is False
    assert blocked.invalidation_reason is CacheInvalidationReason.unavailable


def test_source_checksum_is_order_insensitive_and_excludes_raw_chunk_text():
    pack = build_asset_knowledge_pack("VOO")
    source = pack.source_documents[0]

    checksum = source_checksum_from_retrieval_source(
        source,
        chunks=pack.source_chunks,
        facts=pack.normalized_facts,
        recent_events=pack.recent_developments,
    )
    reordered = source_checksum_from_retrieval_source(
        source,
        chunks=list(reversed(pack.source_chunks)),
        facts=list(reversed(pack.normalized_facts)),
        recent_events=list(reversed(pack.recent_developments)),
    )
    changed_chunk = pack.source_chunks[0].model_copy(update={"chunk": pack.source_chunks[0].chunk.model_copy(update={"text": "Changed local fixture passage."})})
    changed = source_checksum_from_retrieval_source(
        source,
        chunks=[changed_chunk, *pack.source_chunks[1:]],
        facts=pack.normalized_facts,
        recent_events=pack.recent_developments,
    )

    assert checksum.checksum == reordered.checksum
    assert checksum.checksum != changed.checksum
    dumped = checksum.model_dump(mode="json")
    assert "VOO seeks to track" not in str(dumped)
    assert dumped["source_document_id"] == source.source_document_id
    assert dumped["asset_ticker"] == "VOO"
    assert dumped["freshness_state"] == "fresh"


def test_provider_checksum_respects_cache_permission_contract():
    response = fetch_mock_provider_response(ProviderKind.market_reference, "AAPL")
    checksum = source_checksum_from_provider_attribution(
        response.source_attributions[0],
        facts=response.facts,
        recent_events=response.recent_developments,
    )

    denied = compute_source_document_checksum(
        SourceChecksumInput(
            source_document_id="restricted-paid-news-example",
            asset_ticker="AAPL",
            source_type="paid_news",
            publisher="Restricted Provider",
            freshness_state=FreshnessState.fresh,
            cache_allowed=False,
            fact_bindings=["fact|safe-id|hash-only"],
        )
    )

    assert checksum.cache_allowed is True
    assert denied.cache_allowed is False
    decision = evaluate_cache_revalidation(None, "restricted-key", cache_allowed=denied.cache_allowed)
    assert decision.state is CacheEntryState.permission_limited
    assert decision.reusable is False
    assert decision.invalidation_reason is CacheInvalidationReason.permission_limited


def test_knowledge_pack_hash_is_order_insensitive_for_sources_facts_and_events():
    pack = build_asset_knowledge_pack("QQQ")
    freshness_input = build_knowledge_pack_freshness_input(pack)
    reordered = KnowledgePackFreshnessInput(
        **{
            **freshness_input.model_dump(mode="json"),
            "source_checksums": list(reversed(freshness_input.source_checksums)),
            "canonical_facts": list(reversed(freshness_input.canonical_facts)),
            "recent_events": list(reversed(freshness_input.recent_events)),
            "evidence_gaps": list(reversed(freshness_input.evidence_gaps)),
            "section_freshness_labels": list(reversed(freshness_input.section_freshness_labels)),
        }
    )

    assert compute_knowledge_pack_freshness_hash(freshness_input) == compute_knowledge_pack_freshness_hash(reordered)


def test_knowledge_pack_build_result_uses_cache_freshness_hash_contract():
    result = build_asset_knowledge_pack_result("VOO")
    pack = build_asset_knowledge_pack("VOO")
    expected_input = build_knowledge_pack_freshness_input(pack, section_freshness_labels=result.section_freshness)
    expected_hash = compute_knowledge_pack_freshness_hash(expected_input)

    assert result.knowledge_pack_freshness_hash == expected_hash
    assert result.source_checksums == expected_input.source_checksums
    assert result.cache_key is not None
    assert "asset-voo" in result.cache_key
    assert "knowledge-pack" in result.cache_key
    assert result.cache_revalidation is not None
    assert result.cache_revalidation.state is CacheEntryState.miss
    assert result.cache_revalidation.expected_freshness_hash == expected_hash

    changed_label = result.section_freshness[0].model_copy(update={"freshness_state": FreshnessState.stale})
    changed_input = KnowledgePackFreshnessInput(
        **{
            **expected_input.model_dump(mode="json"),
            "section_freshness_labels": [changed_label, *result.section_freshness[1:]],
        }
    )
    assert expected_hash != compute_knowledge_pack_freshness_hash(changed_input)


def test_non_cached_knowledge_pack_states_block_generated_output_cache_reuse():
    for ticker, expected_state in [
        ("SPY", CacheEntryState.eligible_not_cached),
        ("BTC", CacheEntryState.unsupported),
        ("ZZZZ", CacheEntryState.unknown),
    ]:
        result = build_asset_knowledge_pack_result(ticker)

        assert result.generated_output_available is False
        assert result.reusable_generated_output_cache_hit is False
        assert result.cache_revalidation is not None
        assert result.cache_revalidation.state is expected_state
        assert result.cache_revalidation.reusable is False
        assert result.source_checksums == []
        assert result.knowledge_pack_freshness_hash is None


def test_freshness_hash_changes_when_evidence_inputs_change():
    pack = build_asset_knowledge_pack("VOO")
    freshness_input = build_knowledge_pack_freshness_input(pack)
    baseline = compute_knowledge_pack_freshness_hash(freshness_input)
    first_fact = freshness_input.canonical_facts[0]
    changed_fact = first_fact.model_copy(update={"value": "changed normalized fact value"})
    changed_input = KnowledgePackFreshnessInput(
        **{
            **freshness_input.model_dump(mode="json"),
            "canonical_facts": [changed_fact, *freshness_input.canonical_facts[1:]],
        }
    )

    assert baseline != compute_knowledge_pack_freshness_hash(changed_input)


def test_generated_output_hash_changes_for_prompt_model_schema_source_fact_event_and_freshness():
    pack = build_asset_knowledge_pack("AAPL")
    knowledge_input = build_knowledge_pack_freshness_input(pack)
    generated_input = build_generated_output_freshness_input(
        output_identity="asset:AAPL",
        entry_kind=CacheEntryKind.asset_page,
        scope=CacheScope.asset,
        schema_version="asset-page-v1",
        prompt_version="asset-page-prompt-v1",
        model_name="deterministic-fixture-model",
        knowledge_input=knowledge_input,
    )
    baseline = compute_generated_output_freshness_hash(generated_input)

    def changed_hash(**updates):
        return compute_generated_output_freshness_hash(generated_input.model_copy(update=updates))

    changed_source = generated_input.source_checksums[0].model_copy(update={"checksum": "changed-source-checksum"})
    changed_fact = generated_input.canonical_facts[0].model_copy(update={"value": "changed fact"})
    changed_event = generated_input.recent_events[0].model_copy(update={"event_date": "2026-04-02"})

    assert baseline != changed_hash(prompt_version="asset-page-prompt-v2")
    assert baseline != changed_hash(model_name="another-model")
    assert baseline != changed_hash(schema_version="asset-page-v2")
    assert baseline != changed_hash(source_freshness_state=FreshnessState.stale)
    assert baseline != changed_hash(source_checksums=[changed_source, *generated_input.source_checksums[1:]])
    assert baseline != changed_hash(canonical_facts=[changed_fact, *generated_input.canonical_facts[1:]])
    assert baseline != changed_hash(recent_events=[changed_event, *generated_input.recent_events[1:]])


def test_comparison_freshness_hash_uses_directional_identity_for_generated_output():
    comparison_pack = build_comparison_knowledge_pack("VOO", "QQQ")
    knowledge_input = build_comparison_pack_freshness_input(comparison_pack)
    forward = build_generated_output_freshness_input(
        output_identity="comparison:VOO-to-QQQ",
        entry_kind=CacheEntryKind.comparison,
        scope=CacheScope.comparison,
        schema_version="comparison-v1",
        prompt_version="comparison-prompt-v1",
        model_name="deterministic-fixture-model",
        knowledge_input=knowledge_input,
    )
    reverse = forward.model_copy(update={"output_identity": "comparison:QQQ-to-VOO"})

    assert compute_generated_output_freshness_hash(forward) != compute_generated_output_freshness_hash(reverse)


def test_revalidation_returns_hit_miss_hash_mismatch_and_expired_states():
    expected_hash = "fresh-hash"
    key = build_cache_key(_asset_page_key("VOO", expected_hash))
    entry = CacheEntryMetadata(
        cache_key=key,
        entry_kind=CacheEntryKind.asset_page,
        scope=CacheScope.asset,
        schema_version="asset-page-v1",
        generated_output_freshness_hash=expected_hash,
        source_document_ids=["src_voo_fact_sheet_fixture"],
        citation_ids=["c_voo_profile"],
        source_freshness_states={"src_voo_fact_sheet_fixture": FreshnessState.fresh},
        section_freshness_labels={"top_risks": FreshnessState.fresh},
        created_at="2026-04-20T00:00:00Z",
        expires_at="2026-04-23T00:00:00Z",
        cache_allowed=True,
    )

    hit = evaluate_cache_revalidation(entry, key, expected_hash, current_time="2026-04-22T00:00:00Z")
    miss = evaluate_cache_revalidation(None, key, expected_hash)
    mismatch = evaluate_cache_revalidation(entry, key, "different-hash")
    expired = evaluate_cache_revalidation(entry, key, expected_hash, current_time="2026-04-24T00:00:00Z")

    assert hit.state is CacheEntryState.hit
    assert hit.reusable is True
    assert hit.source_document_ids == ["src_voo_fact_sheet_fixture"]
    assert hit.citation_ids == ["c_voo_profile"]
    assert miss.state is CacheEntryState.miss
    assert mismatch.state is CacheEntryState.hash_mismatch
    assert expired.state is CacheEntryState.expired
    assert {miss.reusable, mismatch.reusable, expired.reusable} == {False}


def test_revalidation_blocks_stale_unknown_unavailable_unsupported_and_eligible_not_cached_inputs():
    cases = [
        (CacheEntryState.stale, CacheInvalidationReason.stale_input),
        (CacheEntryState.unknown, CacheInvalidationReason.unknown),
        (CacheEntryState.unavailable, CacheInvalidationReason.unavailable),
        (CacheEntryState.unsupported, CacheInvalidationReason.unsupported),
        (CacheEntryState.eligible_not_cached, CacheInvalidationReason.eligible_not_cached),
        (ProviderResponseState.unsupported, CacheInvalidationReason.unsupported),
        (ProviderResponseState.unknown, CacheInvalidationReason.unknown),
        (ProviderResponseState.unavailable, CacheInvalidationReason.unavailable),
        (ProviderResponseState.eligible_not_cached, CacheInvalidationReason.eligible_not_cached),
    ]

    for state, reason in cases:
        decision = evaluate_cache_revalidation(None, "cache-key", input_state=state)
        assert decision.reusable is False
        assert decision.invalidation_reason is reason


def test_cache_module_has_no_live_call_store_or_secret_imports():
    source = (ROOT / "backend" / "cache.py").read_text(encoding="utf-8")
    forbidden = [
        "import requests",
        "import httpx",
        "urllib",
        "socket",
        "import redis",
        "psycopg",
        "sqlalchemy",
        "boto3",
        "openai",
        "anthropic",
        "os.environ",
        "api_key",
    ]
    for needle in forbidden:
        assert needle not in source


def test_cache_entry_metadata_preserves_source_citation_and_freshness_fields():
    generated = GeneratedOutputFreshnessInput(
        output_identity="asset:TEST",
        entry_kind=CacheEntryKind.asset_page,
        scope=CacheScope.asset,
        schema_version="asset-page-v1",
        source_freshness_state=FreshnessState.fresh,
        prompt_version="prompt-v1",
        model_name="model-v1",
        source_checksums=[
            compute_source_document_checksum(
                SourceChecksumInput(
                    source_document_id="src_test",
                    asset_ticker="TEST",
                    source_type="issuer_fact_sheet",
                    publisher="Issuer",
                    freshness_state=FreshnessState.fresh,
                    citation_ids=["c_test"],
                )
            )
        ],
        canonical_facts=[
            FreshnessFactInput(
                fact_id="fact_test",
                asset_ticker="TEST",
                field_name="benchmark",
                value="Fixture Index",
                freshness_state=FreshnessState.fresh,
                evidence_state="supported",
                source_document_ids=["src_test"],
                citation_ids=["c_test"],
            )
        ],
        recent_events=[
            FreshnessRecentEventInput(
                event_id="event_test",
                asset_ticker="TEST",
                event_type="no_high_signal_review",
                event_date=None,
                freshness_state=FreshnessState.fresh,
                evidence_state="no_major_recent_development",
                source_document_id="src_test",
                citation_ids=["c_test"],
            )
        ],
    )
    freshness_hash = compute_generated_output_freshness_hash(generated)
    metadata = cache_entry_metadata_from_generated_output(
        cache_key="cache-key",
        freshness_input=generated,
        freshness_hash=freshness_hash,
        citation_ids=["c_test"],
        export_allowed=False,
    )

    assert metadata.source_document_ids == ["src_test"]
    assert metadata.citation_ids == ["c_test"]
    assert metadata.source_freshness_states == {"src_test": FreshnessState.fresh}
    assert metadata.prompt_version == "prompt-v1"
    assert metadata.model_name == "model-v1"
    assert metadata.export_allowed is False


def test_cache_entry_metadata_blocks_generated_output_for_restricted_source_use_tiers():
    restricted_checksums = [
        compute_source_document_checksum(
            SourceChecksumInput(
                source_document_id=f"src_{policy.value}",
                asset_ticker="TEST",
                source_type="provider_fixture",
                publisher="Restricted Fixture",
                freshness_state=FreshnessState.fresh,
                citation_ids=[f"c_{policy.value}"],
                cache_allowed=True,
                allowlist_status=(
                    SourceAllowlistStatus.rejected if policy is SourceUsePolicy.rejected else SourceAllowlistStatus.allowed
                ),
                source_use_policy=policy,
            )
        )
        for policy in [SourceUsePolicy.metadata_only, SourceUsePolicy.link_only, SourceUsePolicy.rejected]
    ]
    for checksum in restricted_checksums:
        generated = GeneratedOutputFreshnessInput(
            output_identity="asset:TEST",
            entry_kind=CacheEntryKind.asset_page,
            scope=CacheScope.asset,
            schema_version="asset-page-v1",
            source_freshness_state=FreshnessState.fresh,
            source_checksums=[checksum],
            canonical_facts=[],
            recent_events=[],
            evidence_gaps=[],
            section_freshness_labels=[
                SectionFreshnessInput(
                    section_id="beginner_summary",
                    freshness_state=FreshnessState.fresh,
                    evidence_state="supported",
                )
            ],
        )
        freshness_hash = compute_generated_output_freshness_hash(generated)
        metadata = cache_entry_metadata_from_generated_output(
            cache_key="restricted-cache-key",
            freshness_input=generated,
            freshness_hash=freshness_hash,
            citation_ids=checksum.citation_ids,
            cache_allowed=True,
        )
        decision = evaluate_cache_revalidation(None, "restricted-cache-key", cache_allowed=metadata.cache_allowed)

        assert checksum.cache_allowed is True
        assert metadata.cache_allowed is False
        assert decision.state is CacheEntryState.permission_limited
        assert decision.reusable is False


def test_generated_output_cache_repository_metadata_is_dormant_and_explicit():
    metadata = generated_output_cache_repository_metadata()

    assert metadata.boundary == GENERATED_OUTPUT_CACHE_REPOSITORY_BOUNDARY
    assert metadata.opens_connection_on_import is False
    assert metadata.creates_runtime_tables is False
    assert tuple(metadata.tables) == GENERATED_OUTPUT_CACHE_TABLES
    assert set(GENERATED_OUTPUT_CACHE_TABLES) == {
        "generated_output_cache_envelopes",
        "generated_output_cache_artifacts",
        "generated_output_cache_source_checksums",
        "generated_output_cache_knowledge_pack_hash_inputs",
        "generated_output_cache_freshness_hash_inputs",
        "generated_output_cache_validation_statuses",
        "generated_output_cache_diagnostics",
    }
    assert "generated_output_freshness_hash" in metadata.tables["generated_output_cache_envelopes"].columns
    assert "knowledge_pack_freshness_hash" in metadata.tables["generated_output_cache_knowledge_pack_hash_inputs"].columns
    assert "source_use_policy" in metadata.tables["generated_output_cache_source_checksums"].columns
    assert "stores_raw_user_text" in metadata.tables["generated_output_cache_artifacts"].columns
    assert "compact_metadata" in metadata.tables["generated_output_cache_diagnostics"].columns


def test_durable_generated_output_cache_repository_persists_metadata_and_reads_by_asset_category():
    records = _generated_cache_records("VOO")
    session = FakeDurableSession()
    repository = GeneratedOutputCacheRepository(session=session, commit_on_write=True)

    persisted = repository.persist(records)
    read_back = repository.read_asset_overview_records("voo")

    assert persisted == records
    assert read_back == records
    assert repository.read_generated_output_cache_records("VOO") == records
    assert session.records[("generated_output_cache_entry", "generated-output-voo-overview")] == records
    assert session.records[("generated_output_cache_lookup", "asset:VOO:asset_overview_section")] == records
    assert session.commits == 2
    assert all(artifact.stores_payload_text is False for artifact in persisted.artifacts)
    assert all(envelope.stores_raw_model_reasoning is False for envelope in persisted.envelopes)


def test_generated_output_cache_categories_cover_required_artifacts():
    assert {category.value for category in GeneratedOutputArtifactCategory} >= {
        "asset_overview_section",
        "comparison_output",
        "grounded_chat_answer_artifact",
        "export_payload_metadata",
        "source_list_export_metadata",
        "source_checksum_record",
        "knowledge_pack_hash_input",
        "generated_output_hash_input",
        "diagnostics_metadata",
        "weekly_news_focus_section",
        "ai_comprehensive_analysis_artifact",
    }


def test_generated_output_cache_migration_is_importable_and_limited_to_contract_tables():
    revision_path = ROOT / "alembic" / "versions" / "20260425_0005_generated_output_cache_contracts.py"
    source = revision_path.read_text(encoding="utf-8")
    spec = importlib.util.spec_from_file_location("generated_output_cache_revision", revision_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.revision == "20260425_0005"
    assert module.down_revision == "20260425_0004"
    assert module.GENERATED_OUTPUT_CACHE_TABLE_NAMES == GENERATED_OUTPUT_CACHE_TABLES
    for table_name in GENERATED_OUTPUT_CACHE_TABLES:
        assert f'"{table_name}"' in source

    forbidden_table_markers = [
        "chat_sessions",
        "chat_messages",
        "user_accounts",
        "provider_secrets",
        "source_snapshot_artifacts",
        "asset_knowledge_pack_envelopes",
        "public_urls",
    ]
    for marker in forbidden_table_markers:
        assert marker not in module.GENERATED_OUTPUT_CACHE_TABLE_NAMES
        assert f'op.create_table("{marker}"' not in source


def test_generated_output_cache_records_preserve_hashes_validation_and_citation_bindings():
    records = _generated_cache_records("VOO")
    validated = GeneratedOutputCacheRepository().persist(records)
    envelope = validated.envelopes[0]

    assert validated.table_names == GENERATED_OUTPUT_CACHE_TABLES
    assert envelope.asset_ticker == "VOO"
    assert envelope.comparison_id is None
    assert envelope.cacheable is True
    assert envelope.generated_output_available is True
    assert envelope.prompt_version == "asset-page-prompt-v1"
    assert envelope.model_name == "deterministic-fixture-model"
    assert envelope.knowledge_pack_freshness_hash
    assert envelope.generated_output_freshness_hash
    assert envelope.validation_status == "passed"
    assert envelope.safety_status == "educational"
    assert envelope.source_use_status == "allowed"
    assert envelope.citation_coverage_status == "complete"
    assert all(row.source_document_id in envelope.source_document_ids for row in records.source_checksums)
    assert set(envelope.citation_ids) <= {citation for row in records.source_checksums for citation in row.citation_ids}
    assert records.artifacts[0].stores_payload_text is False


def test_in_memory_generated_output_cache_repository_reads_metadata_by_artifact_category():
    repository = InMemoryGeneratedOutputCacheRepository()
    records = _generated_cache_records("VOO")

    persisted = repository.persist(records)
    read_back = repository.read_asset_overview_records("voo")

    assert persisted.envelopes[0].cache_entry_id == "generated-output-voo-overview"
    assert read_back is not None
    assert read_back.envelopes[0].artifact_category == GeneratedOutputArtifactCategory.asset_overview_section.value
    assert repository.read_generated_output_cache_records("VOO").envelopes[0].cache_entry_id == "generated-output-voo-overview"


def test_comparison_generated_output_cache_preserves_left_right_identity_and_pack_binding():
    comparison_pack = build_comparison_knowledge_pack("VOO", "QQQ")
    knowledge_input = build_comparison_pack_freshness_input(comparison_pack)
    knowledge_hash = compute_knowledge_pack_freshness_hash(knowledge_input)
    generated_input = build_generated_output_freshness_input(
        output_identity="comparison:VOO-to-QQQ",
        entry_kind=CacheEntryKind.comparison,
        scope=CacheScope.comparison,
        schema_version="comparison-v1",
        prompt_version="comparison-prompt-v1",
        model_name="deterministic-fixture-model",
        knowledge_input=knowledge_input,
    )
    fresh_comparison_sources = [
        checksum for checksum in generated_input.source_checksums if checksum.freshness_state is FreshnessState.fresh
    ]
    knowledge_input = knowledge_input.model_copy(update={"source_checksums": fresh_comparison_sources})
    generated_input = generated_input.model_copy(update={"source_checksums": fresh_comparison_sources})
    knowledge_hash = compute_knowledge_pack_freshness_hash(knowledge_input)
    generated_hash = compute_generated_output_freshness_hash(generated_input)
    key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.comparison,
            scope=CacheScope.comparison,
            comparison_left_ticker="VOO",
            comparison_right_ticker="QQQ",
            pack_identity=comparison_pack.comparison_pack_id,
            mode_or_output_type="beginner",
            schema_version="comparison-v1",
            source_freshness_state=FreshnessState.fresh,
            prompt_version="comparison-prompt-v1",
            model_name="deterministic-fixture-model",
            input_freshness_hash=generated_hash,
        )
    )
    metadata = cache_entry_metadata_from_generated_output(
        cache_key=key,
        freshness_input=generated_input,
        freshness_hash=generated_hash,
        citation_ids=[citation for checksum in generated_input.source_checksums for citation in checksum.citation_ids],
        created_at="2026-04-25T18:04:25Z",
    )

    records = build_generated_output_cache_records(
        cache_entry_id="generated-output-voo-qqq-comparison",
        output_identity="comparison:VOO-to-QQQ",
        mode_or_output_type="beginner-comparison",
        artifact_category=GeneratedOutputArtifactCategory.comparison_output,
        cache_metadata=metadata,
        generated_freshness_input=generated_input,
        knowledge_freshness_input=knowledge_input,
        knowledge_pack_freshness_hash=knowledge_hash,
        created_at="2026-04-25T18:04:25Z",
    )

    envelope = records.envelopes[0]
    assert envelope.asset_ticker is None
    assert envelope.comparison_id == comparison_pack.comparison_pack_id
    assert envelope.comparison_left_ticker == "VOO"
    assert envelope.comparison_right_ticker == "QQQ"

    wrong_right = records.knowledge_pack_hash_inputs[0].model_copy(update={"comparison_right_ticker": "SPY"})
    with pytest.raises(GeneratedOutputCacheContractError, match="left/right identity"):
        validate_generated_output_cache_records(records.model_copy(update={"knowledge_pack_hash_inputs": [wrong_right]}))


def test_generated_output_cache_blocks_wrong_asset_wrong_citation_and_source_policy_violations():
    records = _generated_cache_records("VOO")

    wrong_asset_source = records.source_checksums[0].model_copy(update={"asset_ticker": "QQQ"})
    with pytest.raises(GeneratedOutputCacheContractError, match="same asset or comparison pack"):
        validate_generated_output_cache_records(records.model_copy(update={"source_checksums": [wrong_asset_source, *records.source_checksums[1:]]}))

    bad_citation = records.envelopes[0].model_copy(update={"citation_ids": ["wrong-pack-citation"]})
    with pytest.raises(GeneratedOutputCacheContractError, match="citations must bind"):
        validate_generated_output_cache_records(records.model_copy(update={"envelopes": [bad_citation]}))

    metadata_only = records.source_checksums[0].model_copy(
        update={"source_use_policy": SourceUsePolicy.metadata_only.value, "cache_allowed": True}
    )
    with pytest.raises(GeneratedOutputCacheContractError, match="Source-use policy"):
        validate_generated_output_cache_records(records.model_copy(update={"source_checksums": [metadata_only, *records.source_checksums[1:]]}))

    rejected = records.source_checksums[0].model_copy(update={"allowlist_status": "rejected"})
    with pytest.raises(GeneratedOutputCacheContractError, match="allowlist status"):
        validate_generated_output_cache_records(records.model_copy(update={"source_checksums": [rejected, *records.source_checksums[1:]]}))

    parser_invalid = records.source_checksums[0].model_copy(
        update={"parser_status": SourceParserStatus.failed.value, "parser_failure_diagnostics": "fixture parse failed"}
    )
    with pytest.raises(GeneratedOutputCacheContractError, match="Golden Asset Source Handoff"):
        validate_generated_output_cache_records(
            records.model_copy(update={"source_checksums": [parser_invalid, *records.source_checksums[1:]]})
        )

    pending_review = records.source_checksums[0].model_copy(update={"review_status": SourceReviewStatus.pending_review.value})
    with pytest.raises(GeneratedOutputCacheContractError, match="Golden Asset Source Handoff"):
        validate_generated_output_cache_records(
            records.model_copy(update={"source_checksums": [pending_review, *records.source_checksums[1:]]})
        )


def test_generated_output_cache_blocks_unsafe_unvalidated_unknown_and_unlabeled_freshness_states():
    records = _generated_cache_records("VOO")

    validation_failed = records.validation_statuses[0].model_copy(update={"citation_validation_status": "failed"})
    with pytest.raises(GeneratedOutputCacheContractError, match="validation"):
        validate_generated_output_cache_records(records.model_copy(update={"validation_statuses": [validation_failed]}))

    unsupported_claim = records.validation_statuses[0].model_copy(update={"unsupported_claim_count": 1})
    with pytest.raises(GeneratedOutputCacheContractError, match="unsupported"):
        validate_generated_output_cache_records(records.model_copy(update={"validation_statuses": [unsupported_claim]}))

    advice_like = records.validation_statuses[0].model_copy(update={"advice_like_detected": True})
    with pytest.raises(GeneratedOutputCacheContractError, match="advice-like"):
        validate_generated_output_cache_records(records.model_copy(update={"validation_statuses": [advice_like]}))

    blocked = records.envelopes[0].model_copy(update={"support_status": "unsupported"})
    with pytest.raises(GeneratedOutputCacheContractError, match="Blocked states"):
        validate_generated_output_cache_records(records.model_copy(update={"envelopes": [blocked]}))

    unknown_source = records.envelopes[0].model_copy(
        update={"source_freshness_states": {records.source_checksums[0].source_document_id: "unknown"}}
    )
    with pytest.raises(GeneratedOutputCacheContractError, match="Unknown or unavailable"):
        validate_generated_output_cache_records(records.model_copy(update={"envelopes": [unknown_source]}))

    stale_without_label = records.envelopes[0].model_copy(
        update={"source_freshness_states": {records.source_checksums[0].source_document_id: "stale"}, "section_freshness_labels": {"page": "fresh"}}
    )
    with pytest.raises(GeneratedOutputCacheContractError, match="Stale inputs"):
        validate_generated_output_cache_records(records.model_copy(update={"envelopes": [stale_without_label]}))

    unavailable_with_label = records.envelopes[0].model_copy(
        update={
            "source_freshness_states": {records.source_checksums[0].source_document_id: "unavailable"},
            "section_freshness_labels": {"source_limitation": "unavailable"},
            "evidence_state_labels": {"source_limitation": "unavailable"},
        }
    )
    unavailable_source = records.source_checksums[0].model_copy(update={"freshness_state": "unavailable"})
    validate_generated_output_cache_records(
        records.model_copy(
            update={
                "envelopes": [unavailable_with_label],
                "source_checksums": [unavailable_source, *records.source_checksums[1:]],
            }
        )
    )


def test_chat_safe_answer_artifact_metadata_does_not_store_raw_user_text_or_transcripts():
    records = _generated_cache_records("VOO")
    envelope = records.envelopes[0].model_copy(
        update={
            "entry_kind": CacheEntryKind.chat_answer.value,
            "cache_scope": CacheScope.chat.value,
            "artifact_category": GeneratedOutputArtifactCategory.grounded_chat_answer_artifact.value,
            "output_identity": "asset:VOO:chat-safe-answer-metadata",
            "mode_or_output_type": "grounded-chat-safe-answer",
        }
    )
    artifact = records.artifacts[0].model_copy(
        update={
            "artifact_category": GeneratedOutputArtifactCategory.grounded_chat_answer_artifact.value,
            "payload_metadata": {"conversation_ttl_days": 7, "answer_artifact_only": True},
        }
    )
    generated_hash_input = records.generated_output_hash_inputs[0].model_copy(
        update={"entry_kind": CacheEntryKind.chat_answer.value, "cache_scope": CacheScope.chat.value}
    )
    validate_generated_output_cache_records(
        records.model_copy(
            update={
                "envelopes": [envelope],
                "artifacts": [artifact],
                "generated_output_hash_inputs": [generated_hash_input],
            }
        )
    )

    raw_text_artifact = artifact.model_copy(update={"stores_raw_user_text": True})
    with pytest.raises(GeneratedOutputCacheContractError, match="metadata only"):
        validate_generated_output_cache_records(
            records.model_copy(
                update={
                    "envelopes": [envelope],
                    "artifacts": [raw_text_artifact],
                    "generated_output_hash_inputs": [generated_hash_input],
                }
            )
        )

    transcript_metadata = artifact.model_copy(update={"payload_metadata": {"transcript": "Should I buy VOO?"}})
    with pytest.raises(GeneratedOutputCacheContractError, match="sanitized"):
        validate_generated_output_cache_records(
            records.model_copy(
                update={
                    "envelopes": [envelope],
                    "artifacts": [transcript_metadata],
                    "generated_output_hash_inputs": [generated_hash_input],
                }
            )
        )


def test_generated_output_cache_diagnostics_are_compact_and_sanitized():
    records = _generated_cache_records("VOO")
    diagnostic = GeneratedOutputDiagnosticRow(
        diagnostic_id="diag-voo-hash-mismatch",
        cache_entry_id=records.envelopes[0].cache_entry_id,
        category="invalidation",
        code="hash_mismatch",
        invalidation_reason="hash_mismatch",
        source_document_ids=records.envelopes[0].source_document_ids,
        checksum_values=records.envelopes[0].source_checksum_ids,
        freshness_states=records.envelopes[0].source_freshness_states,
        created_at="2026-04-25T18:04:25Z",
        compact_metadata={"validation_code": "hash_mismatch", "freshness_state": "fresh"},
    )
    validate_generated_output_cache_records(records.model_copy(update={"diagnostics": [diagnostic]}))

    leaking = diagnostic.model_copy(update={"compact_metadata": {"raw_prompt": "hidden prompt text"}})
    with pytest.raises(GeneratedOutputCacheContractError, match="sanitized"):
        validate_generated_output_cache_records(records.model_copy(update={"diagnostics": [leaking]}))


def test_generated_output_cache_repository_imports_do_not_open_live_database_cache_or_provider_paths():
    repository_source = (ROOT / "backend" / "repositories" / "generated_outputs.py").read_text(encoding="utf-8")

    forbidden = [
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "requests",
        "httpx",
        "redis",
        "boto3",
        "OPENROUTER",
        "openai",
        "os.environ",
        "api_key",
    ]
    for marker in forbidden:
        assert marker not in repository_source

    records = _generated_cache_records("VOO")
    class BadSession:
        pass

    with pytest.raises(GeneratedOutputCacheContractError, match="add_all"):
        GeneratedOutputCacheRepository(session=BadSession()).persist(records)
