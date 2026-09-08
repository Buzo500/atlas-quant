"""Preserve the original server exit before cooperative sibling shutdown."""
from __future__ import annotations

from unittest.mock import Mock

import pytest

from atlas_runtime import locked, read_json
import run_atlas


class Child:
    def __init__(self, pid, code=None):
        self.pid = pid
        self.code = code
        self.waited = False

    def poll(self):
        return self.code

    def wait(self, timeout):
        self.waited = True
        if self.code is None:
            self.code = 0  # The sibling obeyed the cooperative stop signal.
        return self.code

    def terminate(self):
        pytest.fail("Cooperative cleanup must not terminate any process")

    def kill(self):
        pytest.fail("Cooperative cleanup must not kill any process")


@pytest.fixture
def supervisor(tmp_path, monkeypatch):
    var = tmp_path / "var"
    var.mkdir()
    for name, value in {"ROOT": tmp_path, "VAR": var, "STATE": var / "runtime.json",
                        "LOCK": var / "atlas.lock"}.items():
        monkeypatch.setattr(run_atlas, name, value)
    monkeypatch.setattr(run_atlas.shutil, "which", lambda name: "offline-node")
    monkeypatch.setattr(run_atlas.subprocess, "check_output", lambda *args, **kwargs: "v24.15.0")
    monkeypatch.setattr(run_atlas, "verify_build", lambda path: None)
    monkeypatch.setattr(run_atlas, "port_open", lambda port: False)
    group = Mock()
    monkeypatch.setattr(run_atlas, "ProcessGroup", lambda: group)
    return group


@pytest.mark.parametrize("phase, code", [("startup", 7), ("running", 0), ("running", 3221225786)])
def test_failure_identifies_original_child_and_preserves_sibling_exit_codes(supervisor, monkeypatch, phase, code):
    backend, frontend = Child(41001), Child(41002, code if phase == "startup" else None)
    spawn = Mock(side_effect=[backend, frontend])
    monkeypatch.setattr(run_atlas.subprocess, "Popen", spawn)
    monkeypatch.setattr(run_atlas, "health", lambda port: True)
    response = Mock(status=200)
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)

    def page_open(*args, **kwargs):
        frontend.code = code
        return response

    monkeypatch.setattr(run_atlas, "open_local_http", page_open)
    with pytest.raises(RuntimeError, match=f"frontend: código {code}"):
        run_atlas.supervise(5, False, "e" * 32)
    state = read_json(run_atlas.STATE)
    assert state["status"] == "failed"
    assert state["unexpected_child_exit"]["exit_codes"] == {"frontend": code}
    assert state["unexpected_child_exit"]["phase"] == ("el arranque" if phase == "startup" else "la ejecución")
    assert state["child_exit_codes"] == {"backend": 0, "frontend": code}
    assert state["forced_stop"] is False
    assert read_json(run_atlas.VAR / "logs" / f"runtime-{'e' * 32}.json") == state
    for name in ("backend", "frontend"):
        log = (run_atlas.VAR / "logs" / f"{name}.log").read_text(encoding="utf-8")
        assert f"run_id={'e' * 32} server={name} started_at=" in log
    assert backend.waited and frontend.waited
    assert not locked(run_atlas.LOCK)
    assert spawn.call_count == 2
    assert supervisor.add.call_args_list == [((backend,),), ((frontend,),)]
    supervisor.close.assert_called_once_with()


def test_stop_request_racing_child_exit_is_not_reported_as_failure(supervisor, monkeypatch):
    backend, frontend = Child(42001), Child(42002)
    monkeypatch.setattr(run_atlas.subprocess, "Popen", Mock(side_effect=[backend, frontend]))

    def stopped_poll():
        run_atlas.stop_file("f" * 32).write_text("requested stop", encoding="ascii")
        return 0

    # The while condition ran just before stop(), then frontend obeyed it.
    monkeypatch.setattr(frontend, "poll", stopped_poll)
    health = Mock(side_effect=AssertionError("No health check after the stop request"))
    monkeypatch.setattr(run_atlas, "health", health)
    assert run_atlas.supervise(5, False, "f" * 32) == 0
    state = read_json(run_atlas.STATE)
    assert state["status"] == "stopped"
    assert state["error"] is None
    assert "unexpected_child_exit" not in state
    assert state["child_exit_codes"] == {"backend": 0, "frontend": 0}
    assert read_json(run_atlas.VAR / "logs" / f"runtime-{'f' * 32}.json") == state
    health.assert_not_called()


def test_startup_failure_is_archived_and_a_new_run_keeps_previous_evidence(supervisor, monkeypatch):
    def missing_build(path):
        raise RuntimeError("Falta la interfaz compilada")

    monkeypatch.setattr(run_atlas, "verify_build", missing_build)
    spawn = Mock(side_effect=AssertionError("No child before build verification"))
    monkeypatch.setattr(run_atlas.subprocess, "Popen", spawn)
    first = None
    for run_id in ("a" * 32, "b" * 32):
        with pytest.raises(RuntimeError, match="Falta la interfaz compilada"):
            run_atlas.supervise(5, False, run_id)
        state = read_json(run_atlas.STATE)
        assert state["run_id"] == run_id
        assert state["status"] == "failed"
        assert state["child_exit_codes"] == {}
        assert read_json(run_atlas.VAR / "logs" / f"runtime-{run_id}.json") == state
        assert not locked(run_atlas.LOCK)
        if first is None:
            first = state
    assert read_json(run_atlas.VAR / "logs" / f"runtime-{'a' * 32}.json") == first
    spawn.assert_not_called()


@pytest.mark.parametrize("log_unwritable", [False, True])
def test_archive_failure_never_masks_original_exit_or_prevents_cleanup(
        supervisor, monkeypatch, capsys, log_unwritable):
    backend, frontend = Child(43001), Child(43002, 17)
    monkeypatch.setattr(run_atlas.subprocess, "Popen", Mock(side_effect=[backend, frontend]))
    original_write = run_atlas.atomic_json

    def failed_archive(path, value):
        if path.name.startswith("runtime-"):
            raise OSError("archive full")
        original_write(path, value)

    monkeypatch.setattr(run_atlas, "atomic_json", failed_archive)
    if log_unwritable:
        def failed_log(*args, **kwargs):
            raise OSError("launcher log full")

        monkeypatch.setattr(run_atlas, "print", failed_log, raising=False)
    with pytest.raises(RuntimeError, match="frontend: código 17"):
        run_atlas.supervise(5, False, "c" * 32)
    state = read_json(run_atlas.STATE)
    assert state["status"] == "failed"
    assert state["unexpected_child_exit"]["exit_codes"] == {"frontend": 17}
    assert state["child_exit_codes"] == {"backend": 0, "frontend": 17}
    assert backend.waited and frontend.waited
    assert not locked(run_atlas.LOCK)
    supervisor.close.assert_called_once_with()
    if not log_unwritable:
        assert "No se pudo archivar el diagnóstico" in capsys.readouterr().err
