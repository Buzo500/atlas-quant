"""Validate schema 2 -> 3 on disposable copies of a backup, never on the source."""
from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from atlas_quant.backup import create_backup, restore_backup, validate_backup  # noqa: E402
from atlas_quant.book_store import DDL  # noqa: E402
from atlas_quant.identity_store import DDL as IDENTITY_DDL  # noqa: E402
from atlas_quant.portfolios import PortfolioService  # noqa: E402
from atlas_quant.store import Store, UnitOfWork, SCHEMA_VERSION  # noqa: E402
from atlas_quant.worker_lock import WorkerLock  # noqa: E402
from check_d2_migration import dump, require  # noqa: E402


class ReadOnly:
    """Read old schema without constructing Store or running any migrations."""
    def __init__(self, path):
        self.path = path

    def atomic(self, operation):
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            return operation(UnitOfWork(db))


def check(folder):
    manifest = validate_backup(folder)
    require(manifest["schema"]["user_version"] == 2, "Se requiere una copia del esquema 2, anterior a D4.")
    source = folder / "atlas.sqlite3"
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    original = dump(source)
    old = PortfolioService(ReadOnly(source))
    expected = {p["id"]: old.read(p["id"]) for p in old.list()}
    directory = ROOT / "var/validation" / ("d4-migration-" + uuid4().hex)
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / "migrated.sqlite3"
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as origin, closing(sqlite3.connect(target)) as destination:
        origin.backup(destination)
    started = time.perf_counter()
    store = Store(target)
    elapsed = time.perf_counter() - started
    migrated = dump(target)
    require(all(migrated[name] == rows for name, rows in original.items()), "La migración cambió registros históricos.")
    require(all(migrated[table] == [] for table in DDL), "Aparecieron movimientos/documentos nuevos durante la migración.")
    portfolios = PortfolioService(store)
    require({p["id"]: portfolios.read(p["id"]) for p in portfolios.list()} == expected, "La valoración o los vínculos cambiaron.")
    Store(target)
    require(dump(target) == migrated, "La reapertura volvió a modificar datos.")
    copied = create_backup(target, directory / "backups")
    restored_path = directory / "restored.sqlite3"
    restore_backup(copied, restored_path, directory / "before", instance_lock=WorkerLock(directory / "restore.lock"))
    restored_store = Store(restored_path)
    restored = dump(restored_path)
    require(all(restored[name] == migrated[name] for name in [*DDL, *IDENTITY_DDL, "versions"]), "La restauración alteró precios, identidades o libros.")
    restored_portfolios = PortfolioService(restored_store)
    require({p["id"]: restored_portfolios.read(p["id"]) for p in restored_portfolios.list()} == expected, "La cartera cambió al restaurar.")
    for path in (target, restored_path):
        with closing(sqlite3.connect(path)) as db:
            require(db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION, "Esquema inesperado.")
            require(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "Integridad inválida.")
            require(not db.execute("PRAGMA foreign_key_check").fetchall(), "Referencias inválidas.")
    require(hashlib.sha256(source.read_bytes()).hexdigest() == original_hash, "La copia original cambió.")
    comparisons = [dict(portfolio_id=ident, revision=d["portfolio"]["revision"], event_count=len(d["entries"]),
                       nav=d["value"]["nav"] if d["value"] else None, exact_equal=True) for ident, d in expected.items()]
    result = dict(source=str(source), source_unchanged=True, source_sha256=original_hash, directory=str(directory),
                  schema_before=2, schema_after=SCHEMA_VERSION, migration_seconds=elapsed, history_preserved=True,
                  new_tables_empty=True, reopened_unchanged=True, restored_books_and_values_equal=True,
                  integrity="ok", comparisons=comparisons)
    report = directory / "report.json"
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report), "result": "passed", "portfolios": len(comparisons)}, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    check(parser.parse_args().backup.resolve())
