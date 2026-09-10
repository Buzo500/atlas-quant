import { test, expect, readApi, tab, select } from './fixtures';
import type {
  StateResponse,
  CatalogResponse,
  BookDetail,
  BookDocuments,
  PortfolioDetail,
} from '../lib/api-types';

const columns =
  'external_id,date,day_sequence,kind,listing_ref,quantity,unit_price,gross_amount,currency,fee_amount,fee_currency,tax_amount,tax_currency,fx_to_amount,fx_to_currency,ratio_numerator,ratio_denominator,corporate_event_ref'.split(
    ',',
  );
const movements: Record<string, string>[] = [
  { external_id: 'deposit', kind: 'deposit', gross_amount: '1000.00' },
  {
    external_id: 'buy',
    kind: 'buy',
    listing_ref: 'ASSET',
    quantity: '4',
    unit_price: '100',
    gross_amount: '400.00',
    fee_amount: '2.00',
  },
  {
    external_id: 'sale',
    kind: 'sell',
    listing_ref: 'ASSET',
    quantity: '1',
    unit_price: '110',
    gross_amount: '110.00',
    fee_amount: '1.00',
  },
];
const csv =
  [
    columns.join(','),
    ...movements.map((event, index) => {
      const row: Record<string, string> = {
        date: '2026-01-05',
        day_sequence: String(index + 1),
        currency: 'EUR',
        fee_amount: '0.00',
        fee_currency: 'EUR',
        tax_amount: '0.00',
        tax_currency: 'EUR',
        ...event,
      };
      return columns.map((key) => row[key] || '').join(',');
    }),
  ].join('\n') + '\n';

test('D4: libro exacto, revisión del extracto y corrección conservando historia', async ({
  page,
}, testInfo) => {
  await page.goto('/');
  await expect(
    page.getByText('Motor conectado', { exact: true }),
  ).toBeVisible();
  if (!(await readApi<StateResponse>(page, '/api/state')).datasets.length) {
    await page
      .getByRole('button', { name: 'Cargar demostración', exact: true })
      .click();
    await expect(
      page.getByRole('heading', { name: 'Posiciones', exact: true }),
    ).toBeVisible();
  }
  const state = await readApi<StateResponse>(page, '/api/state');
  const oldId = state.portfolios![0].id;
  const original = await readApi<PortfolioDetail>(
    page,
    `/api/portfolios/${oldId}`,
  );
  const catalog = await readApi<CatalogResponse>(page, '/api/catalog');
  const listing = catalog.listings.find((item) => item.currency === 'EUR')!;
  const instrument = catalog.instruments.find(
    (item) => item.id === listing.instrument_id,
  )!;
  const listingOption = `${instrument.name} · ${listing.market || 'local'} · ${listing.currency} · ${listing.id.slice(0, 8)}`;
  await tab(page, 'Datos');
  await page.getByText('Crear una cartera', { exact: true }).click();
  await page
    .getByLabel('Nombre de cartera', { exact: true })
    .fill('D4 libro sintético E2E');
  await expect(
    page.getByRole('combobox', { name: 'Formato del libro', exact: true }),
  ).toContainText('Libro exacto');
  await page
    .getByRole('button', { name: 'Crear cartera EUR', exact: true })
    .click();
  await expect(
    page.getByRole('combobox', { name: 'Cartera activa', exact: true }),
  ).toContainText('D4 libro sintético E2E');
  const created = (
    await readApi<StateResponse>(page, '/api/state')
  ).portfolios!.find((p) => p.name === 'D4 libro sintético E2E')!;
  const route = `/api/portfolios/${created.id}/book`;
  const panel = page.getByRole('region', {
    name: 'Libro y conciliación',
    exact: true,
  });
  const preview = panel.getByRole('region', {
    name: 'Previsualización contable',
  });
  const prepare = panel.getByRole('button', {
    name: 'Previsualizar revisión',
    exact: true,
  });
  const confirm = panel.getByRole('button', {
    name: 'Confirmar revisión contable',
    exact: true,
  });
  const open = panel.getByRole('button', {
    name: 'Revisar un lote o extracto',
    exact: true,
  });
  await open.click();
  await panel
    .getByLabel('Fuente del extracto', { exact: true })
    .fill('Fixture E2E');
  await panel.getByLabel('Cuenta de origen', { exact: true }).fill('DEMO-D4');
  await panel
    .getByLabel('Archivo de libro o extracto', { exact: true })
    .setInputFiles({
      name: 'movimientos.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(csv),
    });
  await expect(
    panel.getByLabel('Contenido del libro o extracto', { exact: true }),
  ).toHaveValue(csv);
  async function mapAsset() {
    await panel
      .getByText('Mapeo de referencias a cotizaciones', { exact: true })
      .click();
    await panel
      .getByRole('button', { name: 'Añadir referencia CSV', exact: true })
      .click();
    await panel.getByLabel('Referencia CSV 1', { exact: true }).fill('ASSET');
    await select(page, 'Cotización CSV 1', listingOption);
  }
  await mapAsset();
  await prepare.click();
  await expect(
    preview.getByText('Efectivo: 707.00 EUR', { exact: true }),
  ).toBeVisible();
  expect((await readApi<BookDetail>(page, route)).total).toBe(0);
  await panel
    .getByLabel('Cuenta de origen', { exact: true })
    .fill('DEMO-D4-revisada');
  await expect(confirm).toHaveCount(0);
  await prepare.click();
  await confirm.click();
  await expect(
    panel.getByText('EUR · revisión 2', { exact: true }),
  ).toBeVisible();
  let book = await readApi<BookDetail>(page, route);
  expect(book.balance).toMatchObject({
    cash: '707.00',
    realized_pnl: '8.5',
    positions: [{ listing_id: listing.id, quantity: '3', cost_basis: '301.5' }],
  });
  expect(book.total).toBe(3);
  await open.click();
  await select(page, 'Tipo de revisión', 'Extracto de referencia');
  await panel
    .getByLabel('Fecha del lote o extracto', { exact: true })
    .fill('2026-01-05');
  await panel
    .getByLabel('Contenido del libro o extracto', { exact: true })
    .fill(
      'as_of_date,record_type,listing_ref,currency,quantity,amount\n2026-01-05,cash,,EUR,,708.00\n2026-01-05,position,ASSET,EUR,3,\n',
    );
  await mapAsset();
  await expect(prepare).toBeDisabled();
  await panel.getByRole('checkbox').check();
  await prepare.click();
  await expect(
    preview.getByRole('row', {
      name: 'Efectivo EUR 707 708 1 Pendiente de resolver',
      exact: true,
    }),
  ).toBeVisible();
  await confirm.click();
  await expect(panel.getByText(/Revisión guardada/)).toBeVisible();
  expect((await readApi<BookDetail>(page, route)).balance).toEqual(
    book.balance,
  );
  await panel
    .getByText('Historial de lotes, extractos y correcciones', { exact: true })
    .click();
  await expect(
    panel.getByRole('cell', { name: 'Diferencias', exact: true }),
  ).toBeVisible();
  for (const width of [3440, 1280, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await panel.screenshot({
    path: testInfo.outputPath('book-before-correction.png'),
  });
  await select(page, 'Tipo de revisión', 'Corrección de movimiento');
  await select(page, 'Movimiento a corregir', '05/01/2026 · sell · sale');
  await panel
    .getByLabel('Motivo de corrección', { exact: true })
    .fill('Venta incluida por error en el fixture');
  await prepare.click();
  await expect(
    preview.getByText('Efectivo: 598.00 EUR', { exact: true }),
  ).toBeVisible();
  await confirm.click();
  await expect(
    panel.getByText('EUR · revisión 3', { exact: true }),
  ).toBeVisible();
  book = await readApi<BookDetail>(page, route);
  expect(book.balance).toMatchObject({
    cash: '598.00',
    positions: [{ quantity: '4', cost_basis: '402' }],
  });
  expect(
    (await readApi<BookDetail>(page, route + '?revision=2')).balance.cash,
  ).toBe('707.00');
  const documents = await readApi<BookDocuments>(
    page,
    `/api/portfolios/${created.id}/book-documents`,
  );
  expect(documents.total).toBe(3);
  expect(
    documents.documents.find((d) => d.kind === 'reconciliation')!.current,
  ).toBe(false);
  await panel
    .getByLabel('Fecha de corte del libro', { exact: true })
    .fill('2026-01-04');
  await panel
    .getByRole('button', { name: 'Consultar libro al corte', exact: true })
    .click();
  await expect(
    panel.getByText('Efectivo: 0.00 EUR', { exact: true }),
  ).toBeVisible();
  await tab(page, 'Cartera');
  await expect(
    page.getByRole('heading', { name: 'Libro contable EUR / USD', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText('Efectivo: 598.00 EUR', { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText('Valor de la cartera', { exact: true }),
  ).toHaveCount(0);
  expect(
    (await readApi<PortfolioDetail>(page, `/api/portfolios/${oldId}`)).value,
  ).toEqual(original.value);
});
