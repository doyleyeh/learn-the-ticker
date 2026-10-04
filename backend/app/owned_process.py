"""Bounded lifecycle for app-launched runtimes and their descendants."""
import asyncio
import os
import signal
import subprocess


class ProcessGroup:
    """POSIX deterministic development/CI support; Windows is the release target."""
    def __init__(self, pid):
        self.pid = pid

    def close(self):
        pid, self.pid = self.pid, None
        if pid is not None:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


async def launch_owned(*command, memory_limit=None, **kwargs):
    owner, process = None, None
    try:
        if os.name == "nt":
            from backend.app.windows_job import WindowsJob
            owner = WindowsJob(memory_limit=memory_limit) if memory_limit is not None else WindowsJob()
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | 0x4  # CREATE_SUSPENDED
        else:
            kwargs["start_new_session"] = True
        process = await asyncio.create_subprocess_exec(*command, **kwargs)
        if owner:
            owner.attach_and_resume(process.pid)
        else:
            owner = ProcessGroup(process.pid)
        process._ltt_owner = owner
        return process
    except BaseException:
        if owner:
            owner.close()
        if process:
            await close_owned(process)
        raise


async def close_owned(process, *, grace: float = 0):
    if process is None:
        return
    try:
        if getattr(process, "stdin", None):
            process.stdin.close()
        if grace and process.returncode is None:
            try:
                await asyncio.wait_for(process.wait(), grace)
            except TimeoutError:
                pass
    finally:
        # Always close the group even when the leader already exited: a child may
        # still be alive or holding the stdout pipe open. Handles are not inherited.
        owner = getattr(process, "_ltt_owner", None)
        if owner:
            owner.close()
        elif process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        try:
            await asyncio.wait_for(process.wait(), 5)
        except TimeoutError as exc:
            raise OSError("Owned provider shutdown did not complete") from exc
