"""Explicit Gemini inventory or account preflight; consumer setup is retired."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from scripts.connect_gemini import ROOT, login_environment, reviewed_entry


STATUSES = {
    "inventory_verified", "metadata_verified", "quota_exhausted", "invalid_account", "account_validation_required",
    "onboarding_required", "unsupported_tier", "project_unverified", "invalid_quota", "stale_quota",
    "ambiguous_quota", "transport_scope", "account_access_denied", "metadata_transport_failed", "sign_in_required",
    "credential_persistence_failed", "tool_inventory_drift", "tool_policy_drift", "unexpected_failure", "cancelled",
    "timed_out", "invalid_launcher", "file_credentials_present",
    "account_service_unavailable", "account_scope_denied", "project_access_denied",
    "consumer_setup_retired",
}


def validate_report(value):
    if not isinstance(value, dict) or value.get("status") not in STATUSES:
        raise ValueError("Invalid report")
    allowed = {"status", "phase", "generation_qualified", "inference_requested", "credits_enabled", "inventories", "quota_models", "tier", "paid_tier_present", "onboarding"}
    if set(value) - allowed or any(value.get(flag) is not False for flag in ("generation_qualified", "inference_requested", "credits_enabled")):
        raise ValueError("Unsafe report")
    # The child emits allowlisted metadata only; keep output bounded, never dump diagnostics.
    if len(json.dumps(value)) > 32_768:
        raise ValueError("Oversized report")
    if "phase" in value and value["phase"] not in {"runtime_load", "inventory", "authentication", "metadata"}:
        raise ValueError("Invalid phase")
    if "onboarding" in value:
        summary = value["onboarding"]
        if value["status"] != "onboarding_required" or set(summary) != {"default_tier", "free_tier_offered", "user_project_required", "paid_tier_present"}:
            raise ValueError("Invalid onboarding summary")
        if summary["default_tier"] not in {"free-tier", "legacy-tier", "standard-tier", "unknown", "ambiguous", "none"} or type(summary["free_tier_offered"]) is not bool or type(summary["paid_tier_present"]) is not bool:
            raise ValueError("Invalid offered tier")
        if summary["user_project_required"] is not None and type(summary["user_project_required"]) is not bool:
            raise ValueError("Invalid project requirement")
    if "inventories" in value:
        if value["status"] != "inventory_verified" or len(value["inventories"]) != 2:
            raise ValueError("Invalid inventory")
        for index, row in enumerate(value["inventories"]):
            expected = [] if index == 0 else ["google_web_search", "web_fetch"]
            if set(row) != {"browsing", "names", "declarations_sha256", "denied_checks"} or row["browsing"] is not bool(index) or row["names"] != expected:
                raise ValueError("Invalid inventory")
            if row["denied_checks"] != 8 or not re.fullmatch(r"[0-9a-f]{64}", row["declarations_sha256"]):
                raise ValueError("Invalid inventory evidence")
    elif value["status"] == "inventory_verified":
        raise ValueError("Missing inventory")
    if "quota_models" in value:
        if value["status"] not in {"metadata_verified", "quota_exhausted"} or value.get("tier") not in {"free-tier", "legacy-tier", "standard-tier"} or type(value.get("paid_tier_present")) is not bool:
            raise ValueError("Invalid account summary")
        rows = value["quota_models"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 128:
            raise ValueError("Invalid quota rows")
        for row in rows:
            if set(row) != {"model", "remaining_fraction", "reset_at"} or not re.fullmatch(r"gemini-[a-z0-9][a-z0-9.-]{0,78}", row["model"]):
                raise ValueError("Invalid quota model")
            fraction = row["remaining_fraction"]
            if type(fraction) not in (float, int) or not 0 <= fraction <= 1 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z", row["reset_at"]):
                raise ValueError("Invalid quota availability")
    elif value["status"] == "metadata_verified" or "tier" in value or "paid_tier_present" in value:
        raise ValueError("Missing quota")
    return value


def run(mode, profile):
    entry = reviewed_entry()
    node = shutil.which("node")
    if not node:
        raise ValueError("Node unavailable")
    profile.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [node, str(ROOT / "scripts/gemini_preflight.mjs"), mode, str(entry)],
        cwd=profile, env=login_environment(profile), capture_output=True, timeout=85,
    )
    if len(result.stdout) > 32_768:
        raise ValueError("Oversized report")
    report = validate_report(json.loads(result.stdout))
    print(json.dumps(report, separators=(",", ":")))
    return 0 if result.returncode == 0 and report["status"] in {"inventory_verified", "metadata_verified"} else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inventory", action="store_true", help="Inspect isolated tool declarations without auth/network")
    mode.add_argument("--live", action="store_true", help="Read existing account tier/quota; never infer, onboard or sign in")
    mode.add_argument("--complete-free-setup", action="store_true", help="Retired: returns locally without contacting Google")
    args = parser.parse_args(argv)
    try:
        if args.complete_free_setup:
            print('{"status":"consumer_setup_retired","inference_requested":false,"generation_qualified":false,"credits_enabled":false}')
            return 2
        if args.inventory:
            with tempfile.TemporaryDirectory(prefix="ltt-gemini-inventory-") as directory:
                return run("--inventory", Path(directory))
        if os.name != "nt" or not os.environ.get("LOCALAPPDATA"):
            raise ValueError("Windows native credentials required")
        profile = Path(os.environ["LOCALAPPDATA"]) / "org.learntheticker.desktop/connections/gemini-qualification"
        return run("--live", profile)
    except KeyboardInterrupt:
        print('{"status":"cancelled","inference_requested":false,"generation_qualified":false,"credits_enabled":false}')
        return 2
    except Exception:
        print('{"status":"unexpected_failure","inference_requested":false,"generation_qualified":false,"credits_enabled":false}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
