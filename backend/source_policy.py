from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - dependency-free quality gate fallback.
    import sys

    ROOT_FOR_FALLBACK = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT_FOR_FALLBACK / "scripts"))
    import yaml

from backend.models import (
    DEFAULT_BLOCKED_EXCERPT_BEHAVIOR,
    DEFAULT_BLOCKED_SOURCE_OPERATIONS,
    SourceAllowedExcerptBehavior,
    SourceAllowlistManifest,
    SourceAllowlistRecord,
    SourceAllowlistStatus,
    SourceOperationPermissions,
    SourcePolicyDecision,
    SourcePolicyDecisionState,
    SourceQuality,
    SourceUsePolicy,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ALLOWLIST_PATH = ROOT / "config" / "source_allowlist.yaml"
REQUIRED_SOURCE_USE_POLICIES = {
    SourceUsePolicy.metadata_only,
    SourceUsePolicy.link_only,
    SourceUsePolicy.summary_allowed,
    SourceUsePolicy.full_text_allowed,
    SourceUsePolicy.rejected,
}


class SourcePolicyError(ValueError):
    """Raised when source-use policy configuration violates the deterministic contract."""


@lru_cache(maxsize=4)
def load_source_allowlist(path: str | None = None) -> SourceAllowlistManifest:
    manifest_path = Path(path) if path else DEFAULT_SOURCE_ALLOWLIST_PATH
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest = SourceAllowlistManifest.model_validate(data)
    validate_source_allowlist(manifest)
    return manifest


def validate_source_allowlist(manifest: SourceAllowlistManifest) -> SourceAllowlistManifest:
    if not manifest.no_live_external_calls:
        raise SourcePolicyError("Source allowlist validation must not require live external calls.")

    seen_match_keys: set[tuple[str, str]] = set()
    seen_source_ids: set[str] = set()
    policies = {record.source_use_policy for record in manifest.source_records}
    missing_policies = REQUIRED_SOURCE_USE_POLICIES - policies
    if missing_policies:
        missing = ", ".join(sorted(policy.value for policy in missing_policies))
        raise SourcePolicyError(f"Source allowlist must cover required policy tiers: {missing}.")

    for record in manifest.source_records:
        if record.source_id in seen_source_ids:
            raise SourcePolicyError(f"Duplicate source allowlist ID: {record.source_id}.")
        seen_source_ids.add(record.source_id)

        match_value = _record_match_value(record)
        match_key = (record.match_kind, match_value)
        if match_key in seen_match_keys:
            raise SourcePolicyError(f"Duplicate source allowlist match key: {record.match_kind}:{match_value}.")
        seen_match_keys.add(match_key)

        _validate_record_consistency(record)

    return manifest


def resolve_source_policy(
    *,
    url: str | None = None,
    source_identifier: str | None = None,
    provider_name: str | None = None,
    manifest: SourceAllowlistManifest | None = None,
) -> SourcePolicyDecision:
    registry = manifest or load_source_allowlist()

    if source_identifier:
        fixture = _match_local_fixture(source_identifier, registry.source_records)
        if fixture is not None:
            return _decision_from_record(fixture, matched_by="local_fixture")

    if provider_name:
        provider = _match_provider(provider_name, registry.source_records)
        if provider is not None:
            return _decision_from_record(provider, matched_by="provider")

    domain = _domain_from_url(url)
    if domain:
        record = _match_domain(domain, registry.source_records)
        if record is not None:
            return _decision_from_record(record, matched_by="domain")

    return SourcePolicyDecision(
        decision=SourcePolicyDecisionState.not_allowlisted,
        matched_by="none",
        source_quality=SourceQuality.unknown,
        allowlist_status=SourceAllowlistStatus.not_allowlisted,
        source_use_policy=SourceUsePolicy.rejected,
        permitted_operations=DEFAULT_BLOCKED_SOURCE_OPERATIONS.model_copy(),
        allowed_excerpt=DEFAULT_BLOCKED_EXCERPT_BEHAVIOR.model_copy(),
        reason="Source is not present in the local source allowlist.",
    )


def source_can_support_generated_output(decision: SourcePolicyDecision) -> bool:
    return (
        decision.decision is SourcePolicyDecisionState.allowed
        and decision.allowlist_status is SourceAllowlistStatus.allowed
        and decision.source_use_policy
        not in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only, SourceUsePolicy.rejected}
        and decision.permitted_operations.can_support_generated_output
        and decision.permitted_operations.can_support_citations
    )


def source_can_export_excerpt(decision: SourcePolicyDecision) -> bool:
    return (
        decision.decision is SourcePolicyDecisionState.allowed
        and decision.allowed_excerpt.allowed
        and decision.permitted_operations.can_export_excerpt
        and decision.source_use_policy in {SourceUsePolicy.summary_allowed, SourceUsePolicy.full_text_allowed}
    )


def policy_fields_from_decision(decision: SourcePolicyDecision) -> dict[str, Any]:
    return {
        "source_quality": decision.source_quality,
        "allowlist_status": decision.allowlist_status,
        "source_use_policy": decision.source_use_policy,
        "permitted_operations": decision.permitted_operations,
    }


def excerpt_text_for_policy(text: str, decision: SourcePolicyDecision) -> str | None:
    if not source_can_export_excerpt(decision):
        return None
    words = text.split()
    max_words = decision.allowed_excerpt.max_words
    if max_words and len(words) > max_words:
        return " ".join(words[:max_words])
    return text


def _decision_from_record(record: SourceAllowlistRecord, *, matched_by: str) -> SourcePolicyDecision:
    if record.allowlist_status is SourceAllowlistStatus.allowed:
        decision = SourcePolicyDecisionState.allowed
        reason = "Source matched an allowed local source-use policy record."
    elif record.allowlist_status is SourceAllowlistStatus.pending_review:
        decision = SourcePolicyDecisionState.pending_review
        reason = "Source matched a pending-review policy record and cannot feed generated output."
    else:
        decision = SourcePolicyDecisionState.rejected
        reason = "Source matched a rejected source-use policy record."

    return SourcePolicyDecision(
        decision=decision,
        source_id=record.source_id,
        matched_by=matched_by,  # type: ignore[arg-type]
        source_quality=record.source_quality,
        allowlist_status=record.allowlist_status,
        source_use_policy=record.source_use_policy,
        permitted_operations=record.permitted_operations,
        allowed_excerpt=record.allowed_excerpt,
        recent_context_only=record.recent_context_only,
        canonical_facts_allowed=record.canonical_facts_allowed,
        reason=reason,
    )


def _validate_record_consistency(record: SourceAllowlistRecord) -> None:
    operations = record.permitted_operations

    if record.allowlist_status is SourceAllowlistStatus.rejected:
        if record.source_use_policy is not SourceUsePolicy.rejected:
            raise SourcePolicyError(f"Rejected record {record.source_id} must use the rejected policy tier.")
        if any(_operation_values(operations)):
            raise SourcePolicyError(f"Rejected record {record.source_id} cannot permit source operations.")

    if record.source_use_policy is SourceUsePolicy.rejected and record.allowlist_status is not SourceAllowlistStatus.rejected:
        raise SourcePolicyError(f"Rejected policy record {record.source_id} must have rejected allowlist status.")

    if record.source_use_policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only}:
        if operations.can_store_raw_text or operations.can_display_excerpt or operations.can_export_excerpt:
            raise SourcePolicyError(f"{record.source_id} cannot expose passages under {record.source_use_policy.value}.")
        if operations.can_support_generated_output or operations.can_support_citations:
            raise SourcePolicyError(f"{record.source_id} cannot support generated claims under {record.source_use_policy.value}.")

    if record.source_use_policy is SourceUsePolicy.summary_allowed:
        if operations.can_store_raw_text or operations.can_export_full_text:
            raise SourcePolicyError(f"Summary-allowed source {record.source_id} cannot store or export full raw text.")
        if not record.allowed_excerpt.allowed or not operations.can_display_excerpt:
            raise SourcePolicyError(f"Summary-allowed source {record.source_id} must define allowed excerpt behavior.")

    if record.source_use_policy is SourceUsePolicy.full_text_allowed:
        if not operations.can_store_raw_text:
            raise SourcePolicyError(f"Full-text source {record.source_id} must permit raw text storage.")
        if operations.can_export_full_text:
            raise SourcePolicyError(f"Full source text export remains disabled for MVP fixtures: {record.source_id}.")

    if record.recent_context_only and operations.can_support_canonical_facts:
        raise SourcePolicyError(f"Recent-context-only source {record.source_id} cannot support canonical facts.")


def _record_match_value(record: SourceAllowlistRecord) -> str:
    if record.match_kind == "domain" and record.domain:
        return _normalize_domain(record.domain)
    if record.match_kind == "local_fixture" and record.fixture_identifier:
        return record.fixture_identifier
    if record.match_kind == "provider" and record.provider_name:
        return _normalize_provider(record.provider_name)
    raise SourcePolicyError(f"Source allowlist record {record.source_id} is missing its match value.")


def _match_domain(domain: str, records: list[SourceAllowlistRecord]) -> SourceAllowlistRecord | None:
    normalized = _normalize_domain(domain)
    candidates = [
        record
        for record in records
        if record.match_kind == "domain"
        and record.domain
        and (normalized == _normalize_domain(record.domain) or normalized.endswith(f".{_normalize_domain(record.domain)}"))
    ]
    return sorted(candidates, key=lambda record: len(record.domain or ""), reverse=True)[0] if candidates else None


def _match_local_fixture(identifier: str, records: list[SourceAllowlistRecord]) -> SourceAllowlistRecord | None:
    matches = [
        record
        for record in records
        if record.match_kind == "local_fixture"
        and record.fixture_identifier
        and identifier.startswith(record.fixture_identifier)
    ]
    return sorted(matches, key=lambda record: len(record.fixture_identifier or ""), reverse=True)[0] if matches else None


def _match_provider(provider_name: str, records: list[SourceAllowlistRecord]) -> SourceAllowlistRecord | None:
    normalized = _normalize_provider(provider_name)
    for record in records:
        if record.match_kind == "provider" and record.provider_name and _normalize_provider(record.provider_name) == normalized:
            return record
    return None


def _domain_from_url(url: str | None) -> str | None:
    if not url or "://" not in url or url.startswith("local://"):
        return None
    without_scheme = url.split("://", 1)[1]
    authority = without_scheme.split("/", 1)[0].split("@")[-1]
    host = authority.split(":", 1)[0]
    return _normalize_domain(host) if host else None


def _normalize_domain(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("www."):
        normalized = normalized[4:]
    return normalized


def _normalize_provider(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _operation_values(operations: SourceOperationPermissions) -> list[bool]:
    return [bool(value) for value in operations.model_dump(mode="json").values()]

