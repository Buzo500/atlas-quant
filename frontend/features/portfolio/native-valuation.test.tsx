import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import type { ValuationCut, MarketSeries } from '@/lib/api-types';
import { NativeValuation, ValuationDetails } from './native-valuation';
import { ExactBalance } from '@/features/data/book-panel';
import { MarketWorkspace } from '@/features/data/market-workspace';
import { PortfolioPanel } from './portfolio-panel';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
vi.mock('@/features/data/book-panel', async (original) => ({
  ...(await original<typeof import('@/features/data/book-panel')>()),
  BookSummary: () => null,
}));
vi.mock('@/features/data/corporate-panel', () => ({
  CorporateSummary: () => null,
}));
const request = vi.mocked(api);
const cut: ValuationCut = {
  id: 'cut',
  portfolio_id: 'p',
  portfolio_revision: 1,
  catalog_revision: 1,
  corporate_revision: 0,
  context_hash: 'a'.repeat(64),
  policy: 'atlas-nav-v1',
  mode: 'reconstruction_at_close',
  as_of_date: '2026-01-05',
  decision_at: '2026-01-05T23:59:59Z',
  created_at: '2026-01-06T00:00:00Z',
  current: true,
  saved: false,
  status: 'incomplete',
  value: null,
  exact_value: null,
  known_subtotal: '500.00',
  rounding_difference: '0.00',
  balance: {
    as_of_date: '2026-01-05',
    balances: [
      {
        currency: 'EUR',
        cash: '500.00',
        net_contributions: '500.00',
        realized_pnl: '0',
      },
      {
        currency: 'USD',
        cash: '100.00',
        net_contributions: '100.00',
        realized_pnl: '0',
      },
    ],
    positions: [],
    warnings: [],
  },
  components: [],
  flows: [],
  reasons: ['missing_fx'],
  historical_known: false,
  historical_reasons: ['reconstruction_incomplete'],
};
const series: MarketSeries = {
  id: 'fx',
  kind: 'fx',
  name: 'FX ficticio',
  source: 'Fuente ficticia',
  version: 1,
  listing_id: null,
  symbol: 'USD_EUR',
  currency: 'USD',
  format_id: 'atlas-fx-v1',
  sha256: 'a'.repeat(64),
  date_min: '2026-01-05',
  date_max: '2026-01-05',
  row_count: 1,
  received_at: '2026-01-06T00:00:00Z',
  price_basis: 'unknown',
  basis_verified: false,
  calendar_verified: false,
};

beforeEach(() => request.mockReset());

it('el sondeo de auditoría conserva la fecha y la previsualización de patrimonio', async () => {
  request.mockImplementation(async (path, body) => {
    if (path === '/portfolios/p')
      return {
        portfolio: { accounting_policy: 'atlas-accounting-v2', revision: 1 },
        context: { portfolio_revision: 1 },
        value: null,
        status: 'unavailable',
        warnings: [],
      };
    if (body) return { cut, preview_token: 'token', committed: false };
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
  fireEvent.change(await screen.findByLabelText('Fecha de valoración'), {
    target: { value: '2026-01-05' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Calcular patrimonio' }));
  await screen.findByRole('button', { name: 'Guardar corte de patrimonio' });
  view.rerender(<PortfolioPanel {...props} auditSequence={11} />);
  await waitFor(() =>
    expect(
      request.mock.calls.filter(([p]) => p === '/portfolios/p'),
    ).toHaveLength(2),
  );
  expect(
    (screen.getByLabelText('Fecha de valoración') as HTMLInputElement).value,
  ).toBe('2026-01-05');
  fireEvent.click(
    screen.getByRole('button', { name: 'Guardar corte de patrimonio' }),
  );
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith('/v2/portfolios/p/valuations', {
      as_of_date: '2026-01-05',
      expected_revision: 1,
      commit: true,
      preview_token: 'token',
    }),
  );
});

it('distingue patrimonio incompleto de su subtotal conocido sin inventar cero', () => {
  render(<ValuationDetails cut={cut} />);
  expect(screen.getByText('No disponible')).not.toBeNull();
  expect(screen.getByText('500.00 EUR')).not.toBeNull();
  expect(
    screen.getByText(/El subtotal conocido no es el patrimonio total/),
  ).not.toBeNull();
  expect(screen.getByText(/Falta un tipo de cambio válido/)).not.toBeNull();
  expect(screen.queryByText('0.00 EUR')).toBeNull();
});

it('mantiene separado cada saldo y muestra su moneda', () => {
  render(<ExactBalance value={cut.balance} />);
  expect(screen.getByText('Efectivo: 500.00 EUR')).not.toBeNull();
  expect(screen.getByText('Efectivo: 100.00 USD')).not.toBeNull();
  expect(screen.queryByText('Efectivo: 600.00 EUR')).toBeNull();
});

it('editar la fecha descarta la previsualización y no guarda un corte antiguo', async () => {
  request.mockImplementation(async (_path, body) =>
    body
      ? { cut, preview_token: 'b'.repeat(64), committed: false }
      : { cuts: [], offset: 0, limit: 20 },
  );
  render(<NativeValuation portfolioId="p" revision={1} active />);
  fireEvent.click(screen.getByRole('button', { name: 'Calcular patrimonio' }));
  await screen.findByRole('button', { name: 'Guardar corte de patrimonio' });
  fireEvent.change(screen.getByLabelText('Fecha de valoración'), {
    target: { value: '2026-01-06' },
  });
  expect(
    screen.queryByRole('button', { name: 'Guardar corte de patrimonio' }),
  ).toBeNull();
  expect(request.mock.calls.filter(([, body]) => body)).toHaveLength(1);
});

it('el cambio de cotización o evidencia invalida una importación FX revisada', async () => {
  const onError = vi.fn();
  request.mockImplementation(async (_path, body) =>
    body
      ? {
          series,
          added: 1,
          changed: 0,
          affected_portfolios: [],
          committed: false,
          preview_token: 'c'.repeat(64),
        }
      : { series: [] },
  );
  render(
    <MarketWorkspace
      catalog={{ revision: 0, instruments: [], listings: [], aliases: [] }}
      active
      refresh={async () => {}}
      onError={onError}
    />,
  );
  fireEvent.click(
    screen.getByRole('button', { name: 'Importar FX USD → EUR' }),
  );
  fireEvent.change(screen.getByLabelText('Nombre de la serie'), {
    target: { value: 'FX ficticio' },
  });
  fireEvent.change(screen.getByLabelText('Fuente de la serie'), {
    target: { value: 'Fuente ficticia' },
  });
  fireEvent.change(
    screen.getByLabelText('CSV de observaciones', { exact: true }),
    {
      target: {
        value:
          'date,from_currency,to_currency,rate,available_at\n2026-01-05,USD,EUR,0.9,\n',
      },
    },
  );
  fireEvent.click(screen.getByRole('button', { name: 'Previsualizar serie' }));
  await screen.findByRole('button', { name: 'Confirmar serie' });
  const call = request.mock.calls.find(
    ([path, body]) => path === '/v2/market/fx/imports' && !!body,
  );
  expect(call?.[1]).toMatchObject({
    listing_id: null,
    expected_version: 0,
    evidence: { calendar_verified: false, basis_verified: false },
  });
  fireEvent.change(screen.getByLabelText('Fuente de la serie'), {
    target: { value: 'Otra fuente' },
  });
  await waitFor(() =>
    expect(
      screen.queryByRole('button', { name: 'Confirmar serie' }),
    ).toBeNull(),
  );
  expect(request.mock.calls.filter(([, body]) => body)).toHaveLength(1);
});
