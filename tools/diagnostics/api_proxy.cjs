// Opt-in timing only. Never print body, cookie, authorization or query strings.
const fs = require('node:fs');
const path = require('node:path');
const root = fs.realpathSync(path.resolve(__dirname, '../..'));
const data = fs.realpathSync(process.env.ATLAS_DATA_DIR || '');
const run = path.dirname(data);
if (path.dirname(run) !== path.join(root, 'var/validation') ||
    !/^e2e-[a-f0-9]{32}$/.test(path.basename(run)) || path.basename(data) !== 'data' ||
    path.resolve(process.env.ATLAS_STOP_FILE || '') !== path.join(run, 'servers.stop')) {
  throw new Error('El diagnóstico requiere una base E2E y su parada aislada.');
}
const http = require('node:http');
const dc = require('node:diagnostics_channel');
const { AsyncLocalStorage } = require('node:async_hooks');
const { performance } = require('node:perf_hooks');
const scope = new AsyncLocalStorage();
const requests = new WeakMap();
let sequence = 0;
const emit = (event, fields = {}) => process.stdout.write(JSON.stringify({
  diag: 'proxy', utc: new Date().toISOString(), event, ...fields,
}) + '\n');
const originalEmit = http.Server.prototype.emit;
http.Server.prototype.emit = function(event, ...args) {
  if (event !== 'request') return originalEmit.call(this, event, ...args);
  const [request, response] = args;
  const correlation = request.headers['x-atlas-diag'];
  const info = { request: ++sequence,
    correlation: /^[a-zA-Z0-9-]{1,80}$/.test(correlation || '') ? correlation : `proxy-${process.pid}-${sequence}`,
    method: request.method, path: request.url.split('?')[0],
    client_port: request.socket.remotePort };
  const start = performance.now();
  emit('incoming', info);
  response.once('finish', () => emit('finish', { ...info, status: response.statusCode, ms: performance.now() - start }));
  response.once('close', () => emit('close', { ...info, finished: response.writableFinished, ms: performance.now() - start }));
  return scope.run(info, () => originalEmit.call(this, event, ...args));
};
const originalFetch = globalThis.fetch;
globalThis.fetch = function(input, init) {
  if (String(input).startsWith('http://127.0.0.1:8000/') && scope.getStore()) {
    const headers = new Headers(init?.headers);
    headers.set('x-atlas-diag', scope.getStore().correlation);
    return originalFetch(input, { ...init, headers });
  }
  return originalFetch(input, init);
};
for (const event of ['create', 'bodySent', 'headers', 'trailers', 'error']) {
  dc.channel('undici:request:' + event).subscribe(({ request, response, error }) => {
    if (String(request.origin) !== 'http://127.0.0.1:8000') return;
    if (event === 'create') requests.set(request, { ...scope.getStore(), start: performance.now() });
    const info = requests.get(request) || {};
    const { start, ...fields } = info;
    emit('upstream_' + event, { ...fields, path: request.path.split('?')[0],
      ms: start === undefined ? null : performance.now() - start,
      status: response?.statusCode, code: error?.code });
  });
}
dc.channel('undici:client:sendHeaders').subscribe(({ request, socket }) => {
  if (String(request.origin) !== 'http://127.0.0.1:8000') return;
  const { start, ...fields } = requests.get(request) || {};
  emit('upstream_send', { ...fields, port: socket.localPort,
    ms: start === undefined ? null : performance.now() - start });
});
let previous = performance.now();
setInterval(() => {
  const current = performance.now();
  const lag = current - previous - 200;
  if (lag > 100) emit('event_loop_lag', { ms: lag });
  previous = current;
}, 200).unref();
