"""Wire contracts use real offline results, including nullable risk metrics.

Every store is isolated. The complete research lifecycle uses provider=none;
no external service, paid API or user dataset is used by these tests.
"""
import asyncio
from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from atlas_quant.app import create_app
from atlas_quant import __version__
from atlas_quant.contracts import (
    ExperimentResponse, PaperAccount, PortfolioResponse, ResearchResponse, ResearchResult,
    StateResponse,
)
from atlas_quant.paper import advance_paper, new_account
from export_contracts import DEFAULT_OUTPUT, render_openapi


LOCAL = {"x-atlas-client": "local-v1"}


@pytest.fixture
def offline_app(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return create_app(tmp_path, run_worker=False)


@pytest.mark.parametrize("path,method,status,model", [
    ("/api/health", "get", "200", "HealthResponse"),
    ("/api/state", "get", "200", "StateResponse"),
    ("/api/datasets/demo", "post", "200", "DatasetResponse"),
    ("/api/datasets", "post", "200", "DatasetResponse"),
    ("/api/feeds", "post", "200", "DatasetResponse"),
    ("/api/feeds/{ident}/refresh", "post", "200", "DatasetResponse"),
    ("/api/datasets/{ident}/portfolio", "get", "200", "PortfolioResponse"),
    ("/api/datasets/{ident}/ledger", "post", "200", "LedgerResponse"),
    ("/api/research", "post", "200", "ResearchResponse"),
    ("/api/experiments", "post", "201", "ExperimentResponse"),
    ("/api/experiments/{ident}", "get", "200", "ExperimentResponse"),
    ("/api/experiments/{ident}/control", "post", "200", "ExperimentResponse"),
    ("/api/settings", "post", "200", "SettingsResponse"),
])
def test_openapi_declares_response_contract(offline_app, path, method, status, model):
    schema = offline_app.openapi()
    response = schema["paths"][path][method]["responses"][status]["content"]["application/json"]["schema"]
    assert response == {"$ref": f"#/components/schemas/{model}"}
    assert schema["components"]["schemas"][model]["properties"]


def test_frontend_types_match_current_openapi(offline_app):
    assert DEFAULT_OUTPUT.is_file(), "Genera los contratos con python tools/export_contracts.py."
    assert DEFAULT_OUTPUT.read_text(encoding="utf-8") == render_openapi(offline_app.openapi()), (
        "Los contratos de frontend deben regenerarse después de cambiar OpenAPI."
    )


def test_release_version_matches_health_openapi_and_frontend(offline_app):
    frontend = DEFAULT_OUTPUT.parents[1]
    assert json.loads((frontend / "package.json").read_text(encoding="utf-8"))["version"] == __version__
    assert offline_app.openapi()["info"]["version"] == __version__
    with TestClient(offline_app) as client:
        assert client.get("/api/health").json()["version"] == __version__


def test_real_offline_lifecycle_preserves_typed_results(offline_app):
    with TestClient(offline_app) as client:
        demo = client.post("/api/datasets/demo", headers=LOCAL)
        assert demo.status_code == 200, demo.text
        dataset = demo.json()
        portfolio = client.get(f"/api/datasets/{dataset['id']}/portfolio")
        assert portfolio.status_code == 200, portfolio.text
        assert PortfolioResponse.model_validate(portfolio.json()).model_dump() == offline_app.state.service.portfolio(dataset["id"])

        body = {"dataset_id": dataset["id"], "symbol": "DEMO_BOND", "provider": "none", "budget_usd": 0}
        created = client.post("/api/experiments", headers=LOCAL, json=body)
        assert created.status_code == 201, created.text
        ident = created.json()["id"]
        asyncio.run(offline_app.state.service.tick())

        response = client.get(f"/api/experiments/{ident}")
        assert response.status_code == 200, response.text
        job = response.json()
        assert job["status"] == "observing"
        assert job["spent_usd"] == job["reserved_usd"] == job["budget_usd"] == 0
        assert job["paper_account"] is None
        assert ExperimentResponse.model_validate(job).model_dump(exclude_unset=True) == job
        assert ResearchResult.model_validate(job["research"]).model_dump(exclude_unset=True) == job["research"]

        state_response = client.get("/api/state")
        assert state_response.status_code == 200, state_response.text
        state = state_response.json()
        assert StateResponse.model_validate(state).model_dump(exclude_unset=True) == state
        assert all(not provider["configured"] for provider in state["providers"])
        assert all("bars" not in item for item in state["datasets"])
        assert all("research" not in item and "plan" not in item and "forward_result" not in item for item in state["experiments"])
        assert job["research"]["out_of_sample"]["metrics"]["observations"] == 220


def test_manual_research_contract_requires_complete_evidence(offline_app):
    with TestClient(offline_app) as client:
        dataset = client.post("/api/datasets/demo", headers=LOCAL).json()
        response = client.post("/api/research", headers=LOCAL, json={"dataset_id": dataset["id"], "symbol": "DEMO_BOND"})
        assert response.status_code == 200, response.text
        research = response.json()
        assert ResearchResponse.model_validate(research).model_dump(exclude_unset=True) == research
        del research["out_of_sample"]
        with pytest.raises(ValidationError):
            ResearchResponse.model_validate(research)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_response_contract_rejects_nonfinite_portfolio(bad):
    snapshot = {"nav": 0, "cash": bad, "net_contributions": 0, "pnl": 0, "twr": 0,
                "positions": [], "curve": [], "warnings": []}
    with pytest.raises(ValidationError):
        PortfolioResponse.model_validate(snapshot)


def test_http_boundary_rejects_malformed_domain_response(offline_app, monkeypatch):
    monkeypatch.setattr(offline_app.state.service, "portfolio", lambda _: {"nav": 100})
    with TestClient(offline_app, raise_server_exceptions=False) as client:
        response = client.get("/api/datasets/invalid/portfolio")
    assert response.status_code == 500


def test_public_state_omits_internal_ownership_tokens(offline_app):
    with TestClient(offline_app) as client:
        dataset = client.post("/api/datasets/demo", headers=LOCAL).json()
        response = client.post("/api/experiments", headers=LOCAL, json={
            "dataset_id": dataset["id"], "symbol": "DEMO_BOND", "provider": "none", "budget_usd": 0,
        })
        job = response.json()
        store = offline_app.state.service.store
        job.update(execution_active=True, execution_token="private-executor-token")
        store.put("experiment", job)
        stored_dataset = store.get("dataset", dataset["id"])
        stored_dataset["feed"] = {"symbol": "DEMO_BOND", "start": "2026-01-01",
                                  "last_attempt": "2026-09-06T00:00:00+00:00", "error": None,
                                  "interval_hours": 6, "request_id": "private-download-token"}
        store.put("dataset", stored_dataset)

        state = client.get("/api/state")
        assert state.status_code == 200, state.text
        assert state.json()["experiments"][0]["execution_active"] is True
        assert "private-executor-token" not in state.text
        assert "private-download-token" not in state.text
        assert "execution_token" not in state.json()["experiments"][0]
        assert "request_id" not in state.json()["datasets"][0]["feed"]
        detail = client.get(f"/api/experiments/{job['id']}")
        assert detail.status_code == 200, detail.text
        assert "execution_token" not in detail.json()


def test_paper_contract_preserves_signals_fills_and_history():
    bars = [{"date": day, "symbol": "DEMO", "open": 100, "high": 102,
             "low": 99, "close": 101, "volume": 1000, "currency": "EUR"}
            for day in ("2026-01-05", "2026-01-06")]
    account = advance_paper(new_account(1000, started_at_date="2026-01-04"), bars,
                            {"kind": "buy_hold", "symbol": "DEMO"}, enabled=True)
    assert account["orders"][0]["status"] == "filled"
    assert len(account["fills"]) == 1
    assert PaperAccount.model_validate(account).model_dump(exclude_unset=True) == account
    summary = deepcopy(account)
    del summary["observed_bars"]
    assert PaperAccount.model_validate(summary).model_dump(exclude_unset=True) == summary
