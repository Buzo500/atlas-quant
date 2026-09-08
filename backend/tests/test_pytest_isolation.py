"""Collection must never create/open the operator's ordinary SQLite database."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("inherited_directory", [False, True])
def test_collection_isolates_global_app_and_cleans_up(tmp_path, inherited_directory):
    protected = tmp_path / "operator-data"
    protected.mkdir()
    # An accidental connection here would fail loudly; the guard in the probe
    # also prevents a broken conftest from touching the actual ordinary store.
    original = protected / "atlas.sqlite3"
    original.write_bytes(b"operator database must not be opened")
    report = tmp_path / "collection.json"
    shutil.copyfile(Path(__file__).with_name("conftest.py"), tmp_path / "conftest.py")
    (tmp_path / "test_collection_probe.py").write_text(
        "import json, os\n"
        "from pathlib import Path\n"
        "data = Path(os.environ['ATLAS_DATA_DIR']).resolve()\n"
        f"assert data != Path({str(protected)!r}).resolve()\n"
        f"assert data != Path({str(ROOT / 'var/atlas')!r}).resolve()\n"
        "assert data.name.startswith('atlas-pytest-data-') and data.is_dir()\n"
        "from atlas_quant.app import app\n"
        # Windows TEMP may use an 8.3 alias; compare the actual file identity.
        "assert app.state.service.store.path.samefile(data / 'atlas.sqlite3')\n"
        "assert (data / 'atlas.sqlite3').is_file()\n"
        f"Path({str(report)!r}).write_text(json.dumps({{'data_dir': str(data)}}))\n"
        "def test_never_executed():\n"
        "    raise AssertionError('This subprocess only collects tests')\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment.pop("PYTEST_ADDOPTS", None)
    if inherited_directory:
        environment["ATLAS_DATA_DIR"] = str(protected)
    else:
        environment.pop("ATLAS_DATA_DIR", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
         "--confcutdir", str(tmp_path), "-c", str(ROOT / "pyproject.toml"),
         str(tmp_path / "test_collection_probe.py")],
        cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 test collected" in result.stdout
    data = Path(json.loads(report.read_text())["data_dir"])
    assert not data.exists(), "Collection's temporary database must be removed at shutdown"
    assert original.read_bytes() == b"operator database must not be opened"
    assert sorted(path.name for path in protected.iterdir()) == ["atlas.sqlite3"]
