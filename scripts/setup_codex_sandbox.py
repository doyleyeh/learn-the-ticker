"""Inspect the dedicated Windows sandbox; --apply explicitly requests OS setup.

Setup may prompt for administrator approval to provision sandbox accounts,
filesystem permissions and firewall rules. It requests no login or inference.
"""
import argparse
import asyncio
import os
import sys

from backend.app.codex_policy import require_execution_sandbox
from backend.app.codex_rpc import CodexRPC
from backend.app.codex_runtime import CodexRuntime
from backend.app.runtime_base import AIRuntime, RuntimeFailure
from scripts.qualify_codex import resolve_profile


async def setup(profile, *, apply=False, rpc_factory=CodexRPC, timeout=600):
    version = await AIRuntime.check(CodexRuntime(profile))
    if not version.installed or version.qualification == "unqualified":
        print("A reviewed Codex runtime is required. No sandbox setup was started.")
        return 2
    rpc = rpc_factory(profile, profile / "sandbox-setup", allow_browsing=False)
    try:
        await rpc.open()
        readiness = await rpc.request("windowsSandbox/readiness", {})
        if readiness.get("status") == "ready":
            print("The dedicated elevated sandbox reports ready. Actual enforcement still requires qualification.")
            return 0
        if readiness.get("status") not in ("notConfigured", "updateRequired"):
            raise RuntimeFailure("Unknown sandbox readiness")
        if not apply:
            print("The dedicated elevated sandbox requires setup. No OS setup, sign-in or inference was requested. Use --apply only after approving the documented system changes.")
            return 2
        print("Starting provider-managed elevated sandbox setup. Review the Windows administrator prompt. No weaker-mode fallback, login or inference is requested.")
        # No cwd means no project write roots are provisioned (pinned protocol).
        result = await rpc.request("windowsSandbox/setupStart", {"mode": "elevated"})
        if result.get("started") is not True:
            raise RuntimeFailure("Sandbox setup was not acknowledged")
        async with asyncio.timeout(timeout):
            while True:
                message = await rpc.event()
                if "id" in message:
                    raise RuntimeFailure("Unexpected setup access request")
                if message.get("method") == "windowsSandbox/setupCompleted":
                    params = message.get("params")
                    if not isinstance(params, dict) or params.get("mode") != "elevated" or params.get("success") is not True:
                        raise RuntimeFailure("Sandbox setup did not succeed")
                    break
        await rpc.close()
        # Reopen to verify the provider-persisted minimal config and readiness.
        await rpc.open()
        await require_execution_sandbox(rpc)
        print("Dedicated elevated sandbox setup and reconnect checks passed. No inference was requested; live enforcement qualification remains required.")
        return 0
    except (RuntimeFailure, OSError, ValueError, TypeError, TimeoutError):
        print("Sandbox setup or verification failed. No retry or weaker fallback was attempted. Any completed OS provisioning was preserved; inspect readiness before another attempt.")
        return 2
    finally:
        await rpc.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help="Dedicated app-owned profile; never the developer profile")
    parser.add_argument("--apply", action="store_true", help="Authorize provider-managed Windows accounts, filesystem and firewall setup")
    args = parser.parse_args()
    if os.name != "nt":
        print("This setup helper supports native Windows only.")
        return 2
    if args.apply and (not sys.stdin.isatty() or not sys.stdout.isatty()):
        print("Run --apply in an interactive terminal to review administrator prompts.")
        return 2
    try:
        return asyncio.run(setup(resolve_profile(args.profile), apply=args.apply))
    except KeyboardInterrupt:
        print("Setup interrupted. Completed OS provisioning was preserved; inspect readiness before retrying.")
        return 2
    except (RuntimeFailure, OSError, ValueError, TypeError):
        print("The dedicated runtime or profile could not be verified. No inference was requested.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
