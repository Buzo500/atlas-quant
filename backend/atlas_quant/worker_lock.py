"""Local executor ownership, independent of SQLite write transactions.

The lock file is deliberately persistent: removing it can create two different
inodes and allow simultaneous owners. Only the OS lock denotes ownership, never
file contents or a recorded PID. This is a single-machine guard, not a lease for
distributed workers or a database on a network share.
"""
from __future__ import annotations

import errno
import os
from pathlib import Path
import threading
from typing import BinaryIO


class WorkerAlreadyRunning(RuntimeError):
    """Another local executor owns this database's execution lock."""


class WorkerLock:
    """Nonblocking, crash-released lock across threads and local processes."""

    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self._handle: BinaryIO | None = None
        self._guard = threading.Lock()

    def acquire(self) -> bool:
        """Return False on contention; propagate filesystem/configuration errors."""
        with self._guard:
            if self._handle is not None:
                raise RuntimeError("Este objeto ya tiene adquirido el bloqueo del ejecutor.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle = self.path.open("a+b")
            try:
                if os.fstat(handle.fileno()).st_size == 0:
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    if exc.errno in (errno.EACCES, errno.EAGAIN):
                        handle.close()
                        return False
                    raise
            except BaseException:
                handle.close()
                raise
            self._handle = handle
            return True

    def release(self) -> None:
        with self._guard:
            if self._handle is not None:
                # Closing the last descriptor releases the OS lock even on crash.
                self._handle.close()
                self._handle = None

    def __enter__(self) -> WorkerLock:
        if not self.acquire():
            raise WorkerAlreadyRunning("Ya hay un ejecutor de ATLAS usando esta base local.")
        return self

    def __exit__(self, *args) -> None:
        self.release()
