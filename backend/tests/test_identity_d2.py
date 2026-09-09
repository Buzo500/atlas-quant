"""D2 identity, transaction, immutable cut and real SQLite migration regressions."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from atlas_quant.app import create_app
from atlas_quant.backup import create_backup, restore_backup, validate_backup
from atlas_quant.catalog import CatalogService, RevisionConflict
from atlas_quant.identity_store import DDL, IdentityWork
from atlas_quant.portfolios import PortfolioService
from atlas_quant.service import Service
from atlas_quant.store import Store
from atlas_quant.worker_lock import WorkerLock


def logical_dump(path):
    with closing(sqlite3.connect(path)) as db:
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {table: db.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in tables}


def legacy(path):
    store = Store(path)
    service = Service(store)
    dataset = service.load_demo()
    events = store.get("ledger", dataset["id"])
    snapshot = service.portfolio(dataset["id"])
    # Build the actual schema-1 layout, with a ledger keyed by dataset.
    with closing(sqlite3.connect(path)) as db, db:
        for table in reversed(DDL):
            db.execute(f"DROP TABLE {table}")
        db.execute("INSERT INTO records VALUES('ledger',?,?)", (dataset["id"], json.dumps(events)))
        db.execute("PRAGMA user_version=1")
    return dataset, events, snapshot


def strip_identity(value):
    return {**value, "positions": [{k: v for k, v in p.items() if k != "listing_id"} for p in value["positions"]]}


def test_migration_preserves_archive_ids_order_values_and_is_idempotent(tmp_path):
    path = tmp_path / "atlas.sqlite3"
    dataset, events, expected = legacy(path)
    before = logical_dump(path)
    store = Store(path)
    after = logical_dump(path)
    assert {table: after[table] for table in before} == before
    portfolio = PortfolioService(store).list()[0]
    detail = PortfolioService(store).read(portfolio["id"])
    assert portfolio["id"] != dataset["id"]
    assert portfolio["accounting_policy"] == "legacy-eur-v1"
    assert [entry["event"] for entry in detail["entries"]] == sorted(events["events"], key=lambda item: item["date"])
    assert strip_identity(detail["value"]) == expected
    assert all(not listing["verified"] and listing["market"] is None for listing in CatalogService(store).read()["listings"])
    Store(path)
    assert logical_dump(path) == after


def test_migration_failure_rolls_back_ddl_data_and_version(tmp_path, monkeypatch):
    path = tmp_path / "atlas.sqlite3"
    legacy(path)
    before = logical_dump(path)
    def fail(*args):
        raise RuntimeError("simulated write failure")
    monkeypatch.setattr(IdentityWork, "append_entries", fail)
    with pytest.raises(RuntimeError, match="simulated"):
        Store(path)
    assert logical_dump(path) == before
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1


def test_migration_refuses_active_old_executor(tmp_path):
    path = tmp_path / "atlas.sqlite3"
    legacy(path)
    before = logical_dump(path)
    with WorkerLock(str(path) + ".worker.lock"):
        with pytest.raises(RuntimeError):
            Store(path)
    assert logical_dump(path) == before


def test_v2_backup_restoration_preserves_catalog_books_and_revisions(tmp_path):
    source = Store(tmp_path / "source.sqlite3")
    Service(source).load_demo()
    saved = logical_dump(source.path)
    backup = create_backup(source.path, tmp_path / "backups")
    assert validate_backup(backup)["schema"]["user_version"] == 2
    target = tmp_path / "target.sqlite3"
    restore_backup(backup, target, tmp_path / "before", instance_lock=WorkerLock(str(target) + ".instance.lock"))
    restored = logical_dump(Store(target).path)
    assert all(restored[table] == saved[table] for table in DDL)
    assert PortfolioService(Store(target)).list() == PortfolioService(source).list()


@pytest.fixture
def local(tmp_path):
    store = Store(tmp_path / "atlas.sqlite3")
    service = Service(store)
    dataset = service.load_demo()
    return store, service, dataset, PortfolioService(store)


def test_explicit_new_source_and_ticker_keep_book_and_history(local):
    store, service, dataset, portfolios = local
    portfolio = portfolios.list()[0]
    original = portfolios.read(portfolio["id"])
    changed_bars = [{**bar, "symbol": "NEW_" + bar["symbol"]} for bar in dataset["bars"]]
    other = service.save_dataset(changed_bars, "Otra fuente", "synthetic", "Fixture local")
    # Identical instruments are never inferred from the equal data.
    listings = CatalogService(store).read()["listings"]
    assert len(listings) == 6 and len({item["instrument_id"] for item in listings}) == 6
    bindings = [{**b, "dataset_id": other["id"], "dataset_version": other["version"], "symbol": "NEW_" + b["symbol"]} for b in portfolio["bindings"]]
    preview = portfolios.bind(portfolio["id"], bindings)
    assert portfolios.read(portfolio["id"])["context"]["bindings"] == portfolio["bindings"]
    result = portfolios.bind(portfolio["id"], bindings, True, preview["preview_token"])
    assert result["value"]["nav"] == original["value"]["nav"]
    assert result["entries"] == original["entries"]
    assert result["portfolio"]["event_ids"] == portfolio["event_ids"]
    assert portfolios.read(portfolio["id"], portfolio["revision"]) == original
    assert service.portfolio(dataset["id"])["nav"] == original["value"]["nav"]
    with closing(sqlite3.connect(store.path)) as db:
        assert db.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0] == len(original["entries"])


@pytest.mark.parametrize("change", ["ledger", "catalog", "bindings"])
def test_stale_binding_confirmation_has_no_writes(local, change):
    store, service, dataset, portfolios = local
    portfolio = portfolios.list()[0]
    preview = portfolios.bind(portfolio["id"], portfolio["bindings"])
    if change == "ledger":
        csv = "id,date,kind,amount,currency\nextra,2026-01-01,deposit,1000,EUR\n"
        service.import_ledger(dataset["id"], csv, True, require_preview=False)
    elif change == "catalog":
        catalog = CatalogService(store)
        catalog.add("instrument", dict(expected_revision=catalog.read()["revision"], name="Nuevo", source="Usuario"))
    else:
        with store.transaction() as db:
            work = IdentityWork()
            work.db = db
            work.write_portfolio_revision(portfolio["id"], portfolio["event_ids"], portfolio["bindings"])
    before = logical_dump(store.path)
    with pytest.raises(RevisionConflict):
        portfolios.bind(portfolio["id"], portfolio["bindings"], True, preview["preview_token"])
    assert logical_dump(store.path) == before


def test_failed_audit_rolls_back_book_and_revision(local, monkeypatch):
    store, _, _, portfolios = local
    portfolio = portfolios.list()[0]
    csv = "id,date,kind,amount,currency\nnew,2026-01-01,deposit,1000,EUR\n"
    preview = portfolios.import_ledger(portfolio["id"], csv)
    before = logical_dump(store.path)
    monkeypatch.setattr(Store, "_audit", lambda *args: (_ for _ in ()).throw(RuntimeError("audit failure")))
    with pytest.raises(RuntimeError, match="audit failure"):
        portfolios.import_ledger(portfolio["id"], csv, True, preview["preview_token"])
    assert logical_dump(store.path) == before


def test_two_concurrent_confirmations_only_one_changes_book(local):
    store, _, _, portfolios = local
    portfolio = portfolios.list()[0]
    csv = "id,date,kind,amount,currency\nnew,2026-01-01,deposit,1000,EUR\n"
    preview = portfolios.import_ledger(portfolio["id"], csv)
    barrier = Barrier(2)
    second = PortfolioService(Store(store.path))
    def confirm(service):
        barrier.wait(5)
        try:
            return service.import_ledger(portfolio["id"], csv, True, preview["preview_token"])["added"]
        except RevisionConflict:
            return "conflict"
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(confirm, [portfolios, second]))
    assert 1 in results and "conflict" in results
    new_preview = portfolios.import_ledger(portfolio["id"], csv)
    assert new_preview["added"] == 0 and new_preview["duplicates"] == 1


def test_missing_prices_do_not_produce_false_zero(local):
    store, _, _, portfolios = local
    portfolio = portfolios.list()[0]
    with store.transaction() as db:
        db.execute("DELETE FROM portfolio_revisions WHERE portfolio_id=?", (portfolio["id"],))
        db.execute("INSERT INTO portfolio_revisions VALUES(?,1,?)", (portfolio["id"], json.dumps({
            "event_ids": portfolio["event_ids"], "bindings": [], "catalog_revision": portfolio["catalog_revision"]})))
    read = portfolios.read(portfolio["id"])
    assert read["status"] == "unavailable" and read["value"] is None and read["entries"]


def test_same_ticker_markets_and_alias_change_preserve_instrument(tmp_path):
    catalog = CatalogService(Store(tmp_path / "atlas.sqlite3"))
    def add(kind, **values):
        return catalog.add(kind, dict(expected_revision=catalog.read()["revision"], **values))
    instrument = add("instrument", name="Fondo", source="Usuario")["instruments"][0]
    first = add("listing", instrument_id=instrument["id"], currency="EUR", market="XPAR")["listings"][0]
    second_catalog = add("listing", instrument_id=instrument["id"], currency="USD", market="XNYS")
    second = next(item for item in second_catalog["listings"] if item["id"] != first["id"])
    for listing in [first, second]:
        add("alias", listing_id=listing["id"], provider="csv", symbol="SAME", source="Usuario", valid_to="2026-01-02")
    with pytest.raises(ValueError, match="ambiguo"):
        catalog.resolve("csv", "SAME", "2026-01-01")
    assert catalog.resolve("csv", "SAME", "2026-01-01", "XNYS")["id"] == second["id"]
    revision = catalog.read()["revision"]
    add("alias", listing_id=first["id"], provider="csv", symbol="NEW", source="Usuario", valid_from="2026-01-02")
    assert catalog.resolve("csv", "NEW", "2026-01-02")["id"] == first["id"]
    assert catalog.read(revision)["revision"] == revision
    before = catalog.read()
    with pytest.raises(ValueError, match="ambiguo"):
        add("alias", listing_id=first["id"], provider="csv", symbol="NEW", source="Usuario", valid_from="2026-01-03")
    assert catalog.read() == before


def test_new_http_routes_guard_validation_and_typed_results(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    headers = {"x-atlas-client": "local-v1"}
    with TestClient(app) as client:
        assert client.post("/api/portfolios", json={"name": "test"}).status_code == 403
        assert client.get("/api/portfolios/absent").status_code == 404
        assert client.post("/api/portfolios", headers=headers, json={"name": " "}).status_code == 422
        assert client.post("/api/catalog/listings", headers=headers, json={"expected_revision": 0, "instrument_id": "absent", "currency": "GBP"}).status_code == 422
        client.post("/api/datasets/demo", headers=headers).raise_for_status()
        portfolio = client.get("/api/portfolios").json()[0]
        detail = client.get("/api/portfolios/" + portfolio["id"])
        assert detail.status_code == 200 and detail.json()["status"] == "available"
        response = client.post(f'/api/portfolios/{portfolio["id"]}/bindings', headers=headers, json={"bindings": portfolio["bindings"]})
        assert response.status_code == 200, response.text
        assert client.post(f'/api/portfolios/{portfolio["id"]}/bindings', headers=headers,
            json={"bindings": portfolio["bindings"], "commit": True}).status_code == 409
