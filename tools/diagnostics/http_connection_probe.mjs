// Bounded loopback-only regression probe for silent Windows Node TCP failures.
// See https://github.com/nodejs/node/issues/63620. No ATLAS data or credentials.
import http from 'node:http';
import { once } from 'node:events';
import { performance } from 'node:perf_hooks';
import { setTimeout as pause } from 'node:timers/promises';

const duration = Number(process.argv[2] ?? 30000);
if (!Number.isInteger(duration) || duration < 100 || duration > 60000)
  throw new Error('Duration must be 100–60000 ms.');
const concurrency = 64;
const server = http.createServer((req, res) => res.end('ok'));
server.listen(0, '127.0.0.1');
await once(server, 'listening');
const start = performance.now();
let completed = 0, failures = 0;
const errors = {};
console.log(JSON.stringify({phase: 'start', node: process.version, uv: process.versions.uv,
  duration_ms: duration, concurrency, host: '127.0.0.1'}));
const timer = setInterval(() => console.log(JSON.stringify({phase: 'progress', completed,
  failures, elapsed_ms: Math.round(performance.now()-start)})), 5000);
try {
  await Promise.all(Array.from({length: concurrency}, async () => {
    while (performance.now() - start < duration) {
      await new Promise(resolve => {
        // Match ATLAS: fresh agent, complete response, then release the socket.
        const agent = new http.Agent({keepAlive: true, maxSockets: 1});
        let settled = false;
        const finish = (success, code = 'INCOMPLETE_RESPONSE') => {
          if (settled) return;
          settled = true;
          success ? completed++ : failures++;
          if (!success) errors[code] = (errors[code] ?? 0) + 1;
          agent.destroy();
          resolve();
        };
        const req = http.get({hostname: '127.0.0.1', port: server.address().port, agent}, res => {
          res.resume();
          res.once('end', () => finish(res.complete && res.statusCode === 200));
          res.once('error', error => finish(false, error.code));
        });
        req.once('error', error => finish(false, error.code));
        req.setTimeout(3000, () => { req.destroy(); finish(false, 'TIMEOUT'); });
      });
      // Keep bounded bursts without exhausting Windows' ephemeral port range.
      await pause(500);
    }
  }));
} finally {
  clearInterval(timer);
  server.closeAllConnections();
  server.close();
}
console.log(JSON.stringify({phase: 'complete', completed, failures,
  errors, elapsed_ms: Math.round(performance.now()-start)}));
if (failures || !completed) process.exitCode = 1;
