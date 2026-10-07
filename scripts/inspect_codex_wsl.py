"""Explicit, account-free inspection of the pinned Linux Codex binary on WSL2.

Uses only Python's standard library so the WSL bootstrap does not depend on an
already working application environment. Never signs in or qualifies inference.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from backend.app.owned_process import close_owned, launch_owned


VERSION = "0.158.0-alpha.2.1"
BINARY_BYTES = 284774856
BINARY_SHA256 = "e8039ff5fdb49ad420a410903efae62dac2c904e616ca4261ede9e327c225619"
OUTPUT_LIMIT = 65536
DEADLINE_SECONDS = 15


class InspectionFailure(ValueError):
    pass


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def reviewed_binary(path):
    if not path.is_absolute() or any(part.is_symlink() for part in (path, *path.parents)):
        raise InspectionFailure("runtime_path_rejected")
    if path.as_posix().startswith("/mnt/"):
        raise InspectionFailure("linux_filesystem_required")
    if not path.is_file() or path.stat().st_size != BINARY_BYTES or digest(path) != BINARY_SHA256:
        raise InspectionFailure("runtime_drift")
    return path


def inspection_environment(profile):
    # No inherited credential bus, Windows PATH, hooks, endpoints or billing.
    # This is for version/help only, not a persistent authentication environment.
    return {"PATH": "/usr/bin:/bin", "HOME": str(profile), "CODEX_HOME": str(profile),
            "XDG_CONFIG_HOME": str(profile / "config"), "XDG_DATA_HOME": str(profile / "data"),
            "XDG_CACHE_HOME": str(profile / "cache"), "TMPDIR": str(profile),
            "LANG": "C.UTF-8", "NO_COLOR": "1"}


async def bounded_output(stream):
    data = bytearray()
    while chunk := await stream.read(min(4096, OUTPUT_LIMIT + 1 - len(data))):
        data.extend(chunk)
        if len(data) > OUTPUT_LIMIT:
            raise InspectionFailure("output_limit")
    return bytes(data)


async def inspect_command(binary, flag, profile):
    if flag not in ("--version", "--help"):
        raise InspectionFailure("command_out_of_scope")
    process = await launch_owned(str(binary), flag, cwd=profile, env=inspection_environment(profile),
                                stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE)
    tasks = []
    try:
        tasks = [asyncio.create_task(bounded_output(process.stdout)),
                 asyncio.create_task(bounded_output(process.stderr)), asyncio.create_task(process.wait())]
        stdout, stderr, code = await asyncio.wait_for(asyncio.gather(*tasks), DEADLINE_SECONDS)
        if code:
            raise InspectionFailure("inspection_failed")
        if flag == "--version":
            if stdout.strip() != ("codex-cli " + VERSION).encode():
                raise InspectionFailure("version_mismatch")
        elif not all(word in stdout for word in (b"Usage:", b"app-server", b"sandbox", b"login")):
            raise InspectionFailure("help_unrecognized")
        if any(profile.rglob("auth.json")):
            raise InspectionFailure("unexpected_file_credentials")
        return {"stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                "stdout_bytes": len(stdout), "stderr_bytes": len(stderr)}
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await close_owned(process)


async def inspect(binary):
    reviewed_binary(binary)
    checks = {}
    for flag in ("--version", "--help"):
        with tempfile.TemporaryDirectory(prefix="ltt-codex-wsl-inspect-") as directory:
            profile = Path(directory)
            checks[flag[2:]] = await inspect_command(binary, flag, profile)
        reviewed_binary(binary)
    return {"status": "runtime_prerequisites_verified", "version": VERSION,
            "binary_sha256": BINARY_SHA256, "checks": checks,
            "dependencies_present": {name: bool(shutil.which(name, path="/usr/bin:/bin"))
                                     for name in ("bwrap", "dbus-run-session", "gnome-keyring-daemon", "secret-tool")},
            "authentication_requested": False, "inference_requested": False,
            "credential_isolation_qualified": False, "sandbox_qualified": False,
            "generation_qualified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true", required=True)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if sys.platform != "linux" or "microsoft-standard-wsl2" not in os.uname().release.lower():
            raise InspectionFailure("wsl2_required")
        report, code = asyncio.run(inspect(args.binary)), 0
    except InspectionFailure as exc:
        report, code = {"status": str(exc)}, 2
    except KeyboardInterrupt:
        report, code = {"status": "cancelled"}, 2
    except Exception:
        report, code = {"status": "inspection_unavailable"}, 2
    print(json.dumps(report, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
