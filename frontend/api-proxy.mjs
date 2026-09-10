// Local HTTP transport owns both streams. No fetch pool, Web Stream conversion
// or automatic retry: a failed POST must never be submitted twice.
import { Agent, request } from 'node:http';
import { pipeline } from 'node:stream';

const HOP = [
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'expect',
];

function headersForHop(headers) {
  const result = { ...headers };
  const names = String(headers.connection ?? '')
    .split(',')
    .map((s) => s.trim().toLowerCase());
  for (const name of [...HOP, ...names]) delete result[name];
  return result;
}

export function createApiProxy({ port = 8000, timeoutMs = 30000 } = {}) {
  return (req, res) => {
    // The destination is fixed loopback; the request never supplies a host.
    const headers = headersForHop(req.headers);
    headers.host = `127.0.0.1:${port}`;
    let response;
    // One agent per request: ask the server to keep the socket open until we
    // consume the complete body, then destroy it. No cross-request reuse and
    // no server-side Connection: close while bytes are still being delivered.
    const agent = new Agent({ keepAlive: true, maxSockets: 1 });
    const upstream = request({
      hostname: '127.0.0.1',
      port,
      method: req.method,
      path: req.url,
      headers,
      agent,
    });
    const cancel = () => {
      req.unpipe(upstream);
      response?.destroy();
      upstream.destroy();
      agent.destroy();
    };
    const fail = (status) => {
      if (!res.destroyed && !res.writableEnded) {
        if (res.headersSent) res.destroy();
        else {
          res.writeHead(status, {
            'content-type': 'application/json; charset=utf-8',
            connection: 'close',
          });
          res.end(
            JSON.stringify({
              detail:
                status === 504
                  ? 'El motor no respondió a tiempo.'
                  : 'No se pudo completar la comunicación con el motor.',
            }),
          );
        }
      }
      cancel();
    };
    const timer = setTimeout(() => fail(504), timeoutMs).unref();
    const cleanup = () => {
      clearTimeout(timer);
      req.off('aborted', cancel);
      req.off('error', cancel);
    };
    req.once('aborted', cancel);
    req.once('error', cancel);
    res.once('close', () => {
      cancel();
      cleanup();
    });
    upstream.once('error', () => fail(502));
    upstream.once('response', (value) => {
      response = value;
      if (res.destroyed) {
        cancel();
        return;
      }
      // Bytes are forwarded unchanged, including encoded bodies and their length.
      res.writeHead(value.statusCode, headersForHop(value.headers));
      pipeline(value, res, (error) => {
        cleanup();
        if (error) cancel();
      });
    });
    req.pipe(upstream);
  };
}

export function installApiProxy(server, options) {
  const handlers = server.listeners('request');
  if (handlers.length !== 1)
    throw new Error('ATLAS: unexpected frontend request handlers.');
  const render = handlers[0];
  const proxy = createApiProxy(options);
  server.removeListener('request', render);
  server.on('request', function (req, res) {
    const pathname = (req.url ?? '').split('?')[0];
    if (pathname === '/api' || pathname.startsWith('/api/')) proxy(req, res);
    else render.call(this, req, res);
  });
}
