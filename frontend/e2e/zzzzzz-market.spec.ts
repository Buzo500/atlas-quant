import type { Page } from '@playwright/test';
import { test, expect, readApi, tab, select } from './fixtures';
import type {
  CatalogResponse,
  PortfolioRecord,
  MarketCatalog,
  ValuationHistory,
  PerformanceHistory,
  TargetHistory,
  TargetReports,
  PlanningHistory,
  PlanningReport,
  TargetPreview,
} from '../lib/api-types';

const headers = { 'X-Atlas-Client': 'local-v1' };
async function post<T>(page: Page, path: string, data: unknown): Promise<T> {
  const response = await page.request.post('/api' + path, { headers, data });
  expect(response.ok(), await response.text()).toBe(true);
  return response.json();
}

test('D6/D7/v0.5: CSV USD y FX, patrimonio, rentabilidad y objetivos en tres anchos', async ({
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
    page
      .getByRole('tabpanel', { name: 'Cartera', exact: true })
      .getByText('Efectivo: 598.00 USD', { exact: true }),
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
  const performance = page.getByRole('region', {
    name: 'Rentabilidad por periodo',
    exact: true,
  });
  await performance
    .getByLabel('Cierre inicial del periodo', { exact: true })
    .fill('2026-01-05');
  await performance
    .getByLabel('Cierre final del periodo', { exact: true })
    .fill('2026-01-06');
  await performance
    .getByRole('button', { name: 'Calcular rentabilidad', exact: true })
    .click();
  await expect(performance.getByText('87,90 €', { exact: true })).toBeVisible();
  await expect(
    performance.getByText(/La tasa queda fuera del dominio/),
  ).toBeVisible();
  for (const width of [3440, 1280, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await performance.scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: info.outputPath(`d7-performance-${width}.png`),
      fullPage: true,
    });
  }
  await performance
    .getByRole('button', {
      name: 'Guardar informe de rentabilidad',
      exact: true,
    })
    .click();
  await expect
    .poll(
      async () =>
        (
          await readApi<PerformanceHistory>(
            page,
            `/api/v2/portfolios/${portfolio.id}/performance`,
          )
        ).reports.length,
    )
    .toBe(1);
  await page.reload();
  await performance
    .getByText('Informes de rentabilidad guardados', { exact: true })
    .click();
  await performance
    .getByRole('button', {
      name: 'Consultar informe 2026-01-05 a 2026-01-06',
      exact: true,
    })
    .click();
  await expect(
    performance
      .getByRole('region', { name: 'Detalle de rentabilidad', exact: true })
      .getByText('87,90 €', { exact: true }),
  ).toBeVisible();

  const objectives = page.getByRole('region', {
    name: 'Objetivos y desviaciones',
    exact: true,
  });
  await objectives
    .getByText('Consultar y editar objetivos', { exact: true })
    .click();
  await objectives
    .getByText('Crear o editar un borrador de objetivos', { exact: true })
    .click();
  await objectives
    .getByLabel('Nombre de los objetivos', { exact: true })
    .fill('Distribución ficticia v0.5');
  for (const [label, value] of [
    ['Objetivo', '60'],
    ['Mínimo', '50'],
    ['Máximo', '100'],
    ['Límite', '100'],
  ])
    await objectives
      .getByLabel(`${label} % · Efectivo`, { exact: true })
      .fill(value);
  await select(page, 'Instrumento para objetivos', instrument.name);
  await objectives
    .getByRole('button', { name: 'Añadir instrumento', exact: true })
    .click();
  for (const [label, value] of [
    ['Objetivo', '40'],
    ['Mínimo', '0'],
    ['Máximo', '50'],
    ['Límite', '60'],
  ])
    await objectives
      .getByLabel(`${label} % · ${instrument.name}`, { exact: true })
      .fill(value);
  for (const width of [3440, 1280, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await objectives
      .getByLabel('Nombre de los objetivos', { exact: true })
      .scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await objectives.screenshot({
      path: info.outputPath(`v05-editor-${width}.png`),
    });
  }
  await objectives
    .getByRole('button', { name: 'Revisar borrador', exact: true })
    .click();
  await objectives
    .getByRole('button', { name: 'Guardar borrador', exact: true })
    .click();
  await expect
    .poll(
      async () =>
        (
          await readApi<TargetHistory>(
            page,
            `/api/v2/portfolios/${portfolio.id}/targets`,
          )
        ).revision,
    )
    .toBe(1);
  expect(
    (
      await readApi<TargetHistory>(
        page,
        `/api/v2/portfolios/${portfolio.id}/targets`,
      )
    ).active,
  ).toBeNull();
  await objectives.getByText('Versiones y activación', { exact: true }).click();
  await objectives
    .getByRole('button', { name: 'Revisar activación v1', exact: true })
    .click();
  await objectives
    .getByRole('button', {
      name: 'Confirmar activación de objetivos',
      exact: true,
    })
    .click();
  await expect(
    objectives.getByRole('heading', {
      name: 'Activo: Distribución ficticia v0.5 · v1',
      exact: true,
    }),
  ).toBeVisible();
  const cutSummary = (
    await readApi<ValuationHistory>(
      page,
      `/api/v2/portfolios/${portfolio.id}/valuations`,
    )
  ).cuts[0];
  await select(
    page,
    'Corte para diagnóstico',
    `2026-01-06 · r${cutSummary.portfolio_revision} · 986.10 EUR · ${cutSummary.id.slice(0, 6)}`,
  );
  await objectives
    .getByRole('button', { name: 'Calcular desviaciones', exact: true })
    .click();
  const diagnosis = objectives.getByRole('region', {
    name: 'Diagnóstico de objetivos',
    exact: true,
  });
  await expect(diagnosis.locator('data[value="23.56"]')).toBeVisible();
  await expect(diagnosis.locator('data[value="-23.56"]')).toBeVisible();
  await objectives
    .getByText('Crear o editar un borrador de objetivos', { exact: true })
    .click();
  await objectives.getByText('Versiones y activación', { exact: true }).click();
  for (const width of [3440, 1280, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await objectives
      .getByRole('heading', { name: 'Objetivos y desviaciones', exact: true })
      .click();
    await diagnosis.scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await objectives.screenshot({
      path: info.outputPath(`v05-objectives-${width}.png`),
    });
  }
  await objectives
    .getByRole('button', { name: 'Guardar diagnóstico', exact: true })
    .click();
  await expect
    .poll(
      async () =>
        (
          await readApi<TargetReports>(
            page,
            `/api/v2/portfolios/${portfolio.id}/target-reports`,
          )
        ).reports.length,
    )
    .toBe(1);
  await page.reload();
  await objectives
    .getByText('Consultar y editar objetivos', { exact: true })
    .click();
  await objectives.getByText('Diagnósticos guardados', { exact: true }).click();
  await objectives
    .getByRole('button', {
      name: 'Consultar diagnóstico 2026-01-06',
      exact: true,
    })
    .click();
  await expect(diagnosis.locator('data[value="23.56"]')).toBeVisible();
  await expect(
    diagnosis.getByText(
      /^Cierre 2026-01-06.*Contexto vigente en la última consulta/,
    ),
  ).toBeVisible();

  const planning = page.getByRole('region', {
    name: 'Planificación y escenarios',
    exact: true,
  });
  await planning
    .getByText('Abrir análisis de cartera', { exact: true })
    .click();
  await select(
    page,
    'Patrimonio de partida',
    '2026-01-06 · 986.10 EUR · complete',
  );
  await planning
    .getByLabel('Aportación hipotética USD', { exact: true })
    .fill('250');
  await select(page, 'Cotización para simular', `${instrument.name} ·  · USD`);
  await planning
    .getByRole('button', { name: 'Añadir cotización al plan', exact: true })
    .click();
  await planning.getByLabel('Lote mínimo · 1', { exact: true }).fill('0.1');
  await planning
    .getByLabel('Comisión fija nativa · 1', { exact: true })
    .fill('1');
  await planning
    .getByLabel('Comisión proporcional (pb) · 1', { exact: true })
    .fill('0');
  await planning
    .getByRole('button', { name: 'Calcular análisis', exact: true })
    .click();
  const result = planning.getByRole('region', {
    name: 'Resultado de planificación',
    exact: true,
  });
  await expect(
    result.getByText('Compra simulada', { exact: true }).first(),
  ).toBeVisible();
  async function saveAnalysis(count: number) {
    await planning
      .getByRole('button', { name: 'Guardar análisis', exact: true })
      .click();
    await expect
      .poll(
        async () =>
          (
            await readApi<PlanningHistory>(
              page,
              `/api/v2/portfolios/${portfolio.id}/planning-reports`,
            )
          ).reports.length,
      )
      .toBe(count);
  }
  for (const width of [3440, 1280, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await result.scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await planning.screenshot({
      path: info.outputPath(`v05-planning-${width}.png`),
    });
  }
  await saveAnalysis(1);
  await select(page, 'Tipo de análisis', 'Escenarios de cartera');
  await planning
    .getByLabel('Variación de EUR por USD (%)', { exact: true })
    .fill('5');
  await select(page, 'Instrumento del escenario', instrument.name);
  await planning
    .getByRole('button', { name: 'Añadir cambio de precio', exact: true })
    .click();
  await planning.getByLabel('Cambio de precio 1', { exact: true }).fill('-10');
  await planning
    .getByRole('button', { name: 'Calcular análisis', exact: true })
    .click();
  await expect(result.getByText('991,515 EUR', { exact: true })).toBeVisible();
  await saveAnalysis(2);
  await select(page, 'Tipo de análisis', 'Comparar referencia');
  await select(
    page,
    'Rentabilidad de cartera para comparar',
    '2026-01-05 a 2026-01-06 · complete',
  );
  await planning
    .getByLabel('Nombre de referencia', { exact: true })
    .fill('Referencia ficticia E2E');
  await planning
    .getByLabel('Fuente de referencia', { exact: true })
    .fill('Serie sintética total return EUR');
  await planning
    .getByLabel('CSV de referencia', { exact: true })
    .fill('date,value\n2026-01-05,100\n2026-01-06,110\n');
  await planning
    .getByRole('checkbox', {
      name: 'Confirmo que la referencia representa rentabilidad total en EUR',
      exact: true,
    })
    .check();
  await planning
    .getByRole('button', { name: 'Calcular análisis', exact: true })
    .click();
  await expect(
    result.getByRole('heading', { name: /Referencia ficticia E2E/ }),
  ).toBeVisible();
  await saveAnalysis(3);

  const targetHead = await readApi<TargetHistory>(
    page,
    `/api/v2/portfolios/${portfolio.id}/targets`,
  );
  const draftBody = {
    expected_revision: cutSummary.portfolio_revision,
    expected_targets_revision: targetHead.revision,
    spec: {
      name: 'Segunda estrategia ficticia',
      rows: targetHead.active!.spec.rows.map((r) => ({
        ...r,
        weight: r.instrument_id ? '20' : '80',
      })),
    },
  };
  const draftPreview = await post<TargetPreview>(
    page,
    `/v2/portfolios/${portfolio.id}/targets`,
    draftBody,
  );
  await post(page, `/v2/portfolios/${portfolio.id}/targets`, {
    ...draftBody,
    commit: true,
    preview_token: draftPreview.preview_token,
  });
  await page.reload();
  await planning
    .getByText('Abrir análisis de cartera', { exact: true })
    .click();
  await select(page, 'Tipo de análisis', 'Combinar estrategias');
  for (const label of [
    'Distribución ficticia v0.5 · v1',
    'Segunda estrategia ficticia · v2',
  ]) {
    await select(page, 'Objetivos de estrategia', label);
    await planning
      .getByRole('button', {
        name: 'Añadir estrategia al presupuesto',
        exact: true,
      })
      .click();
  }
  await planning
    .getByLabel('Presupuesto de estrategia 1', { exact: true })
    .fill('50');
  await planning
    .getByLabel('Presupuesto de estrategia 2', { exact: true })
    .fill('50');
  await planning
    .getByRole('button', { name: 'Calcular análisis', exact: true })
    .click();
  await expect(result.getByText('30', { exact: true })).toBeVisible();
  await expect(result.getByText('70', { exact: true })).toBeVisible();
  await saveAnalysis(4);
  const analyses = (
    await readApi<PlanningHistory>(
      page,
      `/api/v2/portfolios/${portfolio.id}/planning-reports`,
    )
  ).reports;
  for (const item of analyses) {
    const saved = await readApi<PlanningReport>(
      page,
      `/api/v2/portfolios/${portfolio.id}/planning-reports/${item.id}`,
    );
    expect(saved.current).toBe(true);
    if (saved.result.kind === 'allocation')
      expect(saved.result.variants[0].trades[0].quantity).toBe('0.6');
    if (saved.result.kind === 'scenario')
      expect(saved.result.nav_after).toBe('991.515');
    if (saved.result.kind === 'aggregate')
      expect(
        saved.result.combined.spec.rows.find((r) => r.instrument_id)?.weight,
      ).toBe('30');
  }
  await page.reload();
  await planning
    .getByText('Abrir análisis de cartera', { exact: true })
    .click();
  await planning.getByText('Análisis guardados', { exact: true }).click();
  await planning
    .getByRole('button', {
      name: `Consultar análisis ${analyses[0].created_at}`,
      exact: true,
    })
    .click();
  await expect(
    result.getByText(
      'Informe guardado · contexto vigente en la última consulta.',
      { exact: true },
    ),
  ).toBeVisible();
  for (const width of [3440, 1280, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await result.scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await planning.screenshot({
      path: info.outputPath(`v05-aggregate-${width}.png`),
    });
  }
});
