import type { Page } from '@playwright/test';
import { test, expect, readApi, select } from './fixtures';
import type {
  CatalogResponse,
  MarketPreview,
  LabHistory,
  LabReport,
} from '../lib/api-types';
import reference from '../../docs/fixtures/v0_6_lab_reference.json' with { type: 'json' };

async function post<T>(page: Page, path: string, data: unknown): Promise<T> {
  const response = await page.request.post('/api' + path, {
    headers: { 'X-Atlas-Client': 'local-v1' },
    data,
  });
  expect(response.ok(), await response.text()).toBe(true);
  return response.json();
}

test('v0.6 Laboratorio: CSV, desarrollo, reserva final, persistencia y reproducción', async ({
  page,
}) => {
  let catalog = await readApi<CatalogResponse>(page, '/api/catalog');
  catalog = await post(page, '/catalog/instruments', {
    expected_revision: catalog.revision,
    name: 'Activo ficticio SMA',
    source: 'Fixture sintético v0.6',
  });
  const instrument = catalog.instruments.find(
    (i) => i.name === 'Activo ficticio SMA',
  )!;
  catalog = await post(page, '/catalog/listings', {
    expected_revision: catalog.revision,
    instrument_id: instrument.id,
    currency: 'EUR',
    market: 'TEST',
  });
  const listing = catalog.listings.find(
    (l) => l.instrument_id === instrument.id,
  )!;
  const body = { ...reference.market, listing_id: listing.id };
  const preview = await post<MarketPreview>(
    page,
    '/v2/market/prices/imports',
    body,
  );
  await post(page, '/v2/market/prices/imports', {
    ...body,
    commit: true,
    preview_token: preview.preview_token,
  });
  await page.goto('/?tab=lab');
  await page
    .getByText('Simulación SMA con protocolo temporal', { exact: true })
    .click();
  await select(page, 'Versión CSV nativa EUR', 'SMA EUR ficticia · v1');
  const p = reference.protocol;
  const form = page.getByRole('form', {
    name: 'Configuración del protocolo SMA',
  });
  for (const [label, value] of [
    ['Nombre del protocolo', p.name],
    ['Inicio del desarrollo', p.start_date],
    ['Inicio de la prueba final', p.holdout_date],
    ['Fin del protocolo', p.end_date],
    ['Media rápida (sesiones)', String(p.fast)],
    ['Media lenta (sesiones)', String(p.slow)],
    ['CSV de sesiones y disponibilidad de apertura', p.sessions_csv],
    ['Procedencia de aperturas y disponibilidad', p.opening_source],
    ['Evidencia de ausencia de eventos corporativos', p.event_free_source],
    ['Capital inicial EUR', '1000'],
    ['Comisión proporcional (pb)', '0'],
    ['Deslizamiento (pb)', '0'],
  ])
    await form.getByLabel(label, { exact: true }).fill(value);
  await page
    .getByLabel(
      'He revisado la evidencia y la ausencia de eventos corporativos en el periodo',
    )
    .check();
  await page
    .getByRole('button', { name: 'Congelar y simular desarrollo' })
    .click();
  const development = page.getByRole('region', {
    name: 'Resultado de desarrollo',
    exact: true,
  });
  await expect(development).toBeVisible();
  await expect(
    development.getByRole('cell', { name: '800,00 €', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Abrir prueba final' }),
  ).toBeDisabled();
  const history = await readApi<LabHistory>(page, '/api/lab/protocols');
  const id = history.items.find((item) => item.name === p.name)!.id;
  expect(
    (await readApi<LabReport>(page, `/api/lab/protocols/${id}`)).holdout,
  ).toBeNull();
  for (const width of [1366, 3440, 960]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
    await expect(
      page.getByRole('button', { name: 'Abrir prueba final' }),
    ).toBeVisible();
  }
  await page
    .getByLabel('Entiendo que abrir la prueba final consume su reserva')
    .check();
  await page.getByRole('button', { name: 'Abrir prueba final' }).click();
  await expect(
    page.getByRole('region', {
      name: 'Resultado de la prueba final',
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await page
    .getByText('Simulación SMA con protocolo temporal', { exact: true })
    .click();
  await page
    .getByRole('button', { name: `Ver ${p.name}`, exact: true })
    .click();
  await expect(
    page.getByRole('region', {
      name: 'Resultado de la prueba final',
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Comprobar reproducción' }).click();
  await expect(
    page.getByText('Reproducción correcta: coincide con el informe guardado.'),
  ).toBeVisible();
  const report = await readApi<LabReport>(page, `/api/lab/protocols/${id}`);
  expect(report.holdout!.metrics.map((m) => m.final_nav_eur)).toEqual(
    reference.expected_nav_eur,
  );
});
