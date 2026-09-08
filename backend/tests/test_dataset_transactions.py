"""Deterministic races with separate repositories, isolated SQLite and fake feeds."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import threading

import pytest

from atlas_quant import feed
from atlas_quant.data import build_provenance_manifest
from atlas_quant.datasets import DatasetService
from atlas_quant.store import Store


NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


def price(day, value=100):
    return {"date": f"2026-01-{day:02d}", "symbol": "ETF", "open": value, "high": value,
            "low": value, "close": value, "volume": 1000, "currency": "EUR"}


def service(path):
    return DatasetService(Store(path), clock=lambda: NOW, timestamp=lambda: NOW.isoformat())


def dataset(instance):
    return instance.save_dataset([price(1)], "Original", "observed", "Offline source", extras={
        "feed": {"symbol": "ETF", "start": "2026-01-01", "last_attempt": "2026-01-01T00:00:00+00:00",
                 "error": None, "interval_hours": 6}})


def snapshot(bars):
    return {"bars": bars, "source": "Offline feed", "corporate_actions": [],
            "source_metadata": {"currency": "EUR"}, "warnings": []}


async def wait_started(event):
    assert await asyncio.to_thread(event.wait, 5), "Simulated feed did not start"


@pytest.mark.parametrize("outcome", ["failure", "older_success", "newer_success"])
def test_refresh_and_import_preserve_latest_version_and_metadata(tmp_path, monkeypatch, outcome):
    first = service(tmp_path / "race.sqlite3")
    second = service(first.store.path)
    original = dataset(first)
    started, release = threading.Event(), threading.Event()

    def fetch(*args):
        started.set()
        assert release.wait(5)
        if outcome == "failure":
            raise RuntimeError("private transport detail")
        return snapshot([price(1)] if outcome == "older_success" else [price(1), price(2), price(3)])

    monkeypatch.setattr(feed, "fetch_daily", fetch)

    async def race():
        refresh = asyncio.create_task(first.refresh_feed(original["id"]))
        try:
            await wait_started(started)
            imported = second.save_dataset([price(1), price(2)], "Renamed concurrently", "synthetic",
                "Changed source", original["id"], extras={"notes": "retain this metadata"})
            assert imported["version"] == 2
        finally:
            release.set()
        return await asyncio.wait_for(refresh, 5)

    returned = asyncio.run(race())
    current = first.dataset(original["id"])
    assert returned == current
    assert current["name"] == "Renamed concurrently"
    assert current["notes"] == "retain this metadata"
    assert current["source_kind"] == "observed"
    assert current["source"] == "Offline source"
    assert current["version"] == (3 if outcome == "newer_success" else 2)
    assert current["bars"] == ([price(1), price(2), price(3)] if outcome == "newer_success" else [price(1), price(2)])
    assert first.store.get_dataset_version(original["id"], 1)["bars"] == [price(1)]
    assert first.store.get_dataset_version(original["id"], 2)["bars"] == [price(1), price(2)]
    if outcome == "newer_success":
        assert current["feed"]["error"] is None
    else:
        assert current["feed"]["error"]
        assert "private transport" not in current["feed"]["error"]
    assert "request_id" not in current["feed"]


@pytest.mark.parametrize("older_fails", [False, True])
def test_overlapping_refresh_ignores_old_completion(tmp_path, monkeypatch, older_fails):
    first = service(tmp_path / "overlap.sqlite3")
    second = service(first.store.path)
    original = dataset(first)
    started, release = threading.Event(), threading.Event()
    lock = threading.Lock()
    calls = 0

    def fetch(*args):
        nonlocal calls
        with lock:
            calls += 1
            order = calls
        if order == 1:
            started.set()
            assert release.wait(5)
            if older_fails:
                raise ValueError("Older request failed")
            return snapshot([price(1), price(2)])
        return snapshot([price(1), price(2), price(3)])

    monkeypatch.setattr(feed, "fetch_daily", fetch)

    async def race():
        older = asyncio.create_task(first.refresh_feed(original["id"]))
        try:
            await wait_started(started)
            newer = await second.refresh_feed(original["id"])
        finally:
            release.set()
        return await older, newer

    old_result, new_result = asyncio.run(race())
    assert old_result == new_result == first.dataset(original["id"])
    assert new_result["version"] == 2
    assert new_result["bars"] == [price(1), price(2), price(3)]
    assert new_result["feed"]["error"] is None
    assert len([entry for entry in first.store.audit_list() if entry["event"] == "feed.refreshed"]) == 1
    assert not any(entry["event"] == "feed.failed" for entry in first.store.audit_list())


def test_manual_refresh_rate_limit_is_atomic_across_services(tmp_path, monkeypatch):
    first = service(tmp_path / "rate.sqlite3")
    second = service(first.store.path)
    original = dataset(first)
    started, release = threading.Event(), threading.Event()
    calls = []

    def fetch(*args):
        calls.append(args)
        started.set()
        assert release.wait(5)
        return snapshot([price(1), price(2)])

    monkeypatch.setattr(feed, "fetch_daily", fetch)

    async def race():
        active = asyncio.create_task(first.refresh_feed(original["id"], min_interval_seconds=60))
        try:
            await wait_started(started)
            with pytest.raises(ValueError, match="minuto"):
                await second.refresh_feed(original["id"], min_interval_seconds=60)
        finally:
            release.set()
        await active

    asyncio.run(race())
    assert len(calls) == 1


def test_stale_import_cannot_drop_newer_bars_even_with_separate_stores(tmp_path):
    first = service(tmp_path / "imports.sqlite3")
    second = service(first.store.path)
    original = dataset(first)
    stale = {**deepcopy(original), "bars": [price(1), price(2)]}
    saved = first.save_dataset([price(1), price(2), price(3)], "Latest", "observed", "source", original["id"])
    audit = first.store.audit_list()
    with pytest.raises(ValueError, match="conservar"):
        second.store.save_dataset(stale)
    assert second.dataset(original["id"]) == saved
    assert first.store.audit_list() == audit
    assert first.store.get_dataset_version(original["id"], 3) is None


def test_two_simultaneous_incompatible_imports_commit_only_one(tmp_path):
    first = service(tmp_path / "parallel.sqlite3")
    second = service(first.store.path)
    original = dataset(first)
    barrier = threading.Barrier(2)

    def save(instance, value):
        barrier.wait(5)
        try:
            instance.save_dataset([price(1), price(2, value)], "Extended", "synthetic", "changed", original["id"])
            return "committed"
        except ValueError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(save, first, 101)
        two = pool.submit(save, second, 102)
        assert sorted([one.result(5), two.result(5)]) == ["committed", "conflict"]
    current = first.dataset(original["id"])
    assert current["version"] == 2
    assert len(current["bars"]) == 2
    assert current["source_kind"] == "observed"
    expected_manifest = build_provenance_manifest(
        current["bars"], current["name"], current["source_kind"], current["source"])
    assert {key: value for key, value in current["manifest"].items() if key != "generated_at"} == {
        key: value for key, value in expected_manifest.items() if key != "generated_at"}


@pytest.mark.parametrize("same_id", [False, True])
def test_concurrent_ledger_import_preserves_events_and_idempotency(tmp_path, same_id):
    first = service(tmp_path / "ledger.sqlite3")
    second = service(first.store.path)
    original = dataset(first)
    barrier = threading.Barrier(2)

    def import_event(instance, ident):
        barrier.wait(5)
        csv = f"id,date,kind,amount,currency\n{ident},2026-01-01,deposit,1000,EUR\n"
        return instance.import_ledger(original["id"], csv, commit=True, require_preview=False)

    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(import_event, first, "deposit-1")
        two = pool.submit(import_event, second, "deposit-1" if same_id else "deposit-2")
        results = [one.result(5), two.result(5)]
    expected = 1 if same_id else 2
    assert sum(result["added"] for result in results) == expected
    assert len(first.store.get("ledger", original["id"])["events"]) == expected
    assert first.portfolio(original["id"])["nav"] == expected * 1000


def test_ledger_rejection_rolls_back_ledger_and_audit(tmp_path):
    instance = service(tmp_path / "ledger-reject.sqlite3")
    original = dataset(instance)
    csv = "id,date,kind,amount,currency\ndeposit-1,2026-01-01,deposit,1000,EUR\n"
    instance.import_ledger(original["id"], csv, commit=True, require_preview=False)
    before = instance.store.get("ledger", original["id"])
    audit = instance.store.audit_list()
    with pytest.raises(ValueError, match="contenido diferente"):
        instance.import_ledger(original["id"], csv.replace("1000", "2000"), commit=True, require_preview=False)
    assert instance.store.get("ledger", original["id"]) == before
    assert instance.store.audit_list() == audit


def test_atomic_update_prevents_lost_updates_across_stores(tmp_path):
    one = Store(tmp_path / "update.sqlite3")
    two = Store(one.path)
    one.put("counter", {"id": "main", "value": 0})
    barrier = threading.Barrier(2)

    def increment(store):
        barrier.wait(5)
        for _ in range(15):
            store.update("counter", "main", lambda current: {**current, "value": current["value"] + 1})

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(increment, one), pool.submit(increment, two)
        a.result(10)
        b.result(10)
    assert one.get("counter", "main")["value"] == 30


def test_atomic_multi_record_failure_rolls_back_records_and_audit(tmp_path):
    store = Store(tmp_path / "rollback.sqlite3")
    store.put("settings", {"id": "main", "kill_switch": True})

    def failed(work):
        work.put("settings", {"id": "main", "kill_switch": False}, "settings.changed")
        work.put("experiment", {"id": "job", "status": "running"})
        raise ValueError("validation failed")

    with pytest.raises(ValueError, match="validation failed"):
        store.atomic(failed)
    assert store.get("settings", "main")["kill_switch"] is True
    assert store.get("experiment", "job") is None
    assert store.audit_list() == []


def test_skipped_mutator_does_not_change_record_or_audit(tmp_path):
    store = Store(tmp_path / "skip.sqlite3")
    original = store.put("record", {"id": "item", "nested": {"value": 1}})

    def skip(current):
        current["nested"]["value"] = 2
        return None

    assert store.update("record", "item", skip, "should.not.appear") == original
    assert store.get("record", "item") == original
    assert store.audit_list() == []


def test_concurrent_demo_load_is_single_complete_dataset_and_ledger(tmp_path, monkeypatch):
    class DemoClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz) if tz is not None else NOW.replace(tzinfo=None)

    # The real generator and the services must use the same fixed day; wall-clock
    # demo dates otherwise become "future" dates after this fixture's NOW.
    monkeypatch.setattr("atlas_quant.data.datetime", DemoClock)
    one = service(tmp_path / "demo.sqlite3")
    two = service(one.store.path)
    barrier = threading.Barrier(2)

    def load(instance):
        barrier.wait(5)
        return instance.load_demo()

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(load, one), pool.submit(load, two)
        assert a.result(15)["id"] == b.result(15)["id"]
    datasets = one.store.list("dataset")
    assert len(datasets) == 1
    assert len(one.store.list("ledger")) == 1
    assert len(datasets[0]["bars"]) == 3300
    assert datasets[0]["bars"][-1]["date"] == "2026-09-04"
    assert len(one.store.get("ledger", datasets[0]["id"])["events"]) == 6
    assert one.portfolio(datasets[0]["id"])["nav"] > 0


@pytest.mark.parametrize("status,reserve,active,expected", [
    ("running", 0, True, "interrupted"), ("paused", 1, True, "interrupted"),
    ("cancelled", 1, True, "cancelled"), ("paused", 0, False, "paused"),
])
def test_recovery_does_not_reactivate_controls_or_release_uncertain_reserve(tmp_path, status, reserve, active, expected):
    store = Store(tmp_path / "recover.sqlite3")
    store.put("experiment", {"id": "job", "status": status, "reserved_usd": reserve,
                             "execution_active": active, "execution_token": "old-owner", "control_requested": "pause"})
    store.recover()
    result = store.get("experiment", "job")
    assert result["status"] == expected
    assert result["reserved_usd"] == reserve
    assert result["execution_active"] is False
    if active:
        assert "execution_token" not in result
        assert result["control_requested"] is None
