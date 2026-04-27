from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.data import load_top500_stock_universe_manifest, normalize_ticker
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
TOP500_APPROVED_CURRENT_MANIFEST_PATH = "data/universes/us_common_stocks_top500.current.json"
TOP500_CANDIDATE_OUTPUT_TEMPLATE = "data/universes/us_common_stocks_top500.candidate.{candidate_month}.json"
TOP500_DIFF_OUTPUT_TEMPLATE = "data/universes/us_common_stocks_top500.diff.{candidate_month}.json"
TOP500_REFRESH_BOUNDARY = "top500-reviewed-candidate-refresh-v1"

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
    return manifest


def build_top500_candidate_diff_report(
    *,
    candidate_manifest: Top500CandidateManifest,
    rejected_rows: list[dict[str, str]],
    source_warnings: list[str],
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
    }
    diff_json = _canonical_json(diff_payload)
    return Top500CandidateDiffReport.model_validate({**diff_payload, "generated_checksum": _sha256(diff_json)})


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


def normalize_candidate_ticker(ticker: str) -> str:
    normalized = normalize_ticker(ticker).replace("-", ".")
    if "/" in normalized and len(normalized.split("/", 1)[1]) == 1:
        normalized = normalized.replace("/", ".")
    return normalized


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


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _pretty_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
