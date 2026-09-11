import type { Page } from '@playwright/test';
import { test, expect, readApi, select } from './fixtures';
import type {
  CatalogResponse,
  MarketPreview,
  LabHistory,
  LabReport,
  CandidateHistory,
  CandidateRevision,
  CandidateRevisions,
} from '../lib/api-types';
import reference from '../../docs/fixtures/v0_6_walk_forward_reference.json' with { type: 'json' };

async function post<T>(page: Page, path: string, data: unknown): Promise<T> {
  const response = await page.request.post('/api' + path, {
    headers: { 'X-Atlas-Client': 'local-v1' },
    data,
  });
  expect(response.ok(), await response.text()).toBe(true);
  return response.json();
}

test('v0.6 sensibilidad y candidatas: costes, descarte, evidencia e historial', async ({
  page,
}) => {
  let catalog = await readApi<CatalogResponse>(page, '/api/catalog');
  catalog = await post(page, '/catalog/instruments', {
    expected_revision: catalog.revision,
    name: 'Activo ficticio sensibilidad',
    source: 'Fixture sintético v0.6',
  });
  const instrument = catalog.instruments.find(
    (i) => i.name === 'Activo ficticio sensibilidad',
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
  const body = {
    ...reference.market,
    name: 'Sensibilidad ficticia EUR',
    listing_id: listing.id,
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
  await page.goto('/?tab=lab');
  await page
    .getByText('Simulación SMA con protocolo temporal', { exact: true })
    .click();
  await select(
    page,
    'Versión CSV nativa EUR',
    'Sensibilidad ficticia EUR · v1',
  );
  const p = {
    ...reference.protocol,
    name: 'Sensibilidad y registro ficticios',
  };
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
    ['Comisión fija EUR', '1'],
    ['Comisión proporcional (pb)', '0'],
    ['Deslizamiento (pb)', '0'],
  ])
    await form.getByLabel(label, { exact: true }).fill(value);
  await page
    .getByLabel(
      'He revisado la evidencia y la ausencia de eventos corporativos en el periodo',
    )
    .check();
  await form.getByLabel('Añadir validación walk-forward').check();
  await form.getByLabel('Sesiones de contexto', { exact: true }).fill('7');
  await form.getByLabel('Sesiones por evaluación', { exact: true }).fill('7');
  await form.getByLabel('Añadir análisis de sensibilidad').check();
  await form.getByLabel('Ventanas lentas alternativas').fill('4, 5');
  await page
    .getByRole('button', { name: 'Congelar y simular desarrollo' })
    .click();
  const development = page.getByRole('region', {
    name: 'Resultado de desarrollo',
    exact: true,
  });
  await expect(development).toBeVisible();
  const walkForward = page.getByRole('region', {
    name: 'Resultado walk-forward',
    exact: true,
  });
  await expect(walkForward).toBeVisible();
  const sensitivity = page.getByRole('region', {
    name: 'Resultado de sensibilidad',
    exact: true,
  });
  await expect(sensitivity).toBeVisible();
  await expect(
    sensitivity.getByRole('cell', { name: 'Costes × 2', exact: true }),
  ).toBeVisible();
  await sensitivity.getByText('Detalle: Costes × 2', { exact: true }).click();
  await expect(
    sensitivity.getByText('Comisión fija 2 EUR', { exact: false }),
  ).toBeVisible();
  await form.getByLabel('Sesiones de contexto', { exact: true }).fill('100');
  await expect(walkForward.getByText(/Contexto: 7 sesiones/)).toBeVisible();
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
  await page.reload();
  await page
    .getByText('Simulación SMA con protocolo temporal', { exact: true })
    .click();
  await page
    .getByRole('button', { name: `Ver ${p.name}`, exact: true })
    .click();
  await expect(
    page.getByRole('region', {
      name: 'Resultado walk-forward',
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Comprobar reproducción' }).click();
  await expect(
    page.getByText('Reproducción correcta: coincide con el informe guardado.'),
  ).toBeVisible();
  const report = await readApi<LabReport>(page, `/api/lab/protocols/${id}`);
  expect(report.holdout).toBeNull();
  expect(report.protocol.opened).toBe(false);
  expect(report.walk_forward!.windows).toHaveLength(reference.expected_windows);
  expect(report.sensitivity!.cases).toHaveLength(4);
  expect(report.sensitivity!.cases.map((c) => c.label)).toEqual([
    'base',
    'slow:4',
    'slow:5',
    'cost:2',
  ]);
  expect(
    report.sensitivity!.cases.every(
      (c) => c.result.end_date < report.protocol.holdout_date,
    ),
  ).toBe(true);
  await page
    .getByText('Hipótesis y candidatas de investigación', { exact: true })
    .click();
  const registry = page.getByRole('region', {
    name: 'Registro de candidatas',
    exact: true,
  });
  await registry
    .getByRole('button', { name: 'Nueva candidata', exact: true })
    .click();
  await registry
    .getByLabel('Nombre de la candidata')
    .fill('Hipótesis sintética de tendencia');
  await registry
    .getByLabel('Hipótesis', { exact: true })
    .fill('Un cruce de medias podría filtrar tendencias persistentes.');
  await registry
    .getByLabel('Motivo y limitaciones de esta revisión')
    .fill(
      'Registrar la evidencia ficticia; no es un preregistro ni datos observados.',
    );
  await registry.getByLabel(p.name, { exact: false }).check();
  await registry
    .getByRole('button', { name: 'Registrar candidata', exact: true })
    .click();
  await expect(
    registry.getByRole('heading', {
      name: 'Hipótesis sintética de tendencia · revisión 1',
    }),
  ).toBeVisible();
  await registry
    .getByRole('button', { name: 'Revisar candidata', exact: true })
    .click();
  await expect(registry.getByLabel(p.name, { exact: false })).toBeDisabled();
  await select(page, 'Estado de investigación', 'Descartada');
  await registry
    .getByLabel('Motivo y limitaciones de esta revisión')
    .fill('Se descarta esta hipótesis ficticia por resultados insuficientes.');
  await registry
    .getByRole('button', { name: 'Guardar nueva revisión' })
    .click();
  await expect(
    registry.getByRole('heading', {
      name: 'Hipótesis sintética de tendencia · revisión 2',
    }),
  ).toBeVisible();
  const candidates = await readApi<CandidateHistory>(
    page,
    '/api/lab/candidates',
  );
  const candidateId = candidates.items.find(
    (c) => c.name === 'Hipótesis sintética de tendencia',
  )!.id;
  const candidate = await readApi<CandidateRevision>(
    page,
    `/api/lab/candidates/${candidateId}`,
  );
  expect(candidate.status).toBe('discarded');
  expect(candidate.evidence[0].sensitivity_hash).toBe(
    report.sensitivity!.report_hash,
  );
  expect(candidate.evidence[0].holdout_hash).toBeNull();
  const revisions = await readApi<CandidateRevisions>(
    page,
    `/api/lab/candidates/${candidateId}/revisions`,
  );
  expect(revisions.items.map((r) => r.status)).toEqual([
    'discarded',
    'researching',
  ]);
  await page.reload();
  await page
    .getByText('Hipótesis y candidatas de investigación', { exact: true })
    .click();
  await registry
    .getByRole('button', {
      name: 'Ver candidata Hipótesis sintética de tendencia',
    })
    .click();
  await registry.getByText('Revisiones conservadas', { exact: true }).click();
  await registry
    .getByText('Revisión 1 · En investigación', { exact: true })
    .click();
  await expect(
    registry.getByText(
      'Registrar la evidencia ficticia; no es un preregistro ni datos observados.',
      { exact: false },
    ),
  ).toBeVisible();
  for (const width of [1366, 3440, 960]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
  }
  expect(
    (await readApi<LabReport>(page, `/api/lab/protocols/${id}`)).holdout,
  ).toBeNull();
});
