'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

function assertStateResponse(status, state) {
  assert.equal(status, 200, 'La lectura de estado debe responder HTTP 200.');
  assert.equal(state.settings.kill_switch, true);
  assert.ok(state.providers.every(provider => !provider.configured));
  assert.equal(state.experiments.length, 0);
  assert.ok(state.datasets.every(dataset => dataset.source_kind === 'synthetic'));
}

function readActiveRun(root, runId, token) {
  assert.match(runId || '', /^e2e-[a-f0-9]{32}$/);
  const parent = fs.realpathSync(path.join(root, 'var/validation'));
  const folder = fs.realpathSync(path.join(parent, runId));
  assert.equal(path.dirname(folder), parent);
  const current = JSON.parse(fs.readFileSync(path.join(folder, 'run.json'), 'utf8'));
  assert.equal(current.format, 1);
  assert.equal(current.active, true);
  assert.match(current.token || '', /^[a-f0-9]{32}$/);
  if (token !== undefined) assert.equal(current.token, token);
  assert.equal(fs.realpathSync(current.root), fs.realpathSync(root));
  assert.equal(current.run_id, runId);
  assert.equal(current.base_url, 'http://127.0.0.1:3000');
  const data = fs.realpathSync(path.join(folder, 'data'));
  assert.equal(path.dirname(data), folder);
  assert.equal(fs.realpathSync(current.data_dir), data);
  for (const pid of [current.harness_pid, current.children?.backend, current.children?.frontend,
    current.listener_pids?.backend, current.listener_pids?.frontend]) {
    assert.ok(Number.isInteger(pid) && pid > 0, 'Falta un proceso E2E identificado.');
    process.kill(pid, 0);
  }
  return current;
}

module.exports = { assertStateResponse, readActiveRun };
