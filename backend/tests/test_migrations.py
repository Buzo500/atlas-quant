"""Schema adoption preserves v0.1 data and rolls back failed DDL atomically."""
import json
import sqlite3
from contextlib import closing

import pytest

from atlas_quant.store import SCHEMA_VERSION, Store


def snapshot(path):
    with closing(sqlite3.connect(path)) as db:
        return {
            "version": db.execute("PRAGMA user_version").fetchone()[0],
            "records": db.execute("SELECT * FROM records ORDER BY kind,id").fetchall(),
            "audit": db.execute("SELECT * FROM audit ORDER BY seq").fetchall(),
            "versions": db.execute("SELECT * FROM versions ORDER BY dataset_id,version").fetchall(),
        }


def legacy_database(path, schema_transform=None):
    ledger = {"id": "portfolio", "events": [{"id": "deposit", "date": "2026-01-01", "kind": "deposit", "amount": "1234.56", "currency": "EUR"}]}
    experiment = {"id": "experiment", "status": "observing", "provider": "none",
                  "budget_usd": 0, "spent_usd": 0, "reserved_usd": 0, "auto_paper": False}
    dataset = {"id": "demo", "version": 1, "manifest": "original-hash", "name": "Demostración"}
    with closing(sqlite3.connect(path)) as db, db:
        schema = (
            "CREATE TABLE records(kind TEXT,id TEXT,body TEXT NOT NULL, PRIMARY KEY(kind,id));"
            "CREATE TABLE audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,"
            "event TEXT NOT NULL,entity TEXT,details TEXT NOT NULL);"
            "CREATE TABLE versions(dataset_id TEXT,version INTEGER,body TEXT NOT NULL, PRIMARY KEY(dataset_id,version));"
        )
        db.executescript(schema_transform(schema) if schema_transform else schema)
        for kind, value in (("ledger", ledger), ("experiment", experiment), ("dataset", dataset)):
            db.execute("INSERT INTO records VALUES(?,?,?)", (kind, value["id"], json.dumps(value, ensure_ascii=False)))
        db.execute("INSERT INTO audit VALUES(7,'2026-09-06T00:00:00+00:00','original','portfolio','{}')")
        db.execute("INSERT INTO versions VALUES('demo',1,?)", (json.dumps(dataset, ensure_ascii=False),))
    return ledger, experiment, dataset


def test_v01_schema_adoption_preserves_all_records_versions_and_audit(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    ledger, experiment, dataset = legacy_database(path)
    before = snapshot(path)
    assert before["version"] == 0
    store = Store(path)
    after = snapshot(path)
    assert after == {**before, "version": SCHEMA_VERSION}
    assert SCHEMA_VERSION == 3
    assert store.get("ledger", "portfolio") == ledger
    assert store.get("experiment", "experiment") == experiment
    assert store.get("dataset", "demo") == dataset
    store.audit("after-migration")
    assert store.audit_list(1)[0]["seq"] == 8


def test_new_database_is_versioned_and_reopening_is_idempotent(tmp_path):
    path = tmp_path / "new" / "atlas.sqlite3"
    store = Store(path)
    store.put("settings", {"id": "main", "kill_switch": True}, "settings.saved")
    before = snapshot(path)
    assert before["version"] == SCHEMA_VERSION
    Store(path)
    Store(path)
    assert snapshot(path) == before
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_future_schema_is_rejected_without_modifying_data_or_version(tmp_path):
    path = tmp_path / "future.sqlite3"
    legacy_database(path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(f"PRAGMA user_version={SCHEMA_VERSION + 1}")
    before = snapshot(path)
    with pytest.raises(ValueError, match="más nuevo que el soportado"):
        Store(path)
    assert snapshot(path) == before


def test_invalid_legacy_table_rolls_back_created_tables_and_schema_version(tmp_path):
    path = tmp_path / "invalid-legacy.sqlite3"
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE records(id TEXT PRIMARY KEY, body TEXT)")
        db.execute("INSERT INTO records VALUES('retained','original payload')")
    with pytest.raises(ValueError, match="Esquema incompatible en records"):
        Store(path)
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert tables == {"records"}
        assert db.execute("SELECT * FROM records").fetchall() == [("retained", "original payload")]
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


@pytest.mark.parametrize("schema_version", [0, 1])
@pytest.mark.parametrize("table, old, new", [
    pytest.param("records", ", PRIMARY KEY(kind,id)", "", id="missing-record-key"),
    pytest.param("records", "PRIMARY KEY(kind,id)", "PRIMARY KEY(id,kind)", id="reordered-record-key"),
    pytest.param("records", "kind TEXT,id TEXT,body TEXT NOT NULL", "kind TEXT,id TEXT,body TEXT",
                 id="nullable-record-body"),
    pytest.param("records", "kind TEXT,id TEXT,body TEXT NOT NULL", "kind TEXT,id TEXT,body BLOB NOT NULL",
                 id="wrong-record-body-type"),
    pytest.param("audit", "event TEXT NOT NULL", "event TEXT", id="nullable-audit-event"),
    pytest.param("audit", "seq INTEGER PRIMARY KEY AUTOINCREMENT", "seq INTEGER", id="missing-audit-key"),
    pytest.param("versions", "dataset_id TEXT,version INTEGER", "dataset_id TEXT,version TEXT",
                 id="wrong-version-type"),
    pytest.param("versions", "PRIMARY KEY(dataset_id,version)", "PRIMARY KEY(version,dataset_id)",
                 id="reordered-version-key"),
])
def test_incompatible_constraints_are_rejected_without_changing_state(tmp_path, schema_version, table, old, new):
    path = tmp_path / "incompatible.sqlite3"
    legacy_database(path, schema_transform=lambda schema: schema.replace(old, new))
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(f"PRAGMA user_version={schema_version}")
        original_schema = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name").fetchall()
    before = snapshot(path)
    with pytest.raises(ValueError, match=f"Esquema incompatible en {table}"):
        Store(path)
    assert snapshot(path) == before
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name").fetchall() == original_schema
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_current_schema_with_missing_table_is_not_repaired_silently(tmp_path):
    path = tmp_path / "missing-current-table.sqlite3"
    legacy_database(path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("DROP TABLE versions")
        db.execute("PRAGMA user_version=1")
        before = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name").fetchall()
    with pytest.raises(ValueError, match="Esquema incompatible en versions"):
        Store(path)
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name").fetchall() == before
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
