"""Real isolated child processes, never installed providers or system services."""
import asyncio
import os
from pathlib import Path
import sys

import pytest

from backend.app.owned_process import launch_owned, close_owned


PYTHON = getattr(sys, "_base_executable", sys.executable)
CHILD = "import os,time; print(os.getpid(),flush=True); time.sleep(60)"


def open_child(pid):
    if os.name != "nt": return None
    from backend.app.windows_job import WindowsJob
    # Read-only wait handle held before cleanup avoids PID-reuse assumptions.
    job = WindowsJob()
    handle = job.api.OpenProcess(0x100000, False, pid)
    job.close()
    assert handle
    return job.api, handle


async def assert_child_stopped(process, child):
    if child:
        api, handle = child
        try:
            assert await asyncio.to_thread(api.WaitForSingleObject, handle, 5000) == 0
        finally:
            api.CloseHandle(handle)
    # The child inherited stdout; EOF establishes that the descendant closed it.
    assert await asyncio.wait_for(process.stdout.read(), 5) == b""


@pytest.mark.parametrize("leader_exits", [False, True])
def test_closing_owned_tree_stops_descendants_and_preserves_unrelated_child(leader_exits):
    async def run():
        script = f"import subprocess,time; subprocess.Popen([{PYTHON!r},'-c',{CHILD!r}]); " + ("time.sleep(.2)" if leader_exits else "time.sleep(60)")
        process = await launch_owned(PYTHON, "-c", script, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        unrelated = await launch_owned(PYTHON, "-c", CHILD, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            child = open_child(int(await asyncio.wait_for(process.stdout.readline(), 5)))
            await asyncio.wait_for(unrelated.stdout.readline(), 5)
            if leader_exits:
                async with asyncio.timeout(5):
                    while process.returncode is None: await asyncio.sleep(.01)
            await close_owned(process, grace=.05)
            await assert_child_stopped(process, child)
            assert unrelated.returncode is None
            await close_owned(process)  # Idempotent; no unrelated process discovery.
        finally:
            await close_owned(process)
            await close_owned(unrelated)
    asyncio.run(run())


@pytest.mark.skipif(os.name != "nt", reason="Windows job assignment and crash ownership")
def test_ownership_failure_never_executes_suspended_child(tmp_path, monkeypatch):
    from backend.app.windows_job import WindowsJob
    marker = tmp_path / "must-not-execute"
    def reject(self, pid): raise OSError("injected assignment failure")
    monkeypatch.setattr(WindowsJob, "attach_and_resume", reject)
    async def run():
        with pytest.raises(OSError, match="assignment failure"):
            await launch_owned(PYTHON, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('executed')")
        assert not marker.exists()
    asyncio.run(run())


@pytest.mark.skipif(os.name != "nt", reason="Windows kill-on-owner-exit boundary")
def test_owner_crash_closes_job_and_terminates_descendant_without_recovery_scan():
    async def run():
        owner_code = f"""
import asyncio,os,sys
from backend.app.owned_process import launch_owned
async def main():
    child = await launch_owned({PYTHON!r}, '-c', {CHILD!r}, stdout=asyncio.subprocess.PIPE)
    print((await child.stdout.readline()).decode().strip(), flush=True)
    await asyncio.to_thread(sys.stdin.readline)
    os._exit(7)
asyncio.run(main())
"""
        owner = await asyncio.create_subprocess_exec(PYTHON, "-c", owner_code, cwd=Path(__file__).resolve().parents[2],
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            creationflags=0x08000000)
        child = None
        try:
            child = open_child(int(await asyncio.wait_for(owner.stdout.readline(), 5)))
            owner.stdin.write(b"stop\n"); await owner.stdin.drain()
            assert await asyncio.wait_for(owner.wait(), 5) == 7
            await assert_child_stopped(owner, child)
            child = None
        finally:
            if owner.returncode is None: owner.kill()
            await owner.wait()
            if child: child[0].CloseHandle(child[1])
    asyncio.run(run())
