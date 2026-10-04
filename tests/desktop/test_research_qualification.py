import asyncio
import json

import pytest

from backend.app.contracts import Claim
from scripts.qualify_research import admission_counts, assess, check, page_key, record_navigation
from tests.desktop.test_sec_filings import AT, dated_bundle


def supported_bundle():
    bundle = dated_bundle()
    bundle.claims.append(Claim(asset_id=bundle.asset.id, kind="fact", text="SYNTHETIC COMPANY reported a material event.", source_ids=["event"]))
    bundle.notes.append(Claim(asset_id=bundle.asset.id, section="freshness", text="No current news was verified."))
    return bundle


def test_default_online_qualification_does_not_open_provider_or_sources(monkeypatch):
    monkeypatch.setattr("scripts.qualify_research.resolve_profile", lambda *a: pytest.fail("Explicit live flag required"))
    assert asyncio.run(check())["status"] == "not_run"


@pytest.mark.parametrize("actions", [[], ["search"], ["search", "other", "search"], ["search", "openPage"], ["search", "openPage", "findInPage"], ["openPage", "openPage"]])
def test_search_or_quotation_without_observed_followup_cannot_qualify(actions):
    assert assess(supported_bundle(), actions)["status"] == "blocked"


def test_qualification_requires_source_support_numeric_evidence_and_freshness_disclosure(monkeypatch):
    monkeypatch.setattr("scripts.qualify_research.now", lambda: AT)
    bundle = supported_bundle()
    pages = {page_key(bundle.sources[-1].url): [bundle.sources[-1].excerpt.casefold()]}
    report = assess(bundle, ["search", "openPage", "search"], pages)
    assert report["status"] == "passed" and report["dated_claim_count"] == 1
    assert "9007199254740993" not in json.dumps(report) and "material event" not in json.dumps(report)
    bundle.claims.clear()
    assert assess(bundle, ["search", "openPage", "search"], pages)["status"] == "blocked"
    bundle = supported_bundle()
    bundle.financials = None
    assert assess(bundle, ["search", "openPage", "search"], pages)["status"] == "blocked"
    bundle = supported_bundle()
    bundle.notes.clear()
    assert assess(bundle, ["search", "openPage", "search"], pages)["status"] == "blocked"


@pytest.mark.parametrize("url,text,kind", [
    ("https://different.example/", "SYNTHETIC COMPANY reported a material event.", "openPage"),
    (None, "Retrieval failed", "openPage"),
    (None, "SYNTHETIC COMPANY reported a material event.", "search"),
])
def test_wrong_page_failed_open_or_search_snippet_cannot_prove_page_reading(url, text, kind):
    bundle = supported_bundle()
    actions, pages = [], {}
    record_navigation({"action": {"type": kind, "url": url or str(bundle.sources[-1].url)}, "results": [{"text": text}]}, actions, pages)
    assert not assess(bundle, ["search", "openPage", "search"], pages)["checks"]["cited_page_result_support"]


def test_navigation_retains_bounded_support_only_in_memory():
    bundle = supported_bundle()
    actions, pages = [], {}
    record_navigation({"action": {"type": "openPage", "url": str(bundle.sources[-1].url)},
                       "results": [{"text": bundle.sources[-1].excerpt}]}, actions, pages)
    report = assess(bundle, ["search", *actions, "search"], pages)
    assert report["checks"]["cited_page_result_support"]
    assert "material event" not in json.dumps(report)
    record_navigation({"action": {"type": "openPage", "url": str(bundle.sources[-1].url)}, "results": ["x" * 300_000]}, actions, pages)
    assert sum(map(len, pages[page_key(bundle.sources[-1].url)])) == 200_000


def test_admission_diagnosis_retains_only_aggregate_counts():
    bundle = supported_bundle()
    claims = [*bundle.claims, Claim(asset_id=bundle.asset.id, text="PRIVATE proposed explanation", section="weekly_news", value="1234567")]
    counts = admission_counts(bundle.sources, claims, bundle)
    assert counts == {"candidate_claims": 2, "admitted_claims": 1, "retained_notes": 1,
                      "candidate_facts": 1, "candidate_numeric_fields": 1, "deferred_report_sections": 1,
                      "facts_citing_verified_pages": 1, "literal_verified_support": 1}
    assert all(isinstance(value, int) for value in counts.values())
    assert "PRIVATE" not in json.dumps(counts) and "1234567" not in json.dumps(counts)
