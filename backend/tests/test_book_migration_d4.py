"""D3->D4 preserves old rows exactly and rollback/restoration remain coherent."""
import sqlite3
import json
from contextlib import closing

import pytest

from atlas_quant.backup import create_backup, restore_backup, validate_backup
from atlas_quant.book_store import DDL
from atlas_quant.portfolios import PortfolioService
from atlas_quant.service import Service
from atlas_quant.store import Store, SCHEMA_VERSION
from atlas_quant.corporate_store import DDL as CORPORATE_DDL
from atlas_quant.valuation_store import DDL as VALUATION_DDL
from atlas_quant.worker_lock import WorkerLock
from test_book_d4 import dump, setup, confirm, request, statement


def schema2(path):
    store = Store(path)
    dataset = Service(store).load_demo()
    expected = Service(store).portfolio(dataset["id"])
    with closing(sqlite3.connect(path)) as db, db:
        for table in reversed(VALUATION_DDL):
            db.execute(f"DROP TABLE {table}")
        for table in reversed(CORPORATE_DDL):
            db.execute(f"DROP TABLE {table}")
        for table in reversed(DDL):
            db.execute(f"DROP TABLE {table}")
        db.execute("PRAGMA user_version=2")
    return dataset, expected


def test_schema2_migration_is_additive_and_repeatable(tmp_path):
    path = tmp_path / "source.sqlite3"
    dataset, expected = schema2(path)
    before = dump(path)
    store = Store(path)
    after = dump(path)
    assert {table: after[table] for table in before} == before
    assert all(after[table] == [] for table in DDL)
    assert Service(store).portfolio(dataset["id"]) == expected
    assert all(p["accounting_policy"] == "legacy-eur-v1" for p in PortfolioService(store).list())
    Store(path)
    assert dump(path) == after
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_partial_migration_rolls_back_ddl_and_version(tmp_path, monkeypatch):
    import atlas_quant.store as module
    path = tmp_path / "source.sqlite3"
    schema2(path)
    before = dump(path)
    def fail(db):
        db.execute(next(iter(DDL.values())))
        raise RuntimeError("migration failure")
    monkeypatch.setattr(module, "migrate_v3", fail)
    with pytest.raises(RuntimeError, match="migration failure"):
        Store(path)
    assert dump(path) == before
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2


def test_migration_requires_exclusion_from_previous_executor(tmp_path):
    path = tmp_path / "source.sqlite3"
    schema2(path)
    before = dump(path)
    with WorkerLock(str(path) + ".worker.lock"):
        with pytest.raises(RuntimeError):
            Store(path)
    assert dump(path) == before


def test_schema3_backup_restores_native_book_sources_and_reports(setup, tmp_path):
    store, service, portfolio, _ = setup
    confirm(setup, request(setup))
    body = statement(setup)
    preview = service.reconcile(portfolio["id"], body)
    service.reconcile(portfolio["id"], body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))
    before = dump(store.path)
    backup = create_backup(store.path, tmp_path / "backups")
    assert validate_backup(backup)["schema"]["user_version"] == SCHEMA_VERSION
    target = tmp_path / "restore.sqlite3"
    restore_backup(backup, target, tmp_path / "before-restore", instance_lock=WorkerLock(str(target) + ".instance.lock"))
    Store(target)
    restored = dump(target)
    assert all(restored[table] == rows for table, rows in before.items() if table not in {"audit", "records"})
    assert before["records"] == []
    assert len(restored["records"]) == 1
    assert restored["records"][0][:2] == ("settings", "main")
    assert json.loads(restored["records"][0][2]) == dict(id="main", max_position_weight=0.25,
                                                       kill_switch=True, mode="paper", live_available=False)
    assert len(restored["audit"]) >= len(before["audit"])


@pytest.mark.parametrize("table", DDL)
def test_current_schema_missing_table_is_not_repaired(tmp_path, table):
    store = Store(tmp_path / "broken.sqlite3")
    with closing(sqlite3.connect(store.path)) as db, db:
        db.execute(f"DROP TABLE {table}")
    before = dump(store.path)
    with pytest.raises(ValueError, match="Esquema incompatible"):
        Store(store.path)
    assert dump(store.path) == before
