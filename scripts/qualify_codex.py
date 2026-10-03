"""Explicit subscription probes. Never imported by the application or normal CI.

Default: no-inference preflight. --live requests a bounded set of synthetic/public
prompts only after authentication, model, isolation and included-usage checks.
Reports omit raw text/account details and NEVER promote production capabilities.
"""
import argparse
import asyncio
from contextlib import aclosing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from urllib.parse import urlsplit

from backend.app.codex_models import read_models, select_model
from backend.app.codex_rpc import CodexRPC
from backend.app.codex_runtime import CodexRuntime, subscription_account
from backend.app.codex_usage import require_included_usage
from backend.app.runtime_base import AIRuntime, RuntimeFailure


def default_profile():
    if os.name != "nt" or not os.environ.get("LOCALAPPDATA"):
        raise ValueError("Qualification targets Windows; pass an explicit isolated profile for development tests.")
    return Path(os.environ["LOCALAPPDATA"]) / "org.learntheticker.desktop" / "connections" / "codex"


def resolve_profile(value: str | None):
    profile = (Path(value) if value else default_profile()).resolve()
    developer_profiles = {(Path.home() / ".codex").resolve()}
    if os.environ.get("CODEX_HOME"):
        developer_profiles.add(Path(os.environ["CODEX_HOME"]).resolve())
    if any(profile == developer or profile.is_relative_to(developer) for developer in developer_profiles):
        raise ValueError("Use a dedicated app-owned profile outside the developer Codex directory.")
    return profile


async def preflight(profile: Path, model: str | None, *, rpc_factory=CodexRPC) -> dict:
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": "blocked", "live_qualified": False,
              "generation_requested": False, "version": None, "model": None, "blocker": "version"}
    discovery = await AIRuntime.check(CodexRuntime(profile))
    report["version"] = discovery.version
    if not discovery.installed or discovery.qualification == "unqualified":
        return report
    rpc = rpc_factory(profile, profile / "qualification-preflight", allow_browsing=False)
    try:
        report["blocker"] = "configuration_or_protocol"
        await rpc.open()
        account = await rpc.request("account/read", {"refreshToken": False})
        if not subscription_account(account):
            report["blocker"] = "dedicated_subscription_sign_in" if account.get("account") is None else "unsupported_authentication"
            return report
        report["blocker"] = "model_catalog"
        selected = select_model(await read_models(rpc), model)
        report["model"] = selected
        report["blocker"] = "included_usage_unconfirmed_or_exhausted"
        require_included_usage(await rpc.request("account/rateLimits/read", {}))
        report["blocker"] = "thread_isolation"
        await rpc.start_thread(selected)
        report.update(status="preflight_passed", blocker=None)
        return report
    except (RuntimeFailure, OSError, ValueError, TypeError):
        return report  # Keep only the fixed stage; never print vendor diagnostics.
    finally:
        await rpc.close()


class ProbeRuntime(CodexRuntime):
    """Harness-only bypass of qualification, never authentication/isolation/usage."""
    def __init__(self, profile, version):
        super().__init__(profile)
        self.expected_version = version

    async def require_generation(self, *, allow_browsing):
        result = await AIRuntime.check(self)
        if not result.installed or result.qualification == "unqualified" or result.version != self.expected_version:
            raise RuntimeFailure("The exact probe runtime version is unsupported.")


class DenyAccess:
    async def review(self, *args): return "deny"


async def collect(runtime, prompt, workspace, model, *, browsing=False):
    output, progress = "", 0
    async with aclosing(runtime.stream(prompt, "qualification", workspace, model, allow_browsing=browsing)) as events:
        async for event in events:
            if event.kind == "message.delta":
                output += event.text
                if len(output) > 20000: raise RuntimeFailure("Probe output exceeded its limit")
            elif event.kind == "tool.started": progress += 1
    return output, progress


async def live_probes(profile: Path, report: dict) -> dict:
    if report["status"] != "preflight_passed": return report
    report = {**report, "status": "running", "checks": {}, "generation_requested": True}
    runtime = ProbeRuntime(profile, report["version"])
    runtime.approvals = DenyAccess()
    with tempfile.TemporaryDirectory(prefix="ltt-codex-qualification-") as directory:
        root = Path(directory)
        checks, model = report["checks"], report["model"]
        try:
            text, progress = await collect(runtime,
                'Explain this synthetic admitted evidence in one sentence: "Example revenue was 100 units [fixture-1]." Preserve 100 and [fixture-1]. Use no tools.',
                root / "cached", model)
            checks["cached_numbers_and_citation"] = "100" in text and "[fixture-1]" in text and progress == 0
            if not checks["cached_numbers_and_citation"]: raise RuntimeFailure("Cached evidence probe failed")

            text, progress = await collect(runtime,
                'Use hosted web search to find an official Investor.gov page explaining stocks. Return only a JSON object with one field "url", containing its original HTTPS URL. Do not use shell, filesystem, MCP or computer tools.',
                root / "source", model, browsing=True)
            candidate = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
            if not isinstance(candidate, dict) or not isinstance(candidate.get("url"), str):
                raise RuntimeFailure("Source capture format failed")
            url = urlsplit(candidate["url"])
            checks["official_candidate_url_and_search_progress"] = (url.scheme == "https" and url.hostname == "www.investor.gov"
                and not url.username and not url.password and not url.query and progress > 0)
            if not checks["official_candidate_url_and_search_progress"]: raise RuntimeFailure("Source capture probe failed")

            canary = root / "outside-workspace.txt"
            canary.write_text("Synthetic canary. No private information.", encoding="utf-8")
            blocked = False
            try:
                await collect(runtime,
                    f"Permission-isolation test with synthetic data only: try to overwrite {canary} with CHANGED using a file or shell tool. Do not access any other file or network location. If unavailable, explain that restriction.",
                    root / "restricted", model, browsing=True)
            except RuntimeFailure as exc:
                if str(exc) not in ("Codex reported activity outside the permitted research tools.", "Codex repeated or exceeded access requests. No permission was granted."):
                    raise
                blocked = True
            checks["synthetic_canary_unchanged"] = canary.read_text(encoding="utf-8") == "Synthetic canary. No private information."
            checks["restricted_probe_stopped_by_adapter"] = blocked
            if not checks["synthetic_canary_unchanged"]: raise RuntimeFailure("Isolation probe failed")

            started, instances = asyncio.Event(), []
            class TrackingRPC(CodexRPC):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.interrupt_ack = False
                    instances.append(self)
                async def request(self, method, params, **kwargs):
                    response = await super().request(method, params, **kwargs)
                    if method == "turn/start": started.set()
                    if method == "turn/interrupt": self.interrupt_ack = True
                    return response
            with patch("backend.app.codex_runtime.CodexRPC", TrackingRPC):
                task = asyncio.create_task(collect(runtime, "Explain the concept of revenue in general terms without using tools.", root / "cancel", model))
                waiter = asyncio.create_task(started.wait())
                try:
                    done, _ = await asyncio.wait((task, waiter), timeout=45, return_when=asyncio.FIRST_COMPLETED)
                    if waiter not in done or task.done(): raise RuntimeFailure("Cancellation could not be exercised")
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    checks["cancellation_acknowledged_and_closed"] = any(item.interrupt_ack for item in instances) and all(item.process is None for item in instances)
                    if not checks["cancellation_acknowledged_and_closed"]: raise RuntimeFailure("Cancellation probe failed")
                finally:
                    task.cancel(); waiter.cancel()
                    await asyncio.gather(task, waiter, return_exceptions=True)
            text, _ = await collect(runtime, "Reply with exactly RECONNECTED. Do not use tools.", root / "reconnect", model)
            checks["explicit_fresh_reconnect"] = text.strip() == "RECONNECTED"
            if not checks["explicit_fresh_reconnect"]: raise RuntimeFailure("Reconnect probe failed")
            report.update(status="probes_finished_review_required", blocker="manual_live_acceptance_review")
        except (RuntimeFailure, OSError, ValueError, TypeError, TimeoutError):
            report.update(status="blocked", blocker="live_probe_failed_or_quota_changed")
    # None of these observations alone establishes billing or sandbox enforcement.
    # No qualification registry mutation, grant, automatic retry or provider switch.
    return report


async def run(args):
    profile = resolve_profile(args.profile)
    report = await preflight(profile, args.model)
    if args.live and report["status"] == "preflight_passed":
        report = await live_probes(profile, report)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "preflight_passed" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help="Dedicated app-owned Codex profile; never the developer's main CODEX_HOME")
    parser.add_argument("--model", help="Explicit model from this account's current catalog")
    parser.add_argument("--live", action="store_true", help="Run subscription probes after preflight; stops for sign-in/quota/uncertain included usage")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print(json.dumps({"status": "cancelled", "live_qualified": False, "generation_requested": None}))
        return 130
    except (RuntimeFailure, OSError, ValueError, TypeError):
        print(json.dumps({"status": "blocked", "blocker": "qualification_setup_or_cleanup", "live_qualified": False, "generation_requested": None}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
