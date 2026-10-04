"""Explicit installed Codex inventory evidence; never invokes a cloud model."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from backend.app.codex_models import read_models, select_model
from backend.app.codex_rpc import CodexRPC
from backend.app.codex_runtime import CodexRuntime, subscription_account
from backend.app.runtime_base import AIRuntime, RuntimeFailure, executable_command
from scripts.codex_inventory import capture_inventory
from scripts.qualify_codex import resolve_profile


def executable_fingerprint():
    command = executable_command("codex")
    # This explicit lane qualifies the native Windows executable only.
    if len(command) != 1 or Path(command[0]).suffix.lower() != ".exe":
        raise RuntimeFailure("Inventory attestation requires the installed native Windows Codex executable.")
    with Path(command[0]).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


async def inventory(profile, model):
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": "blocked", "live_qualified": False,
              "cloud_inference_requested": False, "stage": "version", "checks": {}}
    rpc = CodexRPC(profile, profile / "qualification-preflight")
    try:
        discovery = await AIRuntime.check(CodexRuntime(profile))
        if not discovery.installed or discovery.qualification == "unqualified": return report
        report["version"] = discovery.version
        before = executable_fingerprint()
        report["stage"] = "subscription_metadata"
        await rpc.open()
        if not subscription_account(await rpc.request("account/read", {"refreshToken": False})): return report
        selected = select_model(await read_models(rpc), model)
        await rpc.restrict_model(selected)
        rpc.catalog.verify()
        payload = rpc.catalog.path.read_bytes()
        capabilities = await rpc.request("modelProvider/capabilities/read", {})
        await rpc.close()  # Authenticated process is gone before any test listener starts.
        report.update(model=selected, executable_sha256=before, catalog_sha256=hashlib.sha256(payload).hexdigest())
        for browsing in (False, True):
            report["stage"] = "research" if browsing else "cached"
            report["checks"][report["stage"]] = await capture_inventory(payload, selected, capabilities, browsing)
        if executable_fingerprint() != before: raise RuntimeFailure("Codex executable changed during inventory verification.")
        report.update(status="serialized_inventory_verified_review_required", stage="review")
    except (RuntimeFailure, OSError, ValueError, TypeError, TimeoutError):
        report["status"] = "blocked"  # Stage only; never emit raw provider diagnostics.
    finally:
        await rpc.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--model", required=True)
    try:
        args = parser.parse_args()
        report = asyncio.run(inventory(resolve_profile(args.profile), args.model))
        print(json.dumps(report, indent=2))
        return 0 if report["status"] == "serialized_inventory_verified_review_required" else 2
    except KeyboardInterrupt: return 130
    except (RuntimeFailure, OSError, ValueError, TypeError):
        print(json.dumps({"status": "blocked", "stage": "inventory_setup", "cloud_inference_requested": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
