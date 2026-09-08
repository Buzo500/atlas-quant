"""Read-only Windows release soak; never starts, stops or mutates ATLAS itself."""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid

from atlas_runtime import InstanceLock, atomic_json, locked, read_json
from local_http import open_local_http

ROOT = Path(__file__).resolve().parents[1]
TERMINAL_SUCCESS = "completion_requires_restart_check"
VOLATILE_EXPERIMENT = {"status", "phase", "observation", "gate", "finished_at", "completion_note",
                       "execution_token", "execution_active", "updated_at"}
ERROR_LINE = re.compile(r"^\s*(?:ERROR\b|FATAL\b|Error:|Traceback \(most recent call last\):)", re.M)


def timestamp(value=None):
    return datetime.fromtimestamp(time.time() if value is None else value, timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, allow_nan=False,
                                     sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Limits:
    duration_seconds: float = 48 * 3600
    interval_seconds: float = 60
    max_gap_seconds: float = 90
    max_clock_drift_seconds: float = 5
    max_rss_bytes: int = 4 * 1024**3
    max_rss_growth_bytes: int = 1024**3
    max_cpu_percent: float = 80
    resource_consecutive_samples: int = 5
    max_log_growth_bytes: int = 512 * 1024**2
    min_free_bytes: int = 1024**3
    max_backup_age_seconds: float = 25 * 3600
    integrity_interval_seconds: float = 15 * 60


class Detector:
    """Explicit consecutive-time criteria, independent of real clocks and probes."""

    def __init__(self, limits):
        self.limits = limits
        self.previous = None
        self.accepted_seconds = 0.0
        self.samples = 0
        self.resource_streak = 0
        self.initial_rss = None

    def accept(self, sample):
        issues = list(sample["issues"])
        increment = 0
        if self.previous:
            wall = sample["wall"] - self.previous["wall"]
            monotonic = sample["monotonic"] - self.previous["monotonic"]
            if wall <= 0 or monotonic <= 0:
                issues.append("clock_reversed")
            if max(wall, monotonic) > self.limits.max_gap_seconds:
                issues.append("sampling_gap_or_suspend")
            if abs(wall - monotonic) > self.limits.max_clock_drift_seconds:
                issues.append("clock_discontinuity")
            increment = max(0, min(wall, monotonic))
        rss = sample.get("rss_bytes", 0)
        if self.initial_rss is None:
            self.initial_rss = rss
        over_resource = (rss > self.limits.max_rss_bytes
                         or rss - self.initial_rss > self.limits.max_rss_growth_bytes
                         or sample.get("cpu_percent", 0) > self.limits.max_cpu_percent)
        self.resource_streak = self.resource_streak + 1 if over_resource else 0
        if self.resource_streak >= self.limits.resource_consecutive_samples:
            issues.append("sustained_resource_threshold")
        if not issues:
            self.accepted_seconds += increment
        self.previous = sample
        self.samples += 1
        return sorted(set(issues))


class AwakeRequest:
    """Temporary idle-sleep request owned by this thread; no power-plan edits."""

    def __init__(self, enabled=False, api=None):
        self.enabled, self.api, self.active = enabled, api, False

    def __enter__(self):
        if not self.enabled:
            return self
        if self.api is None:
            if os.name != "nt":
                raise RuntimeError("--keep-awake necesita Windows nativo.")
            import ctypes
            from ctypes import wintypes
            self.api = ctypes.WinDLL("kernel32", use_last_error=True).SetThreadExecutionState
            self.api.argtypes = [wintypes.DWORD]
            self.api.restype = wintypes.DWORD
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED. Display sleep and manual sleep
        # are unaffected; Windows removes the request when this thread exits.
        if not self.api(0x80000001):
            raise RuntimeError("Windows rechazó la solicitud temporal de mantener el sistema despierto.")
        self.active = True
        return self

    def __exit__(self, *exc):
        if self.active:
            if not self.api(0x80000000):  # ES_CONTINUOUS releases this thread's requirement.
                raise RuntimeError("Windows no confirmó la liberación de la solicitud de vigilia.")
            self.active = False


def git_identity(root, candidate):
    flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(root), *arguments], text=True,
                                       stderr=subprocess.PIPE, timeout=15, **flags).strip()
    head = git("rev-parse", "HEAD")
    if head != candidate:
        raise RuntimeError("La candidata solicitada no corresponde a HEAD.")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise RuntimeError("La candidata tiene cambios locales sin identificar en Git.")
    return head


def database_snapshot(path, *, full_integrity=False, audit_prefix_count=None):
    """Read a coherent transaction, including WAL, without creating/migrating a DB."""
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        if full_integrity and db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise RuntimeError("SQLite integrity_check no es correcto.")
        records = [(kind, ident, json.loads(body)) for kind, ident, body in
                   db.execute("SELECT kind,id,body FROM records ORDER BY kind,id")]
        versions = [(ident, version, json.loads(body)) for ident, version, body in
                    db.execute("SELECT dataset_id,version,body FROM versions ORDER BY dataset_id,version")]
        audit = list(db.execute("SELECT seq,at,event,entity,details FROM audit ORDER BY seq"))
        schema = db.execute("PRAGMA user_version").fetchone()[0]
    issues = []
    stable = []
    experiments, datasets = {}, []
    for kind, ident, body in records:
        if kind == "dataset":
            datasets.append(ident)
            if body.get("source_kind") != "synthetic" or body.get("feed"):
                issues.append("non_demo_dataset_or_network_feed")
        if kind == "experiment":
            experiments[ident] = {key: body.get(key) for key in
                                   ("status", "provider", "budget_usd", "spent_usd", "reserved_usd")}
            if body.get("provider") != "none" or any(body.get(key) != 0 for key in
                                                      ("budget_usd", "spent_usd", "reserved_usd")):
                issues.append("provider_or_budget_nonzero")
            if body.get("auto_paper") is not False or body.get("paper_account"):
                issues.append("paper_not_disabled")
            if body.get("status") not in {"observing", "completed"}:
                issues.append("unexpected_experiment_status")
            body = {key: value for key, value in body.items() if key not in VOLATILE_EXPERIMENT}
        stable.append((kind, ident, body))
    if not datasets or not experiments:
        issues.append("demo_and_settled_experiment_required")
    prefix = audit if audit_prefix_count is None else audit[:audit_prefix_count]
    return {"schema": schema, "persistent_digest": digest([schema, stable, versions]),
            "audit_count": len(audit), "audit_prefix_digest": digest(prefix),
            "dataset_ids": datasets, "experiments": experiments, "issues": issues,
            "full_integrity": full_integrity}


def http_read(url, *, json_response=False):
    started = time.perf_counter()
    with open_local_http(url, timeout=5) as response:
        payload = response.read(8 * 1024**2 + 1)
        if response.status != 200 or len(payload) > 8 * 1024**2:
            raise RuntimeError("Respuesta HTTP no válida o excesiva.")
    return (json.loads(payload) if json_response else payload), round(time.perf_counter() - started, 4)


def probe_http(version=None):
    timings, healths = {}, {}
    for port in (8000, 3000):
        value, timings[str(port)] = http_read(f"http://127.0.0.1:{port}/api/health", json_response=True)
        if value.get("status") != "ok" or value.get("live_available") is not False or value.get("mode") != "local":
            raise RuntimeError(f"Salud incorrecta en el puerto {port}.")
        healths[str(port)] = value
    if healths["8000"] != healths["3000"] or (version and healths["8000"].get("version") != version):
        raise RuntimeError("API/proxy difieren o la versión ha cambiado.")
    page, timings["page"] = http_read("http://127.0.0.1:3000/")
    if b"<html" not in page.lower():
        raise RuntimeError("La interfaz no devuelve HTML.")
    assets = re.findall(rb'(?:src|href)="(/[^"?#]+\.(?:js|css))', page)
    if not assets:
        raise RuntimeError("La interfaz no contiene recursos compilados reconocibles.")
    _, timings["asset"] = http_read("http://127.0.0.1:3000" + assets[0].decode())
    state, timings["state"] = http_read("http://127.0.0.1:3000/api/state", json_response=True)
    if state["settings"].get("kill_switch") is not True or any(p.get("configured") for p in state["providers"]):
        raise RuntimeError("Se requieren parada global activa y proveedores sin claves.")
    portfolios = {}
    for dataset in state["datasets"]:
        value, _ = http_read(f"http://127.0.0.1:3000/api/datasets/{dataset['id']}/portfolio", json_response=True)
        portfolios[dataset["id"]] = digest(value)
    return {"version": healths["8000"]["version"], "timings_seconds": timings,
            "portfolio_digests": portfolios}


def windows_resources(pids):
    """Measure anchors and descendants, including Windows venv redirectors.

    Each PID is counted once even when an anchor is another anchor's child.
    Creation times reject children whose recorded parent PID has been reused.
    No process is signalled, suspended or terminated.
    """
    if os.name != "nt":
        raise RuntimeError("Este ensayo mide recursos de Windows nativo.")
    import ctypes
    from ctypes import wintypes
    class Memory(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]
    class Entry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Memory), wintypes.DWORD]
    def ticks(value):
        return (value.dwHighDateTime << 32) | value.dwLowDateTime
    parents = {}
    snapshot = kernel.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        if not more:
            raise ctypes.WinError(ctypes.get_last_error())
        while more:
            parents[entry.th32ProcessID] = entry.th32ParentProcessID
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(snapshot)

    def measure(name, pid):
        handle = kernel.OpenProcess(0x1000 | 0x0010, False, pid)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            created, exited, system, user = (wintypes.FILETIME() for _ in range(4))
            memory = Memory()
            memory.cb = ctypes.sizeof(memory)
            exit_code = wintypes.DWORD()
            if (not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)) or exit_code.value != 259
                    or not kernel.GetProcessTimes(handle, *[ctypes.byref(v) for v in (created, exited, system, user)])
                    or not psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb)):
                raise RuntimeError(f"No se pudo medir el proceso activo {name}.")
            return {"pid": pid, "parent_pid": parents.get(pid), "creation_ticks": ticks(created),
                    "rss_bytes": memory.WorkingSetSize,
                    "cpu_seconds": (ticks(system) + ticks(user)) / 10_000_000}
        finally:
            kernel.CloseHandle(handle)

    values = {name: measure(name, pid) for name, pid in pids.items()}
    known = {value["pid"]: name for name, value in values.items()}
    if len(known) != len(pids):
        raise RuntimeError("Los PID raíz no identifican procesos distintos.")
    while True:
        added = False
        for pid, parent in parents.items():
            if pid in known or parent not in known:
                continue
            parent_name = known[parent]
            name = f"{parent_name}/descendant-{pid}"
            measured = measure(name, pid)
            if measured["creation_ticks"] < values[parent_name]["creation_ticks"]:
                continue  # Not a child of this incarnation of the parent PID.
            values[name] = measured
            known[pid] = name
            added = True
        if not added:
            break
    return values


class LogReader:
    def __init__(self, paths):
        self.offsets = {str(path): path.stat().st_size if path.exists() else 0 for path in paths}
        self.initial_bytes = sum(self.offsets.values())
        self.partial = {path: "" for path in self.offsets}

    def sample(self):
        sizes, errors = {}, 0
        for name, offset in self.offsets.items():
            path = Path(name)
            size = path.stat().st_size if path.exists() else 0
            if size < offset:
                raise RuntimeError("Un registro fue truncado durante el ensayo.")
            if size - offset > 8 * 1024**2:
                raise RuntimeError("Más de 8 MiB de log nuevos en una muestra.")
            payload = b""
            if path.exists():
                with path.open("rb") as stream:
                    stream.seek(offset)
                    payload = stream.read(size - offset)
            self.offsets[name] = size
            text = self.partial[name] + payload.decode("utf-8", errors="replace")
            lines = text.splitlines(keepends=True)
            self.partial[name] = lines.pop() if lines and not lines[-1].endswith(("\n", "\r")) else ""
            # Include a final line without newline: an idle process need not
            # append again after logging an error.
            errors += len(ERROR_LINE.findall(text))
            sizes[name] = size
        return {"sizes_bytes": sizes, "growth_bytes": sum(sizes.values()) - self.initial_bytes,
                "new_error_lines": errors}


class Probe:
    def __init__(self, root, candidate, run_id, limits):
        self.root, self.candidate, self.run_id, self.limits = root, candidate, run_id, limits
        self.started_wall = time.time()
        self.baseline = None
        self.version = None
        self.portfolios = None
        self.process_identity = None
        self.previous_resources = None
        self.last_integrity = -float("inf")
        self.backups = {}
        self.logs = LogReader([root / "var/logs" / name for name in
                               ("backend.log", "frontend.log", f"launcher-{run_id}.log")])

    def sample(self):
        sample = {"wall": time.time(), "monotonic": time.monotonic(), "issues": []}
        try:
            git_identity(self.root, self.candidate)
            state = read_json(self.root / "var/runtime.json")
            sample["runtime"] = state
            if state.get("run_id") != self.run_id or state.get("status") != "running" or not locked(self.root / "var/atlas.lock"):
                raise RuntimeError("La instancia identificada terminó, cambió o dejó de estar en ejecución.")
            if state.get("health_failures", 0) or state.get("unexpected_child_exit"):
                raise RuntimeError("El supervisor registró un fallo de salud o salida inesperada.")
            full = sample["monotonic"] - self.last_integrity >= self.limits.integrity_interval_seconds
            database = database_snapshot(self.root / "var/atlas/atlas.sqlite3", full_integrity=full,
                                        audit_prefix_count=self.baseline["audit_count"] if self.baseline else None)
            if full:
                self.last_integrity = sample["monotonic"]
            sample["database"] = database
            sample["issues"].extend(database["issues"])
            if self.baseline and (database["persistent_digest"] != self.baseline["persistent_digest"]
                    or database["audit_prefix_digest"] != self.baseline["audit_prefix_digest"]
                    or database["audit_count"] < self.baseline["audit_count"]):
                raise RuntimeError("El contenido persistente cambió o se perdió auditoría previa.")
            self.baseline = self.baseline or database
            sample["http"] = probe_http(self.version)
            self.version = self.version or sample["http"]["version"]
            if self.portfolios is not None and self.portfolios != sample["http"]["portfolio_digests"]:
                raise RuntimeError("La cartera expuesta por API cambió.")
            self.portfolios = sample["http"]["portfolio_digests"]
            pids = {"supervisor": state["pid"], **state["children"]}
            if set(pids) != {"supervisor", "backend", "frontend"}:
                raise RuntimeError("Falta la identidad de alguno de los procesos esperados.")
            resources = windows_resources(pids)
            identity = {name: (value["pid"], value["creation_ticks"]) for name, value in resources.items()}
            if self.process_identity is not None and identity != self.process_identity:
                raise RuntimeError("Un proceso cambió o su PID fue reutilizado.")
            self.process_identity = identity
            cpu = sum(value["cpu_seconds"] for value in resources.values())
            sample["resources"] = resources
            sample["rss_bytes"] = sum(value["rss_bytes"] for value in resources.values())
            sample["cpu_percent"] = 0
            if self.previous_resources:
                before, moment = self.previous_resources
                sample["cpu_percent"] = max(0, (cpu - before) / max(.001, sample["monotonic"] - moment)
                                            / (os.cpu_count() or 1) * 100)
            self.previous_resources = (cpu, sample["monotonic"])
            sample["logs"] = self.logs.sample()
            if sample["logs"]["new_error_lines"] or sample["logs"]["growth_bytes"] > self.limits.max_log_growth_bytes:
                raise RuntimeError("Hay errores nuevos en logs o crecimiento superior al umbral.")
            sample["free_bytes"] = shutil.disk_usage(self.root).free
            if sample["free_bytes"] < self.limits.min_free_bytes:
                raise RuntimeError("El espacio libre es inferior al mínimo declarado.")
            backup = Path(state["last_backup"]).resolve()
            if not backup.is_relative_to((self.root / "backups/automatic").resolve()):
                raise RuntimeError("La última copia no pertenece al directorio automático esperado.")
            if str(backup) not in self.backups:
                sys.path.insert(0, str(self.root / "backend"))
                from atlas_quant.backup import validate_backup
                manifest = validate_backup(backup)
                copied = database_snapshot(backup / "atlas.sqlite3", full_integrity=True,
                                           audit_prefix_count=self.baseline["audit_count"])
                # Startup backup may precede lifecycle recovery, which is omitted
                # from the persistence digest; economic content must be identical.
                if copied["persistent_digest"] != self.baseline["persistent_digest"]:
                    raise RuntimeError("La copia automática no conserva el contenido del ensayo.")
                self.backups[str(backup)] = {"created_at": manifest["created_at"],
                                            "sha256": manifest["sha256"], "validated_at": timestamp()}
            sample["backup"] = {"path": str(backup), **self.backups[str(backup)]}
            age = sample["wall"] - datetime.fromisoformat(sample["backup"]["created_at"]).timestamp()
            if age < -self.limits.max_clock_drift_seconds or age > self.limits.max_backup_age_seconds:
                raise RuntimeError("La copia automática está ausente, caducada o tiene fecha futura.")
            # Catch a shutdown or swap that happened during this sample.
            latest = read_json(self.root / "var/runtime.json")
            if latest.get("run_id") != self.run_id or latest.get("status") != "running":
                raise RuntimeError("La instancia terminó durante la comprobación.")
        except Exception as exc:
            sample["issues"].append(f"{type(exc).__name__}: {exc}")
        sample["at"] = timestamp(sample["wall"])
        sample["probe_seconds"] = time.monotonic() - sample["monotonic"]
        return sample


def run_monitor(probe, output, limits, *, keep_awake=False, wall=time.time,
                monotonic=time.monotonic, sleep=time.sleep):
    """No resume: a stopped/lost monitor cannot certify the unobserved interval."""
    output.mkdir(parents=True, exist_ok=False)
    summary = {"format_version": 1, "status": "running", "monitor_pid": os.getpid(),
               "candidate_commit": probe.candidate, "runtime_run_id": probe.run_id,
               "root": str(probe.root), "started_at": timestamp(wall()), "limits": asdict(limits),
               "environment": {"platform": platform.platform(), "python": sys.version,
                               "logical_cpu_count": os.cpu_count()},
               "scope": "demo observation; HTTP/UI assets; no interactive browser regression or new market data",
               "restart_check": "pending", "samples": 0, "accepted_seconds": 0,
               "issues": [], "automatic_backups": {}, "keep_awake": keep_awake,
               "keep_awake_active": False}
    detector = Detector(limits)
    next_sample = monotonic()
    awake = AwakeRequest(keep_awake)
    try:
        with InstanceLock(output / "monitor.lock"), awake:
            summary["keep_awake_active"] = awake.active
            atomic_json(output / "summary.json", summary)
            while True:
                if (output / "stop.request").exists():
                    summary.update(status="stopped", issues=["monitor_stop_requested"])
                    break
                if monotonic() < next_sample:
                    sleep(min(1, next_sample - monotonic()))
                    continue
                sample = probe.sample()
                issues = detector.accept(sample)
                sample["issues"] = issues
                with (output / "samples.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(sample, ensure_ascii=False, allow_nan=False) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                summary.update(last_sample_at=sample["at"], version=probe.version,
                               samples=detector.samples, accepted_seconds=detector.accepted_seconds,
                               issues=issues, automatic_backups=probe.backups,
                               persistence_baseline=probe.baseline, latest_sample=sample)
                if issues:
                    summary["status"] = "failed"
                    break
                if detector.accepted_seconds >= limits.duration_seconds:
                    later_backups = [value for value in probe.backups.values()
                                     if datetime.fromisoformat(value["created_at"]).timestamp() > probe.started_wall]
                    if limits.duration_seconds >= limits.max_backup_age_seconds and not later_backups:
                        summary.update(status="failed", issues=["no_automatic_backup_during_soak"])
                    else:
                        summary["status"] = TERMINAL_SUCCESS
                    break
                atomic_json(output / "summary.json", summary)
                next_sample = sample["monotonic"] + limits.interval_seconds
    except KeyboardInterrupt:
        summary.update(status="stopped", issues=["monitor_interrupted"])
    except Exception as exc:
        summary.update(status="failed", issues=[f"monitor_exception: {type(exc).__name__}: {exc}"])
    summary["keep_awake_active"] = awake.active
    summary["finished_at"] = timestamp(wall())
    atomic_json(output / "summary.json", summary)
    return 0 if summary["status"] == TERMINAL_SUCCESS else 1


def monitor_status(output):
    summary = read_json(output / "summary.json")
    if summary.get("status") == "running":
        age = time.time() - datetime.fromisoformat(summary.get("last_sample_at", summary["started_at"])).timestamp()
        summary["monitor_lock_held"] = locked(output / "monitor.lock")
        summary["last_sample_age_seconds"] = age
        if not summary["monitor_lock_held"] or age > summary["limits"]["max_gap_seconds"]:
            summary["status"] = "monitor_lost_or_stale"
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "status", "stop"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--candidate")
    parser.add_argument("--run-id")
    parser.add_argument("--keep-awake", action="store_true",
                        help="Solicitar vigilia temporal mientras vive el monitor; no cambia el plan de energía.")
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.output or root / "output/validation" / ("soak-" + uuid.uuid4().hex)).resolve()
    if not output.is_relative_to(root / "output/validation") or output == root / "output/validation":
        parser.error("La evidencia debe quedar en una subcarpeta ignorada de output/validation.")
    if args.action != "run" and args.output is None:
        parser.error("status/stop requieren --output.")
    try:
        if args.action == "status":
            value = monitor_status(output)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0 if value.get("status") in {"running", TERMINAL_SUCCESS} else 1
        if args.action == "stop":
            if not (output / "summary.json").is_file():
                raise RuntimeError("No existe evidencia de ese monitor.")
            (output / "stop.request").write_text("stop monitor only", encoding="ascii")
            print("Parada del monitor solicitada. ATLAS no se modifica.")
            return 0
        if not args.candidate or not re.fullmatch(r"[0-9a-f]{40}", args.candidate):
            parser.error("run requiere --candidate con el hash Git completo.")
        if not args.run_id or not re.fullmatch(r"[0-9a-f]{32}", args.run_id):
            parser.error("run requiere --run-id de la instancia real.")
        git_identity(root, args.candidate)
        limits = Limits()
        print(f"Evidencia del ensayo: {output}", flush=True)
        return run_monitor(Probe(root, args.candidate, args.run_id, limits), output, limits,
                           keep_awake=args.keep_awake)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Ensayo ATLAS: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
