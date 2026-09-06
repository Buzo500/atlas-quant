"""Shared local runtime primitives. No application import or provider calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import uuid


class InstanceLock:
    """OS-owned lock; a stale file or PID never counts as a running instance."""

    def __init__(self, path):
        self.path = Path(path)
        self.handle = None

    def acquire(self):
        if self.handle is not None:
            raise RuntimeError("El bloqueo ya está adquirido por este objeto.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            if self.path.stat().st_size == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False
        self.handle = handle
        return True

    def release(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("ATLAS está activo o hay otra operación de mantenimiento.")
        return self

    def __exit__(self, *args):
        self.release()


def locked(path):
    lock = InstanceLock(path)
    acquired = lock.acquire()
    lock.release()
    return not acquired


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def port_open(port):
    with socket.socket() as sock:
        sock.settimeout(.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def frontend_env(environment):
    result = {k: v for k, v in environment.items()
              if k.upper() not in {"OPENAI_API_KEY", "ANTHROPIC_API_KEY"}}
    result["NODE_ENV"] = "production"
    return result


def run_owned(command, **kwargs):
    """Keep installers/builders in the same owned Windows process tree."""
    from process_group import ProcessGroup
    # CREATE_NO_WINDOW does not reliably inherit redirected console handles
    # on Windows unless they are supplied explicitly to Popen.
    kwargs.setdefault("stdout", sys.stdout)
    kwargs.setdefault("stderr", sys.stderr)
    with ProcessGroup() as group:
        child = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                                 **kwargs)
        try:
            group.add(child)
            result = child.wait()
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
        if result:
            raise subprocess.CalledProcessError(result, command)
