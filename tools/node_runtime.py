"""Select and validate Node consistently for installation, build and servers."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess

NODE_VERSION = '24.21.0'


def find_node(root: Path) -> str | None:
    # Optional official portable installation, private to this checkout.
    local = root / 'var/tools' / f'node-v{NODE_VERSION}-win-x64/node.exe'
    return str(local) if os.name == 'nt' and local.is_file() else shutil.which('node')


def validate_version(version: str, *, windows: bool) -> None:
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', version.strip())
    if not match:
        raise RuntimeError('No se pudo identificar la versión de Node.js.')
    major, minor, _ = map(int, match.groups())
    if (major, minor) < (22, 13):
        raise RuntimeError('Se necesita Node.js 22.13 o posterior.')
    if windows and major == 24 and minor < 16:
        raise RuntimeError(f'Node.js {version.strip()} tiene un fallo de conexiones HTTP en Windows. '
                           f'Instala Node.js {NODE_VERSION} LTS y abre una nueva consola; '
                           'consulta docs/operacion_windows.md.')


def check_node(node: str) -> str:
    version = subprocess.check_output([node, '--version'], text=True).strip()
    validate_version(version, windows=os.name == 'nt')
    return version


def node_environment(node: str, environment) -> dict[str, str]:
    result = dict(environment)
    paths = [value for key, value in result.items() if key.upper() == 'PATH']
    for key in list(result):
        if key.upper() == 'PATH':
            del result[key]
    result['PATH'] = str(Path(node).resolve().parent) + os.pathsep + (paths[0] if paths else '')
    return result
