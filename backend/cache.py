from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel

from backend.models import (
    CacheEntryKind,
    CacheEntryMetadata,
    CacheEntryState,
    CacheInvalidationReason,
    CacheKeyMetadata,
    CacheRevalidationResult,
    CacheScope,
    FreshnessEvidenceGapInput,
    FreshnessFactInput,
    FreshnessRecentEventInput,
    FreshnessState,
    GeneratedOutputFreshnessInput,
    KnowledgePackFreshnessInput,
    SectionFreshnessInput,
    SourceChecksumInput,
    SourceChecksumRecord,
)


HASH_SCHEMA_VERSION = "cache-contract-v1"
TEXT_FINGERPRINT_SCHEMA_VERSION = "local-evidence-text-v1"


def build_cache_key(metadata: CacheKeyMetadata) -> str:
    identity = _cache_identity(metadata)
    parts = [
        "ltt",
        _key_part(metadata.schema_version),
        _key_part(metadata.scope.value),
        _key_part(metadata.entry_kind.value),
        identity,
        _key_part(metadata.mode_or_output_type),
        f"freshness-{_key_part(metadata.source_freshness_state.value)}",
        f"prompt-{_key_part(metadata.prompt_version or 'none')}",
        f"model-{_key_part(metadata.model_name or 'none')}",
        f"input-{_key_part(metadata.input_freshness_hash or 'none')}",
    ]
    return ":".join(parts)


def compute_source_document_checksum(source_input: SourceChecksumInput) -> SourceChecksumRecord:
    normalized_input = SourceChecksumInput(
        **{
            **source_input.model_dump(mode="json"),
            "fact_bindings": sorted(set(source_input.fact_bindings)),
            "recent_event_bindings": sorted(set(source_input.recent_event_bindings)),
            "citation_ids": sorted(set(source_input.citation_ids)),
            "local_chunk_text_fingerprints": sorted(set(source_input.local_chunk_text_fingerprints)),
        }
    )
    checksum = _hash_payload(normalized_input)
    return SourceChecksumRecord(
        source_document_id=normalized_input.source_document_id,
        asset_ticker=normalized_input.asset_ticker.upper(),
        checksum=checksum,
        freshness_state=normalized_input.freshness_state,
        cache_allowed=normalized_input.cache_allowed,
        source_type=normalized_input.source_type,
        source_rank=normalized_input.source_rank,
        citation_ids=normalized_input.citation_ids,
        fact_bindings=normalized_input.fact_bindings,
        recent_event_bindings=normalized_input.recent_event_bindings,
    )


def compute_knowledge_pack_freshness_hash(freshness_input: KnowledgePackFreshnessInput) -> str:
    payload = {
        **freshness_input.model_dump(mode="json"),
        "source_checksums": _sorted_models(freshness_input.source_checksums),
        "canonical_facts": _sorted_models(freshness_input.canonical_facts),
        "recent_events": _sorted_models(freshness_input.recent_events),
        "evidence_gaps": _sorted_models(freshness_input.evidence_gaps),
        "section_freshness_labels": _sorted_models(freshness_input.section_freshness_labels),
    }
    return _hash_payload(payload)


def compute_generated_output_freshness_hash(freshness_input: GeneratedOutputFreshnessInput) -> str:
    payload = {
        **freshness_input.model_dump(mode="json"),
        "source_checksums": _sorted_models(freshness_input.source_checksums),
        "canonical_facts": _sorted_models(freshness_input.canonical_facts),
        "recent_events": _sorted_models(freshness_input.recent_events),
        "evidence_gaps": _sorted_models(freshness_input.evidence_gaps),
        "section_freshness_labels": _sorted_models(freshness_input.section_freshness_labels),
    }
    return _hash_payload(payload)


def evaluate_cache_revalidation(
    cached_entry: CacheEntryMetadata | None,
    expected_cache_key: str,
    expected_freshness_hash: str | None = None,
    *,
    current_time: str | None = None,
    input_state: CacheEntryState | str | Enum | None = None,
    cache_allowed: bool = True,
) -> CacheRevalidationResult:
    normalized_input_state = _normalize_entry_state(input_state)
    if not cache_allowed or normalized_input_state is CacheEntryState.permission_limited:
        return _revalidation_result(
            cached_entry,
            CacheEntryState.permission_limited,
            False,
            CacheInvalidationReason.permission_limited,
            expected_cache_key,
            expected_freshness_hash,
            "Caching is not allowed for one or more required sources or provider responses.",
        )

    if normalized_input_state in {
        CacheEntryState.unsupported,
        CacheEntryState.unknown,
        CacheEntryState.unavailable,
        CacheEntryState.eligible_not_cached,
        CacheEntryState.stale,
    }:
        return _blocked_state_result(cached_entry, normalized_input_state, expected_cache_key, expected_freshness_hash)

    if cached_entry is None:
        return _revalidation_result(
            cached_entry,
            CacheEntryState.miss,
            False,
            CacheInvalidationReason.no_entry,
            expected_cache_key,
            expected_freshness_hash,
            "No cached entry is available for this cache key.",
        )

    if cached_entry.cache_allowed is False:
        return _revalidation_result(
            cached_entry,
            CacheEntryState.permission_limited,
            False,
            CacheInvalidationReason.permission_limited,
            expected_cache_key,
            expected_freshness_hash,
            "The cached entry records a provider or source permission limit.",
        )

    if cached_entry.entry_state in {
        CacheEntryState.unsupported,
        CacheEntryState.unknown,
        CacheEntryState.unavailable,
        CacheEntryState.eligible_not_cached,
        CacheEntryState.stale,
        CacheEntryState.permission_limited,
    }:
        return _blocked_state_result(cached_entry, cached_entry.entry_state, expected_cache_key, expected_freshness_hash)

    if cached_entry.cache_key != expected_cache_key:
        return _revalidation_result(
            cached_entry,
            CacheEntryState.miss,
            False,
            CacheInvalidationReason.cache_key_mismatch,
            expected_cache_key,
            expected_freshness_hash,
            "The cached entry key does not match the expected cache identity.",
        )

    if _has_blocking_freshness_metadata(cached_entry):
        return _revalidation_result(
            cached_entry,
            CacheEntryState.stale,
            False,
            CacheInvalidationReason.stale_input,
            expected_cache_key,
            expected_freshness_hash,
            "Cached metadata preserves stale, unknown, or unavailable source states.",
        )

    if _is_expired(cached_entry, current_time):
        return _revalidation_result(
            cached_entry,
            CacheEntryState.expired,
            False,
            CacheInvalidationReason.expired,
            expected_cache_key,
            expected_freshness_hash,
            "The cached entry is past its explicit expiration time.",
        )

    if expected_freshness_hash and cached_entry.generated_output_freshness_hash != expected_freshness_hash:
        return _revalidation_result(
            cached_entry,
            CacheEntryState.hash_mismatch,
            False,
            CacheInvalidationReason.hash_mismatch,
            expected_cache_key,
            expected_freshness_hash,
            "The generated-output freshness hash no longer matches the current evidence inputs.",
        )

    return _revalidation_result(
        cached_entry,
        CacheEntryState.hit,
        True,
        CacheInvalidationReason.none,
        expected_cache_key,
        expected_freshness_hash,
        "The cached entry is reusable for the current deterministic contract inputs.",
    )


def local_text_fingerprint(text: str) -> str:
    normalized = " ".join(text.split())
    return _hash_string(f"{TEXT_FINGERPRINT_SCHEMA_VERSION}:{normalized}")


def source_checksum_from_retrieval_source(
    source: Any,
    *,
    chunks: list[Any] | None = None,
    facts: list[Any] | None = None,
    recent_events: list[Any] | None = None,
) -> SourceChecksumRecord:
    source_id = _attr(source, "source_document_id")
    source_input = SourceChecksumInput(
        source_document_id=source_id,
        asset_ticker=_attr(source, "asset_ticker"),
        source_type=_attr(source, "source_type"),
        source_rank=_optional_attr(source, "source_rank"),
        publisher=_attr(source, "publisher"),
        url=_optional_attr(source, "url"),
        published_at=_optional_attr(source, "published_at"),
        as_of_date=_optional_attr(source, "as_of_date"),
        retrieved_at=_optional_attr(source, "retrieved_at"),
        freshness_state=_freshness(_attr(source, "freshness_state")),
        content_type=_optional_attr(source, "content_type"),
        fact_bindings=_fact_bindings(facts or [], source_id),
        recent_event_bindings=_recent_event_bindings(recent_events or [], source_id),
        citation_ids=_citation_bindings(facts or [], recent_events or []),
        local_chunk_text_fingerprints=_chunk_text_fingerprints(chunks or [], source_id),
        cache_allowed=True,
        redistribution_allowed=False,
    )
    return compute_source_document_checksum(source_input)


def source_checksum_from_provider_attribution(
    source: Any,
    *,
    facts: list[Any] | None = None,
    recent_events: list[Any] | None = None,
) -> SourceChecksumRecord:
    source_id = _attr(source, "source_document_id")
    licensing = _optional_attr(source, "licensing")
    source_input = SourceChecksumInput(
        source_document_id=source_id,
        asset_ticker=_attr(source, "asset_ticker"),
        source_type=_attr(source, "source_type"),
        source_rank=_optional_attr(source, "source_rank"),
        publisher=_attr(source, "publisher"),
        url=_optional_attr(source, "url"),
        published_at=_optional_attr(source, "published_at"),
        as_of_date=_optional_attr(source, "as_of_date"),
        retrieved_at=_optional_attr(source, "retrieved_at"),
        freshness_state=_freshness(_attr(source, "freshness_state")),
        content_type=None,
        provider_name=_optional_attr(source, "provider_name"),
        fact_bindings=_fact_bindings(facts or [], source_id),
        recent_event_bindings=_recent_event_bindings(recent_events or [], source_id),
        citation_ids=_citation_bindings(facts or [], recent_events or []),
        cache_allowed=bool(_optional_attr(licensing, "cache_allowed", True)),
        redistribution_allowed=bool(_optional_attr(licensing, "redistribution_allowed", False)),
    )
    return compute_source_document_checksum(source_input)


def build_knowledge_pack_freshness_input(
    pack: Any,
    *,
    section_freshness_labels: list[SectionFreshnessInput] | None = None,
) -> KnowledgePackFreshnessInput:
    sources = list(_optional_attr(pack, "source_documents", []))
    facts = list(_optional_attr(pack, "normalized_facts", []))
    chunks = list(_optional_attr(pack, "source_chunks", []))
    recent_events = list(_optional_attr(pack, "recent_developments", []))
    evidence_gaps = list(_optional_attr(pack, "evidence_gaps", []))
    asset = _optional_attr(pack, "asset")
    freshness = _optional_attr(pack, "freshness")

    source_checksums = [
        source_checksum_from_retrieval_source(
            source,
            chunks=_items_for_source(chunks, source.source_document_id),
            facts=_items_for_source(facts, source.source_document_id),
            recent_events=_items_for_source(recent_events, source.source_document_id),
        )
        for source in sources
    ]

    page_freshness_state = _freshness(_optional_attr(freshness, "freshness_state", FreshnessState.unavailable))
    return KnowledgePackFreshnessInput(
        asset_ticker=_optional_attr(asset, "ticker"),
        pack_identity=_optional_attr(asset, "ticker"),
        source_checksums=source_checksums,
        canonical_facts=[_freshness_fact_input(fact) for fact in facts],
        recent_events=[_freshness_recent_event_input(event) for event in recent_events],
        evidence_gaps=[_freshness_gap_input(gap) for gap in evidence_gaps],
        page_freshness_state=page_freshness_state,
        section_freshness_labels=section_freshness_labels
        or [
            SectionFreshnessInput(
                section_id="page",
                freshness_state=page_freshness_state,
                evidence_state="supported" if _optional_attr(asset, "supported", False) else "unavailable",
                as_of_date=_optional_attr(freshness, "facts_as_of"),
                retrieved_at=_optional_attr(freshness, "page_last_updated_at"),
            )
        ],
    )


def build_comparison_pack_freshness_input(
    comparison_pack: Any,
    *,
    section_freshness_labels: list[SectionFreshnessInput] | None = None,
) -> KnowledgePackFreshnessInput:
    left_pack = _attr(comparison_pack, "left_asset_pack")
    right_pack = _attr(comparison_pack, "right_asset_pack")
    left = _attr(left_pack, "asset")
    right = _attr(right_pack, "asset")
    left_input = build_knowledge_pack_freshness_input(left_pack)
    right_input = build_knowledge_pack_freshness_input(right_pack)
    comparison_sources = list(_optional_attr(comparison_pack, "comparison_sources", []))
    source_checksums = [
        checksum
        for checksum in [*left_input.source_checksums, *right_input.source_checksums]
        if checksum.source_document_id in {source.source_document_id for source in comparison_sources}
    ]
    return KnowledgePackFreshnessInput(
        comparison_left_ticker=left.ticker,
        comparison_right_ticker=right.ticker,
        pack_identity=_attr(comparison_pack, "comparison_pack_id"),
        source_checksums=source_checksums,
        canonical_facts=[*left_input.canonical_facts, *right_input.canonical_facts],
        recent_events=[*left_input.recent_events, *right_input.recent_events],
        evidence_gaps=[*left_input.evidence_gaps, *right_input.evidence_gaps],
        page_freshness_state=_combined_freshness_state(
            [left_input.page_freshness_state, right_input.page_freshness_state]
        ),
        section_freshness_labels=section_freshness_labels
        or [
            SectionFreshnessInput(
                section_id="comparison",
                freshness_state=_combined_freshness_state(
                    [left_input.page_freshness_state, right_input.page_freshness_state]
                ),
                evidence_state="supported",
            )
        ],
    )


def build_generated_output_freshness_input(
    *,
    output_identity: str,
    entry_kind: CacheEntryKind,
    scope: CacheScope,
    schema_version: str,
    knowledge_input: KnowledgePackFreshnessInput,
    prompt_version: str | None = None,
    model_name: str | None = None,
) -> GeneratedOutputFreshnessInput:
    return GeneratedOutputFreshnessInput(
        output_identity=output_identity,
        entry_kind=entry_kind,
        scope=scope,
        schema_version=schema_version,
        source_freshness_state=knowledge_input.page_freshness_state,
        prompt_version=prompt_version,
        model_name=model_name,
        source_checksums=knowledge_input.source_checksums,
        canonical_facts=knowledge_input.canonical_facts,
        recent_events=knowledge_input.recent_events,
        evidence_gaps=knowledge_input.evidence_gaps,
        section_freshness_labels=knowledge_input.section_freshness_labels,
    )


def cache_entry_metadata_from_generated_output(
    *,
    cache_key: str,
    freshness_input: GeneratedOutputFreshnessInput,
    freshness_hash: str,
    citation_ids: list[str] | None = None,
    expires_at: str | None = None,
    created_at: str | None = None,
    cache_allowed: bool = True,
    export_allowed: bool = False,
) -> CacheEntryMetadata:
    source_states = {
        checksum.source_document_id: checksum.freshness_state for checksum in freshness_input.source_checksums
    }
    return CacheEntryMetadata(
        cache_key=cache_key,
        entry_kind=freshness_input.entry_kind,
        scope=freshness_input.scope,
        schema_version=freshness_input.schema_version,
        generated_output_freshness_hash=freshness_hash,
        source_checksum_hashes=sorted({checksum.checksum for checksum in freshness_input.source_checksums}),
        source_document_ids=sorted({checksum.source_document_id for checksum in freshness_input.source_checksums}),
        citation_ids=sorted(set(citation_ids or [])),
        source_freshness_states=source_states,
        section_freshness_labels={
            label.section_id: label.freshness_state for label in freshness_input.section_freshness_labels
        },
        unknown_states=[
            gap.gap_id for gap in freshness_input.evidence_gaps if gap.freshness_state is FreshnessState.unknown
        ],
        stale_states=[
            gap.gap_id for gap in freshness_input.evidence_gaps if gap.freshness_state is FreshnessState.stale
        ],
        unavailable_states=[
            gap.gap_id for gap in freshness_input.evidence_gaps if gap.freshness_state is FreshnessState.unavailable
        ],
        cache_allowed=cache_allowed and all(checksum.cache_allowed for checksum in freshness_input.source_checksums),
        export_allowed=export_allowed,
        created_at=created_at,
        expires_at=expires_at,
        prompt_version=freshness_input.prompt_version,
        model_name=freshness_input.model_name,
    )


def _cache_identity(metadata: CacheKeyMetadata) -> str:
    if metadata.scope is CacheScope.comparison:
        left = _key_part(metadata.comparison_left_ticker or "missing-left")
        right = _key_part(metadata.comparison_right_ticker or "missing-right")
        pack = _key_part(metadata.pack_identity or f"{left}-vs-{right}")
        return f"comparison-{left}-to-{right}-pack-{pack}"
    if metadata.asset_ticker:
        return f"asset-{_key_part(metadata.asset_ticker)}"
    return f"pack-{_key_part(metadata.pack_identity or 'global')}"


def _blocked_state_result(
    cached_entry: CacheEntryMetadata | None,
    state: CacheEntryState,
    expected_cache_key: str,
    expected_freshness_hash: str | None,
) -> CacheRevalidationResult:
    reason_by_state = {
        CacheEntryState.unsupported: CacheInvalidationReason.unsupported,
        CacheEntryState.unknown: CacheInvalidationReason.unknown,
        CacheEntryState.unavailable: CacheInvalidationReason.unavailable,
        CacheEntryState.eligible_not_cached: CacheInvalidationReason.eligible_not_cached,
        CacheEntryState.stale: CacheInvalidationReason.stale_input,
        CacheEntryState.permission_limited: CacheInvalidationReason.permission_limited,
    }
    return _revalidation_result(
        cached_entry,
        state,
        False,
        reason_by_state[state],
        expected_cache_key,
        expected_freshness_hash,
        f"The current inputs are {state.value}; generated-output cache reuse is blocked.",
    )


def _revalidation_result(
    cached_entry: CacheEntryMetadata | None,
    state: CacheEntryState,
    reusable: bool,
    reason: CacheInvalidationReason,
    expected_cache_key: str,
    expected_freshness_hash: str | None,
    message: str,
) -> CacheRevalidationResult:
    return CacheRevalidationResult(
        state=state,
        reusable=reusable,
        invalidation_reason=reason,
        cache_key=expected_cache_key,
        expected_freshness_hash=expected_freshness_hash,
        cached_freshness_hash=cached_entry.generated_output_freshness_hash if cached_entry else None,
        source_document_ids=cached_entry.source_document_ids if cached_entry else [],
        citation_ids=cached_entry.citation_ids if cached_entry else [],
        source_freshness_states=cached_entry.source_freshness_states if cached_entry else {},
        section_freshness_labels=cached_entry.section_freshness_labels if cached_entry else {},
        message=message,
    )


def _has_blocking_freshness_metadata(cached_entry: CacheEntryMetadata) -> bool:
    if cached_entry.stale_states or cached_entry.unknown_states or cached_entry.unavailable_states:
        return True
    blocked_source_states = {FreshnessState.stale, FreshnessState.unknown, FreshnessState.unavailable}
    return any(state in blocked_source_states for state in cached_entry.source_freshness_states.values())


def _is_expired(cached_entry: CacheEntryMetadata, current_time: str | None) -> bool:
    if not cached_entry.expires_at or not current_time:
        return False
    expires_at = _parse_timestamp(cached_entry.expires_at)
    now = _parse_timestamp(current_time)
    if expires_at is None or now is None:
        return False
    return now > expires_at


def _parse_timestamp(value: str) -> datetime | None:
    try:
        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _normalize_entry_state(value: CacheEntryState | str | Enum | None) -> CacheEntryState | None:
    if value is None:
        return None
    raw = value.value if isinstance(value, Enum) else str(value)
    if raw in {"supported", "fresh", "no_high_signal"}:
        return CacheEntryState.available
    if raw in {"rate_limited"}:
        return CacheEntryState.unavailable
    try:
        return CacheEntryState(raw)
    except ValueError:
        return None


def _freshness(value: Any) -> FreshnessState:
    if isinstance(value, FreshnessState):
        return value
    if isinstance(value, Enum):
        return FreshnessState(value.value)
    return FreshnessState(str(value))


def _freshness_fact_input(item: Any) -> FreshnessFactInput:
    fact = _record(item, "fact")
    source_ids = list(_optional_attr(fact, "source_document_ids", []))
    if not source_ids and _optional_attr(fact, "source_document_id"):
        source_ids = [_attr(fact, "source_document_id")]
    return FreshnessFactInput(
        fact_id=_attr(fact, "fact_id"),
        asset_ticker=_attr(fact, "asset_ticker"),
        field_name=_attr(fact, "field_name"),
        value=_optional_attr(fact, "value"),
        as_of_date=_optional_attr(fact, "as_of_date"),
        freshness_state=_freshness(_attr(fact, "freshness_state")),
        evidence_state=_state_text(_optional_attr(fact, "evidence_state", "supported")),
        source_document_ids=source_ids,
        citation_ids=list(_optional_attr(fact, "citation_ids", [])),
    )


def _freshness_recent_event_input(item: Any) -> FreshnessRecentEventInput:
    event = _record(item, "recent_development")
    return FreshnessRecentEventInput(
        event_id=_attr(event, "event_id"),
        asset_ticker=_attr(event, "asset_ticker"),
        event_type=_attr(event, "event_type"),
        event_date=_optional_attr(event, "event_date"),
        source_date=_optional_attr(event, "source_date"),
        as_of_date=_optional_attr(event, "as_of_date"),
        freshness_state=_freshness(_attr(event, "freshness_state")),
        evidence_state=_state_text(_optional_attr(event, "evidence_state", "supported")),
        source_document_id=_optional_attr(event, "source_document_id"),
        citation_ids=list(_optional_attr(event, "citation_ids", [])),
    )


def _freshness_gap_input(item: Any) -> FreshnessEvidenceGapInput:
    return FreshnessEvidenceGapInput(
        gap_id=_attr(item, "gap_id"),
        asset_ticker=_attr(item, "asset_ticker"),
        field_name=_attr(item, "field_name"),
        evidence_state=_state_text(_attr(item, "evidence_state")),
        freshness_state=_freshness(_attr(item, "freshness_state")),
        source_document_id=_optional_attr(item, "source_document_id"),
    )


def _items_for_source(items: list[Any], source_document_id: str) -> list[Any]:
    return [item for item in items if _item_source_document_id(item) == source_document_id]


def _item_source_document_id(item: Any) -> str | None:
    for candidate in [item, _optional_attr(item, "fact"), _optional_attr(item, "recent_development"), _optional_attr(item, "chunk")]:
        if candidate is not None and _optional_attr(candidate, "source_document_id") is not None:
            return _optional_attr(candidate, "source_document_id")
    source = _optional_attr(item, "source_document")
    return _optional_attr(source, "source_document_id")


def _fact_bindings(items: list[Any], source_document_id: str) -> list[str]:
    bindings = []
    for item in items:
        fact = _record(item, "fact")
        source_ids = list(_optional_attr(fact, "source_document_ids", []))
        if not source_ids and _optional_attr(fact, "source_document_id"):
            source_ids = [_attr(fact, "source_document_id")]
        if source_document_id in source_ids:
            value_hash = _hash_payload(_optional_attr(fact, "value"))
            bindings.append(
                "|".join(
                    [
                        "fact",
                        _attr(fact, "fact_id"),
                        _attr(fact, "field_name"),
                        value_hash,
                        str(_optional_attr(fact, "as_of_date", "")),
                        _state_text(_optional_attr(fact, "freshness_state", "")),
                    ]
                )
            )
    return sorted(set(bindings))


def _recent_event_bindings(items: list[Any], source_document_id: str) -> list[str]:
    bindings = []
    for item in items:
        event = _record(item, "recent_development")
        if _optional_attr(event, "source_document_id") == source_document_id:
            bindings.append(
                "|".join(
                    [
                        "event",
                        _attr(event, "event_id"),
                        _attr(event, "event_type"),
                        str(_optional_attr(event, "event_date", "")),
                        str(_optional_attr(event, "source_date", "")),
                        _state_text(_optional_attr(event, "freshness_state", "")),
                    ]
                )
            )
    return sorted(set(bindings))


def _citation_bindings(facts: list[Any], recent_events: list[Any]) -> list[str]:
    citations: set[str] = set()
    for item in [*facts, *recent_events]:
        record = _record(item, "fact") if _optional_attr(item, "fact") is not None else item
        record = _record(record, "recent_development") if _optional_attr(record, "recent_development") is not None else record
        citations.update(str(citation_id) for citation_id in _optional_attr(record, "citation_ids", []))
    return sorted(citations)


def _chunk_text_fingerprints(chunks: list[Any], source_document_id: str) -> list[str]:
    fingerprints = []
    for item in chunks:
        chunk = _record(item, "chunk")
        if _optional_attr(chunk, "source_document_id") == source_document_id:
            fingerprints.append(local_text_fingerprint(_attr(chunk, "text")))
    return sorted(set(fingerprints))


def _combined_freshness_state(states: list[FreshnessState]) -> FreshnessState:
    for state in [FreshnessState.unavailable, FreshnessState.unknown, FreshnessState.stale]:
        if state in states:
            return state
    return FreshnessState.fresh


def _record(item: Any, nested_name: str) -> Any:
    nested = _optional_attr(item, nested_name)
    return nested if nested is not None else item


def _state_text(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _attr(item: Any, name: str) -> Any:
    value = _optional_attr(item, name)
    if value is None:
        raise ValueError(f"Missing required cache contract attribute: {name}")
    return value


def _optional_attr(item: Any, name: str, default: Any = None) -> Any:
    if item is None:
        return default
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _sorted_models(items: list[BaseModel]) -> list[dict[str, Any]]:
    dumped = [item.model_dump(mode="json") for item in items]
    return sorted(dumped, key=_canonical_json)


def _hash_payload(value: Any) -> str:
    return _hash_string(f"{HASH_SCHEMA_VERSION}:{_canonical_json(value)}")


def _hash_string(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(_canonical_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(mode="json"))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _canonical_value(val) for key, val in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    return value


def _key_part(value: str) -> str:
    chars = [char.lower() if char.isalnum() else "-" for char in value.strip()]
    compact = "-".join(part for part in "".join(chars).split("-") if part)
    return compact or "none"
