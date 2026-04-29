from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.data import STUB_TIMESTAMP, load_top500_stock_universe_manifest, normalize_ticker
from backend.models import (
    FreshnessState,
    SourceParserStatus,
    SourcePolicyDecision,
    SourceQuality,
    Top500CandidateDiffReport,
    Top500CandidateHoldingInput,
    Top500CandidateManifest,
    Top500CandidateRankBasis,
    Top500CandidateRow,
    Top500CandidateSourceInput,
    Top500CandidateSourceRole,
    Top500CandidateValidationStatus,
)
from backend.source_policy import (
    SourceHandoffContractError,
    SourcePolicyAction,
    resolve_source_policy,
    source_handoff_fields_from_policy,
    validate_source_handoff,
)


TOP500_CANDIDATE_SCHEMA_VERSION = "top500-us-common-stock-candidate-v1"
TOP500_CANDIDATE_DIFF_SCHEMA_VERSION = "top500-candidate-diff-v1"
TOP500_OPERATOR_REVIEW_SCHEMA_VERSION = "top500-launch-review-summary-v1"
STOCK_SEC_READINESS_SCHEMA_VERSION = "stock-sec-source-pack-readiness-v1"
TOP500_APPROVED_CURRENT_MANIFEST_PATH = "data/universes/us_common_stocks_top500.current.json"
TOP500_CANDIDATE_OUTPUT_TEMPLATE = "data/universes/us_common_stocks_top500.candidate.{candidate_month}.json"
TOP500_DIFF_OUTPUT_TEMPLATE = "data/universes/us_common_stocks_top500.diff.{candidate_month}.json"
TOP500_REVIEW_OUTPUT_TEMPLATE = "data/universes/us_common_stocks_top500.review.{candidate_month}.json"
TOP500_REFRESH_BOUNDARY = "top500-reviewed-candidate-refresh-v1"
TOP500_OPERATOR_REVIEW_BOUNDARY = "top500-launch-manifest-review-only-v1"
STOCK_SEC_READINESS_BOUNDARY = "stock-sec-source-pack-readiness-review-only-v1"
STOCK_SEC_REQUIRED_COMPONENTS = (
    "sec_submissions",
    "latest_annual_filing",
    "latest_quarterly_filing_when_available",
    "xbrl_company_facts",
)
STOCK_SEC_BLOCKED_GENERATED_SURFACES = (
    "generated_claims",
    "generated_chat_answers",
    "generated_comparisons",
    "weekly_news_focus",
    "ai_comprehensive_analysis",
    "exports",
    "generated_output_cache_entries",
)

_NON_COMMON_STOCK_MARKERS = {
    "cash",
    "future",
    "futures",
    "option",
    "options",
    "swap",
    "swaps",
    "index",
    "etf",
    "preferred",
    "preferred_stock",
    "warrant",
    "warrants",
    "right",
    "rights",
    "unit",
    "units",
    "fund",
    "funds",
}


class Top500CandidateManifestContractError(ValueError):
    """Raised when a candidate manifest workflow contract is violated."""


@dataclass(frozen=True)
class Top500CandidateGenerationResult:
    boundary: str
    candidate_manifest: Top500CandidateManifest
    diff_report: Top500CandidateDiffReport
    rejected_rows: tuple[dict[str, str], ...]


def generate_top500_candidate_manifest_from_fixture_paths(
    *,
    primary_fixture_path: str | Path,
    fallback_fixture_paths: list[str | Path],
    sec_company_fixture_path: str | Path,
    nasdaq_symbol_fixture_path: str | Path,
    candidate_month: str,
    rank_limit: int = 500,
    generated_at: str = "2026-04-27T00:00:00Z",
    validation_threshold: float = 0.95,
) -> Top500CandidateGenerationResult:
    primary_fixture = _load_json(primary_fixture_path)
    fallback_fixtures = [_load_json(path) for path in fallback_fixture_paths]
    sec_rows = _load_sec_company_rows(sec_company_fixture_path)
    nasdaq_rows = _load_nasdaq_symbol_rows(nasdaq_symbol_fixture_path)
    return generate_top500_candidate_manifest(
        primary_fixture=primary_fixture,
        fallback_fixtures=fallback_fixtures,
        sec_rows=sec_rows,
        nasdaq_rows=nasdaq_rows,
        candidate_month=candidate_month,
        rank_limit=rank_limit,
        generated_at=generated_at,
        validation_threshold=validation_threshold,
    )


def generate_top500_candidate_manifest(
    *,
    primary_fixture: dict[str, Any],
    fallback_fixtures: list[dict[str, Any]],
    sec_rows: dict[str, dict[str, str]],
    nasdaq_rows: dict[str, dict[str, str]],
    candidate_month: str,
    rank_limit: int = 500,
    generated_at: str = "2026-04-27T00:00:00Z",
    validation_threshold: float = 0.95,
) -> Top500CandidateGenerationResult:
    if rank_limit < 1 or rank_limit > 500:
        raise Top500CandidateManifestContractError("Candidate rank_limit must be between 1 and 500.")

    primary_source = _source_from_fixture(primary_fixture, expected_role=Top500CandidateSourceRole.primary)
    primary_usable, fallback_reason, primary_warnings = _source_is_usable(primary_source)
    primary_holdings = _holding_rows_from_fixture(primary_fixture)
    primary_normalized = _normalized_common_stock_rows(primary_holdings, source_by_id={primary_source.source_id: primary_source})

    if primary_usable and len(primary_normalized) >= max(1, min(rank_limit, int(rank_limit * validation_threshold))):
        selected_sources = [primary_source]
        selected_rows = primary_normalized
        rank_basis = Top500CandidateRankBasis.iwb_weight_proxy
        fallback_used = False
        fallback_reason = None
    else:
        if primary_usable:
            fallback_reason = "iwb_below_validation_threshold"
            primary_warnings = (*primary_warnings, "iwb_below_validation_threshold")
        selected_sources = [_source_from_fixture(fixture, expected_role=Top500CandidateSourceRole.fallback) for fixture in fallback_fixtures]
        if not selected_sources:
            raise Top500CandidateManifestContractError("Fallback fixtures are required when IWB cannot be used.")
        if {source.ticker for source in selected_sources} != {"SPY", "IVV", "VOO"}:
            raise Top500CandidateManifestContractError("Fallback refresh requires mocked official SPY, IVV, and VOO inputs.")
        for source in selected_sources:
            _require_usable_source(source)
        fallback_holdings = [row for fixture in fallback_fixtures for row in _holding_rows_from_fixture(fixture)]
        selected_rows = _normalized_common_stock_rows(
            fallback_holdings,
            source_by_id={source.source_id: source for source in selected_sources},
        )
        rank_basis = Top500CandidateRankBasis.sp500_etf_weight_proxy_fallback
        fallback_used = True
        fallback_reason = fallback_reason or "iwb_unavailable"

    _require_selected_sources_have_handoff(selected_sources)
    ranked_rows, rejected_rows = _rank_and_validate_rows(
        selected_rows=selected_rows,
        sources_by_id={source.source_id: source for source in selected_sources},
        sec_rows=sec_rows,
        nasdaq_rows=nasdaq_rows,
        rank_basis=rank_basis,
        rank_limit=rank_limit,
    )

    validation_coverage = _validation_coverage(ranked_rows)
    candidate_path = TOP500_CANDIDATE_OUTPUT_TEMPLATE.format(candidate_month=candidate_month)
    diff_path = TOP500_DIFF_OUTPUT_TEMPLATE.format(candidate_month=candidate_month)
    source_warnings = list(dict.fromkeys([*primary_warnings, *[warning for row in ranked_rows for warning in row.warnings]]))
    source_used = [source.ticker for source in selected_sources]
    source_dates = {source.ticker: source.source_snapshot_date for source in selected_sources}
    source_checksums = {source.ticker: source.source_checksum for source in selected_sources}
    manual_triggers = _manual_review_triggers(
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        validation_coverage=validation_coverage,
        ranked_rows=ranked_rows,
        rejected_rows=rejected_rows,
        source_warnings=source_warnings,
    )
    operator_review_note_block = _operator_review_note_block(
        candidate_month=candidate_month,
        approved_current_manifest_path=TOP500_APPROVED_CURRENT_MANIFEST_PATH,
        source_used=source_used,
        rank_basis=rank_basis.value,
    )

    manifest_without_checksum = {
        "schema_version": TOP500_CANDIDATE_SCHEMA_VERSION,
        "manifest_id": f"us-common-stocks-top500-candidate-{candidate_month}-fixture-contract",
        "universe_name": "Reviewed Top-500-first U.S.-listed common stock candidate universe",
        "local_path": candidate_path,
        "approved_current_manifest_path": TOP500_APPROVED_CURRENT_MANIFEST_PATH,
        "candidate_month": candidate_month,
        "generated_at": generated_at,
        "rank_limit": rank_limit,
        "rank_basis": rank_basis.value,
        "source_used": source_used,
        "source_dates": source_dates,
        "source_checksums": source_checksums,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "validation_coverage": validation_coverage,
        "manual_approval_required": True,
        "manual_review_triggers": manual_triggers,
        "operator_review_note_block": operator_review_note_block,
        "diff_report_path": diff_path,
        "manifest_checksum_input": "",
        "generated_checksum": "",
        "entries": [row.model_dump(mode="json") for row in ranked_rows],
    }
    manifest_checksum_input = _canonical_json({**manifest_without_checksum, "generated_checksum": ""})
    candidate_manifest = Top500CandidateManifest.model_validate(
        {
            **manifest_without_checksum,
            "manifest_checksum_input": manifest_checksum_input,
            "generated_checksum": _sha256(manifest_checksum_input),
        }
    )
    diff_report = build_top500_candidate_diff_report(
        candidate_manifest=candidate_manifest,
        rejected_rows=rejected_rows,
        source_warnings=source_warnings,
        generated_at=generated_at,
        operator_review_note_block=operator_review_note_block,
    )
    validate_top500_candidate_manifest(candidate_manifest)
    return Top500CandidateGenerationResult(
        boundary=TOP500_REFRESH_BOUNDARY,
        candidate_manifest=candidate_manifest,
        diff_report=diff_report,
        rejected_rows=tuple(rejected_rows),
    )


def validate_top500_candidate_manifest(manifest: Top500CandidateManifest) -> Top500CandidateManifest:
    if manifest.local_path != TOP500_CANDIDATE_OUTPUT_TEMPLATE.format(candidate_month=manifest.candidate_month):
        raise Top500CandidateManifestContractError("Candidate manifest local_path must use the reviewed candidate path.")
    if manifest.approved_current_manifest_path != TOP500_APPROVED_CURRENT_MANIFEST_PATH:
        raise Top500CandidateManifestContractError("Candidate manifest must point at the approved current manifest separately.")
    if manifest.rank_limit < 1 or manifest.rank_limit > 500:
        raise Top500CandidateManifestContractError("Candidate manifest rank_limit must be within 1..500.")
    if manifest.manual_approval_required is not True:
        raise Top500CandidateManifestContractError("Candidate manifest promotion must require manual approval.")
    if not manifest.entries:
        raise Top500CandidateManifestContractError("Candidate manifest must contain candidate rows.")
    tickers = [entry.ticker for entry in manifest.entries]
    ranks = [entry.rank for entry in manifest.entries]
    if len(tickers) != len(set(tickers)):
        raise Top500CandidateManifestContractError("Candidate manifest entries must have unique tickers.")
    if len(ranks) != len(set(ranks)):
        raise Top500CandidateManifestContractError("Candidate manifest entries must have unique ranks.")
    if any(entry.ticker != normalize_candidate_ticker(entry.ticker) for entry in manifest.entries):
        raise Top500CandidateManifestContractError("Candidate manifest tickers must be normalized.")
    if any(entry.asset_type != "stock" or entry.security_type != "us_listed_common_stock" for entry in manifest.entries):
        raise Top500CandidateManifestContractError("Candidate manifest entries must be U.S.-listed common stocks.")
    if any(entry.rank < 1 or entry.rank > manifest.rank_limit for entry in manifest.entries):
        raise Top500CandidateManifestContractError("Candidate ranks must be within the declared rank_limit.")
    if any(not entry.source_checksum.startswith("sha256:") for entry in manifest.entries):
        raise Top500CandidateManifestContractError("Candidate rows must preserve sha256 source checksums.")
    if any(_contains_advice_language(_canonical_json(entry.model_dump(mode="json"))) for entry in manifest.entries):
        raise Top500CandidateManifestContractError("Candidate manifest entries contain advice-like language.")
    if _contains_advice_language(_canonical_json(manifest.model_dump(mode="json"))):
        raise Top500CandidateManifestContractError("Candidate manifest contains advice-like language.")
    if not manifest.operator_review_note_block:
        raise Top500CandidateManifestContractError("Candidate manifest must include an operator review note block.")
    return manifest


def build_top500_candidate_diff_report(
    *,
    candidate_manifest: Top500CandidateManifest,
    rejected_rows: list[dict[str, str]],
    source_warnings: list[str],
    operator_review_note_block: list[str],
    generated_at: str,
) -> Top500CandidateDiffReport:
    current_manifest = load_top500_stock_universe_manifest()
    current_by_ticker = {entry.ticker: entry for entry in current_manifest.entries}
    candidate_by_ticker = {entry.ticker: entry for entry in candidate_manifest.entries}

    added = sorted(set(candidate_by_ticker) - set(current_by_ticker))
    removed = sorted(set(current_by_ticker) - set(candidate_by_ticker))
    rank_changes = [
        {
            "ticker": ticker,
            "current_rank": current_by_ticker[ticker].rank,
            "candidate_rank": candidate_by_ticker[ticker].rank,
        }
        for ticker in sorted(set(candidate_by_ticker) & set(current_by_ticker))
        if current_by_ticker[ticker].rank != candidate_by_ticker[ticker].rank
    ]
    missing_ciks = [entry.ticker for entry in candidate_manifest.entries if not entry.cik]
    nasdaq_failures = [
        row for row in rejected_rows if row.get("reason", "").startswith("nasdaq_")
    ]
    diff_payload = {
        "schema_version": TOP500_CANDIDATE_DIFF_SCHEMA_VERSION,
        "candidate_manifest_path": candidate_manifest.local_path,
        "approved_current_manifest_path": TOP500_APPROVED_CURRENT_MANIFEST_PATH,
        "candidate_month": candidate_manifest.candidate_month,
        "generated_at": generated_at,
        "source_used": candidate_manifest.source_used,
        "source_dates": candidate_manifest.source_dates,
        "source_checksums": candidate_manifest.source_checksums,
        "fallback_used": candidate_manifest.fallback_used,
        "fallback_reason": candidate_manifest.fallback_reason,
        "added_tickers": added,
        "removed_tickers": removed,
        "rank_changes": rank_changes,
        "missing_ciks": missing_ciks,
        "nasdaq_validation_failures": nasdaq_failures,
        "source_warnings": source_warnings,
        "manual_approval_required": True,
        "manual_review_triggers": candidate_manifest.manual_review_triggers,
        "operator_review_note_block": operator_review_note_block,
    }
    diff_json = _canonical_json(diff_payload)
    return Top500CandidateDiffReport.model_validate({**diff_payload, "generated_checksum": _sha256(diff_json)})


def build_top500_operator_review_summary(result: Top500CandidateGenerationResult) -> dict[str, Any]:
    return inspect_top500_candidate_review_packet(
        candidate_manifest=result.candidate_manifest,
        diff_report=result.diff_report,
        rejected_row_count=len(result.rejected_rows),
    )


def inspect_top500_candidate_review_packet(
    *,
    candidate_manifest: Top500CandidateManifest,
    diff_report: Top500CandidateDiffReport,
    rejected_row_count: int = 0,
) -> dict[str, Any]:
    validate_top500_candidate_manifest(candidate_manifest)
    candidate_checksum_matches = _candidate_checksum_matches(candidate_manifest)
    diff_checksum_matches = _diff_checksum_matches(diff_report)
    golden_tickers = {"AAPL", "MSFT", "NVDA"}
    candidate_tickers = {entry.ticker for entry in candidate_manifest.entries}
    missing_golden_tickers = sorted(golden_tickers - candidate_tickers)
    warning_tickers = sorted(
        entry.ticker
        for entry in candidate_manifest.entries
        if entry.validation_status is Top500CandidateValidationStatus.warning or entry.warnings
    )
    fixture_or_local_only = _top500_packet_uses_fixture_or_local_only_provenance(candidate_manifest)
    stop_conditions = _top500_review_stop_conditions(
        candidate_manifest=candidate_manifest,
        diff_report=diff_report,
        candidate_checksum_matches=candidate_checksum_matches,
        diff_checksum_matches=diff_checksum_matches,
        missing_golden_tickers=missing_golden_tickers,
        warning_tickers=warning_tickers,
        fixture_or_local_only=fixture_or_local_only,
    )
    review_status = "blocked" if any("checksum_mismatch" in condition for condition in stop_conditions) else (
        "review_needed" if stop_conditions else "pass"
    )
    return {
        "schema_version": TOP500_OPERATOR_REVIEW_SCHEMA_VERSION,
        "boundary": TOP500_OPERATOR_REVIEW_BOUNDARY,
        "review_only": True,
        "no_live_external_calls": True,
        "candidate_manifest_path": candidate_manifest.local_path,
        "diff_report_path": candidate_manifest.diff_report_path,
        "review_summary_path": TOP500_REVIEW_OUTPUT_TEMPLATE.format(candidate_month=candidate_manifest.candidate_month),
        "approved_current_manifest_path": TOP500_APPROVED_CURRENT_MANIFEST_PATH,
        "candidate_month": candidate_manifest.candidate_month,
        "rank_basis": candidate_manifest.rank_basis.value,
        "entry_count": len(candidate_manifest.entries),
        "rank_limit": candidate_manifest.rank_limit,
        "source_used": candidate_manifest.source_used,
        "source_dates": candidate_manifest.source_dates,
        "source_checksums": candidate_manifest.source_checksums,
        "fallback_used": candidate_manifest.fallback_used,
        "fallback_reason": candidate_manifest.fallback_reason,
        "validation_coverage": candidate_manifest.validation_coverage,
        "manual_approval_required": candidate_manifest.manual_approval_required,
        "manual_review_triggers": candidate_manifest.manual_review_triggers,
        "candidate_checksum": candidate_manifest.generated_checksum,
        "candidate_checksum_matches": candidate_checksum_matches,
        "diff_checksum": diff_report.generated_checksum,
        "diff_checksum_matches": diff_checksum_matches,
        "missing_golden_tickers": missing_golden_tickers,
        "validation_warning_tickers": warning_tickers,
        "rejected_row_count": rejected_row_count,
        "fixture_or_local_only_contract": fixture_or_local_only,
        "launch_approved": False,
        "review_status": review_status,
        "stop_conditions": stop_conditions,
        "manual_promotion_required": True,
        "operator_review_note_block": candidate_manifest.operator_review_note_block,
        "non_advice_framing": (
            "This packet is operational coverage metadata only; it is not an endorsement, recommendation, "
            "model portfolio, allocation, price target, or trading instruction."
        ),
    }


def build_stock_sec_source_pack_readiness_packet(
    *,
    root: str | Path = ".",
    current_manifest: Any | None = None,
    candidate_manifests: list[Top500CandidateManifest] | None = None,
    sec_fixture_by_ticker: dict[str, Any] | None = None,
    parser_status_by_source_document_id: dict[str, SourceParserStatus | str] | None = None,
    generated_at: str = "2026-04-29T00:00:00Z",
) -> dict[str, Any]:
    """Build a deterministic review-only SEC source-pack readiness packet for stock manifests."""

    from backend.provider_adapters.sec_stock import SEC_STOCK_FIXTURES

    root_path = Path(root)
    current = current_manifest or load_top500_stock_universe_manifest()
    candidates = candidate_manifests if candidate_manifests is not None else _load_reviewed_candidate_manifests(root_path)
    fixture_map = {
        normalize_candidate_ticker(ticker): fixture
        for ticker, fixture in (sec_fixture_by_ticker or SEC_STOCK_FIXTURES).items()
    }
    parser_overrides = {
        source_id: SourceParserStatus(status)
        for source_id, status in (parser_status_by_source_document_id or {}).items()
    }

    rows: list[dict[str, Any]] = []
    rows.extend(
        _stock_sec_readiness_row(
            entry=entry,
            manifest_kind="current",
            manifest_id=current.manifest_id,
            manifest_path=current.local_path,
            candidate_month=None,
            fixture_map=fixture_map,
            parser_overrides=parser_overrides,
        )
        for entry in current.entries
    )
    for candidate in candidates:
        validate_top500_candidate_manifest(candidate)
        rows.extend(
            _stock_sec_readiness_row(
                entry=entry,
                manifest_kind="candidate",
                manifest_id=candidate.manifest_id,
                manifest_path=candidate.local_path,
                candidate_month=candidate.candidate_month,
                fixture_map=fixture_map,
                parser_overrides=parser_overrides,
            )
            for entry in candidate.entries
        )

    readiness_counts = _stock_sec_readiness_counts(rows)
    stop_conditions = _stock_sec_readiness_stop_conditions(rows)
    review_status = "blocked" if readiness_counts["blocked"] else ("review_needed" if stop_conditions else "pass")
    return {
        "schema_version": STOCK_SEC_READINESS_SCHEMA_VERSION,
        "boundary": STOCK_SEC_READINESS_BOUNDARY,
        "review_only": True,
        "no_live_external_calls": True,
        "generated_at": generated_at,
        "runtime_manifest_authority": TOP500_APPROVED_CURRENT_MANIFEST_PATH,
        "candidate_manifest_paths": [candidate.local_path for candidate in candidates],
        "approved_current_manifest_path": TOP500_APPROVED_CURRENT_MANIFEST_PATH,
        "current_manifest_path": current.local_path,
        "manifests_promoted": False,
        "sources_approved_by_packet": False,
        "retrieval_alone_approves_evidence": False,
        "launch_approved": False,
        "required_sec_components": list(STOCK_SEC_REQUIRED_COMPONENTS),
        "readiness_counts": readiness_counts,
        "review_status": review_status,
        "stop_conditions": stop_conditions,
        "blocked_generated_surfaces": list(STOCK_SEC_BLOCKED_GENERATED_SURFACES),
        "rows": rows,
        "non_advice_framing": (
            "This packet is source-readiness metadata for educational rendering only; it is not an endorsement, "
            "recommendation, model portfolio, allocation, price target, or trading instruction."
        ),
    }


def promotion_requires_manual_approval(manifest: Top500CandidateManifest) -> bool:
    validate_top500_candidate_manifest(manifest)
    return manifest.manual_approval_required


def assert_manual_approval_for_promotion(manifest: Top500CandidateManifest, *, approved: bool = False) -> None:
    validate_top500_candidate_manifest(manifest)
    if not approved:
        raise Top500CandidateManifestContractError(
            "Manual approval is required before replacing data/universes/us_common_stocks_top500.current.json."
        )


def write_candidate_outputs(
    result: Top500CandidateGenerationResult,
    *,
    root: str | Path,
) -> tuple[Path, Path]:
    root_path = Path(root)
    candidate_path = root_path / result.candidate_manifest.local_path
    diff_path = root_path / result.diff_report.candidate_manifest_path.replace(".candidate.", ".diff.")
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(_pretty_json(result.candidate_manifest.model_dump(mode="json")), encoding="utf-8")
    diff_path.write_text(_pretty_json(result.diff_report.model_dump(mode="json")), encoding="utf-8")
    return candidate_path, diff_path


def write_top500_review_summary(summary: dict[str, Any], *, root: str | Path) -> Path:
    root_path = Path(root)
    summary_path = root_path / str(summary["review_summary_path"])
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(_pretty_json(summary), encoding="utf-8")
    return summary_path


def normalize_candidate_ticker(ticker: str) -> str:
    normalized = normalize_ticker(ticker).replace("-", ".")
    if "/" in normalized and len(normalized.split("/", 1)[1]) == 1:
        normalized = normalized.replace("/", ".")
    return normalized


def _load_reviewed_candidate_manifests(root: Path) -> list[Top500CandidateManifest]:
    paths = sorted((root / "data" / "universes").glob("us_common_stocks_top500.candidate.*.json"))
    manifests: list[Top500CandidateManifest] = []
    for path in paths:
        manifests.append(validate_top500_candidate_manifest(Top500CandidateManifest.model_validate(_load_json(path))))
    return manifests


def _stock_sec_readiness_row(
    *,
    entry: Any,
    manifest_kind: str,
    manifest_id: str,
    manifest_path: str,
    candidate_month: str | None,
    fixture_map: dict[str, Any],
    parser_overrides: dict[str, SourceParserStatus],
) -> dict[str, Any]:
    ticker = normalize_candidate_ticker(entry.ticker)
    fixture = fixture_map.get(ticker)
    if fixture is None:
        components = [
            _missing_stock_sec_component("sec_submissions", required=True, reason_code="sec_submissions_fixture_missing"),
            _missing_stock_sec_component("latest_annual_filing", required=True, reason_code="latest_10k_fixture_missing"),
            _missing_stock_sec_component(
                "latest_quarterly_filing_when_available",
                required=False,
                reason_code="latest_10q_not_available_in_fixture",
            ),
            _missing_stock_sec_component("xbrl_company_facts", required=True, reason_code="xbrl_company_facts_fixture_missing"),
        ]
    else:
        components = _stock_sec_components_for_fixture(
            ticker=ticker,
            expected_cik=getattr(entry, "cik", None),
            fixture=fixture,
            parser_overrides=parser_overrides,
        )
    source_pack_status = _stock_sec_row_status(components)
    return {
        "ticker": ticker,
        "name": entry.name,
        "cik": getattr(entry, "cik", None),
        "exchange": entry.exchange,
        "manifest_kind": manifest_kind,
        "manifest_id": manifest_id,
        "manifest_path": manifest_path,
        "candidate_month": candidate_month,
        "source_pack_status": source_pack_status,
        "source_backed_partial_rendering_ready": _source_backed_partial_rendering_ready(components),
        "review_packet_unlocks_generated_output": False,
        "readiness_failures_unlock_generated_output": False,
        "blocked_generated_surfaces": list(STOCK_SEC_BLOCKED_GENERATED_SURFACES),
        "components": components,
    }


def _stock_sec_components_for_fixture(
    *,
    ticker: str,
    expected_cik: str | None,
    fixture: Any,
    parser_overrides: dict[str, SourceParserStatus],
) -> list[dict[str, Any]]:
    source_by_id = {source.source_document_id: source for source in fixture.sources}
    submissions_source = source_by_id.get(fixture.identity.submissions_source_document_id)
    annual = _latest_filing(fixture.selected_filings, "10-K")
    quarterly = _latest_filing(fixture.selected_filings, "10-Q")
    xbrl_source = next((source for source in fixture.sources if source.source_type == "sec_xbrl_company_facts"), None)
    xbrl_citations = [fact.citation_id for fact in fixture.xbrl_company_facts]
    return [
        _stock_sec_component_from_source(
            component_id="sec_submissions",
            source=submissions_source,
            ticker=ticker,
            expected_cik=expected_cik,
            fixture=fixture,
            required=True,
            citation_ids=[],
            reason_code_if_missing="sec_submissions_fixture_missing",
            parser_overrides=parser_overrides,
        ),
        _stock_sec_component_from_source(
            component_id="latest_annual_filing",
            source=source_by_id.get(annual.source_document_id) if annual else None,
            ticker=ticker,
            expected_cik=expected_cik,
            fixture=fixture,
            required=True,
            citation_ids=[annual.citation_id] if annual else [],
            filing_metadata=_filing_metadata(annual),
            reason_code_if_missing="latest_10k_fixture_missing",
            parser_overrides=parser_overrides,
        ),
        _stock_sec_component_from_source(
            component_id="latest_quarterly_filing_when_available",
            source=source_by_id.get(quarterly.source_document_id) if quarterly else None,
            ticker=ticker,
            expected_cik=expected_cik,
            fixture=fixture,
            required=False,
            citation_ids=[quarterly.citation_id] if quarterly else [],
            filing_metadata=_filing_metadata(quarterly),
            reason_code_if_missing="latest_10q_not_available_in_fixture",
            parser_overrides=parser_overrides,
        ),
        _stock_sec_component_from_source(
            component_id="xbrl_company_facts",
            source=xbrl_source,
            ticker=ticker,
            expected_cik=expected_cik,
            fixture=fixture,
            required=True,
            citation_ids=xbrl_citations,
            reason_code_if_missing="xbrl_company_facts_fixture_missing",
            parser_overrides=parser_overrides,
        ),
    ]


def _stock_sec_component_from_source(
    *,
    component_id: str,
    source: Any | None,
    ticker: str,
    expected_cik: str | None,
    fixture: Any,
    required: bool,
    citation_ids: list[str],
    reason_code_if_missing: str,
    parser_overrides: dict[str, SourceParserStatus],
    filing_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if source is None:
        return _missing_stock_sec_component(component_id, required=required, reason_code=reason_code_if_missing)

    parser_status = parser_overrides.get(source.source_document_id, SourceParserStatus.parsed)
    decision = resolve_source_policy(url=source.url)
    handoff_payload = {
        **source_handoff_fields_from_policy(
            decision,
            source_identity=source.url,
            parser_status=parser_status,
            approval_rationale=(
                "Deterministic SEC source-pack readiness metadata; retrieval alone does not approve evidence use."
            ),
        ),
        "source_document_id": source.source_document_id,
        "source_type": source.source_type,
        "is_official": True,
        "source_quality": decision.source_quality if decision.source_quality is not SourceQuality.unknown else SourceQuality.official,
        "allowlist_status": decision.allowlist_status,
        "source_use_policy": decision.source_use_policy,
        "permitted_operations": decision.permitted_operations,
        "freshness_state": source.freshness_state,
        "as_of_date": source.as_of_date,
        "published_at": source.published_at,
        "retrieved_at": STUB_TIMESTAMP,
        "parser_failure_diagnostics": "deterministic_parser_failure" if parser_status is SourceParserStatus.failed else None,
    }
    action_results = {
        action.value: validate_source_handoff(handoff_payload, action=action)
        for action in (
            SourcePolicyAction.generated_claim_support,
            SourcePolicyAction.cacheable_generated_output,
            SourcePolicyAction.markdown_json_section_export,
        )
    }
    generated_claim_handoff = action_results[SourcePolicyAction.generated_claim_support.value]
    same_asset = _stock_sec_same_asset(ticker=ticker, expected_cik=expected_cik, fixture=fixture, source=source)
    status, evidence_state, reason_codes = _stock_sec_component_status(
        required=required,
        same_asset=same_asset,
        freshness_state=source.freshness_state,
        parser_status=parser_status,
        handoff_allowed=generated_claim_handoff.allowed,
        handoff_reason_codes=list(generated_claim_handoff.reason_codes),
    )
    return {
        "component_id": component_id,
        "required": required,
        "status": status,
        "evidence_state": evidence_state,
        "reason_codes": reason_codes,
        "same_asset_validation": same_asset,
        "official_source_status": True,
        "source_identity": source.url,
        "source_document_id": source.source_document_id,
        "source_type": source.source_type,
        "source_quality": _enum_value(handoff_payload["source_quality"]),
        "allowlist_status": _enum_value(handoff_payload["allowlist_status"]),
        "source_use_policy": _enum_value(handoff_payload["source_use_policy"]),
        "storage_rights": _enum_value(handoff_payload["storage_rights"]),
        "export_rights": _enum_value(handoff_payload["export_rights"]),
        "review_status": _enum_value(handoff_payload["review_status"]),
        "parser_status": parser_status.value,
        "parser_failure_diagnostics": handoff_payload["parser_failure_diagnostics"],
        "freshness_state": source.freshness_state.value,
        "as_of_date": source.as_of_date,
        "published_at": source.published_at,
        "retrieved_at": STUB_TIMESTAMP,
        "citation_ids": citation_ids,
        "citation_ready": bool(citation_ids) and same_asset and generated_claim_handoff.allowed and parser_status is SourceParserStatus.parsed,
        "source_can_support_citations": (
            same_asset and generated_claim_handoff.allowed and parser_status is SourceParserStatus.parsed
        ),
        "golden_asset_source_handoff_status": "approved" if generated_claim_handoff.allowed else "blocked",
        "golden_asset_source_handoff_reason_codes": list(generated_claim_handoff.reason_codes),
        "action_readiness": {
            action: {
                "allowed": result.allowed,
                "reason_codes": list(result.reason_codes),
            }
            for action, result in action_results.items()
        },
        "filing_metadata": filing_metadata,
    }


def _missing_stock_sec_component(component_id: str, *, required: bool, reason_code: str) -> dict[str, Any]:
    evidence_state = "insufficient_evidence" if required else "partial"
    status = "insufficient_evidence" if required else "partial"
    return {
        "component_id": component_id,
        "required": required,
        "status": status,
        "evidence_state": evidence_state,
        "reason_codes": [reason_code],
        "same_asset_validation": False,
        "official_source_status": False,
        "source_identity": None,
        "source_document_id": None,
        "source_type": None,
        "source_quality": "unknown",
        "allowlist_status": "not_allowlisted",
        "source_use_policy": "rejected",
        "storage_rights": "unknown",
        "export_rights": "unknown",
        "review_status": "pending_review",
        "parser_status": "pending_review",
        "parser_failure_diagnostics": None,
        "freshness_state": "unavailable",
        "as_of_date": None,
        "published_at": None,
        "retrieved_at": None,
        "citation_ids": [],
        "citation_ready": False,
        "source_can_support_citations": False,
        "golden_asset_source_handoff_status": "not_evaluated_missing_source",
        "golden_asset_source_handoff_reason_codes": [reason_code],
        "action_readiness": {
            action.value: {"allowed": False, "reason_codes": [reason_code]}
            for action in (
                SourcePolicyAction.generated_claim_support,
                SourcePolicyAction.cacheable_generated_output,
                SourcePolicyAction.markdown_json_section_export,
            )
        },
        "filing_metadata": None,
    }


def _stock_sec_component_status(
    *,
    required: bool,
    same_asset: bool,
    freshness_state: FreshnessState,
    parser_status: SourceParserStatus,
    handoff_allowed: bool,
    handoff_reason_codes: list[str],
) -> tuple[str, str, list[str]]:
    reason_codes: list[str] = []
    if not same_asset:
        reason_codes.append("wrong_asset_sec_source")
    if parser_status in {SourceParserStatus.failed, SourceParserStatus.pending_review}:
        reason_codes.append(f"parser_{parser_status.value}")
    if not handoff_allowed:
        reason_codes.extend(handoff_reason_codes)
    if not same_asset or parser_status in {SourceParserStatus.failed, SourceParserStatus.pending_review} or not handoff_allowed:
        return "blocked", "unavailable", list(dict.fromkeys(reason_codes))
    if freshness_state is FreshnessState.stale:
        return "stale", "stale", ["stale_sec_source"]
    if freshness_state in {FreshnessState.unknown, FreshnessState.unavailable}:
        return freshness_state.value, freshness_state.value, [f"{freshness_state.value}_sec_source"]
    if parser_status is SourceParserStatus.partial:
        return "partial", "partial", ["parser_partial"]
    return "pass", "supported", []


def _stock_sec_row_status(components: list[dict[str, Any]]) -> str:
    required_components = [component for component in components if component["required"]]
    if any(component["status"] == "blocked" for component in required_components):
        return "blocked"
    if any(component["status"] == "insufficient_evidence" for component in required_components):
        return "insufficient_evidence"
    if any(component["status"] == "stale" for component in required_components):
        return "stale"
    if any(component["status"] in {"unknown", "unavailable"} for component in required_components):
        return "unavailable"
    if any(component["status"] == "partial" for component in components):
        return "partial"
    return "pass"


def _source_backed_partial_rendering_ready(components: list[dict[str, Any]]) -> bool:
    component_by_id = {component["component_id"]: component for component in components}
    return all(
        component_by_id.get(component_id, {}).get("status") == "pass"
        for component_id in ("sec_submissions", "latest_annual_filing", "xbrl_company_facts")
    )


def _stock_sec_readiness_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    statuses = [str(row["source_pack_status"]) for row in rows]
    return {
        "rows": len(rows),
        "current_manifest_rows": sum(1 for row in rows if row["manifest_kind"] == "current"),
        "candidate_manifest_rows": sum(1 for row in rows if row["manifest_kind"] == "candidate"),
        "unique_tickers": len({str(row["ticker"]) for row in rows}),
        "pass": statuses.count("pass"),
        "partial": statuses.count("partial"),
        "stale": statuses.count("stale"),
        "unknown": statuses.count("unknown"),
        "unavailable": statuses.count("unavailable"),
        "insufficient_evidence": statuses.count("insufficient_evidence"),
        "blocked": statuses.count("blocked"),
        "source_backed_partial_rendering_ready": sum(
            1 for row in rows if row["source_backed_partial_rendering_ready"]
        ),
        "review_packet_unlocks_generated_output": sum(
            1 for row in rows if row["review_packet_unlocks_generated_output"]
        ),
    }


def _stock_sec_readiness_stop_conditions(rows: list[dict[str, Any]]) -> list[str]:
    stop_conditions = ["missing_manual_review_or_approval", "stock_sec_source_pack_review_not_complete"]
    statuses = {str(row["source_pack_status"]) for row in rows}
    if "blocked" in statuses:
        stop_conditions.append("blocked_sec_source_pack")
    if "insufficient_evidence" in statuses:
        stop_conditions.append("insufficient_sec_evidence")
    if "partial" in statuses:
        stop_conditions.append("partial_sec_source_pack")
    if "stale" in statuses:
        stop_conditions.append("stale_sec_source_pack")
    if "unknown" in statuses:
        stop_conditions.append("unknown_sec_source_pack")
    if "unavailable" in statuses:
        stop_conditions.append("unavailable_sec_source_pack")
    if any(row["review_packet_unlocks_generated_output"] for row in rows):
        stop_conditions.append("readiness_packet_generated_output_unlock_attempt")
    return list(dict.fromkeys(stop_conditions))


def _latest_filing(filings: tuple[Any, ...], form_type: str) -> Any | None:
    matching = [filing for filing in filings if filing.form_type == form_type]
    return max(matching, key=lambda filing: filing.filing_date) if matching else None


def _filing_metadata(filing: Any | None) -> dict[str, Any] | None:
    if filing is None:
        return None
    return {
        "form_type": filing.form_type,
        "accession_or_fixture_id": filing.accession_or_fixture_id,
        "filing_date": filing.filing_date,
        "report_date": filing.report_date,
    }


def _stock_sec_same_asset(*, ticker: str, expected_cik: str | None, fixture: Any, source: Any) -> bool:
    expected_source_prefix = f"provider_sec_{ticker.lower()}_"
    return (
        fixture.identity.ticker == ticker
        and (expected_cik in {None, fixture.identity.cik})
        and source.source_document_id.startswith(expected_source_prefix)
        and str(fixture.identity.asset_type) == "stock"
        and str(fixture.identity.support_state) == "supported"
    )


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _source_from_fixture(fixture: dict[str, Any], *, expected_role: Top500CandidateSourceRole) -> Top500CandidateSourceInput:
    source = Top500CandidateSourceInput.model_validate(fixture["source"])
    if source.source_role is not expected_role:
        raise Top500CandidateManifestContractError(f"{source.ticker} source role must be {expected_role.value}.")
    if source.source_role is Top500CandidateSourceRole.primary and source.ticker != "IWB":
        raise Top500CandidateManifestContractError("The primary Top-500 candidate source must be IWB.")
    if source.source_role is Top500CandidateSourceRole.fallback and source.ticker not in {"SPY", "IVV", "VOO"}:
        raise Top500CandidateManifestContractError("Top-500 fallback sources must be SPY, IVV, or VOO.")
    if not source.is_official:
        raise Top500CandidateManifestContractError("Top-500 candidate sources must be marked as official mocked inputs.")
    if not source.source_checksum.startswith("sha256:"):
        raise Top500CandidateManifestContractError("Top-500 candidate source checksums must use sha256.")
    return source


def _holding_rows_from_fixture(fixture: dict[str, Any]) -> list[Top500CandidateHoldingInput]:
    return [Top500CandidateHoldingInput.model_validate(row) for row in fixture.get("holdings", [])]


def _source_is_usable(source: Top500CandidateSourceInput) -> tuple[bool, str | None, tuple[str, ...]]:
    warnings: list[str] = []
    if source.parser_status is not SourceParserStatus.parsed:
        warnings.append(f"iwb_parser_{source.parser_status.value}")
        return False, f"iwb_parser_{source.parser_status.value}", tuple(warnings)
    if source.freshness_state is not FreshnessState.fresh:
        warnings.append(f"iwb_freshness_{source.freshness_state.value}")
        return False, f"iwb_freshness_{source.freshness_state.value}", tuple(warnings)
    handoff = _handoff_result(source)
    if not handoff.allowed:
        warnings.extend(f"iwb_handoff_{reason}" for reason in handoff.reason_codes)
        return False, "iwb_source_handoff_failed", tuple(warnings)
    return True, None, ()


def _require_usable_source(source: Top500CandidateSourceInput) -> None:
    handoff = _handoff_result(source)
    if not handoff.allowed:
        raise SourceHandoffContractError("Golden Asset Source Handoff failed: " + ", ".join(handoff.reason_codes))
    if source.parser_status is not SourceParserStatus.parsed:
        raise Top500CandidateManifestContractError(f"Selected source {source.ticker} is not parser-valid.")
    if source.freshness_state is FreshnessState.unavailable:
        raise Top500CandidateManifestContractError(f"Selected source {source.ticker} is unavailable.")


def _require_selected_sources_have_handoff(sources: list[Top500CandidateSourceInput]) -> None:
    for source in sources:
        handoff = _handoff_result(source)
        if not handoff.allowed:
            raise SourceHandoffContractError("Golden Asset Source Handoff failed: " + ", ".join(handoff.reason_codes))


def _handoff_result(source: Top500CandidateSourceInput):
    decision = resolve_source_policy(source_identifier=source.source_identity)
    handoff_source = _source_handoff_payload(source, decision)
    return validate_source_handoff(handoff_source, action=SourcePolicyAction.generated_claim_support)


def _source_handoff_payload(source: Top500CandidateSourceInput, decision: SourcePolicyDecision) -> dict[str, Any]:
    return {
        **source_handoff_fields_from_policy(
            decision,
            source_identity=source.source_identity,
            parser_status=source.parser_status,
            approval_rationale=(
                "Reviewed deterministic official-source Top-500 candidate fixture input; retrieval alone is not evidence approval."
            ),
        ),
        "source_document_id": source.source_id,
        "source_type": source.source_type,
        "is_official": source.is_official,
        "source_quality": decision.source_quality if decision.source_quality is not SourceQuality.unknown else SourceQuality.fixture,
        "allowlist_status": decision.allowlist_status,
        "source_use_policy": decision.source_use_policy,
        "permitted_operations": decision.permitted_operations,
        "freshness_state": source.freshness_state,
        "as_of_date": source.source_snapshot_date,
        "retrieved_at": source.retrieved_at,
        "parser_failure_diagnostics": source.parser_failure_diagnostics,
    }


def _normalized_common_stock_rows(
    rows: list[Top500CandidateHoldingInput],
    *,
    source_by_id: dict[str, Top500CandidateSourceInput],
) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        ticker = normalize_candidate_ticker(row.ticker)
        markers = {row.asset_type.strip().lower(), row.security_type.strip().lower()}
        if ticker in {"", "-", "CASH", "USD", "CASH_USD"} or markers & _NON_COMMON_STOCK_MARKERS:
            continue
        warnings = []
        if ticker != row.ticker.strip().upper():
            warnings.append(f"normalized_ticker_from_{row.ticker.strip().upper()}")
        source = source_by_id[row.source_id]
        normalized_rows.append(
            {
                "ticker": ticker,
                "name": row.name.strip(),
                "weight": float(row.weight),
                "source_id": row.source_id,
                "source": source,
                "exchange": row.exchange,
                "warnings": warnings,
            }
        )
    return normalized_rows


def _rank_and_validate_rows(
    *,
    selected_rows: list[dict[str, Any]],
    sources_by_id: dict[str, Top500CandidateSourceInput],
    sec_rows: dict[str, dict[str, str]],
    nasdaq_rows: dict[str, dict[str, str]],
    rank_basis: Top500CandidateRankBasis,
    rank_limit: int,
) -> tuple[list[Top500CandidateRow], list[dict[str, str]]]:
    aggregated: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, str]] = []
    for row in selected_rows:
        ticker = row["ticker"]
        aggregate = aggregated.setdefault(
            ticker,
            {
                "ticker": ticker,
                "name": row["name"],
                "weight": 0.0,
                "source_ids": [],
                "warnings": [],
                "exchange": row.get("exchange"),
            },
        )
        aggregate["weight"] += row["weight"]
        aggregate["source_ids"].append(row["source_id"])
        aggregate["warnings"].extend(row["warnings"])

    ranked_inputs = sorted(aggregated.values(), key=lambda item: (-item["weight"], item["ticker"]))[:rank_limit]
    ranked_rows: list[Top500CandidateRow] = []
    for aggregate in ranked_inputs:
        ticker = aggregate["ticker"]
        nasdaq = nasdaq_rows.get(ticker)
        if nasdaq and str(nasdaq.get("ETF", "")).upper() == "Y":
            rejected.append({"ticker": ticker, "reason": "nasdaq_etf_flag", "field": "ETF"})
            continue
        if nasdaq and str(nasdaq.get("Test Issue", "")).upper() == "Y":
            rejected.append({"ticker": ticker, "reason": "nasdaq_test_issue_flag", "field": "Test Issue"})
            continue

        sec = sec_rows.get(ticker)
        warnings = list(dict.fromkeys(aggregate["warnings"]))
        validation_status = Top500CandidateValidationStatus.validated
        cik = sec.get("cik") if sec else None
        exchange = (sec.get("exchange") if sec else None) or aggregate.get("exchange") or (nasdaq or {}).get("Exchange")
        name = (sec.get("name") if sec else None) or aggregate["name"]
        if not sec:
            warnings.append("missing_sec_company_tickers_exchange_validation")
            validation_status = Top500CandidateValidationStatus.warning
        if not cik:
            warnings.append("missing_cik")
            validation_status = Top500CandidateValidationStatus.warning
        if not exchange:
            warnings.append("missing_exchange")
            validation_status = Top500CandidateValidationStatus.warning
            exchange = "UNKNOWN"

        first_source = sources_by_id[aggregate["source_ids"][0]]
        rank = len(ranked_rows) + 1
        checksum_input = "|".join(
            [
                ticker,
                name,
                "stock",
                "us_listed_common_stock",
                cik or "",
                exchange,
                str(rank),
                rank_basis.value,
                first_source.source_snapshot_date,
                first_source.source_checksum,
            ]
        )
        ranked_rows.append(
            Top500CandidateRow(
                ticker=ticker,
                name=name,
                cik=cik,
                exchange=exchange,
                rank=rank,
                rank_basis=rank_basis,
                source_provenance=f"{first_source.publisher} {first_source.ticker} mocked official holdings fixture",
                source_snapshot_date=first_source.source_snapshot_date,
                source_checksum=first_source.source_checksum,
                validation_status=validation_status,
                warnings=warnings,
                checksum_input=checksum_input,
                generated_checksum=_sha256(checksum_input),
            )
        )
    return ranked_rows, rejected


def _manual_review_triggers(
    *,
    fallback_used: bool,
    fallback_reason: str | None,
    validation_coverage: float,
    ranked_rows: list[Top500CandidateRow],
    rejected_rows: list[dict[str, str]],
    source_warnings: list[str],
) -> list[str]:
    triggers = ["manual_review_required_before_current_manifest_replacement"]
    if fallback_used:
        triggers.append("fallback_sources_used")
    if fallback_reason:
        triggers.append(fallback_reason)
    if validation_coverage < 0.95:
        triggers.append("validation_coverage_below_threshold")
    if any(not row.cik for row in ranked_rows):
        triggers.append("missing_cik_review")
    if rejected_rows:
        triggers.append("nasdaq_validation_failures")
    if any("freshness" in warning or "parser" in warning or "handoff" in warning for warning in source_warnings):
        triggers.append("source_snapshot_or_parser_warning")
    current_top = {entry.ticker for entry in load_top500_stock_universe_manifest().entries[:5]}
    if current_top - {row.ticker for row in ranked_rows}:
        triggers.append("top_ranked_current_names_disappear")
    changed_count = len(set(row.ticker for row in ranked_rows) ^ {entry.ticker for entry in load_top500_stock_universe_manifest().entries})
    if changed_count >= 5:
        triggers.append("many_tickers_changed")
    return list(dict.fromkeys(triggers))


def _operator_review_note_block(
    *,
    candidate_month: str,
    approved_current_manifest_path: str,
    source_used: list[str],
    rank_basis: str,
) -> list[str]:
    return [
        "One-cycle safe-promotion boundary: this candidate output is review-only and must not auto-promote runtime coverage.",
        f"Do not replace {approved_current_manifest_path} until an operator manually approves this {candidate_month} Top-500 refresh.",
        f"Before approval, validate source provenance, source checksums, and source snapshot dates for {', '.join(source_used)}.",
        f"Current rank method: {rank_basis}.",
    ]


def _validation_coverage(rows: list[Top500CandidateRow]) -> float:
    if not rows:
        return 0.0
    validated = sum(1 for row in rows if row.validation_status is Top500CandidateValidationStatus.validated)
    return round(validated / len(rows), 4)


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_sec_company_rows(path: str | Path) -> dict[str, dict[str, str]]:
    payload = _load_json(path)
    rows = payload.get("data", payload if isinstance(payload, list) else [])
    return {normalize_candidate_ticker(str(row["ticker"])): _string_values(row) for row in rows}


def _load_nasdaq_symbol_rows(path: str | Path) -> dict[str, dict[str, str]]:
    payload = _load_json(path)
    rows = payload.get("rows", payload if isinstance(payload, list) else [])
    return {normalize_candidate_ticker(str(row["Symbol"])): _string_values(row) for row in rows}


def _string_values(row: dict[str, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in row.items() if value is not None}


def _contains_advice_language(text: str) -> bool:
    lowered = text.lower()
    forbidden = (
        "should buy",
        "should sell",
        "should hold",
        "price target",
        "target price",
        "model portfolio",
        "personalized allocation",
        "brokerage",
        "tax advice",
    )
    return any(phrase in lowered for phrase in forbidden)


def _candidate_checksum_matches(manifest: Top500CandidateManifest) -> bool:
    return manifest.generated_checksum == _sha256(manifest.manifest_checksum_input)


def _diff_checksum_matches(diff_report: Top500CandidateDiffReport) -> bool:
    payload = diff_report.model_dump(mode="json")
    generated_checksum = payload.pop("generated_checksum")
    return generated_checksum == _sha256(_canonical_json(payload))


def _top500_packet_uses_fixture_or_local_only_provenance(manifest: Top500CandidateManifest) -> bool:
    text = _canonical_json(manifest.model_dump(mode="json")).lower()
    return any(marker in text for marker in ("fixture", "mock", "local-only", "mocked"))


def _top500_review_stop_conditions(
    *,
    candidate_manifest: Top500CandidateManifest,
    diff_report: Top500CandidateDiffReport,
    candidate_checksum_matches: bool,
    diff_checksum_matches: bool,
    missing_golden_tickers: list[str],
    warning_tickers: list[str],
    fixture_or_local_only: bool,
) -> list[str]:
    stop_conditions = ["missing_manual_review_or_approval"]
    if not candidate_checksum_matches:
        stop_conditions.append("candidate_checksum_mismatch")
    if not diff_checksum_matches:
        stop_conditions.append("diff_checksum_mismatch")
    if len(candidate_manifest.entries) < 500:
        stop_conditions.append("fixture_sized_candidate_not_launch_approved")
    if fixture_or_local_only:
        stop_conditions.append("fixture_or_local_only_provenance_not_launch_approved")
    if candidate_manifest.fallback_used:
        stop_conditions.append("fallback_source_requires_manual_review")
    if candidate_manifest.validation_coverage < 0.95:
        stop_conditions.append("low_validation_coverage")
    if missing_golden_tickers:
        stop_conditions.append("missing_golden_ticker")
    if warning_tickers or diff_report.nasdaq_validation_failures:
        stop_conditions.append("validation_warning")
    source_warning_text = " ".join(diff_report.source_warnings).lower()
    if "stale" in source_warning_text:
        stop_conditions.append("stale_source_snapshot")
    if "partial" in source_warning_text:
        stop_conditions.append("partial_source_snapshot")
    if "unknown" in source_warning_text:
        stop_conditions.append("unknown_source_state")
    if "unavailable" in source_warning_text:
        stop_conditions.append("unavailable_source_state")
    if "insufficient" in source_warning_text or not candidate_manifest.entries:
        stop_conditions.append("insufficient_evidence")
    return list(dict.fromkeys(stop_conditions))


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _pretty_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
