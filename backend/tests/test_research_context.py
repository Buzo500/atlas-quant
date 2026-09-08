"""Manual results describe the snapshot actually calculated, including races."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, datetime, timedelta
import threading

import pytest
from fastapi.testclient import TestClient

from atlas_quant import app as app_module
from atlas_quant.app import create_app
from atlas_quant.contracts import ResearchResponse


LOCAL = {"x-atlas-client": "local-v1"}
COSTS = {"initial_cash": 15000.0, "commission_bps": 3.0, "slippage_bps": 7.0,
         "minimum_fee": 1.5, "max_position_weight": 0.4}


def prices():
    return [{"date": (date(2024, 1, 1) + timedelta(days=index)).isoformat(), "symbol": "DEMO",
             "open": 100 + index * 0.1, "high": 102 + index * 0.1, "low": 99 + index * 0.1,
             "close": 101 + index * 0.1, "volume": 1000, "currency": "EUR"} for index in range(300)]


@pytest.fixture
def offline(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app = create_app(tmp_path, run_worker=False)
    service = app.state.service
    dataset = service.save_dataset(prices(), "Snapshot original", "synthetic", "Offline fixture")
    with TestClient(app) as client:
        yield service, client, dataset


def test_manual_result_has_complete_execution_identity_and_audit(offline):
    service, client, dataset = offline
    request = {"dataset_id": dataset["id"], "symbol": "DEMO", "costs": COSTS}
    response = client.post("/api/research", headers=LOCAL, json=request)
    assert response.status_code == 200, response.text
    result = response.json()
    assert ResearchResponse.model_validate(result).model_dump(exclude_unset=True) == result
    context = result["execution"]
    assert context["dataset_id"] == dataset["id"]
    assert context["dataset_name"] == dataset["name"]
    assert context["dataset_version"] == dataset["version"]
    assert context["dataset_manifest_hash"] == dataset["manifest"]["sha256"]
    assert context["symbol"] == "DEMO"
    assert context["costs"] == COSTS
    assert context["period"] == {"start": dataset["bars"][0]["date"],
                                 "end": dataset["bars"][-1]["date"], "observations": 300}
    assert datetime.fromisoformat(context["started_at"]) <= datetime.fromisoformat(context["completed_at"])
    audit = next(entry for entry in service.store.audit_list() if entry["event"] == "research.manual")
    assert audit["details"]["execution"] == context
    assert audit["details"]["data_hash"] == result["data_hash"]
    repeated = client.post("/api/research", headers=LOCAL, json=request).json()
    assert repeated["execution"]["id"] != context["id"]
    assert repeated["data_hash"] == result["data_hash"]


def test_dataset_update_during_calculation_cannot_relabel_the_result(offline, monkeypatch):
    service, client, dataset = offline
    calculating, release = threading.Event(), threading.Event()
    actual_run = app_module.run_research
    captured = {}

    def delayed_research(bars, candidates, **costs):
        captured.update(bars=deepcopy(bars), costs=deepcopy(costs))
        calculating.set()
        assert release.wait(5)
        result = actual_run(bars, candidates, **costs)
        captured["hash"] = result["data_hash"]
        return result

    monkeypatch.setattr(app_module, "run_research", delayed_research)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, "/api/research", headers=LOCAL,
                              json={"dataset_id": dataset["id"], "symbol": "DEMO", "costs": COSTS})
        try:
            assert calculating.wait(5)
            updated_bars = deepcopy(dataset["bars"])
            updated_bars.append({**updated_bars[-1], "date": "2024-10-27"})
            latest = service.save_dataset(updated_bars, "Nombre posterior", "synthetic", "Offline fixture",
                                          dataset["id"])
            assert latest["version"] == dataset["version"] + 1
        finally:
            release.set()
        response = pending.result(10)
    assert response.status_code == 200, response.text
    result = response.json()
    assert captured["bars"] == dataset["bars"]
    assert captured["costs"] == COSTS
    assert result["execution"]["dataset_name"] == "Snapshot original"
    assert result["execution"]["dataset_version"] == 1
    assert result["execution"]["dataset_manifest_hash"] == dataset["manifest"]["sha256"]
    assert result["execution"]["period"]["end"] == dataset["bars"][-1]["date"]
    assert result["data_hash"] == captured["hash"]
    assert service.dataset(dataset["id"])["name"] == "Nombre posterior"
