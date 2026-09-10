import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { once } from 'node:events';
import { gzipSync, gunzipSync } from 'node:zlib';
import { createApiProxy, installApiProxy } from './api-proxy.mjs';

async function serving(t, handler) {
  const server = http.createServer(handler);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => {
    server.closeAllConnections();
    server.close();
  });
  return server;
}
const url = (s, path = '/api/state') =>
  `http://127.0.0.1:${s.address().port}${path}`;
function read(server, options = {}, body) {
  return new Promise((resolve, reject) => {
    const req = http.request(url(server, options.path), options, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('error', reject);
      res.on('end', () =>
        resolve({
          status: res.statusCode,
          headers: res.headers,
          body: Buffer.concat(chunks),
        }),
      );
    });
    req.on('error', reject);
    req.end(body);
  });
}

await test(
  'client cancellation closes upstream before headers and a subsequent read works',
  { timeout: 3000 },
  async (t) => {
    let entered, closed;
    const entry = new Promise((r) => (entered = r)),
      close = new Promise((r) => (closed = r));
    const upstream = await serving(t, (req, res) => {
      if (req.url === '/api/wait') {
        res.once('close', closed);
        entered();
      } else res.end('healthy');
    });
    const proxy = await serving(
      t,
      createApiProxy({ port: upstream.address().port }),
    );
    const client = http.get(url(proxy, '/api/wait'));
    client.on('error', () => {});
    await entry;
    client.destroy();
    await close;
    assert.equal((await read(proxy)).body.toString(), 'healthy');
  },
);

await test(
  'cancellation in a response body closes upstream',
  { timeout: 3000 },
  async (t) => {
    let closed;
    const close = new Promise((r) => (closed = r));
    const upstream = await serving(t, (_req, res) => {
      res.once('close', closed);
      res.write('partial');
    });
    const proxy = await serving(
      t,
      createApiProxy({ port: upstream.address().port }),
    );
    const client = http.get(url(proxy), (res) =>
      res.once('data', () => client.destroy()),
    );
    client.on('error', () => {});
    await close;
  },
);

await test('POST and GET on one browser connection keep exact bodies; upstream connections are isolated', async (t) => {
  const sockets = new Set();
  const upstream = await serving(t, (req, res) => {
    sockets.add(req.socket);
    assert.equal(req.headers.connection, 'keep-alive');
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () =>
      res.end(`${req.method}:${req.url}:${Buffer.concat(chunks).toString()}`),
    );
  });
  const proxy = await serving(
    t,
    createApiProxy({ port: upstream.address().port }),
  );
  const agent = new http.Agent({ keepAlive: true, maxSockets: 1 });
  t.after(() => agent.destroy());
  for (let i = 0; i < 30; i++) {
    const body = 'á'.repeat(10000);
    assert.equal(
      (
        await read(
          proxy,
          {
            method: 'POST',
            agent,
            headers: { 'content-length': Buffer.byteLength(body) },
          },
          body,
        )
      ).body.toString(),
      `POST:/api/state:${body}`,
    );
    assert.equal(
      (
        await read(proxy, { agent, path: '/api/state?q=a%20b&q=c' })
      ).body.toString(),
      'GET:/api/state?q=a%20b&q=c:',
    );
  }
  assert.equal(sockets.size, 60);
});

await test(
  'large bodies finish before the isolated upstream connection closes',
  { timeout: 5000 },
  async (t) => {
    const payload = Buffer.alloc(2 * 1024 * 1024, 'atlas');
    const connections = new Set();
    const upstream = await serving(t, (req, res) => {
      assert.equal(req.headers.connection, 'keep-alive');
      connections.add(req.socket);
      res.writeHead(200, { 'content-length': payload.length });
      res.end(payload);
    });
    const proxy = await serving(
      t,
      createApiProxy({ port: upstream.address().port }),
    );
    for (let wave = 0; wave < 3; wave++) {
      const values = await Promise.all(
        Array.from({ length: 8 }, () => read(proxy)),
      );
      for (const value of values) assert.deepEqual(value.body, payload);
    }
    assert.equal(connections.size, 24);
    await new Promise((resolve) => setTimeout(resolve, 50));
    assert.ok([...connections].every((socket) => socket.destroyed));
  },
);

await test('encoded bodies, error status and multiple cookies remain byte exact', async (t) => {
  const zipped = gzipSync('x'.repeat(100000));
  const upstream = await serving(t, (_req, res) => {
    res.writeHead(422, {
      'content-encoding': 'gzip',
      'content-length': zipped.length,
      'set-cookie': ['a=1', 'b=2'],
      connection: 'close, x-private-hop',
      'x-private-hop': 'omit',
    });
    res.end(zipped);
  });
  const proxy = await serving(
    t,
    createApiProxy({ port: upstream.address().port }),
  );
  const result = await read(proxy);
  assert.equal(result.status, 422);
  assert.deepEqual(result.headers['set-cookie'], ['a=1', 'b=2']);
  assert.equal(result.headers['x-private-hop'], undefined);
  assert.deepEqual(result.body, zipped);
  assert.equal(gunzipSync(result.body).length, 100000);
});

await test('failed POST is never retried and a truncated body is never success', async (t) => {
  let calls = 0;
  const upstream = await serving(t, (req, res) => {
    calls++;
    req.resume();
    req.on('end', () => {
      if (req.url === '/api/partial') {
        res.writeHead(200, { 'content-length': '100' });
        res.write('short');
        setImmediate(() => res.destroy());
      } else req.socket.destroy();
    });
  });
  const proxy = await serving(
    t,
    createApiProxy({ port: upstream.address().port }),
  );
  assert.equal((await read(proxy, { method: 'POST' }, 'mutation')).status, 502);
  assert.equal(calls, 1);
  await assert.rejects(read(proxy, { path: '/api/partial' }));
  assert.equal(calls, 2);
});

await test(
  'deadline includes stalled body and releases upstream',
  { timeout: 3000 },
  async (t) => {
    let closed;
    const close = new Promise((r) => (closed = r));
    const upstream = await serving(t, (_req, res) => {
      res.once('close', closed);
      res.write('partial');
    });
    const proxy = await serving(
      t,
      createApiProxy({ port: upstream.address().port, timeoutMs: 50 }),
    );
    await assert.rejects(read(proxy));
    await close;
  },
);

await test('routing keeps one owner and preserves non API rendering', async (t) => {
  const upstream = await serving(t, (_req, res) => res.end('api'));
  const proxy = await serving(t, (_req, res) => res.end('page'));
  installApiProxy(proxy, { port: upstream.address().port });
  assert.equal(proxy.listeners('request').length, 1);
  assert.equal((await read(proxy)).body.toString(), 'api');
  assert.equal(
    (await read(proxy, { path: '/apiary' })).body.toString(),
    'page',
  );
  assert.equal((await read(proxy, { path: '/' })).body.toString(), 'page');
});
