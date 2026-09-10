import type { Page } from '@playwright/test';
import { test, expect, readApi, tab, select, ensureDemo } from './fixtures';
import type {
  StateResponse,
  CatalogResponse,
  BookDetail,
  CorporateCatalog,
  CorporatePortfolio,
  CorporateDocuments,
} from '../lib/api-types';

const movementColumns =
  'external_id,date,day_sequence,kind,listing_ref,quantity,unit_price,gross_amount,currency,fee_amount,fee_currency,tax_amount,tax_currency,fx_to_amount,fx_to_currency,ratio_numerator,ratio_denominator,corporate_event_ref'.split(
    ',',
  );
const eventColumns =
  'external_id,event_type,listing_ref,effective_date,payment_date,available_at,gross_per_unit,currency,ratio_numerator,ratio_denominator,source_reference'.split(
    ',',
  );
const csv = (columns: string[], rows: Record<string, string>[]) =>
  [
    columns.join(','),
    ...rows.map((r) => columns.map((k) => r[k] || '').join(',')),
  ].join('\n') + '\n';

async function createBook(page: Page, name: string) {
  await page.goto('/');
  await expect(
    page.getByText('Motor conectado', { exact: true }),
  ).toBeVisible();
  if (!(await readApi<StateResponse>(page, '/api/state')).datasets.length)
    await ensureDemo(page);
  const catalog = await readApi<CatalogResponse>(page, '/api/catalog');
  const listing = catalog.listings.find((l) => l.currency === 'EUR')!;
  const instrument = catalog.instruments.find(
    (i) => i.id === listing.instrument_id,
  )!;
  const option = `${instrument.name} · ${listing.market || 'local'} · ${listing.id.slice(0, 8)}`;
  await tab(page, 'Datos');
  await page.getByText('Crear una cartera', { exact: true }).click();
  await page.getByLabel('Nombre de cartera', { exact: true }).fill(name);
  await page
    .getByRole('button', { name: 'Crear cartera EUR', exact: true })
    .click();
  await expect(
    page.getByRole('combobox', { name: 'Cartera activa', exact: true }),
  ).toContainText(name);
  const created = (
    await readApi<StateResponse>(page, '/api/state')
  ).portfolios!.find((p) => p.name === name)!;
  const book = page.getByRole('region', {
    name: 'Libro y conciliación',
    exact: true,
  });
  await book
    .getByRole('button', { name: 'Revisar un lote o extracto', exact: true })
    .click();
  await book
    .getByLabel('Fuente del extracto', { exact: true })
    .fill('Fixture D5');
  await book.getByLabel('Cuenta de origen', { exact: true }).fill(name);
  const common = {
    date: '2026-01-05',
    currency: 'EUR',
    fee_amount: '0.00',
    fee_currency: 'EUR',
    tax_amount: '0.00',
    tax_currency: 'EUR',
  };
  await book.getByLabel('Contenido del libro o extracto', { exact: true }).fill(
    csv(movementColumns, [
      {
        ...common,
        external_id: 'deposit',
        kind: 'deposit',
        gross_amount: '10000.00',
        day_sequence: '1',
      },
      {
        ...common,
        external_id: 'buy',
        kind: 'buy',
        listing_ref: 'ASSET',
        quantity: '100',
        unit_price: '1',
        gross_amount: '100.00',
        day_sequence: '2',
      },
    ]),
  );
  await book
    .getByText('Mapeo de referencias a cotizaciones', { exact: true })
    .click();
  await book
    .getByRole('button', { name: 'Añadir referencia CSV', exact: true })
    .click();
  await book.getByLabel('Referencia CSV 1', { exact: true }).fill('ASSET');
  await select(page, 'Cotización CSV 1', option);
  await book
    .getByRole('button', { name: 'Previsualizar revisión', exact: true })
    .click();
  await book
    .getByRole('button', { name: 'Confirmar revisión contable', exact: true })
    .click();
  await expect(
    book.getByText('EUR · revisión 2', { exact: true }),
  ).toBeVisible();
  return { id: created.id, name, listing, option, book };
}

async function importEvent(
  page: Page,
  fixture: Awaited<ReturnType<typeof createBook>>,
  kind: 'dividend' | 'split',
) {
  const panel = page.getByRole('region', {
    name: 'Dividendos y splits',
    exact: true,
  });
  await panel.getByText('Importar o revisar eventos', { exact: true }).click();
  await panel
    .getByLabel('Fuente de eventos', { exact: true })
    .fill(fixture.name);
  const contents = csv(eventColumns, [
    {
      external_id: 'event',
      event_type: kind,
      listing_ref: 'ASSET',
      effective_date: '2026-01-10',
      payment_date: kind === 'dividend' ? '2026-01-20' : '',
      gross_per_unit: kind === 'dividend' ? '0.50' : '',
      currency: 'EUR',
      ratio_numerator: kind === 'split' ? '1' : '',
      ratio_denominator: kind === 'split' ? '2' : '',
      source_reference: 'Documento sintético E2E',
    },
  ]);
  await panel
    .getByLabel('Archivo · CSV de eventos corporativos', { exact: true })
    .setInputFiles({
      name: 'evento.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(contents),
    });
  await expect(
    panel.getByLabel('CSV de eventos corporativos', { exact: true }),
  ).toHaveValue(contents);
  await select(
    page,
    'Cotizaciones del evento · destino 1',
    fixture.option.replace(' · local · ', ' · Local · '),
  );
  await panel
    .getByLabel('Evidencia del evento', { exact: true })
    .fill('Datos y fechas contrastados del fixture');
  await panel
    .getByRole('checkbox', {
      name: 'He contrastado la evidencia y los campos declarados',
    })
    .check();
  // Another synthetic test may have a different economic event on the same day.
  await panel
    .getByText('Segunda fuente o posibles duplicados', { exact: true })
    .click();
  await panel
    .getByRole('button', {
      name: 'Añadir motivos de evento distinto',
      exact: true,
    })
    .click();
  await panel
    .getByLabel('Motivos de evento distinto · referencia 1', { exact: true })
    .fill('event');
  await panel
    .getByLabel('Motivos de evento distinto · destino 1', { exact: true })
    .fill('Evento independiente de esta prueba sintética');
  await panel
    .getByRole('button', { name: 'Previsualizar eventos', exact: true })
    .click();
  await panel
    .getByRole('button', { name: 'Confirmar eventos revisados', exact: true })
    .click();
  await expect(
    panel.getByRole('row').filter({ hasText: fixture.name }),
  ).toBeVisible();
  const catalog = await readApi<CorporateCatalog>(
    page,
    '/api/corporate-events',
  );
  const eventId = catalog.sources.find(
    (s) => s.source === fixture.name,
  )!.event_id;
  const event = catalog.events.find((e) => e.id === eventId)!;
  const row = panel
    .getByRole('row')
    .filter({ hasText: `${kind === 'dividend' ? 'Dividendo' : 'Split'} ·` })
    .filter({ hasText: kind === 'dividend' ? '0.5 EUR/título' : '1:2' })
    .filter({ hasText: fixture.name })
    .first();
  await row
    .getByRole('button', { name: 'Seleccionar evento', exact: true })
    .click();
  return {
    panel,
    event,
    application: panel.getByRole('region', {
      name: 'Aplicación del evento a cartera',
      exact: true,
    }),
  };
}

test('D5: derecho separado, cobro neto, corte histórico y evidencia sin duplicados', async ({
  page,
}, info) => {
  const fixture = await createBook(page, 'D5 dividendo E2E');
  const { panel, application } = await importEvent(page, fixture, 'dividend');
  await application
    .getByLabel('Fuente del movimiento', { exact: true })
    .fill('Fixture D5');
  await application
    .getByLabel('Cuenta de origen del movimiento', { exact: true })
    .fill(fixture.name);
  await application
    .getByLabel('Cantidad elegible acreditada', { exact: true })
    .fill('100');
  await application
    .getByLabel('Evidencia de elegibilidad y orden', { exact: true })
    .fill('100 títulos con derecho antes de exfecha');
  await application
    .getByRole('button', { name: 'Previsualizar aplicación', exact: true })
    .click();
  const preview = application.getByRole('region', {
    name: 'Previsualización de aplicación',
    exact: true,
  });
  await expect(
    preview.getByText('Derechos pendientes: 50.00 EUR', { exact: true }),
  ).toBeVisible();
  expect(
    (
      await readApi<CorporatePortfolio>(
        page,
        `/api/portfolios/${fixture.id}/corporate-actions`,
      )
    ).total,
  ).toBe(0);
  await application
    .getByRole('button', { name: 'Confirmar aplicación revisada', exact: true })
    .click();
  await expect(
    fixture.book.getByText('EUR · revisión 3', { exact: true }),
  ).toBeVisible();
  await select(page, 'Acción en la cartera', 'Crear cobro revisado');
  await application
    .getByLabel('Evidencia de elegibilidad y orden', { exact: true })
    .fill('Pago completo acreditado por el fixture');
  await application
    .getByLabel('ID externo del nuevo movimiento', { exact: true })
    .fill('payment');
  await application
    .getByLabel('Bruto del cobro EUR', { exact: true })
    .fill('50.00');
  await application
    .getByLabel('Retención del cobro EUR', { exact: true })
    .fill('9.50');
  await application
    .getByLabel('Comisión del cobro EUR', { exact: true })
    .fill('0.50');
  await application
    .getByRole('button', { name: 'Previsualizar aplicación', exact: true })
    .click();
  await expect(preview).toContainText('Efectivo del libro: 9940.00 EUR');
  await application
    .getByRole('button', { name: 'Confirmar aplicación revisada', exact: true })
    .click();
  await expect(
    fixture.book.getByText('EUR · revisión 4', { exact: true }),
  ).toBeVisible();
  const paid = await readApi<CorporatePortfolio>(
    page,
    `/api/portfolios/${fixture.id}/corporate-actions`,
  );
  expect(paid).toMatchObject({
    pending_receivables: '0.00',
    balance: { cash: '9940.00', net_contributions: '10000.00' },
    applications: [{ status: 'reconciled' }],
  });
  await panel
    .getByLabel('Corte de derechos y eventos', { exact: true })
    .fill('2026-01-15');
  await panel
    .getByRole('button', { name: 'Consultar derechos al corte', exact: true })
    .click();
  await expect(
    panel.getByText('Derechos pendientes: 50.00 EUR', { exact: true }),
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
  await panel.screenshot({ path: info.outputPath('dividendos.png') });
  await page.reload();
  await expect(
    panel.getByText('Derechos pendientes: 0.00 EUR', { exact: true }),
  ).toBeVisible();
  await tab(page, 'Cartera');
  const portfolioTab = page.getByRole('tabpanel', {
    name: 'Cartera',
    exact: true,
  });
  await expect(
    portfolioTab.getByRole('heading', {
      name: 'Derechos y eventos',
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    portfolioTab.getByText('Derechos pendientes: 0.00 EUR', { exact: true }),
  ).toBeVisible();
  expect(
    (
      await readApi<CorporateDocuments>(
        page,
        `/api/portfolios/${fixture.id}/corporate-documents`,
      )
    ).total,
  ).toBe(2);
});

test('D5: reverse split exacto conserva coste y requiere precios acreditados', async ({
  page,
}, info) => {
  const fixture = await createBook(page, 'D5 reverse split E2E');
  const { panel, application } = await importEvent(page, fixture, 'split');
  await application
    .getByLabel('Fuente del movimiento', { exact: true })
    .fill('Fixture D5');
  await application
    .getByLabel('Cuenta de origen del movimiento', { exact: true })
    .fill(fixture.name);
  await application
    .getByLabel('Evidencia de elegibilidad y orden', { exact: true })
    .fill('Reverse split 1 por 2 anterior a cualquier operación del día');
  await application
    .getByLabel('ID externo del nuevo movimiento', { exact: true })
    .fill('split');
  await application
    .getByRole('button', { name: 'Previsualizar aplicación', exact: true })
    .click();
  await application
    .getByRole('button', { name: 'Confirmar aplicación revisada', exact: true })
    .click();
  await expect(
    fixture.book.getByText('EUR · revisión 3', { exact: true }),
  ).toBeVisible();
  const current = await readApi<BookDetail>(
    page,
    `/api/portfolios/${fixture.id}/book`,
  );
  expect(current.balance).toMatchObject({
    cash: '9900.00',
    positions: [{ quantity: '50', cost_basis: '100' }],
  });
  await expect(
    panel.getByRole('cell', { name: 'Split aplicado', exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByRole('cell', { name: 'Sin acreditar', exact: true }),
  ).toBeVisible();
  const historical = await readApi<BookDetail>(
    page,
    `/api/portfolios/${fixture.id}/book?revision=2`,
  );
  expect(historical.balance.positions[0].quantity).toBe('100');
  await panel
    .getByText('Historial de aplicaciones y evidencia', { exact: true })
    .click();
  await panel
    .getByRole('button', { name: 'Consultar evidencia', exact: true })
    .click();
  const download = page.waitForEvent('download');
  await panel
    .getByRole('button', { name: 'Descargar evidencia JSON', exact: true })
    .click();
  expect((await download).suggestedFilename()).toMatch(
    /^atlas-evento-.+\.json$/,
  );
  await panel.screenshot({ path: info.outputPath('split.png') });
});

test('D5: enlazar cobro existente, rechazar contexto concurrente y corrección incompatible', async ({
  page,
}) => {
  const fixture = await createBook(page, 'D5 enlace E2E');
  const { application } = await importEvent(page, fixture, 'dividend');
  const book = fixture.book;
  await book
    .getByRole('button', { name: 'Revisar un lote o extracto', exact: true })
    .click();
  await book.getByLabel('Contenido del libro o extracto', { exact: true }).fill(
    csv(movementColumns, [
      {
        external_id: 'payment',
        date: '2026-01-20',
        day_sequence: '10',
        kind: 'dividend_payment',
        listing_ref: 'ASSET',
        gross_amount: '50.00',
        currency: 'EUR',
        fee_amount: '0.00',
        fee_currency: 'EUR',
        tax_amount: '0.00',
        tax_currency: 'EUR',
      },
    ]),
  );
  await book
    .getByText('Mapeo de referencias a cotizaciones', { exact: true })
    .click();
  await book
    .getByRole('button', { name: 'Añadir referencia CSV', exact: true })
    .click();
  await book.getByLabel('Referencia CSV 1', { exact: true }).fill('ASSET');
  await select(page, 'Cotización CSV 1', fixture.option);
  await book
    .getByText('Dividendos, splits y derechos afectados por el lote', {
      exact: true,
    })
    .click();
  await book
    .getByRole('button', {
      name: 'Añadir cobros sin derecho acreditado',
      exact: true,
    })
    .click();
  await book
    .getByLabel('Cobros sin derecho acreditado · referencia 1', { exact: true })
    .fill('payment');
  await book
    .getByLabel('Cobros sin derecho acreditado · destino 1', { exact: true })
    .fill('Extracto completo del pago; derecho aún pendiente');
  await book
    .getByRole('button', { name: 'Previsualizar revisión', exact: true })
    .click();
  await book
    .getByRole('button', { name: 'Confirmar revisión contable', exact: true })
    .click();
  await expect(
    book.getByText('EUR · revisión 3', { exact: true }),
  ).toBeVisible();
  const route = `/api/portfolios/${fixture.id}/corporate-actions`;
  const before = await readApi<CorporatePortfolio>(page, route);
  expect(before.unlinked_payments).toHaveLength(1);
  await select(page, 'Acción en la cartera', 'Enlazar movimiento existente');
  await application
    .getByLabel('Fuente del movimiento', { exact: true })
    .fill('Fixture D5');
  await application
    .getByLabel('Cuenta de origen del movimiento', { exact: true })
    .fill(fixture.name);
  await application
    .getByLabel('Cantidad elegible acreditada', { exact: true })
    .fill('100');
  await application
    .getByLabel('Evidencia de elegibilidad y orden', { exact: true })
    .fill('Derecho histórico acreditado posteriormente');
  await select(page, 'Movimiento existente', '2026-01-20 · payment · 50.00');
  await application
    .getByRole('button', { name: 'Previsualizar aplicación', exact: true })
    .click();
  // A second client changes the real catalog immediately before the confirmation.
  // The HTTP response is never replaced: the backend must reject the old token.
  await page.route(`**${route}`, async (intercepted) => {
    if (
      intercepted.request().method() === 'POST' &&
      intercepted.request().postDataJSON().commit
    ) {
      const catalog = await readApi<CatalogResponse>(page, '/api/catalog');
      const changed = await page.request.post('/api/catalog/instruments', {
        headers: { 'X-Atlas-Client': 'local-v1' },
        data: {
          expected_revision: catalog.revision,
          name: 'Cambio concurrente D5 sintético',
          source: 'Fixture',
        },
      });
      expect(changed.ok()).toBe(true);
    }
    await intercepted.continue();
  });
  const rejected = page.waitForResponse(
    (r) =>
      r.url().endsWith(route) &&
      r.request().method() === 'POST' &&
      r.request().postDataJSON().commit === true,
  );
  await application
    .getByRole('button', { name: 'Confirmar aplicación revisada', exact: true })
    .click();
  expect((await rejected).status()).toBe(409);
  await page.unroute(`**${route}`);
  await expect(
    application.getByRole('button', {
      name: 'Confirmar aplicación revisada',
      exact: true,
    }),
  ).toHaveCount(0);
  expect((await readApi<CorporatePortfolio>(page, route)).balance).toEqual(
    before.balance,
  );
  await application
    .getByRole('button', { name: 'Previsualizar aplicación', exact: true })
    .click();
  await application
    .getByRole('button', { name: 'Confirmar aplicación revisada', exact: true })
    .click();
  await expect(
    book.getByText('EUR · revisión 4', { exact: true }),
  ).toBeVisible();
  const linked = await readApi<CorporatePortfolio>(page, route);
  expect(linked.balance).toEqual(before.balance);
  expect(linked.unlinked_payments).toEqual([]);
  expect(linked.applications[0].status).toBe('reconciled');
  await book
    .getByRole('button', { name: 'Revisar un lote o extracto', exact: true })
    .click();
  await select(page, 'Tipo de revisión', 'Corrección de movimiento');
  await select(page, 'Movimiento a corregir', '05/01/2026 · buy · buy');
  await book
    .getByLabel('Motivo de corrección', { exact: true })
    .fill('Anulación incompatible con el derecho ya confirmado');
  const correction = page.waitForResponse((r) =>
    r.url().endsWith(`/api/portfolios/${fixture.id}/corrections`),
  );
  await book
    .getByRole('button', { name: 'Previsualizar revisión', exact: true })
    .click();
  expect((await correction).status()).toBe(422);
  await expect(
    book.getByRole('button', {
      name: 'Confirmar revisión contable',
      exact: true,
    }),
  ).toHaveCount(0);
  expect((await readApi<CorporatePortfolio>(page, route)).balance).toEqual(
    linked.balance,
  );
});
