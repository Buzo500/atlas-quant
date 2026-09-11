import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import type { LabReport, LabSummary } from '@/lib/api-types';
import { deferred } from '@/test/fixtures';
import { SimulationLab } from './simulation-lab';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
vi.mock('@/components/atlas/curve', () => ({ Curve: () => <div>Curva</div> }));
const call = vi.mocked(api);
const summary = (id: string): LabSummary => ({
  id,
  name: 'Protocolo ' + id,
  created_at: '2025-01-15',
  policy: 'atlas-lab-temporal-v1',
  instrument_id: 'i',
  listing_id: 'l',
  series_id: 's',
  series_version: 1,
  source_hash: 'a'.repeat(64),
  start_date: '2025-01-01',
  holdout_date: '2025-01-08',
  end_date: '2025-01-14',
  opened: false,
  fast: 2,
  slow: 3,
});
const report = (id: string): LabReport => ({
  protocol: summary(id),
  config: { initial_cash_eur: '1000' },
  development: {
    start_date: '2025-01-01',
    end_date: '2025-01-07',
    sessions: 7,
    curve: [],
    metrics: [],
    trades: [],
    rejected: 0,
    expired: 0,
    report_hash: 'h',
  },
  holdout: null,
  warnings: ['Simulación aislada'],
  evidence_hash: 'e',
});
beforeEach(() => {
  call.mockReset();
});
function defaults(path: string) {
  if (path === '/v2/market') return { series: [] };
  if (path.startsWith('/lab/protocols?'))
    return { items: [summary('a'), summary('b')], offset: 0, limit: 20 };
  return report(path.endsWith('/a') ? 'a' : 'b');
}

it('mantiene la reserva cerrada hasta una confirmación explícita y no duplica la apertura', async () => {
  const pending = deferred<LabReport>();
  call.mockImplementation(async (path) =>
    path.endsWith('/holdout') ? pending.promise : defaults(path),
  );
  render(<SimulationLab onError={vi.fn()} />);
  fireEvent.click(
    await screen.findByRole('button', { name: 'Ver Protocolo a' }),
  );
  const button = await screen.findByRole('button', {
    name: 'Abrir prueba final',
  });
  expect(button.hasAttribute('disabled')).toBe(true);
  fireEvent.click(
    screen.getByLabelText(
      'Entiendo que abrir la prueba final consume su reserva',
    ),
  );
  fireEvent.click(button);
  fireEvent.click(button);
  await waitFor(() =>
    expect(
      call.mock.calls.filter(([p]) => p.endsWith('/holdout')),
    ).toHaveLength(1),
  );
  expect(call).toHaveBeenCalledWith('/lab/protocols/a/holdout', {
    protocol_hash: 'a',
    acknowledge_exposure: true,
  });
  expect(
    screen
      .getByRole('button', { name: 'Ver Protocolo b' })
      .hasAttribute('disabled'),
  ).toBe(true);
  await act(async () =>
    pending.resolve({ ...report('a'), holdout: report('a').development }),
  );
  expect(
    await screen.findByRole('region', { name: 'Resultado de la prueba final' }),
  ).toBeTruthy();
});

it('ignora una lectura tardía de otro protocolo', async () => {
  const old = deferred<LabReport>();
  call.mockImplementation(async (path) =>
    path === '/lab/protocols/a' ? old.promise : defaults(path),
  );
  render(<SimulationLab onError={vi.fn()} />);
  fireEvent.click(
    await screen.findByRole('button', { name: 'Ver Protocolo a' }),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Ver Protocolo b' }));
  await screen.findByRole('heading', { name: 'Protocolo b' });
  await act(async () => old.resolve(report('a')));
  expect(screen.queryByRole('heading', { name: 'Protocolo a' })).toBeNull();
});

it('presenta un fallo de apertura sin revelar resultados ni reintentar la mutación', async () => {
  const onError = vi.fn();
  call.mockImplementation(async (path) => {
    if (path.endsWith('/holdout')) throw new Error('Periodo ya calculado');
    return defaults(path);
  });
  render(<SimulationLab onError={onError} />);
  fireEvent.click(
    await screen.findByRole('button', { name: 'Ver Protocolo a' }),
  );
  fireEvent.click(
    await screen.findByLabelText(
      'Entiendo que abrir la prueba final consume su reserva',
    ),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Abrir prueba final' }));
  await waitFor(() =>
    expect(onError).toHaveBeenCalledWith('Periodo ya calculado'),
  );
  expect(
    screen.queryByRole('region', { name: 'Resultado de la prueba final' }),
  ).toBeNull();
  expect(call.mock.calls.filter(([p]) => p.endsWith('/holdout'))).toHaveLength(
    1,
  );
});

it('no confirma reproducción si el walk-forward guardado falta o diverge', async () => {
  const stored = {
    ...report('a'),
    walk_forward: {
      policy: 'atlas-walk-forward-fixed-v1',
      config: { context_sessions: 7, evaluation_sessions: 7 },
      windows: [],
      summary: {
        status: 'insufficient_data',
        windows: 0,
        evaluable_windows: 0,
        passing_windows: 0,
        passing_pct: '0',
        mean_return_pct: null,
        mean_excess_pct: null,
        worst_drawdown_pct: null,
        reasons: [],
      },
      unused_sessions: 0,
      unused_start: null,
      unused_end: null,
      warnings: [],
      report_hash: 'wf-hash',
    },
  };
  call.mockImplementation(async (path) =>
    path.endsWith('/reproduce')
      ? {
          id: 'a',
          development_matches: true,
          holdout_matches: null,
          walk_forward_matches: false,
        }
      : path === '/lab/protocols/a'
        ? stored
        : defaults(path),
  );
  render(<SimulationLab onError={vi.fn()} />);
  fireEvent.click(
    await screen.findByRole('button', { name: 'Ver Protocolo a' }),
  );
  fireEvent.click(
    await screen.findByRole('button', { name: 'Comprobar reproducción' }),
  );
  expect(await screen.findByText(/La reproducción no coincide/)).toBeTruthy();
  expect(call.mock.calls.filter(([p]) => p.endsWith('/holdout'))).toHaveLength(
    0,
  );
});
