from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
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
    DEFAULT_ALLOWED_SOURCE_OPERATIONS,
    DEFAULT_ALLOWED_EXCERPT_BEHAVIOR,
    DEFAULT_BLOCKED_EXCERPT_BEHAVIOR,
    DEFAULT_BLOCKED_SOURCE_OPERATIONS,
    SourceAllowedExcerptBehavior,
    SourceAllowlistManifest,
    SourceAllowlistRecord,
    SourceAllowlistStatus,
    SourceExportRights,
    SourceOperationPermissions,
    SourceParserStatus,
    SourcePolicyDecision,
    SourcePolicyDecisionState,
    SourceQuality,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
    FreshnessState,
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
TEXT_LIMITED_SOURCE_USE_POLICIES = {
    SourceUsePolicy.metadata_only,
    SourceUsePolicy.link_only,
    SourceUsePolicy.rejected,
}


class SourcePolicyAction(str, Enum):
    generated_claim_support = "generated_claim_support"
    cache_input_checksum = "cache_input_checksum"
    cacheable_generated_output = "cacheable_generated_output"
    source_list_export_metadata = "source_list_export_metadata"
    allowed_excerpt_export = "allowed_excerpt_export"
    markdown_json_section_export = "markdown_json_section_export"
    diagnostics = "diagnostics"


@dataclass(frozen=True)
class SourcePolicyActionDecision:
    action: SourcePolicyAction
    allowed: bool
    reason_code: str
    source_use_policy: SourceUsePolicy
    allowlist_status: SourceAllowlistStatus
    sanitized_diagnostics_only: bool = False
    metadata_only: bool = False
    text_or_excerpt_allowed: bool = False
    generated_output_eligible: bool = False


class SourcePolicyError(ValueError):
    """Raised when source-use policy configuration violates the deterministic contract."""


class SourceHandoffContractError(ValueError):
    """Raised when retrieved source metadata is not approved for evidence use."""


@dataclass(frozen=True)
class SourceHandoffValidationResult:
    allowed: bool
    reason_codes: tuple[str, ...]
    source_use_policy: SourceUsePolicy
    allowlist_status: SourceAllowlistStatus
    review_status: SourceReviewStatus
    parser_status: SourceParserStatus
    storage_rights: SourceStorageRights
    export_rights: SourceExportRights


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
    return evaluate_source_policy_action(decision, SourcePolicyAction.generated_claim_support).allowed


def source_can_export_excerpt(decision: SourcePolicyDecision) -> bool:
    return evaluate_source_policy_action(decision, SourcePolicyAction.allowed_excerpt_export).allowed


def source_can_cache_input_checksum(decision: SourcePolicyDecision) -> bool:
    return evaluate_source_policy_action(decision, SourcePolicyAction.cache_input_checksum).allowed


def source_can_feed_generated_output_cache(decision: SourcePolicyDecision) -> bool:
    return evaluate_source_policy_action(decision, SourcePolicyAction.cacheable_generated_output).allowed


def source_can_export_source_metadata(decision: SourcePolicyDecision) -> bool:
    return evaluate_source_policy_action(decision, SourcePolicyAction.source_list_export_metadata).allowed


def source_can_support_markdown_json_export(decision: SourcePolicyDecision) -> bool:
    return evaluate_source_policy_action(decision, SourcePolicyAction.markdown_json_section_export).allowed


def classify_source_policy_actions(decision: SourcePolicyDecision) -> dict[SourcePolicyAction, SourcePolicyActionDecision]:
    return {action: evaluate_source_policy_action(decision, action) for action in SourcePolicyAction}


def evaluate_source_policy_action(
    decision: SourcePolicyDecision,
    action: SourcePolicyAction | str,
) -> SourcePolicyActionDecision:
    normalized_action = SourcePolicyAction(action)
    base = {
        "action": normalized_action,
        "source_use_policy": decision.source_use_policy,
        "allowlist_status": decision.allowlist_status,
        "metadata_only": decision.source_use_policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only},
    }

    blocked_reason = _policy_block_reason(decision)
    if normalized_action is SourcePolicyAction.diagnostics:
        return SourcePolicyActionDecision(
            **base,
            allowed=True,
            sanitized_diagnostics_only=True,
            reason_code="diagnostics_sanitized_only" if blocked_reason else "diagnostics_compact_metadata_only",
        )
    if blocked_reason:
        return SourcePolicyActionDecision(**base, allowed=False, reason_code=blocked_reason)

    operations = decision.permitted_operations
    policy = decision.source_use_policy

    if normalized_action is SourcePolicyAction.cache_input_checksum:
        allowed = operations.can_store_metadata and operations.can_cache and policy is not SourceUsePolicy.rejected
        return SourcePolicyActionDecision(
            **base,
            allowed=allowed,
            reason_code="cache_checksum_metadata_only" if allowed else "cache_checksum_not_permitted",
        )

    if normalized_action is SourcePolicyAction.source_list_export_metadata:
        allowed = operations.can_display_metadata and operations.can_export_metadata and policy is not SourceUsePolicy.rejected
        return SourcePolicyActionDecision(
            **base,
            allowed=allowed,
            reason_code="source_metadata_export_allowed" if allowed else "source_metadata_export_not_permitted",
        )

    if normalized_action is SourcePolicyAction.allowed_excerpt_export:
        allowed = (
            policy in {SourceUsePolicy.summary_allowed, SourceUsePolicy.full_text_allowed}
            and decision.allowed_excerpt.allowed
            and operations.can_export_excerpt
        )
        return SourcePolicyActionDecision(
            **base,
            allowed=allowed,
            reason_code="bounded_excerpt_export_allowed" if allowed else _text_limited_reason(policy),
            text_or_excerpt_allowed=allowed,
        )

    if normalized_action in {
        SourcePolicyAction.generated_claim_support,
        SourcePolicyAction.cacheable_generated_output,
        SourcePolicyAction.markdown_json_section_export,
    }:
        allowed = (
            policy not in TEXT_LIMITED_SOURCE_USE_POLICIES
            and operations.can_support_generated_output
            and operations.can_support_citations
        )
        if normalized_action is SourcePolicyAction.cacheable_generated_output:
            allowed = allowed and operations.can_cache
        if normalized_action is SourcePolicyAction.markdown_json_section_export:
            allowed = allowed and operations.can_export_metadata
        return SourcePolicyActionDecision(
            **base,
            allowed=allowed,
            reason_code="generated_output_rights_allowed" if allowed else _text_limited_reason(policy),
            text_or_excerpt_allowed=policy in {SourceUsePolicy.summary_allowed, SourceUsePolicy.full_text_allowed},
            generated_output_eligible=allowed,
        )

    raise SourcePolicyError(f"Unhandled source policy action: {normalized_action.value}.")


def policy_fields_from_decision(decision: SourcePolicyDecision) -> dict[str, Any]:
    return {
        "source_quality": decision.source_quality,
        "allowlist_status": decision.allowlist_status,
        "source_use_policy": decision.source_use_policy,
        "permitted_operations": decision.permitted_operations,
    }


def source_handoff_fields_from_policy(
    decision: SourcePolicyDecision,
    *,
    source_identity: str | None = None,
    parser_status: SourceParserStatus = SourceParserStatus.parsed,
    approval_rationale: str | None = None,
) -> dict[str, Any]:
    return {
        "source_identity": source_identity or decision.source_id,
        "storage_rights": _storage_rights_for_policy(decision.source_use_policy),
        "export_rights": _export_rights_for_policy(decision.source_use_policy),
        "review_status": _review_status_for_decision(decision),
        "approval_rationale": approval_rationale or decision.reason,
        "parser_status": parser_status,
        "parser_failure_diagnostics": None,
    }


def validate_source_handoff(
    source: Any,
    *,
    action: SourcePolicyAction | str = SourcePolicyAction.generated_claim_support,
) -> SourceHandoffValidationResult:
    normalized_action = SourcePolicyAction(action)
    source_type = str(_source_attr(source, "source_type", "") or "").strip()
    source_identity = str(
        _source_attr(source, "source_identity", None)
        or _source_attr(source, "url", None)
        or _source_attr(source, "source_document_id", "")
        or ""
    ).strip()
    approval_rationale = str(_source_attr(source, "approval_rationale", "") or "").strip()
    parser_failure_diagnostics = str(_source_attr(source, "parser_failure_diagnostics", "") or "").strip()

    source_use_policy = _coerce_enum(
        SourceUsePolicy,
        _source_attr(source, "source_use_policy", SourceUsePolicy.rejected),
        SourceUsePolicy.rejected,
    )
    allowlist_status = _coerce_enum(
        SourceAllowlistStatus,
        _source_attr(source, "allowlist_status", SourceAllowlistStatus.not_allowlisted),
        SourceAllowlistStatus.not_allowlisted,
    )
    review_status = _coerce_enum(
        SourceReviewStatus,
        _source_attr(source, "review_status", SourceReviewStatus.pending_review),
        SourceReviewStatus.pending_review,
    )
    parser_status = _coerce_enum(
        SourceParserStatus,
        _source_attr(source, "parser_status", SourceParserStatus.pending_review),
        SourceParserStatus.pending_review,
    )
    storage_rights = _coerce_enum(
        SourceStorageRights,
        _source_attr(source, "storage_rights", SourceStorageRights.unknown),
        SourceStorageRights.unknown,
    )
    export_rights = _coerce_enum(
        SourceExportRights,
        _source_attr(source, "export_rights", SourceExportRights.unknown),
        SourceExportRights.unknown,
    )
    freshness_state = _coerce_enum(
        FreshnessState,
        _source_attr(source, "freshness_state", FreshnessState.unavailable),
        FreshnessState.unavailable,
    )
    source_quality = _coerce_enum(
        SourceQuality,
        _source_attr(source, "source_quality", SourceQuality.unknown),
        SourceQuality.unknown,
    )
    is_official = _source_attr(source, "is_official", None)

    reasons: list[str] = []
    if not source_identity:
        reasons.append("missing_source_identity")
    if not source_type:
        reasons.append("missing_source_type")
    if is_official is None:
        reasons.append("missing_official_source_status")
    if not approval_rationale:
        reasons.append("missing_approval_rationale")
    if allowlist_status is not SourceAllowlistStatus.allowed:
        reasons.append(f"allowlist_{allowlist_status.value}")
    if review_status is not SourceReviewStatus.approved:
        reasons.append(f"review_{review_status.value}")
    if source_use_policy is SourceUsePolicy.rejected:
        reasons.append("source_rejected")
    if storage_rights in {SourceStorageRights.unknown, SourceStorageRights.rejected}:
        reasons.append(f"storage_rights_{storage_rights.value}")
    if export_rights in {SourceExportRights.unknown, SourceExportRights.rejected}:
        reasons.append(f"export_rights_{export_rights.value}")
    if parser_status in {SourceParserStatus.failed, SourceParserStatus.pending_review}:
        reasons.append(f"parser_{parser_status.value}")
    if parser_status is SourceParserStatus.failed and not parser_failure_diagnostics:
        reasons.append("missing_parser_failure_diagnostics")
    if not (
        _source_attr(source, "as_of_date", None)
        or _source_attr(source, "published_at", None)
        or _source_attr(source, "retrieved_at", None)
    ):
        reasons.append("missing_freshness_as_of_metadata")
    if source_quality in {SourceQuality.rejected, SourceQuality.unknown}:
        reasons.append(f"source_quality_{source_quality.value}")
    if _is_hidden_or_internal_source(source_type, source_identity):
        reasons.append("hidden_or_internal_source")

    action_decision = evaluate_source_policy_action(
        SourcePolicyDecision(
            decision=(
                SourcePolicyDecisionState.allowed
                if allowlist_status is SourceAllowlistStatus.allowed and review_status is SourceReviewStatus.approved
                else SourcePolicyDecisionState.pending_review
            ),
            matched_by="none",
            source_quality=source_quality,
            allowlist_status=allowlist_status,
            source_use_policy=source_use_policy,
            permitted_operations=_source_operations(source),
            allowed_excerpt=(
                DEFAULT_ALLOWED_EXCERPT_BEHAVIOR.model_copy()
                if source_use_policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed}
                else DEFAULT_BLOCKED_EXCERPT_BEHAVIOR.model_copy()
            ),
            reason=approval_rationale or "Source handoff metadata is incomplete.",
        ),
        normalized_action,
    )
    if not action_decision.allowed:
        reasons.append(action_decision.reason_code)

    return SourceHandoffValidationResult(
        allowed=not reasons,
        reason_codes=tuple(dict.fromkeys(reasons)),
        source_use_policy=source_use_policy,
        allowlist_status=allowlist_status,
        review_status=review_status,
        parser_status=parser_status,
        storage_rights=storage_rights,
        export_rights=export_rights,
    )


def require_source_handoff(
    source: Any,
    *,
    action: SourcePolicyAction | str = SourcePolicyAction.generated_claim_support,
) -> SourceHandoffValidationResult:
    result = validate_source_handoff(source, action=action)
    if not result.allowed:
        raise SourceHandoffContractError("Golden Asset Source Handoff failed: " + ", ".join(result.reason_codes))
    return result


def excerpt_text_for_policy(text: str, decision: SourcePolicyDecision) -> str | None:
    if not source_can_export_excerpt(decision):
        return None
    words = text.split()
    max_words = decision.allowed_excerpt.max_words
    if max_words and len(words) > max_words:
        return " ".join(words[:max_words])
    return text


def _policy_block_reason(decision: SourcePolicyDecision) -> str | None:
    if decision.decision is not SourcePolicyDecisionState.allowed:
        if decision.decision is SourcePolicyDecisionState.not_allowlisted:
            return "source_not_allowlisted"
        if decision.decision is SourcePolicyDecisionState.pending_review:
            return "source_pending_review"
        return "source_rejected"
    if decision.allowlist_status is not SourceAllowlistStatus.allowed:
        return f"allowlist_{decision.allowlist_status.value}"
    if decision.source_use_policy is SourceUsePolicy.rejected:
        return "source_rejected"
    return None


def _text_limited_reason(policy: SourceUsePolicy) -> str:
    if policy is SourceUsePolicy.metadata_only:
        return "metadata_only_content_omitted"
    if policy is SourceUsePolicy.link_only:
        return "link_only_content_omitted"
    if policy is SourceUsePolicy.rejected:
        return "source_rejected"
    return "operation_not_permitted"


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


def _source_attr(source: Any, name: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _coerce_enum(enum_type: type[Enum], value: Any, default: Any) -> Any:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except (TypeError, ValueError):
        return default


def _source_operations(source: Any) -> SourceOperationPermissions:
    operations = _source_attr(source, "permitted_operations", None)
    if isinstance(operations, SourceOperationPermissions):
        return operations
    if operations is not None:
        try:
            return SourceOperationPermissions.model_validate(operations)
        except Exception:
            return DEFAULT_BLOCKED_SOURCE_OPERATIONS.model_copy()
    policy = _coerce_enum(
        SourceUsePolicy,
        _source_attr(source, "source_use_policy", SourceUsePolicy.rejected),
        SourceUsePolicy.rejected,
    )
    if policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed}:
        return DEFAULT_ALLOWED_SOURCE_OPERATIONS.model_copy(
            update={
                "can_store_raw_text": policy is SourceUsePolicy.full_text_allowed,
                "can_cache": bool(_source_attr(source, "cache_allowed", True)),
                "can_export_metadata": bool(_source_attr(source, "export_allowed", True)),
                "can_export_excerpt": policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed},
            }
        )
    if policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only}:
        return SourceOperationPermissions(
            can_store_metadata=True,
            can_store_raw_text=False,
            can_display_metadata=True,
            can_display_excerpt=False,
            can_summarize=False,
            can_cache=bool(_source_attr(source, "cache_allowed", False)),
            can_export_metadata=bool(_source_attr(source, "export_allowed", False)),
            can_export_excerpt=False,
            can_export_full_text=False,
            can_support_generated_output=False,
            can_support_citations=False,
            can_support_canonical_facts=False,
            can_support_recent_developments=False,
        )
    return DEFAULT_BLOCKED_SOURCE_OPERATIONS.model_copy()


def _storage_rights_for_policy(policy: SourceUsePolicy) -> SourceStorageRights:
    if policy is SourceUsePolicy.full_text_allowed:
        return SourceStorageRights.raw_snapshot_allowed
    if policy is SourceUsePolicy.summary_allowed:
        return SourceStorageRights.summary_allowed
    if policy is SourceUsePolicy.metadata_only:
        return SourceStorageRights.metadata_only
    if policy is SourceUsePolicy.link_only:
        return SourceStorageRights.link_only
    return SourceStorageRights.rejected


def _export_rights_for_policy(policy: SourceUsePolicy) -> SourceExportRights:
    if policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed}:
        return SourceExportRights.excerpts_allowed
    if policy is SourceUsePolicy.metadata_only:
        return SourceExportRights.metadata_only
    if policy is SourceUsePolicy.link_only:
        return SourceExportRights.link_only
    return SourceExportRights.rejected


def _review_status_for_decision(decision: SourcePolicyDecision) -> SourceReviewStatus:
    if decision.decision is SourcePolicyDecisionState.allowed and decision.allowlist_status is SourceAllowlistStatus.allowed:
        return SourceReviewStatus.approved
    if decision.decision is SourcePolicyDecisionState.rejected or decision.allowlist_status is SourceAllowlistStatus.rejected:
        return SourceReviewStatus.rejected
    return SourceReviewStatus.pending_review


def _is_hidden_or_internal_source(source_type: str, source_identity: str) -> bool:
    text = f"{source_type} {source_identity}".lower()
    return any(marker in text for marker in ("hidden", "internal", "private://", "localhost", "127.0.0.1"))
