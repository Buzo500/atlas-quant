"""Contain only subprocesses created and explicitly added by this launcher.

On Windows an unnamed, non-inheritable Job Object terminates assigned processes
and their subsequent descendants when its last handle closes, including when
the launcher is killed. Other platforms only clean up the recorded Popen
handles on normal close; they do not provide the same abrupt-exit guarantee.

Call add immediately after Popen. The caller still owns cleanup if assignment
fails, or if it exits between spawning and assigning a process. Descendants
created before assignment are not retroactively included in the Windows job.
Request graceful application shutdown before closing this last-resort guard.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
from ctypes import wintypes


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def _windows_api():
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    api.CreateJobObjectW.restype = wintypes.HANDLE
    api.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    api.SetInformationJobObject.restype = wintypes.BOOL
    api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    api.AssignProcessToJobObject.restype = wintypes.BOOL
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    return api


def _windows_error(action: str) -> OSError:
    code = ctypes.get_last_error()
    return ctypes.WinError(code, f"{action}: {ctypes.FormatError(code).strip()}")


class _WindowsJob:
    def __init__(self):
        self._api = _windows_api()
        # NULL SECURITY_ATTRIBUTES makes this handle non-inheritable. Keeping
        # it unnamed also prevents another launcher from opening the same job.
        # https://learn.microsoft.com/windows/win32/api/jobapi2/nf-jobapi2-createjobobjectw
        self._handle = self._api.CreateJobObjectW(None, None)
        if not self._handle:
            raise _windows_error("No se pudo crear la protección de procesos de ATLAS")
        limits = _ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not self._api.SetInformationJobObject(
            self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits),
        ):
            error = _windows_error("No se pudo configurar la protección de procesos de ATLAS")
            self._api.CloseHandle(self._handle)
            self._handle = None
            raise error

    def add(self, process: subprocess.Popen):
        # Popen owns this handle, so identity remains stable even if a PID is
        # recycled. Never reopen processes by name, port, or recorded PID.
        if not self._api.AssignProcessToJobObject(self._handle, int(process._handle)):
            raise _windows_error("No se pudo proteger un proceso hijo de ATLAS")

    def close(self):
        if self._handle is not None:
            if not self._api.CloseHandle(self._handle):
                raise _windows_error("No se pudo cerrar la protección de procesos de ATLAS")
            self._handle = None


class ProcessGroup:
    """Context manager owning a job and the successfully assigned Popen handles.

    Creation/assignment errors propagate: callers must stop startup and clean
    up any subprocess whose add failed. close is idempotent after success.
    """

    def __init__(self):
        self._processes: list[subprocess.Popen] = []
        self._closed = False
        self._job = _WindowsJob() if os.name == "nt" else None

    def __enter__(self):
        if self._closed:
            raise RuntimeError("El grupo de procesos ya está cerrado.")
        return self

    def add(self, process: subprocess.Popen) -> subprocess.Popen:
        if self._closed:
            raise RuntimeError("El grupo de procesos ya está cerrado.")
        if process in self._processes:
            return process
        if self._job is not None:
            self._job.add(process)
        self._processes.append(process)
        return process

    def close(self):
        if self._closed:
            return
        errors = []
        if self._job is not None:
            try:
                self._job.close()
            except OSError as error:
                errors.append(error)
        # Also reap Popen handles and clean them up if the OS job close failed.
        # On non-Windows this is the only available containment mechanism.
        for process in self._processes:
            try:
                if process.poll() is None:
                    process.terminate()
            except OSError as error:
                errors.append(error)
        for process in self._processes:
            try:
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=8)
            except (OSError, subprocess.TimeoutExpired) as error:
                errors.append(error)
        if errors:
            raise ExceptionGroup("No se pudo cerrar completamente el grupo de ATLAS", errors)
        self._closed = True

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
