import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import type { PerformanceReport } from '@/lib/api-types';
import { NativePerformance, PerformanceDetails } from './native-performance';
import { PortfolioPanel } from './portfolio-panel';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
vi.mock('@/components/atlas/curve', () => ({
  Curve: () => <div>Curva de patrimonio</div>,
}));
vi.mock('@/features/data/book-panel', () => ({ BookSummary: () => null }));
vi.mock('@/features/data/corporate-panel', () => ({
  CorporateSummary: () => null,
}));
const call = vi.mocked(api);
const unavailable = {
  value: null,
  status: 'unavailable' as const,
  reasons: ['missing_flow_fx'],
};
const report: PerformanceReport = {
  id: 'report',
  portfolio_id: 'p',
  portfolio_revision: 1,
  context_hash: 'a'.repeat(64),
  created_at: '2026-01-06T12:00:00Z',
  current: true,
  saved: false,
  policy: 'atlas-performance-v1',
  start_date: '2026-01-05',
  end_date: '2026-01-06',
  initial_nav: '0.00',
  final_nav: '900.00',
  external_net: unavailable,
  pnl: { ...unavailable, display_value: null },
  twr: {
    ...unavailable,
    convention: 'daily-external-flows-at-close',
    start_date: null,
    end_date: '2026-01-06',
    segments: [],
  },
  mwr: {
    ...unavailable,
    convention: 'actual-days/365',
    domain: ['-0.999999', '1000'],
    iterations: 0,
    bracket_width: null,
    normalized_residual: null,
    rate_tolerance: '1e-10',
    residual_tolerance: '1e-10',
    max_iterations: 200,
  },
  costs: [],
  costs_eur: { value: '0', status: 'complete', reasons: [] },
  flows: [],
  points: [
    {
      date: '2026-01-05',
      nav: null,
      nav_exact: null,
      flow_eur: null,
      status: 'incomplete',
      twr_factor: null,
      historical_known: false,
      reasons: ['missing_fx'],
    },
  ],
  unlinked_payments: [],
  historical_known: false,
  source_context: {
    portfolio_id: 'p',
    portfolio_revision: 1,
    catalog_revision: 0,
    corporate_revision: 0,
    bindings: [],
    fx_binding: null,
    price_heads: [],
    fx_head: null,
  },
};
beforeEach(() => {
  call.mockReset();
  call.mockImplementation(async (path, body) =>
    body
      ? { report, preview_token: 'token', committed: false }
      : String(path).endsWith('/report')
        ? report
        : { reports: [], offset: 0, limit: 20 },
  );
});

it('keeps unavailable rates absent and explains why instead of showing zero', () => {
  render(<PerformanceDetails report={report} />);
  expect(screen.getAllByText('No disponible').length).toBeGreaterThan(1);
  expect(screen.queryByText('0,00 %')).toBeNull();
  expect(
    screen.getAllByText(/Falta FX para convertir un flujo externo/).length,
  ).toBeGreaterThan(0);
  expect(screen.queryByText('Curva de patrimonio')).toBeNull();
});

it('changing period invalidates its confirmation without writing', async () => {
  render(<NativePerformance portfolioId="p" revision={1} active />);
  fireEvent.change(screen.getByLabelText('Cierre inicial del periodo'), {
    target: { value: '2026-01-05' },
  });
  fireEvent.change(screen.getByLabelText('Cierre final del periodo'), {
    target: { value: '2026-01-06' },
  });
  fireEvent.click(
    screen.getByRole('button', { name: 'Calcular rentabilidad' }),
  );
  await waitFor(() =>
    expect(
      screen.queryByRole('button', { name: 'Guardar informe de rentabilidad' }),
    ).not.toBeNull(),
  );
  fireEvent.change(screen.getByLabelText('Cierre inicial del periodo'), {
    target: { value: '2026-01-04' },
  });
  expect(
    screen.queryByRole('button', { name: 'Guardar informe de rentabilidad' }),
  ).toBeNull();
  expect(call.mock.calls.filter(([, body]) => body)).toHaveLength(1);
});

it('a late calculation does not restore the confirmation after changing dates', async () => {
  let finish: (value: unknown) => void = () => {};
  call.mockImplementation(async (_path, body) =>
    body
      ? new Promise((resolve) => {
          finish = resolve;
        })
      : { reports: [], offset: 0, limit: 20 },
  );
  render(<NativePerformance portfolioId="p" revision={1} active />);
  fireEvent.change(screen.getByLabelText('Cierre inicial del periodo'), {
    target: { value: '2026-01-05' },
  });
  fireEvent.change(screen.getByLabelText('Cierre final del periodo'), {
    target: { value: '2026-01-06' },
  });
  fireEvent.click(
    screen.getByRole('button', { name: 'Calcular rentabilidad' }),
  );
  fireEvent.change(screen.getByLabelText('Cierre inicial del periodo'), {
    target: { value: '2026-01-04' },
  });
  finish({ report, preview_token: 'stale', committed: false });
  await waitFor(() =>
    expect(
      screen.queryByText('Calculando y comprobando el contexto…'),
    ).toBeNull(),
  );
  expect(
    screen.queryByRole('button', { name: 'Guardar informe de rentabilidad' }),
  ).toBeNull();
});

it('preserves saved historical qualification without presenting it as current', () => {
  render(
    <PerformanceDetails report={{ ...report, current: false, saved: true }} />,
  );
  expect(
    screen.getByText(/Informe histórico: el contexto ha cambiado/),
  ).not.toBeNull();
  expect(screen.getByText(/este informe no acredita/i)).not.toBeNull();
});

it('an audit refresh preserves the reviewed period and sends its frozen confirmation', async () => {
  call.mockImplementation(async (path, body) => {
    if (path === '/portfolios/p')
      return {
        portfolio: { accounting_policy: 'atlas-accounting-v2', revision: 1 },
        context: { portfolio_revision: 1 },
        value: null,
        status: 'unavailable',
        warnings: [],
      };
    if (body) return { report, preview_token: 'token', committed: false };
    return String(path).includes('/valuations')
      ? { cuts: [] }
      : { reports: [] };
  });
  const props = {
    dataset: undefined,
    portfolioId: 'p',
    portfolioRevision: 1,
    active: true,
    connected: true,
    stateLoaded: true,
    busy: false,
    onImport: vi.fn(),
    onDemo: vi.fn(async () => {}),
  };
  const view = render(<PortfolioPanel {...props} auditSequence={10} />);
  fireEvent.change(await screen.findByLabelText('Cierre inicial del periodo'), {
    target: { value: '2026-01-05' },
  });
  fireEvent.change(screen.getByLabelText('Cierre final del periodo'), {
    target: { value: '2026-01-06' },
  });
  fireEvent.click(
    screen.getByRole('button', { name: 'Calcular rentabilidad' }),
  );
  await screen.findByRole('button', {
    name: 'Guardar informe de rentabilidad',
  });
  view.rerender(<PortfolioPanel {...props} auditSequence={11} />);
  await waitFor(() =>
    expect(call.mock.calls.filter(([p]) => p === '/portfolios/p')).toHaveLength(
      2,
    ),
  );
  expect(
    (screen.getByLabelText('Cierre inicial del periodo') as HTMLInputElement)
      .value,
  ).toBe('2026-01-05');
  fireEvent.click(
    screen.getByRole('button', { name: 'Guardar informe de rentabilidad' }),
  );
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith('/v2/portfolios/p/performance', {
      start_date: '2026-01-05',
      end_date: '2026-01-06',
      expected_revision: 1,
      commit: true,
      preview_token: 'token',
    }),
  );
});

it('a changed portfolio revision discards the old confirmation', async () => {
  let revision = 1;
  call.mockImplementation(async (path, body) => {
    if (path === '/portfolios/p')
      return {
        portfolio: { accounting_policy: 'atlas-accounting-v2', revision },
        context: { portfolio_revision: revision },
        value: null,
        status: 'unavailable',
        warnings: [],
      };
    if (body) return { report, preview_token: 'token', committed: false };
    return String(path).includes('/valuations')
      ? { cuts: [] }
      : { reports: [] };
  });
  const props = {
    dataset: undefined,
    portfolioId: 'p',
    active: true,
    connected: true,
    stateLoaded: true,
    busy: false,
    onImport: vi.fn(),
    onDemo: vi.fn(async () => {}),
  };
  const view = render(
    <PortfolioPanel
      {...props}
      portfolioRevision={revision}
      auditSequence={10}
    />,
  );
  fireEvent.change(await screen.findByLabelText('Cierre inicial del periodo'), {
    target: { value: '2026-01-05' },
  });
  fireEvent.change(screen.getByLabelText('Cierre final del periodo'), {
    target: { value: '2026-01-06' },
  });
  fireEvent.click(
    screen.getByRole('button', { name: 'Calcular rentabilidad' }),
  );
  await screen.findByRole('button', {
    name: 'Guardar informe de rentabilidad',
  });
  revision = 2;
  view.rerender(
    <PortfolioPanel
      {...props}
      portfolioRevision={revision}
      auditSequence={11}
    />,
  );
  await waitFor(() =>
    expect(
      screen.queryByRole('button', { name: 'Guardar informe de rentabilidad' }),
    ).toBeNull(),
  );
  expect(call.mock.calls.filter(([, body]) => body)).toHaveLength(1);
});

it('a rejected context clears confirmation and never retries a write', async () => {
  call.mockImplementation(async (_path, body) => {
    if (body && (body as { commit?: boolean }).commit)
      throw new Error('El contexto ha cambiado. Vuelve a calcular.');
    return body
      ? { report, preview_token: 'token', committed: false }
      : { reports: [] };
  });
  render(<NativePerformance portfolioId="p" revision={1} active />);
  fireEvent.change(screen.getByLabelText('Cierre inicial del periodo'), {
    target: { value: '2026-01-05' },
  });
  fireEvent.change(screen.getByLabelText('Cierre final del periodo'), {
    target: { value: '2026-01-06' },
  });
  fireEvent.click(
    screen.getByRole('button', { name: 'Calcular rentabilidad' }),
  );
  fireEvent.click(
    await screen.findByRole('button', {
      name: 'Guardar informe de rentabilidad',
    }),
  );
  await screen.findByText('El contexto ha cambiado. Vuelve a calcular.');
  expect(
    screen.queryByRole('button', { name: 'Guardar informe de rentabilidad' }),
  ).toBeNull();
  expect(
    call.mock.calls.filter(
      ([, body]) => body && (body as { commit?: boolean }).commit,
    ),
  ).toHaveLength(1);
});
