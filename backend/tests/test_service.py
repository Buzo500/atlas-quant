"""Persistence and time-boundary integration tests, without paid API calls."""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from atlas_quant import service as service_module
from atlas_quant.service import Service
from atlas_quant.store import Store


FIXED_NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW if tz else FIXED_NOW.replace(tzinfo=None)


def price(day, close=100):
    return {"date": day, "symbol": "ETF", "open": close, "high": close,
            "low": close, "close": close, "volume": 10000, "currency": "EUR"}


def history(count=150):
    first = datetime(2024, 1, 1)
    return [price((first + timedelta(days=index)).date().isoformat(), 100 + index / 10)
            for index in range(count)]


def research_result():
    metrics = {"total_return": 0.2, "annualized_return": 0.2, "volatility": 0.12,
               "sharpe": 1.5, "max_drawdown": -0.05, "trade_count": 30,
               "costs": 15, "benchmark_return": 0.1, "excess_return": 0.1,
               "observations": 252}
    return {"selected_strategy": {"kind": "buy_hold", "symbol": "ETF"},
            "candidate_results": [], "train_period": {}, "validation_period": {},
            "test_period": {}, "out_of_sample": {"metrics": metrics, "curve": [], "trades": []},
            "full_result": {"metrics": metrics, "curve": [], "trades": []},
            "sensitivity": [{"cost_multiplier": 2, "period": "test", "metrics": dict(metrics)}],
            "data_hash": "fixed-for-offline-test", "warnings": []}


@pytest.fixture
def local_service(tmp_path, monkeypatch):
    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module, "now", lambda: FIXED_NOW.isoformat())
    monkeypatch.setattr(service_module, "run_research", lambda *args, **kwargs: research_result())
    store = Store(tmp_path / "atlas.sqlite3")
    return Service(store)


def add_dataset(service, data=None):
    return service.save_dataset(data or history(), "Test dataset", "observed", "Offline test fixture")


def request(dataset_id, **overrides):
    return {"dataset_id": dataset_id, "symbol": "ETF", "provider": "none", "model": None,
            "budget_usd": 1.0, "hours": 48, "auto_paper": True,
            "prompt": "Evaluate a predefined rule", "policy": {},
            "costs": {"initial_cash": 10000, "commission_bps": 5,
                      "slippage_bps": 5, "minimum_fee": 1.25}, **overrides}


def test_ledger_persists_and_snapshot_survives_reopening(local_service):
    dataset = add_dataset(local_service, history(2))
    events = [
        {"id": "deposit", "date": "2024-01-01", "kind": "deposit", "amount": "1000", "currency": "EUR"},
        {"id": "buy", "date": "2024-01-01", "kind": "buy", "symbol": "ETF", "quantity": "5", "price": "100", "fee": "1", "currency": "EUR"},
    ]
    local_service.store.put("ledger", {"id": dataset["id"], "events": events}, "ledger.imported")
    snapshot = local_service.portfolio(dataset["id"])
    reopened = Service(Store(local_service.store.path))
    assert reopened.portfolio(dataset["id"]) == snapshot
    assert snapshot["cash"] == 499
    assert snapshot["nav"] == 999.5
    assert snapshot["pnl"] == -0.5


def test_dataset_revision_rejected_atomically(local_service):
    dataset = add_dataset(local_service)
    revised = deepcopy(dataset["bars"])
    revised[0].update(open=500, high=500, low=500, close=500)
    with pytest.raises(ValueError, match="conservar"):
        local_service.save_dataset(revised, "Revision", "observed", "Different source", ident=dataset["id"])
    persisted = local_service.dataset(dataset["id"])
    assert persisted["bars"] == dataset["bars"]
    assert persisted["version"] == 1


def test_historical_insertion_cannot_rewrite_future_indicator_history(local_service):
    full = history()
    dataset = add_dataset(local_service, full[:50] + full[51:])
    local_service.create_experiment(request(dataset["id"]))
    # Even an unchanged old bar set is not enough: inserting a past missing bar
    # changes SMA inputs and can change the simulated forward fills retroactively.
    with pytest.raises(ValueError):
        local_service.save_dataset(full, "Past insertion", "observed", "Offline test fixture", ident=dataset["id"])


def test_queued_research_survives_restart_and_uses_frozen_version(local_service, monkeypatch):
    dataset = add_dataset(local_service)
    job = local_service.create_experiment(request(dataset["id"]))
    appended = [*dataset["bars"], price("2024-06-01", 150)]
    latest = local_service.save_dataset(appended, "Extended", "synthetic", "Changed label", ident=dataset["id"])
    assert latest["version"] == 2
    assert latest["source_kind"] == "observed"
    captured = []

    def capture_research(bars, candidates, **kwargs):
        captured.append(deepcopy(bars))
        return research_result()

    monkeypatch.setattr(service_module, "run_research", capture_research)
    restarted_store = Store(local_service.store.path)
    restarted_store.recover()
    assert restarted_store.get("experiment", job["id"])["status"] == "queued"
    asyncio.run(Service(restarted_store).tick())
    result = restarted_store.get("experiment", job["id"])
    assert captured == [dataset["bars"]]
    assert result["status"] == "observing"
    assert result["research"]["selected_strategy"] == {"kind": "buy_hold", "symbol": "ETF"}
    assert result["observation"]["new_sessions"] == 0
    assert any(item["event"] == "research.completed" for item in restarted_store.audit_list())


def test_elapsed_time_without_new_data_is_not_new_evidence(local_service):
    dataset = add_dataset(local_service)
    job = local_service.create_experiment(request(dataset["id"]))
    asyncio.run(local_service.tick())
    job = local_service.store.get("experiment", job["id"])
    job["observation_started_at"] = (FIXED_NOW - timedelta(hours=49)).isoformat()
    local_service.store.put("experiment", job)
    asyncio.run(local_service.tick())
    result = local_service.store.get("experiment", job["id"])
    assert result["status"] == "completed"
    assert result["observation"]["new_sessions"] == 0
    assert result["observation"]["forward_metrics"] is None
    assert result["gate"]["passed"] is False
    assert result["paper_account"] is None


def test_two_days_with_new_prices_cannot_promote_default_policy(local_service):
    dataset = add_dataset(local_service)
    job = local_service.create_experiment(request(dataset["id"]))
    asyncio.run(local_service.tick())
    job = local_service.store.get("experiment", job["id"])
    job["observation_started_at"] = "2026-09-03T00:00:00+00:00"
    local_service.store.put("experiment", job)
    local_service.save_dataset([*dataset["bars"], price("2026-09-04", 120), price("2026-09-05", 125)],
                               "Extended", "observed", dataset["source"], ident=dataset["id"])
    asyncio.run(local_service.tick())
    result = local_service.store.get("experiment", job["id"])
    assert result["observation"]["new_sessions"] == 2
    assert result["observation"]["forward_metrics"]["observations"] == 2
    assert result["gate"]["passed"] is False
    assert result["status"] == "completed"
    assert result["paper_account"] is None
    checks = {item["name"]: item for item in result["gate"]["checks"]}
    assert checks["new_forward_sessions"]["passed"] is False


def test_process_death_preserves_api_reservation_and_never_retries(local_service):
    dataset = add_dataset(local_service)
    job = local_service.create_experiment(request(dataset["id"]))
    job.update(status="running", phase="planning", spent_usd=0.1)
    local_service.store.put("experiment", job)

    async def interrupted_network(**kwargs):
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(local_service._call_ai(job, interrupted_network))
    crashed = local_service.store.get("experiment", job["id"])
    assert crashed["reserved_usd"] == pytest.approx(0.9)
    reopened = Store(local_service.store.path)
    reopened.recover()
    recovered = reopened.get("experiment", job["id"])
    assert recovered["status"] == "interrupted"
    assert recovered["reserved_usd"] == pytest.approx(0.9)
    assert recovered["spent_usd"] == pytest.approx(0.1)
    asyncio.run(Service(reopened).tick())
    assert reopened.get("experiment", job["id"])["status"] == "interrupted"


def test_future_prices_rejected_before_persistence(local_service):
    data = history()
    data.append(price("2026-09-06", 100))
    with pytest.raises(ValueError, match="futuras"):
        add_dataset(local_service, data)
    assert local_service.store.list("dataset") == []
