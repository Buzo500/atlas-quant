import type {
  DatasetPricesResponse,
  ExperimentResponse,
  LedgerResponse,
  PortfolioResponse,
  ResearchResponse,
  StateResponse,
} from '../lib/api-types';
import type { Locator, Page } from '@playwright/test';
import {
  test,
  expect,
  ensureDemo,
  expectVisibleFocus,
  readApi,
  select,
  tab,
} from './fixtures';

async function expectFloatingReading(page: Page) {
  const tooltip = page.getByRole('tooltip');
  await expect(tooltip).toBeVisible();
  await expect
    .poll(() =>
      tooltip.evaluate((element) => {
        const box = element.getBoundingClientRect();
        return (
          box.left >= 7 &&
          box.top >= 7 &&
          box.right <= innerWidth - 7 &&
          box.bottom <= innerHeight - 7
        );
      }),
    )
    .toBe(true);
  expect(
    await tooltip.evaluate(
      (element) => getComputedStyle(element).pointerEvents,
    ),
  ).toBe('none');
  return tooltip;
}

async function hoverFinalCurvePoint(page: Page, plot: Locator) {
  await plot.scrollIntoViewIfNeeded();
  const anchor = await plot.evaluate((element) => {
    const line = element.querySelector('polyline')!;
    const point = line.points.getItem(line.points.numberOfItems - 1);
    const mapped = new DOMPoint(point.x, point.y).matrixTransform(
      (element as SVGSVGElement).getScreenCTM()!,
    );
    return { x: mapped.x, y: mapped.y };
  });
  await page.mouse.move(anchor.x, anchor.y);
  return expectFloatingReading(page);
}

async function hoverCandle(page: Page, plot: Locator, edge: 'first' | 'last') {
  await plot.scrollIntoViewIfNeeded();
  const anchor = await plot.evaluate((element, chosen) => {
    const candles = element.querySelectorAll('.price-rise, .price-fall');
    const index = chosen === 'first' ? 0 : candles.length - 1;
    const wick = candles[index].querySelector('line')!;
    const mapped = new DOMPoint(
      wick.x1.baseVal.value,
      (wick.y1.baseVal.value + wick.y2.baseVal.value) / 2,
    ).matrixTransform((element as SVGSVGElement).getScreenCTM()!);
    return { x: mapped.x, y: mapped.y, index };
  }, edge);
  await page.mouse.move(anchor.x, anchor.y);
  return { tooltip: await expectFloatingReading(page), index: anchor.index };
}

test('cartera vacía, foco entre secciones, teclado y demostración real', async ({
  page,
}) => {
  await page.goto('/');
  await expect(
    page.getByText('Motor conectado', { exact: true }),
  ).toBeVisible();
  const state = await readApi<StateResponse>(page, '/api/state');
  expect(state.datasets).toHaveLength(0);
  await page
    .getByRole('button', { name: 'Importar datos', exact: true })
    .click();
  await expect(
    page.getByRole('tab', { name: 'Datos', exact: true }),
  ).toHaveAttribute('aria-selected', 'true');
  await expectVisibleFocus(page);
  await page.keyboard.press('Tab');
  await expectVisibleFocus(page);
  const portfolioTab = page.getByRole('tab', { name: 'Cartera', exact: true });
  await portfolioTab.focus();
  await page.keyboard.press('ArrowRight');
  await expect(
    page.getByRole('tab', { name: 'Laboratorio', exact: true }),
  ).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(
    page.getByRole('heading', { name: 'Comparar estrategias', exact: true }),
  ).toBeVisible();
  const dataset = await ensureDemo(page);
  const portfolio = await readApi<PortfolioResponse>(
    page,
    `/api/datasets/${dataset.id}/portfolio`,
  );
  expect(portfolio.positions).toHaveLength(3);
  expect(portfolio.nav).toBeGreaterThan(0);
  const positions = page.locator('.positions-panel');
  await expect(positions.getByRole('row')).toHaveCount(4);
  for (const position of portfolio.positions)
    await expect(
      positions.getByText(position.symbol, { exact: true }),
    ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Evolución del patrimonio' }),
  ).toBeVisible();
});

test('movimientos: revisar, invalidar al editar, confirmar y conservar tras recargar', async ({
  page,
}) => {
  const dataset = await ensureDemo(page);
  const before = await readApi<PortfolioResponse>(
    page,
    `/api/datasets/${dataset.id}/portfolio`,
  );
  await tab(page, 'Datos');
  await select(page, 'Tipo de archivo', 'Movimientos de cartera');
  const id = 'e2e-deposit';
  const csv = (amount: number) =>
    `id,date,kind,symbol,quantity,price,amount,fee,currency\n${id},${dataset.manifest.date_max},deposit,,,,${amount},,EUR\n`;
  const input = page.getByRole('textbox', {
    name: 'Contenido CSV',
    exact: true,
  });
  await input.fill(csv(100));
  const previews: LedgerResponse[] = [];
  const preview = async () => {
    const response = page.waitForResponse((reply) =>
      reply.url().endsWith(`/datasets/${dataset.id}/ledger`),
    );
    await page
      .getByRole('button', { name: 'Previsualizar movimientos', exact: true })
      .click();
    const reply = await response;
    expect(reply.ok()).toBe(true);
    const body: LedgerResponse = await reply.json();
    expect(body.committed).toBe(false);
    previews.push(body);
    await expect(
      page.getByRole('button', { name: 'Confirmar importación', exact: true }),
    ).toBeVisible();
    return body;
  };
  expect((await preview()).added).toBe(1);
  await input.fill(csv(150));
  await expect(
    page.getByRole('button', { name: 'Confirmar importación', exact: true }),
  ).toHaveCount(0);
  const revised = await preview();
  expect(revised.preview_token).not.toBe(previews[0].preview_token);
  expect(revised.portfolio.nav).toBeCloseTo(before.nav + 150, 6);
  const committed = page.waitForResponse(
    (reply) =>
      reply.url().endsWith(`/datasets/${dataset.id}/ledger`) &&
      reply.request().postDataJSON()?.commit === true,
  );
  await page
    .getByRole('button', { name: 'Confirmar importación', exact: true })
    .click();
  const confirmation = await committed;
  expect(confirmation.ok()).toBe(true);
  expect(confirmation.request().postDataJSON()).toMatchObject({
    csv: csv(150),
    commit: true,
    preview_token: revised.preview_token,
  });
  expect(await confirmation.json()).toMatchObject({
    added: 1,
    duplicates: 0,
    committed: true,
  });
  await expect(
    page.getByText('1 movimientos añadidos; 0 duplicados omitidos.', {
      exact: true,
    }),
  ).toBeVisible();
  await expectVisibleFocus(page);
  await page.reload();
  await expect(
    page.getByRole('heading', { name: 'Importar CSV' }),
  ).toBeVisible();
  await select(page, 'Tipo de archivo', 'Movimientos de cartera');
  await page
    .getByRole('textbox', { name: 'Contenido CSV', exact: true })
    .fill(csv(150));
  expect(await preview()).toMatchObject({ added: 0, duplicates: 1 });
  const after = await readApi<PortfolioResponse>(
    page,
    `/api/datasets/${dataset.id}/portfolio`,
  );
  expect(after.nav).toBeCloseTo(before.nav + 150, 6);
  expect(after.cash).toBeCloseTo(before.cash + 150, 6);
});

test('laboratorio real: identidad inmutable, costes y borrador entre pestañas', async ({
  page,
}) => {
  const dataset = await ensureDemo(page);
  await tab(page, 'Laboratorio');
  await select(page, 'Activo', 'DEMO_WORLD');
  const response = page.waitForResponse(
    (reply) =>
      reply.url().endsWith('/api/research') &&
      reply.request().method() === 'POST',
  );
  await page
    .getByRole('button', { name: 'Ejecutar comparación', exact: true })
    .click();
  const reply = await response;
  expect(reply.ok()).toBe(true);
  const result: ResearchResponse = await reply.json();
  expect(result.execution).toMatchObject({
    dataset_id: dataset.id,
    dataset_name: dataset.name,
    dataset_version: dataset.version,
    dataset_manifest_hash: dataset.manifest.sha256,
    symbol: 'DEMO_WORLD',
    costs: { commission_bps: 5 },
  });
  expect(result.out_of_sample.metrics.observations).toBeGreaterThan(0);
  const backtestCurve = page
    .locator('figure.chart')
    .filter({
      has: page.locator('svg[tabindex="0"]'),
    })
    .last();
  const backtestPlot = backtestCurve.locator('svg[tabindex="0"]');
  await expect(
    backtestCurve.getByRole('slider', {
      name: 'Observación de la curva',
      exact: true,
    }),
  ).toHaveCount(0);
  await backtestPlot.focus();
  await page.keyboard.press('End');
  const finalBacktest = result.out_of_sample.curve.at(-1)!;
  const backtestDetail = backtestCurve.getByLabel('Detalle de la observación', {
    exact: true,
  });
  await expect(backtestDetail.locator('time')).toHaveAttribute(
    'datetime',
    finalBacktest.date,
  );
  await expect(backtestDetail.locator('data').nth(0)).toHaveAttribute(
    'value',
    String(finalBacktest.equity),
  );
  await expect(backtestDetail.locator('data').nth(1)).toHaveAttribute(
    'value',
    String(finalBacktest.benchmark),
  );
  const backtestTooltip = await hoverFinalCurvePoint(page, backtestPlot);
  await expect(backtestTooltip.locator('time')).toHaveAttribute(
    'datetime',
    finalBacktest.date,
  );
  await expect(backtestTooltip.locator('data').nth(0)).toHaveAttribute(
    'value',
    String(finalBacktest.equity),
  );
  await expect(backtestTooltip.locator('data').nth(1)).toHaveAttribute(
    'value',
    String(finalBacktest.benchmark),
  );
  await backtestCurve
    .getByRole('button', { name: 'Acercar curva', exact: true })
    .click();
  await backtestCurve
    .getByRole('combobox', { name: 'Representación de la curva', exact: true })
    .selectOption('area');
  await expect(backtestDetail.locator('data').nth(0)).toHaveAttribute(
    'value',
    String(finalBacktest.equity),
  );
  await backtestCurve
    .getByRole('button', { name: 'Restablecer curva', exact: true })
    .click();
  const context = page.getByRole('region', {
    name: 'Contexto de la ejecución',
  });
  await expect(
    context.getByRole('heading', {
      name: `DEMO_WORLD · ${dataset.name}`,
      exact: true,
    }),
  ).toBeVisible();
  await context
    .getByText('Parámetros y trazabilidad de la ejecución', { exact: true })
    .click();
  await expect(
    context.getByText(result.execution.id, { exact: true }),
  ).toBeVisible();
  await expect(
    context.getByText(dataset.manifest.sha256, { exact: true }),
  ).toBeVisible();
  await page
    .getByRole('spinbutton', { name: 'Comisión (pb)', exact: true })
    .fill('9');
  await expect(
    page.getByText('Resultado de otra configuración', { exact: true }),
  ).toBeVisible();
  await expect(
    context.getByText('5 pb', { exact: true }).first(),
  ).toBeVisible();
  await select(page, 'Activo', 'DEMO_BOND');
  await expect(
    context.getByRole('heading', {
      name: `DEMO_WORLD · ${dataset.name}`,
      exact: true,
    }),
  ).toBeVisible();
  await tab(page, 'Datos');
  await page
    .getByRole('textbox', { name: 'Contenido CSV', exact: true })
    .fill('borrador sin enviar');
  await tab(page, 'Laboratorio');
  await expect(
    page.getByRole('spinbutton', { name: 'Comisión (pb)', exact: true }),
  ).toHaveValue('9');
  await expect(
    context.getByText(result.execution.id, { exact: true }),
  ).toBeVisible();
  await tab(page, 'Datos');
  await expect(
    page.getByRole('textbox', { name: 'Contenido CSV', exact: true }),
  ).toHaveValue('borrador sin enviar');
});

test('experimento breve sin IA: crear, pausar, reanudar, cancelar y recuperar selección', async ({
  page,
}) => {
  const dataset = await ensureDemo(page);
  await tab(page, 'Agente IA');
  if (
    await page
      .getByRole('button', { name: 'Nuevo experimento', exact: true })
      .isVisible()
  )
    await page
      .getByRole('button', { name: 'Nuevo experimento', exact: true })
      .click();
  await page
    .getByRole('textbox', { name: 'Hipótesis de investigación', exact: true })
    .fill('Recorrido E2E sintético sin IA ni órdenes reales.');
  await page.getByRole('spinbutton', { name: /^Duración \(horas\)/ }).fill('1');
  await expect(
    page.getByRole('combobox', { name: 'Proveedor de IA', exact: true }),
  ).toContainText('Catálogo fijo · sin IA');
  await expect(
    page.getByRole('switch', { name: /Activar simulación automáticamente/ }),
  ).toHaveAttribute('aria-checked', 'false');
  const creation = page.waitForResponse(
    (reply) =>
      reply.url().endsWith('/api/experiments') &&
      reply.request().method() === 'POST',
  );
  await page
    .getByRole('button', { name: 'Iniciar experimento', exact: true })
    .click();
  const reply = await creation;
  expect(reply.ok()).toBe(true);
  const created: ExperimentResponse = await reply.json();
  expect(reply.request().postDataJSON()).toMatchObject({
    dataset_id: dataset.id,
    provider: 'none',
    budget_usd: 0,
    hours: 1,
    auto_paper: false,
  });
  try {
    await expect(
      page.getByRole('button', { name: 'Nuevo experimento', exact: true }),
    ).toBeVisible();
    await expectVisibleFocus(page);
    const control = async (button: string, action: string) => {
      const response = page.waitForResponse(
        (item) =>
          item.url().endsWith(`/experiments/${created.id}/control`) &&
          item.request().postDataJSON()?.action === action,
      );
      await page.getByRole('button', { name: button, exact: true }).click();
      expect((await response).ok()).toBe(true);
    };
    await control('Pausar', 'pause');
    await expect(
      page.getByRole('heading', {
        name: `${created.symbol} · Pausado`,
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Reanudar', exact: true }),
    ).toBeEnabled();
    await control('Reanudar', 'resume');
    await expect
      .poll(
        async () =>
          (
            await readApi<ExperimentResponse>(
              page,
              `/api/experiments/${created.id}`,
            )
          ).status,
      )
      .toMatch(/^(queued|running|observing|eligible_paper)$/);
    await expect(
      page.getByRole('button', { name: 'Pausar', exact: true }),
    ).toBeEnabled();
    await control('Cancelar experimento', 'cancel');
    await expect(
      page.getByRole('heading', {
        name: `${created.symbol} · Cancelado`,
        exact: true,
      }),
    ).toBeVisible();
    expect(new URL(page.url()).searchParams.get('experiment')).toBe(created.id);
    await page.reload();
    await expect(
      page.getByRole('heading', {
        name: `${created.symbol} · Cancelado`,
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole('combobox', { name: 'Conjunto de datos', exact: true }),
    ).toContainText(dataset.name);
    const job = await readApi<ExperimentResponse>(
      page,
      `/api/experiments/${created.id}`,
    );
    expect(job).toMatchObject({
      status: 'cancelled',
      provider: 'none',
      spent_usd: 0,
      reserved_usd: 0,
      auto_paper: false,
      paper_account: null,
    });
    await page
      .getByRole('button', { name: 'Nuevo experimento', exact: true })
      .click();
    await expect(
      page.getByRole('switch', { name: /Activar simulación automáticamente/ }),
    ).toHaveAttribute('aria-checked', 'false');
  } finally {
    // Failure cleanup uses the real local API; it is not part of the UI assertions.
    const current = await readApi<ExperimentResponse>(
      page,
      `/api/experiments/${created.id}`,
    );
    if (current.status !== 'cancelled') {
      const stopped = await page.request.post(
        `/api/experiments/${created.id}/control`,
        {
          headers: {
            'X-Atlas-Client': 'local-v1',
            Origin: 'http://127.0.0.1:3000',
          },
          data: { action: 'cancel' },
        },
      );
      expect(stopped.ok()).toBe(true);
    }
  }
});

test('interrupción de conexión y reintento contra la misma cartera real', async ({
  page,
  context,
}) => {
  const dataset = await ensureDemo(page);
  // Reload into Lab so this mount has never loaded the portfolio query.
  await page.goto(`/?tab=lab&dataset=${dataset.id}`);
  await expect(
    page.getByText('Motor conectado', { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Comparar estrategias', exact: true }),
  ).toBeVisible();
  await context.setOffline(true);
  try {
    await tab(page, 'Cartera');
    await expect(
      page.getByRole('heading', {
        name: 'No se pudo consultar la cartera',
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', {
        name: 'Importa tus movimientos',
        exact: true,
      }),
    ).toHaveCount(0);
  } finally {
    await context.setOffline(false);
  }
  const retry = page.waitForResponse((reply) =>
    reply.url().endsWith(`/datasets/${dataset.id}/portfolio`),
  );
  await page
    .getByRole('button', { name: 'Reintentar cartera', exact: true })
    .click();
  expect((await retry).ok()).toBe(true);
  await expect(
    page.getByRole('heading', {
      name: 'Evolución del patrimonio',
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Reintentar cartera', exact: true }),
  ).toHaveCount(0);
});

test('curva real: valores originales, TWR, rango inclusivo y controles adaptables', async ({
  page,
}, testInfo) => {
  const dataset = await ensureDemo(page);
  const portfolio = await readApi<PortfolioResponse>(
    page,
    `/api/datasets/${dataset.id}/portfolio`,
  );
  const curve = page.locator('figure.chart').first();
  const plot = curve.locator('svg[tabindex="0"]');
  await expect(
    curve.getByRole('slider', { name: 'Observación de la curva', exact: true }),
  ).toHaveCount(0);
  const detail = curve.getByLabel('Detalle de la observación', { exact: true });
  const stats = await page.locator('.stats').first().innerText();
  const first = portfolio.curve[0],
    last = portfolio.curve.at(-1)!;
  await plot.focus();
  await page.keyboard.press('Home');
  await expect(detail.locator('time')).toHaveAttribute('datetime', first.date);
  await expect(detail.locator('data').first()).toHaveAttribute(
    'value',
    String(first.nav),
  );
  await page.keyboard.press('End');
  await expect(detail.locator('time')).toHaveAttribute('datetime', last.date);
  await expect(detail.locator('data').first()).toHaveAttribute(
    'value',
    String(last.nav),
  );
  await curve
    .getByRole('combobox', { name: 'Serie de la curva', exact: true })
    .selectOption('twr');
  await expect(detail.locator('data').nth(1)).toHaveText(
    new Intl.NumberFormat('es-ES', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(last.twr_index - 1),
  );
  await curve
    .getByRole('combobox', { name: 'Representación de la curva', exact: true })
    .selectOption('area');
  const from = portfolio.curve.at(-12)!,
    to = portfolio.curve.at(-3)!;
  await curve.getByLabel('Inicio de la curva', { exact: true }).fill(from.date);
  await curve.getByLabel('Fin de la curva', { exact: true }).fill(to.date);
  await curve
    .getByRole('button', { name: 'Aplicar rango', exact: true })
    .click();
  await plot.focus();
  await page.keyboard.press('Home');
  await expect(detail.locator('time')).toHaveAttribute('datetime', from.date);
  await expect(detail.locator('data').nth(1)).toHaveAttribute(
    'value',
    String(from.twr_index),
  );
  await page.keyboard.press('End');
  await expect(detail.locator('time')).toHaveAttribute('datetime', to.date);
  await curve
    .getByRole('button', { name: 'Acercar curva', exact: true })
    .click();
  await expect(plot).toBeVisible();
  await curve
    .getByRole('button', { name: 'Restablecer curva', exact: true })
    .click();
  await plot.focus();
  await page.keyboard.press('Home');
  await expect(detail.locator('time')).toHaveAttribute('datetime', first.date);
  expect(await page.locator('.stats').first().innerText()).toBe(stats);
  for (const [width, height] of [
    [3440, 1440],
    [1920, 1080],
    [1366, 768],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth + 1,
        ),
      )
      .toBe(true);
    await curve.scrollIntoViewIfNeeded();
    await expect(
      curve.getByRole('button', { name: 'Restablecer curva', exact: true }),
    ).toBeVisible();
    await plot.focus();
    await page.keyboard.press('End');
    await expect(detail.locator('time')).toHaveAttribute('datetime', last.date);
    const tooltip = await hoverFinalCurvePoint(page, plot);
    await expect(tooltip.locator('time')).toHaveAttribute(
      'datetime',
      last.date,
    );
    await expect(tooltip.locator('data').first()).toHaveAttribute(
      'value',
      String(last.nav),
    );
    await expect(tooltip.locator('data').nth(1)).toHaveAttribute(
      'value',
      String(last.twr_index),
    );
    await page.screenshot({
      path: testInfo.outputPath(`curva-${width}.png`),
      fullPage: true,
    });
    await page.keyboard.press('Escape');
    await expect(page.getByRole('tooltip')).toHaveCount(0);
  }
  expect(
    await readApi<PortfolioResponse>(
      page,
      `/api/datasets/${dataset.id}/portfolio`,
    ),
  ).toEqual(portfolio);
});

test('precios reales: OHLCV, agregación del rango, estilos, teclado y pantallas', async ({
  page,
}, testInfo) => {
  const dataset = await ensureDemo(page);
  const symbol = 'DEMO_WORLD';
  const path = `/api/datasets/${dataset.id}/prices?version=${dataset.version}&symbol=${symbol}`;
  const source = await readApi<DatasetPricesResponse>(page, path);
  expect(source.manifest_hash).toBe(dataset.manifest.sha256);
  await tab(page, 'Datos');
  await expect(
    page.getByRole('heading', { name: 'Precios del activo', exact: true }),
  ).toBeVisible();
  await select(page, 'Activo del gráfico', symbol);
  const plot = page.locator('.price-chart-svg');
  await expect(
    page.getByRole('slider', { name: 'Inspeccionar barra', exact: true }),
  ).toHaveCount(0);
  const detail = page.getByRole('region', {
    name: 'Lectura de precios',
    exact: true,
  });
  const numeric = (value: number) =>
    new Intl.NumberFormat('es-ES', { maximumFractionDigits: 20 }).format(value);
  const field = (name: string) =>
    detail.locator(`[data-price-field="${name}"]`);
  await plot.focus();
  await page.keyboard.press('End');
  const last = source.bars.at(-1)!;
  for (const name of ['open', 'high', 'low', 'close'] as const)
    await expect(field(name)).toHaveText(`${numeric(last[name])} EUR`);
  await expect(field('volume')).toHaveText(numeric(last.volume));
  for (const label of ['Línea', 'Área', 'Barras OHLC', 'Velas']) {
    await select(page, 'Representación de precios', label);
    await expect(field('close')).toHaveText(`${numeric(last.close)} EUR`);
  }
  // Choose two actual daily observations inside one civil month. Compute the
  // expected aggregate independently from the backend response, not UI helpers.
  const pairIndex = source.bars.findIndex(
    (bar, index) =>
      index > 0 &&
      bar.date.slice(0, 7) === source.bars[index - 1].date.slice(0, 7),
  );
  expect(pairIndex).toBeGreaterThan(0);
  const pair = source.bars.slice(pairIndex - 1, pairIndex + 1);
  await page.getByLabel('Precios desde', { exact: true }).fill(pair[0].date);
  await page.getByLabel('Precios hasta', { exact: true }).fill(pair[1].date);
  await page
    .getByRole('button', { name: 'Aplicar fechas', exact: true })
    .click();
  await select(page, 'Intervalo del gráfico', 'Mensual');
  await expect(field('open')).toHaveText(`${numeric(pair[0].open)} EUR`);
  await expect(field('high')).toHaveText(
    `${numeric(Math.max(...pair.map((bar) => bar.high)))} EUR`,
  );
  await expect(field('low')).toHaveText(
    `${numeric(Math.min(...pair.map((bar) => bar.low)))} EUR`,
  );
  await expect(field('close')).toHaveText(`${numeric(pair[1].close)} EUR`);
  await expect(field('volume')).toHaveText(
    numeric(pair[0].volume + pair[1].volume),
  );
  await expect(detail.getByText(/Periodo civil recortado/)).toBeVisible();
  await page.getByText('Datos diarios originales', { exact: true }).click();
  const original = page.getByRole('table', {
    name: `Precios diarios originales · ${symbol}`,
    exact: true,
  });
  await expect(original.getByRole('row')).toHaveCount(3);
  await expect(original.getByRole('cell').nth(0)).toHaveText(
    numeric(pair[0].open),
  );
  await page
    .getByRole('button', { name: 'Restablecer vista', exact: true })
    .click();
  await select(page, 'Intervalo del gráfico', 'Diario');
  await page
    .getByRole('slider', { name: 'Desplazar precios', exact: true })
    .focus();
  await page.keyboard.press('Home');
  await plot.focus();
  await page.keyboard.press('Home');
  await expect(field('close')).toHaveText(
    `${numeric(source.bars[0].close)} EUR`,
  );
  await expect(field('change')).toHaveText('—');
  for (const [width, height] of [
    [3440, 1440],
    [1920, 1080],
    [1366, 768],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth + 1,
        ),
      )
      .toBe(true);
    await page.locator('.price-chart-svg').scrollIntoViewIfNeeded();
    await plot.focus();
    await page.keyboard.press('Home');
    await expect(field('close')).toHaveText(
      `${numeric(source.bars[0].close)} EUR`,
    );
    for (const edge of ['first', 'last'] as const) {
      const { tooltip, index } = await hoverCandle(page, plot, edge);
      const observation = source.bars[index];
      await expect(tooltip.locator('time').first()).toHaveAttribute(
        'datetime',
        observation.date,
      );
      for (const name of ['open', 'high', 'low', 'close'] as const)
        await expect(
          tooltip.locator(`[data-price-field="${name}"] data`),
        ).toHaveAttribute('value', String(observation[name]));
      await expect(
        tooltip.locator('[data-price-field="volume"] data'),
      ).toHaveAttribute('value', String(observation.volume));
    }
    await page.screenshot({
      path: testInfo.outputPath(`precios-${width}.png`),
      fullPage: true,
    });
    await page.mouse.move(0, 0);
    await expect(page.getByRole('tooltip')).toHaveCount(0);
  }
  await select(page, 'Activo del gráfico', 'DEMO_BOND');
  await expect(page.getByRole('tooltip')).toHaveCount(0);
  const bond = await readApi<DatasetPricesResponse>(
    page,
    `/api/datasets/${dataset.id}/prices?version=${dataset.version}&symbol=DEMO_BOND`,
  );
  await plot.focus();
  await page.keyboard.press('End');
  await expect(field('close')).toHaveText(
    `${numeric(bond.bars.at(-1)!.close)} EUR`,
  );
  expect(await readApi<DatasetPricesResponse>(page, path)).toEqual(source);
});

test('curva estrecha: la primera lectura sobrevive al ajuste de altura', async ({
  page,
}, testInfo) => {
  await page.addInitScript(() => {
    Element.prototype.requestFullscreen = () =>
      Promise.reject(new DOMException('Exercise window fallback', 'NotAllowedError'));
  });
  const dataset = await ensureDemo(page);
  const source = await readApi<PortfolioResponse>(
    page,
    `/api/datasets/${dataset.id}/portfolio`,
  );
  const last = source.curve.at(-1)!;
  for (const input of ['pointer', 'keyboard'] as const) {
    await page.setViewportSize({ width: 390, height: 844 });
    // A fresh mount has no selected observation, so the first reading changes
    // the height of the details below the flex-sized fullscreen plot.
    await page.goto(`/?tab=portfolio&dataset=${dataset.id}`);
    const curve = page.locator('.portfolio-curve');
    const plot = curve.locator('.chart-viewport svg');
    await expect(plot).toBeVisible();
    await expect(curve.locator('.curve-point-detail data')).toHaveCount(0);
    await curve.getByRole('button', { name: /^Pantalla completa:/ }).click();
    await expect(curve.locator('.chart-workspace')).toHaveClass(/is-expanded/);
    if (input === 'pointer') await hoverFinalCurvePoint(page, plot);
    else {
      await plot.focus();
      await page.keyboard.press('End');
    }
    await page.evaluate(
      () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
    );
    const tooltip = await expectFloatingReading(page);
    await expect(tooltip.locator('time')).toHaveAttribute('datetime', last.date);
    await expect(tooltip.locator('data').first()).toHaveAttribute('value', String(last.nav));
    await page.screenshot({ path: testInfo.outputPath(`first-reading-${input}.png`) });
    // A real browser resize still dismisses the floating reading, while the
    // selected original observation remains available in the fixed details.
    await page.setViewportSize({ width: 420, height: 844 });
    await expect(page.getByRole('tooltip')).toHaveCount(0);
    await expect(curve.locator('.curve-point-detail time')).toHaveAttribute('datetime', last.date);
    await page.keyboard.press('Escape');
    await expect(curve.getByRole('button', { name: /^Pantalla completa:/ })).toBeFocused();
  }
  expect(await readApi<PortfolioResponse>(page, `/api/datasets/${dataset.id}/portfolio`)).toEqual(source);
});

for (const mode of ['native', 'fallback'] as const) {
  test(`navegación gráfica: barra, lupas, pantalla completa ${mode}, arrastre y rueda`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize(
      mode === 'native'
        ? { width: 3440, height: 1440 }
        : { width: 390, height: 844 },
    );
    if (mode === 'fallback') {
      // Exercise a browser permission denial; all data still uses the real API.
      await page.addInitScript(() => {
        Element.prototype.requestFullscreen = () =>
          Promise.reject(
            new DOMException(
              'Fullscreen unavailable for this test',
              'NotAllowedError',
            ),
          );
      });
    }
    const dataset = await ensureDemo(page);
    const before = await readApi<PortfolioResponse>(
      page,
      `/api/datasets/${dataset.id}/portfolio`,
    );
    for (const kind of ['curve', 'prices'] as const) {
      if (kind === 'prices') await tab(page, 'Datos');
      const owner =
        kind === 'curve'
          ? page.locator('figure.chart').first()
          : page.locator('.prices-panel');
      const workspace = owner.locator('.chart-workspace');
      const plot = owner.locator(
        kind === 'curve' ? '.chart-viewport svg' : '.price-chart-svg',
      );
      const noun = kind === 'curve' ? 'curva' : 'precios';
      const navigator = owner.getByRole('slider', {
        name: `Desplazar ${noun}`,
        exact: true,
      });
      const start = async () =>
        navigator.evaluate(
          (element) => (element as HTMLInputElement).valueAsNumber,
        );
      const count = async () =>
        kind === 'curve'
          ? Number(
              (await owner.locator('.chart-period').innerText()).replace(
                /\D/g,
                '',
              ),
            )
          : owner.locator('.price-rise, .price-fall').count();
      await expect(
        owner.getByRole('button', { name: /Desplazar .* (atrás|adelante)/ }),
      ).toHaveCount(0);
      const zoomIn = owner.getByRole('button', {
        name: `Acercar ${noun}`,
        exact: true,
      });
      await expect(zoomIn.locator('svg')).toHaveCount(1);
      const initialCount = await count();
      await zoomIn.click();
      await expect.poll(count).toBeLessThan(initialCount);
      const zoomedCount = await count();
      await navigator.focus();
      await page.keyboard.press('Home');
      await expect.poll(start).toBe(0);
      await page.keyboard.press('End');
      await expect.poll(start).toBeGreaterThan(0);
      expect(await count()).toBe(zoomedCount);

      // Outside fullscreen, scrolling over the plot must not change its range.
      await plot.scrollIntoViewIfNeeded();
      let box = (await plot.boundingBox())!;
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.wheel(0, 100);
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve)),
          ),
      );
      expect(await count()).toBe(zoomedCount);

      const open = owner.getByRole('button', { name: /^Pantalla completa:/ });
      await open.click();
      await expect(workspace).toHaveClass(/is-expanded/);
      await expect(
        owner.getByRole('button', {
          name: 'Salir de pantalla completa',
          exact: true,
        }),
      ).toBeVisible();
      await expect
        .poll(() =>
          workspace.evaluate((element) => {
            const rect = element.getBoundingClientRect();
            return (
              Math.abs(rect.width - innerWidth) < 2 &&
              Math.abs(rect.height - innerHeight) < 2
            );
          }),
        )
        .toBe(true);
      await expect
        .poll(() => page.evaluate(() => document.fullscreenElement !== null))
        .toBe(mode === 'native');
      await expect
        .poll(async () => (await plot.boundingBox())!.height)
        .toBeGreaterThan(300);

      box = (await plot.boundingBox())!;
      const anchor = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
      const priorStart = await start();
      const priorCount = await count();
      await page.mouse.move(anchor.x, anchor.y);
      await page.mouse.down();
      await page.mouse.move(anchor.x + Math.min(160, box.width / 4), anchor.y, {
        steps: 6,
      });
      await page.mouse.up();
      await expect.poll(start).toBeLessThan(priorStart);
      expect(await count()).toBe(priorCount);
      await expect(page.getByRole('tooltip')).toHaveCount(0);
      await page.mouse.move(anchor.x, anchor.y);
      await page.mouse.wheel(0, -300);
      await expect.poll(count).toBeLessThan(priorCount);
      if (kind === 'prices') expect(await count()).toBeLessThanOrEqual(1000);
      if (kind === 'curve') await hoverFinalCurvePoint(page, plot);
      else await hoverCandle(page, plot, 'last');
      const reading = page.getByRole('tooltip');
      await expect(reading).toBeVisible();
      expect(
        await reading.evaluate((element) => {
          const full =
            document.fullscreenElement ??
            document.querySelector('.chart-workspace.is-expanded');
          return full?.contains(element);
        }),
      ).toBe(true);
      // Viewport capture preserves the actual floating reading (full-page capture resizes).
      await page.screenshot({
        path: testInfo.outputPath(`${kind}-${mode}-fullscreen.png`),
      });
      // The wheel must remain usable at maximum zoom: rounding cannot trap a
      // single observation or prevent returning from two observations to one.
      for (let step = 0; step < 12 && (await count()) > 1; step++) {
        const previousCount = await count();
        await zoomIn.click();
        await expect.poll(count).toBeLessThan(previousCount);
      }
      await expect.poll(count).toBe(1);
      box = (await plot.boundingBox())!;
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.wheel(0, 100);
      await expect.poll(count).toBe(2);
      await page.mouse.wheel(0, -100);
      await expect.poll(count).toBe(1);
      const retainedStart = await start(),
        retainedCount = await count();
      await page.keyboard.press('Escape');
      await expect(workspace).not.toHaveClass(/is-expanded/);
      await expect(open).toBeFocused();
      await expect
        .poll(() => page.evaluate(() => document.fullscreenElement === null))
        .toBe(true);
      expect(await start()).toBe(retainedStart);
      expect(await count()).toBe(retainedCount);
      await expect(page.getByRole('tooltip')).toHaveCount(0);
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth + 1,
          ),
        )
        .toBe(true);
    }
    expect(
      await readApi<PortfolioResponse>(
        page,
        `/api/datasets/${dataset.id}/portfolio`,
      ),
    ).toEqual(before);
  });
}
