"""Coherent local SQLite backups and explicitly requested, stopped-state restores.

Only database state is copied: environment files and API credentials are never
read. A published backup directory is immutable and contains its own manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import time
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from . import __version__
from .worker_lock import WorkerLock
from .identity_store import DDL, validate_schema


FORMAT_VERSION = 1
SCHEMA_VERSIONS = {0, 1, 2}
DATABASE_NAME = "atlas.sqlite3"
MANIFEST_NAME = "manifest.json"
_SCHEMA = {
    "records": [("kind", "TEXT", 0, 1), ("id", "TEXT", 0, 2), ("body", "TEXT", 1, 0)],
    "audit": [("seq", "INTEGER", 0, 1), ("at", "TEXT", 1, 0),
              ("event", "TEXT", 1, 0), ("entity", "TEXT", 0, 0), ("details", "TEXT", 1, 0)],
    "versions": [("dataset_id", "TEXT", 0, 1), ("version", "INTEGER", 0, 2),
                 ("body", "TEXT", 1, 0)],
}


class BackupError(ValueError):
    """Actionable failure that leaves a published backup or original intact."""


class ExclusiveLock(Protocol):
    def acquire(self) -> bool: ...
    def release(self) -> None: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"


def _reject_constant(value):
    raise ValueError("Constante JSON no válida")


def _object(payload: str) -> dict:
    value = json.loads(payload, parse_constant=_reject_constant)
    if not isinstance(value, dict):
        raise BackupError("La base contiene un registro JSON que no es un objeto.")
    return value


def _hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _connect(path: Path, mode="ro") -> sqlite3.Connection:
    db = sqlite3.connect(path.as_uri() + "?mode=" + mode, uri=True, timeout=5)
    db.execute("PRAGMA trusted_schema=OFF")
    return db


def _validate_database(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise BackupError("No existe una base SQLite regular en la ruta indicada.")
    try:
        with closing(_connect(path)) as db:
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise BackupError("La comprobación de integridad SQLite ha fallado.")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in SCHEMA_VERSIONS:
                raise BackupError("Versión de esquema no compatible con esta instalación.")
            objects = db.execute(
                "SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
            ).fetchall()
            tables = set(_SCHEMA) | (set(DDL) if version == 2 else set())
            if set(objects) != {("table", name) for name in tables}:
                raise BackupError("La base no tiene las tablas de ATLAS esperadas.")
            for table, expected in _SCHEMA.items():
                columns = [(r[1], r[2].upper(), r[3], r[5])
                           for r in db.execute(f"PRAGMA table_info({table})")]
                if columns != expected:
                    raise BackupError("Las columnas de la base no corresponden al esquema de ATLAS.")
            counts = {}
            if version == 2:
                validate_schema(db)
                for table in DDL:
                    if table != "listing_aliases":
                        for (payload,) in db.execute(f"SELECT body FROM {table}"):
                            _object(payload)
                    counts[table] = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table, column in (("records", "body"), ("versions", "body"), ("audit", "details")):
                count = 0
                for (payload,) in db.execute(f"SELECT {column} FROM {table}"):
                    _object(payload)
                    count += 1
                counts[table] = count
            return {"user_version": version, "tables": counts}
    except (sqlite3.Error, json.JSONDecodeError, TypeError, UnicodeError) as exc:
        raise BackupError("La base SQLite o sus registros no son válidos.") from exc
    except ValueError as exc:
        if isinstance(exc, BackupError):
            raise
        raise BackupError("La base contiene valores JSON no válidos.") from exc


def _snapshot(source: Path, target: Path) -> None:
    deadline = time.monotonic() + 30

    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise BackupError("La copia excedió 30 segundos; inténtalo cuando haya menos actividad.")

    with closing(_connect(source)) as origin, closing(sqlite3.connect(target)) as destination:
        origin.backup(destination, pages=256, progress=progress, sleep=0.05)
        destination.execute("PRAGMA journal_mode=DELETE")
    _fsync_file(target)


def _fsync_file(path: Path) -> None:
    # Windows FlushFileBuffers requires a handle opened with write access.
    with path.open("r+b") as stream:
        os.fsync(stream.fileno())


def _fsync_directory(path: Path) -> None:
    # Windows does not expose fsync for directory handles through this API.
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def create_backup(source_db, backup_dir) -> Path:
    """Return a new published backup folder; safe while the engine writes WAL.

    Publication renames a temporary directory on the same filesystem only after
    SQLite integrity, ATLAS schema and JSON records have all been checked.
    """
    source = Path(source_db).resolve()
    destination = Path(backup_dir).resolve()
    if not source.is_file():
        raise BackupError("No existe la base de ATLAS; no se ha creado una base vacía.")
    destination.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".atlas-backup-", dir=destination))
    published = destination / ("atlas-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                               + "-" + uuid.uuid4().hex[:8])
    try:
        database = staging / DATABASE_NAME
        _snapshot(source, database)
        schema = _validate_database(database)
        manifest = {"format": "atlas-quant-backup", "format_version": FORMAT_VERSION,
                    "app_version": __version__, "created_at": _now(), "database": DATABASE_NAME,
                    "sha256": _hash(database), "size_bytes": database.stat().st_size,
                    "schema": schema}
        manifest_path = staging / MANIFEST_NAME
        manifest_path.write_text(_json(manifest), encoding="utf-8")
        _fsync_file(manifest_path)
        validate_backup(staging)
        _fsync_directory(staging)
        os.replace(staging, published)
        _fsync_directory(destination)
        return published
    except (sqlite3.Error, OSError) as exc:
        raise BackupError("No se pudo publicar la copia de seguridad; la base original se conserva.") from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def validate_backup(backup_path) -> dict:
    """Validate a self-contained backup before any destination is modified."""
    folder = Path(backup_path).resolve()
    manifest_path = folder / MANIFEST_NAME
    database = folder / DATABASE_NAME
    try:
        if not folder.is_dir() or manifest_path.is_symlink() or not manifest_path.is_file():
            raise BackupError("La ruta debe ser una carpeta de copia con manifest.json y atlas.sqlite3.")
        if set(p.name for p in folder.iterdir()) != {MANIFEST_NAME, DATABASE_NAME}:
            raise BackupError("La copia debe contener solo el manifiesto y la base, sin WAL ni otros archivos.")
        if manifest_path.stat().st_size > 64_000:
            raise BackupError("El manifiesto de la copia es demasiado grande.")
        manifest = _object(manifest_path.read_text(encoding="utf-8"))
        if (manifest.get("format") != "atlas-quant-backup"
                or manifest.get("format_version") != FORMAT_VERSION
                or manifest.get("database") != DATABASE_NAME):
            raise BackupError("Formato de copia no compatible.")
        app_version = manifest.get("app_version", "")
        if not isinstance(app_version, str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][\w.-]+)?", app_version):
            raise BackupError("El manifiesto no declara una versión de ATLAS válida.")
        source_version = tuple(map(int, app_version.split("-")[0].split("+")[0].split(".")))
        current_version = tuple(map(int, __version__.split("-")[0].split("+")[0].split(".")))
        if source_version > current_version:
            raise BackupError("La copia procede de una versión de ATLAS más nueva; actualiza primero.")
        timestamp = datetime.fromisoformat(manifest.get("created_at", ""))
        if timestamp.utcoffset() is None:
            raise BackupError("El manifiesto no tiene una fecha con zona horaria.")
        if not database.is_file() or database.is_symlink():
            raise BackupError("No existe una base regular dentro de la copia.")
        if (manifest.get("size_bytes") != database.stat().st_size
                or manifest.get("sha256") != _hash(database)):
            raise BackupError("El tamaño o SHA256 no coincide; la copia está alterada o incompleta.")
        if _validate_database(database) != manifest.get("schema"):
            raise BackupError("El esquema o recuento de tablas no coincide con el manifiesto.")
        return manifest
    except (OSError, TypeError, json.JSONDecodeError, UnicodeError) as exc:
        raise BackupError("No se pudo leer un manifiesto de copia válido.") from exc
    except ValueError as exc:
        if isinstance(exc, BackupError):
            raise
        raise BackupError("El manifiesto contiene una fecha o valor no válido.") from exc


def prune_backups(backup_dir, keep: int = 7) -> list[Path]:
    """Remove only the oldest verified backups, retaining at least ``keep``.

    Intended for the automatic-backup directory immediately after a successful
    create_backup. Unknown, incomplete and linked entries are never deleted.
    The returned absolute paths identify only backups successfully removed.
    """
    if type(keep) is not int or keep < 1:
        raise BackupError("La retención debe conservar al menos una copia (keep >= 1).")
    supplied = Path(backup_dir)
    root = supplied.resolve()
    if supplied.is_symlink() or supplied.is_junction() or not root.is_dir():
        raise BackupError("El directorio de retención debe existir y no ser un enlace.")

    def direct_folder(folder: Path) -> bool:
        return (folder.parent == root and not folder.is_symlink() and not folder.is_junction()
                and folder.resolve() == folder and folder.is_dir())

    try:
        valid = []
        # Complete inventory before removing anything. Only names published by
        # create_backup are eligible; foreign folders remain untouched.
        for folder in root.iterdir():
            if not re.fullmatch(r"atlas-\d{8}T\d{12}Z-[0-9a-f]{8}", folder.name) or not direct_folder(folder):
                continue
            try:
                manifest = validate_backup(folder)
            except BackupError:
                continue
            valid.append((datetime.fromisoformat(manifest["created_at"]), folder, manifest))
        valid.sort(key=lambda item: (item[0], item[1].name), reverse=True)
        if len(valid) <= keep:
            return []
        retained, obsolete = valid[:keep], valid[keep:]
        removed = []
        for _, folder, manifest in reversed(obsolete):
            # Recheck survivors and the deletion target after inventory. A
            # changed or malformed directory stops pruning without guessing.
            for _, survivor, expected in retained:
                if not direct_folder(survivor) or validate_backup(survivor) != expected:
                    raise BackupError("Una copia que debía conservarse ha cambiado; se detiene la retención.")
            if not direct_folder(folder) or validate_backup(folder) != manifest:
                raise BackupError("Una copia candidata ha cambiado; se detiene la retención.")
            # Resolved absolute direct child, verified above; never traverse
            # external links or delete an unrecognised directory recursively.
            shutil.rmtree(folder)
            removed.append(folder)
        _fsync_directory(root)
        return removed
    except OSError as exc:
        raise BackupError("No se pudo completar la retención de copias; revisa permisos y espacio local.") from exc


def _make_safe(path: Path, source_manifest: dict) -> dict:
    counts = {"paused_experiments": 0, "disabled_feeds": 0, "cancelled_orders": 0}
    with closing(_connect(path, "rw")) as db, db:
        for kind, ident, payload in db.execute("SELECT kind,id,body FROM records").fetchall():
            record = _object(payload)
            changed = False
            if kind == "experiment":
                previous = record.get("status")
                was_executing = record.get("execution_active", False)
                if previous in {"queued", "running", "observing", "eligible", "eligible_paper", "paper"}:
                    record["status"] = "paused"
                    record["resume_status"] = ("interrupted" if previous == "running"
                                               or record.get("reserved_usd", 0) else previous)
                    record["restored_previous_status"] = previous
                    record["error"] = ("Restaurado en pausa. Revisa el experimento antes de reanudar. "
                                       "Las reservas de API pendientes se conservan.")
                    counts["paused_experiments"] += 1
                # Older paused copies may also contain an in-flight reservation.
                if record.get("status") == "paused" and record.get("reserved_usd", 0):
                    record["resume_status"] = "interrupted"
                # A paused planning call may have settled just before the
                # snapshot, without its result being checkpointed. Do not
                # replay it merely because its remaining reservation is zero.
                if (previous == "paused" and was_executing
                        and record.get("resume_status") == "running"):
                    record["resume_status"] = "interrupted"
                # Execution ownership belongs to the old process, never to a
                # restored database. Safe observation pauses remain resumable.
                record["execution_active"] = False
                record["control_requested"] = None
                record.pop("execution_token", None)
                record["auto_paper"] = False
                account = record.get("paper_account")
                if account:
                    account["enabled"] = False
                    for order in account.get("orders", []):
                        if order.get("status") == "pending":
                            order["status"] = "cancelled"
                            order["reason"] = "database_restored"
                            counts["cancelled_orders"] += 1
                changed = True
            elif kind == "dataset" and record.get("feed"):
                record["restored_feed"] = record.pop("feed")
                record["restored_feed"].pop("request_id", None)
                counts["disabled_feeds"] += 1
                changed = True
            if changed:
                db.execute("UPDATE records SET body=? WHERE kind=? AND id=?", (_json(record), kind, ident))
        row = db.execute("SELECT body FROM records WHERE kind='settings' AND id='main'").fetchone()
        settings = _object(row[0]) if row else {"id": "main", "max_position_weight": 0.25}
        settings.update(kill_switch=True, mode="paper", live_available=False)
        db.execute("INSERT OR REPLACE INTO records VALUES('settings','main',?)", (_json(settings),))
        db.execute("INSERT INTO audit(at,event,entity,details) VALUES(?,?,?,?)",
                   (_now(), "database.restored", None,
                    _json({**counts, "source_sha256": source_manifest["sha256"],
                           "source_created_at": source_manifest["created_at"],
                           "api_reservations_preserved": True, "kill_switch": True})))
    _fsync_file(path)
    return counts


def restore_backup(backup_path, target_db, backup_dir, *, instance_lock: ExclusiveLock) -> dict:
    """Restore only while holding the launcher's exclusive installation lock.

    The caller must pass the same InstanceLock used by run_atlas. The previous
    destination is backed up before SQLite checkpoints its WAL and atomically
    replaces the database. Restored jobs cannot run without explicit review.
    """
    folder = Path(backup_path).resolve()
    target = Path(target_db).resolve()
    if target == folder / DATABASE_NAME:
        raise BackupError("La base de destino no puede ser la propia copia de seguridad.")
    if not instance_lock.acquire():
        raise BackupError("ATLAS está en ejecución o la instalación está ocupada. Detén ATLAS antes de restaurar.")
    staged = None
    previous = None
    worker_lock = WorkerLock(str(target) + ".worker.lock")
    tick_lock = WorkerLock(str(target) + ".tick.lock")
    try:
        # Direct API/Service users also own these locks, even when they were
        # not started by the desktop launcher. Check before snapshot or writes.
        if not worker_lock.acquire() or not tick_lock.acquire():
            raise BackupError("Hay un ejecutor de ATLAS usando la base de destino. Detén ATLAS antes de restaurar.")
        manifest = validate_backup(folder)
        # Finish validation and sanitization before touching the old database.
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=".atlas-restore-", suffix=".sqlite3", dir=target.parent)
        os.close(descriptor)
        staged = Path(name)
        # A published backup has no WAL; copying and hashing this exact file
        # closes the validation/copy race without changing SQLite header bytes.
        shutil.copyfile(folder / DATABASE_NAME, staged)
        if _hash(staged) != manifest["sha256"]:
            raise BackupError("La copia cambió durante la restauración; el destino se conserva.")
        _validate_database(staged)
        counts = _make_safe(staged, manifest)
        _validate_database(staged)
        if target.exists():
            previous = create_backup(target, backup_dir)
            with closing(_connect(target, "rw")) as db:
                result = db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                if result[0] != 0:
                    raise BackupError("La base de destino sigue abierta; no se ha sustituido.")
                if db.execute("PRAGMA journal_mode=DELETE").fetchone()[0] != "delete":
                    raise BackupError("No se ha podido cerrar el WAL del destino; no se ha sustituido.")
        if any(Path(str(target) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
            raise BackupError("Hay archivos SQLite pendientes en el destino; no se han borrado ni sustituido datos.")
        os.replace(staged, target)
        _fsync_directory(target.parent)
        return {"target": str(target), "source_backup": str(folder),
                "pre_restore_backup": str(previous) if previous else None, **counts}
    except (sqlite3.Error, OSError) as exc:
        recovery = f" Copia previa conservada: {previous}" if previous else ""
        raise BackupError("No se pudo completar la restauración." + recovery) from exc
    finally:
        try:
            if staged is not None and staged.exists():
                staged.unlink()
        finally:
            tick_lock.release()
            worker_lock.release()
            instance_lock.release()
