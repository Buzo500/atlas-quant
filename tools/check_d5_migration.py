"""Check schema 3 -> 4 and recovery on disposable copies, keeping the source intact."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from atlas_quant.backup import create_backup, restore_backup, validate_backup  # noqa: E402
from atlas_quant.book import balance  # noqa: E402
from atlas_quant.corporate_store import DDL  # noqa: E402
from atlas_quant.portfolios import PortfolioService  # noqa: E402
from atlas_quant.store import Store, SCHEMA_VERSION  # noqa: E402
from atlas_quant.worker_lock import WorkerLock  # noqa: E402
from check_d2_migration import dump, require  # noqa: E402
from check_d4_migration import ReadOnly  # noqa: E402


def values(store, day):
    service = PortfolioService(store)
    result = {}
    for portfolio in service.list():
        ident = portfolio["id"]
        value = service.read(ident)
        result[ident] = dict(detail=value, book=balance(value["entries"], day, portfolio["accounting_policy"]))
    return result


def check(folder, *, schema_before=3, new_tables=DDL, read_values=values, run_prefix='d5'):
    manifest = validate_backup(folder)
    require(manifest["schema"]["user_version"] == schema_before, f"Se requiere una copia de esquema {schema_before}.")
    source = folder / "atlas.sqlite3"
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    day = datetime.now(timezone.utc).date().isoformat()
    original, expected = dump(source), read_values(ReadOnly(source), day)
    directory = ROOT / "var/validation" / (run_prefix + "-migration-" + uuid4().hex)
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / "migrated.sqlite3"
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as origin, closing(sqlite3.connect(target)) as destination:
        origin.backup(destination)
    store = Store(target)
    migrated = dump(target)
    require(all(migrated[name] == rows for name, rows in original.items()), "La migración modificó registros históricos.")
    require(all(migrated[name] == [] for name in new_tables), "Se crearon datos durante la migración.")
    require(read_values(store, day) == expected, "Cambiaron carteras, vínculos o resultados.")
    Store(target)
    require(dump(target) == migrated, "La reapertura modificó datos.")
    copied = create_backup(target, directory / "backups")
    restored = directory / "restored.sqlite3"
    restore_backup(copied, restored, directory / "before", instance_lock=WorkerLock(directory / "restore.lock"))
    restored_store = Store(restored)
    restored_dump = dump(restored)
    require(all(restored_dump[name] == rows for name, rows in migrated.items() if name not in {"audit", "records"}), "La restauración modificó datos históricos.")
    before_records = {(kind, ident): json.loads(body) for kind, ident, body in migrated["records"]}
    after_records = {(kind, ident): json.loads(body) for kind, ident, body in restored_dump["records"]}
    for (kind, ident), value in before_records.items():
        recovered = after_records[(kind, ident)]
        if kind == "dataset" and value.get("feed"):
            require(recovered.get("restored_feed") == {k: v for k, v in value["feed"].items() if k != "request_id"}, "No se conservó la fuente pausada.")
            value = {k: v for k, v in value.items() if k != "feed"}
            recovered = {k: v for k, v in recovered.items() if k != "restored_feed"}
        if kind != "settings":
            require(recovered == value, "Cambió un registro fuera de la pausa de fuentes.")
    require(after_records[("settings", "main")]["kill_switch"] is True, "La restauración no activó la parada.")
    require(read_values(restored_store, day) == expected, "La recuperación cambió libros o valoraciones.")
    for path in (target, restored):
        with closing(sqlite3.connect(path)) as db:
            require(db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION, "Esquema inesperado.")
            require(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "Integridad inválida.")
            require(not db.execute("PRAGMA foreign_key_check").fetchall(), "Referencias inválidas.")
    require(hashlib.sha256(source.read_bytes()).hexdigest() == original_hash, "La copia original cambió.")
    result = dict(source=str(source), source_sha256=original_hash, source_unchanged=True,
                  schema_before=schema_before, schema_after=SCHEMA_VERSION, history_preserved=True,
                  new_tables_empty=True, reopened_unchanged=True, recovery_equal=True, integrity="ok",
                  portfolios=[dict(id=ident, revision=v["detail"]["portfolio"]["revision"],
                                   events=len(v["detail"]["entries"]), exact_equal=True) for ident, v in expected.items()])
    report = directory / "report.json"
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(dict(report=str(report), result="passed"), ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    check(parser.parse_args().backup.resolve())
