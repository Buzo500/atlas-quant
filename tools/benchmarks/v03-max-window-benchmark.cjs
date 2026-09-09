/* Additional read-only benchmark. Never imports, starts servers, or changes old evidence.
 * node tools/benchmarks/v03-max-window-benchmark.cjs e2e-<exact active run id>
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { performance } = require('node:perf_hooks');
const root = fs.realpathSync(path.resolve(__dirname, '../..'));
const runId = process.argv[2];
assert.match(runId ?? '', /^e2e-[0-9a-f]{32}$/);
const run = fs.realpathSync(path.join(root, 'var/validation', runId));
assert.equal(path.dirname(run), fs.realpathSync(path.join(root, 'var/validation')));
const BASE = 'http://127.0.0.1:3000';
const identity = JSON.parse(fs.readFileSync(path.join(run, 'run.json'), 'utf8'));
assert.ok(/^[0-9a-f]{32}$/.test(identity.token ?? ''), 'Missing active execution identity.');
function checkRun() {
  const live = JSON.parse(fs.readFileSync(path.join(run, 'run.json'), 'utf8'));
  assert.equal(live.format, 1); assert.equal(live.run_id, runId); assert.equal(live.active, true);
  assert.ok(live.token === identity.token, 'The active execution identity changed.');
  assert.equal(live.base_url, BASE); assert.equal(fs.realpathSync(live.root), root);
  assert.equal(fs.realpathSync(live.data_dir), fs.realpathSync(path.join(run, 'data')));
  for (const pid of [live.harness_pid, live.children?.backend, live.children?.frontend,
    live.listener_pids?.backend, live.listener_pids?.frontend]) {
    assert.ok(Number.isInteger(pid) && pid > 0); process.kill(pid, 0);
  }
}
checkRun();
const previousPath = path.join(root, 'output/validation', `v03-browser-benchmark-${runId}.json`);
fs.mkdirSync(path.dirname(previousPath), { recursive: true });
const previousBytes = fs.readFileSync(previousPath);
const previous = JSON.parse(previousBytes);
assert.equal(previous.success, true); assert.equal(previous.run_id, runId); assert.equal(previous.base_url, BASE);
const dataset = previous.results.find((item) => item.daily_observations === 100000);
assert.ok(dataset && dataset.final_source_identity_preserved);
assert.match(dataset.dataset_id, /^[0-9a-f]{32}$/);
process.env.PLAYWRIGHT_BROWSERS_PATH = path.join(root, 'var/playwright-browsers');
const { chromium } = require(path.join(root, 'frontend/node_modules/@playwright/test'));
const frontendBuildSources = JSON.parse(fs.readFileSync(path.join(root, 'frontend/dist/atlas-build.json'), 'utf8')).sources;
assert.match(frontendBuildSources, /^[0-9a-f]{64}$/);
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const target = path.join(root, 'output/validation', `v03-max-window-benchmark-${runId}-${stamp}.json`);
const sha = (value) => crypto.createHash('sha256').update(value).digest('hex');
const began = performance.now(), abort = new AbortController();
let browser;
const deadline = setTimeout(() => { abort.abort(); void browser?.close(); }, 110000);
const report = { report_format: 2, at: new Date().toISOString(), run_id: runId, base_url: BASE, dataset_id: dataset.dataset_id,
  frontend_build_sources_sha256: frontendBuildSources,
  dataset_version: dataset.dataset_version, manifest_hash: dataset.manifest_hash,
  original_benchmark: previousPath, original_benchmark_sha256: sha(previousBytes),
  additional_read_only_validation: true, imports: 0, mutations: 0,
  viewport_css: { width: 1440, height: 1000 }, physical_dpi_validation: false,
  methodology: 'Dedicated headless Chromium on real compiled UI/API. Expand to 1000 candles, count actual candle groups, point at 20 rendered candle wicks using their actual SVG coordinates transformed through getScreenCTM, dispatch DOM PointerEvents, await two rAF frames and verify date/OHLCV/previous close against the exact immutable snapshot plus the floating tooltip. This measures DOM pointer handling and tooltip rendering, not physical mouse hardware. Alternate 1000/500 zoom windows for 20 samples. DOMCounters and heap follow explicit CDP GC.',
  interaction_method: 'svg-pointer-tooltip-v2',
  historical_comparison: 'Earlier reports had a persistent inspector without this floating tooltip. This report removes slider-derived metrics and includes tooltip rendering; historical timings do not validate the changed UI.',
  network_violations: [], page_errors: [], success: false };
async function api(resource) {
  checkRun(); assert.ok(resource.startsWith('/api/') && !resource.includes('..'));
  assert.ok(!/^\/api\/(feeds|experiments|research)/.test(resource));
  const response = await fetch(BASE + resource, { method: 'GET', redirect: 'manual',
    signal: AbortSignal.any([abort.signal, AbortSignal.timeout(30000)]) });
  if (!response.ok) throw new Error(`GET ${resource}: HTTP ${response.status}`);
  return response.json();
}
function summary(samples) {
  const sorted = [...samples].sort((a, b) => a - b);
  return { samples_ms: samples, median_ms: sorted[Math.floor(sorted.length / 2)],
    p95_ms: sorted[Math.ceil(sorted.length * .95) - 1], max_ms: sorted.at(-1) };
}
async function metrics(page, session) {
  await session.send('HeapProfiler.collectGarbage');
  const heap = await session.send('Runtime.getHeapUsage');
  return { heap_used_bytes: heap.usedSize, heap_total_bytes: heap.totalSize,
    ...(await session.send('Memory.getDOMCounters')),
    ...(await page.evaluate(() => ({
      price_svg_nodes: document.querySelectorAll('.price-chart-svg *').length,
      candle_groups: document.querySelectorAll('.price-chart-svg g.price-rise,.price-chart-svg g.price-fall').length,
      volume_bars: document.querySelectorAll('.price-chart-svg .price-volume-bar').length,
    }))) };
}
(async () => {
  const health = await api('/api/health');
  assert.equal(health.status, 'ok'); assert.equal(health.live_available, false);
  assert.match(health.version, /^0\.3\./); report.health_version = health.version;
  const state = await api('/api/state');
  const current = state.datasets.find((item) => item.id === dataset.dataset_id);
  assert.equal(current?.version, dataset.dataset_version);
  assert.equal(current?.manifest.sha256, dataset.manifest_hash);
  assert.equal(current?.source_kind, 'synthetic'); assert.equal(current?.manifest.row_count, 100000);
  const symbol = current.manifest.symbols[0]; assert.equal(current.manifest.symbols.length, 1);
  const resource = `/api/datasets/${dataset.dataset_id}/prices?version=${dataset.dataset_version}&symbol=${encodeURIComponent(symbol)}`;
  const snapshot = await api(resource);
  assert.equal(snapshot.dataset_version, dataset.dataset_version); assert.equal(snapshot.manifest_hash, dataset.manifest_hash);
  assert.equal(snapshot.bars.length, 100000); report.source_bars_sha256 = sha(JSON.stringify(snapshot.bars));
  browser = await chromium.launch({ headless: true, timeout: 20000,
    args: ['--disable-background-networking', '--disable-background-timer-throttling', '--disable-renderer-backgrounding'] });
  report.chromium = browser.version();
  const context = await browser.newContext({ viewport: report.viewport_css, locale: 'es-ES',
    timezoneId: 'Europe/Madrid', serviceWorkers: 'block' });
  await context.route('**/*', async (route) => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin !== BASE || request.method() !== 'GET' || /^\/api\/(feeds|experiments|research)/.test(url.pathname)) {
      report.network_violations.push(`${request.method()} ${url.origin}${url.pathname}`); await route.abort();
    } else await route.continue();
  });
  await context.routeWebSocket('**/*', async (socket) => { report.network_violations.push('Unexpected WebSocket'); await socket.close(); });
  const page = await context.newPage(); page.setDefaultTimeout(25000); page.setDefaultNavigationTimeout(25000);
  page.on('pageerror', (error) => report.page_errors.push(error.message));
  await page.goto(`${BASE}/?tab=data&dataset=${dataset.dataset_id}`, { waitUntil: 'domcontentloaded' });
  await page.locator('.prices-panel .price-chart-svg').waitFor({ state: 'visible' });
  await page.locator('.prices-panel .price-chart-svg').scrollIntoViewIfNeeded();
  const session = await context.newCDPSession(page);
  report.expansion = await page.evaluate(async () => {
    const wait = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const panel = document.querySelector('.prices-panel');
    const size = () => panel.querySelectorAll('.price-chart-svg g.price-rise,.price-chart-svg g.price-fall').length;
    const button = (name) => [...panel.querySelectorAll('button')].find((item) => (item.getAttribute('aria-label') || item.textContent.trim()) === name);
    const steps = [];
    for (let turn = 0; size() < 1000 && turn < 8; turn++) {
      const next = button('Alejar precios'); if (!next || next.disabled) throw new Error('Cannot expand to 1000 candles.');
      const before = size(); next.click(); await wait();
      const after = size(); if (after <= before) throw new Error('Zoom-out did not enlarge the price window.');
      steps.push({ before, after });
    }
    if (size() !== 1000) throw new Error('Expected exactly 1000 visible candles.');
    const navigator = panel.querySelector('input[type="range"][aria-label="Desplazar precios"]');
    if (!navigator) throw new Error('Missing price window navigator.');
    navigator.focus();
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(navigator, navigator.max);
    navigator.dispatchEvent(new Event('input', { bubbles: true })); await wait();
    if (navigator.valueAsNumber !== Number(navigator.max)) throw new Error('Price window does not end at the final source observation.');
    const groups = panel.querySelectorAll('svg g.price-rise,svg g.price-fall');
    if (groups.length !== 1000) throw new Error(`Expected 1000 actual candle groups, received ${groups.length}.`);
    return { steps, visible_candles: groups.length, source_first_index: 99000, source_last_index: 99999 };
  });
  await page.locator('.prices-panel .price-chart-svg').scrollIntoViewIfNeeded();
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  report.before_pointer = await metrics(page, session);
  const pointer = await page.evaluate(async ({ expected, sourceOffset }) => {
    const wait = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const samples = [], evidence = [];
    const indices = [0, 999, 500, 1, 998, ...Array.from({ length: 15 }, (_, index) => (index * 67 + 23) % 1000)];
    const dateFormat = new Intl.DateTimeFormat('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' });
    for (const index of indices) {
      const svg = document.querySelector('.prices-panel .price-chart-svg');
      const group = svg.querySelectorAll('g.price-rise,g.price-fall')[index];
      const wick = group.querySelector('line');
      const x = Number(wick.getAttribute('x1'));
      const y = (Number(wick.getAttribute('y1')) + Number(wick.getAttribute('y2'))) / 2;
      const ctm = svg.getScreenCTM(); if (!ctm) throw new Error('SVG has no screen transformation.');
      const client = new DOMPoint(x, y).matrixTransform(ctm);
      const tick = performance.now();
      svg.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, pointerType: 'mouse',
        clientX: client.x, clientY: client.y, pointerId: 1, isPrimary: true }));
      await wait(); samples.push(performance.now() - tick);
      const original = expected[index + 1];
      const values = {};
      for (const field of ['open', 'high', 'low', 'close', 'volume']) {
        const node = document.querySelector(`.price-readout [data-price-field="${field}"] data[value]`);
        const value = node ? Number(node.getAttribute('value')) : null;
        if (value !== original[field]) throw new Error(`Pointer ${index}: ${field}=${value}, expected ${original[field]}.`);
        values[field] = value;
      }
      const heading = document.querySelector('.price-readout-heading h3').textContent;
      if (!heading.includes(dateFormat.format(new Date(original.date + 'T00:00:00Z')))) throw new Error('Inspector date differs from snapshot.');
      const tooltip = document.querySelector('[role="tooltip"]');
      if (!tooltip || !tooltip.textContent.includes(dateFormat.format(new Date(original.date + 'T00:00:00Z')))
        || tooltip.getBoundingClientRect().width <= 0) throw new Error('Pointer did not display a tooltip for the inspected source date.');
      const previous = document.querySelector('.price-readout [data-price-field="previous-close"] data[value]');
      const previousDate = document.querySelector('.price-readout [data-price-field="previous-close"] time')?.getAttribute('datetime');
      if (Number(previous?.getAttribute('value')) !== expected[index].close || previousDate !== expected[index].date)
        throw new Error(`Pointer ${index}: preceding session evidence differs from immutable snapshot.`);
      evidence.push({ visible_index: index, source_index: sourceOffset + index, date: original.date,
        svg_x: x, svg_y: y, client_x: client.x, client_y: client.y, ...values, previous_date: previousDate });
    }
    return { samples, evidence };
  }, { expected: snapshot.bars.slice(98999), sourceOffset: 99000 });
  report.pointer = { ...summary(pointer.samples), evidence: pointer.evidence };
  report.after_pointer = await metrics(page, session);
  const zoom = await page.evaluate(async () => {
    const wait = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const samples = [], changes = [];
    const panel = document.querySelector('.prices-panel');
    const size = () => panel.querySelectorAll('.price-chart-svg g.price-rise,.price-chart-svg g.price-fall').length;
    for (let i = 0; i < 20; i++) {
      const name = i % 2 === 0 ? 'Acercar precios' : 'Alejar precios';
      const next = [...panel.querySelectorAll('button')].find((item) => (item.getAttribute('aria-label') || item.textContent.trim()) === name);
      if (!next || next.disabled) throw new Error(`Missing enabled ${name}.`);
      const before = size(), tick = performance.now(); next.click(); await wait();
      samples.push(performance.now() - tick); const after = size();
      if (before !== (i % 2 === 0 ? 1000 : 500) || after !== (i % 2 === 0 ? 500 : 1000))
        throw new Error(`Expected 1000/500 alternation, got ${before}/${after}.`);
      changes.push({ before, after });
    }
    return { samples, changes };
  });
  report.zoom = { ...summary(zoom.samples), changes: zoom.changes };
  report.after_zoom = await metrics(page, session);
  assert.equal(report.after_zoom.candle_groups, 1000);
  const after = await api(resource);
  assert.equal(after.dataset_version, dataset.dataset_version); assert.equal(after.manifest_hash, dataset.manifest_hash);
  assert.equal(sha(JSON.stringify(after.bars)), report.source_bars_sha256);
  report.source_snapshot_unchanged = true;
  assert.equal(sha(fs.readFileSync(previousPath)), report.original_benchmark_sha256);
  report.original_report_unchanged = true;
  assert.deepEqual(report.network_violations, []); assert.deepEqual(report.page_errors, []);
  checkRun(); report.success = true;
})().catch((error) => { report.error = error.stack ?? String(error); process.exitCode = 1; })
  .finally(async () => {
    clearTimeout(deadline); abort.abort(); await browser?.close(); report.elapsed_ms = performance.now() - began;
    fs.writeFileSync(target, JSON.stringify(report, null, 2), { flag: 'wx' });
    console.log(JSON.stringify({ report: target, success: report.success, error: report.error,
      elapsed_ms: report.elapsed_ms, pointer_p95_ms: report.pointer?.p95_ms, zoom_p95_ms: report.zoom?.p95_ms,
      candle_groups: report.after_zoom?.candle_groups, svg_nodes: report.after_zoom?.price_svg_nodes,
      heap_used_bytes: report.after_zoom?.heap_used_bytes }, null, 2));
  });
