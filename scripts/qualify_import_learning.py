"""Explicit production Codex document-learning check using synthetic material only."""
import argparse
import asyncio
import json
import re
from pathlib import Path
import tempfile

from backend.app.codex_runtime import CodexRuntime
from backend.app.contracts import Settings
from backend.app.db import Database
from backend.app.import_learning import ImportExplanation, ImportLearningRequest, validate_learning
from backend.app.import_learning_service import ImportLearning
from backend.app.import_previews import ImportPreviews
from backend.app.import_storage import ImportStorage, RetainMetadata
from backend.app.research import ResearchService
from backend.app.runtime_base import RuntimeFailure
from scripts.qualify_codex import enforcement_ready, preflight, resolve_profile

SYNTHETIC = b"Topic,Meaning\nRevenue,Sales before costs\nUncertainty,This fictional learning example has no verified financial figures\n"


async def check(*, live=False, profile=None, model=None):
    if not live:
        return {"status": "not_requested", "generation_requested": False, "live_qualified": False}
    profile = resolve_profile(profile)
    report = await preflight(profile, model)
    if report["status"] != "preflight_passed":
        return report
    if not await enforcement_ready(profile):
        return {**report, "status": "blocked", "blocker": "sandbox_enforcement", "generation_requested": False}
    db = Database("sqlite://", testing=True)
    service = None
    try:
        with tempfile.TemporaryDirectory(prefix="ltt-import-learning-check-") as directory:
            service = ResearchService(db, {"codex": CodexRuntime(profile)}, Path(directory))
            db.put("settings", "settings", Settings(cloud_enabled=True, model=report["model"]).model_dump(mode="json"))
            previews = ImportPreviews(service)
            storage = ImportStorage(previews)
            learning = ImportLearning(service, storage)
            preview = await previews.file(SYNTHETIC, "csv", True)
            item = await storage.file(SYNTHETIC, "csv", RetainMetadata(title="Synthetic revenue learning document",
                preview_hash=preview.document.content_hash, storage_and_backup_confirmed=True))
            request = ImportLearningRequest(document_id=item.id, content_hash=item.content_hash, model=report["model"], transmission_confirmed=True)
            results = []
            for language in ("en", "zh-TW"):
                scoped = request.model_copy(update={"language": language})
                job = await learning.submit(scoped)
                await service.tasks[job["id"]]
                completed = db.job(job["id"])
                if completed["status"] != "completed":
                    return {**report, "status": "blocked", "blocker": "explanation_not_admitted", "generation_requested": None,
                            "completed_languages": len(results), "persistent_user_library_modified": False}
                value = ImportExplanation.model_validate(completed["result"])
                validate_learning(value, await storage.view(item.id))
                language_observed = len(re.findall(r"[\u4e00-\u9fff]" if language == "zh-TW" else r"[A-Za-z]", value.explanation)) >= 10
                results.append({"language": language, "language_characters_observed": language_observed,
                    "references": len(value.references), "interpretation_only": value.interpretation and not value.verified})
            db.put("settings", "settings", Settings().model_dump(mode="json"))
            original = (await learning.lookup(request))["result"]
            checks = {"requested_languages_observed": len(results) == 2 and all(row["language_characters_observed"] for row in results), "original_literal_references": all(row["references"] > 0 for row in results),
                      "cached_offline_reuse": original is not None, "no_facts_or_charts": not db.list("asset") and not db.list("bundle"),
                      "no_raw_events": all(row["kind"] != "message.delta" for row in db.events(job["id"]))}
            return {**report, "status": "passed" if all(checks.values()) else "blocked", "blocker": None if all(checks.values()) else "acceptance",
                    "generation_requested": True, "checks": checks, "results": results, "persistent_user_library_modified": False}
    finally:
        if service:
            await service.close()
        db.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Use included subscription usage after guarded preflight; no sign-in or paid fallback")
    parser.add_argument("--profile")
    parser.add_argument("--model")
    args = parser.parse_args()
    try:
        report = asyncio.run(check(live=args.live, profile=args.profile, model=args.model))
    except (ValueError, OSError, RuntimeFailure, TimeoutError):
        report = {"status": "blocked", "blocker": "setup_or_cleanup", "generation_requested": None, "live_qualified": False}
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in ("not_requested", "passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
