"""Local supervisor: verified startup, cooperative stop and owned children."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.client import HTTPException
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import webbrowser

from atlas_runtime import InstanceLock, atomic_json, frontend_env, locked, port_open, read_json
from build_frontend import verify_build
from local_http import open_local_http
from process_group import ProcessGroup
from node_runtime import check_node, find_node, node_environment

ROOT = Path(__file__).resolve().parents[1]
VAR = ROOT / "var"
STATE = VAR / "runtime.json"
LOCK = VAR / "atlas.lock"
STOP = VAR / "atlas.stop"
URL = "http://127.0.0.1:3000/"


def child_exit_codes(children, identities):
    """Read only retained Popen handles; never reopen or signal recorded PIDs."""
    names = {pid: name for name, pid in identities.items()}
    exits = {}
    for child in children:
        code = child.poll()
        if code is not None:
            exits[names.get(child.pid, f"pid-{child.pid}")] = code
    return exits


def stop_file(run_id):
    if not isinstance(run_id, str) or len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
        raise RuntimeError("No hay una instancia identificada para detener; puede haber mantenimiento activo.")
    return VAR / f"stop-{run_id}"


def load_env(path, env):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        # Optional local CA bundle for verified HTTPS (e.g. antivirus TLS inspection).
        if separator and key.strip() in {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "REQUESTS_CA_BUNDLE"}:
            env.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def health(port):
    try:
        with open_local_http(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
            if response.status != 200:
                return False
            value = json.load(response)
        return isinstance(value, dict) and value.get("status") == "ok" and value.get("live_available") is False
    except (OSError, HTTPException, ValueError):
        return False


def status():
    value = read_json(STATE)
    active = locked(LOCK)
    if not active:
        return {**value, "status": "failed" if value.get("status") == "failed" else "stopped", "lock_held": False}
    result = {**value, "lock_held": True}
    if value.get("status") == "running" and not all(health(p) for p in (8000, 3000)):
        result["status"] = "unhealthy"
    return result


def stop(timeout):
    if not locked(LOCK):
        print("ATLAS ya está detenido.")
        return 0
    stop_file(read_json(STATE).get("run_id")).write_text("stop", encoding="ascii")
    deadline = time.monotonic() + timeout
    while locked(LOCK) and time.monotonic() < deadline:
        time.sleep(.2)
    if locked(LOCK):
        raise RuntimeError("La parada no terminó dentro del plazo. Revisa var/logs; no se han matado procesos ajenos.")
    if any(port_open(p) for p in (3000, 8000)):
        raise RuntimeError("ATLAS liberó su bloqueo, pero un puerto sigue ocupado. Revisa su propietario.")
    print("ATLAS detenido: motor e interfaz cerrados.")
    return 0


def background(timeout, open_browser):
    if locked(LOCK):
        current = status()
        if current.get("status") == "running":
            print(f"ATLAS ya está funcionando: {URL}")
            if open_browser:
                webbrowser.open(URL)
            return 0
        raise RuntimeError("ATLAS está iniciando, deteniéndose o en mantenimiento. Consulta --status.")
    run_id = uuid.uuid4().hex
    logs = VAR / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / f"launcher-{run_id}.log"
    command = [sys.executable, "-u", str(Path(__file__).resolve()), "--run-id", run_id, "--timeout", str(timeout)]
    if open_browser:
        command.append("--open")
    with log_path.open("ab") as output:
        child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                                 start_new_session=os.name != "nt")
    deadline = time.monotonic() + timeout + 5
    while time.monotonic() < deadline:
        value = read_json(STATE)
        if value.get("run_id") == run_id:
            if value.get("status") == "running" and child.poll() is None:
                print(f"ATLAS funciona: {URL}\nRegistro del lanzador: {log_path}")
                return 0
            if value.get("status") == "failed":
                raise RuntimeError(value.get("error", f"Falló el arranque. Revisa {log_path}"))
        if child.poll() is not None:
            raise RuntimeError(f"El lanzador terminó antes de estar listo. Revisa {log_path}")
        time.sleep(.2)
    if read_json(STATE).get("run_id") == run_id:
        stop_file(run_id).write_text("startup timeout", encoding="ascii")
    raise RuntimeError(f"No se confirmó el arranque. Revisa {log_path}")


def supervise(timeout, open_browser, run_id):
    stop_signal = stop_file(run_id)
    lock = InstanceLock(LOCK)
    if not lock.acquire():
        raise RuntimeError("ATLAS ya está activo o hay otra operación de mantenimiento.")
    info = {"run_id": run_id, "pid": os.getpid(), "status": "starting",
            "started_at": datetime.now(timezone.utc).isoformat(), "url": URL,
            "frontend_mode": "compiled", "children": {}}
    children, streams = [], []
    group, error = None, None

    def record(**fields):
        info.update(fields)
        atomic_json(STATE, info)

    def check_children(phase):
        exits = child_exit_codes(children, info["children"])
        if exits and not stop_signal.exists():
            # Capture the first observed exits BEFORE requesting sibling cleanup.
            # Their later exit codes alone cannot identify the original failure.
            record(unexpected_child_exit={"phase": phase, "exit_codes": exits,
                   "detected_at": datetime.now(timezone.utc).isoformat()})
            details = "; ".join(f"{name}: código {code}"
                + (f" (0x{code & 0xffffffff:08X})" if os.name == "nt" and code else "")
                for name, code in exits.items())
            raise RuntimeError(f"Un servidor terminó durante {phase} ({details}). "
                               "Se detiene la instancia completa; revisa var/logs.")

    try:
        record()
        if sys.version_info < (3, 12):
            raise RuntimeError("Se necesita Python 3.12 o posterior.")
        node = find_node(ROOT)
        if not node:
            raise RuntimeError("Falta Node.js en PATH.")
        record(node_version=check_node(node), node_path=node)
        verify_build(ROOT / "frontend")
        for port in (8000, 3000):
            if port_open(port):
                raise RuntimeError(f"Puerto {port} ocupado. No se modificó el proceso que lo utiliza.")
        sys.path.insert(0, str(ROOT / "backend"))
        from atlas_quant.backup import create_backup, prune_backups
        data = VAR / "atlas/atlas.sqlite3"
        if data.exists():
            saved = create_backup(data, ROOT / "backups/automatic")
            prune_backups(ROOT / "backups/automatic", keep=7)
            record(last_backup=str(saved), last_backup_at=datetime.now(timezone.utc).isoformat())
        environment = os.environ.copy()
        load_env(ROOT / ".env", environment)
        environment.update(ATLAS_DATA_DIR=str(VAR / "atlas"), ATLAS_STOP_FILE=str(stop_signal), PYTHONUTF8="1")
        commands = [
            ("backend", [sys.executable, "-u", str(ROOT / "tools/serve_backend.py")], environment, ROOT),
            ("frontend", [node, str(ROOT / "frontend/local-server.mjs")], frontend_env(node_environment(node, environment)), ROOT / "frontend"),
        ]
        group = ProcessGroup()
        for name, command, env, cwd in commands:
            output = VAR / "logs" / f"{name}.log"
            output.parent.mkdir(parents=True, exist_ok=True)
            stream = output.open("ab")
            streams.append(stream)
            stream.write((f"\n[ATLAS] run_id={run_id} server={name} "
                          f"started_at={datetime.now(timezone.utc).isoformat()}\n").encode("utf-8"))
            stream.flush()
            child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                     stdout=stream, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            children.append(child)
            info["children"][name] = child.pid
            group.add(child)
        record()
        deadline = time.monotonic() + timeout
        while not stop_signal.exists():
            check_children("el arranque")
            if stop_signal.exists():
                break
            if all(health(p) for p in (8000, 3000)):
                with open_local_http(URL, timeout=10) as response:
                    if response.status != 200:
                        raise RuntimeError("La interfaz no responde correctamente.")
                record(status="running")
                print(f"ATLAS funcionando: {URL}", flush=True)
                if open_browser:
                    webbrowser.open(URL)
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("El motor o la interfaz no alcanzó un estado saludable. Revisa var/logs.")
            time.sleep(.2)
        next_health, next_backup = time.monotonic() + 10, time.monotonic() + 24 * 3600
        failures = 0
        while not stop_signal.exists():
            check_children("la ejecución")
            if stop_signal.exists():
                break
            if time.monotonic() >= next_health:
                failures = 0 if all(health(p) for p in (8000, 3000)) else failures + 1
                record(health_checked_at=datetime.now(timezone.utc).isoformat(), health_failures=failures)
                if failures >= 3:
                    raise RuntimeError("Tres comprobaciones de salud fallaron. Se detiene ATLAS sin repetir trabajos.")
                next_health = time.monotonic() + 10
            if time.monotonic() >= next_backup:
                saved = create_backup(data, ROOT / "backups/automatic")
                prune_backups(ROOT / "backups/automatic", keep=7)
                record(last_backup=str(saved), last_backup_at=datetime.now(timezone.utc).isoformat())
                next_backup = time.monotonic() + 24 * 3600
            time.sleep(.2)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        error = str(exc)
    finally:
        # Diagnostics must never prevent cleanup (e.g. a full disk).
        try:
            record(status="stopping")
        except OSError:
            pass
        try:
            stop_signal.write_text("stop", encoding="ascii")
        except OSError:
            pass
        forced = False
        try:
            deadline = time.monotonic() + 20
            for child in children:
                try:
                    child.wait(timeout=max(.1, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    forced = True
                    child.terminate()
            for child in children:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    forced = True
                    child.kill()
                    child.wait(timeout=5)
        finally:
            try:
                if group:
                    group.close()
            finally:
                for stream in streams:
                    stream.close()
                try:
                    record(status="failed" if error else "stopped", error=error, forced_stop=forced,
                           child_exit_codes=child_exit_codes(children, info["children"]),
                           stopped_at=datetime.now(timezone.utc).isoformat())
                finally:
                    try:
                        # runtime.json describes only the latest run. Preserve the
                        # original exit evidence before another startup replaces it.
                        atomic_json(VAR / "logs" / f"runtime-{run_id}.json", info)
                    except OSError as archive_error:
                        # An unwritable archive must not hide the server failure
                        # or prevent releasing the instance lock after cleanup.
                        try:
                            print(f"ATLAS: No se pudo archivar el diagnóstico de {run_id}: "
                                  f"{archive_error}", file=sys.stderr, flush=True)
                        except OSError:
                            pass  # The launcher log can be on the same full disk.
                    finally:
                        lock.release()
    if error:
        raise RuntimeError(error)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--background", action="store_true")
    mode.add_argument("--stop", action="store_true")
    mode.add_argument("--status", action="store_true")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--run-id", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 5 <= args.timeout <= 300:
        parser.error("El plazo debe estar entre 5 y 300 segundos.")
    VAR.mkdir(exist_ok=True)
    try:
        if args.status:
            value = status()
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0 if value.get("status") == "running" else 1
        if args.stop:
            return stop(args.timeout)
        if args.background:
            return background(args.timeout, args.open)
        return supervise(args.timeout, args.open, args.run_id or uuid.uuid4().hex)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"ATLAS: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
