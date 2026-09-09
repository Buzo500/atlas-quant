"""Diagnostic wrappers must reject ordinary data before importing the application."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("optimized", [False, True])
def test_backend_rejects_foreign_data_even_with_python_optimization(tmp_path, optimized):
    ordinary = tmp_path / "ordinary"
    environment = {**os.environ, "PYTHONUTF8": "1", "ATLAS_DATA_DIR": str(ordinary),
                   "ATLAS_STOP_FILE": str(tmp_path / "servers.stop")}
    result = subprocess.run([sys.executable, *(["-O"] if optimized else []),
                             str(ROOT / "tools/diagnostics/api_backend.py")],
                            env=environment, capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert result.returncode != 0
    assert "El diagnóstico requiere" in result.stderr
    assert not ordinary.exists()


def test_proxy_rejects_ordinary_data_before_installing_hooks(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed for the optional proxy diagnostic")
    ordinary = tmp_path / "ordinary"
    ordinary.mkdir()
    environment = {**os.environ, "ATLAS_DATA_DIR": str(ordinary),
                   "ATLAS_STOP_FILE": str(tmp_path / "servers.stop")}
    result = subprocess.run([node, "--require", str(ROOT / "tools/diagnostics/api_proxy.cjs"),
                             "-e", "console.log('HOOKS_INSTALLED')"], env=environment,
                            capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert result.returncode != 0
    assert "El diagnóstico requiere" in result.stderr
    assert "HOOKS_INSTALLED" not in result.stdout
    assert not list(ordinary.iterdir())


def test_node_diagnostic_client_checks():
    """Include the Node guards in the ordinary Python CI test collection."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed for the optional client diagnostic")
    result = subprocess.run([node, "--test", str(ROOT / "tools/diagnostics/checks.test.cjs")],
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
