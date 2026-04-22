from pathlib import Path

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
    SourceChecksumInput,
)
from backend.providers import fetch_mock_provider_response
from backend.retrieval import build_asset_knowledge_pack, build_comparison_knowledge_pack
from backend.models import ProviderKind, ProviderResponseState


ROOT = Path(__file__).resolve().parents[2]


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
