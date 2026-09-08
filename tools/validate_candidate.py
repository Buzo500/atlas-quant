"""Validate a committed Windows candidate in a new, disposable local clone.

The installer downloads pinned packages; application checks only use loopback
and synthetic data. No environment file or installed dependency is copied.
Evidence and command logs stay under --work-dir, which must not exist initially.
This is a short release walkthrough, not a browser test or a sustained trial.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request


BASE = "http://127.0.0.1:3000"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def clean_environment(environ):
    # Never inherit paid credentials or route application data outside the clone.
    blocked = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ATLAS_DATA_DIR", "PYTHONPATH", "PYTHONHOME"}
    return {**{k: v for k, v in environ.items() if k.upper() not in blocked}, "PYTHONUTF8": "1"}


def snapshot(path):
    """Read a coherent snapshot without opening the application or migrating it."""
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("BEGIN")
        require(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "Integridad SQLite fallida.")
        return {
            "schema": db.execute("PRAGMA user_version").fetchone()[0],
            "records": {(kind, ident): json.loads(body) for kind, ident, body
                        in db.execute("SELECT kind,id,body FROM records")},
            "versions": [(ident, version, json.loads(body)) for ident, version, body
                         in db.execute("SELECT dataset_id,version,body FROM versions ORDER BY dataset_id,version")],
        }


def stable_content(value):
    """Compare complete financial/research content, excluding live lifecycle fields."""
    lifecycle = {"status", "phase", "observation", "gate", "forward_result", "error", "updated_at",
                 "execution_active", "execution_token", "control_requested", "resume_status",
                 "restored_previous_status", "finished_at", "completion_note"}
    records = []
    for (kind, ident), record in sorted(value["records"].items()):
        if kind == "experiment":
            record = {key: item for key, item in record.items() if key not in lifecycle}
        records.append([kind, ident, record])
    return {"records": records, "versions": value["versions"]}


def require_demo_only(value):
    for (kind, _), record in value["records"].items():
        if kind == "experiment":
            require(record.get("provider") == "none" and not record.get("auto_paper")
                    and record.get("paper_account") is None
                    and all(record.get(k, 0) == 0 for k in ("budget_usd", "spent_usd", "reserved_usd")),
                    "La base de prueba debe usar provider none y presupuesto/gasto/reserva cero, sin paper.")
        if kind == "dataset":
            require(record.get("source_kind") == "synthetic" and not record.get("feed"),
                    "La base de prueba solo admite datos sintéticos y ninguna fuente automática.")
        if kind == "settings":
            require(record.get("kill_switch") is True, "La parada global debe estar activada.")


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        path = attrs.get("src") if tag == "script" else attrs.get("href") if tag == "link" else None
        if path and path.startswith("/") and not path.startswith("//") and path.split("?")[0].endswith((".js", ".css")):
            self.urls.add(path)


class Walkthrough:
    def __init__(self, work_dir, source, commit, legacy):
        self.work = work_dir.resolve()
        self.source = source.resolve()
        self.clone = self.work / "candidate install"
        self.database = self.clone / "var/atlas/atlas.sqlite3"
        self.commit = commit
        self.legacy = legacy.resolve()
        self.env = clean_environment(os.environ)
        self.started = False
        self.report = {"started_at": datetime.now(timezone.utc).isoformat(),
                       "source_root": str(self.source), "clone": str(self.clone), "checks": {}, "commands": [],
                       "browser_interactions": "not_tested", "sustained_trial": "not_tested"}

    def save(self):
        target = self.work / "evidence.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)

    def command(self, label, command, *, expected=0, timeout=1200, cwd=None):
        log = self.work / f"{len(self.report['commands']):02d}-{label}.log"
        print(f"ATLAS candidata: {label}", flush=True)
        started = time.monotonic()
        with log.open("w", encoding="utf-8") as output:
            result = subprocess.run([str(item) for item in command], cwd=cwd or self.work, env=self.env,
                                    stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                    timeout=timeout,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.report["commands"].append({"label": label, "args": [str(item) for item in command],
                                        "exit_code": result.returncode, "seconds": round(time.monotonic() - started, 3),
                                        "log": str(log)})
        self.save()
        require(result.returncode == expected if expected is not None else result.returncode != 0,
                f"Resultado inesperado en {label}; consulta {log}.")
        return log.read_text(encoding="utf-8")

    def powershell(self, name, *args, **kwargs):
        return self.command(name.removesuffix(".ps1").lower(),
                            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             self.clone / name, *args], **kwargs)

    def python(self, label, script, *args, **kwargs):
        return self.command(label, [self.clone / ".venv/Scripts/python.exe", self.clone / script, *args], **kwargs)

    @staticmethod
    def ports_free():
        for port in (3000, 8000):
            with socket.socket() as probe:
                probe.settimeout(0.3)
                require(probe.connect_ex(("127.0.0.1", port)) != 0,
                        f"Puerto {port} ocupado; detén ATLAS antes de validar. No se ha detenido ningún proceso.")

    def request(self, path, body=None, *, headers=None, expected=200, raw=False):
        payload = None if body is None else json.dumps(body).encode()
        defaults = {"Content-Type": "application/json", "X-Atlas-Client": "local-v1", "Origin": BASE}
        request = urllib.request.Request(BASE + path, data=payload, headers=defaults if headers is None else headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            response = opener.open(request, timeout=45)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            content = response.read()
            require(response.status == expected, f"{path}: HTTP {response.status}, esperado {expected}.")
        return content if raw else json.loads(content)

    def start(self):
        self.ports_free()
        self.started = True  # Also clean up a partially successful startup.
        self.powershell("Start-Atlas.ps1", timeout=120)
        state = json.loads(self.powershell("Status-Atlas.ps1", timeout=30))
        require(state["status"] == "running" and state["lock_held"], "La candidata no está funcionando.")
        return state

    def stop(self):
        self.powershell("Stop-Atlas.ps1", timeout=120)
        self.started = False
        self.ports_free()
        state = json.loads((self.clone / "var/runtime.json").read_text(encoding="utf-8"))
        require(state["status"] == "stopped" and not state.get("forced_stop") and not state.get("error"),
                "La parada no fue limpia.")
        return state

    def prepare(self):
        require(os.name == "nt", "Este recorrido comprueba los lanzadores nativos de Windows.")
        require(not self.work.exists() and not self.work.is_symlink(), "--work-dir debe ser un directorio nuevo.")
        require(not self.source.is_relative_to(self.work), "El destino no puede contener el repositorio de origen.")
        self.ports_free()
        legacy = snapshot(self.legacy)
        require(legacy["schema"] == 0, "La copia de actualización debe proceder del esquema v0.1 (0).")
        require_demo_only(legacy)
        self.work.mkdir(parents=True)
        resolved = self.command("resolve-commit", ["git", "-C", self.source, "rev-parse", "--verify", "--end-of-options",
                                                   self.commit + "^{commit}"]).strip()
        require(len(resolved) in (40, 64), "Git no devolvió un commit completo.")
        self.report["candidate_commit"] = resolved
        self.command("clone", ["git", "clone", "--local", "--no-checkout", self.source, self.clone])
        self.command("checkout", ["git", "-C", self.clone, "checkout", "--detach", resolved])
        for relative in (".env", ".venv", "frontend/node_modules", "var/atlas/atlas.sqlite3"):
            require(not (self.clone / relative).exists(), f"El clon no está limpio: {relative}.")
        self.report["checks"]["clean_clone"] = True
        self.report["legacy_source"] = {"path": str(self.legacy), "schema": 0,
                                        "content_sha256": digest(stable_content(legacy))}
        self.save()

    def clean_install(self):
        self.powershell("Install-Atlas.ps1")
        self.python("build-check", "tools/build_frontend.py", "--check")
        first = self.start()
        self.powershell("Start-Atlas.ps1", timeout=120)
        require(json.loads(self.powershell("Status-Atlas.ps1"))["run_id"] == first["run_id"],
                "El doble arranque creó otra instancia.")
        health = self.request("/api/health")
        require(health["status"] == "ok" and health["live_available"] is False, "Salud/proxy inválidos.")
        html = self.request("/", raw=True).decode()
        require("/@vite/client" not in html and "@react-refresh" not in html, "La página usa desarrollo/HMR.")
        assets = Assets()
        assets.feed(html)
        require(bool(assets.urls), "No hay recursos compilados en el HTML.")
        for asset in sorted(assets.urls):
            require(bool(self.request(asset, raw=True)), f"Recurso vacío: {asset}.")
        self.request("/api/datasets/demo", {}, headers={"Content-Type": "application/json"}, expected=403)
        self.request("/api/datasets/demo", {}, headers={"X-Atlas-Client": "local-v1", "Origin": "https://example.invalid"}, expected=403)
        state = self.request("/api/state")
        require(not state["datasets"] and not state["experiments"], "La instalación limpia ya tiene datos.")
        require(all(not p["configured"] for p in state["providers"]), "Hay proveedores configurados.")
        self.request("/api/settings", {"kill_switch": True,
                                       "max_position_weight": state["settings"]["max_position_weight"]})
        self.python("demo-smoke", "tools/smoke_local.py")
        smoke = json.loads((self.clone / "output/validation/runtime_v01.json").read_text(encoding="utf-8"))
        research = self.request("/api/research", {"dataset_id": smoke["dataset_id"], "symbol": "DEMO_BOND"})
        require(len(research["candidate_results"]) == 3 and len(research["sensitivity"]) == 3,
                "El Laboratorio no devolvió candidatos y sensibilidad esperados.")
        ident = smoke["experiment_id"]
        job = self.request(f"/api/experiments/{ident}/control", {"action": "pause"})
        require(job["status"] == "paused", "Pausa no aplicada.")
        deadline = time.monotonic() + 30
        while job.get("execution_active") and time.monotonic() < deadline:
            time.sleep(0.2)
            job = self.request(f"/api/experiments/{ident}")
        require(not job.get("execution_active"), "La pausa no terminó la operación activa.")
        job = self.request(f"/api/experiments/{ident}/control", {"action": "resume"})
        require(job["status"] == "observing", "Reanudación no conservó observación.")
        require(self.request(f"/api/experiments/{ident}/report")["id"] == ident, "Informe no disponible.")
        self.report["checks"]["clean_install"] = {"smoke": smoke, "compiled_assets": len(assets.urls),
                                                   "local_guard": True, "pause_resume": True, "laboratory": True}
        self.restore_walkthrough(ident, smoke["dataset_id"])

    def restore_walkthrough(self, ident, dataset_id):
        before = snapshot(self.database)
        require_demo_only(before)
        portfolio = self.request(f"/api/datasets/{dataset_id}/portfolio")
        backup = Path(json.loads(self.python("backup", "tools/backup_atlas.py"))["backup"])
        self.python("verify-backup", "tools/backup_atlas.py", "--verify", backup)
        self.python("reject-active-restore", "tools/backup_atlas.py", "--restore", backup, expected=None)
        require(stable_content(snapshot(self.database)) == stable_content(before), "Restauración activa alteró datos.")
        self.stop()
        bad = self.work / "corrupt-backup"
        shutil.copytree(backup, bad)
        manifest = json.loads((bad / "manifest.json").read_text(encoding="utf-8"))
        manifest["sha256"] = "0" * 64
        (bad / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.python("reject-corrupt-restore", "tools/backup_atlas.py", "--restore", bad, expected=None)
        require(stable_content(snapshot(self.database)) == stable_content(before), "Copia corrupta alteró el destino.")
        incompatible = self.work / "incompatible-backup"
        shutil.copytree(backup, incompatible)
        manifest = json.loads((incompatible / "manifest.json").read_text(encoding="utf-8"))
        manifest["app_version"] = "99.0.0"
        (incompatible / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.python("reject-future-restore", "tools/backup_atlas.py", "--restore", incompatible, expected=None)
        require(stable_content(snapshot(self.database)) == stable_content(before), "Copia incompatible alteró el destino.")
        restored = json.loads(self.python("restore", "tools/backup_atlas.py", "--restore", backup))
        require(restored.get("pre_restore_backup"), "Restauración sin copia previa del destino.")
        after = snapshot(self.database)
        require(stable_content(after) == stable_content(before), "Restauración cambió datos financieros/investigación.")
        self.start()
        state = self.request("/api/state")
        job = self.request(f"/api/experiments/{ident}")
        require(job["status"] == "paused" and not job.get("execution_active") and not job["auto_paper"],
                "Restauración no dejó el experimento seguro.")
        require(state["settings"]["kill_switch"] is True, "Restauración sin parada global.")
        require(self.request(f"/api/datasets/{dataset_id}/portfolio") == portfolio, "Restauración cambió la cartera.")
        require_demo_only(snapshot(self.database))
        self.stop()
        self.report["checks"]["restore"] = {"financial_content_sha256": digest(stable_content(after)),
                                             "portfolio_sha256": digest(portfolio), "result": restored,
                                             "active_rejected": True, "corrupt_rejected": True,
                                             "incompatible_rejected": True, "restart_safe": True}
        self.save()

    def upgrade(self):
        # Preserve the entire clean-install database directory; never overwrite
        # user data or touch the read-only historical source to exercise updates.
        origin = (self.clone / "var/atlas").resolve()
        archive = (self.clone / "var/demo-validated").resolve()
        require(origin.is_relative_to(self.clone) and archive.is_relative_to(self.clone)
                and not archive.exists(), "Destino aislado de actualización no válido.")
        origin.rename(archive)
        origin.mkdir()
        before = snapshot(self.legacy)
        with closing(sqlite3.connect(self.legacy.as_uri() + "?mode=ro", uri=True)) as src, \
                closing(sqlite3.connect(self.database)) as target:
            src.backup(target)
        require(snapshot(self.database) == before, "El snapshot de v0.1 no coincide con el origen.")
        self.powershell("Install-Atlas.ps1")
        pre_updates = list((self.clone / "backups/before-update").glob("atlas-*/manifest.json"))
        require(bool(pre_updates), "Actualización sin copia previa.")
        self.start()
        after = snapshot(self.database)
        require(after["schema"] == 1 and stable_content(after) == stable_content(before),
                "La migración no conserva los datos de v0.1.")
        portfolios = {ident: self.request(f"/api/datasets/{ident}/portfolio")
                      for kind, ident in before["records"] if kind == "dataset"}
        statuses = {ident: record["status"] for (kind, ident), record in before["records"].items()
                    if kind == "experiment"}
        for ident, status in statuses.items():
            require(self.request(f"/api/experiments/{ident}")["status"] == status,
                    "La actualización alteró el estado de observación histórico.")
        self.stop()
        self.start()
        require(stable_content(snapshot(self.database)) == stable_content(before), "El segundo inicio alteró datos.")
        for ident, portfolio in portfolios.items():
            require(self.request(f"/api/datasets/{ident}/portfolio") == portfolio, "El reinicio alteró la cartera.")
        require_demo_only(snapshot(self.database))
        final = self.stop()
        require(stable_content(snapshot(self.legacy)) == stable_content(before), "El origen histórico cambió.")
        self.report["checks"]["upgrade_v01"] = {"schema_before": 0, "schema_after": 1,
                                                  "financial_content_sha256": digest(stable_content(before)),
                                                  "portfolio_sha256": digest(portfolios), "statuses": statuses,
                                                  "pre_update_manifests": [str(path) for path in pre_updates],
                                                  "repeat_start": True, "final_runtime": final}

    def run(self):
        self.prepare()
        try:
            self.clean_install()
            self.upgrade()
            dirty = self.command("verify-clean-sources", ["git", "-C", self.clone, "status", "--porcelain", "--untracked-files=no"])
            require(not dirty.strip(), "Las fuentes de la candidata cambiaron durante la validación.")
            self.report["result"] = "passed"
        except Exception as exc:
            self.report["result"] = "failed"
            self.report["error"] = str(exc)
            raise
        finally:
            if self.started:
                try:
                    self.stop()
                except Exception as exc:
                    self.report["cleanup_error"] = str(exc)
            self.report["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.save()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--legacy-database", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        Walkthrough(args.work_dir, args.source_root, args.candidate_commit, args.legacy_database).run()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Validación de candidata: {exc}")
        return 1
    print(f"Candidata comprobada; evidencia: {args.work_dir.resolve() / 'evidence.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
