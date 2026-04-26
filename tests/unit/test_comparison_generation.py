from pathlib import Path
from typing import Any

from backend.citations import CitationEvidence, CitationValidationStatus
from backend.comparison import (
    PlannedComparisonClaim,
    generate_comparison,
    read_persisted_comparison_response,
    validate_comparison_response,
    validate_generated_comparison_claims,
)
from backend.cache import (
    build_cache_key,
    build_comparison_pack_freshness_input,
    build_generated_output_freshness_input,
    cache_entry_metadata_from_generated_output,
    compute_generated_output_freshness_hash,
    compute_knowledge_pack_freshness_hash,
)
from backend.generated_output_cache_repository import (
    GeneratedOutputArtifactCategory,
    InMemoryGeneratedOutputCacheRepository,
    build_generated_output_cache_records,
)
from backend.models import AssetStatus, CacheEntryKind, CacheKeyMetadata, CacheScope, CompareResponse, FreshnessState, SourceDocument, SourceUsePolicy
from backend.repositories.knowledge_packs import AssetKnowledgePackRepository
from backend.retrieval import build_asset_knowledge_pack, build_comparison_knowledge_pack
from backend.retrieval import build_asset_knowledge_pack_result
from backend.safety import find_forbidden_output_phrases


ROOT = Path(__file__).resolve().parents[2]


def test_voo_qqq_comparison_is_schema_valid_and_source_backed():
    pack = build_comparison_knowledge_pack("VOO", "QQQ")
    comparison = generate_comparison("VOO", "QQQ")
    validated = CompareResponse.model_validate(comparison.model_dump(mode="json"))

    assert validated.left_asset.ticker == "VOO"
    assert validated.right_asset.ticker == "QQQ"
    assert validated.state.status is AssetStatus.supported
    assert validated.comparison_type == "etf_vs_etf"
    assert validated.bottom_line_for_beginners is not None
    assert validated.citations

    dimensions = {difference.dimension for difference in validated.key_differences}
    assert {"Benchmark", "Expense ratio", "Holdings count", "Breadth", "Educational role"} <= dimensions

    citation_ids = {citation.citation_id for citation in validated.citations}
    source_ids = {source.source_document_id for source in validated.source_documents}
    used_citation_ids = {
        *{citation_id for item in validated.key_differences for citation_id in item.citation_ids},
        *validated.bottom_line_for_beginners.citation_ids,
    }
    assert used_citation_ids <= citation_ids
    assert {citation.source_document_id for citation in validated.citations} <= {
        source.source_document_id for source in pack.comparison_sources
    }
    assert {citation.source_document_id for citation in validated.citations} <= source_ids
    assert source_ids <= {source.source_document_id for source in pack.comparison_sources}
    assert all(source.title for source in validated.source_documents)
    assert all(source.publisher for source in validated.source_documents)
    assert all(source.source_type for source in validated.source_documents)
    assert all(source.url for source in validated.source_documents)
    assert all(source.published_at or source.as_of_date for source in validated.source_documents)
    assert all(source.retrieved_at for source in validated.source_documents)
    assert all(source.freshness_state is FreshnessState.fresh for source in validated.source_documents)
    assert all(source.is_official is True for source in validated.source_documents)
    assert all(source.supporting_passage for source in validated.source_documents)
    assert validate_comparison_response(validated, pack).valid
    assert validated.evidence_availability is not None
    assert validated.evidence_availability.schema_version == "comparison-evidence-availability-v1"
    assert validated.evidence_availability.availability_state.value == "available"
    assert validated.evidence_availability.left_asset.ticker == "VOO"
    assert validated.evidence_availability.right_asset.ticker == "QQQ"
    assert set(validated.evidence_availability.required_dimensions) == {
        "Benchmark",
        "Expense ratio",
        "Holdings count",
        "Breadth",
        "Educational role",
    }
    assert {dimension.dimension for dimension in validated.evidence_availability.required_evidence_dimensions} == {
        "Benchmark",
        "Expense ratio",
        "Holdings count",
        "Breadth",
        "Educational role",
    }
    assert all(
        dimension.availability_state.value == "available"
        for dimension in validated.evidence_availability.required_evidence_dimensions
    )
    assert all(
        binding.citation_id in citation_ids
        and binding.source_document_id in source_ids
        and binding.supports_generated_claim is True
        for binding in validated.evidence_availability.citation_bindings
    )
    assert {
        binding.side_role.value for binding in validated.evidence_availability.citation_bindings
    } >= {"left_side_support", "right_side_support"}
    assert {
        binding.side_role.value for binding in validated.evidence_availability.claim_bindings
    } == {"shared_comparison_support"}
    assert {
        reference.source_document_id for reference in validated.evidence_availability.source_references
    } <= source_ids
    assert {
        reference.allowlist_status.value for reference in validated.evidence_availability.source_references
    } == {"allowed"}
    assert {
        reference.source_use_policy.value for reference in validated.evidence_availability.source_references
    } <= {"full_text_allowed", "summary_allowed"}
    assert all(
        reference.permitted_operations.can_support_generated_output
        for reference in validated.evidence_availability.source_references
    )
    assert validated.evidence_availability.diagnostics.no_live_external_calls is True
    assert validated.evidence_availability.diagnostics.no_new_generated_output is True
    assert validated.evidence_availability.diagnostics.availability_contract_created_generated_output is False


def test_voo_qqq_comparison_supports_reverse_ticker_order():
    pack = build_comparison_knowledge_pack("QQQ", "VOO")
    comparison = generate_comparison("QQQ", "VOO")

    assert comparison.left_asset.ticker == "QQQ"
    assert comparison.right_asset.ticker == "VOO"
    assert comparison.comparison_type == "etf_vs_etf"
    assert comparison.key_differences[0].plain_english_summary.startswith("QQQ tracks")
    assert comparison.evidence_availability is not None
    assert comparison.evidence_availability.left_asset.ticker == "QQQ"
    assert comparison.evidence_availability.right_asset.ticker == "VOO"
    left_side_assets = {
        item.asset_ticker
        for item in comparison.evidence_availability.evidence_items
        if item.side_role.value == "left_side_support"
    }
    right_side_assets = {
        item.asset_ticker
        for item in comparison.evidence_availability.evidence_items
        if item.side_role.value == "right_side_support"
    }
    assert left_side_assets == {"QQQ"}
    assert right_side_assets == {"VOO"}
    assert comparison.source_documents
    assert {source.source_document_id for source in comparison.source_documents} <= {
        source.source_document_id for source in pack.comparison_sources
    }
    assert validate_comparison_response(comparison, pack).valid


def test_knowledge_pack_builder_does_not_change_comparison_output():
    before = generate_comparison("VOO", "QQQ").model_dump(mode="json")
    build_result = build_asset_knowledge_pack_result("VOO")
    after = generate_comparison("VOO", "QQQ").model_dump(mode="json")

    assert build_result.build_state.value == "available"
    assert after == before


def test_persisted_comparison_read_prefers_valid_same_pack_records_when_supplied():
    default = generate_comparison("VOO", "QQQ")
    pack_records = _persisted_pack_records(["VOO", "QQQ"])
    cache_records = _comparison_cache_records("VOO", "QQQ")

    read = read_persisted_comparison_response(
        "VOO",
        "QQQ",
        persisted_pack_reader=pack_records,
        generated_output_cache_reader={("VOO", "QQQ"): cache_records},
    )

    assert read.found
    assert read.comparison is not None
    assert read.comparison.model_dump(mode="json") == default.model_dump(mode="json")
    assert read.diagnostics == ("comparison:persisted_hit",)
    assert "prompt" not in " ".join(read.diagnostics).lower()
    assert "secret" not in " ".join(read.diagnostics).lower()


def test_valid_comparison_generation_writes_same_pack_cache_metadata_when_configured():
    writer = InMemoryGeneratedOutputCacheRepository()
    default = generate_comparison("VOO", "QQQ")
    generated = generate_comparison("VOO", "QQQ", generated_output_cache_writer=writer)
    records = writer.read_comparison_records("VOO", "QQQ")

    assert generated.model_dump(mode="json") == default.model_dump(mode="json")
    assert records is not None
    envelope = records.envelopes[0]
    assert envelope.artifact_category == GeneratedOutputArtifactCategory.comparison_output.value
    assert envelope.comparison_left_ticker == "VOO"
    assert envelope.comparison_right_ticker == "QQQ"
    assert envelope.asset_ticker is None
    assert envelope.cacheable is True
    assert set(envelope.citation_ids) <= {citation for row in records.source_checksums for citation in row.citation_ids}


def test_default_comparison_path_remains_fixture_backed_without_persisted_readers():
    expected = generate_comparison("VOO", "QQQ").model_dump(mode="json")
    read = read_persisted_comparison_response("VOO", "QQQ")
    actual = generate_comparison("VOO", "QQQ").model_dump(mode="json")

    assert read.status == "not_configured"
    assert actual == expected


def test_invalid_comparison_cache_falls_back_to_fixture_output():
    expected = generate_comparison("VOO", "QQQ").model_dump(mode="json")
    cache_records = _comparison_cache_records("VOO", "QQQ")
    wrong_right = cache_records.envelopes[0].model_copy(update={"comparison_right_ticker": "SPY"})
    invalid_cache = cache_records.model_copy(update={"envelopes": [wrong_right]})

    read = read_persisted_comparison_response(
        "VOO",
        "QQQ",
        persisted_pack_reader=_persisted_pack_records(["VOO", "QQQ"]),
        generated_output_cache_reader={("VOO", "QQQ"): invalid_cache},
    )
    actual = generate_comparison(
        "VOO",
        "QQQ",
        persisted_pack_reader=_persisted_pack_records(["VOO", "QQQ"]),
        generated_output_cache_reader={("VOO", "QQQ"): invalid_cache},
    ).model_dump(mode="json")

    assert read.status == "contract_error"
    assert actual == expected


def test_persisted_comparison_rejects_wrong_left_identity_and_wrong_pack_citations():
    expected = generate_comparison("VOO", "QQQ").model_dump(mode="json")
    wrong_pack_reader = {"VOO": _persisted_pack_records(["QQQ"])["QQQ"], "QQQ": _persisted_pack_records(["QQQ"])["QQQ"]}

    wrong_identity = read_persisted_comparison_response(
        "VOO",
        "QQQ",
        persisted_pack_reader=wrong_pack_reader,
        generated_output_cache_reader={("VOO", "QQQ"): _comparison_cache_records("VOO", "QQQ")},
    )
    assert wrong_identity.status == "contract_error"

    cache_records = _comparison_cache_records("VOO", "QQQ")
    wrong_citation = cache_records.envelopes[0].model_copy(update={"citation_ids": ["c_fact_aapl_primary_business"]})
    wrong_citation_records = cache_records.model_copy(update={"envelopes": [wrong_citation]})
    wrong_citation_read = read_persisted_comparison_response(
        "VOO",
        "QQQ",
        persisted_pack_reader=_persisted_pack_records(["VOO", "QQQ"]),
        generated_output_cache_reader={("VOO", "QQQ"): wrong_citation_records},
    )
    fallback = generate_comparison(
        "VOO",
        "QQQ",
        persisted_pack_reader=_persisted_pack_records(["VOO", "QQQ"]),
        generated_output_cache_reader={("VOO", "QQQ"): wrong_citation_records},
    ).model_dump(mode="json")

    assert wrong_citation_read.status == "contract_error"
    assert fallback == expected


def test_persisted_comparison_preserves_reverse_order():
    default = generate_comparison("QQQ", "VOO")
    read = read_persisted_comparison_response(
        "QQQ",
        "VOO",
        persisted_pack_reader=_persisted_pack_records(["QQQ", "VOO"]),
        generated_output_cache_reader={("QQQ", "VOO"): _comparison_cache_records("QQQ", "VOO")},
    )

    assert read.found
    assert read.comparison is not None
    assert read.comparison.left_asset.ticker == "QQQ"
    assert read.comparison.right_asset.ticker == "VOO"
    assert read.comparison.model_dump(mode="json") == default.model_dump(mode="json")


def test_persisted_comparison_does_not_create_no_local_or_blocked_comparisons():
    no_local = read_persisted_comparison_response(
        "AAPL",
        "VOO",
        persisted_pack_reader=_persisted_pack_records(["AAPL", "VOO"]),
        generated_output_cache_reader={("AAPL", "VOO"): _comparison_cache_records("VOO", "QQQ")},
    )
    unsupported = generate_comparison(
        "VOO",
        "BTC",
        persisted_pack_reader=_persisted_pack_records(["VOO"]),
        generated_output_cache_reader={("VOO", "BTC"): _comparison_cache_records("VOO", "QQQ")},
    )

    assert no_local.status == "blocked_state"
    assert generate_comparison("AAPL", "VOO").evidence_availability.availability_state.value == "no_local_pack"
    assert unsupported.comparison_type == "unavailable"
    assert unsupported.evidence_availability.availability_state.value == "unsupported"


def test_persisted_comparison_rejects_source_use_freshness_and_safety_blocks():
    expected = generate_comparison("VOO", "QQQ").model_dump(mode="json")
    pack_records = _persisted_pack_records(["VOO", "QQQ"])
    voo_records = pack_records["VOO"]
    blocked_source = voo_records.source_documents[0].model_copy(
        update={"source_use_policy": SourceUsePolicy.metadata_only.value}
    )
    source_use_read = read_persisted_comparison_response(
        "VOO",
        "QQQ",
        persisted_pack_reader={**pack_records, "VOO": voo_records.model_copy(update={"source_documents": [blocked_source, *voo_records.source_documents[1:]]})},
        generated_output_cache_reader={("VOO", "QQQ"): _comparison_cache_records("VOO", "QQQ")},
    )

    cache_records = _comparison_cache_records("VOO", "QQQ")
    stale_source_states = {
        **cache_records.envelopes[0].source_freshness_states,
        cache_records.envelopes[0].source_document_ids[0]: "stale",
    }
    stale_envelope = cache_records.envelopes[0].model_copy(
        update={"source_freshness_states": stale_source_states, "section_freshness_labels": {"comparison": "fresh"}}
    )
    stale_read = read_persisted_comparison_response(
        "VOO",
        "QQQ",
        persisted_pack_reader=pack_records,
        generated_output_cache_reader={("VOO", "QQQ"): cache_records.model_copy(update={"envelopes": [stale_envelope]})},
    )

    unsafe_fact = next(fact for fact in voo_records.normalized_facts if fact.field_name == "beginner_role")
    unsafe_records = voo_records.model_copy(
        update={
            "normalized_facts": [
                fact.model_copy(update={"value": "you should buy this fund"})
                if fact.fact_id == unsafe_fact.fact_id
                else fact
                for fact in voo_records.normalized_facts
            ]
        }
    )
    unsafe_read = read_persisted_comparison_response(
        "VOO",
        "QQQ",
        persisted_pack_reader={**pack_records, "VOO": unsafe_records},
        generated_output_cache_reader={("VOO", "QQQ"): cache_records},
    )
    fallback = generate_comparison(
        "VOO",
        "QQQ",
        persisted_pack_reader={**pack_records, "VOO": unsafe_records},
        generated_output_cache_reader={("VOO", "QQQ"): cache_records},
    ).model_dump(mode="json")

    assert source_use_read.status == "contract_error"
    assert stale_read.status == "contract_error"
    assert unsafe_read.status == "contract_error"
    assert fallback == expected


def test_unavailable_comparisons_do_not_generate_claims_or_citations():
    cases = [
        ("VOO", "BTC", AssetStatus.unsupported, "unsupported"),
        ("VOO", "TQQQ", AssetStatus.unsupported, "unsupported"),
        ("VOO", "GME", AssetStatus.unknown, "out_of_scope"),
        ("VOO", "SPY", AssetStatus.unknown, "eligible_not_cached"),
        ("VOO", "ZZZZ", AssetStatus.unknown, "unknown"),
        ("AAPL", "VOO", AssetStatus.unknown, "no_local_pack"),
    ]

    for left_ticker, right_ticker, expected_status, expected_availability_state in cases:
        comparison = generate_comparison(left_ticker, right_ticker)

        assert comparison.state.status is expected_status
        assert comparison.comparison_type == "unavailable"
        assert comparison.key_differences == []
        assert comparison.bottom_line_for_beginners is None
        assert comparison.citations == []
        assert comparison.source_documents == []
        assert comparison.evidence_availability is not None
        assert comparison.evidence_availability.availability_state.value == expected_availability_state
        assert comparison.evidence_availability.evidence_items == []
        assert comparison.evidence_availability.claim_bindings == []
        assert comparison.evidence_availability.citation_bindings == []
        assert comparison.evidence_availability.source_references == []
        assert comparison.evidence_availability.diagnostics.generated_comparison_available is False
        assert comparison.evidence_availability.diagnostics.no_live_external_calls is True
        assert comparison.evidence_availability.diagnostics.no_new_generated_output is True
        assert all(
            dimension.availability_state.value == expected_availability_state
            for dimension in comparison.evidence_availability.required_evidence_dimensions
        )


def test_comparison_validation_surfaces_missing_and_insufficient_evidence():
    pack = build_comparison_knowledge_pack("VOO", "QQQ")
    comparison = generate_comparison("VOO", "QQQ")

    missing = comparison.model_copy(deep=True)
    missing.key_differences[0].citation_ids = []
    assert validate_comparison_response(missing, pack).status is CitationValidationStatus.missing_citation

    insufficient = comparison.model_copy(deep=True)
    insufficient.key_differences[0].citation_ids = [insufficient.key_differences[0].citation_ids[0]]
    assert validate_comparison_response(insufficient, pack).status is CitationValidationStatus.insufficient_evidence

    outside_pack = comparison.model_copy(deep=True)
    outside_pack.key_differences[0].citation_ids = ["c_fact_aapl_primary_business"]
    assert validate_comparison_response(outside_pack, pack).status is CitationValidationStatus.citation_not_found


def test_comparison_source_metadata_validation_rejects_missing_wrong_stale_unsupported_and_empty_metadata():
    pack = build_comparison_knowledge_pack("VOO", "QQQ")
    comparison = generate_comparison("VOO", "QQQ")

    missing = comparison.model_copy(deep=True)
    missing.source_documents = []
    assert validate_comparison_response(missing, pack).status is CitationValidationStatus.citation_not_found

    wrong_asset = comparison.model_copy(deep=True)
    for citation in wrong_asset.citations:
        citation.source_document_id = "src_aapl_10k_fixture"
    wrong_asset.source_documents = [_aapl_source_document()]
    assert validate_comparison_response(wrong_asset, pack).status is CitationValidationStatus.wrong_asset

    stale = comparison.model_copy(deep=True)
    stale.source_documents[0].freshness_state = FreshnessState.stale
    assert validate_comparison_response(stale, pack).status is CitationValidationStatus.stale_source

    unsupported = comparison.model_copy(deep=True)
    unsupported.source_documents[0].source_type = "news_article"
    assert validate_comparison_response(unsupported, pack).status is CitationValidationStatus.unsupported_source

    insufficient = comparison.model_copy(deep=True)
    insufficient.source_documents[0].supporting_passage = ""
    assert validate_comparison_response(insufficient, pack).status is CitationValidationStatus.insufficient_evidence


def test_comparison_claim_validation_rejects_wrong_stale_unsupported_and_empty_evidence():
    pack = build_comparison_knowledge_pack("VOO", "QQQ")
    claim = PlannedComparisonClaim(
        claim_id="claim_bad_comparison",
        claim_text="A comparison claim must stay inside the VOO and QQQ comparison pack.",
        citation_ids=["c_voo_bad", "c_qqq_ok"],
        required_asset_tickers=["VOO", "QQQ"],
    )
    qqq_ok = CitationEvidence(
        citation_id="c_qqq_ok",
        asset_ticker="QQQ",
        source_document_id="src_qqq_fact_sheet_fixture",
        source_type="issuer_fact_sheet",
        supporting_text="QQQ fixture describes Nasdaq-100 exposure.",
    )

    wrong_asset = validate_generated_comparison_claims(
        pack,
        [PlannedComparisonClaim(**{**claim.__dict__, "citation_ids": ["c_aapl_bad", "c_qqq_ok"]})],
        [
            CitationEvidence(
                citation_id="c_aapl_bad",
                asset_ticker="AAPL",
                source_document_id="src_aapl_10k_fixture",
                source_type="sec_filing",
                supporting_text="Apple 10-K fixture.",
            ),
            qqq_ok,
        ],
    )
    stale = validate_generated_comparison_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="c_voo_bad",
                asset_ticker="VOO",
                source_document_id="src_voo_stale",
                source_type="issuer_fact_sheet",
                freshness_state=FreshnessState.stale,
                supporting_text="Old VOO fact sheet fixture.",
            ),
            qqq_ok,
        ],
    )
    unsupported = validate_generated_comparison_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="c_voo_bad",
                asset_ticker="VOO",
                source_document_id="src_voo_news",
                source_type="news_article",
                supporting_text="Generic news fixture.",
            ),
            qqq_ok,
        ],
    )
    insufficient = validate_generated_comparison_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="c_voo_bad",
                asset_ticker="VOO",
                source_document_id="src_voo_empty",
                source_type="issuer_fact_sheet",
                supporting_text="",
            ),
            qqq_ok,
        ],
    )

    assert wrong_asset.status is CitationValidationStatus.wrong_asset
    assert stale.status is CitationValidationStatus.stale_source
    assert unsupported.status is CitationValidationStatus.unsupported_source
    assert insufficient.status is CitationValidationStatus.insufficient_evidence


def test_generated_comparison_copy_avoids_forbidden_advice_phrases():
    for pair in [("VOO", "QQQ"), ("QQQ", "VOO"), ("VOO", "BTC"), ("AAPL", "VOO")]:
        comparison = generate_comparison(*pair)
        assert find_forbidden_output_phrases(_flatten_text(comparison.model_dump(mode="json"))) == []


def test_comparison_generation_module_does_not_import_network_clients():
    comparison_source = (ROOT / "backend" / "comparison.py").read_text(encoding="utf-8")

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in comparison_source


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    return ""


def _aapl_source_document() -> SourceDocument:
    return SourceDocument(
        source_document_id="src_aapl_10k_fixture",
        source_type="sec_filing",
        title="Apple Form 10-K fixture excerpt",
        publisher="U.S. SEC",
        url="https://www.sec.gov/",
        published_at="2025-11-01",
        as_of_date="2025-09-27",
        retrieved_at="2026-04-20T00:00:00Z",
        freshness_state=FreshnessState.fresh,
        is_official=True,
        supporting_passage="Apple 10-K fixture evidence.",
    )


def _persisted_pack_records(tickers: list[str]) -> dict[str, Any]:
    repository = AssetKnowledgePackRepository()
    return {
        ticker: repository.serialize(
            build_asset_knowledge_pack_result(ticker),
            retrieval_pack=build_asset_knowledge_pack(ticker),
        )
        for ticker in tickers
    }


def _comparison_cache_records(left_ticker: str, right_ticker: str) -> Any:
    comparison_pack = build_comparison_knowledge_pack(left_ticker, right_ticker)
    comparison = generate_comparison(left_ticker, right_ticker)
    response_source_ids = {source.source_document_id for source in comparison.source_documents}
    knowledge_input = build_comparison_pack_freshness_input(comparison_pack)
    knowledge_input = knowledge_input.model_copy(
        update={
            "source_checksums": [
                checksum for checksum in knowledge_input.source_checksums if checksum.source_document_id in response_source_ids
            ]
        }
    )
    knowledge_hash = compute_knowledge_pack_freshness_hash(knowledge_input)
    generated_input = build_generated_output_freshness_input(
        output_identity=f"comparison:{left_ticker}-to-{right_ticker}",
        entry_kind=CacheEntryKind.comparison,
        scope=CacheScope.comparison,
        schema_version="comparison-v1",
        prompt_version="comparison-prompt-v1",
        model_name="deterministic-fixture-model",
        knowledge_input=knowledge_input,
    )
    generated_hash = compute_generated_output_freshness_hash(generated_input)
    key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.comparison,
            scope=CacheScope.comparison,
            comparison_left_ticker=left_ticker,
            comparison_right_ticker=right_ticker,
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
        citation_ids=[],
        created_at="2026-04-25T18:33:44Z",
        expires_at="2026-05-02T18:33:44Z",
    )
    records = build_generated_output_cache_records(
        cache_entry_id=f"generated-output-{left_ticker.lower()}-{right_ticker.lower()}-comparison",
        output_identity=f"comparison:{left_ticker}-to-{right_ticker}",
        mode_or_output_type="beginner-comparison",
        artifact_category=GeneratedOutputArtifactCategory.comparison_output,
        cache_metadata=metadata,
        generated_freshness_input=generated_input,
        knowledge_freshness_input=knowledge_input,
        knowledge_pack_freshness_hash=knowledge_hash,
        created_at="2026-04-25T18:33:44Z",
        ttl_seconds=604800,
    )
    citations_by_source: dict[str, list[str]] = {}
    for citation in comparison.citations:
        citations_by_source.setdefault(citation.source_document_id, []).append(citation.citation_id)
    source_rows = [
        row.model_copy(update={"citation_ids": sorted(citations_by_source.get(row.source_document_id, []))})
        for row in records.source_checksums
    ]
    citation_ids = sorted({citation.citation_id for citation in comparison.citations})
    return records.model_copy(
        update={
            "envelopes": [records.envelopes[0].model_copy(update={"citation_ids": citation_ids})],
            "artifacts": [records.artifacts[0].model_copy(update={"citation_ids": citation_ids})],
            "source_checksums": source_rows,
            "validation_statuses": [
                records.validation_statuses[0].model_copy(
                    update={
                        "important_claim_count": len(citation_ids),
                        "cited_important_claim_count": len(citation_ids),
                    }
                )
            ],
        }
    )
