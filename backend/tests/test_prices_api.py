"""Daily chart reads preserve immutable evidence and never use external services."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, timedelta
import sqlite3
import threading

import pytest
from fastapi.testclient import TestClient

from atlas_quant import datasets, feed
from atlas_quant.app import create_app
from atlas_quant.contracts import DatasetPricesResponse
from atlas_quant.prices import MAX_PRICE_BARS


LOCAL = {"x-atlas-client": "local-v1"}
CSV = """date,symbol,open,high,low,close,volume,currency
2020-03-03,ETF,13.25,15.125,12.25,14.625,12.5,EUR
2020-02-27,OTHER,40,41,39,40,100,EUR
2020-02-28,ETF,10.125,12.25,9.0625,11.375,0,EUR
2020-03-02,ETF,11.375,14.5,10.5,13.25,100.25,EUR
"""


@pytest.fixture
def chart_app(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app = create_app(tmp_path, run_worker=False)
    with TestClient(app) as client:
        response = client.post("/api/datasets", headers=LOCAL, json={
            "csv": CSV, "name": "Daily evidence", "source_kind": "observed", "source": "Offline fixture",
        })
        assert response.status_code == 200, response.text
        yield app, client, response.json()


def query(client, dataset, **params):
    return client.get(f"/api/datasets/{dataset['id']}/prices", params={
        "version": dataset["version"], "symbol": "ETF", **params,
    })


def logical_dump(path):
    with sqlite3.connect(path) as connection:
        return "\n".join(connection.iterdump())


def test_daily_prices_are_faithful_scoped_and_read_only(chart_app, monkeypatch):
    app, client, dataset = chart_app
    service = app.state.service
    stored = service.store.get_dataset_version(dataset["id"], 1)
    before = logical_dump(service.store.path)
    service.wake.clear()

    def unexpected(*args, **kwargs):
        pytest.fail("A chart read must not download, write records, or audit.")

    monkeypatch.setattr(feed, "fetch_daily", unexpected)
    monkeypatch.setattr(service.store, "put", unexpected)
    monkeypatch.setattr(service.store, "save_dataset", unexpected)
    monkeypatch.setattr(service.store, "audit", unexpected)
    response = query(client, dataset)
    assert response.status_code == 200, response.text
    result = response.json()
    assert DatasetPricesResponse.model_validate(result).model_dump() == result
    assert result["bars"] == [
        {field: bar[field] for field in ("date", "open", "high", "low", "close", "volume")}
        for bar in stored["bars"] if bar["symbol"] == "ETF"
    ]
    assert [bar["date"] for bar in result["bars"]] == ["2020-02-28", "2020-03-02", "2020-03-03"]
    assert result["bars"][0]["volume"] == 0
    assert result["source_kind"] == "observed"
    assert result["source"] == "Offline fixture"
    assert result["source_metadata"] is None
    assert result["currency"] == "EUR"
    assert result["price_basis"] == "unspecified"
    assert result["calendar"] == "provided_rows_only"
    assert result["warnings"] == dataset["manifest"]["warnings"]
    assert result["manifest_hash"] == dataset["manifest"]["sha256"]
    assert result["dataset_id"] == dataset["id"]
    assert result["dataset_version"] == 1
    assert result["available_start"] == result["first_date"] == "2020-02-28"
    assert result["available_end"] == result["last_date"] == "2020-03-03"
    assert result["preceding_close"] is result["preceding_date"] is None
    assert "OTHER" not in response.text
    assert "corporate_actions" not in result
    assert response.headers["cache-control"] == "no-store"
    assert not service.wake.is_set()
    assert logical_dump(service.store.path) == before


@pytest.mark.parametrize("start,end,dates,preceding", [
    ("2020-03-02", "2020-03-03", ["2020-03-02", "2020-03-03"], ("2020-02-28", 11.375)),
    ("2020-02-29", "2020-03-02", ["2020-03-02"], ("2020-02-28", 11.375)),
    ("2020-03-03", "2020-03-03", ["2020-03-03"], ("2020-03-02", 13.25)),
    (None, "2020-02-28", ["2020-02-28"], (None, None)),
    ("2020-03-03", None, ["2020-03-03"], ("2020-03-02", 13.25)),
])
def test_inclusive_dates_and_preceding_session_not_calendar_day(chart_app, start, end, dates, preceding):
    _, client, dataset = chart_app
    response = query(client, dataset, **{key: value for key, value in (("start", start), ("end", end))
                                       if value is not None})
    assert response.status_code == 200, response.text
    result = response.json()
    assert [bar["date"] for bar in result["bars"]] == dates
    assert (result["preceding_date"], result["preceding_close"]) == preceding
    assert (result["first_date"], result["last_date"]) == (dates[0], dates[-1])
    assert (result["available_start"], result["available_end"]) == ("2020-02-28", "2020-03-03")


@pytest.mark.parametrize("start,end", [
    ("2020-02-29", "2020-03-01"), ("2019-01-01", "2019-12-31"), ("2021-01-01", "2021-12-31"),
])
def test_empty_range_is_explicit_and_has_no_imputed_price(chart_app, start, end):
    _, client, dataset = chart_app
    response = query(client, dataset, start=start, end=end)
    assert response.status_code == 200
    result = response.json()
    assert result["bars"] == []
    assert result["first_date"] is result["last_date"] is result["preceding_close"] is result["preceding_date"] is None
    assert "No hay sesiones" in result["warnings"][-1]
    assert (result["available_start"], result["available_end"]) == ("2020-02-28", "2020-03-03")


@pytest.mark.parametrize("params", [
    {"start": "2020-02-30"}, {"end": "2019-02-29"}, {"start": "2020-13-01"},
    {"start": "20200302"}, {"end": "2020-W10-1"}, {"start": "2020-3-2"},
    {"start": "2020-03-02T00:00:00"}, {"start": ""}, {"end": "0000-01-01"},
    {"start": "2020-03-03", "end": "2020-03-02"},
    {"version": 0}, {"version": -1}, {"version": "latest"}, {"version": "1.5"},
    {"symbol": ""}, {"symbol": "A" * 51},
])
def test_invalid_queries_are_rejected(chart_app, params):
    _, client, dataset = chart_app
    response = query(client, dataset, **params)
    assert response.status_code == 422, response.text
    assert "detail" in response.json()


def test_version_and_symbol_are_required_and_unknown_evidence_is_not_substituted(chart_app):
    _, client, dataset = chart_app
    url = f"/api/datasets/{dataset['id']}/prices"
    assert client.get(url, params={"symbol": "ETF"}).status_code == 422
    assert client.get(url, params={"version": 1}).status_code == 422
    assert query(client, dataset, symbol="MISSING").status_code == 404
    assert query(client, dataset, symbol="etf").status_code == 404
    assert query(client, dataset, version=2).status_code == 404
    assert query(client, {"id": "unknown", "version": 1}).status_code == 404


def test_old_version_survives_concurrent_append_without_reading_latest(chart_app, monkeypatch):
    app, client, dataset = chart_app
    service = app.state.service
    old = service.store.get_dataset_version(dataset["id"], 1)
    started, release = threading.Event(), threading.Event()
    original_project = datasets.project_prices

    def blocked_projection(snapshot, *args):
        assert snapshot == old
        started.set()
        assert release.wait(5)
        return original_project(snapshot, *args)

    monkeypatch.setattr(datasets, "project_prices", blocked_projection)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(query, client, dataset)
        try:
            assert started.wait(5)
            appended = {**old["bars"][-1], "date": "2020-03-04", "close": 14.75}
            new = service.save_dataset([*old["bars"], appended], "New version", "observed", "Offline fixture", old["id"])
            assert new["version"] == 2
        finally:
            release.set()
        result = pending.result(timeout=5)
    assert result.status_code == 200, result.text
    assert result.json()["dataset_version"] == 1
    assert result.json()["manifest_hash"] == old["manifest"]["sha256"]
    assert result.json()["last_date"] == "2020-03-03"
    assert service.store.get_dataset_version(old["id"], 1) == old
    monkeypatch.setattr(datasets, "project_prices", original_project)
    latest = query(client, new).json()
    assert latest["last_date"] == "2020-03-04"
    assert latest["manifest_hash"] != result.json()["manifest_hash"]


def test_limit_rejects_excess_without_truncation_and_accepts_exact_bound(chart_app):
    app, client, _ = chart_app
    assert MAX_PRICE_BARS == 100_000
    # Appended versions can outgrow the single-import limit. Historical dates
    # stay valid; this stress fixture does not download or alter ordinary data.
    beginning = date(1700, 1, 1)
    bars = [{"date": (beginning + timedelta(days=index)).isoformat(), "symbol": "LONG",
             "open": 10.0, "high": 10.0, "low": 10.0, "close": 10.0, "volume": 0.0, "currency": "EUR"}
            for index in range(MAX_PRICE_BARS + 1)]
    dataset = app.state.service.save_dataset(bars, "Long", "synthetic", "Offline limit fixture")
    rejected = query(client, dataset, symbol="LONG")
    assert rejected.status_code == 422
    assert "100.000" in rejected.json()["detail"]
    assert "Recorta" in rejected.json()["detail"]
    accepted = query(client, dataset, symbol="LONG", end=bars[-2]["date"])
    assert accepted.status_code == 200, accepted.text[:1000]
    result = accepted.json()
    assert len(result["bars"]) == MAX_PRICE_BARS
    assert result["last_date"] == bars[-2]["date"]
    assert result["available_end"] == bars[-1]["date"]


def test_synthetic_origin_is_visible(chart_app):
    _, client, _ = chart_app
    demo = client.post("/api/datasets/demo", headers=LOCAL).json()
    response = query(client, demo, symbol="DEMO_WORLD")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["source_kind"] == "synthetic"
    assert any("sintéticos" in warning for warning in result["warnings"])


def test_provider_metadata_is_exact_without_adjusting_or_filling_bars(chart_app, monkeypatch):
    app, client, _ = chart_app

    class OfflineFrame:
        columns = ["Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits"]

        def iterrows(self):
            return iter([
                ("2020-03-02", {"Open": 100, "High": 100, "Low": 100, "Close": 100,
                                "Volume": 0, "Dividends": 0, "Stock Splits": 0}),
                ("2020-03-04", {"Open": 50, "High": 50, "Low": 50, "Close": 50,
                                "Volume": 1, "Dividends": 1.5, "Stock Splits": 2}),
            ])

    monkeypatch.setattr(feed, "_today_utc", lambda: date(2020, 3, 5))
    monkeypatch.setattr(feed, "_bounded_snapshot", lambda *args: (OfflineFrame(), {
        "currency": "EUR", "symbol": "ETF", "instrumentType": "ETF",
        "exchangeName": "GER", "exchangeTimezoneName": "Europe/Berlin",
    }, "offline-test"))
    snapshot = feed.fetch_daily("ETF", "2020-03-01")
    dataset = app.state.service.save_dataset(snapshot["bars"], "Feed fixture", "observed", snapshot["source"],
        extras={key: deepcopy(snapshot[key]) for key in ("source_metadata", "warnings", "corporate_actions")})
    response = query(client, dataset)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["source_metadata"] == snapshot["source_metadata"]
    assert result["price_basis"] == "provider_ohlc_auto_adjust_false"
    assert result["source_metadata"]["exchange_timezone"] == "Europe/Berlin"
    assert result["source_metadata"]["auto_adjust"] is False
    assert result["source_metadata"]["corporate_actions_applied"] is False
    assert [bar["close"] for bar in result["bars"]] == [100, 50]
    assert [bar["date"] for bar in result["bars"]] == ["2020-03-02", "2020-03-04"]
    assert all(warning in result["warnings"] for warning in snapshot["warnings"])


def test_openapi_prices_contract_is_explicit(chart_app):
    app, _, _ = chart_app
    operation = app.openapi()["paths"]["/api/datasets/{ident}/prices"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DatasetPricesResponse",
    }
    required = {parameter["name"] for parameter in operation["parameters"] if parameter["required"]}
    assert required == {"ident", "version", "symbol"}
