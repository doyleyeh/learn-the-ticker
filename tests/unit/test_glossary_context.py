from pathlib import Path

from backend.glossary import TERM_CATALOG, build_glossary_response
from backend.models import GlossaryResponse, GlossaryAssetContextState, SourceUsePolicy
from backend.retrieval import build_asset_knowledge_pack


ROOT = Path(__file__).resolve().parents[2]


def _terms(response: GlossaryResponse) -> dict[str, object]:
    return {term.term_identity.term: term for term in response.terms}


def test_supported_assets_return_required_glossary_terms_and_contract_metadata():
    required_by_ticker = {
        "AAPL": {
            "market cap",
            "revenue",
            "operating margin",
            "EPS",
            "free cash flow",
            "debt",
            "P/E ratio",
            "forward P/E",
            "market risk",
            "concentration risk",
        },
        "VOO": {
            "expense ratio",
            "AUM",
            "benchmark",
            "index",
            "holdings",
            "top 10 concentration",
            "sector exposure",
            "country exposure",
            "bid-ask spread",
            "premium/discount",
            "NAV",
            "liquidity",
            "tracking error",
            "tracking difference",
            "market risk",
            "concentration risk",
        },
        "QQQ": {
            "expense ratio",
            "AUM",
            "benchmark",
            "index",
            "holdings",
            "top 10 concentration",
            "sector exposure",
            "country exposure",
            "bid-ask spread",
            "premium/discount",
            "NAV",
            "liquidity",
            "tracking error",
            "tracking difference",
            "market risk",
            "concentration risk",
        },
    }

    for ticker, required_terms in required_by_ticker.items():
        response = GlossaryResponse.model_validate(build_glossary_response(ticker).model_dump(mode="json"))
        terms = _terms(response)

        assert response.schema_version == "glossary-asset-context-v1"
        assert response.selected_asset.ticker == ticker
        assert response.glossary_state.value == "available"
        assert required_terms <= set(terms)
        assert response.diagnostics.no_live_external_calls is True
        assert response.diagnostics.live_provider_calls_attempted is False
        assert response.diagnostics.live_llm_calls_attempted is False
        assert response.diagnostics.no_new_generated_output is True
        assert response.diagnostics.no_frontend_change_required is True
        assert response.diagnostics.generic_definitions_are_not_evidence is True

        for term in response.terms:
            assert term.generic_definition.simple_definition
            assert term.generic_definition.why_it_matters
            assert term.generic_definition.common_beginner_mistake
            assert term.generic_definition.generic_definition_requires_citation is False


def test_asset_specific_glossary_context_binds_to_same_asset_sources_and_citations():
    for ticker, filtered_term in [("AAPL", "revenue"), ("VOO", "expense ratio"), ("QQQ", "benchmark")]:
        response = build_glossary_response(ticker, term=filtered_term)
        pack = build_asset_knowledge_pack(ticker)
        source_ids = {source.source_document_id for source in pack.source_documents}
        citation_ids = {binding.citation_id for binding in response.citation_bindings}

        assert len(response.terms) == 1
        assert response.terms[0].asset_context.availability_state is GlossaryAssetContextState.available
        assert response.terms[0].asset_context.citation_ids
        assert response.citation_bindings
        assert response.source_references
        assert {binding.asset_ticker for binding in response.citation_bindings} == {ticker}
        assert {binding.source_document_id for binding in response.citation_bindings} <= source_ids
        assert {reference.source_document_id for reference in response.source_references} <= source_ids
        assert set(response.terms[0].asset_context.citation_ids) <= citation_ids
        assert all(binding.supports_asset_specific_context for binding in response.citation_bindings)
        assert all(
            binding.source_use_policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed}
            for binding in response.citation_bindings
        )
        assert all(binding.permitted_operations.can_support_citations for binding in response.citation_bindings)


def test_generic_only_terms_do_not_use_generic_definitions_as_citation_evidence():
    response = build_glossary_response("AAPL", term="market cap")

    assert response.terms[0].term_identity.term == "market cap"
    assert response.terms[0].asset_context.availability_state is GlossaryAssetContextState.generic_only
    assert response.terms[0].asset_context.citation_ids == []
    assert response.evidence_references == []
    assert response.citation_bindings == []
    assert response.source_references == []
    assert response.diagnostics.generic_definitions_are_not_evidence is True
    assert "glossary" not in " ".join(response.terms[0].asset_context.citation_ids).lower()


def test_unavailable_and_stale_or_insufficient_evidence_states_are_preserved():
    unavailable = build_glossary_response("VOO", term="bid-ask spread")
    stale_or_gap = build_glossary_response("VOO", term="top 10 concentration")

    assert unavailable.terms[0].asset_context.availability_state.value in {"unavailable", "insufficient_evidence"}
    assert unavailable.terms[0].asset_context.freshness_state.value in {"unavailable", "stale"}
    assert unavailable.terms[0].asset_context.uncertainty_labels
    assert any(reference.freshness_state.value in {"unavailable", "stale"} for reference in unavailable.evidence_references)

    assert stale_or_gap.terms[0].asset_context.availability_state.value in {
        "generic_only",
        "insufficient_evidence",
        "unavailable",
    }
    assert stale_or_gap.terms[0].asset_context.citation_ids == []


def test_non_generated_assets_return_generic_only_without_sources_or_citations():
    cases = [
        ("SPY", "eligible_not_cached"),
        ("TQQQ", "unsupported"),
        ("GME", "out_of_scope"),
        ("ZZZZ", "unknown"),
    ]

    for ticker, expected_state in cases:
        response = build_glossary_response(ticker, term="expense ratio")

        assert response.glossary_state.value == expected_state
        assert response.citation_bindings == []
        assert response.source_references == []
        assert response.evidence_references == []
        assert response.diagnostics.unavailable_reasons
        assert response.diagnostics.no_live_external_calls is True
        assert response.diagnostics.no_new_generated_output is True
        assert all(term.asset_context.citation_ids == [] for term in response.terms)
        assert all(term.asset_context.availability_state.value == "generic_only" for term in response.terms)


def test_optional_term_filtering_is_deterministic_and_case_insensitive():
    first = build_glossary_response("voo", term="Expense Ratio")
    second = build_glossary_response("VOO", term="expense-ratio")

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [term.term_identity.slug for term in first.terms] == ["expense-ratio"]
    assert first.diagnostics.filters_applied == {"term": "expense-ratio"}


def test_glossary_contract_does_not_expose_raw_chunks_prompts_or_network_imports():
    response = build_glossary_response("QQQ")
    serialized = str(response.model_dump(mode="json")).lower()

    assert "supporting_passage" not in serialized
    assert "supporting_text" not in serialized
    assert "raw_source_text" not in serialized
    assert "reasoning_details" not in serialized
    assert "qqq seeks investment results" not in serialized

    source = (ROOT / "backend" / "glossary.py").read_text(encoding="utf-8")
    forbidden = ["import requests", "import httpx", "urllib.request", "from socket import", "OPENROUTER_API_KEY"]
    for marker in forbidden:
        assert marker not in source


def test_curated_catalog_covers_prd_required_beginner_terms():
    catalog_terms = {entry.term for entry in TERM_CATALOG}

    assert {
        "expense ratio",
        "AUM",
        "market cap",
        "P/E ratio",
        "forward P/E",
        "revenue",
        "operating margin",
        "EPS",
        "free cash flow",
        "debt",
        "benchmark",
        "index",
        "holdings",
        "top 10 concentration",
        "sector exposure",
        "country exposure",
        "tracking error",
        "tracking difference",
        "NAV",
        "premium/discount",
        "bid-ask spread",
        "liquidity",
        "market risk",
        "concentration risk",
    } <= catalog_terms
