import type { Page } from '@playwright/test';
import { test, expect, readApi, select } from './fixtures';
import type {
  CatalogResponse,
  MarketPreview,
  AssetSourceCatalog,
  AssetAnalysisHistory,
  AssetAnalysisReport,
} from '../lib/api-types';

async function post<T>(page: Page, path: string, data: unknown): Promise<T> {
  const response = await page.request.post('/api' + path, {
    headers: { 'X-Atlas-Client': 'local-v1' },
    data,
  });
  expect(response.ok(), await response.text()).toBe(true);
  return response.json();
}
test('v0.5 comparador: fuentes EUR/USD, muestra común, guardado y tres anchos', async ({
  page,
}, info) => {
  await page.goto('/');
  await expect(
    page.getByText('Motor conectado', { exact: true }),
  ).toBeVisible();
  const days = Array.from(
    { length: 25 },
    (_, i) => `2026-01-${String(i + 1).padStart(2, '0')}`,
  );
  let price = 100;
  const values = days.map((_, i) => {
    if (i) price *= i % 2 ? 1.01 : 0.99;
    return price.toFixed(8);
  });
  const evidence = {
    symbol: 'ASSET',
    calendar_name: 'Escenario diario ficticio',
    market: 'TEST',
    calendar_source: 'Fixture sintético, todos los días abiertos',
    calendar_verified: true,
    calendar_csv:
      'date,status,close_at\n' +
      days.map((d) => `${d},open,${d}T20:00:00Z`).join('\n'),
    price_basis: 'raw',
    basis_verified: true,
    basis_source: 'Precios ficticios sin eventos corporativos',
  };
  for (const currency of ['EUR', 'USD']) {
    let catalog = await readApi<CatalogResponse>(page, '/api/catalog');
    catalog = await post(page, '/catalog/instruments', {
      expected_revision: catalog.revision,
      name: `Comparador ${currency} ficticio`,
      source: 'Fixture sintético',
    });
    const instrument = catalog.instruments.find(
      (i) => i.name === `Comparador ${currency} ficticio`,
    )!;
    catalog = await post(page, '/catalog/listings', {
      expected_revision: catalog.revision,
      instrument_id: instrument.id,
      currency,
    });
    const listing = catalog.listings.find(
      (l) => l.instrument_id === instrument.id,
    )!;
    const body = {
      name: `Comparador precios ${currency}`,
      source: 'Fixture sintético, no cotizaciones reales',
      listing_id: listing.id,
      evidence,
      csv:
        'date,listing_ref,open,high,low,close,volume,currency,available_at\n' +
        days
          .map((d, i) => {
            const v = currency === 'EUR' ? values[i] : '100';
            return `${d},ASSET,${v},${v},${v},${v},10,${currency},${d}T20:01:00Z`;
          })
          .join('\n'),
    };
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
  }
  const fxBody = {
    name: 'Comparador FX ficticio',
    source: 'Fixture sintético',
    evidence,
    csv:
      'date,from_currency,to_currency,rate,available_at\n' +
      days
        .map(
          (d, i) =>
            `${d},USD,EUR,${(Number(values[i]) / 100).toFixed(10)},${d}T20:01:00Z`,
        )
        .join('\n'),
  };
  const fxPreview = await post<MarketPreview>(
    page,
    '/v2/market/fx/imports',
    fxBody,
  );
  await post(page, '/v2/market/fx/imports', {
    ...fxBody,
    commit: true,
    preview_token: fxPreview.preview_token,
  });
  const sources = await readApi<AssetSourceCatalog>(
    page,
    '/api/v2/asset-analysis/sources',
  );
  await page.goto('/?tab=data');
  const workspace = page.getByRole('region', {
    name: 'Fichas y comparador de activos',
    exact: true,
  });
  await workspace
    .getByText('Abrir comparador de activos', { exact: true })
    .click();
  for (const currency of ['EUR', 'USD']) {
    const s = sources.sources.find(
      (s) => s.name === `Comparador ${currency} ficticio`,
    )!;
    await select(
      page,
      'Activo y fuente para comparar',
      `${s.name} · ${s.dataset_name} · ${currency} · v1 · ${s.ref.id.slice(0, 8)}`,
    );
    await workspace
      .getByRole('button', { name: 'Añadir activo a la comparación' })
      .click();
  }
  await expect(
    workspace.getByRole('button', { name: 'Calcular comparación' }),
  ).toBeDisabled();
  await select(
    page,
    'Fuente EUR por USD para comparar',
    `Comparador FX ficticio · v1 · 2026-01-01 — 2026-01-25 · ${fxPreview.series.id.slice(0, 8)}`,
  );
  await workspace.getByRole('button', { name: 'Calcular comparación' }).click();
  const result = workspace.getByRole('region', {
    name: 'Resultado del comparador',
  });
  await expect(
    result.getByText(
      'Pearson · 24 intervalos idénticos para todos los activos · mínimo 20.',
    ),
  ).toBeVisible();
  for (const width of [390, 1280, 3440]) {
    await page.setViewportSize({ width, height: width === 3440 ? 1440 : 900 });
    await expect(
      result.getByRole('heading', {
        name: 'Correlaciones de variaciones en EUR',
      }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await workspace.screenshot({
      path: info.outputPath(`asset-analysis-${width}.png`),
    });
  }
  await workspace.getByRole('button', { name: 'Guardar comparación' }).click();
  await expect(
    workspace.getByText('Confirmación guardada con su historial y evidencia.'),
  ).toBeVisible();
  const history = await readApi<AssetAnalysisHistory>(
    page,
    '/api/v2/asset-analysis/reports',
  );
  expect(history.reports).toHaveLength(1);
  const report = await readApi<AssetAnalysisReport>(
    page,
    '/api/v2/asset-analysis/reports/' + history.reports[0].id,
  );
  expect(report.result.profiles.every((p) => p.status === 'complete')).toBe(
    true,
  );
  expect(
    report.result.correlations.cells.every(
      (c) => Math.abs(Number(c.value) - 1) < 1e-8,
    ),
  ).toBe(true);
  expect(report.saved && report.current).toBe(true);
  await info.attach('asset-analysis-report', {
    body: JSON.stringify(report, null, 2),
    contentType: 'application/json',
  });
  await workspace.getByText('Comparaciones guardadas', { exact: true }).click();
  await workspace
    .getByRole('button', { name: `Consultar comparación ${report.created_at}` })
    .click();
  await expect(
    workspace.getByText('Informe guardado · Contexto vigente'),
  ).toBeVisible();
});
