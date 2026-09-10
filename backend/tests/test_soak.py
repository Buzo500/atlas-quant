"""Release evidence must not pass after sleep, a crash, a data change or a lost monitor."""
from dataclasses import replace
import os
import sqlite3
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from atlas_quant.backup import create_backup
from atlas_quant.store import Store, SCHEMA_VERSION
from atlas_runtime import atomic_json, read_json
import soak_atlas as soak


def sample(moment, **values):
    return {"wall": moment, "monotonic": moment, "issues": [], "rss_bytes": 100,
            "cpu_percent": 0, "at": soak.timestamp(moment), **values}


@pytest.mark.parametrize("wall, monotonic, expected", [
    (3600, 3600, "sampling_gap_or_suspend"),
    (3600, 60, "clock_discontinuity"),
    (60, 3600, "clock_discontinuity"),
    (-1, 60, "clock_reversed"),
])
def test_sleep_gaps_and_clock_changes_never_count_towards_48_hours(wall, monotonic, expected):
    detector = soak.Detector(soak.Limits())
    assert not detector.accept(sample(0))
    assert expected in detector.accept(sample(wall, monotonic=monotonic))
    assert detector.accepted_seconds == 0


def test_unhealthy_interval_is_not_accepted_and_resources_need_consecutive_samples():
    limits = replace(soak.Limits(), max_rss_bytes=200, max_rss_growth_bytes=200,
                     resource_consecutive_samples=3)
    detector = soak.Detector(limits)
    detector.accept(sample(0))
    assert detector.accept(sample(60, issues=["health_failure"])) == ["health_failure"]
    assert detector.accepted_seconds == 0
    assert not detector.accept(sample(120, rss_bytes=250))
    assert not detector.accept(sample(180, rss_bytes=250))
    assert not detector.accept(sample(240, rss_bytes=100))  # Recovery clears the streak.
    assert not detector.accept(sample(300, rss_bytes=250))
    assert not detector.accept(sample(360, rss_bytes=250))
    assert detector.accept(sample(420, rss_bytes=250)) == ["sustained_resource_threshold"]


@pytest.fixture
def demo(tmp_path):
    dbpath = tmp_path / "var/atlas/atlas.sqlite3"
    store = Store(dbpath)
    store.put("dataset", {"id": "demo", "source_kind": "synthetic", "bars": []})
    store.put("ledger", {"id": "demo", "events": [{"id": "deposit", "date": "2026-01-01", "kind": "deposit", "amount": 123}]})
    store.put("experiment", {"id": "job", "provider": "none", "budget_usd": 0,
        "spent_usd": 0, "reserved_usd": 0, "status": "observing", "auto_paper": False,
        "paper_account": None, "research": {"result": 7}, "observation": {"elapsed_hours": 1}})
    return store, dbpath


def test_readonly_snapshot_preserves_data_and_allows_only_expected_lifecycle_changes(demo):
    store, path = demo
    baseline = soak.database_snapshot(path, full_integrity=True)
    assert baseline["issues"] == []
    assert baseline["schema"] == SCHEMA_VERSION
    job = store.get("experiment", "job")
    job.update(status="completed", observation={"elapsed_hours": 49}, phase="finished",
               finished_at="2026-09-08T22:00:00Z", completion_note="Plazo finalizado.")
    store.put("experiment", job)
    complete = soak.database_snapshot(path, full_integrity=True)
    assert complete["persistent_digest"] == baseline["persistent_digest"]
    assert complete["issues"] == []
    assert store.get("ledger", "demo")["events"][0]["amount"] == 123
    job["research"]["result"] = 8
    store.put("experiment", job)
    assert soak.database_snapshot(path)["persistent_digest"] != baseline["persistent_digest"]


@pytest.mark.parametrize("change, issue", [
    ({"provider": "openai"}, "provider_or_budget_nonzero"),
    ({"reserved_usd": .01}, "provider_or_budget_nonzero"),
    ({"spent_usd": .01}, "provider_or_budget_nonzero"),
    ({"budget_usd": 1}, "provider_or_budget_nonzero"),
    ({"auto_paper": True}, "paper_not_disabled"),
    ({"status": "interrupted"}, "unexpected_experiment_status"),
])
def test_nonzero_costs_providers_and_failed_experiments_are_rejected(demo, change, issue):
    store, path = demo
    store.put("experiment", {**store.get("experiment", "job"), **change})
    assert issue in soak.database_snapshot(path)["issues"]


def test_audit_prefix_detects_deletion_and_database_is_never_created(tmp_path, demo):
    store, path = demo
    store.audit("baseline", "job")
    baseline = soak.database_snapshot(path)
    store.audit("new", "job")
    later = soak.database_snapshot(path, audit_prefix_count=baseline["audit_count"])
    assert later["audit_prefix_digest"] == baseline["audit_prefix_digest"]
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM audit WHERE event='baseline'")
    assert soak.database_snapshot(path, audit_prefix_count=baseline["audit_count"])["audit_prefix_digest"] != baseline["audit_prefix_digest"]
    absent = tmp_path / "absent.sqlite3"
    with pytest.raises(sqlite3.OperationalError):
        soak.database_snapshot(absent)
    assert not absent.exists()


def test_log_reader_ignores_history_but_catches_new_errors_and_truncation(tmp_path):
    log = tmp_path / "backend.log"
    log.write_text("ERROR: old event\n", encoding="utf-8")
    reader = soak.LogReader([log, tmp_path / "missing-launcher.log"])
    assert reader.sample()["new_error_lines"] == 0
    with log.open("a") as stream:
        stream.write("INFO: healthy\nERR")
    assert reader.sample()["new_error_lines"] == 0
    with log.open("a") as stream:
        stream.write("OR: later failure\n")
    assert reader.sample()["new_error_lines"] == 1
    log.write_text("", encoding="utf-8")
    with pytest.raises(RuntimeError, match="truncado"):
        reader.sample()


def test_probe_detects_instance_and_persistence_changes_without_mutation(tmp_path, demo, monkeypatch):
    store, path = demo
    backup = create_backup(path, tmp_path / "backups/automatic")
    state = {"status": "running", "run_id": "f" * 32, "pid": 1,
             "children": {"backend": 2, "frontend": 3}, "last_backup": str(backup)}
    atomic_json(tmp_path / "var/runtime.json", state)
    monkeypatch.setattr(soak, "git_identity", lambda *args: None)
    monkeypatch.setattr(soak, "locked", lambda path: True)
    monkeypatch.setattr(soak, "probe_http", lambda version: {"version": "0.1.0", "portfolio_digests": {"demo": "same"}})
    monkeypatch.setattr(soak, "windows_resources", lambda pids: {
        name: {"pid": pid, "creation_ticks": pid, "rss_bytes": 100, "cpu_seconds": 1}
        for name, pid in pids.items()})
    probe = soak.Probe(tmp_path, "a" * 40, state["run_id"], replace(soak.Limits(), min_free_bytes=0))
    assert probe.sample()["issues"] == []
    ledger = store.get("ledger", "demo")
    ledger["events"].append({"id": "new", "date": "2026-01-02", "kind": "deposit", "amount": 1})
    store.put("ledger", ledger)
    assert any("persistente cambió" in issue for issue in probe.sample()["issues"])
    atomic_json(tmp_path / "var/runtime.json", {**state, "run_id": "b" * 32})
    assert any("instancia identificada" in issue for issue in probe.sample()["issues"])


class Clock:
    now = 0

    def sleep(self, seconds):
        self.now += seconds


def fake_probe(clock, samples=None, backups=None):
    values = iter(samples) if samples is not None else None
    return SimpleNamespace(candidate="a" * 40, run_id="f" * 32, root="fake-root", started_wall=0,
                           version="0.1.0", backups=backups or {}, baseline={"persistent_digest": "same"},
                           sample=lambda: next(values) if values else sample(clock.now))


def test_complete_48h_requires_a_real_midrun_backup_and_still_requires_restart(tmp_path, monkeypatch):
    # This is a clock/criteria simulation, not a durability benchmark.
    monkeypatch.setattr(soak.os, "fsync", lambda descriptor: None)
    clock = Clock()
    limits = soak.Limits()
    probe = fake_probe(clock, backups={"backup-24h": {"created_at": soak.timestamp(24 * 3600)}})
    output = tmp_path / "evidence"
    assert soak.run_monitor(probe, output, limits, wall=lambda: clock.now,
                            monotonic=lambda: clock.now, sleep=clock.sleep) == 0
    summary = read_json(output / "summary.json")
    assert summary["status"] == "completion_requires_restart_check"
    assert summary["restart_check"] == "pending"
    assert summary["accepted_seconds"] == 48 * 3600
    assert summary["samples"] == 2881
    assert len((output / "samples.jsonl").read_text().splitlines()) == 2881


def test_missing_midrun_backup_and_unobserved_hours_cannot_pass(tmp_path):
    clock = Clock()
    # Thresholds shortened only in this unit test; the CLI exposes no duration override.
    limits = replace(soak.Limits(), duration_seconds=120, max_backup_age_seconds=100)
    output = tmp_path / "no-backup"
    assert soak.run_monitor(fake_probe(clock), output, limits, wall=lambda: clock.now,
                            monotonic=lambda: clock.now, sleep=clock.sleep) == 1
    assert read_json(output / "summary.json")["issues"] == ["no_automatic_backup_during_soak"]
    clock = Clock()
    output = tmp_path / "suspend"
    probe = fake_probe(clock, [sample(0), sample(48 * 3600)])
    assert soak.run_monitor(probe, output, soak.Limits(), wall=lambda: clock.now,
                            monotonic=lambda: clock.now, sleep=clock.sleep) == 1
    assert read_json(output / "summary.json")["accepted_seconds"] == 0


def test_stop_and_crash_are_recorded_without_touching_atlas(tmp_path):
    clock = Clock()
    output = tmp_path / "stop"
    def sleep(seconds):
        clock.sleep(seconds)
        (output / "stop.request").write_text("stop")
    assert soak.run_monitor(fake_probe(clock), output, soak.Limits(), wall=lambda: clock.now,
                            monotonic=lambda: clock.now, sleep=sleep) == 1
    assert read_json(output / "summary.json")["status"] == "stopped"
    assert not (tmp_path / "var").exists()
    def broken():
        raise OSError("disk failure")
    probe = fake_probe(clock)
    probe.sample = broken
    assert soak.run_monitor(probe, tmp_path / "failure", soak.Limits()) == 1
    assert "disk failure" in read_json(tmp_path / "failure/summary.json")["issues"][0]


def test_status_does_not_mistake_a_stale_running_record_for_active_monitor(tmp_path, monkeypatch):
    atomic_json(tmp_path / "summary.json", {"status": "running", "started_at": soak.timestamp(),
                "limits": {"max_gap_seconds": 90}})
    monkeypatch.setattr(soak, "locked", lambda path: False)
    assert soak.monitor_status(tmp_path)["status"] == "monitor_lost_or_stale"


@pytest.mark.skipif(os.name != "nt", reason="Windows native counters")
def test_native_windows_resource_measurements_use_live_process_creation_identity():
    measured = soak.windows_resources({"self": os.getpid()})["self"]
    assert measured["pid"] == os.getpid()
    assert measured["creation_ticks"] > 0
    assert measured["rss_bytes"] > 0
    assert measured["cpu_seconds"] >= 0


@pytest.mark.skipif(os.name != "nt", reason="Windows venv redirectors")
def test_windows_measurement_includes_real_interpreter_behind_venv_redirector(tmp_path):
    identity = tmp_path / "real-pid.txt"
    stop = tmp_path / "stop"
    code = ("import os, pathlib, time; "
            f"pathlib.Path({str(identity)!r}).write_text(str(os.getpid())); "
            f"stop = pathlib.Path({str(stop)!r}); "
            "\nwhile not stop.exists(): time.sleep(0.02)")
    child = subprocess.Popen([sys.executable, "-c", code], creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 10
        while not identity.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        real_pid = int(identity.read_text())
        measurements = soak.windows_resources({"redirector": child.pid})
        by_pid = {value["pid"]: value for value in measurements.values()}
        assert len(by_pid) == len(measurements)
        assert child.pid in by_pid
        assert real_pid in by_pid
        assert by_pid[real_pid]["rss_bytes"] > 0
        # The current Windows venv uses a redirector; this proves its real
        # interpreter is included instead of merely testing a mocked tree.
        if real_pid != child.pid:
            assert by_pid[real_pid]["parent_pid"] == child.pid
            duplicate_roots = soak.windows_resources({"redirector": child.pid, "interpreter": real_pid})
            assert len({value["pid"] for value in duplicate_roots.values()}) == len(duplicate_roots)
    finally:
        stop.write_text("stop")
        child.wait(timeout=10)


def test_awake_request_releases_on_exception_and_never_requests_display_or_powerplan_changes():
    calls = []
    def api(flags):
        calls.append(flags)
        return 0x80000000
    request = soak.AwakeRequest(True, api)
    with pytest.raises(ValueError, match="failure"):
        with request:
            assert request.active
            raise ValueError("failure")
    assert calls == [0x80000001, 0x80000000]
    assert not request.active
    with soak.AwakeRequest(False, api):
        pass
    assert len(calls) == 2


def test_failed_awake_acquisition_cannot_start_a_successful_soak(tmp_path, monkeypatch):
    request = soak.AwakeRequest(True, lambda flags: 0)
    monkeypatch.setattr(soak, "AwakeRequest", lambda enabled: request)
    probe = fake_probe(Clock())
    assert soak.run_monitor(probe, tmp_path / "awake-failed", soak.Limits(), keep_awake=True) == 1
    summary = read_json(tmp_path / "awake-failed/summary.json")
    assert summary["status"] == "failed"
    assert summary["samples"] == 0
    assert summary["keep_awake"] is True
    assert summary["keep_awake_active"] is False
    assert "rechazó" in summary["issues"][0]
