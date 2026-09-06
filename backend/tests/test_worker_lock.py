"""Executor ownership tested against real local OS locks, without main data."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from atlas_quant import worker_lock
from atlas_quant.store import Store
from atlas_quant.worker_lock import WorkerAlreadyRunning, WorkerLock


BACKEND = Path(worker_lock.__file__).resolve().parents[1]
CHILD_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def test_second_handle_is_rejected_and_exception_releases_owner(tmp_path):
    path = tmp_path / "local" / "atlas.sqlite3.worker.lock"
    contender = WorkerLock(path)
    with pytest.raises(ValueError, match="deliberate"):
        with WorkerLock(path) as owner:
            assert contender.acquire() is False
            with pytest.raises(WorkerAlreadyRunning, match="ejecutor"):
                with contender:
                    pytest.fail("Two simultaneous owners")
            with pytest.raises(RuntimeError, match="ya tiene adquirido"):
                owner.acquire()
            raise ValueError("deliberate")
    assert contender.acquire() is True
    contender.release()
    contender.release()
    assert path.exists()  # Never unlink the file used by potential contenders.


def test_lock_excludes_other_process_until_release(tmp_path):
    path = tmp_path / "atlas.sqlite3.worker.lock"
    source = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from atlas_quant.worker_lock import WorkerLock; "
        "lock = WorkerLock(sys.argv[2]); print(lock.acquire()); lock.release()"
    )

    def contender_result():
        result = subprocess.run(
            [sys.executable, "-c", source, str(BACKEND), str(path)],
            capture_output=True, text=True, timeout=10, check=True,
            creationflags=CHILD_FLAGS,
        )
        return result.stdout.strip()

    with WorkerLock(path):
        assert contender_result() == "False"
    assert contender_result() == "True"


def test_crashed_owner_releases_lock_without_removing_file(tmp_path):
    path = tmp_path / "atlas.sqlite3.worker.lock"
    ready = tmp_path / "child-ready.txt"
    source = (
        "import pathlib, sys, time\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from atlas_quant.worker_lock import WorkerLock\n"
        "lock = WorkerLock(sys.argv[2])\n"
        "assert lock.acquire()\n"
        "pathlib.Path(sys.argv[3]).write_text('ready')\n"
        "time.sleep(60)\n"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", source, str(BACKEND), str(path), str(ready)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        creationflags=CHILD_FLAGS,
    )
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(.01)
        assert ready.exists(), "Child did not acquire its lock within 10 seconds"
        contender = WorkerLock(path)
        assert contender.acquire() is False
        # No finally/release executes in the child: only the OS releases ownership.
        child.kill()
        child.wait(timeout=10)
        assert path.exists()
        # Windows may finish asynchronous handle cleanup just after process exit.
        deadline = time.monotonic() + 5
        acquired = contender.acquire()
        while not acquired and time.monotonic() < deadline:
            time.sleep(.01)
            acquired = contender.acquire()
        assert acquired is True
        contender.release()
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        if child.stderr is not None:
            child.stderr.close()


def test_stale_file_contents_are_not_treated_as_ownership(tmp_path):
    path = tmp_path / "atlas.sqlite3.worker.lock"
    path.write_text("obsolete owner PID: 12345", encoding="utf-8")
    with WorkerLock(path):
        assert not WorkerLock(path).acquire()
    with WorkerLock(path):
        pass
    assert path.read_text(encoding="utf-8") == "obsolete owner PID: 12345"


def test_worker_ownership_does_not_hold_main_database_write_lock(tmp_path):
    path = tmp_path / "atlas.sqlite3"
    with WorkerLock(path.with_suffix(".sqlite3.worker.lock")):
        first = Store(path)
        second = Store(path)
        first.put("settings", {"id": "main", "kill_switch": True})
        second.put("settings", {"id": "main", "kill_switch": False})
        assert first.get("settings", "main")["kill_switch"] is False


def test_filesystem_errors_are_not_reported_as_contention(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("test-denied")

    lock = WorkerLock(tmp_path / "atlas.sqlite3.worker.lock")
    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(PermissionError, match="test-denied"):
        lock.acquire()
