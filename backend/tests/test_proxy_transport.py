"""Real Python → maintained Node proxy → HTTP client, without ATLAS data."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
import uvicorn


def test_python_large_responses_are_received_before_closing_upstream():
    payload = b'atlas' * 420000  # 2.1 MB: exercises several socket buffers.
    connections = []

    async def application(scope, receive, send):
        connections.append((scope['client'], dict(scope['headers']).get(b'connection')))
        await send({'type': 'http.response.start', 'status': 200,
                    'headers': [(b'content-length', str(len(payload)).encode())]})
        await send({'type': 'http.response.body', 'body': payload})

    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(application, lifespan='off', log_level='critical'))
    thread = threading.Thread(target=lambda: asyncio.run(server.serve(sockets=[listener])), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(.01)
    module = (Path(__file__).resolve().parents[2] / 'frontend/api-proxy.mjs').as_uri()
    script = """
import http from 'node:http';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {createApiProxy} from MODULE;
const payload=Buffer.from('atlas'.repeat(420000));
const proxy=http.createServer(createApiProxy({port:PORT}));
proxy.listen(0,'127.0.0.1'); await once(proxy,'listening');
const agent=new http.Agent({keepAlive:true,maxSockets:8});
async function read() {
  await new Promise((resolve,reject)=>{
    const req=http.get({hostname:'127.0.0.1',port:proxy.address().port,path:'/api/large',agent},res=>{
      const chunks=[];
      res.on('data',c=>chunks.push(c));res.on('error',reject);
      res.on('end',()=>{try {assert.deepEqual(Buffer.concat(chunks),payload);resolve();}catch(e){reject(e);}});
    });
    req.on('error',reject);
  });
}
try {
  for(let i=0;i<5;i++) await Promise.all(Array.from({length:8},read));
  console.log(JSON.stringify({responses:40,bytes:payload.length}));
} finally {agent.destroy();proxy.closeAllConnections();proxy.close();}
""".replace('MODULE', json.dumps(module)).replace('PORT', str(port))
    try:
        assert server.started
        result = subprocess.run(
            [shutil.which('node'), '--input-type=module', '-e', script],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)['responses'] == 40
        assert len(connections) == len({address for address, _ in connections}) == 40
        assert all(header == b'keep-alive' for _, header in connections)
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(f'Connections {connections}; stdout={exc.stdout}; stderr={exc.stderr}') from exc
    finally:
        server.should_exit = True
        thread.join(5)
        listener.close()
        assert not thread.is_alive()
