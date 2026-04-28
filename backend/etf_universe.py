from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from backend.models import (
    ETFUniverseCategory,
    ETFUniverseEntry,
    ETFUniverseLaunchCacheState,
    ETFUniverseManifest,
    ETFUniverseSupportState,
    FreshnessState,
    SourceQuality,
)


SUPPORTED_ETF_UNIVERSE_MANIFEST_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "universes" / "us_equity_etfs_supported.current.json"
)
RECOGNITION_ETF_UNIVERSE_MANIFEST_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "universes" / "us_etp_recognition.current.json"
)
ETF_UNIVERSE_SCHEMA_VERSION = "us-equity-etf-universe-v1"
ETF_LAUNCH_REVIEW_PACKET_SCHEMA_VERSION = "etf-launch-review-packet-v1"
ETF_LAUNCH_REVIEW_BOUNDARY = "etf-launch-manifest-review-only-v1"
ETF_UNIVERSE_PRODUCTION_MIRROR_ENV_VAR = "EQUITY_ETF_UNIVERSE_MANIFEST_URI"
ETF_UNIVERSE_MANIFEST_PATHS = {
    "data/universes/us_equity_etfs_supported.current.json",
    "data/universes/us_etp_recognition.current.json",
    "data/universes/us_equity_etfs.current.json",
}

SUPPORTED_SCOPE_ETF_CATEGORIES = {
    ETFUniverseCategory.us_equity_index_etf,
    ETFUniverseCategory.us_equity_sector_etf,
    ETFUniverseCategory.us_equity_thematic_etf,
}
BLOCKED_ETF_CATEGORIES = {
    ETFUniverseCategory.leveraged_etf,
    ETFUniverseCategory.inverse_etf,
    ETFUniverseCategory.etn,
    ETFUniverseCategory.fixed_income_etf,
    ETFUniverseCategory.commodity_etf,
    ETFUniverseCategory.active_etf,
    ETFUniverseCategory.multi_asset_etf,
    ETFUniverseCategory.other_unsupported,
}
FORBIDDEN_MANIFEST_LANGUAGE = (
    "should buy",
    "should sell",
    "should hold",
    "you should " + "invest",
    "price target",
    "target price",
    "personalized allocation",
    "model portfolio inclusion",
    "guaranteed " + "return",
    "execute a " + "trade",
    "place a " + "trade",
    "brokerage account",
)


class ETFUniverseContractError(ValueError):
    """Raised when the deterministic ETF universe metadata contract is invalid."""


def normalize_etf_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def validate_etf_universe_manifest(manifest: ETFUniverseManifest) -> ETFUniverseManifest:
    if manifest.schema_version != ETF_UNIVERSE_SCHEMA_VERSION:
        raise ETFUniverseContractError(f"Unsupported ETF universe schema version: {manifest.schema_version}")
    if manifest.local_path not in ETF_UNIVERSE_MANIFEST_PATHS:
        raise ETFUniverseContractError("ETF manifest local_path must point to the runtime local manifest path.")
    if manifest.production_mirror_env_var != ETF_UNIVERSE_PRODUCTION_MIRROR_ENV_VAR:
        raise ETFUniverseContractError("ETF manifest must declare the private production mirror env var.")
    if not manifest.entries:
        raise ETFUniverseContractError("ETF manifest must contain at least one entry.")
    _validate_checksum("ETF manifest", manifest.checksum_input, manifest.generated_checksum)
    _assert_no_advice_language(manifest)

    tickers = [entry.ticker for entry in manifest.entries]
    if len(tickers) != len(set(tickers)):
        raise ETFUniverseContractError("ETF manifest entries must have unique tickers.")
    for entry in manifest.entries:
        _validate_entry(manifest, entry)
    return manifest


def load_etf_universe_manifest_from_path(path: str | Path) -> ETFUniverseManifest:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_etf_universe_manifest(ETFUniverseManifest.model_validate(payload))


@lru_cache(maxsize=1)
def load_supported_etf_universe_manifest() -> ETFUniverseManifest:
    with SUPPORTED_ETF_UNIVERSE_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_etf_universe_manifest(ETFUniverseManifest.model_validate(payload))


@lru_cache(maxsize=1)
def load_recognition_etf_universe_manifest() -> ETFUniverseManifest:
    with RECOGNITION_ETF_UNIVERSE_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_etf_universe_manifest(ETFUniverseManifest.model_validate(payload))

@lru_cache(maxsize=1)
def load_etf_universe_manifest() -> ETFUniverseManifest:
    # Backward-compatible alias for callers that have not been migrated to explicit
    # supported/recognition split loading.
    return load_supported_etf_universe_manifest()


def etf_universe_entries_by_ticker() -> dict[str, ETFUniverseEntry]:
    supported = {entry.ticker: entry for entry in load_supported_etf_universe_manifest().entries}
    recognition = {entry.ticker: entry for entry in load_recognition_etf_universe_manifest().entries}
    return {**supported, **recognition}


def etf_universe_entry(ticker: str) -> ETFUniverseEntry | None:
    return etf_universe_entries_by_ticker().get(normalize_etf_ticker(ticker))


def cached_supported_etf_entries() -> dict[str, ETFUniverseEntry]:
    return {
        entry.ticker: entry
        for entry in load_supported_etf_universe_manifest().entries
        if entry.support_state is ETFUniverseSupportState.cached_supported
    }


def eligible_not_cached_etf_entries() -> dict[str, ETFUniverseEntry]:
    return {
        entry.ticker: entry
        for entry in load_supported_etf_universe_manifest().entries
        if entry.support_state is ETFUniverseSupportState.eligible_not_cached
    }


def blocked_etf_entries() -> dict[str, ETFUniverseEntry]:
    return {
        entry.ticker: entry
        for entry in load_recognition_etf_universe_manifest().entries
        if entry.support_state
        in {
            ETFUniverseSupportState.recognized_unsupported,
            ETFUniverseSupportState.out_of_scope,
            ETFUniverseSupportState.unknown,
            ETFUniverseSupportState.unavailable,
        }
    }


def can_generate_output_for_etf_entry(entry: ETFUniverseEntry) -> bool:
    return (
        entry.support_state is ETFUniverseSupportState.cached_supported
        and entry.launch_cache_state is ETFUniverseLaunchCacheState.cached
        and entry.etf_category in SUPPORTED_SCOPE_ETF_CATEGORIES
        and not _has_exclusion_flags(entry)
    )


def build_etf_launch_review_packet(
    *,
    supported_manifest: ETFUniverseManifest | None = None,
    recognition_manifest: ETFUniverseManifest | None = None,
) -> dict[str, object]:
    supported = supported_manifest or load_supported_etf_universe_manifest()
    recognition = recognition_manifest or load_recognition_etf_universe_manifest()
    validate_etf_universe_manifest(supported)
    validate_etf_universe_manifest(recognition)
    supported_entries = [_entry_review_row(entry, manifest_kind="supported") for entry in supported.entries]
    recognition_entries = [_entry_review_row(entry, manifest_kind="recognition") for entry in recognition.entries]
    stop_conditions = _etf_review_stop_conditions(
        supported=supported,
        recognition=recognition,
        supported_entries=supported_entries,
        recognition_entries=recognition_entries,
    )
    review_status = "blocked" if any(condition.endswith("checksum_mismatch") for condition in stop_conditions) else (
        "review_needed" if stop_conditions else "pass"
    )
    return {
        "schema_version": ETF_LAUNCH_REVIEW_PACKET_SCHEMA_VERSION,
        "boundary": ETF_LAUNCH_REVIEW_BOUNDARY,
        "review_only": True,
        "no_live_external_calls": True,
        "launch_approved": False,
        "manual_promotion_required": True,
        "supported_runtime_authority": "data/universes/us_equity_etfs_supported.current.json",
        "recognition_runtime_authority": "data/universes/us_etp_recognition.current.json",
        "recognition_rows_unlock_generated_output": False,
        "review_status": review_status,
        "stop_conditions": stop_conditions,
        "supported_manifest": _manifest_review_summary(supported, supported_entries),
        "recognition_manifest": _manifest_review_summary(recognition, recognition_entries),
        "supported_entries": supported_entries,
        "recognition_entries": recognition_entries,
        "blocked_generated_output_capabilities": [
            "generated_pages",
            "chat_answers",
            "comparisons",
            "Weekly News Focus",
            "AI Comprehensive Analysis",
            "exports",
            "generated_risk_summaries",
        ],
        "non_advice_framing": (
            "ETF manifest review is operational coverage metadata only; it is not an endorsement, recommendation, "
            "model portfolio, allocation, price target, or trading instruction."
        ),
    }


def legacy_eligible_not_cached_etf_metadata() -> dict[str, dict[str, str | list[str] | None]]:
    metadata: dict[str, dict[str, str | list[str] | None]] = {}
    for entry in eligible_not_cached_etf_entries().values():
        metadata[entry.ticker] = {
            "name": entry.fund_name,
            "asset_type": entry.asset_type,
            "exchange": entry.exchange,
            "issuer": entry.issuer,
            "aliases": entry.aliases,
            "launch_group": _legacy_launch_group(entry),
            "manifest_id": load_supported_etf_universe_manifest().manifest_id,
            "etf_category": entry.etf_category.value,
            "support_state": entry.support_state.value,
            "launch_cache_state": entry.launch_cache_state.value,
            "source_provenance": entry.source_provenance,
            "snapshot_date": entry.snapshot_date,
            "approval_timestamp": entry.approval_timestamp,
        }
    return metadata


def _validate_entry(manifest: ETFUniverseManifest, entry: ETFUniverseEntry) -> None:
    if entry.ticker != normalize_etf_ticker(entry.ticker):
        raise ETFUniverseContractError("ETF manifest tickers must be normalized uppercase symbols.")
    if entry.asset_type != "etf":
        raise ETFUniverseContractError("ETF manifest entries must use asset_type='etf'.")
    if entry.snapshot_date != manifest.snapshot_date:
        raise ETFUniverseContractError("ETF manifest entry snapshot dates must match the manifest snapshot date.")
    if not entry.source_provenance or not entry.entry_provenance:
        raise ETFUniverseContractError("ETF manifest entries must include source and entry provenance metadata.")
    _validate_checksum(f"ETF manifest entry {entry.ticker}", entry.checksum_input, entry.generated_checksum)
    if entry.ticker not in entry.checksum_input:
        raise ETFUniverseContractError("ETF manifest entry checksum_input must include the ticker.")

    if entry.support_state in {
        ETFUniverseSupportState.cached_supported,
        ETFUniverseSupportState.eligible_not_cached,
    }:
        if entry.etf_category not in SUPPORTED_SCOPE_ETF_CATEGORIES:
            raise ETFUniverseContractError("Supported-scope ETF entries must be equity index, sector, or thematic ETFs.")
        if _has_exclusion_flags(entry):
            raise ETFUniverseContractError("Supported-scope ETF entries cannot carry exclusion flags.")
        expected_cache_state = (
            ETFUniverseLaunchCacheState.cached
            if entry.support_state is ETFUniverseSupportState.cached_supported
            else ETFUniverseLaunchCacheState.not_cached
        )
        if entry.launch_cache_state is not expected_cache_state:
            raise ETFUniverseContractError("Supported-scope ETF entries have conflicting cache state metadata.")
        return

    if entry.support_state in {
        ETFUniverseSupportState.recognized_unsupported,
        ETFUniverseSupportState.out_of_scope,
    }:
        if entry.launch_cache_state is not ETFUniverseLaunchCacheState.blocked:
            raise ETFUniverseContractError("Blocked ETF entries must use launch_cache_state='blocked'.")
        if entry.etf_category not in BLOCKED_ETF_CATEGORIES or not _has_exclusion_flags(entry):
            raise ETFUniverseContractError("Blocked ETF entries must declare a blocked category and exclusion flag.")
        return

    if entry.support_state is ETFUniverseSupportState.unknown:
        if entry.etf_category is not ETFUniverseCategory.unknown:
            raise ETFUniverseContractError("Unknown ETF entries must use etf_category='unknown'.")
        if entry.launch_cache_state is not ETFUniverseLaunchCacheState.unknown:
            raise ETFUniverseContractError("Unknown ETF entries must use launch_cache_state='unknown'.")
        return

    if entry.support_state is ETFUniverseSupportState.unavailable:
        if entry.etf_category is not ETFUniverseCategory.unavailable:
            raise ETFUniverseContractError("Unavailable ETF entries must use etf_category='unavailable'.")
        if entry.launch_cache_state is not ETFUniverseLaunchCacheState.unavailable:
            raise ETFUniverseContractError("Unavailable ETF entries must use launch_cache_state='unavailable'.")
        if not entry.evidence.unavailable_reason:
            raise ETFUniverseContractError("Unavailable ETF entries must explain the unavailable metadata state.")
        return

    raise ETFUniverseContractError(f"Unsupported ETF support state: {entry.support_state}")


def _validate_checksum(label: str, checksum_input: str, generated_checksum: str) -> None:
    if not checksum_input:
        raise ETFUniverseContractError(f"{label} must include checksum input.")
    expected = "sha256:" + hashlib.sha256(checksum_input.encode("utf-8")).hexdigest()
    if generated_checksum != expected:
        raise ETFUniverseContractError(f"{label} generated checksum does not match checksum_input.")


def _assert_no_advice_language(manifest: ETFUniverseManifest) -> None:
    text = " ".join(
        [
            manifest.coverage_purpose,
            manifest.policy_note,
            manifest.source_provenance,
            *(entry.source_provenance for entry in manifest.entries),
            *(entry.entry_provenance for entry in manifest.entries),
            *(entry.non_advice_framing for entry in manifest.entries),
        ]
    ).lower()
    hits = [phrase for phrase in FORBIDDEN_MANIFEST_LANGUAGE if phrase in text]
    if hits:
        raise ETFUniverseContractError(f"ETF manifest contains advice-like language: {hits}")


def _has_exclusion_flags(entry: ETFUniverseEntry) -> bool:
    return any(
        [
            entry.exclusion_flags.leveraged,
            entry.exclusion_flags.inverse,
            entry.exclusion_flags.etn,
            entry.exclusion_flags.fixed_income,
            entry.exclusion_flags.commodity,
            entry.exclusion_flags.active,
            entry.exclusion_flags.multi_asset,
            entry.exclusion_flags.crypto,
            entry.exclusion_flags.international,
            entry.exclusion_flags.other_unsupported,
        ]
    )


def _legacy_launch_group(entry: ETFUniverseEntry) -> str:
    if entry.etf_category is ETFUniverseCategory.us_equity_index_etf:
        return "broad_etf"
    return "sector_theme_etf"


def _entry_review_row(entry: ETFUniverseEntry, *, manifest_kind: str) -> dict[str, object]:
    exclusion_flags = entry.exclusion_flags.model_dump(mode="json")
    generated_output_eligible = manifest_kind == "supported" and can_generate_output_for_etf_entry(entry)
    return {
        "ticker": entry.ticker,
        "fund_name": entry.fund_name,
        "manifest_kind": manifest_kind,
        "issuer": entry.issuer,
        "exchange": entry.exchange,
        "listing_country": entry.listing_country,
        "wrapper_or_scope": entry.etf_category.value,
        "support_state": entry.support_state.value,
        "launch_cache_state": entry.launch_cache_state.value,
        "generated_output_eligible": generated_output_eligible,
        "blocked_state_reason": _blocked_state_reason(entry, generated_output_eligible=generated_output_eligible),
        "exclusion_flags": exclusion_flags,
        "evidence_state": entry.evidence.evidence_state.value,
        "freshness_state": entry.evidence.freshness_state.value,
        "evidence_as_of": entry.evidence.evidence_as_of,
        "retrieved_at": entry.evidence.retrieved_at,
        "source_use_policy": entry.evidence.source_use_policy.value,
        "source_quality": entry.evidence.source_quality.value,
        "parser_status": "not_available_in_manifest",
        "handoff_status": _handoff_status_for_entry(entry),
        "source_provenance": entry.source_provenance,
        "entry_provenance": entry.entry_provenance,
        "snapshot_date": entry.snapshot_date,
        "approval_timestamp": entry.approval_timestamp,
        "generated_checksum": entry.generated_checksum,
        "non_advice_framing": entry.non_advice_framing,
    }


def _manifest_review_summary(manifest: ETFUniverseManifest, entries: list[dict[str, object]]) -> dict[str, object]:
    return {
        "manifest_id": manifest.manifest_id,
        "local_path": manifest.local_path,
        "entry_count": len(manifest.entries),
        "snapshot_date": manifest.snapshot_date,
        "approved_at": manifest.approved_at,
        "source_provenance": manifest.source_provenance,
        "generated_checksum": manifest.generated_checksum,
        "checksum_matches": _manifest_checksum_matches(manifest),
        "support_state_counts": _count_values(str(entry["support_state"]) for entry in entries),
        "wrapper_or_scope_counts": _count_values(str(entry["wrapper_or_scope"]) for entry in entries),
        "source_quality_counts": _count_values(str(entry["source_quality"]) for entry in entries),
        "tickers": [str(entry["ticker"]) for entry in entries],
    }


def _etf_review_stop_conditions(
    *,
    supported: ETFUniverseManifest,
    recognition: ETFUniverseManifest,
    supported_entries: list[dict[str, object]],
    recognition_entries: list[dict[str, object]],
) -> list[str]:
    stop_conditions = ["missing_manual_review_or_approval"]
    if not _manifest_checksum_matches(supported):
        stop_conditions.append("supported_manifest_checksum_mismatch")
    if not _manifest_checksum_matches(recognition):
        stop_conditions.append("recognition_manifest_checksum_mismatch")
    expected_supported = {"VOO", "SPY", "VTI", "IVV", "QQQ", "IWM", "DIA", "VGT", "XLK", "SOXX", "SMH", "XLF", "XLV", "XLE"}
    supported_tickers = {entry.ticker for entry in supported.entries}
    if expected_supported - supported_tickers:
        stop_conditions.append("missing_golden_ticker")
    if _manifest_uses_fixture_or_local_only_provenance(supported) or _manifest_uses_fixture_or_local_only_provenance(recognition):
        stop_conditions.append("fixture_or_local_only_provenance_not_launch_approved")
    if len(supported.entries) < len(expected_supported):
        stop_conditions.append("fixture_sized_supported_manifest_not_launch_approved")
    if any(entry["manifest_kind"] == "recognition" and entry["generated_output_eligible"] for entry in recognition_entries):
        stop_conditions.append("recognition_generated_output_unlock_attempt")
    if any(str(entry["support_state"]) in {"unknown", "unavailable"} for entry in supported_entries + recognition_entries):
        stop_conditions.append("unknown_or_unavailable_review_needed")
    if any(str(entry["freshness_state"]) in {"stale", "unknown", "unavailable"} for entry in supported_entries + recognition_entries):
        stop_conditions.append("stale_unknown_or_unavailable_freshness_review_needed")
    if any(str(entry["evidence_state"]) in {"partial", "unknown", "unavailable", "insufficient_evidence"} for entry in supported_entries + recognition_entries):
        stop_conditions.append("partial_unknown_unavailable_or_insufficient_evidence_review_needed")
    if any(entry["source_quality"] == "fixture" for entry in supported_entries + recognition_entries):
        stop_conditions.append("fixture_source_quality_not_launch_approved")
    return list(dict.fromkeys(stop_conditions))


def _manifest_checksum_matches(manifest: ETFUniverseManifest) -> bool:
    return manifest.generated_checksum == "sha256:" + hashlib.sha256(manifest.checksum_input.encode("utf-8")).hexdigest()


def _manifest_uses_fixture_or_local_only_provenance(manifest: ETFUniverseManifest) -> bool:
    text = " ".join(
        [
            manifest.manifest_id,
            manifest.source_provenance,
            *(entry.source_provenance for entry in manifest.entries),
            *(entry.entry_provenance for entry in manifest.entries),
        ]
    ).lower()
    return any(marker in text for marker in ("fixture", "mock", "local-only"))


def _blocked_state_reason(entry: ETFUniverseEntry, *, generated_output_eligible: bool) -> str | None:
    if generated_output_eligible:
        return None
    if entry.support_state is ETFUniverseSupportState.eligible_not_cached:
        return "supported_but_not_cached_pending_ingestion"
    if entry.support_state in {ETFUniverseSupportState.recognized_unsupported, ETFUniverseSupportState.out_of_scope}:
        active_flags = [flag for flag, value in entry.exclusion_flags.model_dump(mode="json").items() if value]
        return "blocked_by_exclusion_flags:" + ",".join(active_flags or [entry.etf_category.value])
    if entry.support_state is ETFUniverseSupportState.unknown:
        return "unknown_recognition_state_blocks_generated_output"
    if entry.support_state is ETFUniverseSupportState.unavailable:
        return entry.evidence.unavailable_reason or "unavailable_metadata_blocks_generated_output"
    return "not_cached_or_not_supported_for_generated_output"


def _handoff_status_for_entry(entry: ETFUniverseEntry) -> str:
    if entry.evidence.source_quality is SourceQuality.fixture:
        return "fixture_metadata_only_review_needed"
    if entry.evidence.freshness_state in {FreshnessState.stale, FreshnessState.unknown, FreshnessState.unavailable}:
        return "freshness_review_needed"
    return "handoff_metadata_available"


def _count_values(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))
