"""Create or explicitly restore a local ATLAS database backup (no network)."""
from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from atlas_quant.backup import BackupError, create_backup, restore_backup, validate_backup
from atlas_runtime import InstanceLock


def _local_path(*parts) -> Path:
    path = ROOT.joinpath(*parts).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise BackupError("La ruta de datos o copias sale de la carpeta de esta instalación.")
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--restore", type=Path, metavar="CARPETA",
                           help="Autoriza sustituir la base local por esta copia; ATLAS debe estar detenido.")
    operation.add_argument("--verify", type=Path, metavar="CARPETA", help="Verifica una copia sin restaurar.")
    args = parser.parse_args(argv)
    try:
        if args.verify:
            result = {"verified_backup": str(args.verify.resolve()), "manifest": validate_backup(args.verify)}
        elif args.restore:
            # Also catch manually launched/older servers that do not hold our lock.
            for port in (3000, 8000):
                with socket.socket() as probe:
                    probe.settimeout(0.3)
                    if probe.connect_ex(("127.0.0.1", port)) == 0:
                        raise BackupError(f"El puerto local {port} está ocupado. Detén ATLAS antes de restaurar.")
            result = restore_backup(args.restore, _local_path("var", "atlas", "atlas.sqlite3"),
                                    _local_path("backups"),
                                    instance_lock=InstanceLock(_local_path("var", "atlas.lock")))
        else:
            result = {"backup": str(create_backup(_local_path("var", "atlas", "atlas.sqlite3"),
                                                   _local_path("backups")))}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (BackupError, OSError) as exc:
        print(f"ATLAS: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
