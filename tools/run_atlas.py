"""Run the local app without exposing ports or credentials to the network."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]


def load_env(path, env):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip() in {"OPENAI_API_KEY","ANTHROPIC_API_KEY"}:
            env.setdefault(key.strip(),value.strip().strip('"').strip("'"))


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--open",action="store_true")
    options = args.parse_args()
    var = ROOT/"var"
    var.mkdir(exist_ok=True)
    lock = (var/"atlas.lock").open("a+b")
    lock.seek(0)
    lock.write(b"0")
    lock.flush()
    lock.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        print("ATLAS ya está arrancado.",flush=True)
        if options.open:
            webbrowser.open("http://127.0.0.1:3000/")
        return
    for port in (8000,3000):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1",port))==0:
                raise RuntimeError(f"Puerto {port} ocupado. Detén la otra instancia antes de arrancar ATLAS.")
    node = shutil.which("node")
    if not node:
        fallback = Path.home()/".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
        node = str(fallback) if fallback.exists() else None
    if not node:
        raise RuntimeError("Falta Node.js en PATH.")
    cli = ROOT/"frontend/node_modules/vinext/dist/cli.js"
    if not cli.exists():
        raise RuntimeError("Falta instalar la interfaz. Ejecuta Install-Atlas.ps1.")
    environment = os.environ.copy()
    load_env(ROOT/".env",environment)
    environment["ATLAS_DATA_DIR"] = str(var/"atlas")
    environment["PYTHONUTF8"] = "1"
    # Provider keys go only to Python, never to the UI build/runtime process.
    frontend_environment = {k:v for k,v in environment.items() if k not in {"OPENAI_API_KEY","ANTHROPIC_API_KEY"}}
    stop = var/"atlas.stop"
    if stop.exists():
        stop.unlink()
    logs = var/"logs"
    logs.mkdir(exist_ok=True)
    backend_log = (logs/"backend.log").open("ab")
    frontend_log = (logs/"frontend.log").open("ab")
    children = []
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0
        children.append(subprocess.Popen([sys.executable,"-m","uvicorn","atlas_quant.app:app","--app-dir","backend","--host","127.0.0.1","--port","8000"],cwd=ROOT,env=environment,stdout=backend_log,stderr=subprocess.STDOUT,creationflags=flags))
        children.append(subprocess.Popen([node,str(cli),"dev","--host","127.0.0.1","--port","3000"],cwd=ROOT/"frontend",env=frontend_environment,stdout=frontend_log,stderr=subprocess.STDOUT,creationflags=flags))
        print("ATLAS local: http://127.0.0.1:3000/",flush=True)
        opened = False
        while not stop.exists():
            if any(child.poll() is not None for child in children):
                raise RuntimeError("Uno de los procesos terminó. Revisa var/logs.")
            if options.open and not opened:
                try:
                    with urllib.request.urlopen("http://127.0.0.1:3000/",timeout=2) as response:
                        if response.status==200:
                            webbrowser.open("http://127.0.0.1:3000/")
                            opened=True
                except Exception:
                    pass
            time.sleep(1)
    finally:
        # Only terminate the Popen handles created by this launcher.
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
        backend_log.close()
        frontend_log.close()
        lock.close()


if __name__ == "__main__":
    main()
