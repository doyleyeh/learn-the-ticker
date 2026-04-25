from pathlib import Path
from typing import Any

from backend.cache import (
    build_cache_key,
    build_generated_output_freshness_input,
    build_knowledge_pack_freshness_input,
    cache_entry_metadata_from_generated_output,
    compute_generated_output_freshness_hash,
    compute_knowledge_pack_freshness_hash,
)
from backend.chat import (
    CHAT_PERSISTED_READ_BOUNDARY,
    PlannedChatClaim,
    generate_asset_chat,
    read_persisted_chat_response,
    validate_chat_response,
    validate_generated_chat_claims,
)
from backend.citations import CitationEvidence, CitationValidationStatus
from backend.generated_output_cache_repository import (
    GeneratedOutputArtifactCategory,
    build_generated_output_cache_records,
)
from backend.knowledge_pack_repository import AssetKnowledgePackRepository
from backend.models import (
    AssetStatus,
    CacheEntryKind,
    CacheKeyMetadata,
    CacheScope,
    ChatResponse,
    FreshnessState,
    SafetyClassification,
    SectionFreshnessInput,
    SourceUsePolicy,
)
from backend.retrieval import build_asset_knowledge_pack, build_asset_knowledge_pack_result
from backend.safety import find_forbidden_output_phrases


ROOT = Path(__file__).resolve().parents[2]


def test_supported_chat_intents_are_schema_valid_and_source_backed():
    cases = [
        ("QQQ", "What is this fund?", "Nasdaq-100 Index", "src_qqq_fact_sheet_fixture"),
        ("AAPL", "What does this company do?", "primary business", "src_aapl_10k_fixture"),
        ("VOO", "What does it hold?", "about 500", "src_voo_fact_sheet_fixture"),
        ("QQQ", "What is the biggest risk?", "concentration", "src_qqq_prospectus_fixture"),
        ("VOO", "What changed recently?", "No high-signal recent development", "src_voo_recent_review"),
        ("VOO", "Why do beginners consider it?", "Beginners may study VOO", "src_voo_fact_sheet_fixture"),
    ]

    for ticker, question, expected_text, expected_source in cases:
        pack = build_asset_knowledge_pack(ticker)
        response = generate_asset_chat(ticker, question)
        validated = ChatResponse.model_validate(response.model_dump(mode="json"))

        assert validated.asset.ticker == ticker
        assert validated.asset.status is AssetStatus.supported
        assert validated.safety_classification is SafetyClassification.educational
        assert expected_text in validated.direct_answer
        assert validated.why_it_matters
        assert validated.citations
        assert validated.source_documents
        assert any(citation.source_document_id == expected_source for citation in validated.citations)
        assert any(source.source_document_id == expected_source for source in validated.source_documents)
        _assert_chat_source_metadata_matches_citations(validated)
        assert validated.uncertainty
        assert validate_chat_response(validated, pack).valid


def test_supported_chat_unknown_evidence_does_not_invent_or_cite():
    pack = build_asset_knowledge_pack("AAPL")
    response = generate_asset_chat("AAPL", "Is Apple expensive based on valuation?")

    assert response.safety_classification is SafetyClassification.educational
    assert "Insufficient evidence" in response.direct_answer
    assert "valuation" in " ".join(response.uncertainty).lower()
    assert response.citations == []
    assert response.source_documents == []
    assert validate_chat_response(response, pack).valid


def test_knowledge_pack_builder_does_not_change_chat_output():
    before = generate_asset_chat("QQQ", "What is this fund?").model_dump(mode="json")
    build_result = build_asset_knowledge_pack_result("QQQ")
    after = generate_asset_chat("QQQ", "What is this fund?").model_dump(mode="json")

    assert build_result.build_state.value == "available"
    assert after == before


def test_persisted_chat_read_prefers_valid_same_asset_records_when_supplied():
    default = generate_asset_chat("VOO", "What does it hold?")
    pack_records, cache_records = _persisted_chat_records("VOO", "What does it hold?")

    read = read_persisted_chat_response(
        "voo",
        "What does it hold?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={"VOO": cache_records},
    )
    generated = generate_asset_chat(
        "voo",
        "What does it hold?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={"VOO": cache_records},
    )

    assert CHAT_PERSISTED_READ_BOUNDARY == "chat-persisted-read-boundary-v1"
    assert read.found
    assert read.chat_response is not None
    assert read.diagnostics == ("chat:persisted_hit",)
    assert read.chat_response.model_dump(mode="json") == default.model_dump(mode="json")
    assert generated.model_dump(mode="json") == default.model_dump(mode="json")


def test_default_chat_path_remains_fixture_backed_without_persisted_readers():
    expected = generate_asset_chat("QQQ", "What is this fund?").model_dump(mode="json")
    read = read_persisted_chat_response("QQQ", "What is this fund?")
    actual = generate_asset_chat("QQQ", "What is this fund?").model_dump(mode="json")

    assert read.status == "not_configured"
    assert read.diagnostics == ("reader:not_configured",)
    assert actual == expected


def test_persisted_chat_falls_back_on_missing_failing_and_invalid_cache_records():
    expected = generate_asset_chat("VOO", "What does it hold?").model_dump(mode="json")
    pack_records, cache_records = _persisted_chat_records("VOO", "What does it hold?")
    wrong_kind = cache_records.envelopes[0].model_copy(update={"entry_kind": CacheEntryKind.asset_page.value})
    invalid_cache = cache_records.model_copy(update={"envelopes": [wrong_kind]})

    assert generate_asset_chat(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={},
        generated_output_cache_reader={"VOO": cache_records},
    ).model_dump(mode="json") == expected
    assert generate_asset_chat(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={},
    ).model_dump(mode="json") == expected
    assert generate_asset_chat(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader=_FailingChatCacheReader(),
    ).model_dump(mode="json") == expected

    read = read_persisted_chat_response(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={"VOO": invalid_cache},
    )
    fallback = generate_asset_chat(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={"VOO": invalid_cache},
    ).model_dump(mode="json")

    assert read.status == "contract_error"
    assert read.chat_response is None
    assert fallback == expected


def test_persisted_chat_keeps_advice_and_comparison_redirect_precedence():
    pack_records, cache_records = _persisted_chat_records("VOO", "What does it hold?")
    advice = generate_asset_chat(
        "VOO",
        "Should I buy VOO or QQQ today?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={"VOO": cache_records},
    )
    compare = generate_asset_chat(
        "VOO",
        "How is VOO different from QQQ?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={"VOO": cache_records},
    )
    advice_read = read_persisted_chat_response(
        "VOO",
        "Should I buy VOO?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={"VOO": cache_records},
    )
    compare_read = read_persisted_chat_response(
        "VOO",
        "How is VOO different from QQQ?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={"VOO": cache_records},
    )

    assert advice.safety_classification is SafetyClassification.personalized_advice_redirect
    assert compare.safety_classification is SafetyClassification.compare_route_redirect
    assert advice.citations == []
    assert compare.citations == []
    assert advice_read.diagnostics == ("chat:advice_redirect_precedence",)
    assert compare_read.diagnostics == ("chat:compare_redirect_precedence",)


def test_persisted_chat_rejects_wrong_asset_and_wrong_pack_citations():
    expected = generate_asset_chat("VOO", "What does it hold?").model_dump(mode="json")
    _, qqq_cache_records = _persisted_chat_records("QQQ", "What is this fund?")
    wrong_asset_read = read_persisted_chat_response(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": _persisted_chat_records("QQQ", "What is this fund?")[0]},
        generated_output_cache_reader={"VOO": _persisted_chat_records("VOO", "What does it hold?")[1]},
    )

    wrong_citation = qqq_cache_records.envelopes[0].model_copy(
        update={"asset_ticker": "VOO", "output_identity": "asset:VOO:chat-safe-answer-metadata"}
    )
    wrong_citation_records = qqq_cache_records.model_copy(update={"envelopes": [wrong_citation]})
    wrong_citation_read = read_persisted_chat_response(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": _persisted_chat_records("VOO", "What does it hold?")[0]},
        generated_output_cache_reader={"VOO": wrong_citation_records},
    )
    fallback = generate_asset_chat(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": _persisted_chat_records("VOO", "What does it hold?")[0]},
        generated_output_cache_reader={"VOO": wrong_citation_records},
    ).model_dump(mode="json")

    assert wrong_asset_read.status == "contract_error"
    assert wrong_citation_read.status == "contract_error"
    assert fallback == expected


def test_persisted_chat_rejects_source_use_freshness_safety_and_raw_transcript_blocks():
    expected = generate_asset_chat("VOO", "What does it hold?").model_dump(mode="json")
    pack_records, cache_records = _persisted_chat_records("VOO", "What does it hold?")
    blocked_source = pack_records.source_documents[0].model_copy(
        update={"source_use_policy": SourceUsePolicy.metadata_only.value}
    )
    source_use_read = read_persisted_chat_response(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": pack_records.model_copy(update={"source_documents": [blocked_source, *pack_records.source_documents[1:]]})},
        generated_output_cache_reader={"VOO": cache_records},
    )

    stale_source_states = {
        **cache_records.envelopes[0].source_freshness_states,
        cache_records.envelopes[0].source_document_ids[0]: "stale",
    }
    stale_envelope = cache_records.envelopes[0].model_copy(
        update={"source_freshness_states": stale_source_states, "section_freshness_labels": {"chat_answer": "fresh"}}
    )
    stale_read = read_persisted_chat_response(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={"VOO": cache_records.model_copy(update={"envelopes": [stale_envelope]})},
    )

    unsafe_fact = next(fact for fact in pack_records.normalized_facts if fact.field_name == "holdings_count")
    unsafe_records = pack_records.model_copy(
        update={
            "normalized_facts": [
                fact.model_copy(update={"value": "you should buy this fund"})
                if fact.fact_id == unsafe_fact.fact_id
                else fact
                for fact in pack_records.normalized_facts
            ]
        }
    )
    unsafe_read = read_persisted_chat_response(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": unsafe_records},
        generated_output_cache_reader={"VOO": cache_records},
    )
    raw_transcript = cache_records.envelopes[0].model_copy(update={"stores_chat_transcript": True})
    raw_read = read_persisted_chat_response(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": pack_records},
        generated_output_cache_reader={"VOO": cache_records.model_copy(update={"envelopes": [raw_transcript]})},
    )
    fallback = generate_asset_chat(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": unsafe_records},
        generated_output_cache_reader={"VOO": cache_records},
    ).model_dump(mode="json")

    assert source_use_read.status == "contract_error"
    assert stale_read.status == "contract_error"
    assert unsafe_read.status == "contract_error"
    assert raw_read.status == "contract_error"
    assert fallback == expected


def test_persisted_chat_blocks_non_generated_asset_states_and_sanitizes_diagnostics():
    _, cache_records = _persisted_chat_records("VOO", "What does it hold?")
    for ticker in ["SPY", "BTC", "ZZZZ"]:
        pack_records = AssetKnowledgePackRepository().serialize(build_asset_knowledge_pack_result(ticker))
        read = read_persisted_chat_response(
            ticker,
            "What is this asset?",
            persisted_pack_reader={ticker: pack_records},
            generated_output_cache_reader={ticker: cache_records},
        )
        generated = generate_asset_chat(
            ticker,
            "What is this asset?",
            persisted_pack_reader={ticker: pack_records},
            generated_output_cache_reader={ticker: cache_records},
        )

        assert read.status == "blocked_state"
        assert generated.model_dump(mode="json") == generate_asset_chat(ticker, "What is this asset?").model_dump(mode="json")

    pack_records, cache_records = _persisted_chat_records("VOO", "What does it hold?")
    unsafe_fact = pack_records.normalized_facts[0].model_copy(update={"value": "You should buy VOO now. OPENROUTER secret"})
    result = read_persisted_chat_response(
        "VOO",
        "What does it hold?",
        persisted_pack_reader={"VOO": pack_records.model_copy(update={"normalized_facts": [unsafe_fact, *pack_records.normalized_facts[1:]]})},
        generated_output_cache_reader={"VOO": cache_records},
    )
    diagnostics_text = " ".join(result.diagnostics)

    assert result.status == "contract_error"
    assert "You should buy VOO" not in diagnostics_text
    assert "OPENROUTER" not in diagnostics_text
    for forbidden in ["raw_prompt", "raw_model_reasoning", "raw_user_text", "transcript", "secret"]:
        assert forbidden not in diagnostics_text.lower()


def test_stateless_chat_generation_does_not_create_session_metadata():
    response = generate_asset_chat("QQQ", "What is this fund?")

    assert response.session is None


def test_chat_advice_and_unsupported_redirects_have_no_citations():
    advice = generate_asset_chat("VOO", "Should I buy VOO today?")
    unsupported = generate_asset_chat("BTC", "Should I buy BTC?")

    assert advice.safety_classification is SafetyClassification.personalized_advice_redirect
    assert unsupported.safety_classification is SafetyClassification.unsupported_asset_redirect
    assert advice.citations == []
    assert unsupported.citations == []
    assert advice.source_documents == []
    assert unsupported.source_documents == []
    assert "educational" in f"{advice.direct_answer} {advice.why_it_matters}".lower()
    assert "outside" in unsupported.direct_answer


def test_chat_comparison_questions_redirect_to_compare_workflow_without_multi_asset_citations():
    cases = [
        ("VOO", "How is VOO different from QQQ?", "VOO", "QQQ", "available"),
        ("VOO", "How is QQQ different from VOO?", "QQQ", "VOO", "available"),
        ("QQQ", "Why is this more concentrated than VOO?", "QQQ", "VOO", "available"),
        ("VOO", "AAPL vs VOO", "AAPL", "VOO", "no_local_pack"),
        ("VOO", "VOO vs SPY", "VOO", "SPY", "eligible_not_cached"),
        ("VOO", "VOO vs BTC", "VOO", "BTC", "unsupported"),
        ("VOO", "VOO vs GME", "VOO", "GME", "out_of_scope"),
        ("VOO", "VOO vs ZZZZ", "VOO", "ZZZZ", "unknown"),
    ]

    for ticker, question, expected_left, expected_right, expected_state in cases:
        response = generate_asset_chat(ticker, question)

        assert response.safety_classification is SafetyClassification.compare_route_redirect
        assert response.citations == []
        assert response.source_documents == []
        assert response.compare_route_suggestion is not None
        assert response.compare_route_suggestion.left_ticker == expected_left
        assert response.compare_route_suggestion.right_ticker == expected_right
        assert response.compare_route_suggestion.route == f"/compare?left={expected_left}&right={expected_right}"
        assert response.compare_route_suggestion.comparison_availability_state.value == expected_state
        assert response.compare_route_suggestion.diagnostics.generated_multi_asset_chat_answer is False
        assert response.compare_route_suggestion.diagnostics.mixed_asset_citations_included is False
        assert response.compare_route_suggestion.diagnostics.mixed_asset_source_documents_included is False
        assert "comparison workflow" in response.direct_answer.lower()


def test_advice_redirect_keeps_precedence_when_second_ticker_is_present():
    response = generate_asset_chat("VOO", "Should I buy VOO or QQQ today?")

    assert response.safety_classification is SafetyClassification.personalized_advice_redirect
    assert response.compare_route_suggestion is None
    assert response.citations == []
    assert response.source_documents == []


def test_chat_response_validation_surfaces_missing_and_unknown_citations():
    pack = build_asset_knowledge_pack("QQQ")
    response = generate_asset_chat("QQQ", "What is this fund?")

    missing = response.model_copy(deep=True)
    missing.citations = []
    assert validate_chat_response(missing, pack).status is CitationValidationStatus.missing_citation

    nonexistent = response.model_copy(deep=True)
    nonexistent.citations[0].chunk_id = "chk_voo_profile_001"
    assert validate_chat_response(nonexistent, pack).status is CitationValidationStatus.citation_not_found

    missing_source_metadata = response.model_copy(deep=True)
    missing_source_metadata.source_documents = []
    assert validate_chat_response(missing_source_metadata, pack).status is CitationValidationStatus.citation_not_found


def test_generated_chat_claim_validation_rejects_wrong_stale_unsupported_and_empty_evidence():
    pack = build_asset_knowledge_pack("VOO")
    claim = PlannedChatClaim(
        claim_id="chat_bad_claim",
        claim_text="Chat citations must stay inside the selected asset knowledge pack.",
        citation_ids=["bad"],
        claim_type="factual",
    )

    wrong_asset = validate_generated_chat_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="bad",
                asset_ticker="QQQ",
                source_document_id="src_qqq_fact_sheet_fixture",
                source_type="issuer_fact_sheet",
                supporting_text="QQQ fixture evidence.",
            )
        ],
    )
    stale = validate_generated_chat_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="bad",
                asset_ticker="VOO",
                source_document_id="src_voo_old_fact_sheet",
                source_type="issuer_fact_sheet",
                freshness_state=FreshnessState.stale,
                supporting_text="Old VOO fixture evidence.",
            )
        ],
    )
    unsupported = validate_generated_chat_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="bad",
                asset_ticker="VOO",
                source_document_id="src_voo_news",
                source_type="news_article",
                supporting_text="Generic news fixture evidence.",
            )
        ],
    )
    insufficient = validate_generated_chat_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="bad",
                asset_ticker="VOO",
                source_document_id="src_voo_fact_sheet_fixture",
                source_type="issuer_fact_sheet",
                supporting_text="",
            )
        ],
    )

    assert wrong_asset.status is CitationValidationStatus.wrong_asset
    assert stale.status is CitationValidationStatus.stale_source
    assert unsupported.status is CitationValidationStatus.unsupported_source
    assert insufficient.status is CitationValidationStatus.insufficient_evidence


def test_generated_chat_copy_avoids_forbidden_advice_phrases():
    cases = [
        ("VOO", "What is VOO?"),
        ("QQQ", "What risks should a beginner understand?"),
        ("AAPL", "What does Apple do?"),
        ("AAPL", "Is Apple expensive?"),
        ("VOO", "Should I buy VOO?"),
        ("BTC", "Should I buy BTC?"),
    ]

    for ticker, question in cases:
        response = generate_asset_chat(ticker, question)
        assert find_forbidden_output_phrases(_flatten_text(response.model_dump(mode="json"))) == []


def test_chat_generation_module_does_not_import_network_clients():
    chat_source = (ROOT / "backend" / "chat.py").read_text(encoding="utf-8")

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in chat_source


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    return ""


def _assert_chat_source_metadata_matches_citations(response: ChatResponse) -> None:
    citations_by_id = {citation.citation_id: citation for citation in response.citations}
    sources_by_id = {source.citation_id: source for source in response.source_documents}

    assert set(citations_by_id) == set(sources_by_id)
    for citation_id, citation in citations_by_id.items():
        source = sources_by_id[citation_id]
        assert source.source_document_id == citation.source_document_id
        assert source.chunk_id == citation.chunk_id
        assert source.title
        assert source.source_type
        assert source.url
        assert source.published_at or source.as_of_date
        assert source.retrieved_at
        assert source.freshness_state
        assert source.supporting_passage


class _FailingChatCacheReader:
    def read_chat_answer_records(self, ticker: str):
        raise RuntimeError(f"controlled chat cache failure for {ticker}")


def _persisted_chat_records(ticker: str, question: str):
    pack = build_asset_knowledge_pack(ticker)
    response = generate_asset_chat(ticker, question)
    pack_records = AssetKnowledgePackRepository().serialize(
        build_asset_knowledge_pack_result(ticker),
        retrieval_pack=pack,
    )
    response_source_ids = {source.source_document_id for source in response.source_documents}
    response_citation_ids = {citation.citation_id for citation in response.citations}
    knowledge_input = build_knowledge_pack_freshness_input(pack)
    knowledge_input = knowledge_input.model_copy(
        update={
            "source_checksums": [
                checksum for checksum in knowledge_input.source_checksums if checksum.source_document_id in response_source_ids
            ],
            "section_freshness_labels": [
                SectionFreshnessInput(
                    section_id="page",
                    freshness_state=FreshnessState.fresh,
                    evidence_state="supported",
                ),
                SectionFreshnessInput(
                    section_id="chat_answer",
                    freshness_state=FreshnessState.fresh,
                    evidence_state="supported",
                ),
            ],
        }
    )
    knowledge_hash = compute_knowledge_pack_freshness_hash(knowledge_input)
    generated_input = build_generated_output_freshness_input(
        output_identity=f"asset:{ticker}:chat-safe-answer-metadata",
        entry_kind=CacheEntryKind.chat_answer,
        scope=CacheScope.chat,
        schema_version="chat-answer-v1",
        prompt_version="chat-answer-prompt-v1",
        model_name="deterministic-fixture-model",
        knowledge_input=knowledge_input,
    )
    generated_hash = compute_generated_output_freshness_hash(generated_input)
    cache_key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.chat_answer,
            scope=CacheScope.chat,
            asset_ticker=ticker,
            mode_or_output_type="grounded-chat-safe-answer",
            schema_version="chat-answer-v1",
            source_freshness_state=generated_input.source_freshness_state,
            prompt_version="chat-answer-prompt-v1",
            model_name="deterministic-fixture-model",
            input_freshness_hash=generated_hash,
        )
    )
    cache_metadata = cache_entry_metadata_from_generated_output(
        cache_key=cache_key,
        freshness_input=generated_input,
        freshness_hash=generated_hash,
        citation_ids=[],
        created_at="2026-04-25T18:44:56Z",
        expires_at="2026-05-02T18:44:56Z",
    )
    records = build_generated_output_cache_records(
        cache_entry_id=f"generated-output-{ticker.lower()}-chat-answer",
        output_identity=f"asset:{ticker}:chat-safe-answer-metadata",
        mode_or_output_type="grounded-chat-safe-answer",
        artifact_category=GeneratedOutputArtifactCategory.grounded_chat_answer_artifact,
        cache_metadata=cache_metadata,
        generated_freshness_input=generated_input,
        knowledge_freshness_input=knowledge_input,
        knowledge_pack_freshness_hash=knowledge_hash,
        created_at="2026-04-25T18:44:56Z",
        ttl_seconds=604800,
    )
    citations_by_source: dict[str, list[str]] = {}
    for citation in response.citations:
        citations_by_source.setdefault(citation.source_document_id, []).append(citation.citation_id)
    records = records.model_copy(
        update={
            "envelopes": [
                records.envelopes[0].model_copy(update={"citation_ids": sorted(response_citation_ids)})
            ],
            "source_checksums": [
                row.model_copy(update={"citation_ids": sorted(citations_by_source.get(row.source_document_id, []))})
                for row in records.source_checksums
            ],
            "artifacts": [
                records.artifacts[0].model_copy(
                    update={
                        "citation_ids": sorted(response_citation_ids),
                        "payload_metadata": {"conversation_ttl_days": 7, "answer_artifact_only": True},
                    }
                )
            ],
            "validation_statuses": [
                records.validation_statuses[0].model_copy(
                    update={
                        "important_claim_count": len(response_citation_ids),
                        "cited_important_claim_count": len(response_citation_ids),
                    }
                )
            ],
        }
    )
    return pack_records, records
