import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import { CorporatePanel } from '@/features/data/corporate-panel';
import type {
  CatalogResponse,
  CorporateCatalog,
  CorporateEvent,
  CorporatePortfolio,
  PortfolioRecord,
} from '@/lib/api-types';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const event: CorporateEvent = {
  id: 'event',
  revision: 1,
  listing_id: 'listing',
  event_type: 'dividend',
  effective_date: '2026-01-10',
  payment_date: '2026-01-20',
  available_at: null,
  gross_per_unit: '0.50',
  currency: 'EUR',
  ratio_numerator: null,
  ratio_denominator: null,
  source_reference: 'Fixture',
  verified: true,
  evidence: 'Fixture verificada',
  cancelled: false,
  created_at: '2026-01-10T00:00:00Z',
  reason: 'Importación',
};
const events: CorporateCatalog = {
  revision: 2,
  catalog_revision: 2,
  events: [event],
  sources: [],
  total: 1,
  offset: 0,
  limit: 100,
};
const catalog: CatalogResponse = {
  revision: 2,
  instruments: [],
  listings: [],
  aliases: [],
};
const portfolio: PortfolioRecord = {
  id: 'portfolio',
  name: 'Fixture',
  account_id: 'account',
  base_currency: 'EUR',
  accounting_policy: 'atlas-accounting-v2',
  legacy_dataset_id: null,
  revision: 2,
  catalog_revision: 2,
  event_ids: [],
  bindings: [],
};
const empty: CorporatePortfolio = {
  portfolio_id: 'portfolio',
  portfolio_revision: 2,
  corporate_revision: 2,
  as_of_date: '2026-01-20',
  applications: [],
  balance: {
    as_of_date: '2026-01-20',
    currency: 'EUR',
    cash: '9900.00',
    net_contributions: '10000.00',
    realized_pnl: '0.00',
    positions: [],
    warnings: [],
  },
  pending_receivables: '0.00',
  unlinked_payments: [],
  warnings: [],
  total: 0,
  offset: 0,
  limit: 100,
};
const right: CorporatePortfolio = {
  ...empty,
  portfolio_revision: 3,
  pending_receivables: '50.00',
  total: 1,
  applications: [
    {
      event_id: event.id,
      event_revision: 1,
      revision: 1,
      portfolio_revision: 3,
      source: 'Fixture D5',
      source_account: 'Cuenta D5',
      event_type: 'dividend',
      effective_date: '2026-01-10',
      day_sequence: 10,
      eligible_quantity: '100',
      basis_quantity: '100',
      gross_amount: '50.00',
      movement_key: null,
      movement_fingerprint: null,
      basis_hash: 'hash',
      cancelled: false,
      evidence: 'Fixture',
      discrepancy_reason: '',
      gross_explanation: '',
      fraction_evidence: '',
      event_snapshot: event,
      current: true,
      status: 'pending_payment',
      receivable: '50.00',
      price_status: 'not_applicable',
      warnings: [],
    },
  ],
};

it.each(['portfolio-first', 'rights-first', 'portfolio-only'] as const)(
  'el cobro usa los derechos de su revisión y conserva el borrador: %s',
  async (order) => {
    const user = userEvent.setup();
    let latest = empty;
    let release!: (value: CorporatePortfolio) => void;
    let delayed: Promise<CorporatePortfolio> | null = null;
    const deferRights = () => {
      delayed = new Promise((resolve) => {
        release = resolve;
      });
    };
    const finishRights = async () => {
      await act(async () => {
        latest = right;
        delayed = null;
        release(right);
      });
    };
    const request = vi.mocked(api);
    request.mockImplementation(async (path, body) => {
      if (body)
        return {
          ...right,
          balance: { ...right.balance, cash: '9940.00' },
          committed: false,
          preview_token: 'a'.repeat(64),
          document_id: 'doc',
        };
      if (path.startsWith('/corporate-events?')) return events;
      if (path.startsWith('/corporate-events/event/versions/')) return event;
      if (path.includes('/corporate-actions?')) return delayed ?? latest;
      if (path.includes('/corporate-documents'))
        return { documents: [], total: 0, offset: 0, limit: 100 };
      throw new Error(`Ruta no prevista: ${path}`);
    });
    const onError = vi.fn();
    const props = {
      catalog,
      portfolio,
      active: true,
      revision: 1,
      refresh: async () => {},
      onError,
    };
    const view = render(<CorporatePanel {...props} />);
    await user.click(
      await screen.findByRole('button', { name: 'Seleccionar evento' }),
    );
    await screen.findByLabelText('Cantidad elegible acreditada');
    deferRights();
    view.rerender(
      <CorporatePanel
        {...props}
        portfolio={
          order === 'rights-first' ? portfolio : { ...portfolio, revision: 3 }
        }
        revision={order === 'portfolio-only' ? 1 : 2}
      />,
    );
    await waitFor(() =>
      expect(
        request.mock.calls.filter(([path]) =>
          path.includes('/corporate-actions?'),
        ).length,
      ).toBeGreaterThan(1),
    );
    if (order === 'rights-first') {
      await finishRights();
      expect(
        screen.queryByLabelText('Cantidad elegible acreditada'),
      ).toBeNull();
      view.rerender(
        <CorporatePanel
          {...props}
          portfolio={{ ...portfolio, revision: 3 }}
          revision={2}
        />,
      );
    } else {
      expect(
        screen.queryByLabelText('Cantidad elegible acreditada'),
      ).toBeNull();
      await finishRights();
    }
    await screen.findByText('Derechos pendientes: 50.00 EUR');
    const quantity = screen.getByLabelText<HTMLInputElement>(
      'Cantidad elegible acreditada',
    );
    const source = screen.getByLabelText<HTMLInputElement>(
      'Fuente del movimiento',
    );
    const account = screen.getByLabelText<HTMLInputElement>(
      'Cuenta de origen del movimiento',
    );
    expect(quantity.value).toBe('100');
    expect(source.value).toBe('Fixture D5');
    expect(account.value).toBe('Cuenta D5');
    await user.click(
      screen.getByRole('combobox', { name: 'Acción en la cartera' }),
    );
    await user.click(
      screen.getByRole('option', { name: 'Crear cobro revisado' }),
    );
    for (const [label, value] of Object.entries({
      'Evidencia de elegibilidad y orden': 'Evidencia nueva',
      'ID externo del nuevo movimiento': 'payment',
      'Bruto del cobro EUR': '50',
      'Retención del cobro EUR': '9.5',
      'Comisión del cobro EUR': '0.5',
    })) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    }
    // A harmless refresh of the same revision must not erase an edited draft.
    const readsBeforeRefresh = request.mock.calls.filter(([path]) =>
      path.includes('/corporate-actions?'),
    ).length;
    deferRights();
    view.rerender(
      <CorporatePanel
        {...props}
        portfolio={{ ...portfolio, revision: 3 }}
        revision={3}
      />,
    );
    await waitFor(() =>
      expect(
        request.mock.calls.filter(([path]) =>
          path.includes('/corporate-actions?'),
        ).length,
      ).toBeGreaterThan(readsBeforeRefresh),
    );
    expect(
      screen.getByLabelText<HTMLInputElement>(
        'Evidencia de elegibilidad y orden',
      ).value,
    ).toBe('Evidencia nueva');
    await finishRights();
    expect(
      screen.getByLabelText<HTMLInputElement>(
        'Evidencia de elegibilidad y orden',
      ).value,
    ).toBe('Evidencia nueva');
    expect(
      screen.getByLabelText<HTMLInputElement>('Bruto del cobro EUR').value,
    ).toBe('50');
    await user.click(
      screen.getByRole('button', { name: 'Previsualizar aplicación' }),
    );
    const preview = await screen.findByRole('region', {
      name: 'Previsualización de aplicación',
    });
    expect(
      within(preview).getByText(/Efectivo del libro: 9940.00 EUR/),
    ).toBeTruthy();
    expect(request.mock.calls.filter(([, body]) => !!body)).toHaveLength(1);
    expect(request.mock.calls.find(([, body]) => !!body)?.[1]).toMatchObject({
      expected_revision: 3,
      source: 'Fixture D5',
      source_account: 'Cuenta D5',
      review: { eligible_quantity: '100' },
    });
    expect(onError.mock.calls.filter(([message]) => !!message)).toEqual([]);
  },
);
