"""Explicit production-path online research check; no persistent user-library writes."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from urllib.parse import urlsplit

from backend.app.codex_rpc import CodexRPC
from backend.app.codex_runtime import CodexRuntime
from backend.app.contracts import EvidenceBundle, ResearchRequest, now
from backend.app.db import Database
from backend.app.evidence import admit_bundle, normalize, validate_claim_sources
from backend.app.research import ResearchService
from backend.app.runtime_base import RuntimeFailure
from scripts.qualify_codex import failure_reason, preflight, resolve_profile


def admission_counts(sources, claims, bundle):
    """Bounded aggregate diagnosis only; never retain candidate text, values or identifiers."""
    by_id = {source.id: source for source in sources}
    return {"candidate_claims": len(claims), "admitted_claims": len(bundle.claims),
        "retained_notes": len(bundle.notes), "candidate_facts": sum(claim.kind == "fact" for claim in claims),
        "candidate_numeric_fields": sum(claim.value is not None for claim in claims),
        "deferred_report_sections": sum(claim.section in ("weekly_news", "earlier_context") for claim in claims),
        "facts_citing_verified_pages": sum(claim.kind == "fact" and any(sid in by_id and by_id[sid].verified for sid in claim.source_ids) for claim in claims),
        "literal_verified_support": sum(any(sid in by_id and by_id[sid].verified
            and normalize(claim.text) in normalize(by_id[sid].excerpt) for sid in claim.source_ids) for claim in claims)}


def page_key(url):
    return hashlib.sha256(str(url).encode()).hexdigest()


def public_reference(value):
    """Only fingerprint plain public HTTPS references; never retain provider text or queries."""
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and parsed.port in (None, 443):
            return page_key(value)
    except ValueError:
        pass
    return None


def record_navigation(item, actions, pages):
    """Completed actions/results are telemetry, not the separately delivered model page body."""
    if len(actions) >= 100:
        return
    action = item.get("action")
    kind = action.get("type") if isinstance(action, dict) else None
    actions.append(kind if kind in ("search", "openPage", "findInPage") else "other")
    key = public_reference(action.get("url")) if kind == "openPage" else None
    observation = {"opened_url": key, "returned_urls": set(), "failure_reported": False}
    pending, visited = [(item.get("results"), 0)], 0
    while pending and visited < 1000:
        value, depth = pending.pop()
        visited += 1
        if isinstance(value, dict):
            # Opaque metadata: only explicit URL fields and structured failure indicators.
            for field in ("url", "source_url"):
                reference = public_reference(value.get(field))
                if reference and len(observation["returned_urls"]) < 100:
                    observation["returned_urls"].add(reference)
            if value.get("error") or value.get("status") in ("error", "failed", "blocked"):
                observation["failure_reported"] = True
        if depth < 8 and isinstance(value, (dict, list)):
            children = list(value.values())[:100] if isinstance(value, dict) else value[:100]
            pending.extend((child, depth + 1) for child in children[:max(0, 1000 - visited - len(pending))])
    pages[len(actions) - 1] = observation


def assess(bundle, actions, pages=None):
    """Separate navigation telemetry from independent source/fact/numeric validation."""
    try:
        bundle = EvidenceBundle.model_validate_json(bundle.model_dump_json())
        validate_claim_sources(bundle)
    except ValueError:
        return {"status": "blocked", "blocker": "invalid_evidence_references"}
    pages = pages or {}
    completed_opens = [index for index, row in pages.items() if row["opened_url"] and not row["failure_reported"]]
    followed_up = any(any(action in ("search", "openPage") and not pages.get(index, {}).get("failure_reported", False)
                         for index, action in enumerate(actions) if index > opened) for opened in completed_opens)
    sources = {source.id: source for source in bundle.sources}
    dated_claims = [claim for claim in bundle.claims if claim.kind == "fact" and claim.value is None and claim.source_ids and all(
        sid in sources and sources[sid].verified and sources[sid].filing_publication is not None for sid in claim.source_ids)
        and any(normalize(claim.text) in normalize(sources[sid].excerpt) for sid in claim.source_ids)]
    cited_urls = {page_key(sources[sid].url) for claim in dated_claims for sid in claim.source_ids}
    navigated_citation = any(pages[index]["opened_url"] in cited_urls for index in completed_opens)
    disclosed = any(note.section == "freshness" for note in bundle.notes) or any(
        source.verified and source.published_at == now().date() for source in bundle.sources)
    checks = {"search_observed": any(action == "search" and not pages.get(index, {}).get("failure_reported", False) for index, action in enumerate(actions)),
              "page_navigation_observed": bool(completed_opens),
              "follow_up_observed": followed_up, "independent_dated_claim_support": bool(dated_claims),
              "cited_source_navigation_observed": navigated_citation,
              "structured_observations_published": bool(bundle.financials and bundle.financials.observations),
              "freshness_or_unavailability_disclosed": disclosed,
              "model_numeric_fields_not_admitted": all(claim.value is None for claim in bundle.claims)}
    return {"status": "passed" if all(checks.values()) else "blocked",
        "blocker": None if all(checks.values()) else "research_acceptance_checks", "checks": checks,
        "web_actions": actions, "structured_observations": len(bundle.financials.observations) if bundle.financials else 0,
        "completed_page_navigations": len(completed_opens),
        "returned_url_references": len({url for row in pages.values() for url in row["returned_urls"]}),
        "reported_retrieval_failures": sum(row["failure_reported"] for row in pages.values()),
        "page_body_visibility": "Event metadata does not expose the complete model-visible page body; factual support is checked independently.",
        "dated_claim_count": len(dated_claims), "sources": [{"url": str(source.url),
            "published_at": source.published_at.isoformat() if source.published_at else None,
            "as_of": source.as_of.isoformat() if source.as_of else None,
            "retrieved_at": source.retrieved_at.isoformat(), "content_hash": source.content_hash,
            "date_index_hash": source.filing_publication.index_hash if source.filing_publication else None}
            for source in bundle.sources if source.verified],
        "scope": "One instrument/current-source research check; no all-provider, chart, native or release qualification."}


async def check(*, live=False, query="", model=None, profile=None):
    if not live:
        return {"status": "not_run", "generation_requested": False, "reason": "Pass --live with an exact identity and qualified model after deterministic checks."}
    profile = resolve_profile(profile)
    report = await preflight(profile, model)
    if report["status"] != "preflight_passed":
        return report
    actions = []
    pages = {}
    counts = {}
    def observed_admission(asset, sources, claims, **kwargs):
        bundle = admit_bundle(asset, sources, claims, **kwargs)
        counts.update(admission_counts(sources, claims, bundle))
        return bundle

    class ObservedRPC(CodexRPC):
        async def receive(self):
            raw = await super().receive()
            params = raw.get("params")
            item = params.get("item") if isinstance(params, dict) else None
            if raw.get("method") == "item/completed" and isinstance(item, dict) and item.get("type") == "webSearch":
                record_navigation(item, actions, pages)
            return raw
    db = Database("sqlite://", testing=True)
    db.put("settings", "settings", {"cloud_enabled": True, "provider": "codex", "model": report["model"]})
    service = None
    try:
        with tempfile.TemporaryDirectory(prefix="ltt-research-qualification-") as directory:
            service = ResearchService(db, {"codex": CodexRuntime(profile)}, Path(directory))
            with patch("backend.app.codex_runtime.CodexRPC", ObservedRPC), patch("backend.app.research.admit_bundle", observed_admission):
                async with asyncio.timeout(480):
                    submitted = await service.submit(ResearchRequest(query=query, model=report["model"]))
                    if "id" not in submitted:
                        return {**report, "status": "blocked", "blocker": "identity_selection", "generation_requested": False}
                    await service.tasks[submitted["id"]]
                    job = db.job(submitted["id"])
                if job["status"] != "completed" or not job.get("result") or "asset" not in job["result"]:
                    return {**report, "status": "blocked", "blocker": "research_did_not_publish", "web_actions": actions,
                            "generation_requested": None, "failure_reason": failure_reason(RuntimeFailure(job.get("error") or "Research scope unresolved"))}
                bundle = EvidenceBundle.model_validate(job["result"])
                return {**report, **assess(bundle, actions, pages), "generation_requested": True,
                        "admission_counts": counts,
                        "persistent_user_library_modified": False}
    except (RuntimeFailure, OSError, ValueError, TypeError, TimeoutError) as exc:
        return {**report, "status": "blocked", "blocker": "online_research_check", "failure_reason": failure_reason(exc),
                "web_actions": actions, "generation_requested": None}
    finally:
        if service:
            await service.close()
        db.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--query", default="")
    parser.add_argument("--model")
    parser.add_argument("--profile")
    args = parser.parse_args()
    try:
        result = asyncio.run(check(live=args.live, query=args.query, model=args.model, profile=args.profile))
    except (ValueError, OSError, RuntimeFailure):
        result = {"status": "blocked", "blocker": "qualification_setup", "generation_requested": False}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
