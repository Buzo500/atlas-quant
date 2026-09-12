"""Local runtime checks with private files and mocked application processes."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from atlas_runtime import InstanceLock, atomic_json, frontend_env, locked, read_json
import build_frontend
import run_atlas


def test_instance_lock_excludes_other_handles_and_releases_on_exception(tmp_path):
    path = tmp_path / "private" / "atlas.lock"
    competitor = InstanceLock(path)
    with pytest.raises(ValueError, match="deliberate"):
        with InstanceLock(path) as owner:
            assert locked(path)
            assert competitor.acquire() is False
            with pytest.raises(RuntimeError, match="ya está adquirido"):
                owner.acquire()
            raise ValueError("deliberate")
    assert not locked(path)
    assert competitor.acquire()
    competitor.release()
    competitor.release()


def test_instance_lock_is_owned_by_the_os_across_processes(tmp_path):
    path = tmp_path / "atlas.lock"
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from atlas_runtime import InstanceLock; "
        "lock=InstanceLock(sys.argv[2]); print(lock.acquire()); lock.release()"
    )

    def probe_child():
        result = subprocess.run(
            [sys.executable, "-c", probe, str(Path(build_frontend.__file__).parent), str(path)],
            capture_output=True, text=True, timeout=10, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return result.stdout.strip()

    with InstanceLock(path):
        assert probe_child() == "False"
    assert probe_child() == "True"


def test_stale_lock_file_does_not_block_a_new_instance(tmp_path):
    path = tmp_path / "atlas.lock"
    path.write_text("obsolete pid: 12345", encoding="utf-8")
    assert not locked(path)
    with InstanceLock(path):
        assert locked(path)
    assert not locked(path)


def test_frontend_environment_filters_provider_keys_without_mutating_input():
    original = {"OPENAI_API_KEY": "fake-openai", "anthropic_api_key": "fake-anthropic",
                "Anthropic_API_Key": "also-fake", "PATH": "test-path", "NODE_ENV": "development",
                "ATLAS_DATA_DIR": "private-test-path"}
    filtered = frontend_env(original)
    assert filtered == {"PATH": "test-path", "NODE_ENV": "production", "ATLAS_DATA_DIR": "private-test-path"}
    assert original["OPENAI_API_KEY"] == "fake-openai"
    assert original["NODE_ENV"] == "development"


def test_env_file_only_adds_allowed_provider_keys_and_respects_existing_values(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "# test-only credentials\nOPENAI_API_KEY='file-fake'\n"
        'ANTHROPIC_API_KEY="second-fake"\nPATH=untrusted\nATLAS_DATA_DIR=untrusted\n',
        encoding="utf-8-sig",
    )
    environment = {"OPENAI_API_KEY": "existing-fake", "PATH": "keep"}
    run_atlas.load_env(path, environment)
    assert environment == {"OPENAI_API_KEY": "existing-fake", "ANTHROPIC_API_KEY": "second-fake", "PATH": "keep"}


def test_env_file_accepts_local_ca_bundle_without_overriding_environment_or_tls_checks(tmp_path):
    path = tmp_path / ".env"
    bundle = tmp_path / "certificates with spaces" / "trusted.pem"
    path.write_text(f'REQUESTS_CA_BUNDLE="{bundle}"\nPYTHONHTTPSVERIFY=0\nNODE_TLS_REJECT_UNAUTHORIZED=0\n',
                    encoding="utf-8")
    environment = {}
    run_atlas.load_env(path, environment)
    assert environment == {"REQUESTS_CA_BUNDLE": str(bundle)}
    environment["REQUESTS_CA_BUNDLE"] = "inherited.pem"
    run_atlas.load_env(path, environment)
    assert environment == {"REQUESTS_CA_BUNDLE": "inherited.pem"}


@pytest.fixture
def compiled_frontend(tmp_path):
    frontend = tmp_path / "frontend"
    files = {
        "app/page.tsx": "export default function Page() { return null; }",
        "hooks/use-mobile.ts": "export const useMobile = () => false;",
        "features/data/data-panel.tsx": "export const DataPanel = () => null;",
        "shared/use-read.ts": "export const useRead = () => null;",
        "test/setup.ts": "export {};",
        "package.json": '{"name":"test-build"}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'",
        ".openai/hosting.json": '{"project_id":null}',
        "dist/server/index.js": "export default {};",
        "dist/server/chunks/server.js": "export const serverChunk = 1;",
        "dist/client/assets/client.js": "console.log('test');",
    }
    for name, content in files.items():
        path = frontend / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    atomic_json(frontend / "dist/atlas-build.json", {
        "format": 1, "sources": build_frontend.source_hash(frontend),
        "artifacts": build_frontend.artifact_hashes(frontend),
    })
    return frontend


def test_verified_build_accepts_unchanged_sources_and_artifacts(compiled_frontend):
    build_frontend.verify_build(compiled_frontend)


@pytest.mark.parametrize("missing", ["manifest", "server", "both"])
def test_missing_build_is_rejected(compiled_frontend, missing):
    if missing in {"manifest", "both"}:
        (compiled_frontend / "dist/atlas-build.json").unlink()
    if missing in {"server", "both"}:
        (compiled_frontend / "dist/server/index.js").unlink()
    with pytest.raises(RuntimeError, match="Falta la interfaz compilada"):
        build_frontend.verify_build(compiled_frontend)


@pytest.mark.parametrize("source", ["app/page.tsx", "hooks/use-mobile.ts", "features/data/data-panel.tsx",
                                    "shared/use-read.ts", "test/setup.ts", "pnpm-lock.yaml", ".openai/hosting.json"])
def test_changed_sources_including_hooks_make_build_stale(compiled_frontend, source):
    with (compiled_frontend / source).open("a", encoding="utf-8") as stream:
        stream.write("\nchanged test input\n")
    with pytest.raises(RuntimeError, match="desactualizada"):
        build_frontend.verify_build(compiled_frontend)


def test_new_hook_is_part_of_the_build_fingerprint(compiled_frontend):
    (compiled_frontend / "hooks/new-hook.ts").write_text("export const value = 1;", encoding="utf-8")
    with pytest.raises(RuntimeError, match="desactualizada"):
        build_frontend.verify_build(compiled_frontend)


@pytest.mark.parametrize("folder", ["features", "shared"])
def test_new_feature_or_shared_module_invalidates_build(compiled_frontend, folder):
    (compiled_frontend / folder / "new-module.ts").write_text("export const value = 1;", encoding="utf-8")
    with pytest.raises(RuntimeError, match="desactualizada"):
        build_frontend.verify_build(compiled_frontend)


@pytest.mark.parametrize("damage", ["server_changed", "client_changed", "chunk_missing", "extra_chunk"])
def test_modified_or_incomplete_chunks_are_rejected(compiled_frontend, damage):
    if damage == "server_changed":
        (compiled_frontend / "dist/server/chunks/server.js").write_text("changed", encoding="utf-8")
    elif damage == "client_changed":
        (compiled_frontend / "dist/client/assets/client.js").write_text("changed", encoding="utf-8")
    elif damage == "chunk_missing":
        (compiled_frontend / "dist/client/assets/client.js").unlink()
    else:
        (compiled_frontend / "dist/server/chunks/extra.js").write_text("extra", encoding="utf-8")
    with pytest.raises(RuntimeError, match="incompleta o modificada"):
        build_frontend.verify_build(compiled_frontend)


@pytest.fixture
def private_runtime(tmp_path, monkeypatch):
    var = tmp_path / "var"
    var.mkdir()
    for name, value in {"ROOT": tmp_path, "VAR": var, "STATE": var / "runtime.json",
                        "LOCK": var / "atlas.lock", "STOP": var / "atlas.stop"}.items():
        monkeypatch.setattr(run_atlas, name, value)
    return var


@pytest.mark.parametrize("old_status, expected", [("running", "stopped"), ("starting", "stopped"), ("failed", "failed")])
def test_status_never_trusts_a_recorded_pid_without_an_os_lock(private_runtime, monkeypatch, old_status, expected):
    atomic_json(run_atlas.STATE, {"status": old_status, "pid": os.getpid(), "run_id": "stale"})
    run_atlas.LOCK.write_text("stale", encoding="ascii")
    health = Mock(side_effect=AssertionError("Stale state must not query any server"))
    monkeypatch.setattr(run_atlas, "health", health)
    result = run_atlas.status()
    assert result["status"] == expected
    assert result["lock_held"] is False
    health.assert_not_called()


def test_active_state_with_failed_health_is_not_reported_as_running(private_runtime, monkeypatch):
    atomic_json(run_atlas.STATE, {"status": "running", "pid": os.getpid()})
    monkeypatch.setattr(run_atlas, "health", lambda port: port != 3000)
    with InstanceLock(run_atlas.LOCK):
        result = run_atlas.status()
    assert result["status"] == "unhealthy"
    assert result["lock_held"] is True


@pytest.mark.parametrize("failure", ["missing_build", "occupied_port"])
def test_startup_failure_releases_lock_and_never_starts_or_stops_foreign_processes(private_runtime, monkeypatch, failure):
    monkeypatch.setattr(run_atlas, "find_node", lambda root: "test-node")
    monkeypatch.setattr(run_atlas.subprocess, "check_output", lambda *args, **kwargs: "v24.21.0")
    verify = Mock(side_effect=RuntimeError("Falta la interfaz compilada") if failure == "missing_build" else None)
    ports = Mock(return_value=True)
    spawn = Mock(side_effect=AssertionError("No application process may be launched"))
    group = Mock(side_effect=AssertionError("No process group may be created"))
    monkeypatch.setattr(run_atlas, "verify_build", verify)
    monkeypatch.setattr(run_atlas, "port_open", ports)
    monkeypatch.setattr(run_atlas.subprocess, "Popen", spawn)
    monkeypatch.setattr(run_atlas, "ProcessGroup", group)
    expected = "Falta la interfaz compilada" if failure == "missing_build" else "Puerto 8000 ocupado"
    with pytest.raises(RuntimeError, match=expected):
        run_atlas.supervise(5, False, "a" * 32)
    assert not locked(run_atlas.LOCK)
    state = read_json(run_atlas.STATE)
    assert state["status"] == "failed"
    assert expected in state["error"]
    assert state["children"] == {}
    spawn.assert_not_called()
    group.assert_not_called()
    if failure == "missing_build":
        ports.assert_not_called()
    else:
        ports.assert_called_once_with(8000)


def test_duplicate_startup_leaves_existing_state_and_stop_file_untouched(private_runtime, monkeypatch):
    original = {"status": "running", "run_id": "b" * 32, "pid": os.getpid()}
    atomic_json(run_atlas.STATE, original)
    owner_stop = run_atlas.stop_file(original["run_id"])
    owner_stop.write_text("existing marker", encoding="ascii")
    spawn = Mock(side_effect=AssertionError("Duplicate startup must not launch children"))
    monkeypatch.setattr(run_atlas.subprocess, "Popen", spawn)
    with InstanceLock(run_atlas.LOCK):
        with pytest.raises(RuntimeError, match="ya está activo"):
            run_atlas.supervise(5, False, "c" * 32)
        assert locked(run_atlas.LOCK)
    assert read_json(run_atlas.STATE) == original
    assert owner_stop.read_text(encoding="ascii") == "existing marker"
    assert not run_atlas.stop_file("c" * 32).exists()
    spawn.assert_not_called()


@pytest.fixture
def dependency_supervisor(tmp_path):
    dependency = tmp_path / "dependency.py"
    dependency.write_text(
        "import sys\n"
        "print('dependency stdout', flush=True)\n"
        "print('dependency stderr', file=sys.stderr, flush=True)\n"
        "sys.exit(int(sys.argv[1]))\n",
        encoding="utf-8",
    )
    supervisor = tmp_path / "supervisor.py"
    supervisor.write_text(
        "import contextlib, pathlib, subprocess, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from atlas_runtime import run_owned\n"
        "root = pathlib.Path(__file__).parent\n"
        "print('before dependency', flush=True)\n"
        "with contextlib.ExitStack() as stack:\n"
        "    options = {}\n"
        "    if sys.argv[3] == 'files':\n"
        "        options['stdout'] = stack.enter_context((root / 'stdout.log').open('wb'))\n"
        "        options['stderr'] = stack.enter_context((root / 'stderr.log').open('wb'))\n"
        "    elif sys.argv[3] == 'merged':\n"
        "        options['stderr'] = subprocess.STDOUT\n"
        "    try:\n"
        "        run_owned([sys.executable, str(root / 'dependency.py'), sys.argv[2]], **options)\n"
        "    except subprocess.CalledProcessError as error:\n"
        "        print('dependency failed: ' + str(error.returncode), flush=True)\n"
        "        sys.exit(error.returncode)\n"
        "print('after dependency', flush=True)\n",
        encoding="utf-8",
    )

    def run(exit_code=0, mode="inherited"):
        return subprocess.run(
            [sys.executable, str(supervisor), str(Path(build_frontend.__file__).parent), str(exit_code), mode],
            cwd=tmp_path, capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    return run


@pytest.mark.parametrize("exit_code", [0, 7])
def test_owned_dependency_output_reaches_supervisor_streams_on_success_and_failure(dependency_supervisor, exit_code):
    result = dependency_supervisor(exit_code)
    assert result.returncode == exit_code, result.stderr
    assert result.stdout.splitlines() == [
        "before dependency", "dependency stdout",
        "after dependency" if exit_code == 0 else "dependency failed: 7",
    ]
    assert result.stderr.splitlines() == ["dependency stderr"]


def test_owned_dependency_respects_explicit_output_files(dependency_supervisor, tmp_path):
    result = dependency_supervisor(mode="files")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["before dependency", "after dependency"]
    assert result.stderr == ""
    assert (tmp_path / "stdout.log").read_text().splitlines() == ["dependency stdout"]
    assert (tmp_path / "stderr.log").read_text().splitlines() == ["dependency stderr"]


def test_owned_dependency_respects_stderr_redirected_to_stdout(dependency_supervisor):
    result = dependency_supervisor(mode="merged")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["before dependency", "dependency stdout", "dependency stderr", "after dependency"]
    assert result.stderr == ""
