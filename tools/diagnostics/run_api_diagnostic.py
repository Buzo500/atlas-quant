"""Run the existing isolated E2E harness with opt-in proxy/ASGI tracing.

Arguments are run_e2e.py's normal arguments. Defaults/limits, ownership checks,
fresh data, no keys, no paid providers and final cleanup remain unchanged.
This does not modify the ordinary launchers, dependencies or compiled UI.
"""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_e2e

original_popen = subprocess.Popen


def traced_popen(command, *args, **kwargs):
    command = list(command)
    if len(command) > 1 and command[-1] == str(ROOT / 'tools/serve_backend.py'):
        command[-1] = str(HERE / 'api_backend.py')
    elif len(command) == 2 and command[1] == str(ROOT / 'frontend/local-server.mjs'):
        command[1:1] = ['--require', str(HERE / 'api_proxy.cjs')]
    return original_popen(command, *args, **kwargs)


if __name__ == '__main__':
    subprocess.Popen = traced_popen
    try:
        sys.exit(run_e2e.main())
    finally:
        subprocess.Popen = original_popen
