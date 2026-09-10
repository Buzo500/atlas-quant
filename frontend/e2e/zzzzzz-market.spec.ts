import type { Page } from '@playwright/test';
import { test, expect, readApi, tab, select } from './fixtures';
import type {
  CatalogResponse,
  PortfolioRecord,
  MarketCatalog,
  ValuationHistory,
} from '../lib/api-types';

const headers = { 'X-Atlas-Client': 'local-v1' };
async function post<T>(page: Page, path: string, data: unknown): Promise<T> {
  const response = await page.request.post('/api' + path, { headers, data });
  expect(response.ok(), await response.text()).toBe(true);
  return response.json();
}

test('D6: CSV USD y FX, vínculo explícito y patrimonio completo en tres anchos', async ({
  page,
}, info) => {
  await page.goto('/');
  await expect(
    page.getByText('Motor conectado', { exact: true }),
  ).toBeVisible();
  let catalog = await readApi<CatalogResponse>(page, '/api/catalog');
  catalog = await post(page, '/catalog/instruments', {
    expected_revision: catalog.revision,
    name: 'D6 activo USD ficticio',
    source: 'Fixture E2E',
  });
  const instrument = catalog.instruments.find(
    (i) => i.name === 'D6 activo USD ficticio',
  )!;
  catalog = await post(page, '/catalog/listings', {
    expected_revision: catalog.revision,
    instrument_id: instrument.id,
    currency: 'USD',
  });
  const listing = catalog.listings.find(
    (l) => l.instrument_id === instrument.id,
  )!;
  const portfolio = await post<PortfolioRecord>(page, '/portfolios', {
    name: 'D6 cartera USD ficticia',
    accounting_policy: 'atlas-accounting-v2',
  });
  const columns =
    'external_id,date,day_sequence,kind,listing_ref,quantity,unit_price,gross_amount,currency,fee_amount,fee_currency,tax_amount,tax_currency,fx_to_amount,fx_to_currency,ratio_numerator,ratio_denominator,corporate_event_ref'.split(
      ',',
    );
  const common = {
    date: '2026-01-05',
    currency: 'USD',
    fee_amount: '0.00',
    fee_currency: 'USD',
    tax_amount: '0.00',
    tax_currency: 'USD',
  };
  const rows: Record<string, string>[] = [
    {
      ...common,
      external_id: 'deposit',
      day_sequence: '1',
      kind: 'deposit',
      gross_amount: '1000.00',
    },
    {
      ...common,
      external_id: 'buy',
      day_sequence: '2',
      kind: 'buy',
      listing_ref: 'ASSET',
      quantity: '4',
      unit_price: '100',
      gross_amount: '400.00',
      fee_amount: '2.00',
    },
  ];
  const body = {
    expected_revision: 1,
    format_id: 'atlas-ledger-v2',
    source: 'Fixture E2E',
    source_account: 'DEMO-D6',
    as_of_date: '2026-01-06',
    mapping: { ASSET: listing.id },
    csv:
      columns.join(',') +
      '\n' +
      rows.map((r) => columns.map((c) => r[c] || '').join(',')).join('\n') +
      '\n',
  };
  const review = await post<{ preview_token: string }>(
    page,
    `/v2/portfolios/${portfolio.id}/imports`,
    body,
  );
  await post(page, `/v2/portfolios/${portfolio.id}/imports`, {
    ...body,
    commit: true,
    preview_token: review.preview_token,
  });
  await page.goto(`/?tab=data&portfolio=${portfolio.id}`);
  const workspace = page.getByRole('region', {
    name: 'Precios nativos y tipos de cambio',
    exact: true,
  });
  const calendar =
    'date,status,close_at\n2026-01-05,open,2026-01-05T20:00:00Z\n2026-01-06,open,2026-01-06T20:00:00Z\n';
  for (const kind of ['prices', 'fx'] as const) {
    const name = kind === 'prices' ? 'D6 precios USD E2E' : 'D6 FX E2E';
    await workspace
      .getByRole('button', {
        name:
          kind === 'prices'
            ? 'Importar precios EUR/USD'
            : 'Importar FX USD → EUR',
        exact: true,
      })
      .click();
    const form = workspace.getByRole('region', {
      name: 'Importación de serie nativa',
      exact: true,
    });
    await form.getByLabel('Nombre de la serie', { exact: true }).fill(name);
    await form
      .getByLabel('Fuente de la serie', { exact: true })
      .fill('Fixture sintético, no cotizaciones reales');
    if (kind === 'prices')
      await select(
        page,
        'Cotización de los precios',
        `${instrument.name} · Local · USD · ${listing.id.slice(0, 8)}`,
      );
    const csv =
      kind === 'prices'
        ? 'date,listing_ref,open,high,low,close,volume,currency,available_at\n2026-01-05,ASSET,100,100,100,100,10,USD,2026-01-05T20:01:00Z\n2026-01-06,ASSET,110,110,110,110,10,USD,2026-01-06T20:01:00Z\n'
        : 'date,from_currency,to_currency,rate,available_at\n2026-01-05,USD,EUR,0.9,2026-01-05T20:01:00Z\n2026-01-06,USD,EUR,0.95,2026-01-06T20:01:00Z\n';
    await form
      .getByLabel('Archivo · CSV de observaciones', { exact: true })
      .setInputFiles({
        name: name + '.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(csv),
      });
    await expect(
      form.getByLabel('CSV de observaciones', { exact: true }),
    ).toHaveValue(csv);
    await form
      .getByText('Base de precios y calendario acreditado', { exact: true })
      .click();
    if (kind === 'prices') {
      await form
        .getByRole('checkbox', {
          name: 'He contrastado que los precios son brutos, sin ajustar',
          exact: true,
        })
        .check();
      await form
        .getByLabel('Evidencia de la base bruta', { exact: true })
        .fill('Precios brutos del escenario sintético');
    }
    await form
      .getByLabel('Nombre del calendario', { exact: true })
      .fill('Calendario sintético E2E');
    await form
      .getByLabel('Mercado del calendario', { exact: true })
      .fill('TEST');
    await form
      .getByLabel('Fuente del calendario', { exact: true })
      .fill('Dos cierres sintéticos acreditados');
    await form
      .getByLabel('Calendario CSV date,status,close_at', { exact: true })
      .fill(calendar);
    await form
      .getByRole('checkbox', {
        name: 'He contrastado la cobertura completa de este calendario',
        exact: true,
      })
      .check();
    await form
      .getByRole('button', { name: 'Previsualizar serie', exact: true })
      .click();
    await form
      .getByRole('button', { name: 'Confirmar serie', exact: true })
      .click();
    await workspace
      .getByRole('button', { name: 'Consultar ' + name, exact: true })
      .click();
    await workspace
      .getByRole('button', {
        name: 'Previsualizar vínculo de serie',
        exact: true,
      })
      .click();
    await workspace
      .getByRole('button', { name: 'Confirmar vínculo de serie', exact: true })
      .click();
    await expect(
      workspace.getByRole('button', {
        name: 'Confirmar vínculo de serie',
        exact: true,
      }),
    ).toHaveCount(0);
  }
  expect(
    (await readApi<MarketCatalog>(page, '/api/v2/market')).series,
  ).toHaveLength(2);
  await tab(page, 'Cartera');
  const valuation = page.getByRole('region', {
    name: 'Patrimonio en EUR',
    exact: true,
  });
  await valuation
    .getByLabel('Fecha de valoración', { exact: true })
    .fill('2026-01-06');
  await valuation
    .getByRole('button', { name: 'Calcular patrimonio', exact: true })
    .click();
  await expect(
    valuation.getByText('Patrimonio EUR · Completo', { exact: true }),
  ).toBeVisible();
  await expect(
    valuation.getByText('986.10 EUR', { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole('tabpanel', {name:'Cartera', exact:true}).getByText('Efectivo: 598.00 USD', { exact: true }),
  ).toBeVisible();
  for (const width of [3440, 1280, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await valuation.scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: info.outputPath(`d6-nav-${width}.png`),
      fullPage: true,
    });
  }
  await valuation
    .getByRole('button', { name: 'Guardar corte de patrimonio', exact: true })
    .click();
  await expect
    .poll(
      async () =>
        (
          await readApi<ValuationHistory>(
            page,
            `/api/v2/portfolios/${portfolio.id}/valuations`,
          )
        ).cuts.length,
    )
    .toBe(1);
});
