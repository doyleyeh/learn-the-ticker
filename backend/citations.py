from __future__ import annotations

from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, Field

from backend.models import (
    FreshnessState,
    SourceAllowlistStatus,
    SourceExportRights,
    SourceParserStatus,
    SourceQuality,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
)
from backend.source_policy import SourcePolicyAction, validate_source_handoff


class CitationValidationStatus(str, Enum):
    valid = "valid"
    missing_citation = "missing_citation"
    citation_not_found = "citation_not_found"
    wrong_asset = "wrong_asset"
    stale_source = "stale_source"
    non_recent_source = "non_recent_source"
    unsupported_source = "unsupported_source"
    disallowed_source_policy = "disallowed_source_policy"
    insufficient_evidence = "insufficient_evidence"


class EvidenceKind(str, Enum):
    source_document = "source_document"
    document_chunk = "document_chunk"
    normalized_fact = "normalized_fact"


class CitationValidationClaim(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: str = "factual"
    citation_ids: list[str] = Field(default_factory=list)
    citation_required: bool = True
    important: bool = True
    freshness_label: FreshnessState | None = None
    required_asset_tickers: list[str] = Field(default_factory=list)


class CitationEvidence(BaseModel):
    citation_id: str
    asset_ticker: str
    source_document_id: str
    source_type: str
    evidence_kind: EvidenceKind = EvidenceKind.source_document
    freshness_state: FreshnessState = FreshnessState.fresh
    retrieved_at: str | None = "2026-04-25T00:00:00Z"
    as_of_date: str | None = None
    published_at: str | None = None
    supported_claim_types: list[str] = Field(default_factory=list)
    supporting_text: str | None = None
    supports_claim: bool = True
    is_recent: bool | None = None
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
    source_use_policy: SourceUsePolicy = SourceUsePolicy.full_text_allowed
    source_identity: str | None = None
    is_official: bool | None = False
    source_quality: SourceQuality = SourceQuality.fixture
    storage_rights: SourceStorageRights = SourceStorageRights.raw_snapshot_allowed
    export_rights: SourceExportRights = SourceExportRights.excerpts_allowed
    review_status: SourceReviewStatus = SourceReviewStatus.approved
    approval_rationale: str = "Deterministic fixture source passed local source-use policy review."
    parser_status: SourceParserStatus = SourceParserStatus.parsed
    parser_failure_diagnostics: str | None = None


class CitationValidationContext(BaseModel):
    allowed_asset_tickers: list[str]
    comparison_pack_id: str | None = None
    result_freshness_label: FreshnessState | None = None


class CitationValidationIssue(BaseModel):
    status: CitationValidationStatus
    claim_id: str
    message: str
    citation_id: str | None = None
    source_document_id: str | None = None


class CitationValidationResult(BaseModel):
    claim_id: str
    status: CitationValidationStatus
    issues: list[CitationValidationIssue] = Field(default_factory=list)


class CitationValidationReport(BaseModel):
    status: CitationValidationStatus
    results: list[CitationValidationResult] = Field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.status is CitationValidationStatus.valid

    @property
    def issues(self) -> list[CitationValidationIssue]:
        return [issue for result in self.results for issue in result.issues]


RECENT_SOURCE_TYPES = {
    "earnings_release",
    "issuer_press_release",
    "news_article",
    "recent_development",
    "sec_8k",
}

CLAIM_TYPE_ALIASES = {
    "fact": "factual",
    "factual_claim": "factual",
    "recent_development": "recent",
}

SOURCE_TYPES_BY_CLAIM_TYPE: dict[str, set[str]] = {
    "factual": {
        "document_chunk",
        "holdings_file",
        "issuer_fact_sheet",
        "issuer_page",
        "normalized_fact",
        "prospectus",
        "sec_filing",
        "structured_market_data",
        "summary_prospectus",
    },
    "risk": {
        "document_chunk",
        "issuer_fact_sheet",
        "normalized_fact",
        "prospectus",
        "sec_filing",
        "summary_prospectus",
    },
    "comparison": {
        "comparison_fact",
        "document_chunk",
        "holdings_file",
        "issuer_fact_sheet",
        "issuer_page",
        "normalized_fact",
        "prospectus",
        "sec_filing",
        "structured_market_data",
        "summary_prospectus",
    },
    "recent": RECENT_SOURCE_TYPES,
    "suitability": {
        "document_chunk",
        "issuer_fact_sheet",
        "normalized_fact",
        "prospectus",
        "sec_filing",
        "summary_prospectus",
    },
    "interpretation": {
        "document_chunk",
        "issuer_fact_sheet",
        "normalized_fact",
        "prospectus",
        "sec_filing",
        "structured_market_data",
        "summary_prospectus",
    },
}

SOURCE_TYPES_BY_CLAIM_TYPE["fact"] = SOURCE_TYPES_BY_CLAIM_TYPE["factual"]


def validate_claims(
    claims: Sequence[CitationValidationClaim | dict[str, Any]],
    evidence: Sequence[CitationEvidence | dict[str, Any]],
    context: CitationValidationContext | dict[str, Any],
) -> CitationValidationReport:
    normalized_claims = [_coerce(CitationValidationClaim, claim) for claim in claims]
    normalized_evidence = [_coerce(CitationEvidence, item) for item in evidence]
    normalized_context = _coerce(CitationValidationContext, context)

    evidence_by_id = {item.citation_id: item for item in normalized_evidence}
    allowed_assets = {_normalize_ticker(ticker) for ticker in normalized_context.allowed_asset_tickers}

    results = [
        _validate_claim(claim, evidence_by_id, allowed_assets, normalized_context) for claim in normalized_claims
    ]
    first_issue = next((result.issues[0].status for result in results if result.issues), CitationValidationStatus.valid)
    return CitationValidationReport(status=first_issue, results=results)


def evidence_from_sources(
    asset_ticker: str,
    citations: Sequence[Any],
    source_documents: Sequence[Any],
    supported_claim_types_by_citation: dict[str, list[str]] | None = None,
) -> list[CitationEvidence]:
    source_by_id = {source.source_document_id: source for source in source_documents}
    supported_claim_types_by_citation = supported_claim_types_by_citation or {}

    evidence: list[CitationEvidence] = []
    for citation in citations:
        source = source_by_id.get(citation.source_document_id)
        if source is None:
            continue
        evidence.append(
            CitationEvidence(
                citation_id=citation.citation_id,
                asset_ticker=asset_ticker,
                source_document_id=source.source_document_id,
                source_type=source.source_type,
                freshness_state=source.freshness_state,
                supported_claim_types=supported_claim_types_by_citation.get(citation.citation_id, []),
                supporting_text=source.supporting_passage,
                is_recent=source.source_type in RECENT_SOURCE_TYPES,
                allowlist_status=getattr(source, "allowlist_status", SourceAllowlistStatus.allowed),
                source_use_policy=getattr(source, "source_use_policy", SourceUsePolicy.full_text_allowed),
                source_identity=getattr(source, "source_identity", None) or getattr(source, "url", None),
                is_official=getattr(source, "is_official", None),
                source_quality=getattr(source, "source_quality", SourceQuality.fixture),
                storage_rights=getattr(source, "storage_rights", SourceStorageRights.raw_snapshot_allowed),
                export_rights=getattr(source, "export_rights", SourceExportRights.excerpts_allowed),
                review_status=getattr(source, "review_status", SourceReviewStatus.approved),
                approval_rationale=getattr(
                    source,
                    "approval_rationale",
                    "Deterministic fixture source passed local source-use policy review.",
                ),
                parser_status=getattr(source, "parser_status", SourceParserStatus.parsed),
                parser_failure_diagnostics=getattr(source, "parser_failure_diagnostics", None),
            )
        )
    return evidence


def _validate_claim(
    claim: CitationValidationClaim,
    evidence_by_id: dict[str, CitationEvidence],
    allowed_assets: set[str],
    context: CitationValidationContext,
) -> CitationValidationResult:
    issues: list[CitationValidationIssue] = []
    citation_ids = [citation_id for citation_id in claim.citation_ids if citation_id.strip()]

    if claim.important and claim.citation_required and not citation_ids:
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.missing_citation,
                claim_id=claim.claim_id,
                message="Important factual claims must include at least one citation.",
            )
        )
        return CitationValidationResult(claim_id=claim.claim_id, status=issues[0].status, issues=issues)

    cited_assets: set[str] = set()
    for citation_id in citation_ids:
        evidence = evidence_by_id.get(citation_id)
        if evidence is None:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.citation_not_found,
                    claim_id=claim.claim_id,
                    citation_id=citation_id,
                    message="Citation ID does not exist in the provided evidence set.",
                )
            )
            continue

        cited_assets.add(_normalize_ticker(evidence.asset_ticker))
        issues.extend(_validate_evidence(claim, evidence, allowed_assets, context))

    required_assets = {_normalize_ticker(ticker) for ticker in claim.required_asset_tickers}
    missing_required_assets = required_assets - cited_assets
    if missing_required_assets:
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.insufficient_evidence,
                claim_id=claim.claim_id,
                message=f"Comparison claim is missing evidence for: {', '.join(sorted(missing_required_assets))}.",
            )
        )

    status = issues[0].status if issues else CitationValidationStatus.valid
    return CitationValidationResult(claim_id=claim.claim_id, status=status, issues=issues)


def _validate_evidence(
    claim: CitationValidationClaim,
    evidence: CitationEvidence,
    allowed_assets: set[str],
    context: CitationValidationContext,
) -> list[CitationValidationIssue]:
    issues: list[CitationValidationIssue] = []
    claim_type = _normalize_claim_type(claim.claim_type)

    if _normalize_ticker(evidence.asset_ticker) not in allowed_assets:
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.wrong_asset,
                claim_id=claim.claim_id,
                citation_id=evidence.citation_id,
                source_document_id=evidence.source_document_id,
                message="Citation belongs to an asset outside the current asset or comparison pack.",
            )
        )

    if evidence.allowlist_status is not SourceAllowlistStatus.allowed:
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.disallowed_source_policy,
                claim_id=claim.claim_id,
                citation_id=evidence.citation_id,
                source_document_id=evidence.source_document_id,
                message="Citation evidence must come from an allowed source-use policy record.",
            )
        )

    if evidence.source_use_policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only, SourceUsePolicy.rejected}:
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.disallowed_source_policy,
                claim_id=claim.claim_id,
                citation_id=evidence.citation_id,
                source_document_id=evidence.source_document_id,
                message=f"Source-use policy '{evidence.source_use_policy.value}' cannot support generated factual claims.",
            )
        )

    handoff = validate_source_handoff(evidence, action=SourcePolicyAction.generated_claim_support)
    if not handoff.allowed:
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.disallowed_source_policy,
                claim_id=claim.claim_id,
                citation_id=evidence.citation_id,
                source_document_id=evidence.source_document_id,
                message="Citation evidence failed Golden Asset Source Handoff: " + ", ".join(handoff.reason_codes),
            )
        )

    if claim_type == "recent" and not _is_recent_source(evidence):
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.non_recent_source,
                claim_id=claim.claim_id,
                citation_id=evidence.citation_id,
                source_document_id=evidence.source_document_id,
                message="Recent-development claims must cite a recent-development source.",
            )
        )

    if evidence.freshness_state is FreshnessState.stale and not _is_labeled_stale(claim, context):
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.stale_source,
                claim_id=claim.claim_id,
                citation_id=evidence.citation_id,
                source_document_id=evidence.source_document_id,
                message="Stale evidence must be labeled stale at the claim or result level.",
            )
        )

    if evidence.freshness_state in {FreshnessState.unknown, FreshnessState.unavailable} and not _has_matching_freshness_label(
        claim, context, evidence.freshness_state
    ):
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.insufficient_evidence,
                claim_id=claim.claim_id,
                citation_id=evidence.citation_id,
                source_document_id=evidence.source_document_id,
                message="Unknown or unavailable source freshness is insufficient unless the result is labeled that way.",
            )
        )

    if not _source_supports_claim_type(evidence, claim_type):
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.unsupported_source,
                claim_id=claim.claim_id,
                citation_id=evidence.citation_id,
                source_document_id=evidence.source_document_id,
                message=f"Source type '{evidence.source_type}' does not support '{claim_type}' claims.",
            )
        )

    if not evidence.supports_claim or not (evidence.supporting_text or "").strip():
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.insufficient_evidence,
                claim_id=claim.claim_id,
                citation_id=evidence.citation_id,
                source_document_id=evidence.source_document_id,
                message="Citation exists but does not provide sufficient supporting evidence for the claim.",
            )
        )

    return issues


def _source_supports_claim_type(evidence: CitationEvidence, claim_type: str) -> bool:
    explicitly_supported = {_normalize_claim_type(item) for item in evidence.supported_claim_types}
    if explicitly_supported:
        return claim_type in explicitly_supported

    source_type = evidence.source_type.strip().lower()
    if evidence.evidence_kind is EvidenceKind.document_chunk:
        source_type = "document_chunk"
    elif evidence.evidence_kind is EvidenceKind.normalized_fact:
        source_type = "normalized_fact"

    return source_type in SOURCE_TYPES_BY_CLAIM_TYPE.get(claim_type, set())


def _is_recent_source(evidence: CitationEvidence) -> bool:
    if evidence.is_recent is not None:
        return evidence.is_recent
    return evidence.source_type.strip().lower() in RECENT_SOURCE_TYPES


def _is_labeled_stale(claim: CitationValidationClaim, context: CitationValidationContext) -> bool:
    return _has_matching_freshness_label(claim, context, FreshnessState.stale)


def _has_matching_freshness_label(
    claim: CitationValidationClaim, context: CitationValidationContext, freshness_state: FreshnessState
) -> bool:
    return claim.freshness_label is freshness_state or context.result_freshness_label is freshness_state


def _normalize_claim_type(claim_type: str) -> str:
    lowered = claim_type.strip().lower()
    return CLAIM_TYPE_ALIASES.get(lowered, lowered)


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def _coerce(model: type[BaseModel], value: Any) -> Any:
    if isinstance(value, model):
        return value
    return model(**value)
