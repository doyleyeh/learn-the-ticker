from pathlib import Path
import sys

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - dependency-free quality gate fallback.
    ROOT_FOR_FALLBACK = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_FOR_FALLBACK / "scripts"))
    import yaml

from backend.citations import (
    CitationEvidence,
    CitationValidationClaim,
    CitationValidationContext,
    CitationValidationStatus,
    evidence_from_sources,
    validate_claims,
)
from backend.data import supported_asset
from backend.models import FreshnessState


ROOT = Path(__file__).resolve().parents[2]


def test_supported_asset_fixture_claims_validate():
    payload = supported_asset("VOO")
    evidence = evidence_from_sources("VOO", payload["citations"], payload["sources"])
    claims = [
        CitationValidationClaim(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            claim_type="factual",
            citation_ids=claim.citation_ids,
        )
        for claim in payload["claims"]
    ]

    report = validate_claims(claims, evidence, CitationValidationContext(allowed_asset_tickers=["VOO"]))

    assert report.status is CitationValidationStatus.valid
    assert report.valid is True


def test_missing_nonexistent_and_wrong_asset_citations_are_rejected():
    missing = validate_claims(
        claims=[
            {
                "claim_id": "claim_missing",
                "claim_text": "Important claims need citations.",
                "claim_type": "factual",
                "citation_ids": [],
            }
        ],
        evidence=[],
        context={"allowed_asset_tickers": ["VOO"]},
    )
    assert missing.status is CitationValidationStatus.missing_citation

    nonexistent = validate_claims(
        claims=[
            {
                "claim_id": "claim_nonexistent",
                "claim_text": "Citation IDs must exist.",
                "claim_type": "factual",
                "citation_ids": ["c_missing"],
            }
        ],
        evidence=[],
        context={"allowed_asset_tickers": ["VOO"]},
    )
    assert nonexistent.status is CitationValidationStatus.citation_not_found

    wrong_asset = validate_claims(
        claims=[
            {
                "claim_id": "claim_wrong_asset",
                "claim_text": "VOO tracks the S&P 500 Index.",
                "claim_type": "factual",
                "citation_ids": ["c_qqq_profile"],
            }
        ],
        evidence=[
            CitationEvidence(
                citation_id="c_qqq_profile",
                asset_ticker="QQQ",
                source_document_id="src_qqq_fact_sheet",
                source_type="issuer_fact_sheet",
                supporting_text="QQQ fact sheet fixture.",
            )
        ],
        context={"allowed_asset_tickers": ["VOO"]},
    )
    assert wrong_asset.status is CitationValidationStatus.wrong_asset


def test_recent_development_claims_require_recent_sources():
    valid_recent = CitationEvidence(
        citation_id="c_aapl_recent",
        asset_ticker="AAPL",
        source_document_id="src_aapl_recent_fixture",
        source_type="recent_development",
        supporting_text="Recent-development fixture.",
    )
    stable_source = CitationEvidence(
        citation_id="c_aapl_profile",
        asset_ticker="AAPL",
        source_document_id="src_aapl_10k",
        source_type="sec_filing",
        supporting_text="Stable 10-K fixture.",
    )

    accepted = validate_claims(
        claims=[
            {
                "claim_id": "claim_recent_valid",
                "claim_text": "Apple has a recent-development fixture.",
                "claim_type": "recent",
                "citation_ids": ["c_aapl_recent"],
            }
        ],
        evidence=[valid_recent],
        context={"allowed_asset_tickers": ["AAPL"]},
    )
    rejected = validate_claims(
        claims=[
            {
                "claim_id": "claim_recent_invalid",
                "claim_text": "Recent claims cannot cite only stable profile documents.",
                "claim_type": "recent",
                "citation_ids": ["c_aapl_profile"],
            }
        ],
        evidence=[stable_source],
        context={"allowed_asset_tickers": ["AAPL"]},
    )

    assert accepted.status is CitationValidationStatus.valid
    assert rejected.status is CitationValidationStatus.non_recent_source


def test_stale_and_unknown_freshness_states_are_explicit():
    stale_evidence = CitationEvidence(
        citation_id="c_voo_stale",
        asset_ticker="VOO",
        source_document_id="src_voo_stale",
        source_type="issuer_fact_sheet",
        freshness_state=FreshnessState.stale,
        supporting_text="Old VOO fact sheet fixture.",
    )
    unknown_evidence = CitationEvidence(
        citation_id="c_voo_unknown",
        asset_ticker="VOO",
        source_document_id="src_voo_unknown",
        source_type="issuer_fact_sheet",
        freshness_state=FreshnessState.unknown,
        supporting_text="VOO fact sheet fixture with unknown freshness.",
    )

    stale_unlabeled = validate_claims(
        claims=[
            {
                "claim_id": "claim_stale",
                "claim_text": "Stale facts must be labeled.",
                "claim_type": "factual",
                "citation_ids": ["c_voo_stale"],
            }
        ],
        evidence=[stale_evidence],
        context={"allowed_asset_tickers": ["VOO"]},
    )
    stale_labeled = validate_claims(
        claims=[
            {
                "claim_id": "claim_stale_labeled",
                "claim_text": "Stale facts can pass when labeled stale.",
                "claim_type": "factual",
                "citation_ids": ["c_voo_stale"],
                "freshness_label": "stale",
            }
        ],
        evidence=[stale_evidence],
        context={"allowed_asset_tickers": ["VOO"]},
    )
    unknown_unlabeled = validate_claims(
        claims=[
            {
                "claim_id": "claim_unknown",
                "claim_text": "Unknown freshness cannot be treated as fresh.",
                "claim_type": "factual",
                "citation_ids": ["c_voo_unknown"],
            }
        ],
        evidence=[unknown_evidence],
        context={"allowed_asset_tickers": ["VOO"]},
    )

    assert stale_unlabeled.status is CitationValidationStatus.stale_source
    assert stale_labeled.status is CitationValidationStatus.valid
    assert unknown_unlabeled.status is CitationValidationStatus.insufficient_evidence


def test_unsupported_source_type_and_insufficient_evidence_are_rejected():
    unsupported_source = CitationEvidence(
        citation_id="c_voo_news",
        asset_ticker="VOO",
        source_document_id="src_voo_news",
        source_type="news_article",
        supporting_text="News fixture.",
    )
    empty_source = CitationEvidence(
        citation_id="c_voo_empty",
        asset_ticker="VOO",
        source_document_id="src_voo_empty",
        source_type="issuer_fact_sheet",
        supporting_text="",
    )

    unsupported = validate_claims(
        claims=[
            {
                "claim_id": "claim_unsupported",
                "claim_text": "A stable ETF fact cannot cite a generic news article.",
                "claim_type": "factual",
                "citation_ids": ["c_voo_news"],
            }
        ],
        evidence=[unsupported_source],
        context={"allowed_asset_tickers": ["VOO"]},
    )
    insufficient = validate_claims(
        claims=[
            {
                "claim_id": "claim_insufficient",
                "claim_text": "A citation with no passage is insufficient.",
                "claim_type": "factual",
                "citation_ids": ["c_voo_empty"],
            }
        ],
        evidence=[empty_source],
        context={"allowed_asset_tickers": ["VOO"]},
    )

    assert unsupported.status is CitationValidationStatus.unsupported_source
    assert insufficient.status is CitationValidationStatus.insufficient_evidence


def test_comparison_claims_must_stay_inside_comparison_pack():
    voo_evidence = CitationEvidence(
        citation_id="c_voo_profile",
        asset_ticker="VOO",
        source_document_id="src_voo_fact_sheet",
        source_type="issuer_fact_sheet",
        supporting_text="VOO fixture describes broad S&P 500 exposure.",
    )
    qqq_evidence = CitationEvidence(
        citation_id="c_qqq_profile",
        asset_ticker="QQQ",
        source_document_id="src_qqq_fact_sheet",
        source_type="issuer_fact_sheet",
        supporting_text="QQQ fixture describes Nasdaq-100 exposure.",
    )
    aapl_evidence = CitationEvidence(
        citation_id="c_aapl_profile",
        asset_ticker="AAPL",
        source_document_id="src_aapl_10k",
        source_type="sec_filing",
        supporting_text="Apple 10-K fixture.",
    )
    claim = {
        "claim_id": "claim_compare",
        "claim_text": "VOO is broader than QQQ in the local comparison fixture.",
        "claim_type": "comparison",
        "citation_ids": ["c_voo_profile", "c_qqq_profile"],
        "required_asset_tickers": ["VOO", "QQQ"],
    }

    accepted = validate_claims(
        claims=[claim],
        evidence=[voo_evidence, qqq_evidence],
        context={"allowed_asset_tickers": ["VOO", "QQQ"], "comparison_pack_id": "VOO_vs_QQQ"},
    )
    missing_qqq = validate_claims(
        claims=[{**claim, "citation_ids": ["c_voo_profile"]}],
        evidence=[voo_evidence],
        context={"allowed_asset_tickers": ["VOO", "QQQ"], "comparison_pack_id": "VOO_vs_QQQ"},
    )
    wrong_asset = validate_claims(
        claims=[{**claim, "citation_ids": ["c_voo_profile", "c_aapl_profile"]}],
        evidence=[voo_evidence, aapl_evidence],
        context={"allowed_asset_tickers": ["VOO", "QQQ"], "comparison_pack_id": "VOO_vs_QQQ"},
    )

    assert accepted.status is CitationValidationStatus.valid
    assert missing_qqq.status is CitationValidationStatus.insufficient_evidence
    assert wrong_asset.status is CitationValidationStatus.wrong_asset


def test_citation_eval_yaml_cases_match_expected_statuses():
    with (ROOT / "evals" / "citation_eval_cases.yaml").open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for case in data["cases"]:
        if "validation_claim" not in case:
            continue
        report = validate_claims(
            claims=[case["validation_claim"]],
            evidence=case.get("evidence", []),
            context=case["context"],
        )
        assert report.status.value == case["expected_status"], case["id"]
