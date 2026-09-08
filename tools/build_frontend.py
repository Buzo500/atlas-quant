"""Build once, record inputs and artifacts, and refuse stale local releases."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

from atlas_runtime import InstanceLock, atomic_json, frontend_env, read_json, run_owned

ROOT = Path(__file__).resolve().parents[1]


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(frontend):
    paths = []
    for name in ("app", "components", "features", "shared", "test", "e2e", "hooks", "lib", "public", "src", ".openai"):
        folder = frontend / name
        if folder.exists():
            paths.extend(p for p in folder.rglob("*") if p.is_file())
    for path in frontend.iterdir():
        if path.is_file() and (path.suffix in {".json", ".yaml", ".ts", ".js", ".mjs", ".css"}):
            if path.name != "next-env.d.ts":
                paths.append(path)
    return sorted(paths)


def source_hash(frontend):
    digest = hashlib.sha256()
    for path in source_files(frontend):
        digest.update(path.relative_to(frontend).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def artifact_hashes(frontend):
    dist = frontend / "dist"
    return {p.relative_to(dist).as_posix(): file_hash(p)
            for folder in (dist / "server", dist / "client")
            for p in sorted(folder.rglob("*")) if p.is_file()}


def verify_build(frontend):
    manifest = read_json(frontend / "dist/atlas-build.json")
    if not (frontend / "dist/server/index.js").is_file() or not manifest:
        raise RuntimeError("Falta la interfaz compilada. Ejecuta Install-Atlas.ps1 o tools/build_frontend.py.")
    if manifest.get("sources") != source_hash(frontend):
        raise RuntimeError("La compilación está desactualizada. Ejecuta tools/build_frontend.py con la .venv.")
    if not manifest.get("artifacts") or manifest["artifacts"] != artifact_hashes(frontend):
        raise RuntimeError("La compilación está incompleta o modificada. Reconstruye con tools/build_frontend.py.")


def build_locked(root=ROOT):
    frontend = root / "frontend"
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Falta Node.js en PATH.")
    (frontend / "dist/atlas-build.json").unlink(missing_ok=True)
    before = source_hash(frontend)
    run_owned([node, str(frontend / "node_modules/vinext/dist/cli.js"), "build"],
              cwd=frontend, env=frontend_env(os.environ))
    if before != source_hash(frontend):
        raise RuntimeError("Las fuentes cambiaron durante la compilación. Vuelve a compilar.")
    atomic_json(frontend / "dist/atlas-build.json", {
        "format": 1, "sources": before, "artifacts": artifact_hashes(frontend),
    })
    verify_build(frontend)


def build(root=ROOT):
    with InstanceLock(root / "var/atlas.lock"):
        build_locked(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            verify_build(ROOT / "frontend")
        else:
            build()
        print("Interfaz compilada y verificada.")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"{exc}\n")
