import { test, expect, readApi, tab, select } from './fixtures';
import type {
  StateResponse,
  DatasetPricesResponse,
  QualityReport,
} from '../lib/api-types';

test('D3: calendario explícito, evidencia revisable y corrección histórica conservada', async ({
  page,
}) => {
  await page.goto('/');
  await expect(
    page.getByText('Motor conectado', { exact: true }),
  ).toBeVisible();
  const before = await readApi<StateResponse>(page, '/api/state');
  await tab(page, 'Datos');
  await page
    .getByRole('textbox', { name: 'Nombre del conjunto', exact: true })
    .fill('D3 calendario de prueba');
  await page
    .getByPlaceholder('Ej.: exportación de mi proveedor, OHLC sin ajustar')
    .fill('Fixture sintético D3');
  await page
    .getByRole('switch', { name: 'Son datos sintéticos', exact: true })
    .click();
  const csv =
    'date,symbol,open,high,low,close,volume,currency\n2026-01-02,D3,100,100,100,100,10,EUR\n2026-01-05,D3,110,110,110,110,10,EUR';
  await page.getByLabel('Archivo CSV', { exact: true }).setInputFiles({
    name: 'd3.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csv),
  });
  await page
    .getByRole('button', { name: 'Importar precios', exact: true })
    .click();
  await expect(
    page.getByText('Precios importados y versión guardada.', { exact: true }),
  ).toBeVisible();
  const state = await readApi<StateResponse>(page, '/api/state');
  const dataset = state.datasets.find(
    (d) => d.name === 'D3 calendario de prueba',
  )!;
  expect(dataset).toBeDefined();
  const panel = page.getByRole('region', {
    name: 'Calidad de precios',
    exact: true,
  });
  await expect(
    panel.getByText('Sin calendario documentado', { exact: false }),
  ).toBeVisible();
  await panel
    .getByText('Documentar calendario y base de precios', { exact: true })
    .click();
  for (const [label, value] of [
    ['Nombre del calendario', 'Calendario D3'],
    ['Mercado del calendario', 'SYNTHETIC'],
    ['Fuente del calendario', 'Fixture E2E declarado'],
    ['Fuente de la base de precios', 'Precios sintéticos sin ajustes'],
    ['Fuente de la disponibilidad', 'Reloj del fixture'],
  ]) {
    await panel.getByLabel(label, { exact: true }).fill(value);
  }
  await panel
    .getByLabel(/^CSV del calendario/)
    .fill(
      'date,status,close_at\n2026-01-02,open,2026-01-02T16:00:00Z\n2026-01-03,closed,\n2026-01-04,closed,\n2026-01-05,open,2026-01-05T16:00:00Z',
    );
  await panel
    .getByRole('switch', {
      name: 'Calendario contrastado con su fuente',
      exact: true,
    })
    .click();
  await select(page, 'Base de los precios', 'Observados sin ajustar');
  await panel
    .getByRole('switch', {
      name: 'Base contrastada con su fuente',
      exact: true,
    })
    .click();
  await panel
    .getByLabel(/^CSV de disponibilidad/)
    .fill(
      'date,available_at\n2026-01-02,2026-01-02T16:00:00Z\n2026-01-05,2026-01-05T16:00:00Z',
    );
  await panel.getByRole('button', { name: 'Previsualizar evidencia' }).click();
  await expect(
    panel.getByRole('button', { name: 'Confirmar evidencia' }),
  ).toBeVisible();
  await panel
    .getByLabel('Fuente del calendario', { exact: true })
    .fill('Fixture revisado D3');
  await expect(
    panel.getByRole('button', { name: 'Confirmar evidencia' }),
  ).toHaveCount(0);
  await panel.getByRole('button', { name: 'Previsualizar evidencia' }).click();
  await panel.getByRole('button', { name: 'Confirmar evidencia' }).click();
  await expect(panel.getByText('Versión 2', { exact: true })).toBeVisible();
  await expect(
    panel.getByRole('row', {
      name: 'Investigación acreditada al cierre Apta',
      exact: true,
    }),
  ).toBeVisible();
  await panel.getByText('Cobertura por fecha', { exact: true }).click();
  await expect(
    panel
      .getByRole('row')
      .filter({ hasText: '03/01/2026' })
      .filter({ hasText: 'Mercado cerrado' }),
  ).toBeVisible();
  for (const width of [3440, 1280, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
  }
  await page.setViewportSize({ width: 1280, height: 1000 });
  await panel.getByText('Revisar precios históricos', { exact: true }).click();
  await panel
    .getByLabel('Motivo de la revisión', { exact: true })
    .fill('Corregir la primera barra del fixture');
  await panel
    .getByLabel('CSV de precios revisados', { exact: true })
    .fill(csv.replace('100,100,100,100', '102,102,102,102'));
  await panel.getByRole('button', { name: 'Previsualizar revisión' }).click();
  await expect(
    panel.getByText('1 barras corregidas · 0 añadidas', { exact: true }),
  ).toBeVisible();
  await panel
    .getByRole('button', { name: 'Confirmar revisión de precios' })
    .click();
  await expect(panel.getByText('Versión 3', { exact: true })).toBeVisible();
  const old = await readApi<DatasetPricesResponse>(
    page,
    `/api/datasets/${dataset.id}/prices?version=1&symbol=D3`,
  );
  const current = await readApi<DatasetPricesResponse>(
    page,
    `/api/datasets/${dataset.id}/prices?version=3&symbol=D3`,
  );
  expect(old.bars[0].close).toBe(100);
  expect(current.bars[0].close).toBe(102);
  const quality = await readApi<QualityReport>(
    page,
    `/api/datasets/${dataset.id}/quality?version=3&symbol=D3`,
  );
  expect(quality.calendar_verified).toBe(false);
  expect((await readApi<StateResponse>(page, '/api/state')).portfolios).toEqual(
    before.portfolios,
  );
});
