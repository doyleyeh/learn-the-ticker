"""Windows process ownership using documented Job Objects and suspended startup.

No PID scanning for cleanup. Only the just-created suspended process is attached;
its initial thread is resumed after the job's kill-on-close boundary is installed.
"""
import ctypes
from ctypes import wintypes as w


class BasicLimits(ctypes.Structure):
    _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                ("flags", w.DWORD), ("min_working_set", ctypes.c_size_t),
                ("max_working_set", ctypes.c_size_t), ("active_limit", w.DWORD),
                ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [("basic", BasicLimits), ("io_counters", ctypes.c_uint64 * 6),
                ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]


class ThreadEntry(ctypes.Structure):
    _fields_ = [("size", w.DWORD), ("usage", w.DWORD), ("thread_id", w.DWORD),
                ("process_id", w.DWORD), ("base_priority", w.LONG), ("delta_priority", w.LONG), ("flags", w.DWORD)]


class WindowsJob:
    def __init__(self):
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        definitions = {
            "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            "SetInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
            "OpenProcess": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            "OpenThread": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            "GetProcessIdOfThread": ([w.HANDLE], w.DWORD),
            "CreateToolhelp32Snapshot": ([w.DWORD, w.DWORD], w.HANDLE),
            "Thread32First": ([w.HANDLE, ctypes.POINTER(ThreadEntry)], w.BOOL),
            "Thread32Next": ([w.HANDLE, ctypes.POINTER(ThreadEntry)], w.BOOL),
            "ResumeThread": ([w.HANDLE], w.DWORD),
            "WaitForSingleObject": ([w.HANDLE, w.DWORD], w.DWORD),
            "CloseHandle": ([w.HANDLE], w.BOOL),
        }
        for name, (args, result) in definitions.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError("Cannot create provider process ownership boundary")
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise OSError("Cannot configure provider process ownership boundary")

    def attach_and_resume(self, pid: int):
        # PROCESS_SET_QUOTA | PROCESS_TERMINATE | SYNCHRONIZE. The caller retains
        # the asyncio process/Popen handle, so its PID cannot be reused here.
        process = self.api.OpenProcess(0x100 | 0x1 | 0x100000, False, pid)
        if not process:
            raise OSError("Cannot attach provider process")
        try:
            if self.api.WaitForSingleObject(process, 0) != 258:
                raise OSError("Provider exited before ownership was established")
            if not self.api.AssignProcessToJobObject(self.handle, process):
                raise OSError("Cannot enforce provider process ownership")
            self.resume_initial_thread(pid)
        finally:
            self.api.CloseHandle(process)

    def resume_initial_thread(self, pid: int):
        snapshot = self.api.CreateToolhelp32Snapshot(0x4, 0)  # TH32CS_SNAPTHREAD
        if snapshot == ctypes.c_void_p(-1).value:
            raise OSError("Cannot verify suspended provider thread")
        threads = []
        try:
            entry = ThreadEntry()
            entry.size = ctypes.sizeof(entry)
            present = self.api.Thread32First(snapshot, ctypes.byref(entry))
            while present:
                if entry.process_id == pid:
                    threads.append(entry.thread_id)
                entry.size = ctypes.sizeof(entry)
                present = self.api.Thread32Next(snapshot, ctypes.byref(entry))
        finally:
            self.api.CloseHandle(snapshot)
        if len(threads) != 1:
            raise OSError("Provider did not remain suspended during setup")
        thread = self.api.OpenThread(0x2 | 0x800, False, threads[0])  # SUSPEND_RESUME | QUERY_LIMITED_INFORMATION
        if not thread:
            raise OSError("Cannot resume owned provider")
        try:
            if self.api.GetProcessIdOfThread(thread) != pid or self.api.ResumeThread(thread) != 1:
                raise OSError("Provider thread ownership or suspend count changed")
        finally:
            self.api.CloseHandle(thread)

    def close(self):
        handle, self.handle = self.handle, None
        if handle and not self.api.CloseHandle(handle):
            raise OSError("Cannot close provider process ownership boundary")
