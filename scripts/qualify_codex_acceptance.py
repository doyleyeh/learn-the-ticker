"""Explicit additional live acceptance; default invocation never requests inference."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import secrets
import tempfile
from unittest.mock import patch
from urllib.parse import urlsplit

import httpx

from backend.app.api import create_app
from backend.app.codex_rpc import CodexRPC
from backend.app.contracts import ResearchRequest
from backend.app.db import Database
from backend.app.evidence import fetch_public_text, normalize
from backend.app.runtime_base import RuntimeFailure
from scripts.qualify_codex import (ProbeRuntime, collect, enforcement_ready,
    failure_reason, observed_rpc, preflight, resolve_profile)


def source_candidate(text):
    candidate = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
    if not isinstance(candidate, dict) or set(candidate) != {"url", "quote"}:
        raise RuntimeFailure("Source capture format failed")
    url, quote = candidate["url"], candidate["quote"]
    if not isinstance(url, str) or not isinstance(quote, str) or not 20 <= len(quote.strip()) <= 200 or len(quote) > 200:
        raise RuntimeFailure("Source capture format failed")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "www.investor.gov" or parsed.port not in (None, 443)
            or parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.path):
        raise RuntimeFailure("Source capture URL failed")
    return url, quote


async def source_probe(runtime, workspace, model, *, fetcher=fetch_public_text):
    text, progress = await collect(runtime,
        'Use hosted web search to find an official Investor.gov page explaining stocks. Return only JSON with '
        'exactly "url" (the original HTTPS URL without a fragment or query) and "quote" (one exact 20-200 character '
        'sentence from that page defining stocks). Do not use shell, filesystem, MCP or computer tools.',
        workspace, model, browsing=True)
    url, quote = source_candidate(text)
    if progress < 1: raise RuntimeFailure("Source search was not observed")
    fetched = await asyncio.to_thread(fetcher, url)
    supported = normalize(quote) in normalize(fetched)
    if not supported: raise RuntimeFailure("Source quotation was not independently supported")
    # Fingerprint only: no provider text, source body or URL is persisted.
    return {"search_observed": True, "official_url_validated": True,
            "quote_independently_supported": supported,
            "document_sha256": hashlib.sha256(fetched.encode()).hexdigest()}


async def service_probe(profile, workspace, model, version, *, disconnect=False, rpc_base=CodexRPC):
    """Real provider lifecycle through app service/API; isolated in-memory test library."""
    started, instances = asyncio.Event(), []

    class NoAssetLookup:
        # This synthetic lifecycle request has no asset. It cannot certify or
        # publish identity evidence, and must not contact public registries.
        def resolve(self, query):
            return []

    class TrackingRPC(rpc_base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.turns = 0
            self.interrupt_ack = False
            instances.append(self)

        async def request(self, method, params, **kwargs):
            result = await super().request(method, params, **kwargs)
            if method == "turn/start":
                self.turns += 1
                started.set()
            if method == "turn/interrupt": self.interrupt_ack = True
            return result

    db = Database("sqlite://", testing=True)
    token = secrets.token_urlsafe(48)
    runtime = ProbeRuntime(profile, version)
    app = create_app(db, token, workspace, adapters={"codex": runtime}, identity_resolver=NoAssetLookup())
    service = app.state.service
    db.put("settings", "settings", {"cloud_enabled": True, "provider": "codex", "model": model})
    waiter = None
    try:
        with patch("backend.app.codex_runtime.CodexRPC", TrackingRPC):
            async with asyncio.timeout(60):
                job = await service.submit(ResearchRequest(query="Explain the meaning of revenue in general. Use no tools. This is a synthetic lifecycle test."))
                task = service.tasks[job["id"]]
                waiter = asyncio.create_task(started.wait())
                done, _ = await asyncio.wait((task, waiter), timeout=45, return_when=asyncio.FIRST_COMPLETED)
                if waiter not in done or task.done():
                    raise RuntimeFailure("Active provider lifecycle could not be exercised")
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver",
                        headers={"Authorization": "Bearer " + token}) as client:
                    if disconnect:
                        # Stop only the process tree owned by this probe, never by name/PID discovery.
                        await instances[0].close()
                    else:
                        result = await client.put("/api/settings", json={"cloud_enabled": False, "provider": "codex", "model": model})
                        if result.status_code != 200: raise RuntimeFailure("Consent revocation failed")
                    await asyncio.gather(task, return_exceptions=True)
                    # Reading the resulting job must not replay inference.
                    for _ in range(2):
                        response = await client.get("/api/jobs/" + job["id"])
                        if response.status_code != 200: raise RuntimeFailure("Job state read failed")
                result = db.job(job["id"])
                checks = {
                    "terminal_state_correct": result["status"] == ("failed" if disconnect else "cancelled"),
                    "owned_process_closed": bool(instances) and all(item.process is None for item in instances),
                    "single_turn_no_replay": sum(item.turns for item in instances) == 1,
                    "no_research_published": not db.list("asset") and not db.list("bundle"),
                    "no_raw_message_events": all(item["kind"] != "message.delta" for item in db.events(job["id"])),
                    "no_pending_access": not service.approvals.snapshot(),
                    "selected_model_retained": service.settings().model == model,
                }
                if not disconnect:
                    checks["cloud_consent_disabled"] = not service.settings().cloud_enabled
                    checks["interrupt_acknowledged"] = any(item.interrupt_ack for item in instances)
                if not all(checks.values()): raise RuntimeFailure("Provider lifecycle acceptance failed")
                return checks
    finally:
        if waiter:
            waiter.cancel()
            await asyncio.gather(waiter, return_exceptions=True)
        await service.close()
        await app.state.codex_login.close()
        db.engine.dispose()


async def acceptance(profile, report):
    if report["status"] != "preflight_passed": return report
    try:
        if not await enforcement_ready(profile): raise RuntimeFailure("Sandbox enforcement failed")
    except (RuntimeFailure, OSError, ValueError, TypeError, TimeoutError):
        return {**report, "status": "blocked", "blocker": "sandbox_enforcement", "generation_requested": False}
    report = {**report, "checks": {}, "observations": {}, "status": "running", "generation_requested": True}
    runtime = ProbeRuntime(profile, report["version"])
    with tempfile.TemporaryDirectory(prefix="ltt-codex-acceptance-") as directory:
        root = Path(directory)
        try:
            report["stage"] = "source"
            with patch("backend.app.codex_runtime.CodexRPC", observed_rpc(report["observations"])):
                report["checks"]["source"] = await source_probe(runtime, root / "source", report["model"])
            report["stage"] = "consent"
            report["checks"]["consent"] = await service_probe(profile, root / "consent", report["model"], report["version"])
            report["stage"] = "disconnect"
            report["checks"]["disconnect"] = await service_probe(profile, root / "disconnect", report["model"], report["version"], disconnect=True)
            report.update(status="probes_finished_review_required", stage="review", blocker="manual_live_acceptance_review")
        except (RuntimeFailure, OSError, ValueError, TypeError, TimeoutError) as error:
            report.update(status="blocked", blocker="acceptance_probe_failed", failure_reason=failure_reason(error))
    return report


async def run(args):
    profile = resolve_profile(args.profile)
    report = await preflight(profile, args.model)
    if args.live: report = await acceptance(profile, report)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "preflight_passed" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--model")
    parser.add_argument("--live", action="store_true", help="Explicitly request source/consent/disconnect subscription probes")
    try:
        return asyncio.run(run(parser.parse_args()))
    except KeyboardInterrupt:
        print(json.dumps({"status": "cancelled", "live_qualified": False, "generation_requested": None}))
        return 130
    except (RuntimeFailure, OSError, ValueError, TypeError):
        print(json.dumps({"status": "blocked", "blocker": "acceptance_setup_or_cleanup", "live_qualified": False, "generation_requested": None}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
