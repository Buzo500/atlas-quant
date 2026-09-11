import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import type { AssetAnalysisReport, AssetSource } from '@/lib/api-types';
import {
  AssetAnalysisEditor,
  AssetAnalysisPanel,
} from './asset-analysis-panel';
import { AssetAnalysisResults } from './asset-analysis-results';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
vi.mock('@/shared/ui', async (original) => ({
  ...(await original<typeof import('@/shared/ui')>()),
  Choice: ({
    label,
    value,
    options,
    onChange,
  }: {
    label: string;
    value: string;
    options: { value: string; label: string }[];
    onChange: (v: string) => void;
  }) => (
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="" aria-label="Sin selección" />
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  ),
}));
const call = vi.mocked(api);
const source: AssetSource = {
  key: 'a',
  ref: { kind: 'native', id: 'a', version: 1, symbol: 'A' },
  name: 'Activo A',
  dataset_name: 'Precios A',
  source: 'Fixture',
  instrument_id: 'a',
  instrument_type: 'equity',
  listing_id: 'a',
  market: 'TEST',
  currency: 'USD',
  sha256: 'a'.repeat(64),
  date_min: '2026-01-01',
  date_max: '2026-01-03',
  row_count: 3,
};
const fx = {
  ref: { id: 'fx', version: 1 },
  name: 'Cambio',
  source: 'Fixture',
  sha256: 'b'.repeat(64),
  date_min: source.date_min,
  date_max: source.date_max,
};
const report: AssetAnalysisReport = {
  id: 'report',
  created_at: '2026-01-04T00:00:00Z',
  policy: 'atlas-asset-analysis-v1',
  context_hash: 'c'.repeat(64),
  catalog_revision: 1,
  corporate_revision: 0,
  saved: false,
  current: true,
  inputs: {
    sources: [source.ref],
    start_date: source.date_min,
    end_date: source.date_max,
    fx: fx.ref,
  },
  result: {
    profiles: [
      {
        source,
        status: 'unavailable',
        reasons: ['missing_same_date_fx'],
        expected_sessions: 3,
        observed_sessions: 3,
        valid_sessions: 0,
        valid_intervals: 0,
        first_date: source.date_min,
        last_date: source.date_max,
        last_close_native: '100',
        last_close_eur: null,
        price_change_pct: null,
        session_volatility_pct: null,
        annualized_volatility_pct: null,
        max_drawdown_pct: null,
        historical_known: false,
        known_dividends: 0,
      },
    ],
    comparison: {
      start_date: null,
      end_date: null,
      rows: [],
      points: [],
      reasons: ['insufficient_common_dates'],
    },
    correlations: {
      method: 'pearson-simple-returns',
      minimum_observations: 20,
      observations: 0,
      intervals: [],
      cells: [
        {
          left: 'a',
          right: 'a',
          value: null,
          reason: 'insufficient_common_intervals',
        },
      ],
      reasons: [],
    },
    fx,
    currency: 'EUR',
    basis: 'raw-price-excluding-dividends',
    annualization_sessions: 252,
    warnings: [],
  },
};
let catalogFx = fx;
let catalogSources = [source];
const props = {
  active: true,
  refresh: vi.fn(async () => {}),
  onError: vi.fn(),
};
beforeEach(() => {
  call.mockReset();
  catalogFx = fx;
  catalogSources = [source];
  props.onError.mockClear();
  call.mockImplementation(async (path, body) => {
    if (body) return { report, preview_token: 'token', committed: false };
    if (path.endsWith('/sources'))
      return { sources: catalogSources, fx: [catalogFx], limit: 500 };
    return { reports: [], offset: 0, limit: 20 };
  });
});
async function choose() {
  await screen.findByRole('option', { name: /Activo A/ });
  fireEvent.change(screen.getByLabelText('Activo y fuente para comparar'), {
    target: { value: 'a' },
  });
  fireEvent.click(
    screen.getByRole('button', { name: 'Añadir activo a la comparación' }),
  );
}
it('distinguishes same-name sources and preserves both selected identities', async () => {
  catalogSources = [
    source,
    { ...source, key: 'b', ref: { ...source.ref, id: 'b' } },
  ];
  render(<AssetAnalysisEditor {...props} />);
  const first = await screen.findByRole('option', {
    name: 'Activo A · Precios A · USD · v1 · a',
  });
  const second = screen.getByRole('option', {
    name: 'Activo A · Precios A · USD · v1 · b',
  });
  expect(first.textContent).not.toBe(second.textContent);
  for (const value of ['a', 'b']) {
    fireEvent.change(screen.getByLabelText('Activo y fuente para comparar'), {
      target: { value },
    });
    fireEvent.click(
      screen.getByRole('button', { name: 'Añadir activo a la comparación' }),
    );
  }
  fireEvent.change(screen.getByLabelText('Fuente EUR por USD para comparar'), {
    target: { value: 'fx:1' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Calcular comparación' }));
  await screen.findByRole('button', { name: 'Guardar comparación' });
  expect(call.mock.calls.find(([, body]) => body)?.[1]).toMatchObject({
    sources: [source.ref, { ...source.ref, id: 'b' }],
  });
});
async function preview() {
  await choose();
  fireEvent.change(screen.getByLabelText('Fuente EUR por USD para comparar'), {
    target: { value: 'fx:1' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Calcular comparación' }));
  await screen.findByRole('button', { name: 'Guardar comparación' });
}
it('loads only after opening, preserves selection when collapsed', async () => {
  render(<AssetAnalysisPanel {...props} />);
  expect(call).not.toHaveBeenCalled();
  const details = screen
    .getByText('Abrir comparador de activos')
    .closest('details')!;
  details.open = true;
  fireEvent(details, new Event('toggle'));
  await choose();
  details.open = false;
  fireEvent(details, new Event('toggle'));
  details.open = true;
  fireEvent(details, new Event('toggle'));
  expect(screen.getByLabelText('Inicio de comparación')).toHaveProperty(
    'value',
    '2026-01-01',
  );
});
it('requires explicit FX and sends immutable source versions', async () => {
  render(<AssetAnalysisEditor {...props} />);
  await choose();
  expect(
    screen.getByRole('button', { name: 'Calcular comparación' }),
  ).toHaveProperty('disabled', true);
  fireEvent.change(screen.getByLabelText('Fuente EUR por USD para comparar'), {
    target: { value: 'fx:1' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Calcular comparación' }));
  await screen.findByRole('button', { name: 'Guardar comparación' });
  expect(call.mock.calls.find(([, body]) => body)?.[1]).toEqual({
    sources: [source.ref],
    start_date: source.date_min,
    end_date: source.date_max,
    fx: fx.ref,
  });
});
it('editing dates invalidates an existing confirmation', async () => {
  render(<AssetAnalysisEditor {...props} />);
  await preview();
  fireEvent.change(screen.getByLabelText('Inicio de comparación'), {
    target: { value: '2026-01-02' },
  });
  expect(
    screen.queryByRole('button', { name: 'Guardar comparación' }),
  ).toBeNull();
  expect(
    screen.queryByRole('region', { name: 'Resultado del comparador' }),
  ).toBeNull();
});
it('a revised FX source blocks the old preview without reposting', async () => {
  const { rerender } = render(<AssetAnalysisEditor {...props} revision={1} />);
  await preview();
  catalogFx = { ...fx, ref: { ...fx.ref, version: 2 } };
  rerender(<AssetAnalysisEditor {...props} revision={2} />);
  await screen.findByText(/Una fuente ha cambiado/);
  expect(
    screen.queryByRole('button', { name: 'Guardar comparación' }),
  ).toBeNull();
  expect(call.mock.calls.filter(([, body]) => body)).toHaveLength(1);
});
it('a conflict clears the preview and never retries the mutation', async () => {
  render(<AssetAnalysisEditor {...props} />);
  await preview();
  call.mockImplementationOnce(async () => {
    throw new Error('Las fuentes han cambiado');
  });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar comparación' }));
  await waitFor(() =>
    expect(props.onError).toHaveBeenCalledWith('Las fuentes han cambiado'),
  );
  expect(
    screen.queryByRole('button', { name: 'Guardar comparación' }),
  ).toBeNull();
  expect(call.mock.calls.filter(([, body]) => body)).toHaveLength(2);
});
it('unavailable statistics display explanations and never numeric zero', () => {
  render(<AssetAnalysisResults report={report} />);
  expect(
    screen.getByText('Falta un cambio válido de la misma fecha.'),
  ).toBeTruthy();
  expect(
    screen.getByText('Se necesitan al menos 20 intervalos comunes.'),
  ).toBeTruthy();
  expect(screen.queryByText('0 %')).toBeNull();
  expect(
    screen.getByText(/excluye dividendos, costes e impuestos/),
  ).toBeTruthy();
});
