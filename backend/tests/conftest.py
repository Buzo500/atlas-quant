"""Isolate import-time application setup before pytest collects any test module."""
import tempfile

import pytest


def pytest_configure(config):
    # app.py constructs its ASGI app at import time. A fixture is too late:
    # test modules import create_app while pytest is still collecting them.
    # Always override inherited data directories, including an ordinary one.
    directory = tempfile.TemporaryDirectory(prefix="atlas-pytest-data-")
    environment = pytest.MonkeyPatch()
    environment.setenv("ATLAS_DATA_DIR", directory.name)

    def cleanup():
        try:
            directory.cleanup()
        finally:
            environment.undo()

    config.add_cleanup(cleanup)
