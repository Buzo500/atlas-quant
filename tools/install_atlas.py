"""Install/update under the same lock as runtime; back up before any changes."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from atlas_runtime import InstanceLock, frontend_env, port_open, run_owned
from build_frontend import build_locked
from node_runtime import check_node, find_node, node_environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.version_info < (3, 12):
        raise RuntimeError("Se necesita Python 3.12 o posterior.")
    node = find_node(ROOT)
    pnpm = shutil.which("pnpm.cmd") if os.name == "nt" else shutil.which("pnpm")
    if not node or not pnpm:
        raise RuntimeError("Instala Node.js >=22.13 y pnpm 11.19.0 y abre una nueva ventana de PowerShell.")
    check_node(node)
    if subprocess.check_output([pnpm, "--version"], text=True).strip() != "11.19.0":
        raise RuntimeError("Esta entrega se instala con pnpm 11.19.0: npm.cmd install --global pnpm@11.19.0")
    with InstanceLock(ROOT / "var/atlas.lock"):
        if any(port_open(p) for p in (3000, 8000)):
            raise RuntimeError("Un puerto de ATLAS está ocupado. Detén la instancia antes de actualizar.")
        sys.path.insert(0, str(ROOT / "backend"))
        from atlas_quant.backup import create_backup
        database = ROOT / "var/atlas/atlas.sqlite3"
        if database.exists():
            print(f"Copia previa: {create_backup(database, ROOT / 'backups/before-update')}", flush=True)
        (ROOT / "frontend/dist/atlas-build.json").unlink(missing_ok=True)
        python = ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
        if not python.exists():
            run_owned([sys.executable, "-m", "venv", str(ROOT / ".venv")])
        run_owned([str(python), "-c", "import sys; assert sys.version_info >= (3,12), 'Python >=3.12 requerido'"])
        run_owned([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])
        run_owned([str(python), "-m", "pip", "check"])
        run_owned([pnpm, "--dir", str(ROOT / "frontend"), "install", "--frozen-lockfile", "--prod=false"],
                  env=frontend_env(node_environment(node, os.environ)))
        build_locked(ROOT)
    print("Instalación y compilación verificadas. Ejecuta Start-Atlas.ps1 -OpenBrowser.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Instalación de ATLAS: {exc}", file=sys.stderr)
        sys.exit(1)
