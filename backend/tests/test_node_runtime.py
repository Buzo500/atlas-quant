from pathlib import Path

import pytest

import node_runtime


@pytest.mark.parametrize('version', ['v24.0.0', '24.14.1', 'v24.15.0'])
def test_windows_rejects_the_native_crash_versions(version):
    with pytest.raises(RuntimeError, match='fallo de conexiones HTTP'):
        node_runtime.validate_version(version, windows=True)
    node_runtime.validate_version(version, windows=False)


@pytest.mark.parametrize('version', ['v22.13.0', 'v24.16.0', 'v24.21.0'])
def test_supported_versions(version):
    node_runtime.validate_version(version, windows=True)


@pytest.mark.parametrize('version', ['v20.0.0', 'v22.12.9', 'unknown', 'v24.21.0 modified'])
def test_invalid_or_too_old_node_is_not_accepted(version):
    with pytest.raises(RuntimeError):
        node_runtime.validate_version(version, windows=True)


def test_portable_node_is_only_selected_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(node_runtime.shutil, 'which', lambda _: 'system-node')
    assert node_runtime.find_node(tmp_path) == 'system-node'
    local = tmp_path / f'var/tools/node-v{node_runtime.NODE_VERSION}-win-x64/node.exe'
    local.parent.mkdir(parents=True)
    local.touch()
    if node_runtime.os.name == 'nt':
        assert node_runtime.find_node(tmp_path) == str(local)


def test_children_use_selected_node_without_mutating_parent_environment(tmp_path):
    original = {'Path': 'existing', 'OTHER': 'kept'}
    result = node_runtime.node_environment(str(tmp_path/'node.exe'), original)
    assert result['PATH'].split(node_runtime.os.pathsep)[0] == str(tmp_path)
    assert result['PATH'].endswith('existing') and result['OTHER'] == 'kept'
    assert 'Path' not in result
    assert original == {'Path': 'existing', 'OTHER': 'kept'}
