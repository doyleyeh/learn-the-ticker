"""Inspect the supplemental Windows offline-account loopback guard (elevated).

--apply / --remove require an elevated interactive terminal. The two persistent
filters affect CodexSandboxOffline across native profiles (Codex shares it), not
the signed-in Windows user, online sandbox account or WSL. No sign-in/inference.
"""
import argparse
import asyncio
import ctypes
import json
import os
import sys

from backend.app.codex_runtime import CodexRuntime
from backend.app.runtime_base import AIRuntime, RuntimeFailure
from scripts.qualify_codex import resolve_profile
from scripts.windows_codex_filter import GuardError, NativeStore, manage


async def reviewed_runtime():
    runtime = await AIRuntime.check(CodexRuntime(resolve_profile(None)))
    return runtime.installed and runtime.version == "0.158.0-alpha.2.1" and runtime.qualification != "unqualified"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--apply", action="store_true")
    actions.add_argument("--remove", action="store_true")
    args = parser.parse_args(argv)
    action = "apply" if args.apply else "remove" if args.remove else "inspect"
    report = {"status": "blocked", "action": action, "generation_requested": False}
    try:
        if os.name != "nt":
            raise GuardError("Native Windows is required.")
        if action != "inspect" and (not sys.stdin.isatty() or not ctypes.windll.shell32.IsUserAnAdmin()):
            raise GuardError("Run this explicit action in an elevated interactive terminal.")
        # Removal needs no runtime version; its exact local account must still
        # exist and match the owned filter objects. Identity drift fails closed.
        if action == "apply" and not asyncio.run(reviewed_runtime()):
            raise GuardError("The exact reviewed Codex runtime is required; nothing was installed.")
        with NativeStore() as store:
            report["status"] = manage(store, action)
    except GuardError as error:
        report["reason"] = str(error)
    except (OSError, ValueError, RuntimeFailure, KeyboardInterrupt):
        report["reason"] = "The guard operation failed or was cancelled; inspect before retrying."
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == ("absent" if action == "remove" else "installed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
