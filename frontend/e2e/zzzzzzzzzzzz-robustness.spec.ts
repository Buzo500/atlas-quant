import type { Page } from '@playwright/test';
import { test, expect, readApi } from './fixtures';
import type {
  CatalogResponse,
  MarketPreview,
  LabReport,
  CandidateRevision,
  RobustnessHistory,
} from '../lib/api-types';

async function post<T>(page: Page, path: string, data: unknown): Promise<T> {
  const response = await page.request.post('/api' + path, {
    headers: { 'X-Atlas-Client': 'local-v1' },
    data,
  });
  expect(response.ok(), await response.text()).toBe(true);
  return response.json();
}

test('v0.6 robustez: tres intervalos, evidencia inmutable y reserva intacta', async ({
  page,
}, testInfo) => {
  let catalog = await readApi<CatalogResponse>(page, '/api/catalog');
  catalog = await post(page, '/catalog/instruments', {
    expected_revision: catalog.revision,
    name: 'Robustez ficticia',
    source: 'Escenario sintético E2E',
  });
  const instrument = catalog.instruments.find(
    (i) => i.name === 'Robustez ficticia',
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
  const days = Array.from({ length: 514 }, (_, i) =>
    new Date(Date.UTC(2023, 0, 1 + i)).toISOString().slice(0, 10),
  );
  const rows = days.map(
    (d, i) =>
      `${d},ASSET,100,${100 + (i % 11)},100,${100 + (i % 11)},100,EUR,${d}T17:01:00Z`,
  );
  const market = {
    name: 'Robustez sintética EUR',
    listing_id: listing.id,
    source: 'Escenario sintético sin eventos; no datos observados',
    csv:
      'date,listing_ref,open,high,low,close,volume,currency,available_at\n' +
      rows.join('\n'),
    evidence: {
      symbol: 'ASSET',
      calendar_name: 'Ficticio diario',
      market: 'TEST',
      timezone: 'UTC',
      calendar_source: 'Calendario sintético sin festivos',
      calendar_verified: true,
      calendar_csv:
        'date,status,close_at\n' +
        days.map((d) => `${d},open,${d}T17:00:00Z`).join('\n'),
      price_basis: 'raw',
      basis_verified: true,
      basis_source: 'Bruto sintético',
    },
  };
  const preview = await post<MarketPreview>(
    page,
    '/v2/market/prices/imports',
    market,
  );
  const committed = await post<MarketPreview>(
    page,
    '/v2/market/prices/imports',
    { ...market, commit: true, preview_token: preview.preview_token },
  );
  const lab = await post<LabReport>(page, '/lab/protocols', {
    name: `Robustez sintética ${'Referencia'.repeat(8)}`,
    series_id: committed.series!.id,
    series_version: committed.series!.version,
    start_date: days[0],
    holdout_date: days[507],
    end_date: days[513],
    fast: 2,
    slow: 3,
    sessions_csv:
      'date,open_at,close_at,open_available_at\n' +
      days
        .map((d) => `${d},${d}T09:00:00Z,${d}T17:00:00Z,${d}T09:00:00Z`)
        .join('\n'),
    opening_source: 'Aperturas sintéticas disponibles al abrir',
    event_free_source: 'Escenario sintético sin eventos',
    evidence_reviewed: true,
    config: {
      initial_cash_eur: '1000',
      fixed_fee_eur: '1',
      fee_bps: '0',
      slippage_bps: '0',
    },
  });
  const candidate = await post<CandidateRevision>(page, '/lab/candidates', {
    name: 'Hipótesis de robustez sintética',
    hypothesis: 'Evaluar la incertidumbre con datos sintéticos',
    reason: 'Todos los ensayos sintéticos vinculados; no evidencia observada',
    protocol_ids: [lab.protocol.id],
  });
  async function openPanel() {
    await page.goto('/?tab=lab');
    await page
      .getByText('Hipótesis y candidatas de investigación', { exact: true })
      .click();
    await page
      .getByRole('button', {
        name: 'Ver candidata Hipótesis de robustez sintética',
        exact: true,
      })
      .click();
    await page
      .getByText('Robustez estadística del desarrollo', { exact: true })
      .click();
  }
  await openPanel();
  const panel = page.getByRole('region', {
    name: 'Robustez estadística',
    exact: true,
  });
  await panel
    .getByLabel('Motivo de la consulta estadística')
    .fill('Medir incertidumbre sobre el desarrollo ficticio completo');
  await expect(
    panel.getByRole('button', { name: 'Calcular y guardar robustez' }),
  ).toBeDisabled();
  await panel.getByRole('checkbox').check();
  await panel
    .getByRole('button', { name: 'Calcular y guardar robustez' })
    .click();
  const report = page.getByRole('region', {
    name: 'Informe de robustez estadística',
    exact: true,
  });
  await expect(report).toBeVisible();
  for (const length of [5, 10, 20])
    await expect(
      report.getByRole('cell', { name: `${length} sesiones`, exact: true }),
    ).toBeVisible();
  await expect(
    report.getByText(/504 intervalos posteriores a 3 sesiones/),
  ).toBeVisible();
  await report
    .getByText('Contexto económico y ensayos declarados', { exact: true })
    .click();
  await report.getByText('Método y reproducción', { exact: true }).click();
  const historyEntry = panel.getByRole('button', {
    name: /Consultar robustez/,
  });
  for (const width of [565, 960, 1366, 3440]) {
    await page.setViewportSize({ width, height: width === 3440 ? 1440 : 900 });
    const layout = await page.evaluate(() => ({
      fits: document.documentElement.scrollWidth <= window.innerWidth + 1,
      overflowing: [...document.querySelectorAll('body *')]
        .filter((el) => {
          if (el.getBoundingClientRect().right <= window.innerWidth + 1)
            return false;
          for (
            let parent = el.parentElement;
            parent;
            parent = parent.parentElement
          ) {
            if (
              ['auto', 'scroll', 'hidden', 'clip'].includes(
                getComputedStyle(parent).overflowX,
              )
            )
              return false;
          }
          return true;
        })
        .slice(0, 12)
        .map((el) => ({
          tag: el.tagName,
          className: el.className,
          text: el.textContent?.slice(0, 80),
        })),
    }));
    expect(layout.fits, JSON.stringify(layout.overflowing)).toBe(true);
    const bounds = await historyEntry.evaluate((button) => {
      const rect = button.getBoundingClientRect();
      const parent = button.parentElement!.getBoundingClientRect();
      return {
        contained:
          rect.left >= parent.left - 1 && rect.right <= parent.right + 1,
        contentFits:
          button.scrollHeight <= button.clientHeight + 1 &&
          button.scrollWidth <= button.clientWidth + 1,
      };
    });
    expect(bounds).toEqual({ contained: true, contentFits: true });
    await historyEntry.focus();
    await expect(historyEntry).toBeFocused();
    await historyEntry.press('Enter');
    await expect(report.getByText(/504 intervalos posteriores/)).toBeVisible();
    await historyEntry.screenshot({
      path: testInfo.outputPath(`robustness-history-${width}.png`),
    });
    await report.screenshot({
      path: testInfo.outputPath(`robustness-${width}.png`),
    });
  }
  const history = await readApi<RobustnessHistory>(
    page,
    `/api/lab/robustness?candidate_id=${candidate.candidate_id}`,
  );
  expect(history.items).toHaveLength(1);
  expect(history.items[0].result.status).toBe('exploratory');
  await page.reload();
  await openPanel();
  await panel.getByRole('button', { name: /Consultar robustez/ }).click();
  await expect(report.getByText(/504 intervalos posteriores/)).toBeVisible();
  await panel
    .getByRole('button', { name: 'Comprobar reproducción estadística' })
    .click();
  await expect(
    panel.getByText(
      'Reproducción coincidente: instantánea y resultado conservados.',
      { exact: false },
    ),
  ).toBeVisible();
  expect(
    await readApi<RobustnessHistory>(
      page,
      `/api/lab/robustness?candidate_id=${candidate.candidate_id}`,
    ),
  ).toEqual(history);
  expect(
    await readApi<LabReport>(page, `/api/lab/protocols/${lab.protocol.id}`),
  ).toEqual(lab);
  expect(
    await readApi<CandidateRevision>(
      page,
      `/api/lab/candidates/${candidate.candidate_id}`,
    ),
  ).toEqual(candidate);
});
