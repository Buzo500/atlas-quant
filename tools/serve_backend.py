"""Cooperative Uvicorn shutdown, including Windows without console signals."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import uvicorn


async def main():
    stop = Path(os.environ["ATLAS_STOP_FILE"])
    server = uvicorn.Server(uvicorn.Config("atlas_quant.app:app", host="127.0.0.1", port=8000,
                                         timeout_graceful_shutdown=15))

    async def watch():
        while not stop.exists():
            await asyncio.sleep(.2)
        server.should_exit = True

    watcher = asyncio.create_task(watch())
    try:
        await server.serve()
    finally:
        watcher.cancel()


if __name__ == "__main__":
    asyncio.run(main())
