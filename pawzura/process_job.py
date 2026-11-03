"""Windows kill-on-close job for processes created by this application only."""
import ctypes
from ctypes import wintypes
import os
import time


class OwnedProcessJob:
    def __init__(self, process):
        self.handle = None
        self.api = None
        self.wait_handles = []
        if os.name != "nt":
            return
        class Limits(ctypes.Structure):
            _fields_ = [("user", ctypes.c_longlong), ("job", ctypes.c_longlong),
                        ("flags", wintypes.DWORD), ("minimum", ctypes.c_size_t),
                        ("maximum", ctypes.c_size_t), ("active", wintypes.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                        ("scheduling", wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ("read", "write", "other", "read_bytes", "write_bytes", "other_bytes")]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Limits), ("io", IO), ("process_memory", ctypes.c_size_t),
                        ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        api.CreateJobObjectW.restype = wintypes.HANDLE
        api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        api.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.api = api
        handle = api.CreateJobObjectW(None, None)
        info = Extended(); info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not handle or not api.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            if handle:
                api.CloseHandle(handle)
            raise OSError("Cannot contain owned worker")
        if not api.AssignProcessToJobObject(handle, wintypes.HANDLE(int(process._handle))):
            api.CloseHandle(handle)
            raise OSError("Cannot contain owned worker")
        self.handle = handle
        self.forced = False
        # Popen starts this owned process suspended; assign its job before the
        # venv launcher can create an uncontained CUDA child, then resume once.
        class ThreadEntry(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD), ("tid", wintypes.DWORD),
                        ("pid", wintypes.DWORD), ("priority", wintypes.LONG), ("delta", wintypes.LONG), ("flags", wintypes.DWORD)]
        api.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        api.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        api.Thread32First.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        api.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        api.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenThread.restype = wintypes.HANDLE
        api.ResumeThread.argtypes = [wintypes.HANDLE]
        api.ResumeThread.restype = wintypes.DWORD
        snapshot = api.CreateToolhelp32Snapshot(4, 0)
        threads = []
        entry = ThreadEntry(); entry.size = ctypes.sizeof(entry)
        try:
            ok = api.Thread32First(snapshot, ctypes.byref(entry))
            while ok:
                if entry.pid == process.pid:
                    threads.append(entry.tid)
                ok = api.Thread32Next(snapshot, ctypes.byref(entry))
        finally:
            api.CloseHandle(snapshot)
        if len(threads) != 1:
            self.terminate(); self.close()
            raise OSError("Cannot resume contained worker")
        thread = api.OpenThread(2, False, threads[0])
        try:
            if not thread or api.ResumeThread(thread) == 0xffffffff:
                self.terminate()
                self.close()
                raise OSError("Cannot resume contained worker")
        finally:
            if thread:
                api.CloseHandle(thread)

    def terminate(self):
        if self.handle:
            # Job accounting can reach zero just before the process objects are
            # signalled. Keep owned descendant handles and wait for final exit.
            class ProcessList(ctypes.Structure):
                _fields_ = [("assigned", wintypes.DWORD), ("count", wintypes.DWORD),
                            ("ids", ctypes.c_size_t * 512)]
            info = ProcessList()
            if self.api.QueryInformationJobObject(self.handle, 3, ctypes.byref(info), ctypes.sizeof(info), None):
                for pid in info.ids[:info.count]:
                    handle = self.api.OpenProcess(0x100000, False, pid)
                    if handle:
                        self.wait_handles.append(handle)
            self.api.TerminateJobObject(self.handle, 1)

    def close(self):
        if self.handle:
            class Accounting(ctypes.Structure):
                _fields_ = [("user", ctypes.c_longlong), ("kernel", ctypes.c_longlong),
                            ("period_user", ctypes.c_longlong), ("period_kernel", ctypes.c_longlong),
                            ("faults", wintypes.DWORD), ("total", wintypes.DWORD),
                            ("active", wintypes.DWORD), ("terminated", wintypes.DWORD)]
            self.api.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
            started = time.monotonic()
            while True:
                info = Accounting()
                if not self.api.QueryInformationJobObject(self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None):
                    self.terminate()
                    self.api.CloseHandle(self.handle); self.handle = None
                    from .model_jobs import quarantine
                    quarantine()
                    raise OSError("Cannot verify worker release")
                if not info.active:
                    break
                if time.monotonic() - started > .5:
                    self.forced = True
                    self.terminate()
                if time.monotonic() - started > 5:
                    from .model_jobs import quarantine
                    quarantine()
                    self.api.CloseHandle(self.handle); self.handle = None
                    raise OSError("Cannot verify worker release")
                time.sleep(.01)
            self.api.CloseHandle(self.handle)
            self.handle = None
            deadline = time.monotonic() + 5
            failed = False
            for handle in self.wait_handles:
                remaining = max(0, int((deadline - time.monotonic()) * 1000))
                failed |= self.api.WaitForSingleObject(handle, remaining) != 0
                self.api.CloseHandle(handle)
            self.wait_handles.clear()
            if failed:
                from .model_jobs import quarantine
                quarantine()
                raise OSError("Cannot verify worker release")
