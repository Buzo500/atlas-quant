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
const bodies = new WeakMap();
const deliveries = new WeakMap();
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
  response.once('close', () => {
    emit('close', { ...info, finished: response.writableFinished, ms: performance.now() - start });
  });
  request.once('aborted', () => emit('client_request_aborted', { ...info, ms: performance.now() - start }));
  return scope.run(info, () => originalEmit.call(this, event, ...args));
};
const originalFetch = globalThis.fetch;
globalThis.fetch = function(input, init) {
  if (String(input).startsWith('http://127.0.0.1:8000/') && scope.getStore()) {
    const headers = new Headers(init?.headers);
    headers.set('x-atlas-diag', scope.getStore().correlation);
    const info = scope.getStore();
    const start = performance.now();
    deliveries.set(info, { ...info, start });
    init?.signal?.addEventListener('abort', () => emit('fetch_signal_abort', { ...info, ms: performance.now() - start }), { once: true });
    return originalFetch(input, { ...init, headers }).then(response => {
      if (response.body) bodies.set(response.body, { ...info, start });
      emit('fetch_response', { ...info, ms: performance.now() - start, body_used: response.bodyUsed });
      return response;
    });
  }
  return originalFetch(input, init);
};
// Observe the existing stream consumer without teeing, reading ahead or replacing
// the response body. Data events would force flowing mode and change the timing.
const { Readable } = require('node:stream');
const fromWeb = Readable.fromWeb;
Readable.fromWeb = function(body, ...args) {
  const stream = fromWeb.call(this, body, ...args);
  const matched = bodies.get(body);
  const info = matched || deliveries.get(scope.getStore());
  if (info) {
    const { start, ...fields } = info;
    emit('body_consumer_attached', { ...fields, upstream_body_identity: !!matched });
    for (const event of ['end', 'close', 'error']) {
      stream.once(event, error => emit('body_' + event, { ...fields,
        ms: performance.now() - start, ended: stream.readableEnded,
        destroyed: stream.destroyed, code: error?.code }));
    }
  }
  return stream;
};
const readers = new WeakMap();
// Buffered response delivery uses the Body mixin and may bypass public readers.
for (const method of ['arrayBuffer', 'text', 'json', 'bytes']) {
  const original = Response.prototype[method];
  if (!original) continue;
  Response.prototype[method] = function(...args) {
    const info = bodies.get(this.body) || deliveries.get(scope.getStore());
    const result = original.apply(this, args);
    if (!info) return result;
    const { start, ...fields } = info;
    emit('body_buffer_called', { ...fields, method, ms: performance.now() - start });
    return result.then(value => {
      emit('body_buffer_settled', { ...fields, method, ms: performance.now() - start });
      return value;
    }, error => {
      emit('body_buffer_error', { ...fields, method, ms: performance.now() - start, code: error?.code });
      throw error;
    });
  };
}
const getReader = ReadableStream.prototype.getReader;
ReadableStream.prototype.getReader = function(...args) {
  const reader = getReader.apply(this, args);
  if (bodies.has(this)) {
    const info = bodies.get(this);
    readers.set(reader, info);
    const { start, ...fields } = info;
    emit('body_reader_attached', { ...fields, ms: performance.now() - start });
  }
  return reader;
};
for (const [prototype, method, map] of [
  [ReadableStreamDefaultReader.prototype, 'read', readers],
  [ReadableStreamDefaultReader.prototype, 'cancel', readers],
  [ReadableStream.prototype, 'cancel', bodies],
]) {
  const original = prototype[method];
  prototype[method] = function(...args) {
    const info = map.get(this);
    const result = original.apply(this, args);
    if (!info) return result;
    const { start, ...fields } = info;
    emit('body_' + method + '_called', { ...fields, ms: performance.now() - start });
    return result.then(value => {
      emit('body_' + method + '_settled', { ...fields, ms: performance.now() - start, done: value?.done });
      return value;
    }, error => {
      emit('body_' + method + '_error', { ...fields, ms: performance.now() - start, code: error?.code });
      throw error;
    });
  };
}
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
dc.channel('undici:client:sendHeaders').subscribe(({ request, socket, headers }) => {
  if (String(request.origin) !== 'http://127.0.0.1:8000') return;
  const { start, ...fields } = requests.get(request) || {};
  const framing = {};
  for (const line of String(headers || '').split('\r\n')) {
    const index = line.indexOf(':');
    const key = line.slice(0, index).toLowerCase();
    if (['content-length', 'transfer-encoding', 'connection', 'expect'].includes(key)) framing[key] = line.slice(index + 1).trim();
  }
  emit('upstream_send', { ...fields, port: socket.localPort, framing,
    corked: socket.writableCorked, queued_bytes: socket.writableLength, needs_drain: socket.writableNeedDrain,
    ms: start === undefined ? null : performance.now() - start });
});
let previous = performance.now();
setInterval(() => {
  const current = performance.now();
  const lag = current - previous - 200;
  if (lag > 100) emit('event_loop_lag', { ms: lag });
  previous = current;
}, 200).unref();
