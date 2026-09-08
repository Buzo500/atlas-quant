"""Import confirmation must match the reviewed data, ledger and exact CSV.

All stores and clients are isolated; no worker, feed or model is started.
"""
from concurrent.futures import ThreadPoolExecutor
import re
import threading

import pytest
from fastapi.testclient import TestClient

from atlas_quant.app import create_app
from atlas_quant.datasets import DatasetService, LedgerPreviewConflict
from atlas_quant.store import Store, UnitOfWork


LOCAL = {"x-atlas-client": "local-v1"}
PRICES = ("date,symbol,open,high,low,close,volume,currency\n"
          "2026-01-05,DEMO,100,102,99,101,1000,EUR\n"
          "2026-01-06,DEMO,102,105,101,104,1500,EUR\n")
LEDGER = ("id,date,kind,symbol,quantity,price,amount,fee,currency\n"
          "deposit-1,2026-01-05,deposit,,,,1000,,EUR\n"
          "buy-1,2026-01-06,buy,DEMO,2,102,,1,EUR\n")


@pytest.fixture
def offline(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app = create_app(tmp_path, run_worker=False)
    with TestClient(app) as client:
        yield app.state.service, client


def make_dataset(client, **overrides):
    response = client.post("/api/datasets", headers=LOCAL, json={
        "csv": PRICES, "name": "Preview test", "source": "Offline fixture", **overrides})
    assert response.status_code == 200, response.text
    return response.json()


def review(client, ident, csv=LEDGER):
    response = client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL, json={"csv": csv})
    assert response.status_code == 200, response.text
    result = response.json()
    assert re.fullmatch(r"[0-9a-f]{64}", result["preview_token"])
    return result


def persistent_state(store):
    return store.list("dataset"), store.list("ledger"), store.audit_list(1000)


@pytest.mark.parametrize("extra", [{}, {"preview_token": None}])
def test_http_commit_requires_preview_without_mutation(offline, extra):
    service, client = offline
    ident = make_dataset(client)["id"]
    before = persistent_state(service.store)
    response = client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL,
                           json={"csv": LEDGER, "commit": True, **extra})
    assert response.status_code == 422
    assert "Previsualiza" in response.json()["detail"]
    assert persistent_state(service.store) == before


def test_http_cannot_disable_preview_requirement(offline):
    service, client = offline
    ident = make_dataset(client)["id"]
    before = persistent_state(service.store)
    response = client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL,
                           json={"csv": LEDGER, "commit": True, "require_preview": False})
    assert response.status_code == 422
    assert persistent_state(service.store) == before


@pytest.mark.parametrize("change", ["csv", "dataset", "ledger", "prices", "version", "bars_without_manifest"])
def test_changed_preview_context_rejected_without_writes_or_audit(offline, change):
    service, client = offline
    dataset = make_dataset(client)
    ident, csv = dataset["id"], LEDGER
    preview = review(client, ident)
    if change == "csv":
        csv = LEDGER.replace("1000,,EUR", "2000,,EUR")
    elif change == "dataset":
        ident = make_dataset(client, name="Other dataset")["id"]
    elif change == "ledger":
        service.import_ledger(ident, "id,date,kind,amount,currency\nother,2026-01-05,deposit,50,EUR\n",
                              commit=True, require_preview=False)
    elif change == "prices":
        make_dataset(client, dataset_id=ident,
                     csv=PRICES + "2026-01-07,DEMO,105,107,104,106,1600,EUR\n")
    elif change == "version":
        service.store.update("dataset", ident, lambda current: {**current, "version": current["version"] + 1})
    else:
        # Even an inconsistent persisted manifest must not make changed prices look current.
        def changed_bars(current):
            current["bars"][-1]["close"] = 103
            return current
        service.store.update("dataset", ident, changed_bars)
    before = persistent_state(service.store)
    response = client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL,
                           json={"csv": csv, "commit": True, "preview_token": preview["preview_token"]})
    assert response.status_code == 409, response.text
    assert "Vuelve a previsualizar" in response.json()["detail"]
    assert persistent_state(service.store) == before


def test_successful_confirmation_matches_review_and_stale_retry_cannot_duplicate(offline):
    service, client = offline
    ident = make_dataset(client)["id"]
    before = persistent_state(service.store)
    preview = review(client, ident)
    assert review(client, ident) == preview
    assert persistent_state(service.store) == before
    request = {"csv": LEDGER, "commit": True, "preview_token": preview["preview_token"]}
    response = client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL, json=request)
    assert response.status_code == 200, response.text
    assert response.json() == {**preview, "committed": True}
    after = persistent_state(service.store)
    retry = client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL, json=request)
    assert retry.status_code == 409
    assert persistent_state(service.store) == after
    repeated = review(client, ident)
    assert repeated["added"] == 0
    assert repeated["duplicates"] == 2
    assert repeated["preview_token"] != preview["preview_token"]
    request["preview_token"] = repeated["preview_token"]
    assert client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL, json=request).status_code == 200
    assert len(service.store.get("ledger", ident)["events"]) == 2
    assert service.portfolio(ident) == preview["portfolio"]


def test_preview_tokens_are_deterministic_across_store_reopening(offline):
    service, client = offline
    ident = make_dataset(client)["id"]
    preview = review(client, ident)
    reopened = DatasetService(Store(service.store.path))
    assert reopened.import_ledger(ident, LEDGER)["preview_token"] == preview["preview_token"]


def test_concurrent_confirmations_validate_and_write_under_same_transaction(offline, monkeypatch):
    service, client = offline
    ident = make_dataset(client)["id"]
    token = review(client, ident)["preview_token"]
    other = DatasetService(Store(service.store.path))
    first_writing, second_attempting, release = threading.Event(), threading.Event(), threading.Event()
    original_put, original_atomic = UnitOfWork.put, other.store.atomic
    blocked = False

    def held_put(work, kind, value, *args, **kwargs):
        nonlocal blocked
        if kind == "ledger" and not blocked:
            blocked = True
            first_writing.set()
            assert release.wait(5)
        return original_put(work, kind, value, *args, **kwargs)

    def competing_transaction(callback):
        second_attempting.set()
        return original_atomic(callback)

    monkeypatch.setattr(UnitOfWork, "put", held_put)
    monkeypatch.setattr(other.store, "atomic", competing_transaction)

    def confirm(instance):
        try:
            instance.import_ledger(ident, LEDGER, commit=True, preview_token=token)
            return "committed"
        except LedgerPreviewConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(confirm, service)
        try:
            assert first_writing.wait(5)
            second = pool.submit(confirm, other)
            assert second_attempting.wait(5)
        finally:
            release.set()
        assert first.result(5) == "committed"
        assert second.result(5) == "conflict"
    assert len(service.store.get("ledger", ident)["events"]) == 2
    assert len([entry for entry in service.store.audit_list() if entry["event"] == "ledger.imported"]) == 1
