"""SQLite state. Immutable dataset versions, durable experiment state and audit trail."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .data import build_provenance_manifest
from .identity_store import IdentityWork, migrate_v2, validate_schema
from .book_store import BookWork, migrate_v3, validate_schema as validate_book_schema
from .corporate_store import CorporateWork, migrate_v4, validate_schema as validate_corporate_schema
from .valuation_store import ValuationWork, migrate_v5, validate_schema as validate_valuation_schema
from .performance_store import PerformanceWork
from .targets_store import TargetsWork
from .planning_store import PlanningWork
from .worker_lock import WorkerLock

SCHEMA_VERSION = 5


def migrate(db):
    """v0.1 used user_version=0. Adoption of v1 changes no financial records."""
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise ValueError(f"Esquema SQLite {version} más nuevo que el soportado ({SCHEMA_VERSION}). Actualiza ATLAS.")
    if version == 0:
        # execute(), unlike executescript(), does not implicitly commit the transaction.
        for statement in (
            "CREATE TABLE IF NOT EXISTS records(kind TEXT,id TEXT,body TEXT NOT NULL, PRIMARY KEY(kind,id))",
            "CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,event TEXT NOT NULL,entity TEXT,details TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS versions(dataset_id TEXT,version INTEGER,body TEXT NOT NULL, PRIMARY KEY(dataset_id,version))",
        ):
            db.execute(statement)
    # Validate existing v1 databases too: user_version alone does not establish
    # the constraints relied on by INSERT OR REPLACE and immutable versions.
    # Each column records its declared type, NOT NULL flag and position in PK.
    expected = {
        "records": [("kind", "TEXT", 0, 1), ("id", "TEXT", 0, 2), ("body", "TEXT", 1, 0)],
        "audit": [("seq", "INTEGER", 0, 1), ("at", "TEXT", 1, 0), ("event", "TEXT", 1, 0),
                  ("entity", "TEXT", 0, 0), ("details", "TEXT", 1, 0)],
        "versions": [("dataset_id", "TEXT", 0, 1), ("version", "INTEGER", 0, 2), ("body", "TEXT", 1, 0)],
    }
    for table, columns in expected.items():
        actual = [(row[1], row[2].upper(), row[3], row[5]) for row in db.execute(f"PRAGMA table_info({table})")]
        if actual != columns:
            raise ValueError(f"Esquema incompatible en {table}; no se ha migrado la base.")
    if version < 2:
        migrate_v2(UnitOfWork(db))
    else:
        validate_schema(db)
    if version < 3:
        migrate_v3(db)
    else:
        validate_book_schema(db)
    if version < 4:
        migrate_v4(db)
    else:
        validate_corporate_schema(db)
    if version < 5:
        migrate_v5(db)
    else:
        validate_valuation_schema(db)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


class UnitOfWork(IdentityWork, BookWork, CorporateWork, ValuationWork, PerformanceWork, TargetsWork, PlanningWork):
    """Record operations sharing one short SQLite transaction.

    Callbacks must be synchronous and must not open another Store transaction,
    perform network requests, or wait for computation.
    """

    def __init__(self, db):
        self.db = db

    def get(self, kind, ident, default=None):
        if kind == "ledger":
            portfolio_id = self.legacy_portfolio_id(ident)
            if portfolio_id:
                portfolio = self.portfolio_record(portfolio_id)
                return {"id": ident, "events": [item["event"] for item in self.portfolio_events(portfolio)]}
        row = self.db.execute("SELECT body FROM records WHERE kind=? AND id=?", (kind, ident)).fetchone()
        return json.loads(row[0]) if row else deepcopy(default)

    def list(self, kind):
        if kind == "ledger":
            return [{"id": p["legacy_dataset_id"], "events": [item["event"] for item in self.portfolio_events(p)]}
                    for p in self.portfolio_list() if p.get("legacy_dataset_id")]
        return [json.loads(row[0]) for row in self.db.execute(
            "SELECT body FROM records WHERE kind=? ORDER BY rowid DESC", (kind,))]

    def put(self, kind, value, event=None):
        value = dict(value)
        value.setdefault("id", uuid.uuid4().hex)
        if kind == "ledger":
            self.put_legacy_ledger(value)
        else:
            self.db.execute("INSERT OR REPLACE INTO records VALUES(?,?,?)", (kind, value["id"], encode(value)))
        if event:
            self.audit(event, value["id"], {"status": value.get("status")})
        return value

    def audit(self, event, entity=None, details=None):
        Store._audit(self.db, event, entity, details or {})

    def dataset_version(self, ident, version):
        row = self.db.execute("SELECT body FROM versions WHERE dataset_id=? AND version=?", (ident, version)).fetchone()
        return json.loads(row[0]) if row else None

    def save_dataset(self, value, *, prepare=None, allow_revision=False):
        value = dict(value)
        value.setdefault("id", uuid.uuid4().hex)
        ident = value["id"]
        if self.get('native_price', ident) is not None:
            raise ValueError('La serie nativa conserva su identidad; usa su importador versionado de precios.')
        current = self.get("dataset", ident)
        if prepare is not None:
            prepared = prepare(deepcopy(current), value)
            if prepared is None:
                if current is None:
                    raise ValueError("Conjunto de datos no encontrado.")
                return current
            value = prepared
        if value.get("id") != ident:
            raise ValueError("No se puede cambiar el identificador del conjunto.")
        if current:
            # Validate against the committed version, never an earlier snapshot.
            lookup = {(bar["date"], bar["symbol"]): bar for bar in value["bars"]}
            if not allow_revision and any(lookup.get((bar["date"], bar["symbol"])) != bar for bar in current["bars"]):
                raise ValueError("La actualización debe conservar todas las barras anteriores sin cambios. Importe las revisiones como un conjunto nuevo.")
            prior_keys = {(bar["date"], bar["symbol"]) for bar in current["bars"]}
            last_dates = {}
            for bar in current["bars"]:
                last_dates[bar["symbol"]] = max(last_dates.get(bar["symbol"], ""), bar["date"])
            if not allow_revision and any((bar["date"], bar["symbol"]) not in prior_keys
                   and bar["date"] <= last_dates.get(bar["symbol"], "") for bar in value["bars"]):
                raise ValueError("Solo se pueden añadir barras posteriores al último día de cada activo; no insertar historia pasada.")
            value["source_kind"], value["source"] = current["source_kind"], current["source"]
        value["manifest"] = build_provenance_manifest(
            value["bars"], value["name"], value["source_kind"], value["source"])
        version = self.db.execute("SELECT COALESCE(MAX(version),0)+1 FROM versions WHERE dataset_id=?",
                                  (ident,)).fetchone()[0]
        value["version"] = version
        value["updated_at"] = now()
        payload = encode(value)
        self.db.execute("INSERT INTO versions VALUES(?,?,?)", (ident, version, payload))
        self.db.execute("INSERT OR REPLACE INTO records VALUES('dataset',?,?)", (ident, payload))
        self.audit("dataset.saved", ident, {"version": version, "hash": value["manifest"]})
        self.local_identities(ident, {bar["symbol"] for bar in value["bars"]})
        return value


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.transaction() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
                # Never migrate underneath an executor from the previous version.
                with WorkerLock(str(self.path) + ".worker.lock"):
                    with WorkerLock(str(self.path) + ".tick.lock"):
                        migrate(db)
            else:
                migrate(db)

    @contextmanager
    def transaction(self):
        with self.lock:
            db = sqlite3.connect(self.path, timeout=10)
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA foreign_keys=ON")
            try:
                db.execute("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

    def get(self, kind, ident, default=None):
        return self.atomic(lambda work: work.get(kind, ident, default))

    def list(self, kind):
        return self.atomic(lambda work: work.list(kind))

    def atomic(self, callback):
        """Commit a domain operation and its audit together, or roll back both."""
        with self.transaction() as db:
            return callback(UnitOfWork(db))

    def read(self, callback):
        """One WAL snapshot without occupying the application's writer lock.

        The connection is read-only at SQLite's boundary. Callbacks are still
        synchronous; publication rechecks immutable revision references in atomic().
        """
        db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=10)
        try:
            db.execute('PRAGMA query_only=ON')
            db.execute('BEGIN')
            return callback(UnitOfWork(db))
        finally:
            db.close()

    def put(self, kind, value, event=None):
        return self.atomic(lambda work: work.put(kind, value, event))

    def update(self, kind, ident, mutate, event=None):
        def change(work):
            current = work.get(kind, ident)
            if current is None:
                raise ValueError("Registro no encontrado.")
            result = mutate(deepcopy(current))
            if result is None:
                return current
            if result.get("id") != ident:
                raise ValueError("No se puede cambiar el identificador del registro.")
            return work.put(kind, result, event)
        return self.atomic(change)

    def save_dataset(self, value, *, prepare=None):
        return self.atomic(lambda work: work.save_dataset(value, prepare=prepare))

    def get_dataset_version(self, ident, version):
        with self.transaction() as db:
            row = db.execute("SELECT body FROM versions WHERE dataset_id=? AND version=?",
                             (ident, version)).fetchone()
            return json.loads(row[0]) if row else None

    def audit(self, event, entity=None, details=None):
        with self.transaction() as db:
            self._audit(db,event,entity,details or {})

    @staticmethod
    def _audit(db,event,entity,details):
        db.execute("INSERT INTO audit(at,event,entity,details) VALUES(?,?,?,?)",
                   (now(),event,entity,encode(details)))

    def audit_list(self, limit=100):
        with self.transaction() as db:
            return [dict(seq=r[0],at=r[1],event=r[2],entity=r[3],details=json.loads(r[4]))
                    for r in db.execute("SELECT * FROM audit ORDER BY seq DESC LIMIT ?", (limit,))]

    def recover(self):
        # A request can have reached a provider before process death. Never replay it.
        def recover_jobs(work):
            for job in work.list("experiment"):
                if job["status"] == "running" or job.get("execution_active"):
                    if job["status"] != "cancelled":
                        job["status"] = "interrupted"
                    job.update(execution_active=False, control_requested=None,
                               error="Proceso interrumpido. Se conserva la reserva de API; no se repite la llamada.")
                    job.pop("execution_token", None)
                    work.put("experiment", job, "experiment.interrupted")
        self.atomic(recover_jobs)
