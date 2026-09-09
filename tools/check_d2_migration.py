"""Validate D2 on disposable copies of a schema-1 backup; never migrate the source."""
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

from atlas_quant.analytics import portfolio_snapshot  # noqa: E402
from atlas_quant.backup import create_backup, restore_backup, validate_backup  # noqa: E402
from atlas_quant.identity_store import DDL  # noqa: E402
from atlas_quant.portfolios import PortfolioService  # noqa: E402
from atlas_quant.store import Store  # noqa: E402
from atlas_quant.worker_lock import WorkerLock  # noqa: E402


def dump(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {name: db.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall() for name in names}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check(folder):
    manifest = validate_backup(folder)
    require(manifest["schema"]["user_version"] == 1, "Se requiere una copia del esquema 1.")
    source = folder / "atlas.sqlite3"
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    original = dump(source)
    records = {(kind, ident): json.loads(body) for kind, ident, body in original["records"]}
    expected = {}
    for (kind, ident), value in records.items():
        if kind == "ledger":
            bars = records.get(("dataset", ident), {}).get("bars", [])
            expected[ident] = portfolio_snapshot(value.get("events", []), bars)
    directory = ROOT / "var" / "validation" / ("d2-migration-" + uuid4().hex)
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / "migrated.sqlite3"
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as origin, closing(sqlite3.connect(target)) as destination:
        origin.backup(destination)
    started = time.perf_counter()
    store = Store(target)
    elapsed = time.perf_counter() - started
    migrated = dump(target)
    require(all(migrated[name] == rows for name, rows in original.items()), "La migración cambió registros históricos.")
    portfolios = PortfolioService(store)
    comparisons = []
    for portfolio in portfolios.list():
        detail = portfolios.read(portfolio["id"])
        require(detail["status"] == "available", "Una cartera migrada no se puede valorar.")
        value = detail["value"]
        value = {**value, "positions": [{k: v for k, v in p.items() if k != "listing_id"} for p in value["positions"]]}
        require(value == expected[portfolio["legacy_dataset_id"]], "La valoración cambió durante la migración.")
        comparisons.append(dict(portfolio_id=portfolio["id"], legacy_dataset_id=portfolio["legacy_dataset_id"],
            revision=portfolio["revision"], event_count=len(detail["entries"]), nav=value["nav"], exact_equal=True))
    require(len(comparisons) == len(expected), "No se migraron todos los libros.")
    Store(target)
    require(dump(target) == migrated, "La reapertura volvió a modificar datos.")
    copied = create_backup(target, directory / "backups")
    restored_path = directory / "restored.sqlite3"
    restore_backup(copied, restored_path, directory / "before", instance_lock=WorkerLock(directory / "restore.lock"))
    restored = dump(Store(restored_path).path)
    require(all(restored[name] == migrated[name] for name in DDL), "La restauración alteró identidades o libros.")
    require(hashlib.sha256(source.read_bytes()).hexdigest() == original_hash, "La copia original cambió.")
    for path in (target, restored_path):
        with closing(sqlite3.connect(path)) as db:
            require(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "Integridad inválida.")
            require(not db.execute("PRAGMA foreign_key_check").fetchall(), "Referencias inválidas.")
    result = dict(source=str(source), source_unchanged=True, source_sha256=original_hash,
        directory=str(directory), schema_before=1, schema_after=2, migration_seconds=elapsed,
        history_preserved=True, reopened_unchanged=True, restored_identity_tables_equal=True,
        integrity="ok", comparisons=comparisons)
    report = directory / "report.json"
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report), "result": "passed", "portfolios": len(comparisons),
                      "migration_seconds": elapsed}, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    check(parser.parse_args().backup.resolve())
