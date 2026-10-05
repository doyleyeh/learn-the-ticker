"""Explicit saved-page question check using one scoped subscription turn and synthetic data."""
import argparse
import asyncio
import json
from pathlib import Path
import tempfile

from backend.app.codex_runtime import CodexRuntime
from backend.app.contracts import Settings, TermRequest, TermResult, TermExplanation
from backend.app.db import Database
from backend.app.research import ResearchService
from backend.app.terms import TermService, term_key, validate_explanation
from scripts.qualify_codex import enforcement_ready, preflight, resolve_profile
from tests.desktop.market_fixture import market_bundle


def candidate_diagnostic(output, request, bundle):
    """Return an allowlisted classification, never candidate text or exception data."""
    if output.startswith("```json") and output.endswith("```"):
        output = output[7:-3].strip()
    try:
        result = TermResult.model_validate_json(output)
        explanation = TermExplanation(**result.model_dump(exclude={"schema_version"}), id=term_key(request),
            mode=request.mode, term=request.term, bundle_id=bundle.id, asset_id=bundle.asset.id,
            language=request.language, level=request.level, provider=request.provider, model=request.model)
    except Exception:
        return "response_shape"
    try:
        validate_explanation(explanation, bundle)
    except ValueError as exc:
        return {"Unsubstantiated number in term explanation": "unsupported_number",
            "Explanation cites unavailable or unadmitted evidence": "citation_scope",
            "Explanation basis does not match the learning request": "basis",
            "Explanation must remain educational": "advice"}.get(str(exc), "validation")
    return "valid"


class ObservedRuntime(CodexRuntime):
    diagnostic = "stream_incomplete"

    async def stream(self, *args, **kwargs):
        output = ""
        async for event in super().stream(*args, **kwargs):
            if event.kind == "message.delta" and len(output) <= 12000:
                output += event.text
            yield event
        self.diagnostic = candidate_diagnostic(output.strip(), self.request, self.bundle)


async def check(*, live=False):
    if not live:
        return {"status": "not_requested", "generation_requested": False}
    profile = resolve_profile(None)
    report = await preflight(profile, None)
    if report["status"] != "preflight_passed":
        return report
    if not await enforcement_ready(profile):
        return {**report, "status": "blocked", "blocker": "sandbox_enforcement", "generation_requested": False}
    db = Database("sqlite://", testing=True)
    try:
        with tempfile.TemporaryDirectory(prefix="ltt-saved-question-") as directory:
            bundle = market_bundle(valuations=True)
            payload = bundle.model_dump(mode="json")
            db.put("bundle:" + bundle.id, "bundle", payload, bundle.asset.id)
            db.put("asset:" + bundle.asset.id, "asset", payload)
            db.put("settings", "settings", Settings(cloud_enabled=True, model=report["model"]).model_dump(mode="json"))
            runtime = ObservedRuntime(profile)
            research = ResearchService(db, {"codex": runtime}, Path(directory))
            try:
                service = TermService(research)
                request = TermRequest(mode="question", term="What does the retained trailing P/E of 29.5 mean, and what observation date belongs to it? Explain only this saved page.", bundle_id=bundle.id, model=report["model"])
                runtime.request, runtime.bundle = request, bundle
                job = await service.submit(request)
                await research.tasks[job["id"]]
                result = db.job(job["id"])
                if result["status"] != "completed":
                    return {**report, "status": "blocked", "blocker": "question_not_admitted", "diagnostic": runtime.diagnostic,
                        "generation_requested": True, "persistent_library_modified": False}
                answer = result["result"]
                checks = {"question_snapshot": answer["mode"] == "question" and answer["basis"] == "snapshot",
                    "original_citation": bundle.market.valuations.source_id in answer["source_ids"],
                    "retained_value": "29.5" in answer["explanation"],
                    "original_evidence_unchanged": db.get("bundle:" + bundle.id) == payload and db.get("asset:" + bundle.asset.id) == payload,
                    "interpretation_only": answer["interpretation"],
                    "no_research_job": not db.research_jobs(),
                    "no_tool_or_raw_events": all(row["kind"] not in ("message.delta", "tool.started", "approval.required") for row in db.events(job["id"]))}
                db.put("settings", "settings", Settings().model_dump(mode="json"))
                checks["cached_offline"] = (await service.submit(request))["result"] == answer
                return {**report, "status": "passed" if all(checks.values()) else "blocked", "blocker": None if all(checks.values()) else "acceptance",
                    "generation_requested": True, "synthetic_evidence_only": True, "checks": checks, "persistent_library_modified": False}
            finally:
                await research.close()
    finally:
        db.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Use included subscription usage after deterministic checks and guarded preflight")
    args = parser.parse_args()
    try:
        report = asyncio.run(check(live=args.live))
    except Exception:
        report = {"status": "blocked", "blocker": "setup_or_cleanup", "generation_requested": None}
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in ("not_requested", "passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
