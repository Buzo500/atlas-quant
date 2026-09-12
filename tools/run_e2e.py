"""Real compiled UI + real API, owned processes and a fresh isolated Windows database.

Does not use run_atlas (which deliberately selects the everyday database).
The production ports/proxy/Origin guard are exercised unchanged, under the same
maintenance lock as Start/Install. No instance or previous E2E data is reused.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import struct
import subprocess
import sys
import time
import uuid

from atlas_runtime import InstanceLock, atomic_json, frontend_env, port_open, read_json
from build_frontend import file_hash, verify_build
from process_group import ProcessGroup

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:3000"
PORTS = {"backend": 8000, "frontend": 3000}
RUN_PATTERN = re.compile(r"e2e-[0-9a-f]{32}\Z")


def run_directory(name: str) -> Path:
    if not RUN_PATTERN.fullmatch(name):
        raise ValueError("Identificador E2E no válido.")
    parent = (ROOT / "var/validation").resolve()
    target = (parent / name).resolve()
    if target.parent != parent:
        raise ValueError("La ejecución debe permanecer en var/validation.")
    return target


def isolated_data(run: Path) -> Path:
    expected = run_directory(run.name)
    if run.resolve() != expected:
        raise ValueError("Directorio E2E ajeno al proyecto.")
    data = (run / "data").resolve()
    if data.parent != expected or data == (ROOT / "var/atlas").resolve():
        raise ValueError("La base E2E debe ser nueva y exclusiva de esta ejecución.")
    return data


def clean_environment(run: Path) -> dict[str, str]:
    # No .env is loaded; do not forward inherited provider/billing credentials.
    excluded = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    environment = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith("ATLAS_")
                   and not any(part in key.upper() for part in excluded)
                   and key.upper() not in {"NODE_OPTIONS", "PYTHONPATH"}}
    environment.update(ATLAS_DATA_DIR=str(isolated_data(run)),
                       ATLAS_STOP_FILE=str(run / "servers.stop"), PYTHONUTF8="1",
                       PLAYWRIGHT_BROWSERS_PATH=str(ROOT / "var/playwright-browsers"))
    return environment


def listening_pid(port: int) -> int | None:
    """Read the kernel's IPv4 listener owner, never identify processes by name."""
    if os.name != "nt":
        raise RuntimeError("Este recorrido E2E está validado para Windows nativo.")
    api = ctypes.WinDLL("iphlpapi", use_last_error=True)
    api.GetExtendedTcpTable.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD),
                                       wintypes.BOOL, wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
    api.GetExtendedTcpTable.restype = wintypes.DWORD
    size = wintypes.DWORD(0)
    api.GetExtendedTcpTable(None, ctypes.byref(size), False, socket.AF_INET, 3, 0)
    buffer = ctypes.create_string_buffer(size.value)
    result = api.GetExtendedTcpTable(buffer, ctypes.byref(size), False, socket.AF_INET, 3, 0)
    if result:
        raise OSError(result, "No se pudo comprobar el propietario de los puertos E2E.")
    count = struct.unpack_from("=I", buffer)[0]
    for index in range(count):
        state, address, local_port, _, _, pid = struct.unpack_from("=6I", buffer, 4 + index * 24)
        if state == 2 and socket.ntohs(local_port & 0xffff) == port:
            if socket.inet_ntoa(struct.pack("=I", address)) != "127.0.0.1":
                raise RuntimeError("El servidor E2E no escucha exclusivamente en loopback.")
            return pid
    return None


class OwnershipError(RuntimeError):
    def __init__(self, observation):
        self.observation = observation
        super().__init__(f"El puerto {observation['port']} no pertenece al proceso E2E "
                         f"{observation['server']}. Observación: {json.dumps(observation)}")


def assert_owned(children: dict[str, subprocess.Popen], groups: dict[str, ProcessGroup]) -> dict[str, int]:
    listeners = {}
    for name, port in PORTS.items():
        child = children[name]
        pid = listening_pid(port)
        exit_code = child.poll()
        member = groups[name].contains_pid(pid) if exit_code is None and pid is not None else None
        if exit_code is not None or pid is None or not member:
            raise OwnershipError(dict(server=name, port=port, child_pid=child.pid,
                exit_code=exit_code, listener_pid=pid, member=member,
                reason='child_exited' if exit_code is not None else
                       'listener_missing' if pid is None else 'listener_not_owned'))
        listeners[name] = pid
    return listeners


def http(path: str, payload=None):
    if not path.startswith("/api/") or ".." in path:
        raise ValueError("Solo se permiten rutas de la API local.")
    connection = HTTPConnection("127.0.0.1", 3000, timeout=10)
    try:
        body = None if payload is None else json.dumps(payload)
        connection.request("GET" if payload is None else "POST", path, body=body,
                           headers={"Content-Type": "application/json", "Origin": BASE_URL,
                                    "X-Atlas-Client": "local-v1"})
        with connection.getresponse() as response:
            value = json.load(response)
            if response.status != 200:
                raise RuntimeError(f"La API E2E devuelve HTTP {response.status} en {path}.")
            return value
    finally:
        connection.close()


def assert_zero_budget(state: dict) -> None:
    if any(item.get("configured") for item in state["providers"]):
        raise RuntimeError("Un proveedor aparece configurado en el entorno E2E.")
    if any(item.get("source_kind") != "synthetic" or item.get("feed") for item in state["datasets"]):
        raise RuntimeError("La base E2E contiene una fuente externa.")
    for job in state["experiments"]:
        if (job.get("provider") != "none" or job.get("auto_paper")
                or any(job.get(field, 0) != 0 for field in ("budget_usd", "spent_usd", "reserved_usd"))
                or job.get("paper_account") or job.get("hours") != 1):
            raise RuntimeError("El experimento E2E no cumple el alcance sintético de presupuesto cero.")
    if state["settings"].get("kill_switch") is not True:
        raise RuntimeError("La parada global debe permanecer activada en E2E.")


def normal_database_hashes() -> dict[str, str]:
    folder = ROOT / "var/atlas"
    return {path.name: file_hash(path) for path in folder.glob("atlas.sqlite3*") if path.is_file()}


def finish_descriptor(directory: Path, data: Path, descriptor: dict, *, result: int,
                      error: str | None, forced_stop: bool) -> None:
    """Always revoke the token; an incomplete integrity check cannot pass."""
    descriptor.update(active=False, token=None, result=result, error=error, forced_stop=forced_stop,
                      completed_at=datetime.now(timezone.utc).isoformat())
    try:
        after = normal_database_hashes()
        descriptor["ordinary_database_after"] = after
        descriptor["ordinary_database_unchanged"] = descriptor["ordinary_database_before"] == after
        descriptor["ports_released"] = not any(port_open(port) for port in PORTS.values())
        database = data / "atlas.sqlite3"
        if not database.is_file():
            raise RuntimeError("No existe la base aislada al comprobar el cierre E2E.")
        with sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True) as db:
            checks = [row[0] for row in db.execute("PRAGMA integrity_check")]
        descriptor["integrity"] = "ok" if checks == ["ok"] else checks
        if (checks != ["ok"] or not descriptor["ordinary_database_unchanged"]
                or not descriptor["ports_released"] or forced_stop
                or any(code != 0 for code in descriptor.get("server_exit_codes", {}).values())):
            descriptor["result"] = 1
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        descriptor.update(result=1, finalization_error=str(exc))
    finally:
        atomic_json(directory / "run.json", descriptor)


def run(*, manual: bool, timeout: int, grep: str | None = None) -> int:
    if os.name != "nt":
        raise RuntimeError("E2E requiere Windows nativo; otros sistemas no están certificados.")
    node = shutil.which("node")
    cli = ROOT / "frontend/node_modules/@playwright/test/cli.js"
    if not node or not cli.is_file():
        raise RuntimeError("Instala las dependencias de frontend fijadas antes de ejecutar E2E.")
    with InstanceLock(ROOT / "var/atlas.lock"):
        if any(port_open(port) for port in PORTS.values()):
            raise RuntimeError("Detén ATLAS. E2E no reutiliza ni detiene servidores existentes.")
        verify_build(ROOT / "frontend")
        before = normal_database_hashes()
        directory = run_directory("e2e-" + uuid.uuid4().hex)
        directory.mkdir(parents=True, exist_ok=False)
        data = isolated_data(directory)
        data.mkdir(exist_ok=False)
        environment = clean_environment(directory)
        token = uuid.uuid4().hex
        descriptor = {"format": 1, "run_id": directory.name, "root": str(ROOT),
                      "data_dir": str(data), "base_url": BASE_URL, "token": token,
                      "harness_pid": os.getpid(), "active": False,
                      "ordinary_database_before": before,
                      "started_at": datetime.now(timezone.utc).isoformat()}
        children: dict[str, subprocess.Popen] = {}
        owned: list[subprocess.Popen] = []
        streams = []
        result = 1
        error = None
        forced_stop = False
        atomic_json(directory / "run.json", descriptor)
        try:
            with ExitStack() as stack:
                # Separate jobs prove each listener belongs to its own server
                # family; the venv launcher and real interpreter may differ.
                groups = {name: stack.enter_context(ProcessGroup()) for name in PORTS}
                runner_group = stack.enter_context(ProcessGroup())
                try:
                    commands = {
                        "backend": ([sys.executable, "-u", str(ROOT / "tools/serve_backend.py")], ROOT, environment),
                        "frontend": ([node, str(ROOT / "frontend/local-server.mjs")], ROOT / "frontend", frontend_env(environment)),
                    }
                    for name, (command, cwd, env) in commands.items():
                        log = (directory / f"{name}.log").open("wb")
                        streams.append(log)
                        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                                 stdout=log, stderr=subprocess.STDOUT,
                                                 creationflags=subprocess.CREATE_NO_WINDOW)
                        children[name] = child
                        owned.append(child)
                        groups[name].add(child)
                    deadline = time.monotonic() + 60
                    while True:
                        if any(child.poll() is not None for child in children.values()):
                            raise RuntimeError("Un servidor E2E terminó durante el arranque; consulta sus logs.")
                        if all(listening_pid(port) is not None for port in PORTS.values()):
                            descriptor["listener_pids"] = assert_owned(children, groups)
                            try:
                                health = http("/api/health")
                                if health["status"] == "ok" and health["live_available"] is False:
                                    break
                            except (OSError, ValueError):
                                pass
                        if time.monotonic() >= deadline:
                            raise RuntimeError("El entorno E2E no estuvo listo en 60 segundos.")
                        time.sleep(.2)
                    assert_owned(children, groups)
                    state = http("/api/state")
                    assert_zero_budget(state)
                    if state["datasets"] or state["experiments"]:
                        raise RuntimeError("E2E exige una base vacía; no se reutiliza ningún ensayo.")
                    descriptor.update(active=True, children={name: child.pid for name, child in children.items()})
                    atomic_json(directory / "run.json", descriptor)
                    print(f"E2E aislado: {BASE_URL}\nEvidencia: {directory}\nParar: tools/run_e2e.py --stop-run {directory.name}", flush=True)
                    deadline = time.monotonic() + timeout
                    if manual:
                        while not (directory / "stop-request").exists() and time.monotonic() < deadline:
                            assert_owned(children, groups)
                            time.sleep(.2)
                        result = 0
                    else:
                        test_env = {**environment, "ATLAS_E2E_RUN_DIR": str(directory), "ATLAS_E2E_TOKEN": token}
                        command = [node, str(cli), "test", "--config", "playwright.config.ts"]
                        if grep:
                            command.extend(["--grep", grep])
                        test_log = (directory / "playwright.log").open("wb")
                        streams.append(test_log)
                        runner = subprocess.Popen(command, cwd=ROOT / "frontend", env=test_env,
                                                  stdin=subprocess.DEVNULL, stdout=test_log, stderr=subprocess.STDOUT,
                                                  creationflags=subprocess.CREATE_NO_WINDOW)
                        owned.append(runner)
                        runner_group.add(runner)
                        while runner.poll() is None:
                            assert_owned(children, groups)
                            if time.monotonic() >= deadline or (directory / "stop-request").exists():
                                raise RuntimeError("El recorrido E2E superó el plazo o recibió una parada.")
                            time.sleep(.2)
                        result = runner.returncode
                    assert_owned(children, groups)
                    state = http("/api/state")
                    assert_zero_budget(state)
                    descriptor["final_experiments"] = [
                        {key: job.get(key) for key in ("id", "status", "provider", "hours", "spent_usd", "auto_paper")}
                        for job in state["experiments"]]
                finally:
                    # Cancel only jobs in the fresh, positively identified instance,
                    # even when an assertion or the browser fails midway through.
                    if len(children) == 2:
                        try:
                            assert_owned(children, groups)
                            state = http("/api/state")
                            assert_zero_budget(state)
                            for job in state["experiments"]:
                                if job["status"] not in {"cancelled", "completed", "failed"}:
                                    assert_owned(children, groups)
                                    http(f"/api/experiments/{job['id']}/control", {"action": "cancel"})
                        except (OSError, ValueError, RuntimeError) as cleanup_error:
                            descriptor["cleanup_error"] = str(cleanup_error)
                            result = 1
                    (directory / "servers.stop").write_text("E2E finished", encoding="ascii")
                    deadline = time.monotonic() + 22
                    for child in children.values():
                        try:
                            child.wait(timeout=max(.1, deadline - time.monotonic()))
                        except subprocess.TimeoutExpired:
                            forced_stop = True
                    # Also cover assignment failures: a newly created child may
                    # not yet belong to the Job Object, but its Popen is ours.
                    for child in owned:
                        if child.poll() is None:
                            forced_stop = True
                            child.terminate()
                            try:
                                child.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                child.kill()
                                child.wait(timeout=5)
                    if forced_stop:
                        result = 1
                    descriptor["server_exit_codes"] = {name: child.poll() for name, child in children.items()}
                    if any(code != 0 for code in descriptor["server_exit_codes"].values()):
                        result = 1
        except (Exception, KeyboardInterrupt) as exc:
            error = str(exc) or type(exc).__name__
            if isinstance(exc, OwnershipError):
                descriptor['ownership_failure'] = exc.observation
            result = 1
        finally:
            for stream in streams:
                stream.close()
            finish_descriptor(directory, data, descriptor, result=result, error=error, forced_stop=forced_stop)
        print(json.dumps({key: descriptor.get(key) for key in (
            "run_id", "result", "error", "cleanup_error", "ownership_failure", "server_exit_codes",
            "forced_stop", "ordinary_database_unchanged", "ports_released", "integrity")}, ensure_ascii=False), flush=True)
        if (directory / "playwright.log").is_file():
            print((directory / "playwright.log").read_text(encoding="utf-8", errors="replace"), flush=True)
        return descriptor["result"]


def main() -> int:
    # Playwright's failure report contains box-drawing Unicode; legacy Windows
    # console encodings must not replace the real test outcome with a print error.
    sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual", action="store_true", help="Revisión CUA en un entorno nuevo, detenido al terminar el plazo.")
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--grep", help="Seleccionar un recorrido por su título; nunca cambia la base o URL.")
    parser.add_argument("--stop-run", help="Solicitar la parada cooperativa de una ejecución E2E identificada.")
    args = parser.parse_args()
    try:
        if args.stop_run:
            directory = run_directory(args.stop_run)
            descriptor = read_json(directory / "run.json")
            if not descriptor or descriptor.get("root") != str(ROOT) or not descriptor.get("active"):
                raise ValueError("No hay un entorno E2E activo de este proyecto con ese identificador.")
            (directory / "stop-request").write_text("manual stop", encoding="ascii")
            return 0
        timeout = args.timeout if args.timeout is not None else (900 if args.manual else 300)
        if not 30 <= timeout <= (1200 if args.manual else 600):
            raise ValueError("Plazo permitido: 30–600 s automáticos o hasta 1200 s de revisión manual.")
        return run(manual=args.manual, timeout=timeout, grep=args.grep)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"E2E: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
