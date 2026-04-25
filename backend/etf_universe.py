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
)


ETF_UNIVERSE_MANIFEST_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "universes" / "us_equity_etfs.current.json"
)
ETF_UNIVERSE_SCHEMA_VERSION = "us-equity-etf-universe-v1"
ETF_UNIVERSE_PRODUCTION_MIRROR_ENV_VAR = "EQUITY_ETF_UNIVERSE_MANIFEST_URI"

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
    if manifest.local_path != "data/universes/us_equity_etfs.current.json":
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


@lru_cache(maxsize=1)
def load_etf_universe_manifest() -> ETFUniverseManifest:
    with ETF_UNIVERSE_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_etf_universe_manifest(ETFUniverseManifest.model_validate(payload))


def etf_universe_entries_by_ticker() -> dict[str, ETFUniverseEntry]:
    return {entry.ticker: entry for entry in load_etf_universe_manifest().entries}


def etf_universe_entry(ticker: str) -> ETFUniverseEntry | None:
    return etf_universe_entries_by_ticker().get(normalize_etf_ticker(ticker))


def cached_supported_etf_entries() -> dict[str, ETFUniverseEntry]:
    return {
        entry.ticker: entry
        for entry in load_etf_universe_manifest().entries
        if entry.support_state is ETFUniverseSupportState.cached_supported
    }


def eligible_not_cached_etf_entries() -> dict[str, ETFUniverseEntry]:
    return {
        entry.ticker: entry
        for entry in load_etf_universe_manifest().entries
        if entry.support_state is ETFUniverseSupportState.eligible_not_cached
    }


def blocked_etf_entries() -> dict[str, ETFUniverseEntry]:
    return {
        entry.ticker: entry
        for entry in load_etf_universe_manifest().entries
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
            "manifest_id": load_etf_universe_manifest().manifest_id,
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
