"""Check actual source/frozen market dependencies and owned shutdown without network."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from backend.app import yfinance_worker as worker
from backend.app.owned_process import close_owned, launch_owned


async def check():
    result = await worker.check_dependencies()
    # An incomplete request waits for EOF without importing/fetching market data.
    # Close the real Job Object while the worker/bootloader is still running.
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ}
    if not getattr(worker.sys, "frozen", False):
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    with tempfile.TemporaryDirectory(prefix="ltt-market-cancel-") as directory:
        environment.update({"TEMP": directory, "TMP": directory})
        process = await launch_owned(*worker.worker_command(check_only=True), cwd=directory, env=environment,
            memory_limit=worker.MEMORY_LIMIT, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            process.stdin.write(b'{')
            await process.stdin.drain()
            await asyncio.sleep(2)
            assert process.returncode is None
        finally:
            await close_owned(process)
        assert process.returncode is not None
    print(json.dumps({**result, "owned_shutdown": True, "temporary_workspace_removed": not Path(directory).exists()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packaged", action="store_true")
    args = parser.parse_args()
    if args.packaged:
        executable = Path(__file__).resolve().parents[1] / "dist/ltt-service.exe"
        if not executable.is_file():
            raise SystemExit("Build the Windows sidecar before packaged market verification")
        with patch("sys.frozen", True, create=True), patch("sys.executable", str(executable)):
            asyncio.run(check())
    else:
        asyncio.run(check())


if __name__ == "__main__":
    main()
