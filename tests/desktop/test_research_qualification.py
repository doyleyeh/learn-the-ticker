import asyncio
import json

import pytest

from backend.app.contracts import Claim
from scripts.qualify_research import admission_counts, assess, check, record_navigation
from tests.desktop.test_sec_filings import AT, dated_bundle


def supported_bundle():
    bundle = dated_bundle()
    bundle.claims.append(Claim(asset_id=bundle.asset.id, kind="fact", text="SYNTHETIC COMPANY reported a material event.", source_ids=["event"]))
    bundle.notes.append(Claim(asset_id=bundle.asset.id, section="freshness", text="No current news was verified."))
    return bundle


def observed_navigation(bundle, results=None, url=None):
    actions, pages = ["search"], {}
    record_navigation({"action": {"type": "openPage", "url": url or str(bundle.sources[-1].url)}, "results": results}, actions, pages)
    record_navigation({"action": {"type": "search"}}, actions, pages)
    return actions, pages


def test_default_online_qualification_does_not_open_provider_or_sources(monkeypatch):
    monkeypatch.setattr("scripts.qualify_research.resolve_profile", lambda *a: pytest.fail("Explicit live flag required"))
    assert asyncio.run(check())["status"] == "not_run"


@pytest.mark.parametrize("actions", [[], ["search"], ["search", "other", "search"], ["search", "openPage"], ["search", "openPage", "findInPage"], ["openPage", "openPage"]])
def test_search_or_quotation_without_observed_followup_cannot_qualify(actions):
    assert assess(supported_bundle(), actions)["status"] == "blocked"


def test_qualification_requires_source_support_numeric_evidence_and_freshness_disclosure(monkeypatch):
    monkeypatch.setattr("scripts.qualify_research.now", lambda: AT)
    bundle = supported_bundle()
    actions, pages = observed_navigation(bundle)
    report = assess(bundle, actions, pages)
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


@pytest.mark.parametrize("url,results", [
    ("https://different.example/", None),
    (None, [{"error": "PRIVATE retrieval failure"}]),
    (None, [{"status": "failed"}]),
    ("not-an-absolute-url", None),
    ("https://user:private@example.com/", None),
    ("https://example.com/?token=PRIVATE", None),
])
def test_wrong_or_explicitly_failed_navigation_cannot_meet_cited_navigation_gate(url, results):
    bundle = supported_bundle()
    actions, pages = observed_navigation(bundle, results, url)
    report = assess(bundle, actions, pages)
    assert not report["checks"]["cited_source_navigation_observed"]
    assert "PRIVATE" not in json.dumps(report)


def test_opaque_metadata_is_not_mistaken_for_model_visible_body():
    bundle = supported_bundle()
    actions, pages = observed_navigation(bundle, [{"url": str(bundle.sources[-1].url), "title": "PRIVATE title", "text": "NOT THE MODEL BODY"}])
    report = assess(bundle, actions, pages)
    assert report["status"] == "passed" and report["returned_url_references"] == 1
    assert "model-visible" in report["page_body_visibility"]
    assert "material event" not in json.dumps(report)
    assert "PRIVATE" not in str(pages) and "NOT THE MODEL BODY" not in str(pages)
    bundle.claims[0].text = "Unsupported paraphrase"
    assert not assess(bundle, actions, pages)["checks"]["independent_dated_claim_support"]


def test_snippets_without_open_and_unbounded_metadata_do_not_establish_navigation():
    bundle = supported_bundle()
    actions, pages = [], {}
    for _ in range(150):
        record_navigation({"action": {"type": "search"}, "results": [{"url": str(bundle.sources[-1].url), "text": "PRIVATE" * 100000}]}, actions, pages)
    assert len(actions) == len(pages) == 100
    assert not assess(bundle, actions, pages)["checks"]["page_navigation_observed"]
    assert all(len(row["returned_urls"]) <= 100 for row in pages.values())
    assert "PRIVATE" not in str(pages)


def test_admission_diagnosis_retains_only_aggregate_counts():
    bundle = supported_bundle()
    claims = [*bundle.claims, Claim(asset_id=bundle.asset.id, text="PRIVATE proposed explanation", section="weekly_news", value="1234567")]
    counts = admission_counts(bundle.sources, claims, bundle)
    assert counts == {"candidate_claims": 2, "admitted_claims": 1, "retained_notes": 1,
                      "candidate_facts": 1, "candidate_numeric_fields": 1, "deferred_report_sections": 1,
                      "facts_citing_verified_pages": 1, "literal_verified_support": 1}
    assert all(isinstance(value, int) for value in counts.values())
    assert "PRIVATE" not in json.dumps(counts) and "1234567" not in json.dumps(counts)
