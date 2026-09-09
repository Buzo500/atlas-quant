/* Run only against an already active tools/run_e2e.py --manual instance.
 * Usage: node tools/benchmarks/v03-browser-benchmark.cjs e2e-<32 hex>
 * Imports synthetic datasets into that isolated database; never starts servers.
 * One attempt per run: an existing report prevents duplicate imports and evidence replacement.
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { performance } = require('node:perf_hooks');

const root = fs.realpathSync(path.resolve(__dirname, '../..'));
const runId = process.argv[2];
assert.match(runId ?? '', /^e2e-[0-9a-f]{32}$/, 'Pass the exact active isolated run ID.');
const run = fs.realpathSync(path.join(root, 'var/validation', runId));
assert.equal(path.dirname(run), fs.realpathSync(path.join(root, 'var/validation')));
const BASE = 'http://127.0.0.1:3000';
const identity = JSON.parse(fs.readFileSync(path.join(run, 'run.json'), 'utf8'));
assert.ok(/^[0-9a-f]{32}$/.test(identity.token ?? ''), 'The active run must have its execution token.');
function checkRun() {
  const live = JSON.parse(fs.readFileSync(path.join(run, 'run.json'), 'utf8'));
  assert.equal(live.format, 1); assert.equal(live.run_id, runId); assert.equal(live.active, true);
  assert.ok(live.token === identity.token, 'The active execution token changed.'); assert.equal(live.base_url, BASE);
  assert.equal(fs.realpathSync(live.root), root);
  assert.equal(fs.realpathSync(live.data_dir), fs.realpathSync(path.join(run, 'data')));
  for (const pid of [live.harness_pid, live.children?.backend, live.children?.frontend,
    live.listener_pids?.backend, live.listener_pids?.frontend]) {
    assert.ok(Number.isInteger(pid) && pid > 0); process.kill(pid, 0);
  }
  return live;
}
checkRun();
process.env.PLAYWRIGHT_BROWSERS_PATH = path.join(root, 'var/playwright-browsers');
const { chromium } = require(path.join(root, 'frontend/node_modules/@playwright/test'));
const out = path.join(root, 'output/validation', `v03-browser-benchmark-${runId}.json`);
fs.mkdirSync(path.dirname(out), { recursive: true });
const frontendBuildSources = JSON.parse(fs.readFileSync(path.join(root, 'frontend/dist/atlas-build.json'), 'utf8')).sources;
assert.match(frontendBuildSources, /^[0-9a-f]{64}$/);
// Reserve evidence atomically before any HTTP request, browser launch or import.
// A second attempt, including one concurrent with this process, must use a new run.
fs.writeFileSync(out, JSON.stringify({ run_id: runId, status: 'reserved', at: new Date().toISOString() }, null, 2), { flag: 'wx' });
const began = performance.now();
const abort = new AbortController();
let browser;
const deadline = setTimeout(() => {
  abort.abort(new Error('Benchmark exceeded its 170-second execution budget.'));
  void browser?.close();
}, 170000);
const report = { report_format: 3, at: new Date().toISOString(), run_id: runId, base_url: BASE,
  frontend_build_sources_sha256: frontendBuildSources,
  script_sha256: crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex'),
  isolated_data_dir: identity.data_dir, synthetic_only: true, normal_database_accessed: false,
  viewport_css: { width: 1440, height: 1000 }, physical_dpi_validation: false,
  methodology: 'Actual compiled UI/API. First render includes navigation, local HTTP, hydration, scrolling the chart into view and two animation frames. Inspection samples dispatch DOM PointerEvents at actual SVG candle/curve coordinates transformed through getScreenCTM, verify original dates/values and the floating tooltip, then report p95 after two animation frames. Zoom uses real DOM clicks. These include frame pacing, not just handler CPU time; this is not physical mouse hardware. Heap is collected after CDP GC. No API responses are mocked.',
  interaction_method: 'svg-pointer-tooltip-v3-variable-nav',
  historical_comparison: 'Earlier slider and pointer-v2 reports used a flat cash-only NAV. This fixture adds a holding, exercising nonconstant curve geometry and varying values; report the different fixture and method when comparing timings.',
  portfolio_fixture: 'Deposit EUR 10,000 then buy 50 synthetic shares at EUR 100 with zero fee, in input order on the first day. Cash remains EUR 5,000 and NAV is 5,000 + 50 * original closing price; no simulated orders or broker calls.',
  mutations: 'Three synthetic price imports plus preview/commit of one deposit and one purchase per dataset, only in the exact active E2E database.',
  results: [], network_violations: [], page_errors: [], success: false };
const hash = (value) => crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
async function api(resource, body) {
  checkRun();
  assert.ok(resource.startsWith('/api/') && !resource.includes('..'));
  assert.ok(!/^\/api\/(feeds|experiments|research)/.test(resource));
  if (body !== undefined) assert.ok(resource === '/api/datasets' || /^\/api\/datasets\/[a-z0-9]+\/ledger$/.test(resource));
  const response = await fetch(BASE + resource, { method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json', 'X-Atlas-Client': 'local-v1' },
    body: body === undefined ? undefined : JSON.stringify(body), redirect: 'manual',
    signal: AbortSignal.any([abort.signal, AbortSignal.timeout(45000)]) });
  if (!response.ok) throw new Error(`HTTP ${response.status} from ${resource}: ${(await response.text()).slice(0, 300)}`);
  return response.json();
}
function source(count) {
  const symbol = `B${count}`, start = Date.UTC(1750, 0, 1);
  const rows = ['date,symbol,open,high,low,close,volume,currency'];
  const samples = [];
  for (let i = 0; i < count; i++) {
    const day = new Date(start + i * 86400000).toISOString().slice(0, 10);
    const opening = 100 + i % 17, close = opening + 0.25;
    rows.push(`${day},${symbol},${opening},${opening + 1},${opening - 1},${close},${i % 10000},EUR`);
    if ([0, Math.floor(count / 2), count - 1].includes(i))
      samples.push({ index: i, date: day, open: opening, high: opening + 1, low: opening - 1, close, volume: i % 10000 });
  }
  const csv = rows.join('\n');
  assert.ok(Buffer.byteLength(csv) < 8000000);
  assert.ok(samples.at(-1).date < '2026-09-08');
  return { csv, symbol, samples };
}
const frames = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
async function browserFrames(page) { await page.evaluate(frames); }
async function metrics(page, session) {
  await session.send('HeapProfiler.collectGarbage');
  const heap = await session.send('Runtime.getHeapUsage');
  const dom = await session.send('Memory.getDOMCounters');
  const svg = await page.evaluate(() => ({
    allSvgNodes: document.querySelectorAll('svg *').length,
    priceSvgNodes: document.querySelectorAll('.price-chart-svg *').length,
    curveSvgNodes: document.querySelectorAll('figure.chart .chart-viewport svg *').length,
    priceVisibleBarCount: document.querySelectorAll('.price-chart-svg g.price-rise,.price-chart-svg g.price-fall').length,
  }));
  assert.ok(svg.priceVisibleBarCount <= 1000, 'No more than 1000 original/aggregated bars may be painted.');
  return { heap_used_bytes: heap.usedSize, heap_total_bytes: heap.totalSize, ...dom, ...svg };
}
async function interactions(page, kind, sourceCount, count = 20) {
  return page.evaluate(async ({ kind, sourceCount, count }) => {
    const wait = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const results = { inspection_ms: [], zoom_ms: [] };
    const panel = () => document.querySelector(kind === 'prices' ? '.prices-panel' : '.portfolio-curve');
    const svg = () => panel()?.querySelector(kind === 'prices' ? '.price-chart-svg' : 'figure.chart .chart-viewport svg');
    const candles = () => svg()?.querySelectorAll('g.price-rise,g.price-fall');
    const windowSize = () => kind === 'prices' ? candles().length
      : Number(panel().querySelector('.chart-period').textContent.replace(/\D/g, ''));
    if (!(svg() instanceof SVGSVGElement)) throw new Error(`Missing ${kind} chart.`);
    if (kind !== 'prices' && windowSize() !== sourceCount) throw new Error('Initial curve must cover every source observation.');
    const dateFormat = new Intl.DateTimeFormat('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' });
    for (let i = 0; i < count; i++) {
      const element = svg(), visible = windowSize();
      if (!Number.isInteger(visible) || visible < 2) throw new Error('Missing observation window.');
      const index = Math.round((visible - 1) * ((i * 37) % 101) / 100);
      let x, y;
      if (kind === 'prices') {
        const wick = candles()[index].querySelector('line');
        x = Number(wick.getAttribute('x1'));
        y = (Number(wick.getAttribute('y1')) + Number(wick.getAttribute('y2'))) / 2;
      } else {
        const line = element.querySelector('polyline:not([stroke-dasharray])');
        if (!line || line.points.numberOfItems < 2) throw new Error('Missing original curve endpoints.');
        const first = line.points.getItem(0), last = line.points.getItem(line.points.numberOfItems - 1);
        x = first.x + (last.x - first.x) * index / (visible - 1);
        y = (first.y + last.y) / 2;
      }
      const ctm = element.getScreenCTM(); if (!ctm) throw new Error('SVG has no screen transformation.');
      const client = new DOMPoint(x, y).matrixTransform(ctm);
      const sourceIndex = kind === 'prices' ? sourceCount - visible + index : index;
      const expectedDate = new Date(Date.UTC(1750, 0, 1) + sourceIndex * 86400000);
      const began = performance.now();
      element.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, pointerType: 'mouse',
        clientX: client.x, clientY: client.y, pointerId: 1, isPrimary: true }));
      await wait(); results.inspection_ms.push(performance.now() - began);
      if (kind === 'prices') {
        const heading = panel().querySelector('.price-readout-heading h3').textContent;
        const close = panel().querySelector('.price-readout [data-price-field="close"] data[value]');
        if (!heading.includes(dateFormat.format(expectedDate)) || Number(close?.getAttribute('value')) !== 100 + sourceIndex % 17 + 0.25)
          throw new Error('Pointer inspection differs from the original price observation.');
      } else {
        const time = panel().querySelector('.curve-point-detail time')?.getAttribute('datetime');
        const value = panel().querySelector('.curve-point-detail data')?.getAttribute('value');
        if (time !== expectedDate.toISOString().slice(0, 10) || Number(value) !== 5000 + 50 * (100 + sourceIndex % 17 + 0.25))
          throw new Error('Pointer inspection differs from the original curve observation.');
      }
      const tooltip = document.querySelector('[role="tooltip"]');
      if (!tooltip || !tooltip.textContent.includes(dateFormat.format(expectedDate)) || tooltip.getBoundingClientRect().width <= 0)
        throw new Error('Pointer inspection did not show the selected date beside the cursor.');
    }
    for (let i = 0; i < count; i++) {
      const title = (i % 2 === 0 ? 'Acercar' : 'Alejar') + (kind === 'prices' ? ' precios' : ' curva');
      const button = [...panel().querySelectorAll('button')].find((item) => (item.getAttribute('aria-label') || item.textContent.trim()) === title);
      if (!button || button.disabled) throw new Error(`Missing/enabled zoom control: ${title}`);
      const before = windowSize();
      const began = performance.now(); button.click(); await wait();
      results.zoom_ms.push(performance.now() - began);
      const after = windowSize();
      if (i % 2 === 0 ? !(after < before) : !(after > before)) throw new Error(`Zoom did not change the ${kind} window.`);
    }
    for (const name of Object.keys(results)) {
      const sorted = [...results[name]].sort((a, b) => a - b);
      results[name] = { samples: results[name], median: sorted[Math.floor(sorted.length / 2)],
        p95: sorted[Math.ceil(sorted.length * .95) - 1], max: sorted.at(-1) };
    }
    return results;
  }, { kind, sourceCount, count });
}
async function selectTab(page, name) {
  await page.getByRole('tab', { name, exact: true }).click();
  await page.waitForFunction((name) => [...document.querySelectorAll('[role="tab"]')]
    .some((node) => node.textContent.trim() === name && node.getAttribute('aria-selected') === 'true'), name);
}
async function waitPrices(page) {
  await page.locator('.prices-panel .price-chart-svg').waitFor({ state: 'visible' });
  await page.locator('.prices-panel .price-chart-svg').scrollIntoViewIfNeeded();
  await page.locator('.prices-panel [data-price-field="close"]').waitFor({ state: 'visible' });
  await browserFrames(page);
}
async function waitCurve(page) {
  await page.locator('.portfolio-curve figure.chart .chart-viewport svg').waitFor({ state: 'visible' });
  await page.locator('.portfolio-curve figure.chart .chart-viewport svg').scrollIntoViewIfNeeded();
  await browserFrames(page);
}
async function inspectEvidence(page, sample) {
  return page.evaluate(async (sample) => {
    const svg = document.querySelector('.prices-panel .price-chart-svg');
    svg.focus();
    svg.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true, cancelable: true }));
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const actual = {};
    for (const field of ['open', 'high', 'low', 'close', 'volume']) {
      const element = document.querySelector(`.price-readout [data-price-field="${field}"]`);
      const raw = element.matches('data[value]') ? element.getAttribute('value') : element.querySelector('data[value]')?.getAttribute('value');
      const formatted = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 20 }).format(sample[field]);
      const text = element.textContent.replace(/\s+/g, ' ').trim();
      if (raw != null ? Number(raw) !== sample[field] : text !== formatted + (field === 'volume' ? '' : ' EUR'))
        throw new Error(`Price ${field} mismatch: ${text}.`);
      actual[field] = { raw: raw == null ? null : Number(raw), text };
    }
    return actual;
  }, sample);
}

(async () => {
  const health = await api('/api/health');
  assert.equal(health.status, 'ok'); assert.equal(health.live_available, false);
  assert.match(health.version, /^0\.3\./); report.health_version = health.version;
  browser = await chromium.launch({ headless: true, timeout: 20000,
    args: ['--disable-background-networking', '--disable-background-timer-throttling', '--disable-renderer-backgrounding'] });
  report.chromium = browser.version();
  const context = await browser.newContext({ viewport: report.viewport_css, locale: 'es-ES',
    timezoneId: 'Europe/Madrid', serviceWorkers: 'block' });
  await context.route('**/*', async (route) => {
    const request = route.request(), url = new URL(request.url());
    const allowed = url.origin === BASE && !/^\/api\/(feeds|experiments|research)/.test(url.pathname)
      && request.method() === 'GET';
    if (!allowed) { report.network_violations.push(`${request.method()} ${url.origin}${url.pathname}`); await route.abort(); }
    else await route.continue();
  });
  await context.routeWebSocket('**/*', async (socket) => { report.network_violations.push('Unexpected WebSocket'); await socket.close(); });
  const page = await context.newPage();
  page.setDefaultTimeout(25000); page.setDefaultNavigationTimeout(25000);
  page.on('pageerror', (error) => report.page_errors.push(error.message));
  const session = await context.newCDPSession(page);
  for (const size of [1000, 10000, 100000]) {
    const generated = source(size), writeBegin = performance.now();
    const importedDataset = await api('/api/datasets', { name: `BENCH ${size} ${runId.slice(-8)}`, csv: generated.csv,
      source_kind: 'synthetic', source: `Offline browser benchmark ${runId}; generated integer daily sessions` });
    assert.equal(importedDataset.manifest.row_count, size);
    const csv = `id,date,kind,symbol,quantity,price,amount,fee,currency\nbench-deposit-${size},${generated.samples[0].date},deposit,,,,10000,,EUR\nbench-buy-${size},${generated.samples[0].date},buy,${generated.symbol},50,100,,0,EUR\n`;
    const preview = await api(`/api/datasets/${importedDataset.id}/ledger`, { csv, commit: false });
    const committed = await api(`/api/datasets/${importedDataset.id}/ledger`, { csv, commit: true, preview_token: preview.preview_token });
    assert.equal(committed.committed, true);
    assert.equal(committed.portfolio.cash, 5000);
    assert.equal(committed.portfolio.nav, 5000 + 50 * generated.samples.at(-1).close);
    assert.equal(committed.portfolio.curve.length, size);
    for (let index = 0; index < size; index++)
      assert.equal(committed.portfolio.curve[index].nav, 5000 + 50 * (100 + index % 17 + 0.25));
    assert.equal(new Set(committed.portfolio.curve.map((point) => point.nav)).size, 17);
    // Establish the baseline after all setup writes, from the same state route
    // used by the actual UI; never infer a version from an earlier response.
    const setupState = await api('/api/state');
    const dataset = setupState.datasets.find((item) => item.id === importedDataset.id);
    assert.ok(dataset, 'The imported synthetic dataset must remain in current state.');
    assert.equal(dataset.manifest.sha256, importedDataset.manifest.sha256);
    assert.equal(dataset.manifest.row_count, size);
    const item = { daily_observations: size, dataset_id: dataset.id, dataset_version: dataset.version,
      manifest_hash: dataset.manifest.sha256, generated_csv_bytes: Buffer.byteLength(generated.csv),
      generated_csv_sha256: crypto.createHash('sha256').update(generated.csv).digest('hex'), source_samples: generated.samples,
      setup_ms: performance.now() - writeBegin, portfolio: { nav: committed.portfolio.nav, observations: size,
        curve_sha256: hash(committed.portfolio.curve), first: committed.portfolio.curve[0], last: committed.portfolio.curve.at(-1) } };
    report.results.push(item);
    let tick = performance.now();
    await page.goto(`${BASE}/?tab=data&dataset=${dataset.id}`, { waitUntil: 'domcontentloaded' });
    await waitPrices(page); item.first_price_render_ms = performance.now() - tick;
    assert.ok((await page.locator('.prices-trace').textContent()).includes(dataset.manifest.sha256));
    item.initial_price_evidence = await inspectEvidence(page, generated.samples.at(-1));
    item.prices_interactions = await interactions(page, 'prices', size);
    item.prices_memory = await metrics(page, session);
    tick = performance.now(); await selectTab(page, 'Cartera'); await waitCurve(page);
    item.first_curve_render_ms = performance.now() - tick;
    item.curve_interactions = await interactions(page, 'curve', size);
    item.curve_memory = await metrics(page, session);
    const evidence = await page.locator('.portfolio-curve .curve-point-detail data').first().getAttribute('value');
    const inspectedDate = await page.locator('.portfolio-curve .curve-point-detail time').getAttribute('datetime');
    const inspectedIndex = (Date.parse(inspectedDate + 'T00:00:00Z') - Date.UTC(1750, 0, 1)) / 86400000;
    assert.ok(Number.isInteger(inspectedIndex) && inspectedIndex >= 0 && inspectedIndex < size);
    assert.equal(Number(evidence), 5000 + 50 * (100 + inspectedIndex % 17 + 0.25));
    item.inspected_nav = Number(evidence); item.inspected_date = inspectedDate;
    if (size === 100000) {
      item.tab_cycle_memory = [{ cycle: 0, ...(await metrics(page, session)) }];
      for (let cycle = 1; cycle <= 8; cycle++) {
        await selectTab(page, 'Datos'); await waitPrices(page);
        await selectTab(page, 'Cartera'); await waitCurve(page);
        if ([1, 4, 8].includes(cycle)) item.tab_cycle_memory.push({ cycle, ...(await metrics(page, session)) });
      }
      const first = item.tab_cycle_memory[1], last = item.tab_cycle_memory.at(-1);
      item.post_warmup_memory_delta = { heap_used_bytes: last.heap_used_bytes - first.heap_used_bytes,
        nodes: last.nodes - first.nodes, listeners: last.jsEventListeners - first.jsEventListeners,
        caveat: 'Eight tab cycles and GC are a short diagnostic; this is not a sustained-memory or 48-hour test.' };
    }
    fs.writeFileSync(out, JSON.stringify(report, null, 2));
  }
  const state = await api('/api/state');
  for (const item of report.results) {
    const current = state.datasets.find((dataset) => dataset.id === item.dataset_id);
    assert.equal(current.version, item.dataset_version); assert.equal(current.manifest.sha256, item.manifest_hash);
    assert.equal(current.manifest.row_count, item.daily_observations);
    item.final_source_identity_preserved = true;
  }
  assert.deepEqual(report.network_violations, []); assert.deepEqual(report.page_errors, []);
  checkRun(); report.success = true;
})().catch((error) => { report.error = error.stack ?? String(error); process.exitCode = 1; })
  .finally(async () => {
    clearTimeout(deadline); abort.abort(); await browser?.close();
    report.elapsed_ms = performance.now() - began;
    fs.writeFileSync(out, JSON.stringify(report, null, 2));
    console.log(JSON.stringify({ report: out, success: report.success, elapsed_ms: report.elapsed_ms,
      error: report.error, samples: report.results.map((item) => ({ n: item.daily_observations,
        price_first_ms: item.first_price_render_ms, curve_first_ms: item.first_curve_render_ms,
        price_inspection_p95_ms: item.prices_interactions?.inspection_ms.p95,
        price_zoom_p95_ms: item.prices_interactions?.zoom_ms.p95,
        curve_inspection_p95_ms: item.curve_interactions?.inspection_ms.p95,
        curve_zoom_p95_ms: item.curve_interactions?.zoom_ms.p95 })) }, null, 2));
  });
