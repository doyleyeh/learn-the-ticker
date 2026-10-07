"""Bounded bilingual Codex learning/conversation check over synthetic saved evidence."""
import argparse
import asyncio
from contextlib import aclosing
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.codex_runtime import CodexRuntime
from backend.app.codex_rpc import CodexRPC
from backend.app.contracts import Claim, EvidenceBundle, ResearchRequest, Settings, TermRequest
from backend.app.db import Database
from backend.app.evidence import factual_context
from backend.app.evidence_reuse import citation_id
from backend.app.runtime_base import AIRuntime, RuntimeFailure
from backend.app.source_operations import shareable_view
from backend.app.terms import TermService, validate_numbers
from scripts.qualify_codex import enforcement_ready, failure_reason, preflight, resolve_profile
from scripts.qualify_saved_questions import candidate_diagnostic
from tests.desktop.market_fixture import market_bundle
from tests.desktop.test_market_research import service as synthetic_service


TERM = "EPS estimate: exact average, USD/share unit, analyst opinion and unknown publication date"
MATRIX = (("en", "beginner"), ("zh-TW", "beginner"), ("en", "intermediate"), ("zh-TW", "intermediate"))
VALUE = "1.25000000000000001"


def account_error_category(error):
    """Exact pinned-runtime labels only; never return arbitrary vendor text."""
    if not isinstance(error, dict) or type(error.get("code")) is not int or error["code"] != -32603:
        return "other"
    message = error.get("message")
    if not isinstance(message, str):
        return "other"
    return {
        "workspace routing discovery timed out": "routing_timeout",
        "workspace routing discovery failed": "routing_failed",
        "workspace routing discovery unauthorized (401)": "routing_unauthorized",
        "configuration changed during workspace routing discovery; retry account/read": "routing_configuration_changed",
        "failed to load workspace requirements": "requirements_load",
        "failed to reload workspace requirements": "requirements_reload",
        "account changed during workspace routing discovery": "account_changed",
    }.get(message, "other")


def rpc_diagnostic(method, response):
    methods = {"initialize", "account/read", "account/rateLimits/read", "model/list", "config/read", "config/requirements/read",
        "experimentalFeature/list", "windowsSandbox/readiness", "thread/start", "turn/start", "turn/interrupt"}
    error = response.get("error") if isinstance(response, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    return {"method": method if method in methods else "other",
        "response": "rpc_error" if error is not None else "invalid_result",
        "code": str(code) if type(code) is int and code in {-32700, -32600, -32601, -32602, -32603, -32000} else "other",
        "category": account_error_category(error) if method == "account/read" else "other"}


def observed_rpc(report):
    class ObservedRPC(CodexRPC):
        async def receive(self):
            value = await super().receive()
            if "id" in value and "method" not in value and ("error" in value or not isinstance(value.get("result"), dict)):
                diagnostic = rpc_diagnostic(getattr(self, "observed_method", "other"), value)
                report.setdefault("first_error", diagnostic)
                report["last_error"] = diagnostic
            return value

        async def request(self, method, params, timeout=None):
            self.observed_method = method
            self.account_reads = 0
            try:
                return await super().request(method, params, timeout)
            except (RuntimeFailure, OSError, TimeoutError) as exc:
                report["failed_request"] = {"method": rpc_diagnostic(method, {})["method"],
                    "diagnostic": failure_reason(exc), "account_read_attempts": self.account_reads}
                raise
            finally:
                if self.account_reads > 1:
                    report["account_read_retries"] = report.get("account_read_retries", 0) + self.account_reads - 1

        async def send(self, message):
            if message.get("method") == "account/read":
                self.account_reads += 1
            await super().send(message)
    return ObservedRPC


def wording_checks(text, language):
    return {
        "exact_value_and_unit": VALUE + " USD/share" in text,
        "requested_language_script": len(re.findall(r"[\u4e00-\u9fff]" if language == "zh-TW" else r"[A-Za-z]", text)) >= 10,
        "opinion_label": bool(re.search(r"opinion|estimate|分析師|預估|估計", text, re.I)),
        "unknown_publication": bool(re.search(r"unknown|not (?:provided|known|available)|未知|不明|未提供|無法確定", text, re.I)),
    }


class ObservedRuntime:
    """Keep production tool policy and usage checks; retain only safe counters."""
    def __init__(self, runtime):
        self.runtime, self.calls, self.tool_events = runtime, 0, 0
        self.diagnostic, self.term_request, self.bundle = "not_started", None, None

    async def stream(self, prompt, run_id, workspace, model=None, *, allow_browsing=True):
        if "UNVERIFIED_MATRIX_NOTE" in prompt:
            raise RuntimeFailure("Unverified notes entered the learning context")
        self.calls += 1
        self.diagnostic = "stream_incomplete"
        output = ""
        try:
            async with aclosing(self.runtime.stream(prompt, run_id, workspace, model, allow_browsing=allow_browsing)) as events:
                async for event in events:
                    if event.kind == "message.delta" and not allow_browsing and len(output) <= 12000:
                        output += event.text
                    if event.kind in ("tool.started", "approval.required"):
                        self.tool_events += 1
                        raise RuntimeFailure("This synthetic saved-context check requires no tool use")
                    yield event
            if not allow_browsing:
                self.diagnostic = candidate_diagnostic(output.strip(), self.term_request, self.bundle)
        except (RuntimeFailure, OSError, TimeoutError) as exc:
            self.diagnostic = failure_reason(exc)
            raise


async def exercise(runtime, workspace, model, *, review=None):
    """Eight turns maximum; stop at terminal failure, never replay inference or switch providers."""
    db = Database("sqlite://", testing=True)
    app, instrument, _, _ = synthetic_service(workspace, enabled=False, database=db)
    tracked = ObservedRuntime(runtime)
    app.adapters = {"codex": tracked}
    if isinstance(runtime, AIRuntime):
        runtime.approvals = app.approvals
    class NoNewFinancials:
        def retrieve(self, *args, **kwargs):
            raise ValueError("This synthetic saved-page check has no new financial retrieval")
    app.financial_adapter = NoNewFinancials()
    def no_fetch(*args, **kwargs):
        raise ValueError("No external source retrieval is part of this synthetic check")
    app.verifier = no_fetch
    original = market_bundle(financials=False, estimates=True)
    original.notes.append(Claim(asset_id=original.asset.id, text="UNVERIFIED_MATRIX_NOTE"))
    payload = original.model_dump(mode="json")
    db.put("bundle:" + original.id, "bundle", payload, original.asset.id)
    db.put("asset:" + original.asset.id, "asset", payload)
    chat = db.create_conversation(original.asset.id, original.id)
    learning = TermService(app)
    terms, cases = [], []
    try:
        for language, level in MATRIX:
            db.put("settings", "settings", Settings(cloud_enabled=True, language=language, model=model).model_dump(mode="json"))
            request = TermRequest(term=TERM, bundle_id=original.id, language=language, level=level, model=model)
            tracked.term_request, tracked.bundle = request, original
            # Repeated passive lookup must never invoke inference.
            before = tracked.calls
            for _ in range(2):
                assert learning.lookup(request)["status"] == "unavailable"
            assert tracked.calls == before
            job = await learning.submit(request)
            await app.tasks[job["id"]]
            result = db.job(job["id"])
            if result["status"] != "completed":
                return {"status": "blocked", "blocker": "term_not_admitted", "diagnostic": tracked.diagnostic, "cases": cases, "calls": tracked.calls}
            term = result["result"]
            checks = wording_checks(term["explanation"], language)
            checks["original_citation"] = original.market.estimates.source_id in term["source_ids"] and term["basis"] == "snapshot"
            checks["language_level"] = (term["language"], term["level"]) == (language, level)
            cases.append({"kind": "term", "language": language, "level": level, "checks": checks})
            if not all(checks.values()):
                return {"status": "blocked", "blocker": "term_acceptance", "cases": cases, "calls": tracked.calls}
            if review:
                review({"kind": "term", "language": language, "level": level, "interpretation": term["explanation"]})
            terms.append((request, term))
            question = ("Explain only the selected fictional saved page's current-quarter EPS consensus. "
                "Quote its exact average with the literal USD/share unit; identify it as an analyst opinion "
                "and say its publication date is unknown. Use one short unverified_note with the original "
                "numerical source ID. Do not browse, retrieve more data or claim latest coverage; this "
                "synthetic educational question is fully answered by the selected page.")
            job = await app.submit(ResearchRequest(query=question, asset_id=instrument.asset.id,
                conversation_id=chat["id"], language=language, level=level, model=model))
            await app.tasks[job["id"]]
            result = db.job(job["id"])
            if result["status"] != "completed" or not result.get("result", {}).get("asset"):
                return {"status": "blocked", "blocker": "conversation_not_admitted", "diagnostic": tracked.diagnostic, "cases": cases, "calls": tracked.calls}
            answer = EvidenceBundle.model_validate(result["result"])
            alias = citation_id(original.id, original.market.estimates.source_id)
            cited = [note for note in answer.notes if alias in note.source_ids]
            interpretation = " ".join(note.text for note in cited)
            checks = wording_checks(interpretation, language)
            try:
                validate_numbers(SimpleNamespace(explanation=interpretation, mode="question", basis="snapshot", term="",
                    source_ids=[original.market.estimates.source_id]), factual_context(original))
                checks["cited_numbers_only"] = True
            except ValueError:
                checks["cited_numbers_only"] = False
            exported, notice = shareable_view(answer)
            checks.update(original_citation=any(ref.id == alias and ref.bundle_id == original.id for ref in answer.context_references),
                language_level=(answer.language, answer.level) == (language, level),
                interpretation_only=bool(cited) and not answer.claims and not factual_context(answer)["claims"],
                private_export_filtered=bool(notice) and not exported.notes and not exported.context_references,
                selected_context=result["request"]["context_bundle_id"] == original.id,
                bounded_interpretation=len(cited) == 1 and len(interpretation) <= 1600,
                original_unchanged=db.get("asset:" + original.asset.id) == payload and db.get("bundle:" + original.id) == payload)
            cases.append({"kind": "conversation", "language": language, "level": level, "checks": checks})
            if not all(checks.values()):
                return {"status": "blocked", "blocker": "conversation_acceptance", "cases": cases, "calls": tracked.calls}
            if review:
                review({"kind": "conversation", "language": language, "level": level, "interpretation": interpretation})
        db.put("settings", "settings", Settings(cloud_enabled=False, provider="claude").model_dump(mode="json"))
        before = tracked.calls
        offline = True
        for request, term in terms:
            offline = ((await learning.submit(request))["result"] == term) and offline
        history = db.get("conversation:" + chat["id"])
        checks = {"all_language_levels": len(cases) == 8, "offline_across_provider_switch": offline and tracked.calls == before,
            "history_preserved": len([message for message in history["messages"] if message["role"] == "assistant"]) == 4,
            "no_tools": tracked.tool_events == 0, "bounded_calls": tracked.calls == 8}
        return {"status": "passed" if all(checks.values()) else "blocked", "blocker": None if all(checks.values()) else "matrix_acceptance",
            "cases": cases, "checks": checks, "calls": tracked.calls}
    finally:
        await app.close()
        db.engine.dispose()


async def check(*, live=False, review=None):
    if not live:
        return {"status": "not_requested", "generation_requested": False}
    profile = resolve_profile(None)
    rpc_report = {}
    report = await preflight(profile, None, rpc_factory=observed_rpc(rpc_report))
    # Keep the same observation through preflight and generation, including
    # recovered errors; a metadata-stage stop must not erase account diagnostics.
    report["rpc_diagnostic"] = rpc_report
    if report["status"] != "preflight_passed":
        return report
    if not await enforcement_ready(profile):
        return {**report, "status": "blocked", "blocker": "sandbox_enforcement", "generation_requested": False}
    with tempfile.TemporaryDirectory(prefix="ltt-bilingual-learning-") as directory:
        with patch("backend.app.codex_runtime.CodexRPC", observed_rpc(rpc_report)):
            result = await exercise(CodexRuntime(profile), Path(directory), report["model"], review=review)
    return {**report, **result, "generation_requested": True, "synthetic_evidence_only": True, "persistent_library_modified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Use at most eight included-usage turns after guarded preflight")
    parser.add_argument("--review-output", type=Path, help="Create a new local file of admitted synthetic interpretations for language review; no raw provider events")
    args = parser.parse_args()
    reviewed = []
    try:
        report = asyncio.run(check(live=args.live, review=reviewed.append if args.review_output else None))
        if args.review_output and reviewed:
            with args.review_output.open("x", encoding="utf-8") as output:
                json.dump(reviewed, output, ensure_ascii=False, indent=2)
    except Exception:
        report = {"status": "blocked", "blocker": "setup_or_validation", "generation_requested": None}
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in ("passed", "not_requested") else 2


if __name__ == "__main__":
    raise SystemExit(main())
