"""Fail-closed E2E infrastructure checks; no browser, server or real database."""
from copy import deepcopy
import json
import os
import sqlite3
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import run_e2e
from process_group import ProcessGroup


@pytest.fixture
def private_root(tmp_path, monkeypatch):
    monkeypatch.setattr(run_e2e, "ROOT", tmp_path)
    return tmp_path


@pytest.mark.parametrize("name", ["../atlas", "e2e-../atlas", "e2e-", "e2e-" + "a" * 31,
                                  "e2e-" + "a" * 33, "E2E-" + "a" * 32])
def test_run_identifier_cannot_escape_validation(private_root, name):
    with pytest.raises(ValueError, match="Identificador"):
        run_e2e.run_directory(name)
    assert not (private_root / "var").exists()


def test_data_directory_cannot_be_a_foreign_or_ordinary_path(private_root):
    name = "e2e-" + "a" * 32
    assert run_e2e.isolated_data(run_e2e.run_directory(name)) == private_root / "var/validation" / name / "data"
    for foreign in (private_root / "elsewhere" / name, private_root / "var/atlas"):
        with pytest.raises(ValueError):
            run_e2e.isolated_data(foreign)


def test_inherited_credentials_and_database_are_never_forwarded(private_root, monkeypatch):
    inherited = {"OPENAI_API_KEY": "fake-key", "ANTHROPIC_API_KEY": "fake-key", "GH_TOKEN": "fake-token",
                 "SSLKEYLOGFILE": "fake-log", "ATLAS_DATA_DIR": "ordinary-database",
                 "ATLAS_STOP_FILE": "ordinary-stop", "NODE_OPTIONS": "--require untrusted"}
    for key, value in inherited.items():
        monkeypatch.setenv(key, value)
    directory = run_e2e.run_directory("e2e-" + "a" * 32)
    actual = run_e2e.clean_environment(directory)
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GH_TOKEN", "SSLKEYLOGFILE", "NODE_OPTIONS"):
        assert key not in actual
    assert actual["ATLAS_DATA_DIR"] == str(directory / "data")
    assert actual["ATLAS_STOP_FILE"] == str(directory / "servers.stop")
    assert actual["PLAYWRIGHT_BROWSERS_PATH"] == str(private_root / "var/playwright-browsers")


def zero_state():
    return {"providers": [{"configured": False}], "datasets": [{"source_kind": "synthetic"}],
            "settings": {"kill_switch": True}, "experiments": [{"provider": "none", "hours": 1,
                "budget_usd": 0, "spent_usd": 0, "reserved_usd": 0, "auto_paper": False, "paper_account": None}]}


@pytest.mark.parametrize("field,value", [("provider", "openai"), ("hours", 48), ("budget_usd", 1),
                                        ("spent_usd", .01), ("reserved_usd", .01),
                                        ("auto_paper", True), ("paper_account", {"cash": 1})])
def test_experiment_must_remain_brief_and_zero_budget(field, value):
    state = zero_state()
    run_e2e.assert_zero_budget(state)
    state["experiments"][0][field] = value
    with pytest.raises(RuntimeError, match="experimento"):
        run_e2e.assert_zero_budget(state)


def test_sources_keys_and_unlocked_paper_are_rejected():
    initial = zero_state()
    for section, change in (("providers", {"configured": True}),
                            ("datasets", {"source_kind": "observed"}),
                            ("datasets", {"source_kind": "synthetic", "feed": {"enabled": True}})):
        state = deepcopy(initial)
        state[section] = [change]
        with pytest.raises(RuntimeError):
            run_e2e.assert_zero_budget(state)
    initial["settings"]["kill_switch"] = False
    with pytest.raises(RuntimeError):
        run_e2e.assert_zero_budget(initial)


def test_listener_must_belong_to_created_process(monkeypatch):
    children = {"backend": SimpleNamespace(pid=123, poll=lambda: None),
                "frontend": SimpleNamespace(pid=456, poll=lambda: None)}
    monkeypatch.setattr(run_e2e, "listening_pid", lambda port: 123 if port == 8000 else 999)
    groups = {"backend": SimpleNamespace(contains_pid=lambda pid: pid == 123),
              "frontend": SimpleNamespace(contains_pid=lambda pid: pid == 456)}
    with pytest.raises(RuntimeError, match="no pertenece"):
        run_e2e.assert_owned(children, groups)
    # Even an owned listener from the other server family is not acceptable.
    monkeypatch.setattr(run_e2e, "listening_pid", lambda _: 123)
    with pytest.raises(RuntimeError, match="frontend"):
        run_e2e.assert_owned(children, groups)


def test_busy_port_refuses_before_build_or_server_start(private_root, monkeypatch):
    cli = private_root / "frontend/node_modules/@playwright/test/cli.js"
    cli.parent.mkdir(parents=True)
    cli.write_text("not executed", encoding="utf-8")
    monkeypatch.setattr(run_e2e.shutil, "which", lambda _: "node")
    monkeypatch.setattr(run_e2e, "port_open", lambda port: port == 8000)
    spawn = Mock(side_effect=AssertionError("Must not start or stop a process"))
    build = Mock(side_effect=AssertionError("Must not inspect an occupied instance"))
    monkeypatch.setattr(run_e2e.subprocess, "Popen", spawn)
    monkeypatch.setattr(run_e2e, "verify_build", build)
    with pytest.raises(RuntimeError, match="no reutiliza"):
        run_e2e.run(manual=False, timeout=30)
    spawn.assert_not_called()
    build.assert_not_called()
    assert not (private_root / "var/validation").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object")
def test_job_membership_proves_venv_interpreter_and_descendants(tmp_path):
    gate, identity = tmp_path / "assigned", tmp_path / "identity.json"
    code = (
        "import json, os, pathlib, subprocess, sys, time\n"
        "gate, identity = map(pathlib.Path, sys.argv[1:])\n"
        "while not gate.exists(): time.sleep(.01)\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'], "
        "creationflags=subprocess.CREATE_NO_WINDOW)\n"
        "identity.write_text(json.dumps([os.getpid(), child.pid]))\n"
        "time.sleep(20)\n"
    )
    with ProcessGroup() as group, ProcessGroup() as foreign:
        process = subprocess.Popen([sys.executable, "-u", "-c", code, str(gate), str(identity)],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            group.add(process)
        except BaseException:
            process.kill()
            process.wait(timeout=5)
            raise
        gate.touch()
        deadline = time.monotonic() + 8
        while not identity.exists() or not identity.read_text():
            assert process.poll() is None
            assert time.monotonic() < deadline
            time.sleep(.02)
        interpreter, descendant = json.loads(identity.read_text())
        for pid in (process.pid, interpreter, descendant):
            assert group.contains_pid(pid)
            assert not foreign.contains_pid(pid)
        assert not group.contains_pid(os.getpid())
        assert not group.contains_pid(0)
        process.kill()
        process.wait(timeout=5)
        assert not group.contains_pid(process.pid)
    assert not group.contains_pid(descendant)


@pytest.mark.parametrize("integrity", ["corrupt", "exception", "ok"])
def test_final_descriptor_revokes_token_and_fails_for_invalid_database(private_root, monkeypatch, integrity):
    directory = run_e2e.run_directory("e2e-" + "b" * 32)
    data = directory / "data"
    data.mkdir(parents=True)
    (data / "atlas.sqlite3").touch()
    descriptor = {"active": True, "token": "temporary", "ordinary_database_before": {"atlas.sqlite3": "before"},
                  "server_exit_codes": {"backend": 0, "frontend": 0}}
    monkeypatch.setattr(run_e2e, "normal_database_hashes", lambda: {"atlas.sqlite3": "before"})
    monkeypatch.setattr(run_e2e, "port_open", lambda _: False)
    db = Mock()
    db.__enter__ = Mock(return_value=db)
    db.__exit__ = Mock(return_value=None)
    db.execute.return_value = [("ok" if integrity == "ok" else "corrupt index",)]
    connect = Mock(return_value=db)
    if integrity == "exception":
        connect.side_effect = sqlite3.DatabaseError("controlled corruption")
    monkeypatch.setattr(run_e2e.sqlite3, "connect", connect)
    run_e2e.finish_descriptor(directory, data, descriptor, result=0, error=None, forced_stop=False)
    saved = json.loads((directory / "run.json").read_text())
    assert saved["active"] is False and saved["token"] is None
    assert saved["result"] == (0 if integrity == "ok" else 1)
    assert saved["ordinary_database_after"] == saved["ordinary_database_before"]
    if integrity == "exception":
        assert saved["finalization_error"] == "controlled corruption"


def test_nonzero_server_exit_cannot_pass(private_root, monkeypatch):
    directory = run_e2e.run_directory("e2e-" + "c" * 32)
    data = directory / "data"
    data.mkdir(parents=True)
    with sqlite3.connect(data / "atlas.sqlite3") as db:
        db.execute("CREATE TABLE isolated (id INTEGER)")
    descriptor = {"active": True, "token": "temporary", "ordinary_database_before": {},
                  "server_exit_codes": {"backend": 3, "frontend": 0}}
    monkeypatch.setattr(run_e2e, "port_open", lambda _: False)
    run_e2e.finish_descriptor(directory, data, descriptor, result=0, error=None, forced_stop=False)
    assert descriptor["result"] == 1
    assert descriptor["integrity"] == "ok"
