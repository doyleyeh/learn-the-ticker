from dataclasses import replace
from datetime import timedelta

import pytest

from backend.app.contracts import Claim, EvidenceBundle, ResearchRequest, SourcePolicy, now
from backend.app.evidence import admit_bundle, candidate_metadata, verify_candidate
from backend.app.research_cache import reusable
from backend.app.source_registry import SOURCE_RULES, source_rule
from tests.desktop.test_application import IDENTITY, StaticIdentityResolver, source

SEC_FILING_RULE = next(rule for rule in SOURCE_RULES if rule.id == "sec-filings-v1")


@pytest.mark.parametrize("url", [
    "https://www.sec.gov/example", "https://www.sec.gov.evil.example/Archives/edgar/data/1/000000000100000001/a.htm",
    "https://www.sec.gov/files/stock-art.png", "http://www.sec.gov/Archives/edgar/data/1/000000000100000001/a.htm",
    "https://www.sec.gov/Archives/edgar/data/1/000000000100000001/a.htm?url=evil",
    "https://www.sec.gov/Archives/edgar/data/1/000000000100000001/a.htm#fragment",
    "https://www.sec.gov:8443/Archives/edgar/data/1/000000000100000001/a.htm",
    "https://www.sec.gov/Archives/edgar/data/1/000000000100000001/%61.htm",
    "https://www.investor.gov/unknown-rights", "https://127.0.0.1/Archives/edgar/data/1/000000000100000001/a.htm",
])
def test_unregistered_paths_do_not_inherit_domain_rights(url):
    assert source_rule(url) is None
    clean = verify_candidate(source(url=url, verified=True, official=True, policy=SourcePolicy.full_text, excerpt="UNTRUSTED_TEXT", content_hash="fake"),
                             IDENTITY, lambda _: pytest.fail("Unregistered source fetched"))
    assert clean.policy == SourcePolicy.link and not clean.verified and not clean.official
    assert not clean.excerpt and not clean.content_hash and clean.published_at is None


def test_overlapping_rules_fail_closed():
    assert source_rule(str(source().url), [SEC_FILING_RULE, SEC_FILING_RULE]) is None


@pytest.mark.parametrize("url", ["https://user:private@www.sec.gov/a", "https://example.com/a?api_key=private", "https://example.com/a?access-token=private"])
def test_source_credentials_never_enter_candidate_or_identity_contracts(url):
    from backend.app.contracts import IdentityVerification
    with pytest.raises(ValueError, match="credentials|authentication"):
        source(url=url)
    with pytest.raises(ValueError, match="credentials|authentication"):
        IdentityVerification(authority="synthetic", source_url=url, retrieved_at=now(), content_hash="a" * 64, identity_hash="b" * 64)


@pytest.mark.parametrize("policy", [SourcePolicy.link, SourcePolicy.metadata, SourcePolicy.summary, SourcePolicy.rejected])
def test_non_full_text_rules_do_not_cache_raw_text_or_derived_notes(policy):
    rules = [replace(SEC_FILING_RULE, policy=policy)]
    clean = verify_candidate(source(verified=True, policy=SourcePolicy.full_text, excerpt="PRIVATE_TEXT"), IDENTITY,
                             lambda _: pytest.fail("Permission does not cover raw text"), rules=rules)
    assert not clean.excerpt and not clean.verified and clean.policy == policy
    bundle = admit_bundle(IDENTITY, [clean], [Claim(asset_id=IDENTITY.id, text="PRIVATE_TEXT", source_ids=[clean.id])])
    assert not bundle.notes and not bundle.claims


def test_rejected_candidate_cannot_be_promoted_by_a_permissive_rule():
    clean = verify_candidate(source(policy=SourcePolicy.rejected), IDENTITY, lambda _: pytest.fail("Rejected source fetched"))
    assert clean.policy == SourcePolicy.rejected and not clean.excerpt


@pytest.mark.parametrize("cik", ["0000000002", "", "1", "wrong"])
def test_an_issuer_name_mentioned_in_another_filing_is_not_identity_proof(cik):
    asset = IDENTITY.model_copy(update={"identifiers": {"cik": cik}})
    result = verify_candidate(source(), asset, lambda _: pytest.fail("Wrong issuer filing fetched"))
    assert not result.verified


def test_provider_hash_dates_and_publisher_are_discarded_in_manual_or_failure_path():
    candidate = source(verified=True, official=True, policy=SourcePolicy.full_text, excerpt="untrusted", content_hash="fake",
                       publisher="Impersonated issuer", published_at=now().date(), as_of=now().date())
    clean = candidate_metadata(candidate)
    assert not clean.content_hash and not clean.excerpt and not clean.verified
    assert clean.publisher == SEC_FILING_RULE.publisher and clean.as_of is None and clean.published_at is None


def fresh_bundle():
    at = now()
    src = source(verified=True, policy=SourcePolicy.full_text, excerpt="Synthetic Example Company provides services.",
                 content_hash="a" * 64, as_of=at.date(), published_at=at.date(), retrieved_at=at, provenance="structured_adapter")
    claim = Claim(asset_id=IDENTITY.id, kind="fact", text=src.excerpt, source_ids=[src.id], as_of=at.date())
    bundle = EvidenceBundle(asset=IDENTITY, level="beginner", sources=[src], claims=[claim],
                            identity_verification=StaticIdentityResolver().resolve("ALPHA")[0].verification)
    request = ResearchRequest(query="ALPHA", asset_id=IDENTITY.id)
    return bundle, request


def test_exact_fresh_scope_reuses_without_changing_evidence():
    bundle, request = fresh_bundle()
    snapshot = bundle.model_dump_json()
    assert reusable(bundle, request)
    assert bundle.model_dump_json() == snapshot


@pytest.mark.parametrize("field,value", [
    ("language", "zh-TW"), ("level", "intermediate"), ("asset_id", "OTHER:ALPHA"), ("refresh", True),
    ("conversation_id", "chat"), ("query", "latest ALPHA"), ("query", "ALPHA 今天"), ("query", "current market context"),
])
def test_other_scope_or_latest_request_cannot_reuse_a_recent_wrapper(field, value):
    bundle, request = fresh_bundle()
    assert not reusable(bundle, request.model_copy(update={field: value}))


@pytest.mark.parametrize("target,field,value", [
    ("source", "as_of", None), ("source", "as_of", "old"), ("source", "published_at", "old"),
    ("source", "as_of", "future"), ("source", "retrieved_at", "old"), ("source", "retrieved_at", "future"),
    ("source", "verified", False), ("source", "policy", SourcePolicy.link), ("source", "asset_id", "other"),
    ("source", "content_hash", ""), ("bundle", "identity_verification", None), ("bundle", "level", None),
    ("bundle", "state", "stale"), ("bundle", "created_at", "future"), ("bundle", "created_at", "old"),
])
def test_source_dates_identity_and_rights_are_required_for_freshness(target, field, value):
    bundle, request = fresh_bundle()
    if value in ("old", "future"):
        value = now() + timedelta(days=-30 if value == "old" else 1)
        if field in ("as_of", "published_at"):
            value = value.date()
    if target == "source":
        updates = {field: value}
        if field == "as_of" and value is None:
            updates["published_at"] = None
            bundle.claims[0].as_of = None
        bundle.sources[0] = bundle.sources[0].model_copy(update=updates)
    else:
        bundle = bundle.model_copy(update={field: value})
    assert not reusable(bundle, request)


def test_unknown_type_suppresses_type_dependent_facts():
    bundle, _ = fresh_bundle()
    asset = IDENTITY.model_copy(update={"asset_type": "unknown"})
    claims = [bundle.claims[0], bundle.claims[0].model_copy(update={"id": "type-specific", "section": "valuation"})]
    result = admit_bundle(asset, bundle.sources, claims)
    assert len(result.claims) == 1 and len(result.notes) == 1


def test_unsupported_numbers_remain_non_numeric_notes_for_permitted_sources():
    bundle, _ = fresh_bundle()
    claim = bundle.claims[0].model_copy(update={"value": 100, "unit": "USD", "input_claim_ids": ["made-up"]})
    result = admit_bundle(IDENTITY, bundle.sources, [claim])
    assert not result.claims and result.notes[0].value is None and not result.notes[0].input_claim_ids
