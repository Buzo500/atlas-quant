"""Opt-in ASGI timing wrapper, only for run_api_diagnostic.py's fresh E2E base."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
data = Path(os.environ['ATLAS_DATA_DIR']).resolve()
if (data.parent.parent != (ROOT / 'var/validation').resolve()
        or not re.fullmatch(r'e2e-[0-9a-f]{32}', data.parent.name)
        or data.name != 'data'
        or Path(os.environ['ATLAS_STOP_FILE']).resolve() != data.parent / 'servers.stop'):
    raise RuntimeError('El diagnóstico requiere una base E2E y su parada aislada.')

import uvicorn
from atlas_quant.app import app


def emit(event, **fields):
    print(json.dumps({'diag': 'backend', 'event': event,
                      'utc': datetime.now(timezone.utc).isoformat(), **fields}), flush=True)


class Trace:
    def __init__(self, application):
        self.application = application
        self.sequence = 0

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.application(scope, receive, send)
        self.sequence += 1
        request_id = self.sequence
        headers = dict(scope.get('headers', []))
        correlation = headers.get(b'x-atlas-diag', b'').decode('ascii', errors='replace')
        correlation = correlation if re.fullmatch(r'[a-zA-Z0-9-]{1,80}', correlation) else None
        start = time.perf_counter()
        common = {'request': request_id, 'correlation': correlation,
                  'method': scope['method'], 'path': scope['path'], 'client': scope.get('client')}
        emit('start', **common)

        async def traced_send(message):
            await send(message)
            elapsed = round((time.perf_counter() - start) * 1000, 3)
            if message['type'] == 'http.response.start':
                emit('headers', **common, ms=elapsed, status=message['status'])
            elif message['type'] == 'http.response.body' and not message.get('more_body'):
                emit('body_end', **common, ms=elapsed)
        try:
            await self.application(scope, receive, traced_send)
        finally:
            emit('complete', **common, ms=round((time.perf_counter() - start) * 1000, 3))


async def main():
    loop = asyncio.get_running_loop()
    emit('loop', implementation=type(loop).__name__)
    stop = Path(os.environ['ATLAS_STOP_FILE'])
    server = uvicorn.Server(uvicorn.Config(Trace(app), host='127.0.0.1', port=8000,
                                          timeout_graceful_shutdown=15))

    async def watch():
        previous = time.perf_counter()
        while not stop.exists():
            await asyncio.sleep(.2)
            current = time.perf_counter()
            lag = (current - previous - .2) * 1000
            if lag > 100:
                emit('event_loop_lag', ms=round(lag, 3))
            previous = current
        server.should_exit = True
    watcher = asyncio.create_task(watch())
    try:
        await server.serve()
    finally:
        watcher.cancel()


if __name__ == '__main__':
    asyncio.run(main())
