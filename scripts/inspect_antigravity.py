"""Explicit pinned Windows CLI prerequisites; never starts login or generation."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import tempfile

from backend.app.owned_process import close_owned, launch_owned
from backend.app.runtime_base import provider_environment

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / ".local/antigravity-qualification/agy-1.3.0.exe"
BINARY_BYTES = 189972632
BINARY_SHA512 = "00ddc37369441524aa9bd92176e31513e47a2a85fe5d09ec71e3bbe2fd4955551c6b9989f1eb82599dd9329b321e470644106ee3b07c1e3e82bff67124a67461"
HELP_SHA256 = "bbf3bd71084c84e5896296e77b1b022b38c16feb6306817122e2554218e3f8d5"
OUTPUT_LIMIT = 8192
DEADLINE_SECONDS = 15


class InspectionFailure(ValueError):
    pass


def reviewed_binary(path=BINARY):
    if path.stat().st_size != BINARY_BYTES:
        raise InspectionFailure("runtime_drift")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha512").hexdigest() != BINARY_SHA512:
            raise InspectionFailure("runtime_drift")
    return path


def inspection_environment(profile):
    env = provider_environment()
    # Redirect all ordinary home/config/temp discovery for these help-only runs.
    # This is not evidence that authenticated native credentials are namespaced.
    for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "GEMINI_CLI_HOME"):
        env[name] = str(profile)
    env.update({"NO_COLOR": "1", "AGY_CLI_DISABLE_AUTO_UPDATE": "true"})
    return env


async def bounded_output(stream):
    data = bytearray()
    while chunk := await stream.read(min(4096, OUTPUT_LIMIT + 1 - len(data))):
        data.extend(chunk)
        if len(data) > OUTPUT_LIMIT:
            raise InspectionFailure("output_limit")
    return bytes(data)


async def inspect_command(executable, flag, profile):
    if flag not in ("--version", "--help"):
        raise InspectionFailure("command_out_of_scope")
    process = await launch_owned(str(executable), flag, cwd=profile, env=inspection_environment(profile),
                                stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE)
    tasks = []
    try:
        tasks = [asyncio.create_task(bounded_output(process.stdout)),
                 asyncio.create_task(bounded_output(process.stderr)), asyncio.create_task(process.wait())]
        stdout, stderr, code = await asyncio.wait_for(asyncio.gather(*tasks), DEADLINE_SECONDS)
        if code != 0:
            raise InspectionFailure("inspection_failed")
        if flag == "--version":
            if stdout.replace(b"\r\n", b"\n") != b"1.3.0\n" or stderr:
                raise InspectionFailure("version_mismatch")
        else:
            # Pinned Windows CLI prints its public help on stderr, not stdout.
            if stdout or hashlib.sha256(stderr.replace(b"\r\n", b"\n")).hexdigest() != HELP_SHA256:
                raise InspectionFailure("help_mismatch")
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await close_owned(process)


async def inspect(executable=BINARY):
    reviewed_binary(executable)
    for flag in ("--version", "--help"):
        with tempfile.TemporaryDirectory(prefix="ltt-agy-prerequisite-") as directory:
            profile = Path(directory)
            await inspect_command(executable, flag, profile)
            if any(profile.rglob("*")):
                raise InspectionFailure("unexpected_profile_write")
        reviewed_binary(executable)
    return {"status": "prerequisites_verified", "version": "1.3.0",
            "inference_requested": False, "authentication_requested": False,
            "generation_qualified": False, "credential_isolation_qualified": False,
            "tool_execution_qualified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true", required=True,
                        help="Inspect only the exact staged binary's version/help in fresh profiles")
    parser.parse_args(argv)
    try:
        if os.name != "nt":
            raise InspectionFailure("windows_required")
        report = asyncio.run(inspect())
        code = 0
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
