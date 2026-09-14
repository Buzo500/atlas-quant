import { test, expect, ensureDemo, readApi, tab, select } from './fixtures';
import type {
  DatasetPricesResponse,
  DatasetResponse,
  StateResponse,
  PortfolioDetail,
  BindingPreview,
  CatalogResponse,
} from '../lib/api-types';

test('D2: cambiar fuente y ticker conserva cartera, libro y corte histórico', async ({
  page,
}, testInfo) => {
  const started = Date.now();
  const checkpoint = (phase: string) =>
    console.log(
      JSON.stringify({
        test: 'D2',
        phase,
        elapsed_ms: Date.now() - started,
      }),
    );
  const dataset = await ensureDemo(page);
  checkpoint('demo lista');
  const state = await readApi<StateResponse>(page, '/api/state');
  const portfolio = state.portfolios![0];
  const before = await readApi<PortfolioDetail>(
    page,
    `/api/portfolios/${portfolio.id}`,
  );
  const rows: string[] = ['date,symbol,open,high,low,close,volume,currency'];
  for (const symbol of dataset.manifest.symbols) {
    const prices = await readApi<DatasetPricesResponse>(
      page,
      `/api/datasets/${dataset.id}/prices?version=${dataset.version}&symbol=${symbol}`,
    );
    rows.push(
      ...prices.bars.map(
        (bar) =>
          `${bar.date},NEW_${symbol},${bar.open},${bar.high},${bar.low},${bar.close},${bar.volume},EUR`,
      ),
    );
  }
  await tab(page, 'Datos');
  await page
    .getByRole('textbox', { name: 'Nombre del conjunto', exact: true })
    .fill('D2 otra fuente');
  await page
    .getByPlaceholder('Ej.: exportación de mi proveedor, OHLC sin ajustar')
    .fill('Copia sintética E2E');
  // The imported source is explicitly synthetic, like its original demo.
  await page
    .getByRole('switch', { name: 'Son datos sintéticos', exact: true })
    .click();
  await page.getByLabel('Archivo CSV', { exact: true }).setInputFiles({
    name: 'd2-precios.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(rows.join('\n')),
  });
  await expect(
    page.getByRole('textbox', { name: 'Contenido CSV', exact: true }),
  ).toHaveValue(rows.join('\n'));
  expect(
    await page
      .getByRole('textbox', { name: 'Contenido CSV', exact: true })
      .evaluate((element) => ({
        height: element.clientHeight,
        scroll: element.scrollHeight,
      })),
  ).toMatchObject({ height: expect.any(Number), scroll: expect.any(Number) });
  expect(
    (await page
      .getByRole('textbox', { name: 'Contenido CSV', exact: true })
      .boundingBox())!.height,
  ).toBeLessThanOrEqual(512);
  const imported = page.waitForResponse(
    (r) => r.url().endsWith('/api/datasets') && r.request().method() === 'POST',
  );
  await page
    .getByRole('button', { name: 'Importar precios', exact: true })
    .click();
  const response = await imported;
  expect(response.ok()).toBe(true);
  const other: DatasetResponse = await response.json();
  checkpoint('fuente importada');
  await tab(page, 'Cartera');
  await expect(
    page.getByRole('heading', { name: 'Posiciones', exact: true }),
  ).toBeVisible();
  expect(
    (await readApi<PortfolioDetail>(page, `/api/portfolios/${portfolio.id}`))
      .value,
  ).toEqual(before.value);
  await tab(page, 'Datos');
  await page
    .getByText('Configurar fuentes de precios', { exact: true })
    .click();
  for (let index = 0; index < before.portfolio.bindings.length; index++) {
    await select(
      page,
      `Precios ${index + 1}`,
      `${other.name} · v${other.version}`,
    );
    await select(
      page,
      `Símbolo de precios ${index + 1}`,
      `NEW_${before.portfolio.bindings[index].symbol}`,
    );
  }
  const previewResponse = page.waitForResponse((r) =>
    r.url().endsWith(`/portfolios/${portfolio.id}/bindings`),
  );
  await page
    .getByRole('button', { name: 'Previsualizar fuentes', exact: true })
    .click();
  const preview: BindingPreview = await (await previewResponse).json();
  expect(preview.committed).toBe(false);
  expect(preview.value?.nav).toBe(before.value?.nav);
  const confirmation = page.waitForResponse(
    (r) =>
      r.url().endsWith(`/portfolios/${portfolio.id}/bindings`) &&
      r.request().postDataJSON()?.commit === true,
  );
  await page
    .getByRole('button', { name: 'Confirmar fuentes', exact: true })
    .click();
  expect((await confirmation).ok()).toBe(true);
  checkpoint('vínculos confirmados');
  const after = await readApi<PortfolioDetail>(
    page,
    `/api/portfolios/${portfolio.id}`,
  );
  expect(after.entries).toEqual(before.entries);
  expect(after.value?.nav).toBe(before.value?.nav);
  expect(after.context.bindings.every((b) => b.dataset_id === other.id)).toBe(
    true,
  );
  expect(
    await readApi<PortfolioDetail>(
      page,
      `/api/portfolios/${portfolio.id}?revision=${before.portfolio.revision}`,
    ),
  ).toEqual(before);
  checkpoint('histórico verificado');
  await tab(page, 'Cartera');
  for (const symbol of dataset.manifest.symbols)
    await expect(
      page
        .locator('.positions-panel')
        .getByText(`NEW_${symbol}`, { exact: true }),
    ).toBeVisible();
  await tab(page, 'Datos');
  checkpoint('vista de datos recuperada');
  for (const width of [3440, 1280, 390]) {
    await page.setViewportSize({ width, height: width === 3440 ? 1440 : 900 });
    await expect
      .poll(() =>
        page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      )
      .toBe(true);
  }
  await page.screenshot({
    path: testInfo.outputPath('d2-mobile.png'),
    fullPage: true,
  });
  await page.setViewportSize({ width: 3440, height: 1440 });
  await page.screenshot({
    path: testInfo.outputPath('d2-wide.png'),
    fullPage: true,
  });
});

// Catalog registration has its own setup and deadline. It does not depend on
// the imported prices, source rebinding or historical assertions above.
test('D2: registrar un instrumento persiste una única identidad', async ({
  page,
}) => {
  await page.goto('/?tab=data');
  await expect(
    page.getByText('Motor conectado', { exact: true }),
  ).toBeVisible();
  await page
    .getByText('Añadir instrumentos, cotizaciones o símbolos', { exact: true })
    .click();
  await page
    .getByRole('textbox', { name: 'Nombre del instrumento', exact: true })
    .fill('Instrumento E2E');
  await test.step('Registrar instrumento con formulario válido y respuesta POST', async () => {
    const button = page.getByRole('button', {
      name: 'Registrar instrumento',
      exact: true,
    });
    expect(
      await button.evaluate((element) =>
        (element as HTMLButtonElement).form?.checkValidity(),
      ),
    ).toBe(true);
    const [save] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().endsWith('/catalog/instruments') &&
          r.request().method() === 'POST',
        { timeout: 10_000 },
      ),
      button.click(),
    ]);
    expect(save.ok()).toBe(true);
  });
  const catalog = await readApi<CatalogResponse>(page, '/api/catalog');
  expect(
    catalog.instruments.filter((i) => i.name === 'Instrumento E2E'),
  ).toHaveLength(1);
});
