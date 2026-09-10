"""Real schema-3 fixtures, additive D5 migration and immutable restoration."""
from contextlib import closing
import sqlite3
import pytest

from atlas_quant.store import Store, SCHEMA_VERSION
from atlas_quant.backup import create_backup, restore_backup, validate_backup
from atlas_quant.corporate_store import DDL
from atlas_quant.valuation_store import DDL as VALUATION_DDL
from atlas_quant.corporate_service import CorporateService
from atlas_quant.worker_lock import WorkerLock
from atlas_quant.service import Service
from atlas_quant.portfolios import PortfolioService
from test_book_d4 import setup, dump
from test_corporate_d5 import seed, commit_event, apply, application_body, corporate_csv


def schema3(path):
    store = Store(path)
    dataset = Service(store).load_demo()
    expected = Service(store).portfolio(dataset['id'])
    with closing(sqlite3.connect(path)) as db, db:
        for table in reversed(VALUATION_DDL):
            db.execute(f'DROP TABLE {table}')
        for table in reversed(DDL):
            db.execute(f'DROP TABLE {table}')
        db.execute('PRAGMA user_version=3')
    return dataset, expected


def test_schema3_migration_preserves_all_old_tables_and_values(tmp_path):
    path = tmp_path / 'atlas.sqlite3'
    dataset, expected = schema3(path)
    before = dump(path)
    store = Store(path)
    after = dump(path)
    assert {t: after[t] for t in before} == before
    assert all(after[t] == [] for t in DDL)
    assert Service(store).portfolio(dataset['id']) == expected
    Store(path)
    assert dump(path) == after
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == SCHEMA_VERSION
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []


def test_partial_corporate_migration_rolls_back(tmp_path, monkeypatch):
    import atlas_quant.store as module
    path = tmp_path / 'atlas.sqlite3'
    schema3(path)
    before = dump(path)
    def fail(db):
        db.execute(next(iter(DDL.values())))
        raise RuntimeError('migration failure')
    monkeypatch.setattr(module, 'migrate_v4', fail)
    with pytest.raises(RuntimeError, match='migration failure'):
        Store(path)
    assert dump(path) == before
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 3


@pytest.mark.parametrize('lock', ['worker', 'tick'])
def test_migration_excludes_old_executor(tmp_path, lock):
    path = tmp_path / 'atlas.sqlite3'
    schema3(path)
    before = dump(path)
    with WorkerLock(str(path)+'.'+lock+'.lock'):
        with pytest.raises(RuntimeError):
            Store(path)
    assert dump(path) == before


@pytest.mark.parametrize('table', DDL)
def test_missing_corporate_table_is_not_silently_repaired(tmp_path, table):
    store = Store(tmp_path / 'atlas.sqlite3')
    with closing(sqlite3.connect(store.path)) as db, db:
        db.execute(f'DROP TABLE {table}')
    before = dump(store.path)
    with pytest.raises(ValueError, match='Esquema incompatible'):
        Store(store.path)
    assert dump(store.path) == before


def test_backup_restore_keeps_events_rights_book_and_documents(setup, tmp_path):
    seed(setup)
    event = commit_event(setup)
    expected = apply(setup, application_body(setup, event, csv=corporate_csv(event)))
    store = setup[0]
    before = dump(store.path)
    folder = create_backup(store.path, tmp_path / 'backups')
    assert validate_backup(folder)['schema']['user_version'] == SCHEMA_VERSION
    target = tmp_path / 'restored.sqlite3'
    restore_backup(folder, target, tmp_path / 'before', instance_lock=WorkerLock(str(target)+'.instance.lock'))
    restored = Store(target)
    actual = CorporateService(restored).read(setup[2]['id'])
    assert actual['balance'] == expected['balance']
    assert actual['applications'] == expected['applications']
    after = dump(target)
    assert all(after[t] == rows for t, rows in before.items() if t not in {'audit', 'records'})


def test_schema4_rejected_by_older_schema_guard_without_writes(tmp_path, monkeypatch):
    import atlas_quant.store as module
    path = tmp_path / 'atlas.sqlite3'
    Store(path)
    before = dump(path)
    monkeypatch.setattr(module, 'SCHEMA_VERSION', 3)
    with pytest.raises(ValueError, match='más nuevo'):
        Store(path)
    assert dump(path) == before
