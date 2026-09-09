'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { assertStateResponse, readActiveRun } = require('./checks.cjs');

const state = () => ({ settings: { kill_switch: true }, providers: [{ configured: false }],
  experiments: [], datasets: [{ source_kind: 'synthetic' }] });

test('every client rejects an HTTP error even with a valid-looking state body', () => {
  assertStateResponse(200, state());
  for (const status of [201, 302, 401, 500, 503]) {
    assert.throws(() => assertStateResponse(status, state()), /HTTP 200/);
  }
});

test('state preflight rejects configured providers, jobs, ordinary data and disabled stop', () => {
  for (const mutate of [s => { s.settings.kill_switch = false; },
    s => { s.providers[0].configured = true; }, s => { s.experiments.push({}); },
    s => { s.datasets[0].source_kind = 'csv'; }]) {
    const current = state(); mutate(current);
    assert.throws(() => assertStateResponse(200, current));
  }
});

test('a client accepts only a complete, active and unchanged isolated run identity', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-diag-checks-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const id = 'e2e-' + 'a'.repeat(32), token = 'b'.repeat(32);
  const folder = path.join(root, 'var/validation', id);
  fs.mkdirSync(path.join(folder, 'data'), { recursive: true });
  const valid = { format: 1, root, run_id: id, token, active: true,
    base_url: 'http://127.0.0.1:3000', data_dir: path.join(folder, 'data'),
    harness_pid: process.pid, children: { backend: process.pid, frontend: process.pid },
    listener_pids: { backend: process.pid, frontend: process.pid } };
  const write = value => fs.writeFileSync(path.join(folder, 'run.json'), JSON.stringify(value));
  write(valid);
  assert.equal(readActiveRun(root, id, token).run_id, id);
  assert.throws(() => readActiveRun(root, '../atlas', token));
  assert.throws(() => readActiveRun(root, id, 'c'.repeat(32)));
  for (const patch of [{ active: false }, { format: 2 }, { token: '' },
    { base_url: 'http://localhost:3000' }, { data_dir: root },
    { listener_pids: {} }, { children: {} }, { harness_pid: -1 }, { run_id: 'other' }]) {
    write({ ...valid, ...patch });
    assert.throws(() => readActiveRun(root, id, token));
  }
});
