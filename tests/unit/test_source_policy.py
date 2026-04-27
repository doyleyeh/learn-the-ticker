from pathlib import Path

from backend.models import (
    FreshnessState,
    SourceAllowlistStatus,
    SourceExportRights,
    SourceParserStatus,
    SourcePolicyDecisionState,
    SourceQuality,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
)
from backend.source_policy import (
    DEFAULT_SOURCE_ALLOWLIST_PATH,
    REQUIRED_SOURCE_USE_POLICIES,
    SourcePolicyAction,
    classify_source_policy_actions,
    source_handoff_fields_from_policy,
    source_can_cache_input_checksum,
    source_can_export_source_metadata,
    source_can_feed_generated_output_cache,
    source_can_support_markdown_json_export,
    load_source_allowlist,
    resolve_source_policy,
    source_can_export_excerpt,
    source_can_support_generated_output,
    validate_source_handoff,
    validate_source_allowlist,
)
from backend.weekly_news_repository import (
    WeeklyNewsSourceRankTier,
    source_policy_allows_weekly_news_selection,
    source_rank_tier_priority,
)
from tests.unit.test_weekly_news import _repository_candidate


ROOT = Path(__file__).resolve().parents[2]


def test_source_allowlist_loads_required_schema_and_policy_tiers():
    manifest = load_source_allowlist()

    assert DEFAULT_SOURCE_ALLOWLIST_PATH == ROOT / "config" / "source_allowlist.yaml"
    assert manifest.schema_version == "source-allowlist-v1"
    assert manifest.no_live_external_calls is True
    assert {record.source_use_policy for record in manifest.source_records} == REQUIRED_SOURCE_USE_POLICIES
    assert validate_source_allowlist(manifest) == manifest

    required_fields = {
        "source_id",
        "display_name",
        "match_kind",
        "source_type",
        "source_quality",
        "allowlist_status",
        "source_use_policy",
        "permitted_operations",
        "allowed_excerpt",
        "review",
    }
    for record in manifest.source_records:
        assert required_fields <= set(record.model_dump(mode="json"))
        assert record.review.rationale
        assert record.review.reviewed_at


def test_source_policy_resolution_by_domain_fixture_provider_and_unknown():
    sec = resolve_source_policy(url="https://www.sec.gov/Archives/example")
    issuer = resolve_source_policy(url="https://www.investor.vanguard.com/funds")
    recent = resolve_source_policy(source_identifier="local://fixtures/voo/recent-review")
    provider = resolve_source_policy(provider_name="Mock Market Reference")
    rejected = resolve_source_policy(url="https://unlicensed.example/article")
    unknown = resolve_source_policy(url="https://not-allowlisted.example/item")

    assert sec.decision is SourcePolicyDecisionState.allowed
    assert sec.source_use_policy is SourceUsePolicy.full_text_allowed
    assert sec.permitted_operations.can_store_raw_text is True
    assert source_can_support_generated_output(sec) is True

    assert issuer.decision is SourcePolicyDecisionState.allowed
    assert issuer.source_use_policy is SourceUsePolicy.full_text_allowed
    assert issuer.source_quality.value == "issuer"

    assert recent.decision is SourcePolicyDecisionState.allowed
    assert recent.source_use_policy is SourceUsePolicy.summary_allowed
    assert recent.recent_context_only is True
    assert recent.permitted_operations.can_support_canonical_facts is False
    assert source_can_export_excerpt(recent) is True

    assert provider.decision is SourcePolicyDecisionState.allowed
    assert provider.source_use_policy is SourceUsePolicy.metadata_only
    assert provider.permitted_operations.can_cache is True
    assert provider.permitted_operations.can_export_metadata is False
    assert source_can_support_generated_output(provider) is False

    assert rejected.decision is SourcePolicyDecisionState.rejected
    assert rejected.allowlist_status is SourceAllowlistStatus.rejected
    assert rejected.source_use_policy is SourceUsePolicy.rejected
    assert source_can_support_generated_output(rejected) is False

    assert unknown.decision is SourcePolicyDecisionState.not_allowlisted
    assert unknown.allowlist_status is SourceAllowlistStatus.not_allowlisted
    assert unknown.source_use_policy is SourceUsePolicy.rejected
    assert unknown.permitted_operations.can_cache is False


def test_source_policy_config_has_no_live_calls_or_advice_like_language():
    text = DEFAULT_SOURCE_ALLOWLIST_PATH.read_text(encoding="utf-8").lower()

    for forbidden in ["import requests", "import httpx", "urllib", "socket", "api_key", "openai"]:
        assert forbidden not in text
    for forbidden in ["should buy", "should sell", "should hold", "price target", "personalized allocation"]:
        assert forbidden not in text


def test_weekly_news_source_policy_wins_over_rank_and_recency():
    official = _repository_candidate("official", tier=WeeklyNewsSourceRankTier.official_filing, source_rank=1)
    allowlisted = _repository_candidate(
        "allowlisted",
        tier=WeeklyNewsSourceRankTier.allowlisted_news,
        source_rank=20,
    )
    metadata_only = _repository_candidate(
        "metadata_only",
        tier=WeeklyNewsSourceRankTier.official_filing,
        source_rank=1,
        source_use_policy=SourceUsePolicy.metadata_only,
    )
    rejected = _repository_candidate(
        "rejected",
        tier=WeeklyNewsSourceRankTier.official_filing,
        source_rank=1,
        source_use_policy=SourceUsePolicy.rejected,
        allowlist_status=SourceAllowlistStatus.rejected,
    )

    assert source_rank_tier_priority(official.source_rank_tier) < source_rank_tier_priority(allowlisted.source_rank_tier)
    assert source_policy_allows_weekly_news_selection(official) is True
    assert source_policy_allows_weekly_news_selection(allowlisted) is True
    assert source_policy_allows_weekly_news_selection(metadata_only) is False
    assert source_policy_allows_weekly_news_selection(rejected) is False


def test_source_policy_action_contract_covers_all_tiers_and_export_rights():
    full_text = resolve_source_policy(url="https://www.sec.gov/Archives/example")
    summary = resolve_source_policy(source_identifier="local://fixtures/aapl/recent-review/source")
    metadata = resolve_source_policy(provider_name="Mock Market Reference")
    link_only = resolve_source_policy(url="https://link-only.example/story")
    rejected = resolve_source_policy(url="https://unlicensed.example/story")

    decisions_by_policy = {
        decision.source_use_policy: classify_source_policy_actions(decision)
        for decision in [full_text, summary, metadata, link_only, rejected]
    }
    assert set(decisions_by_policy) == REQUIRED_SOURCE_USE_POLICIES

    assert source_can_support_generated_output(full_text) is True
    assert source_can_feed_generated_output_cache(full_text) is True
    assert source_can_export_source_metadata(full_text) is True
    assert source_can_export_excerpt(full_text) is True
    assert source_can_support_markdown_json_export(full_text) is True

    assert source_can_support_generated_output(summary) is True
    assert source_can_feed_generated_output_cache(summary) is True
    assert source_can_export_source_metadata(summary) is True
    assert source_can_export_excerpt(summary) is True
    assert source_can_support_markdown_json_export(summary) is True
    assert summary.canonical_facts_allowed is False
    assert summary.recent_context_only is True

    assert source_can_cache_input_checksum(metadata) is True
    assert source_can_support_generated_output(metadata) is False
    assert source_can_feed_generated_output_cache(metadata) is False
    assert source_can_export_source_metadata(metadata) is False
    assert source_can_export_excerpt(metadata) is False
    assert source_can_support_markdown_json_export(metadata) is False
    assert decisions_by_policy[SourceUsePolicy.metadata_only][
        SourcePolicyAction.generated_claim_support
    ].reason_code == "metadata_only_content_omitted"

    assert source_can_cache_input_checksum(link_only) is True
    assert source_can_support_generated_output(link_only) is False
    assert source_can_feed_generated_output_cache(link_only) is False
    assert source_can_export_source_metadata(link_only) is True
    assert source_can_export_excerpt(link_only) is False
    assert source_can_support_markdown_json_export(link_only) is False
    assert decisions_by_policy[SourceUsePolicy.link_only][
        SourcePolicyAction.allowed_excerpt_export
    ].reason_code == "link_only_content_omitted"

    assert source_can_cache_input_checksum(rejected) is False
    assert source_can_support_generated_output(rejected) is False
    assert source_can_feed_generated_output_cache(rejected) is False
    assert source_can_export_source_metadata(rejected) is False
    assert source_can_export_excerpt(rejected) is False
    assert source_can_support_markdown_json_export(rejected) is False
    assert decisions_by_policy[SourceUsePolicy.rejected][SourcePolicyAction.diagnostics].allowed is True
    assert decisions_by_policy[SourceUsePolicy.rejected][
        SourcePolicyAction.diagnostics
    ].sanitized_diagnostics_only is True


def test_golden_asset_source_handoff_requires_approval_parser_rights_and_freshness_metadata():
    approved = resolve_source_policy(url="https://www.sec.gov/Archives/example")
    source = {
        **source_handoff_fields_from_policy(approved, source_identity="https://www.sec.gov/Archives/example"),
        "source_document_id": "src_sec_fixture",
        "source_type": "sec_filing",
        "is_official": True,
        "source_quality": SourceQuality.official,
        "allowlist_status": approved.allowlist_status,
        "source_use_policy": approved.source_use_policy,
        "permitted_operations": approved.permitted_operations,
        "freshness_state": FreshnessState.fresh,
        "as_of_date": "2026-04-01",
        "retrieved_at": "2026-04-25T00:00:00Z",
    }

    assert validate_source_handoff(source, action=SourcePolicyAction.generated_claim_support).allowed is True

    missing = validate_source_handoff({}, action=SourcePolicyAction.generated_claim_support)
    assert missing.allowed is False
    assert {
        "missing_source_identity",
        "missing_source_type",
        "missing_official_source_status",
        "missing_approval_rationale",
        "review_pending_review",
        "parser_pending_review",
        "storage_rights_unknown",
        "export_rights_unknown",
        "missing_freshness_as_of_metadata",
    } <= set(missing.reason_codes)

    parser_failed = validate_source_handoff(
        {**source, "parser_status": SourceParserStatus.failed, "parser_failure_diagnostics": "fixture parse failed"},
        action=SourcePolicyAction.generated_claim_support,
    )
    assert parser_failed.allowed is False
    assert "parser_failed" in parser_failed.reason_codes

    pending_review = validate_source_handoff(
        {**source, "review_status": SourceReviewStatus.pending_review},
        action=SourcePolicyAction.generated_claim_support,
    )
    assert pending_review.allowed is False
    assert "review_pending_review" in pending_review.reason_codes

    hidden = validate_source_handoff(
        {**source, "source_identity": "private://internal/source", "source_type": "internal_feed"},
        action=SourcePolicyAction.generated_claim_support,
    )
    assert hidden.allowed is False
    assert "hidden_or_internal_source" in hidden.reason_codes

    metadata_only = validate_source_handoff(
        {
            **source,
            "source_use_policy": SourceUsePolicy.metadata_only,
            "storage_rights": SourceStorageRights.metadata_only,
            "export_rights": SourceExportRights.metadata_only,
        },
        action=SourcePolicyAction.generated_claim_support,
    )
    assert metadata_only.allowed is False
    assert "metadata_only_content_omitted" in metadata_only.reason_codes
