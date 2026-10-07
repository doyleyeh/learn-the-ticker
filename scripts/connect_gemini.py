"""Explicit developer-only Gemini OAuth sign-in; no model call or API billing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from backend.app.runtime_base import provider_environment


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / ".local/gemini-qualification/node_modules/@google/gemini-cli"
HASHES = {
    "chunk-MLY4WQFO.js": "c67737944afddc18a1cee05b556367c1beab2235bf608d5fdf57bb0cfc42cce0",
    "chunk-664ZODQF.js": "0e5e41b8af7ca2ddd1bc3509c7276559d48a99705d6716b6d45c4c64b4f9168c",
    "chunk-IUUIT4SU.js": "878469f1440495db8e40b033dde88ab96c0ee7d9e40c3deb4cee91dde1c8031a",
    "chunk-L6PII3GR.js": "6f09ec2e98657a710dfeed9d02de7921bf2e1ff3d8f6b9911129931ff1fb6b31",
    "chunk-34MYV7JD.js": "019fd0819c9e85555d6a6fbe468a53f647955dca2b5d629c6a920ef9ca8de6de",
}


def reviewed_entry(package=PACKAGE):
    metadata = json.loads((package / "package.json").read_text(encoding="utf-8"))
    if metadata.get("name") != "@google/gemini-cli" or metadata.get("version") != "0.62.0":
        raise ValueError("Unreviewed Gemini package")
    for name, digest in HASHES.items():
        if hashlib.sha256((package / "bundle" / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Unreviewed Gemini implementation")
    return package / "bundle/chunk-MLY4WQFO.js"


def login_environment(profile):
    env = provider_environment()
    env.update({
        "GEMINI_CLI_HOME": str(profile),
        # Upstream's name selects its hybrid storage; the JS guard forbids file fallback.
        "GEMINI_FORCE_ENCRYPTED_FILE_STORAGE": "true",
        "GEMINI_TELEMETRY_ENABLED": "false",
        "OAUTH_CALLBACK_HOST": "127.0.0.1",
    })
    return env


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Synthetic native vault probe only")
    mode.add_argument("--login", action="store_true", help="Open Google's official OAuth flow")
    args = parser.parse_args(argv)
    try:
        if os.name != "nt" or not os.environ.get("LOCALAPPDATA"):
            raise ValueError("Windows native login required")
        entry = reviewed_entry()
        node = shutil.which("node")
        if not node:
            raise ValueError("Node is unavailable")
        profile = Path(os.environ["LOCALAPPDATA"]) / "org.learntheticker.desktop/connections/gemini-qualification"
        profile.mkdir(parents=True, exist_ok=True)
        print("Opening Google sign-in; no inference requested." if args.login else "Checking native credential storage.", flush=True)
        result = subprocess.run(
            [node, str(ROOT / "scripts/gemini_login.mjs"), "--login" if args.login else "--check", str(entry)],
            env=login_environment(profile), cwd=profile, capture_output=True, timeout=330,
        )
        allowed = {b"native_storage_ready\n", b"authenticated\n", b"sign_in_failed\n", b"sign_in_cancelled\n", b"sign_in_timed_out\n"}
        status = result.stdout if result.stdout in allowed else b"sign_in_failed\n"
        print(status.decode().strip())
        return 0 if result.returncode == 0 and status in {b"native_storage_ready\n", b"authenticated\n"} else 2
    except KeyboardInterrupt:
        print("sign_in_cancelled")
        return 2
    except Exception:
        print("sign_in_failed: check the reviewed staged runtime and native credential store.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
