"""Exercise real private process handles, never the running ATLAS instance."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import subprocess
import sys
import time
from ctypes import wintypes

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))
import process_group
from process_group import ProcessGroup

FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


@pytest.mark.parametrize('limit', [0, -1, True])
def test_invalid_memory_limit_is_rejected(limit):
    with pytest.raises(ValueError, match='entero positivo'):
        ProcessGroup(memory_limit_bytes=limit)


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object memory enforcement')
def test_windows_memory_limit_blocks_large_child_allocation():
    code = "input()\ntry:\n data=bytearray(256*1024*1024)\n print('unlimited')\nexcept MemoryError:\n print('limited')"
    child = subprocess.Popen([sys.executable, '-c', code], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=FLAGS)
    try:
        with ProcessGroup(memory_limit_bytes=128*1024*1024) as group:
            group.add(child)
            output, error = child.communicate('go\n', timeout=8)
            assert child.returncode == 0, error
            assert output.strip() == 'limited'
    finally:
        stop_owned(child)


def sleeper():
    return subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=FLAGS,
    )


def stop_owned(process):
    if process.poll() is None:
        process.kill()
    process.wait(timeout=8)


def test_context_closes_only_added_processes():
    outside = sleeper()
    child = None
    try:
        with ProcessGroup() as group:
            child = sleeper()
            assert group.add(child) is child
            assert group.add(child) is child
        assert child.poll() is not None
        assert outside.poll() is None
        group.close()
        with pytest.raises(RuntimeError, match="cerrado"):
            group.add(outside)
        assert outside.poll() is None
    finally:
        if child is not None:
            stop_owned(child)
        stop_owned(outside)


def test_context_cleans_up_when_body_raises():
    child = None
    try:
        with pytest.raises(ValueError, match="fallo deliberado"):
            with ProcessGroup() as group:
                child = sleeper()
                group.add(child)
                raise ValueError("fallo deliberado")
        assert child.poll() is not None
    finally:
        if child is not None:
            stop_owned(child)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object")
def test_windows_job_creation_failure_is_explicit(monkeypatch):
    api = process_group._windows_api()

    def denied(*args):
        ctypes.set_last_error(5)
        return None

    monkeypatch.setattr(api, "CreateJobObjectW", denied)
    monkeypatch.setattr(process_group, "_windows_api", lambda: api)
    with pytest.raises(OSError, match="crear la protección") as result:
        ProcessGroup()
    assert result.value.winerror == 5


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object")
def test_windows_assignment_failure_leaves_caller_responsible(monkeypatch):
    child = sleeper()
    try:
        with ProcessGroup() as group:
            def denied(*args):
                ctypes.set_last_error(5)
                return False

            monkeypatch.setattr(group._job._api, "AssignProcessToJobObject", denied)
            with pytest.raises(OSError, match="proteger un proceso") as result:
                group.add(child)
            assert result.value.winerror == 5
        assert child.poll() is None
    finally:
        stop_owned(child)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object")
def test_killed_supervisor_terminates_child_and_descendant(tmp_path):
    # All created scripts and identity handshakes live in this test's directory.
    # Retain OS handles before killing the supervisor: PID reuse cannot change
    # the objects checked or cleaned up by the parent test.
    child_script = tmp_path / "child.py"
    child_script.write_text(
        "import pathlib, subprocess, sys, time\n"
        "root = pathlib.Path(sys.argv[1])\n"
        "while not (root / 'assigned').exists(): time.sleep(0.02)\n"
        "descendant = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], "
        "creationflags=subprocess.CREATE_NO_WINDOW)\n"
        "(root / 'descendant').write_text(str(descendant.pid))\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    supervisor_script = tmp_path / "supervisor.py"
    supervisor_script.write_text(
        "import pathlib, subprocess, sys, time\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from process_group import ProcessGroup\n"
        "root = pathlib.Path(sys.argv[2])\n"
        "with ProcessGroup() as group:\n"
        "    child = subprocess.Popen([sys.executable, str(root / 'child.py'), str(root)], "
        "creationflags=subprocess.CREATE_NO_WINDOW)\n"
        "    try: group.add(child)\n"
        "    except BaseException:\n"
        "        child.kill(); child.wait(); raise\n"
        "    (root / 'child').write_text(str(child.pid))\n"
        "    (root / 'assigned').touch()\n"
        "    time.sleep(30)\n",
        encoding="utf-8",
    )
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    api.TerminateProcess.restype = wintypes.BOOL
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    handles = []
    with (tmp_path / "supervisor.log").open("wb") as log:
        supervisor = subprocess.Popen(
            [sys.executable, str(supervisor_script), str(TOOLS), str(tmp_path)],
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            creationflags=FLAGS,
        )
        try:
            deadline = time.monotonic() + 10
            for filename in ("child", "descendant"):
                identity = tmp_path / filename
                while not identity.exists() or not identity.read_text().strip():
                    assert supervisor.poll() is None, (tmp_path / "supervisor.log").read_text()
                    assert time.monotonic() < deadline, "El proceso de prueba no arrancó."
                    time.sleep(0.02)
                handle = api.OpenProcess(0x00100000 | 0x0001, False, int(identity.read_text()))
                assert handle, ctypes.WinError(ctypes.get_last_error())
                handles.append(handle)
                assert api.WaitForSingleObject(handle, 0) == 258  # WAIT_TIMEOUT: alive
            supervisor.kill()  # Deliberately skips __exit__ and Python finally.
            supervisor.wait(timeout=8)
            for handle in handles:
                assert api.WaitForSingleObject(handle, 8000) == 0  # WAIT_OBJECT_0: exited
        finally:
            stop_owned(supervisor)
            for handle in handles:
                try:
                    if api.WaitForSingleObject(handle, 0) == 258:
                        assert api.TerminateProcess(handle, 1)
                        assert api.WaitForSingleObject(handle, 8000) == 0
                finally:
                    assert api.CloseHandle(handle)
