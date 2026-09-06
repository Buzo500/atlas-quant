"""SQLite state. Immutable dataset versions, durable experiment state and audit trail."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.transaction() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS records(kind TEXT,id TEXT,body TEXT NOT NULL,
              PRIMARY KEY(kind,id));
            CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,
              at TEXT NOT NULL,event TEXT NOT NULL,entity TEXT,details TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS versions(dataset_id TEXT,version INTEGER,body TEXT NOT NULL,
              PRIMARY KEY(dataset_id,version));
            """)

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
        with self.transaction() as db:
            row = db.execute("SELECT body FROM records WHERE kind=? AND id=?", (kind, ident)).fetchone()
            return json.loads(row[0]) if row else default

    def list(self, kind):
        with self.transaction() as db:
            return [json.loads(r[0]) for r in db.execute(
                "SELECT body FROM records WHERE kind=? ORDER BY rowid DESC", (kind,))]

    def put(self, kind, value, event=None):
        value = dict(value)
        value.setdefault("id", uuid.uuid4().hex)
        with self.transaction() as db:
            db.execute("INSERT OR REPLACE INTO records VALUES(?,?,?)", (kind,value["id"],encode(value)))
            if event:
                self._audit(db, event, value["id"], {"status": value.get("status")})
        return value

    def save_dataset(self, value):
        value = dict(value)
        value.setdefault("id", uuid.uuid4().hex)
        with self.transaction() as db:
            version = db.execute("SELECT COALESCE(MAX(version),0)+1 FROM versions WHERE dataset_id=?",
                                 (value["id"],)).fetchone()[0]
            value["version"] = version
            value["updated_at"] = now()
            payload = encode(value)
            db.execute("INSERT INTO versions VALUES(?,?,?)", (value["id"], version, payload))
            db.execute("INSERT OR REPLACE INTO records VALUES('dataset',?,?)", (value["id"],payload))
            self._audit(db, "dataset.saved", value["id"], {"version": version,"hash":value["manifest"]})
        return value

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
        for job in self.list("experiment"):
            if job["status"] == "running":
                job.update(status="interrupted", error="Proceso interrumpido. Se conserva la reserva de API; no se repite la llamada.")
                self.put("experiment",job,"experiment.interrupted")
