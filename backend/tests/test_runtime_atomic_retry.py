"""Transient Windows access does not destroy old state or hide permanent failure."""
import ctypes
import json
import os
import threading

import pytest

import atlas_runtime as runtime


@pytest.mark.skipif(os.name != 'nt', reason='Windows replacement semantics')
@pytest.mark.parametrize('code', [5, 32, 33])
def test_transient_access_retries_same_flushed_snapshot(tmp_path, monkeypatch, code):
    path = tmp_path/'state.json'
    runtime.atomic_json(path, {'revision': 1})
    replace = runtime.os.replace
    sources, pauses = [], []
    def transient(source, target):
        sources.append(source)
        assert json.loads(source.read_text(encoding='utf-8')) == {'revision': 2}
        assert json.loads(target.read_text(encoding='utf-8')) == {'revision': 1}
        if len(sources) < 3: raise ctypes.WinError(code)
        return replace(source, target)
    monkeypatch.setattr(runtime.os, 'replace', transient)
    monkeypatch.setattr(runtime.time, 'sleep', pauses.append)
    runtime.atomic_json(path, {'revision': 2})
    assert len(set(sources)) == 1 and pauses == [.01, .02]
    assert runtime.read_json(path) == {'revision': 2}
    assert list(tmp_path.glob('*.tmp')) == []


def test_permanent_io_error_preserves_old_file_and_never_retries(tmp_path, monkeypatch):
    path = tmp_path/'state.json'
    runtime.atomic_json(path, {'revision': 1})
    def failed(*args): raise OSError('Permanent I/O failure')
    monkeypatch.setattr(runtime.os, 'replace', failed)
    monkeypatch.setattr(runtime.time, 'sleep', lambda _: pytest.fail('Unexpected retry'))
    with pytest.raises(OSError, match='Permanent'): runtime.atomic_json(path, {'revision': 2})
    assert runtime.read_json(path) == {'revision': 1}
    assert list(tmp_path.glob('*.tmp')) == []


@pytest.mark.skipif(os.name != 'nt', reason='Windows replacement semantics')
def test_persistent_windows_denial_is_bounded_and_preserves_old_file(tmp_path, monkeypatch):
    path = tmp_path/'state.json'
    runtime.atomic_json(path, {'revision': 1})
    attempts, pauses = [], []
    def denied(*args):
        attempts.append(args)
        raise ctypes.WinError(5)
    monkeypatch.setattr(runtime.os, 'replace', denied)
    monkeypatch.setattr(runtime.time, 'sleep', pauses.append)
    with pytest.raises(OSError) as failure: runtime.atomic_json(path, {'revision': 2})
    assert failure.value.winerror == 5
    assert len(attempts) == 6 and sum(pauses) == pytest.approx(.31)
    assert runtime.read_json(path) == {'revision': 1}
    assert list(tmp_path.glob('*.tmp')) == []


@pytest.mark.skipif(os.name != 'nt', reason='Windows real shared handle')
def test_real_reader_without_delete_sharing_releases_before_replace(tmp_path):
    from ctypes import wintypes
    path = tmp_path/'state.json'
    runtime.atomic_json(path, {'revision': 1})
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    api.CreateFileW.restype = wintypes.HANDLE
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = api.CreateFileW(str(path), 0x80000000, 3, None, 3, 0x80, None)
    assert handle not in (None, ctypes.c_void_p(-1).value)
    released = threading.Event()
    def close():
        api.CloseHandle(handle)
        released.set()
    timer = threading.Timer(.05, close)
    timer.start()
    try:
        runtime.atomic_json(path, {'revision': 2})
        assert released.wait(1)
        assert runtime.read_json(path) == {'revision': 2}
    finally:
        timer.join(timeout=2)
