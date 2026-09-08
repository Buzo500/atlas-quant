"""Local API integration: persistence, import review and paper controls.

All tests use temporary SQLite stores, a stopped worker and fake environment
keys. None can make a model call or contact a broker.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from atlas_quant.app import ExperimentInput, create_app
from atlas_quant.paper import advance_paper, new_account


LOCAL = {"x-atlas-client": "local-v1", "origin": "http://localhost:3000"}
PRICES = "date,symbol,open,high,low,close,volume,currency\n2026-01-05,DEMO,100,102,99,101,1000,EUR\n2026-01-06,DEMO,102,105,101,104,1500,EUR\n"
LEDGER = "id,date,kind,symbol,quantity,price,amount,fee,currency\ndeposit-1,2026-01-05,deposit,,,,1000,,EUR\nbuy-1,2026-01-06,buy,DEMO,2,102,,1,EUR\n"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-secret-for-api-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-secret-for-api-test")
    return create_app(tmp_path, run_worker=False)


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as instance:
        yield instance


def _dataset(client, **overrides):
    body = {"name": "Prueba", "source": "Datos de prueba importados", "source_kind": "observed", "csv": PRICES, **overrides}
    response = client.post("/api/datasets", json=body, headers=LOCAL)
    assert response.status_code == 200, response.text
    return response.json()


def _experiment(client, dataset, **overrides):
    response = client.post("/api/experiments", headers=LOCAL, json={
        "dataset_id": dataset["id"], "symbol": "DEMO", "provider": "none",
        "prompt": "Comprobar una estrategia finita de tendencia.", **overrides,
    })
    assert response.status_code == 201, response.text
    return response.json()


def _seed_pending_paper(app, client):
    dataset = _dataset(client)
    job = _experiment(client, dataset, auto_paper=True)
    service = app.state.service
    bars = service.dataset(dataset["id"])["bars"]
    account = advance_paper(new_account(1000, started_at_date="2026-01-04"), bars[:1],
                            {"kind": "buy_hold", "symbol": "DEMO"}, enabled=True)
    assert len(account["orders"]) == 1
    assert account["orders"][0]["status"] == "pending"
    job.update(status="eligible_paper", paper_account=account,
               observation_started_at=datetime.now(timezone.utc).isoformat(),
               research={"selected_strategy": {"kind": "buy_hold", "symbol": "DEMO"}})
    service.store.put("experiment", job)
    return job, dataset


def test_local_header_required_before_mutation(client):
    before = client.get("/api/state").json()
    response = client.post("/api/datasets", json={"csv": PRICES, "name": "bad", "source": "source"})
    assert response.status_code == 403
    after = client.get("/api/state").json()
    assert before["datasets"] == after["datasets"] == []


@pytest.mark.parametrize("method,path", [("get", "/api/state"), ("post", "/api/datasets/demo"), ("options", "/api/settings")])
def test_external_origins_blocked_even_with_local_header(client, method, path):
    response = getattr(client, method)(path, headers={**LOCAL, "origin": "https://malicious.invalid"})
    assert response.status_code == 403


def test_untrusted_host_rejected(client):
    assert client.get("/api/health", headers={"host": "attacker.invalid"}).status_code == 400


def test_security_headers_and_no_live_capability(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["live_available"] is False
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    schema = client.get("/openapi.json").json()
    assert not any("live" in path or "broker" in path or "orders" in path for path in schema["paths"])
    for path in ("/api/live", "/api/orders", "/api/broker/orders"):
        assert client.post(path, headers=LOCAL, json={}).status_code == 404


def test_malformed_content_length_is_client_error(client):
    response = client.post("/api/settings", content="{}", headers={**LOCAL, "content-type": "application/json", "content-length": "invalid"})
    assert response.status_code == 400


def test_declared_oversized_body_rejected(client):
    response = client.post("/api/settings", content="{}", headers={**LOCAL, "content-type": "application/json", "content-length": "9000001"})
    assert response.status_code == 413


def test_ledger_preview_does_not_mutate_then_commit_is_idempotent(app, client):
    dataset = _dataset(client)
    ident = dataset["id"]
    before_audit = app.state.service.store.audit_list()
    preview = client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL, json={"csv": LEDGER, "commit": False})
    assert preview.status_code == 200, preview.text
    assert preview.json()["committed"] is False
    assert preview.json()["added"] == 2
    assert app.state.service.store.get("ledger", ident) is None
    assert app.state.service.store.audit_list() == before_audit
    assert client.get(f"/api/datasets/{ident}/portfolio").json()["nav"] == 0

    first = client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL,
                        json={"csv": LEDGER, "commit": True, "preview_token": preview.json()["preview_token"]})
    assert first.status_code == 200, first.text
    assert first.json()["added"] == 2
    snapshot = client.get(f"/api/datasets/{ident}/portfolio").json()
    assert snapshot["cash"] == pytest.approx(795)
    assert snapshot["nav"] == pytest.approx(1003)
    repeated = client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL, json={"csv": LEDGER})
    second = client.post(f"/api/datasets/{ident}/ledger", headers=LOCAL,
                         json={"csv": LEDGER, "commit": True, "preview_token": repeated.json()["preview_token"]})
    assert second.status_code == 200
    assert second.json()["added"] == 0
    assert second.json()["duplicates"] == 2
    assert len(app.state.service.store.get("ledger", ident)["events"]) == 2
    assert client.get(f"/api/datasets/{ident}/portfolio").json() == snapshot


def test_ledger_conflicting_id_returns_422_without_mutation(app, client):
    dataset = _dataset(client)
    path = f"/api/datasets/{dataset['id']}/ledger"
    preview = client.post(path, headers=LOCAL, json={"csv": LEDGER}).json()
    assert client.post(path, headers=LOCAL,
                       json={"csv": LEDGER, "commit": True, "preview_token": preview["preview_token"]}).status_code == 200
    before = app.state.service.store.get("ledger", dataset["id"])
    response = client.post(path, headers=LOCAL, json={"csv": LEDGER.replace("1000,,EUR", "2000,,EUR")})
    assert response.status_code == 422
    assert app.state.service.store.get("ledger", dataset["id"]) == before


def test_invalid_ledger_insufficient_cash_returns_422(client):
    dataset = _dataset(client)
    response = client.post(f"/api/datasets/{dataset['id']}/ledger", headers=LOCAL,
                           json={"csv": LEDGER.replace("1000,,EUR", "100,,EUR")})
    assert response.status_code == 422
    assert "efectivo" in response.json()["detail"].lower()


def test_future_ledger_events_cannot_change_current_portfolio(app, client):
    dataset = _dataset(client)
    future = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
    csv = f"id,date,kind,amount,currency\nfuture-deposit,{future},deposit,1000,EUR\n"
    response = client.post(f"/api/datasets/{dataset['id']}/ledger", headers=LOCAL, json={"csv": csv})
    assert response.status_code == 422
    assert app.state.service.store.get("ledger", dataset["id"]) is None


def test_two_stale_settings_clients_change_only_the_requested_field(app, client):
    # The second client uses the existing application's lifespan; it must not start another worker.
    other = TestClient(app)
    try:
        assert client.post("/api/settings", headers=LOCAL, json={"kill_switch": False}).status_code == 200
        stale_a = client.get("/api/state").json()["settings"]
        stale_b = other.get("/api/state").json()["settings"]
        assert stale_a["kill_switch"] is False
        assert stale_b["max_position_weight"] == .25

        # B stops simulation after A's last poll. A only intends to change its weight draft.
        assert other.post("/api/settings", headers=LOCAL, json={"kill_switch": True}).status_code == 200
        changed_weight = client.post("/api/settings", headers=LOCAL, json={"max_position_weight": .4})
        assert changed_weight.status_code == 200, changed_weight.text
        assert changed_weight.json()["kill_switch"] is True
        assert changed_weight.json()["max_position_weight"] == .4

        # B still knows .25, but its explicit stop toggle must preserve A's new .4 limit.
        changed_stop = other.post("/api/settings", headers=LOCAL, json={"kill_switch": False})
        assert changed_stop.status_code == 200, changed_stop.text
        assert changed_stop.json()["kill_switch"] is False
        assert changed_stop.json()["max_position_weight"] == .4
    finally:
        other.close()


@pytest.mark.parametrize("payload", [
    {}, {"kill_switch": None}, {"max_position_weight": None},
    {"kill_switch": "false"}, {"kill_switch": False, "mode": "live"},
    {"max_position_weight": 0}, {"max_position_weight": 1.1},
])
def test_invalid_partial_settings_leave_records_and_audit_unchanged(app, client, payload):
    store = app.state.service.store
    before = app.state.service.settings(), store.list("experiment"), store.audit_list()
    response = client.post("/api/settings", headers=LOCAL, json=payload)
    assert response.status_code == 422, response.text
    assert (app.state.service.settings(), store.list("experiment"), store.audit_list()) == before


@pytest.mark.parametrize("payload", [
    '{"kill_switch":false,"max_position_weight":NaN}',
    '{"kill_switch":false,"max_position_weight":Infinity}',
    '{"kill_switch":false,"max_position_weight":-Infinity}',
])
def test_schema_nonfinite_numbers_return_422_without_changing_settings(client, payload):
    before = client.get("/api/state").json()["settings"]
    response = client.post("/api/settings", content=payload, headers={**LOCAL, "content-type": "application/json"})
    assert response.status_code == 422, response.text
    assert client.get("/api/state").json()["settings"] == before


def test_model_and_api_key_fields_cannot_be_injected_into_settings(client):
    response = client.post("/api/settings", headers=LOCAL, json={"kill_switch": True, "openai_api_key": "must-not-save", "base_url": "https://attacker.invalid"})
    assert response.status_code == 422


def test_keys_never_exposed_in_state_health_or_experiment(client):
    dataset = _dataset(client)
    job = _experiment(client, dataset)
    for path in ("/api/state", "/api/health", f"/api/experiments/{job['id']}", f"/api/experiments/{job['id']}/report"):
        response = client.get(path)
        assert response.status_code == 200
        assert "fake-openai-secret" not in response.text
        assert "fake-anthropic-secret" not in response.text
    providers = client.get("/api/state").json()["providers"]
    assert all(p["configured"] is True for p in providers)


def test_state_excludes_dataset_and_paper_raw_bars(app, client):
    _seed_pending_paper(app, client)
    state = client.get("/api/state").json()
    assert all("bars" not in d for d in state["datasets"])
    assert all("observed_bars" not in (j.get("paper_account") or {}) for j in state["experiments"])


def test_experiment_validation_rejects_unknown_symbol_and_lower_forward_minimum(client):
    dataset = _dataset(client)
    for body in (
        {"dataset_id": dataset["id"], "symbol": "MISSING"},
        {"dataset_id": dataset["id"], "symbol": "DEMO", "policy": {"min_forward_sessions": 2}},
        {"dataset_id": dataset["id"], "symbol": "DEMO", "hours": 0},
    ):
        response = client.post("/api/experiments", headers=LOCAL, json=body)
        assert response.status_code == 422, response.text


def test_missing_key_rejected_before_creating_ai_job(client, monkeypatch):
    dataset = _dataset(client)
    monkeypatch.delenv("OPENAI_API_KEY")
    response = client.post("/api/experiments", headers=LOCAL, json={"dataset_id": dataset["id"], "symbol": "DEMO", "provider": "openai", "budget_usd": 1})
    assert response.status_code == 422
    assert client.get("/api/state").json()["experiments"] == []


def test_anthropic_default_model_resolves_to_provider(client):
    dataset = _dataset(client)
    job = _experiment(client, dataset, provider="anthropic", budget_usd=1)
    assert job["model"] == "claude-haiku-4-5-20251001"


def test_unknown_model_rejected_before_creating_ai_job(client):
    dataset = _dataset(client)
    response = client.post("/api/experiments", headers=LOCAL, json={"dataset_id": dataset["id"], "symbol": "DEMO", "provider": "openai", "model": "unpriced-model", "budget_usd": 1})
    assert response.status_code == 422
    assert client.get("/api/state").json()["experiments"] == []


@pytest.mark.parametrize("action,target", [("pause", "paused"), ("cancel", "cancelled")])
def test_pause_and_cancel_persist_pending_order_cancellation(app, client, action, target):
    job, _ = _seed_pending_paper(app, client)
    response = client.post(f"/api/experiments/{job['id']}/control", headers=LOCAL, json={"action": action})
    assert response.status_code == 200, response.text
    stored = client.get(f"/api/experiments/{job['id']}").json()
    assert stored["status"] == target
    assert stored["paper_account"]["orders"][0]["status"] == "cancelled"
    assert stored["paper_account"]["fills"] == []


def test_kill_switch_cancels_pending_orders_persistently(app, client):
    job, _ = _seed_pending_paper(app, client)
    response = client.post("/api/settings", headers=LOCAL, json={"kill_switch": True, "max_position_weight": 0.25})
    assert response.status_code == 200
    stored = client.get(f"/api/experiments/{job['id']}").json()
    assert stored["paper_account"]["orders"][0]["status"] == "cancelled"
    assert stored["paper_account"]["fills"] == []
    assert app.state.service.store.get("settings", "main")["kill_switch"] is True


def test_kill_switch_still_advances_valuation_without_fills(app, client, monkeypatch):
    job, dataset = _seed_pending_paper(app, client)
    monkeypatch.setattr("atlas_quant.service.evaluate_evidence", lambda *_: {"passed": True, "decision": "eligible_paper", "checks": [], "limitations": []})
    asyncio.run(app.state.service.observe(job))
    stored = app.state.service.store.get("experiment", job["id"])
    assert stored["paper_account"]["last_processed_date"] == "2026-01-06"
    assert stored["paper_account"]["orders"][0]["status"] == "cancelled"
    assert stored["paper_account"]["fills"] == []
    assert stored["paper_account"]["cash"] == 1000


def _append_paused_sessions(client, dataset, include_later_session=False):
    csv = PRICES + "2026-01-07,DEMO,105,108,104,107,1600,EUR\n2026-01-08,DEMO,108,110,107,109,1700,EUR\n"
    if include_later_session:
        csv += "2026-01-09,DEMO,110,113,109,112,1800,EUR\n"
    response = client.post("/api/datasets", headers=LOCAL, json={
        "dataset_id": dataset["id"], "name": "Prueba actualizada", "source": "Datos de prueba importados",
        "source_kind": "observed", "csv": csv,
    })
    assert response.status_code == 200, response.text


def _observe_stored_paper(app, client, ident):
    job = client.get(f"/api/experiments/{ident}").json()
    asyncio.run(app.state.service.observe(job))
    return client.get(f"/api/experiments/{ident}").json()["paper_account"]


def test_resume_does_not_backfill_trades_from_paused_sessions(app, client, monkeypatch):
    job, dataset = _seed_pending_paper(app, client)
    monkeypatch.setattr("atlas_quant.service.evaluate_evidence", lambda *_: {"passed": True, "decision": "eligible_paper", "checks": [], "limitations": []})
    assert client.post("/api/settings", headers=LOCAL, json={"kill_switch": False, "max_position_weight": 0.25}).status_code == 200
    path = f"/api/experiments/{job['id']}/control"
    assert client.post(path, headers=LOCAL, json={"action": "pause"}).status_code == 200
    _append_paused_sessions(client, dataset)
    assert client.post(path, headers=LOCAL, json={"action": "resume"}).status_code == 200

    account = _observe_stored_paper(app, client, job["id"])
    assert account["last_processed_date"] == "2026-01-08"
    assert account["fills"] == [], "Sesiones recibidas en pausa no deben generar ejecuciones al reanudar."
    assert not any(order["status"] == "pending" for order in account["orders"])

    _append_paused_sessions(client, dataset, include_later_session=True)
    account = _observe_stored_paper(app, client, job["id"])
    assert account["fills"] == []
    pending = [order for order in account["orders"] if order["status"] == "pending"]
    assert len(pending) == 1
    assert pending[0]["signal_date"] == "2026-01-09"


def test_rearming_kill_switch_consumes_disabled_sessions_without_fills(app, client, monkeypatch):
    job, dataset = _seed_pending_paper(app, client)
    monkeypatch.setattr("atlas_quant.service.evaluate_evidence", lambda *_: {"passed": True, "decision": "eligible_paper", "checks": [], "limitations": []})
    assert client.post("/api/settings", headers=LOCAL, json={"kill_switch": False, "max_position_weight": 0.25}).status_code == 200
    assert client.post("/api/settings", headers=LOCAL, json={"kill_switch": True, "max_position_weight": 0.25}).status_code == 200
    _append_paused_sessions(client, dataset)
    # Intentionally do not tick the worker while disabled: rearming must consume
    # accumulated observations even when the machine or process was asleep.
    assert client.post("/api/settings", headers=LOCAL, json={"kill_switch": False, "max_position_weight": 0.25}).status_code == 200
    account = _observe_stored_paper(app, client, job["id"])
    assert account["last_processed_date"] == "2026-01-08"
    assert account["fills"] == [], "No se permite ejecutar retrospectivamente durante una parada."
    assert not any(order["status"] == "pending" for order in account["orders"])

    _append_paused_sessions(client, dataset, include_later_session=True)
    account = _observe_stored_paper(app, client, job["id"])
    assert account["fills"] == []
    pending = [order for order in account["orders"] if order["status"] == "pending"]
    assert len(pending) == 1
    assert pending[0]["signal_date"] == "2026-01-09"


def test_frozen_dataset_cannot_be_rewritten_or_marked_observed(client):
    dataset = _dataset(client, source_kind="synthetic")
    response = client.post("/api/datasets", headers=LOCAL, json={"name": "Rewrite", "source": "real supplier", "source_kind": "observed", "dataset_id": dataset["id"], "csv": PRICES.replace(",104,1500", ",103,1500")})
    assert response.status_code == 422
    response = client.post("/api/datasets", headers=LOCAL, json={"name": "Rename", "source": "real supplier", "source_kind": "observed", "dataset_id": dataset["id"], "csv": PRICES})
    assert response.status_code == 200
    assert response.json()["source_kind"] == "synthetic"


def test_process_recovery_preserves_reservation_and_does_not_retry(app):
    service = app.state.service
    dataset = service.load_demo()
    request = ExperimentInput(dataset_id=dataset["id"], symbol="DEMO_BOND", provider="none", budget_usd=1)
    interrupted = service.create_experiment(request.model_dump())
    interrupted.update(status="running", reserved_usd=0.75, spent_usd=0.10)
    service.store.put("experiment", interrupted)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/experiments/{interrupted['id']}")
        assert response.status_code == 200
        job = response.json()
        assert job["status"] == "interrupted"
        assert job["reserved_usd"] == 0.75
        assert job["spent_usd"] == 0.10
        assert "no se repite" in job["error"]
