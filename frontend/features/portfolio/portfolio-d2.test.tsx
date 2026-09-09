import { render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi, beforeEach } from 'vitest';
import { api } from '@/lib/api';
import { PortfolioPanel } from './portfolio-panel';
import { dataset, portfolioResponse } from '@/test/fixtures';
import type { PortfolioDetail } from '@/lib/api-types';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
vi.mock('@/components/atlas/curve', () => ({ Curve: () => <div>Curva</div> }));
const request = vi.mocked(api);
const props = {
  active: true,
  connected: true,
  stateLoaded: true,
  busy: false,
  onImport: vi.fn(),
  onDemo: vi.fn(async () => {}),
  portfolioId: 'book',
  portfolioRevision: 2,
};
const detail = (): PortfolioDetail => ({
  portfolio: {
    id: 'book',
    name: 'Mi cartera',
    account_id: 'local',
    revision: 2,
    catalog_revision: 1,
    legacy_dataset_id: 'a',
    base_currency: 'EUR',
    accounting_policy: 'legacy-eur-v1',
    event_ids: [],
    bindings: [],
  },
  context: {
    portfolio_id: 'book',
    portfolio_revision: 2,
    catalog_revision: 1,
    accounting_policy: 'legacy-eur-v1',
    bindings: [],
    data_hash: 'a'.repeat(64),
  },
  status: 'available',
  warnings: [],
  entries: [],
  value: {
    ...portfolioResponse(),
    positions: portfolioResponse().positions.map((p) => ({
      ...p,
      listing_id: 'listing',
    })),
  },
});
beforeEach(() => request.mockReset());

it('conserva la cartera elegida al cambiar el conjunto de investigación', async () => {
  request.mockResolvedValue(detail());
  const view = render(<PortfolioPanel {...props} dataset={dataset('a')} />);
  await screen.findByRole('heading', { name: 'Posiciones' });
  view.rerender(<PortfolioPanel {...props} dataset={dataset('b', 3)} />);
  await waitFor(() => expect(request).toHaveBeenCalledTimes(1));
  expect(request.mock.calls[0][0]).toBe('/portfolios/book');
  expect(screen.getByRole('heading', { name: 'Posiciones' })).not.toBeNull();
});

it('muestra valoración no disponible sin presentar saldos cero ni libro vacío', async () => {
  request.mockResolvedValue({
    ...detail(),
    status: 'unavailable',
    value: null,
    warnings: ['Falta precio confirmado.'],
  });
  render(<PortfolioPanel {...props} dataset={dataset()} />);
  await screen.findByText(/Falta precio confirmado/);
  expect(
    screen.queryByRole('heading', { name: 'Importa tus movimientos' }),
  ).toBeNull();
  expect(screen.getAllByText('—')).toHaveLength(4);
});
