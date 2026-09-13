"""Run the existing isolated E2E harness with opt-in proxy/ASGI tracing.

Arguments are run_e2e.py's normal arguments. Defaults/limits, ownership checks,
fresh data, no keys, no paid providers and final cleanup remain unchanged.
This does not modify the ordinary launchers, dependencies or compiled UI.
"""
from pathlib import Path
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_e2e
from incident_report import server_diagnostics, write_report
from tcp_capture import Capture, summary as tcp_summary

original_popen = subprocess.Popen
directories = set()
captures = {}


def traced_popen(command, *args, **kwargs):
    command = list(command)
    environment = kwargs.get('env') or {}
    if environment.get('ATLAS_STOP_FILE') and command[-1] in (
            str(ROOT / 'tools/serve_backend.py'), str(ROOT / 'frontend/local-server.mjs')):
        directories.add(Path(environment['ATLAS_STOP_FILE']).parent)
        directory = Path(environment['ATLAS_STOP_FILE']).parent
        if directory not in captures:
            try:
                captures[directory] = Capture(directory / 'tcp-pressure.jsonl').__enter__()
            except OSError:
                print('Captura TCP no disponible; el recorrido mantiene sus comprobaciones.', file=sys.stderr)
    if environment.get('ATLAS_E2E_RUN_DIR'):
        directories.add(Path(environment['ATLAS_E2E_RUN_DIR']))
        kwargs['env'] = {**environment, 'ATLAS_DIAGNOSTIC': '1'}
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
        for capture in captures.values():
            capture.__exit__(None, None, None)
            print(json.dumps({'atlas_tcp_capture': str(capture.path), 'error': capture.error}))
            try:
                print(json.dumps({'atlas_tcp_pressure':tcp_summary(capture.path)},ensure_ascii=False))
            except (OSError, ValueError, KeyError):
                print('Resumen de presión TCP no disponible.',file=sys.stderr)
        for directory in directories:
            try:
                print(json.dumps({'atlas_server_diagnostics': server_diagnostics(directory)}, ensure_ascii=False))
                report = write_report(directory)
                print(f"Captura correlacionada: {directory / 'diagnostic-report.json'}; incidencias: {len(report['incidents'])}; causa no confirmada.")
                print(json.dumps({'atlas_diagnostic_report': report}, ensure_ascii=False))
            except (OSError, ValueError) as error:
                # Evidence must not replace the original run's exit code.
                print(f"No se pudo completar la captura E2E: {type(error).__name__}", file=sys.stderr)
