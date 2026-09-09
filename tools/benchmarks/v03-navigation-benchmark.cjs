/* Read-only navigation benchmark against an already active isolated manual E2E run.
 * node tools/benchmarks/v03-navigation-benchmark.cjs e2e-<exact 32 hex run id>
 * Requires the successful v03-browser-benchmark report and its 100,000-row dataset.
 * Never starts servers, imports data, changes Windows DPI, or replaces earlier evidence.
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
assert.match(identity.token ?? '', /^[0-9a-f]{32}$/);
function checkRun() {
  const live = JSON.parse(fs.readFileSync(path.join(run, 'run.json'), 'utf8'));
  assert.equal(live.format, 1); assert.equal(live.run_id, runId); assert.equal(live.active, true);
  assert.equal(live.token, identity.token); assert.equal(live.base_url, BASE);
  assert.equal(fs.realpathSync(live.root), root);
  assert.equal(fs.realpathSync(live.data_dir), fs.realpathSync(path.join(run, 'data')));
  for (const pid of [live.harness_pid, live.children?.backend, live.children?.frontend,
    live.listener_pids?.backend, live.listener_pids?.frontend]) {
    assert.ok(Number.isInteger(pid) && pid > 0); process.kill(pid, 0);
  }
}
checkRun();
const previousPath = path.join(root, 'output/validation', `v03-browser-benchmark-${runId}.json`);
const previousBytes = fs.readFileSync(previousPath), previous = JSON.parse(previousBytes);
assert.equal(previous.success, true); assert.equal(previous.run_id, runId); assert.equal(previous.base_url, BASE);
const dataset = previous.results.find((item) => item.daily_observations === 100000);
assert.ok(dataset?.final_source_identity_preserved); assert.match(dataset.dataset_id, /^[0-9a-f]{32}$/);
const build = JSON.parse(fs.readFileSync(path.join(root, 'frontend/dist/atlas-build.json'), 'utf8')).sources;
assert.match(build, /^[0-9a-f]{64}$/);
const sha = (value) => crypto.createHash('sha256').update(value).digest('hex');
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const out = path.join(root, 'output/validation', `v03-navigation-benchmark-${runId}-${stamp}.json`);
const artifactDir = path.join(run, `navigation-benchmark-${stamp}`);
fs.mkdirSync(artifactDir);
process.env.PLAYWRIGHT_BROWSERS_PATH = path.join(root, 'var/playwright-browsers');
const { chromium } = require(path.join(root, 'frontend/node_modules/@playwright/test'));
const abort = new AbortController(), began = performance.now();
let browser;
const deadline = setTimeout(() => { abort.abort(new Error('Navigation benchmark exceeded 240 seconds.')); void browser?.close(); }, 240000);
const report = { report_format: 2, at: new Date().toISOString(), run_id: runId, base_url: BASE,
  frontend_build_sources_sha256: build, script_sha256: sha(fs.readFileSync(__filename)),
  original_benchmark: previousPath, original_benchmark_sha256: sha(previousBytes),
  dataset_id: dataset.dataset_id, dataset_version: dataset.dataset_version, manifest_hash: dataset.manifest_hash,
  source_observations: 100000, synthetic_only: true, additional_read_only_validation: true,
  imports: 0, mutations: 0, physical_dpi_validation: false, artifact_directory: artifactDir,
  methodology: 'Dedicated headless Chromium, compiled UI and real GET-only API. Twenty samples per navigation/zoom/hover/drag/wheel and fullscreen-open/close interaction; each ends after two requestAnimationFrame callbacks. DOM events measure handler/render plus frame pacing; Playwright mouse and fullscreen clicks also include automation dispatch/settling. drag_gesture_total preserves the former drag measurement: real down, three moves, up, protocol and two frames. drag_update measures one DOM pointermove and two frames during a genuinely active mouse drag, with its actual trusted pointerId. Only drag_update is comparable with a per-update responsiveness target. Fullscreen native at 3440x1440 CSS pixels and denied-API fallback at 390x844; no physical DPI claim. Curve source has 100,000 original observations, price window is capped at 1,000 real candles. No API responses mocked. Native fullscreen denial is the only browser API mock, exclusively in fallback mode.',
  memory_method: 'Two warmed open/close cycles followed by 20 measured cycles; CDP explicit GC and DOMCounters at identical closed range/focus/tooltip state after cycles 0, 5, 10 and 20. Deltas are a short diagnostic, not proof of no memory leak or a sustained trial.',
  results: [], network_violations: [], page_errors: [], request_failures: [], http_errors: [], state_gets: [], success: false };
async function api(resource) {
  checkRun(); assert.ok(resource.startsWith('/api/') && !resource.includes('..'));
  assert.ok(!/^\/api\/(feeds|experiments|research)/.test(resource));
  const response = await fetch(BASE + resource, { method: 'GET', redirect: 'manual',
    signal: AbortSignal.any([abort.signal, AbortSignal.timeout(30000)]) });
  assert.ok(response.ok, `GET ${resource}: HTTP ${response.status}`); return response.json();
}
const frames = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
const summarize = (samples) => {
  assert.equal(samples.length, 20); const sorted = [...samples].sort((a, b) => a - b);
  return { samples_ms: samples, median_ms: sorted[10], p95_ms: sorted[18], max_ms: sorted[19] };
};
async function installProbe(page, kind) {
  await page.evaluate((kind) => {
    // Inactive app tabs are legitimately inert before fullscreen. Preserve their
    // exact nodes and attribute values instead of assuming an empty global set.
    const baseline = {
      bodyOverflow: document.body.style.overflow,
      inert: [...document.querySelectorAll('[inert]')].map((element) => ({
        element, value: element.getAttribute('inert'),
      })),
    };
    const owner = () => document.querySelector(kind === 'prices' ? '.prices-panel' : '.portfolio-curve');
    const svg = () => owner().querySelector(kind === 'prices' ? '.price-chart-svg' : 'figure.chart .chart-viewport svg');
    const range = () => owner().querySelector('input.chart-workspace-range');
    const noun = kind === 'prices' ? 'precios' : 'curva';
    const state = () => {
      const input = range(), start = input.valueAsNumber, count = 100000 - Number(input.max);
      if (start < 0 || count < 1 || start + count > 100000) throw new Error('Window exceeds original source bounds.');
      const painted = kind === 'prices' ? svg().querySelectorAll('g.price-rise,g.price-fall').length
        : Number(owner().querySelector('.chart-period').textContent.replace(/\D/g, ''));
      if (painted !== count || (kind === 'prices' && count > 1000)) throw new Error(`Invalid painted window: ${painted}/${count}.`);
      return { start, count };
    };
    const button = (name) => [...owner().querySelectorAll('button')].find((node) => node.getAttribute('aria-label') === name);
    const navigate = (value) => {
      const input = range(); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    };
    const point = (fraction = 0.5) => {
      const element = svg(), current = state(), index = Math.round((current.count - 1) * fraction);
      let x, y;
      if (kind === 'prices') {
        const wick = element.querySelectorAll('g.price-rise,g.price-fall')[index].querySelector('line');
        x = Number(wick.getAttribute('x1')); y = (Number(wick.getAttribute('y1')) + Number(wick.getAttribute('y2'))) / 2;
      } else {
        const line = element.querySelector('polyline:not([stroke-dasharray])');
        const first = line.points.getItem(0), last = line.points.getItem(line.points.numberOfItems - 1);
        x = first.x + (last.x - first.x) * index / (current.count - 1); y = (first.y + last.y) / 2;
      }
      const matrix = element.getScreenCTM(); if (!matrix) throw new Error('Missing SVG transformation.');
      const client = new DOMPoint(x, y).matrixTransform(matrix);
      return { x: client.x, y: client.y, source_index: current.start + index };
    };
    const wait = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    window.atlasNavigationProbe = { owner, svg, range, noun, state, button, navigate, point, wait, baseline };
  }, kind);
}
async function state(page) { return page.evaluate(() => window.atlasNavigationProbe.state()); }
async function domBatch(page, action) {
  const value = await page.evaluate(async (action) => {
    const p = window.atlasNavigationProbe, samples = [], changes = [];
    for (let i = 0; i < 20; i++) {
      const before = p.state(), tick = performance.now();
      if (action === 'navigation') p.navigate(Math.round(Number(p.range().max) * (i % 2 ? 0.75 : 0.25)));
      else p.button(`${i % 2 ? 'Alejar' : 'Acercar'} ${p.noun}`).click();
      await p.wait(); const after = p.state(); samples.push(performance.now() - tick);
      if (action === 'navigation' ? before.count !== after.count || before.start === after.start
        : i % 2 ? after.count <= before.count : after.count >= before.count) throw new Error(`Ineffective ${action}.`);
      changes.push({ before, after });
    }
    return { samples, changes };
  }, action);
  return { ...summarize(value.samples), changes: value.changes };
}
async function hoverBatch(page, kind, snapshot, portfolio, target) {
  const samples = [], evidence = [];
  Object.assign(target, { samples_ms: samples, evidence, completed_samples: 0 });
  for (let i = 0; i < 20; i++) {
    const result = await page.evaluate(async ({ fraction, index }) => {
      const p = window.atlasNavigationProbe, point = p.point(fraction);
      const geometry = () => {
        const svg = p.svg(), box = svg.getBoundingClientRect(), ctm = svg.getScreenCTM();
        return { range: p.state(), box: { x: box.x, y: box.y, width: box.width, height: box.height },
          ctm: ctm ? [ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f] : null,
          view_box: svg.getAttribute('viewBox'), dragging: svg.dataset.chartDragging ?? null,
          viewport: { width: innerWidth, height: innerHeight } };
      };
      const before = geometry(), tick = performance.now();
      p.svg().dispatchEvent(new PointerEvent('pointermove', { bubbles: true, pointerType: 'mouse',
        clientX: point.x, clientY: point.y, pointerId: 1, isPrimary: true }));
      await p.wait(); const duration = performance.now() - tick;
      const after = geometry(), tip = document.querySelector('[role="tooltip"]');
      const result = { sample_index: index, duration, source_index: point.source_index, pointer: point, before, after };
      if (!tip) return { ...result, error: 'Missing hover tooltip after exactly two animation frames.' };
      const rect = tip.getBoundingClientRect(), expanded = document.querySelector('.chart-workspace.is-expanded');
      if (rect.width <= 0 || rect.left < 0 || rect.top < 0 || rect.right > innerWidth + 1 || rect.bottom > innerHeight + 1)
        return { ...result, error: 'Tooltip exceeds viewport.', bounds: { x: rect.x, y: rect.y, width: rect.width, height: rect.height } };
      if (expanded && !expanded.contains(tip)) return { ...result, error: 'Tooltip outside fullscreen portal.' };
      const detail = p.owner().querySelector('.price-readout') ?? p.owner().querySelector('.curve-point-detail');
      return { ...result, date: tip.querySelector('time')?.getAttribute('datetime'),
        values: [...detail.querySelectorAll('data[value]')].map((node) => Number(node.getAttribute('value'))),
        close: detail.querySelector('[data-price-field="close"] data')?.getAttribute('value'),
        tooltip_fields: Object.fromEntries([...tip.querySelectorAll('[data-price-field]')].map((node) => [
          node.getAttribute('data-price-field'), Number(node.querySelector('data')?.getAttribute('value')),
        ])),
        tooltip_values: [...tip.querySelectorAll('data[value]')].map((node) => Number(node.getAttribute('value'))),
        bounds: { x: rect.x, y: rect.y, width: rect.width, height: rect.height } };
    }, { fraction: i < 2 ? i : ((i * 37) % 101) / 100, index: i });
    evidence.push(result);
    try {
      assert.ok(!result.error, `${result.error} Sample ${i}, source ${result.source_index}, point ${JSON.stringify(result.pointer)}, geometry ${JSON.stringify({ before: result.before, after: result.after })}`);
      const original = kind === 'prices' ? snapshot.bars[result.source_index] : portfolio.curve[result.source_index];
      assert.equal(result.date, original.date);
      if (kind === 'prices') {
        assert.equal(Number(result.close), original.close);
        for (const field of ['open', 'high', 'low', 'close', 'volume'])
          assert.equal(result.tooltip_fields[field], original[field], `Tooltip ${field} differs from original observation.`);
      } else { assert.equal(result.values[0], original.nav); assert.equal(result.tooltip_values[0], original.nav); }
    } catch (error) { target.failed_sample = { ...result, error: error.message }; throw error; }
    samples.push(result.duration); target.completed_samples = samples.length;
  }
  Object.assign(target, summarize(samples)); return target;
}
async function layout(page, expanded, mode) {
  const result = await page.evaluate(() => {
    const p = window.atlasNavigationProbe, workspace = p.owner().querySelector('.chart-workspace');
    const rect = workspace.getBoundingClientRect(), plot = p.svg().getBoundingClientRect();
    const inert = [...document.querySelectorAll('[inert]')];
    return { ...p.state(), expanded: workspace.classList.contains('is-expanded'), native: document.fullscreenElement === workspace,
      workspace: { width: rect.width, height: rect.height }, plot: { width: plot.width, height: plot.height },
      viewport: { width: innerWidth, height: innerHeight }, overflow: document.documentElement.scrollWidth > innerWidth + 1,
      toolbar_icons: workspace.querySelectorAll('.chart-workspace-actions button svg').length,
      body_overflow: document.body.style.overflow, baseline_body_overflow: p.baseline.bodyOverflow,
      inert_nodes: inert.length, baseline_inert_nodes: p.baseline.inert.length,
      inert_baseline_restored: inert.length === p.baseline.inert.length && p.baseline.inert.every(
        (prior, index) => inert[index] === prior.element && prior.element.getAttribute('inert') === prior.value,
      ),
      focus: document.activeElement?.getAttribute('aria-label'), tooltip_count: document.querySelectorAll('[role="tooltip"]').length };
  });
  assert.equal(result.expanded, expanded); assert.equal(result.native, expanded && mode === 'native');
  assert.equal(result.overflow, false); assert.equal(result.toolbar_icons, 4);
  if (expanded) {
    assert.ok(Math.abs(result.workspace.width - result.viewport.width) < 2);
    assert.ok(Math.abs(result.workspace.height - result.viewport.height) < 2); assert.ok(result.plot.height > 300);
  } else {
    assert.equal(result.body_overflow, result.baseline_body_overflow);
    assert.equal(result.inert_baseline_restored, true, 'Fullscreen must restore the exact pre-existing inert nodes and attributes.');
  }
  return result;
}
async function toggle(page, expanded, mode) {
  const before = await state(page), tick = await page.evaluate(() => performance.now());
  await page.getByRole('button', { name: expanded ? /^Pantalla completa:/ : 'Salir de pantalla completa', exact: !expanded }).click();
  await page.waitForFunction(({ expanded, mode }) => {
    const full = document.querySelector('.chart-workspace.is-expanded');
    return Boolean(full) === expanded && Boolean(document.fullscreenElement) === (expanded && mode === 'native');
  }, { expanded, mode });
  await page.evaluate(frames); const elapsed = await page.evaluate((tick) => performance.now() - tick, tick);
  assert.deepEqual(await state(page), before); return elapsed;
}
async function memory(page, session, mode) {
  await page.evaluate(frames); await session.send('HeapProfiler.collectGarbage');
  const heap = await session.send('Runtime.getHeapUsage'), dom = await session.send('Memory.getDOMCounters');
  const view = await layout(page, false, mode);
  assert.equal(view.tooltip_count, 0); assert.match(view.focus, /^Pantalla completa:/);
  return { heap_used_bytes: heap.usedSize, ...dom, view };
}
async function gestures(page, kind, snapshot, portfolio) {
  const wheel = [], wheelChanges = [], drag = [], dragChanges = [];
  for (let i = 0; i < 20; i++) {
    const before = await state(page), point = await page.evaluate(() => window.atlasNavigationProbe.point());
    await page.mouse.move(point.x, point.y);
    const tick = await page.evaluate(() => performance.now());
    await page.mouse.wheel(0, i % 2 ? 100 : -100); await page.evaluate(frames);
    wheel.push(await page.evaluate((tick) => performance.now() - tick, tick));
    const after = await state(page);
    assert.ok(i % 2 ? after.count > before.count : after.count < before.count); wheelChanges.push({ before, after });
  }
  for (let i = 0; i < 20; i++) {
    const before = await state(page), point = await page.evaluate(() => window.atlasNavigationProbe.point());
    await page.mouse.move(point.x, point.y); const tick = await page.evaluate(() => performance.now());
    await page.mouse.down(); await page.mouse.move(point.x + (i % 2 ? -40 : 40), point.y, { steps: 3 });
    await page.mouse.up(); await page.evaluate(frames);
    drag.push(await page.evaluate((tick) => performance.now() - tick, tick));
    const after = await state(page); assert.equal(after.count, before.count);
    assert.ok(i % 2 ? after.start > before.start : after.start < before.start);
    assert.equal(await page.getByRole('tooltip').count(), 0); dragChanges.push({ before, after });
  }
  // Keep total real gestures separate from one update's handler/render latency.
  const anchor = await page.evaluate(() => window.atlasNavigationProbe.point());
  await page.mouse.move(anchor.x, anchor.y);
  await page.evaluate(() => {
    const p = window.atlasNavigationProbe; p.dragPointer = null;
    p.svg().addEventListener('pointerdown', (event) => {
      p.dragPointer = { pointerId: event.pointerId, pointerType: event.pointerType,
        isPrimary: event.isPrimary, isTrusted: event.isTrusted, clientX: event.clientX, clientY: event.clientY };
    }, { once: true });
  });
  let updates;
  await page.mouse.down();
  try {
    // Focus/initial inspection is outside the per-move measurement.
    await page.evaluate(frames);
    updates = await page.evaluate(async () => {
      const p = window.atlasNavigationProbe, pointer = p.dragPointer;
      if (!pointer?.isTrusted || pointer.pointerType !== 'mouse' || !Number.isInteger(pointer.pointerId)
        || !p.svg().hasPointerCapture(pointer.pointerId)) throw new Error('No genuine captured pointerdown for drag measurement.');
      const initial = p.state(), samples = [], changes = [];
      for (let i = 0; i < 20; i++) {
        const before = p.state(), clientX = pointer.clientX + (i % 2 ? 0 : 40), tick = performance.now();
        p.svg().dispatchEvent(new PointerEvent('pointermove', { bubbles: true, cancelable: true,
          pointerId: pointer.pointerId, pointerType: pointer.pointerType, isPrimary: pointer.isPrimary,
          buttons: 1, button: -1, clientX, clientY: pointer.clientY }));
        await p.wait(); const duration = performance.now() - tick, after = p.state();
        if (after.count !== before.count || (i % 2 ? after.start <= before.start : after.start >= before.start))
          throw new Error(`Drag update ${i} did not preserve count and move in the expected direction.`);
        if (document.querySelector('[role="tooltip"]')) throw new Error('Tooltip remains visible while dragging.');
        const curveDates = [...p.owner().querySelectorAll('input[type="date"]')].map((node) => node.value);
        changes.push({ before, after, clientX, clientY: pointer.clientY, curve_dates: curveDates,
          price_window_text: p.owner().querySelector('.prices-window-summary')?.textContent ?? null });
        samples.push(duration);
      }
      if (p.state().start !== initial.start || p.state().count !== initial.count)
        throw new Error('Returning the pointer to its origin did not restore the exact initial range.');
      return { pointer, initial, samples, changes };
    });
  } finally { await page.mouse.up(); await page.evaluate(frames); }
  const originals = kind === 'prices' ? snapshot.bars : portfolio.curve;
  const formatDate = new Intl.DateTimeFormat('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' });
  for (const item of updates.changes) {
    const first = originals[item.after.start].date, last = originals[item.after.start + item.after.count - 1].date;
    item.source_dates = { first, last };
    if (kind === 'curve') assert.deepEqual(item.curve_dates, [first, last]);
    else for (const date of [first, last]) assert.ok(item.price_window_text.includes(formatDate.format(new Date(date + 'T00:00:00Z'))));
  }
  return { wheel: { ...summarize(wheel), changes: wheelChanges },
    drag_gesture_total: { ...summarize(drag), changes: dragChanges },
    drag_update: { ...summarize(updates.samples), pointer: updates.pointer, initial: updates.initial, changes: updates.changes } };
}
(async () => {
  const health = await api('/api/health'); assert.equal(health.status, 'ok'); assert.equal(health.live_available, false);
  assert.match(health.version, /^0\.3\./); report.health_version = health.version;
  const initialState = await api('/api/state'), current = initialState.datasets.find((item) => item.id === dataset.dataset_id);
  assert.equal(current?.version, dataset.dataset_version); assert.equal(current?.manifest.sha256, dataset.manifest_hash);
  assert.equal(current.source_kind, 'synthetic'); assert.equal(current.manifest.row_count, 100000);
  assert.equal(current.manifest.symbols.length, 1);
  const resource = `/api/datasets/${dataset.dataset_id}/prices?version=${dataset.dataset_version}&symbol=${encodeURIComponent(current.manifest.symbols[0])}`;
  const portfolioResource = `/api/datasets/${dataset.dataset_id}/portfolio`;
  const snapshot = await api(resource), portfolio = await api(portfolioResource);
  assert.equal(snapshot.bars.length, 100000); assert.equal(portfolio.curve.length, 100000);
  report.price_source_sha256 = sha(JSON.stringify(snapshot)); report.portfolio_sha256 = sha(JSON.stringify(portfolio));
  assert.equal(sha(JSON.stringify(portfolio.curve)), dataset.portfolio.curve_sha256);
  browser = await chromium.launch({ headless: true, timeout: 20000,
    args: ['--disable-background-networking', '--disable-background-timer-throttling', '--disable-renderer-backgrounding'] });
  report.chromium = browser.version();
  for (const mode of ['native', 'fallback']) {
    const viewport = mode === 'native' ? { width: 3440, height: 1440 } : { width: 390, height: 844 };
    const context = await browser.newContext({ viewport, locale: 'es-ES', timezoneId: 'Europe/Madrid', serviceWorkers: 'block' });
    await context.route('**/*', async (route) => {
      const request = route.request(), url = new URL(request.url());
      if (url.origin !== BASE || request.method() !== 'GET' || /^\/api\/(feeds|experiments|research)/.test(url.pathname)) {
        report.network_violations.push(`${request.method()} ${url.origin}${url.pathname}`); await route.abort();
      } else await route.continue();
    });
    await context.routeWebSocket('**/*', async (socket) => { report.network_violations.push('Unexpected WebSocket'); await socket.close(); });
    if (mode === 'fallback') await context.addInitScript(() => {
      Element.prototype.requestFullscreen = () => Promise.reject(new DOMException('Benchmark fallback', 'NotAllowedError'));
    });
    const page = await context.newPage(); page.setDefaultTimeout(20000); page.setDefaultNavigationTimeout(25000);
    page.on('pageerror', (error) => report.page_errors.push(error.message));
    page.on('response', (response) => { if (response.status() >= 400) report.http_errors.push({ status: response.status(), url: response.url() }); });
    page.on('requestfailed', (request) => report.request_failures.push({ url: request.url(), error: request.failure()?.errorText }));
    page.on('requestfinished', (request) => {
      if (new URL(request.url()).pathname === '/api/state' && request.method() === 'GET')
        report.state_gets.push({ mode, timing: request.timing() });
    });
    const session = await context.newCDPSession(page);
    for (const kind of ['prices', 'curve']) {
      checkRun(); const item = { kind, mode, viewport_css: viewport }; report.results.push(item);
      await page.goto(`${BASE}/?tab=${kind === 'prices' ? 'data' : 'portfolio'}&dataset=${dataset.dataset_id}`, { waitUntil: 'domcontentloaded' });
      const plot = page.locator(kind === 'prices' ? '.prices-panel .price-chart-svg' : '.portfolio-curve figure.chart .chart-viewport svg');
      await plot.waitFor({ state: 'visible' }); await plot.scrollIntoViewIfNeeded(); await page.evaluate(frames);
      await installProbe(page, kind);
      if (kind === 'prices') {
        for (let turn = 0; (await state(page)).count < 1000 && turn < 8; turn++) {
          await page.getByRole('button', { name: 'Alejar precios', exact: true }).click(); await page.evaluate(frames);
        }
        assert.equal((await state(page)).count, 1000);
      } else {
        assert.equal((await state(page)).count, 100000);
        await page.getByRole('button', { name: 'Acercar curva', exact: true }).click(); await page.evaluate(frames);
      }
      item.normal_navigation = await domBatch(page, 'navigation'); item.normal_zoom = await domBatch(page, 'zoom');
      await plot.scrollIntoViewIfNeeded(); await page.evaluate(frames);
      item.normal_hover = {}; await hoverBatch(page, kind, snapshot, portfolio, item.normal_hover);
      item.normal_layout = await layout(page, false, mode);
      await page.screenshot({ path: path.join(artifactDir, `${kind}-${mode}-normal.png`) });
      const normalBeforeWheel = await state(page), point = await page.evaluate(() => window.atlasNavigationProbe.point());
      await page.mouse.move(point.x, point.y); await page.mouse.wheel(0, 100); await page.evaluate(frames);
      assert.deepEqual(await state(page), normalBeforeWheel); item.normal_wheel_preserves_range = true;
      await toggle(page, true, mode); item.fullscreen_layout = await layout(page, true, mode);
      item.fullscreen_navigation = await domBatch(page, 'navigation'); item.fullscreen_zoom = await domBatch(page, 'zoom');
      item.fullscreen_gestures = await gestures(page, kind, snapshot, portfolio);
      item.fullscreen_hover = {}; await hoverBatch(page, kind, snapshot, portfolio, item.fullscreen_hover);
      await page.screenshot({ path: path.join(artifactDir, `${kind}-${mode}-fullscreen.png`) });
      await toggle(page, false, mode);
      // Warm native fullscreen resources and event paths, then compare the same closed view.
      for (let i = 0; i < 2; i++) { await toggle(page, true, mode); await toggle(page, false, mode); }
      item.cycles_memory = [{ cycle: 0, ...(await memory(page, session, mode)) }];
      const opening = [], closing = [];
      for (let cycle = 1; cycle <= 20; cycle++) {
        opening.push(await toggle(page, true, mode)); closing.push(await toggle(page, false, mode));
        if ([5, 10, 20].includes(cycle)) item.cycles_memory.push({ cycle, ...(await memory(page, session, mode)) });
      }
      item.fullscreen_open = summarize(opening); item.fullscreen_close = summarize(closing);
      const first = item.cycles_memory[0], last = item.cycles_memory.at(-1);
      assert.deepEqual(last.view, first.view);
      item.post_warmup_memory_delta = { heap_used_bytes: last.heap_used_bytes - first.heap_used_bytes,
        nodes: last.nodes - first.nodes, listeners: last.jsEventListeners - first.jsEventListeners,
        identical_closed_view: true, sustained_trial: false };
    }
    await context.close();
  }
  assert.equal(sha(JSON.stringify(await api(resource))), report.price_source_sha256);
  assert.equal(sha(JSON.stringify(await api(portfolioResource))), report.portfolio_sha256);
  const finalDataset = (await api('/api/state')).datasets.find((item) => item.id === dataset.dataset_id);
  assert.equal(finalDataset.version, dataset.dataset_version); assert.equal(finalDataset.manifest.sha256, dataset.manifest_hash);
  report.source_snapshot_unchanged = true;
  assert.equal(sha(fs.readFileSync(previousPath)), report.original_benchmark_sha256); report.original_report_unchanged = true;
  assert.deepEqual(report.network_violations, []); assert.deepEqual(report.page_errors, []); assert.deepEqual(report.http_errors, []);
  checkRun(); report.success = true;
})().catch((error) => { report.error = error.stack ?? String(error); process.exitCode = 1; })
  .finally(async () => {
    clearTimeout(deadline); abort.abort(); await browser?.close(); report.elapsed_ms = performance.now() - began;
    fs.writeFileSync(out, JSON.stringify(report, null, 2), { flag: 'wx' });
    console.log(JSON.stringify({ report: out, success: report.success, error: report.error, elapsed_ms: report.elapsed_ms,
      results: report.results.map((item) => ({ kind: item.kind, mode: item.mode,
        navigation_p95_ms: item.fullscreen_navigation?.p95_ms, hover_p95_ms: item.fullscreen_hover?.p95_ms,
        drag_update_p95_ms: item.fullscreen_gestures?.drag_update.p95_ms,
        drag_gesture_total_p95_ms: item.fullscreen_gestures?.drag_gesture_total.p95_ms, wheel_p95_ms: item.fullscreen_gestures?.wheel.p95_ms,
        open_p95_ms: item.fullscreen_open?.p95_ms, memory_delta: item.post_warmup_memory_delta })) }, null, 2));
  });
