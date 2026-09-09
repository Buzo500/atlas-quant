"""Independent economic oracles, atomic confirmations, history and strict HTTP."""
import csv
import io
import json
import sqlite3
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from atlas_quant.app import create_app
from atlas_quant.book import MOVEMENT_COLUMNS, STATEMENT_COLUMNS, BookError, POLICY
from atlas_quant.book_contracts import ImportInput, ReconciliationInput, CorrectionInput
from atlas_quant.book_service import BookService
from atlas_quant.catalog import CatalogService, RevisionConflict
from atlas_quant.portfolios import PortfolioService
from atlas_quant.store import Store

ORACLES = json.loads((Path(__file__).parents[2] / "docs/fixtures/v0_4_d4_referencias.json").read_text(encoding="utf-8"))["cases"]
LOCAL = {"x-atlas-client": "local-v1"}


def dump(path):
    with closing(sqlite3.connect(path)) as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {t: db.execute(f'SELECT * FROM "{t}" ORDER BY rowid').fetchall() for t in tables}


def csv_text(columns, rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def movements(events):
    rows = []
    for index, event in enumerate(events, 1):
        row = dict.fromkeys(MOVEMENT_COLUMNS, "")
        row.update(external_id=f"event-{index}", date="2026-01-05", day_sequence=str(index),
                   currency="EUR", fee_amount="0.00", fee_currency="EUR", tax_amount="0.00", tax_currency="EUR")
        row.update({k: v for k, v in event.items() if k != "explanation"})
        if row["kind"] in {"buy", "sell"}:
            row.setdefault("listing_ref", "ASSET")
            row["listing_ref"] = row["listing_ref"] or "ASSET"
        rows.append(row)
    return csv_text(MOVEMENT_COLUMNS, rows)


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / "atlas.sqlite3")
    catalog = CatalogService(store)
    value = catalog.add("instrument", dict(expected_revision=0, name="Activo D4", source="Fixture"))
    value = catalog.add("listing", dict(expected_revision=value["revision"], instrument_id=value["instruments"][0]["id"], currency="EUR", market="XPAR"))
    portfolio = PortfolioService(store).create("D4 sintética", POLICY)
    return store, BookService(store), portfolio, {"ASSET": value["listings"][0]["id"]}


def request(setup, events=None, **changes):
    store, _, portfolio, mapping = setup
    events = events or ORACLES[1]["events"]
    value = dict(format_id="atlas-ledger-v2", source="Fixture", source_account="DEMO-01",
                 as_of_date="2026-01-06", mapping=mapping, csv=movements(events),
                 expected_revision=PortfolioService(store).read(portfolio["id"])["portfolio"]["revision"],
                 gross_explanations={f"event-{i}": e["explanation"] for i, e in enumerate(events, 1) if e.get("explanation")})
    return ImportInput.model_validate({**value, **changes})


def confirm(setup, body):
    _, service, portfolio, _ = setup
    preview = service.import_movements(portfolio["id"], body)
    return service.import_movements(portfolio["id"], body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))


@pytest.mark.parametrize("oracle", ORACLES, ids=lambda c: c["id"])
def test_independent_economic_oracles_without_prices(setup, oracle):
    store, service, portfolio, _ = setup
    result = confirm(setup, request(setup, oracle["events"]))
    book = result["balance"]
    expected = oracle["expected"]
    from decimal import Decimal as D
    assert D(book["cash"]) == D(expected["cash"])
    assert D(book["net_contributions"]) == D(expected["contributions"])
    assert D(book["realized_pnl"]) == D(expected["realized_pnl"])
    assert sum(D(p["quantity"]) for p in book["positions"]) == D(expected["quantity"])
    assert sum(D(p["cost_basis"]) for p in book["positions"]) == D(expected["cost"])
    assert store.list("dataset") == []
    assert service.read(portfolio["id"], "2026-01-04")["balance"]["cash"] == "0.00"
    assert result["context"]["portfolio_revision"] == 2


def test_exact_reimport_is_noop_and_canonical_numbers_deduplicate(setup):
    store, service, portfolio, _ = setup
    body = request(setup)
    result = confirm(setup, body)
    saved = dump(store.path)
    repeated = confirm(setup, request(setup))
    assert repeated["added"] == 0 and repeated["duplicates"] == 3
    assert repeated["document_id"] == result["document_id"]
    assert dump(store.path) == saved
    body = request(setup, csv=body.csv.replace("1000.00", "01000.0").replace(",100,", ",100.000,"))
    preview = service.import_movements(portfolio["id"], body)
    assert preview["added"] == 0 and preview["duplicates"] == 3


@pytest.mark.parametrize("change,code", [
    ({"gross_amount": "1001"}, "duplicate_conflict"),
    ({"day_sequence": "2"}, "duplicate_conflict"),
])
def test_conflicting_external_id_does_not_write(setup, change, code):
    store, service, portfolio, _ = setup
    confirm(setup, request(setup))
    before = dump(store.path)
    events = [{**ORACLES[1]["events"][0], **change}]
    with pytest.raises(BookError) as error:
        confirm(setup, request(setup, events))
    assert error.value.code == code
    assert dump(store.path) == before


def test_equal_deposits_with_distinct_ids_are_both_kept(setup):
    events = [dict(kind="deposit", gross_amount="100"), dict(kind="deposit", gross_amount="100")]
    result = confirm(setup, request(setup, events))
    assert result["added"] == 2 and result["balance"]["cash"] == "200.00"


def test_catalog_change_after_calculation_is_rechecked_inside_commit(setup, monkeypatch):
    import atlas_quant.book_service as module
    store, service, portfolio, _ = setup
    body = request(setup)
    preview = service.import_movements(portfolio["id"], body)
    original_balance = module.balance
    changed = False
    def racing_balance(*args, **kwargs):
        nonlocal changed
        value = original_balance(*args, **kwargs)
        if not changed:
            changed = True
            CatalogService(Store(store.path)).add("instrument", dict(expected_revision=2, name="Cambio concurrente", source="Fixture"))
        return value
    monkeypatch.setattr(module, "balance", racing_balance)
    with pytest.raises(RevisionConflict, match="durante el cálculo"):
        service.import_movements(portfolio["id"], body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))
    assert service.read(portfolio["id"])["total"] == 0
    assert service.documents(portfolio["id"])["total"] == 0
    assert service.read(portfolio["id"])["sources"] == []


@pytest.mark.parametrize("mode", ["correction", "reconciliation"])
def test_review_audit_failure_rolls_back_every_table(setup, monkeypatch, mode):
    from atlas_quant.store import UnitOfWork
    store, service, portfolio, _ = setup
    confirm(setup, request(setup))
    if mode == "correction":
        event = service.read(portfolio["id"])["entries"][-1]["event"]["id"]
        body = CorrectionInput(event_id=event, action="void", reason="Fixture rollback", expected_revision=2)
        operation = service.correct
    else:
        body, operation = statement(setup), service.reconcile
    preview = operation(portfolio["id"], body)
    before = dump(store.path)
    def failure(*args, **kwargs):
        raise RuntimeError("audit failed")
    monkeypatch.setattr(UnitOfWork, "audit", failure)
    with pytest.raises(RuntimeError, match="audit failed"):
        operation(portfolio["id"], body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))
    assert dump(store.path) == before


@pytest.mark.parametrize("change,code", [
    ({"gross_amount": "NaN"}, "invalid_decimal"),
    ({"gross_amount": "1e2"}, "invalid_decimal"),
    ({"gross_amount": "-1"}, "invalid_decimal"),
    ({"gross_amount": "1.001"}, "invalid_decimal"),
    ({"gross_amount": "1000000000000000001"}, "numeric_range"),
    ({"quantity": "1"}, "incompatible_field"),
    ({"currency": "USD"}, "unsupported_currency"),
    ({"tax_amount": "1"}, "unsupported_tax"),
    ({"fee_currency": ""}, "unsupported_currency"),
    ({"day_sequence": ""}, "event_order_ambiguous"),
    ({"date": "2026-01-07"}, "future_date"),
    ({"kind": "fx_exchange"}, "unsupported_kind"),
    ({"external_id": ""}, "invalid_field"),
])
def test_strict_fields_fail_before_any_write(setup, change, code):
    store, service, portfolio, _ = setup
    before = dump(store.path)
    body = request(setup, [dict(kind="deposit", gross_amount="100", **change)] if "kind" not in change and "gross_amount" not in change else [{**dict(kind="deposit", gross_amount="100"), **change}])
    with pytest.raises(BookError) as error:
        service.import_movements(portfolio["id"], body)
    assert error.value.code == code
    assert dump(store.path) == before


def test_declared_gross_difference_requires_reviewed_explanation(setup):
    _, service, portfolio, _ = setup
    body = request(setup, ORACLES[3]["events"], gross_explanations={})
    with pytest.raises(BookError, match="gross_explanation"):
        service.import_movements(portfolio["id"], body)
    reviewed = request(setup, ORACLES[3]["events"])
    preview = service.import_movements(portfolio["id"], reviewed)
    changed = reviewed.model_copy(update={"commit": True, "preview_token": preview["preview_token"],
                                          "gross_explanations": {"event-2": "Otra explicación"}})
    with pytest.raises(RevisionConflict):
        service.import_movements(portfolio["id"], changed)


def test_sequence_collision_and_later_negative_cash_rejected(setup):
    store, service, portfolio, _ = setup
    confirm(setup, request(setup, ORACLES[0]["events"]))
    before = dump(store.path)
    for event, code in [
        (dict(kind="deposit", gross_amount="10", external_id="different", day_sequence="1"), "event_order_ambiguous"),
        (dict(kind="withdrawal", gross_amount="999", external_id="earlier", date="2026-01-04"), "insufficient_cash"),
        (dict(kind="sell", gross_amount="500", quantity="5", unit_price="100", external_id="short", day_sequence="3"), "short_position"),
    ]:
        with pytest.raises(BookError) as error:
            service.import_movements(portfolio["id"], request(setup, [event]))
        assert error.value.code == code
        assert dump(store.path) == before


def test_pagination_and_historical_insertion_review_all_history(setup):
    _, service, portfolio, _ = setup
    confirm(setup, request(setup, [dict(kind="deposit", gross_amount="100", date="2026-01-04")]))
    body = request(setup, [dict(kind="fee", gross_amount="1", external_id="fee-late", date="2026-01-06")])
    confirm(setup, body)
    body = request(setup, [dict(kind="withdrawal", gross_amount="100", external_id="withdrawal-middle", date="2026-01-05")], as_of_date="2026-01-05")
    with pytest.raises(BookError, match="Efectivo insuficiente"):
        service.import_movements(portfolio["id"], body)
    body = request(setup, [dict(kind="withdrawal", gross_amount="10", external_id="withdrawal-middle", date="2026-01-05")], as_of_date="2026-01-06", limit=1, offset=1)
    result = confirm(setup, body)
    assert result["historical_insertion"] and result["total"] == 3 and len(result["entries"]) == 1
    assert result["balance"]["cash"] == "89.00"


def test_two_confirmations_use_one_revision(setup):
    store, service, portfolio, _ = setup
    body = request(setup)
    preview = service.import_movements(portfolio["id"], body)
    committed = body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]})
    barrier = Barrier(2)
    second = BookService(Store(store.path))
    def run(candidate):
        barrier.wait(5)
        try:
            return candidate.import_movements(portfolio["id"], committed)["added"]
        except RevisionConflict:
            return "conflict"
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(run, [service, second]))
    assert sorted(map(str, results)) == ["3", "conflict"]
    assert len(store.atomic(lambda w: w.native_entries(portfolio["id"]))) == 3


def test_audit_failure_rolls_back_book_revision_batch_and_source(setup, monkeypatch):
    store, service, portfolio, _ = setup
    body = request(setup)
    preview = service.import_movements(portfolio["id"], body)
    before = dump(store.path)
    monkeypatch.setattr(Store, "_audit", lambda *args: (_ for _ in ()).throw(RuntimeError("audit failure")))
    with pytest.raises(RuntimeError, match="audit failure"):
        service.import_movements(portfolio["id"], body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))
    assert dump(store.path) == before


def test_catalog_change_and_payload_edit_invalidate_preview(setup):
    store, service, portfolio, _ = setup
    body = request(setup)
    preview = service.import_movements(portfolio["id"], body)
    with pytest.raises(RevisionConflict):
        service.import_movements(portfolio["id"], body.model_copy(update={"commit": True, "source_account": "OTHER", "preview_token": preview["preview_token"]}))
    catalog = CatalogService(store)
    catalog.add("instrument", dict(expected_revision=catalog.read()["revision"], name="Otro", source="Fixture"))
    before = dump(store.path)
    with pytest.raises(RevisionConflict):
        service.import_movements(portfolio["id"], body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))
    assert dump(store.path) == before


def statement(setup, cash="708.00", quantity="3", **changes):
    store, _, portfolio, mapping = setup
    rows = [dict(as_of_date="2026-01-06", record_type="cash", listing_ref="", currency="EUR", quantity="", amount=cash)]
    if quantity is not None:
        rows.append(dict(as_of_date="2026-01-06", record_type="position", listing_ref="ASSET", currency="EUR", quantity=quantity, amount=""))
    return ReconciliationInput.model_validate(dict(format_id="atlas-statement-v2", source="Fixture", source_account="DEMO-01",
        as_of_date="2026-01-06", expected_revision=PortfolioService(store).read(portfolio["id"])["portfolio"]["revision"],
        csv=csv_text(STATEMENT_COLUMNS, rows), mapping=mapping, complete_statement=True, **changes))


def test_reconciliation_persists_difference_without_adjusting_book_and_is_idempotent(setup):
    store, service, portfolio, _ = setup
    confirm(setup, request(setup))
    body = statement(setup)
    before = service.read(portfolio["id"])
    preview = service.reconcile(portfolio["id"], body)
    assert preview["status"] == "differences"
    assert [r["difference"] for r in preview["differences"]] == ["1", "0"]
    result = service.reconcile(portfolio["id"], body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))
    assert service.read(portfolio["id"]) == before
    saved = dump(store.path)
    service.reconcile(portfolio["id"], body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))
    assert dump(store.path) == saved
    document = service.documents(portfolio["id"], document_id=result["document_id"])
    assert document["current"] and document["balance"]["cash"] == "707.00"
    assert document["evidence"]["csv"] == body.csv
    confirm(setup, request(setup, [dict(kind="fee", gross_amount="1", external_id="new-fee", day_sequence="4")]))
    assert service.documents(portfolio["id"], document_id=result["document_id"])["current"] is False


def test_missing_position_in_complete_statement_means_zero_and_unknown_account_rejected(setup):
    _, service, portfolio, _ = setup
    confirm(setup, request(setup))
    result = service.reconcile(portfolio["id"], statement(setup, cash="707", quantity=None))
    assert [r["difference"] for r in result["differences"]] == ["0", "-3"]
    with pytest.raises(BookError) as error:
        service.reconcile(portfolio["id"], statement(setup).model_copy(update={"source_account": "OTHER"}))
    assert error.value.code == "account_mismatch"


def test_correction_preserves_old_revision_and_reimport_does_not_reactivate_void(setup):
    store, service, portfolio, _ = setup
    confirm(setup, request(setup, ORACLES[0]["events"]))
    original = service.read(portfolio["id"], revision=2)
    body = CorrectionInput(expected_revision=2, event_id=original["entries"][1]["event"]["id"], action="void", reason="Compra duplicada")
    preview = service.correct(portfolio["id"], body)
    result = service.correct(portfolio["id"], body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))
    assert result["balance"]["cash"] == "1000.00" and result["balance"]["positions"] == []
    assert service.read(portfolio["id"], revision=2) == original
    assert len(store.atomic(lambda w: w.native_entries(portfolio["id"]))) == 3
    repeated = confirm(setup, request(setup, ORACLES[0]["events"]))
    assert repeated["added"] == 0 and repeated["balance"]["cash"] == "1000.00"


def test_replacement_and_invalidating_correction(setup):
    store, service, portfolio, mapping = setup
    confirm(setup, request(setup))
    original = service.read(portfolio["id"])
    old_buy = original["entries"][1]["event"]["id"]
    void = CorrectionInput(expected_revision=2, event_id=old_buy, action="void", reason="Anulación revisada")
    before = dump(store.path)
    with pytest.raises(BookError, match="venta excede"):
        service.correct(portfolio["id"], void)
    assert dump(store.path) == before
    replacement = movements([dict(kind="buy", quantity="2", unit_price="100", gross_amount="200", fee_amount="2",
                                 external_id="event-2", day_sequence="2")])
    body = void.model_copy(update={"action": "replace", "csv": replacement, "mapping": mapping})
    preview = service.correct(portfolio["id"], body)
    result = service.correct(portfolio["id"], body.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))
    assert result["balance"]["cash"] == "907.00"
    assert result["balance"]["positions"][0]["quantity"] == "1"
    assert result["balance"]["positions"][0]["cost_basis"] == "101"
    assert service.read(portfolio["id"], revision=2)["balance"] == original["balance"]


def test_http_guards_typed_contracts_templates_and_full_statement_requirement(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    with TestClient(app) as client:
        created = client.post("/api/portfolios", headers=LOCAL, json={"name": "Nueva", "accounting_policy": POLICY})
        assert created.status_code == 201
        portfolio = created.json()
        path = f"/api/portfolios/{portfolio['id']}"
        assert client.get(path).json()["value"] is None
        assert client.get(path + "/book").json()["balance"]["cash"] == "0.00"
        body = dict(format_id="atlas-ledger-v2", source="Fixture", source_account="DEMO-01", expected_revision=1,
                    as_of_date="2026-01-06", csv=movements([dict(kind="deposit", gross_amount="100")]))
        assert client.post(path + "/imports", json=body).status_code == 403
        assert client.post(path + "/imports", headers={**LOCAL, "origin": "https://untrusted.example"}, json=body).status_code == 403
        preview = client.post(path + "/imports", headers=LOCAL, json=body)
        assert preview.status_code == 200, preview.text
        assert client.post(path + "/imports", headers=LOCAL, json={**body, "commit": True}).status_code == 409
        result = client.post(path + "/imports", headers=LOCAL, json={**body, "commit": True, "preview_token": preview.json()["preview_token"]})
        assert result.status_code == 200, result.text
        assert client.get(path + "/book-documents").json()["total"] == 1
        assert client.get(path + "/book-documents/" + result.json()["document_id"]).status_code == 200
        assert client.get(path + "/book?as_of_date=2999-01-01").status_code == 422
        assert client.get(path + "/book-documents/missing").status_code == 404
        invalid = client.post(path + "/imports", headers=LOCAL, json={**body, "expected_revision": 2, "csv": body["csv"].replace("deposit", "fx_exchange")})
        assert invalid.status_code == 422 and invalid.json()["detail"][0]["type"] == "unsupported_kind"
        assert "csv" not in invalid.json()["detail"][0]
        for template, columns in [("book-movements", MOVEMENT_COLUMNS), ("book-statement", STATEMENT_COLUMNS)]:
            assert client.get("/api/templates/" + template).text == ",".join(columns) + "\n"
        reference = dict(format_id="atlas-statement-v2", source="Fixture", source_account="DEMO-01",
                         expected_revision=2, as_of_date="2026-01-06", csv="not parsed")
        assert client.post(path + "/reconciliations", headers=LOCAL, json=reference).status_code == 422


def test_large_batch_limit_rejects_without_writes(setup):
    store, service, portfolio, _ = setup
    content = movements([dict(kind="deposit", gross_amount="1", external_id=f"row-{i}") for i in range(10_001)])
    before = dump(store.path)
    with pytest.raises(BookError, match="10.000"):
        service.import_movements(portfolio["id"], request(setup, csv=content))
    assert dump(store.path) == before


def test_legacy_fractional_cent_reconciles_without_prices_or_rounding(setup):
    store, service, _, mapping = setup
    portfolio = PortfolioService(store).create("Libro anterior")
    events = [
        dict(id="deposit", date="2026-01-05", kind="deposit", amount=10),
        dict(id="buy", date="2026-01-05", kind="buy", symbol="ASSET", quantity=3, price=.335),
    ]
    entries = [dict(event=event, date=event["date"], day_sequence=i,
                    listing_id=mapping["ASSET"] if event["kind"] == "buy" else None)
               for i, event in enumerate(events, 1)]
    store.atomic(lambda work: work.append_entries(work.portfolio_record(portfolio["id"]), entries))
    before = dump(store.path)
    result = service.read(portfolio["id"], "2026-01-05")
    assert result["balance"]["cash"] == "8.995"
    assert result["balance"]["positions"][0]["cost_basis"] == "1.005"
    assert any("fracciones de céntimo" in w for w in result["balance"]["warnings"])
    reference = ReconciliationInput(expected_revision=2, format_id="atlas-statement-v2", source="Fixture",
        source_account="LEGACY", as_of_date="2026-01-05", complete_statement=True, mapping=mapping,
        csv="as_of_date,record_type,listing_ref,currency,quantity,amount\n2026-01-05,cash,,EUR,,8.99\n2026-01-05,position,ASSET,EUR,3,\n")
    preview = service.reconcile(portfolio["id"], reference)
    assert preview["differences"][0]["difference"] == "-0.005"
    assert preview["differences"][1]["matched"] is True
    assert dump(store.path) == before
    service.reconcile(portfolio["id"], reference.model_copy(update={"commit": True, "preview_token": preview["preview_token"]}))
    assert service.read(portfolio["id"], "2026-01-05")["balance"] == result["balance"]
    assert store.list("dataset") == []
