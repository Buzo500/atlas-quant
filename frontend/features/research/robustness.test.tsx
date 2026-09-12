import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import type {
  CandidateRevision,
  LabSummary,
  RobustnessReport,
} from '@/lib/api-types';
import { deferred } from '@/test/fixtures';
import { RobustnessPanel, RobustnessResult } from './robustness';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const call = vi.mocked(api);
const protocol: LabSummary = {
  id: 'a'.repeat(64),
  name: 'Protocolo sintético',
  created_at: '2026-09-12T10:00:00Z',
  policy: 'atlas-lab-temporal-v1',
  instrument_id: 'i',
  listing_id: 'l',
  series_id: 's',
  series_version: 1,
  source_hash: 'source',
  start_date: '2023-01-01',
  holdout_date: '2025-01-01',
  end_date: '2025-03-01',
  opened: false,
  fast: 2,
  slow: 3,
};
const candidate: CandidateRevision = {
  id: 'c:1',
  candidate_id: 'c',
  revision: 1,
  name: 'Hipótesis ficticia',
  hypothesis: 'Una hipótesis de prueba',
  reason: 'Registro explícito',
  status: 'researching',
  created_at: protocol.created_at,
  policy: 'atlas-candidate-research-v1',
  protocol_ids: [protocol.id],
  revision_hash: 'revision',
  evidence: [
    {
      protocol,
      captured_at: protocol.created_at,
      development_hash: 'development',
      development_metrics: [],
      walk_forward_hash: null,
      sensitivity_hash: null,
      holdout_hash: null,
      holdout_metrics: null,
    },
  ],
};
function fixture(): RobustnessReport {
  return {
    id: 'report',
    created_at: protocol.created_at,
    protocol,
    config: {
      initial_cash_eur: '1000',
      fixed_fee_eur: '1',
      fee_bps: '0',
      slippage_bps: '0',
    },
    request: {
      protocol_id: protocol.id,
      candidate_id: 'c',
      revision: 1,
      revision_hash: 'revision',
      related_protocol_ids: [protocol.id],
      reason: 'Consulta sintética justificada',
      acknowledge_exploratory: true,
    },
    metrics: [
      {
        name: 'SMA',
        final_nav_eur: '1100',
        return_pct: '10',
        max_drawdown_pct: '5',
        fees_eur: '8',
        fills: 8,
      },
    ],
    rejected: 1,
    expired: 0,
    trials: [
      {
        protocol_id: protocol.id,
        name: protocol.name,
        development_hash: 'development',
        source_hash: 'source',
        context_hash: 'context',
      },
    ],
    snapshot_hash: 'snapshot',
    python_version: '3.14.4',
    platform: 'Windows-AMD64',
    report_hash: 'report_hash',
    result: {
      policy: 'atlas-robustness-stationary-v1',
      status: 'exploratory',
      reasons: [],
      warnings: ['No autoriza operaciones.'],
      intervals: 504,
      warmup_sessions: 3,
      start_date: '2023-01-04',
      end_date: '2024-05-21',
      work_indices: 7560000,
      mean_excess_pp: '0.03',
      principal_includes_zero: true,
      direction_changes: true,
      lengths: [5, 10, 20].map((length) => ({
        length,
        principal: length === 10,
        seed: String(length),
        replicas: 5000,
        lower_pp: length === 5 ? '0.01' : '-0.01',
        upper_pp: '0.07',
        direction: length === 5 ? 'positive' : 'uncertain',
        indices_hash: 'indices-' + length,
      })),
      nav_hash: 'nav',
      returns_hash: 'returns',
      float_returns_hash: 'float',
      prng: 'PCG64',
      numpy_version: '2.5.2',
      master_seed: 20260911,
      result_hash: 'result',
    },
  };
}
beforeEach(() => call.mockReset());
function fill() {
  fireEvent.change(screen.getByLabelText('Motivo de la consulta estadística'), {
    target: { value: 'Consulta sintética justificada' },
  });
  fireEvent.click(screen.getByRole('checkbox'));
}

it('muestra las tres longitudes, incertidumbre, contexto y limitaciones juntas', () => {
  render(<RobustnessResult report={fixture()} />);
  for (const length of [5, 10, 20])
    expect(
      screen.getByRole('cell', { name: `${length} sesiones` }),
    ).toBeTruthy();
  expect(screen.getByText(/El intervalo principal incluye cero/)).toBeTruthy();
  expect(screen.getByText(/La dirección cambia con la longitud/)).toBeTruthy();
  fireEvent.click(screen.getByText('Contexto económico y ensayos declarados'));
  expect(screen.getByText(/peso configurado No disponible/)).toBeTruthy();
  expect(screen.getByText(/No autoriza operaciones/)).toBeTruthy();
});

it('no inventa cifras para una muestra no evaluable', () => {
  const report = fixture();
  report.result = {
    ...report.result,
    status: 'no_evaluable',
    reasons: ['Muestra inferior a 504 intervalos.'],
    lengths: [],
    mean_excess_pp: null,
    principal_includes_zero: null,
    direction_changes: null,
  };
  render(<RobustnessResult report={report} />);
  expect(screen.getByText('No evaluable')).toBeTruthy();
  expect(screen.getByText('Muestra inferior a 504 intervalos.')).toBeTruthy();
  expect(screen.queryByText(/Media del exceso SMA/)).toBeNull();
});

it('requiere declaración y bloquea dobles envíos con referencia inmutable', async () => {
  const pending = deferred<RobustnessReport>();
  call.mockImplementation(async (_path, body) =>
    body ? pending.promise : { items: [], offset: 0, limit: 20 },
  );
  render(<RobustnessPanel candidate={candidate} onError={vi.fn()} />);
  const form = screen.getByRole('form', { name: 'Calcular robustez' });
  fireEvent.submit(form);
  expect(call.mock.calls.filter(([, body]) => body)).toHaveLength(0);
  fill();
  fireEvent.submit(form);
  fireEvent.submit(form);
  await waitFor(() =>
    expect(call.mock.calls.filter(([, body]) => body)).toHaveLength(1),
  );
  expect(call.mock.calls.find(([, body]) => body)?.[1]).toEqual(
    fixture().request,
  );
  await act(async () => pending.resolve(fixture()));
  expect(
    await screen.findByRole('region', {
      name: 'Informe de robustez estadística',
    }),
  ).toBeTruthy();
});

it('conserva la consulta tras conflicto y no reintenta una escritura', async () => {
  const onError = vi.fn();
  call.mockImplementation(async (_path, body) => {
    if (body) throw new Error('Cambió el contexto.');
    return { items: [], offset: 0, limit: 20 };
  });
  render(<RobustnessPanel candidate={candidate} onError={onError} />);
  fill();
  fireEvent.submit(screen.getByRole('form', { name: 'Calcular robustez' }));
  await waitFor(() =>
    expect(onError).toHaveBeenCalledWith('Cambió el contexto.'),
  );
  expect(
    (
      screen.getByLabelText(
        'Motivo de la consulta estadística',
      ) as HTMLTextAreaElement
    ).value,
  ).toBe('Consulta sintética justificada');
  expect(call.mock.calls.filter(([, body]) => body)).toHaveLength(1);
});

it('recupera el informe guardado y señala una reproducción discrepante', async () => {
  call.mockImplementation(async (_path, body) =>
    body
      ? { matches: false, warnings: ['Entorno diferente.'] }
      : { items: [fixture()], offset: 0, limit: 20 },
  );
  render(<RobustnessPanel candidate={candidate} onError={vi.fn()} />);
  fireEvent.click(
    await screen.findByRole('button', { name: /Consultar robustez/ }),
  );
  fireEvent.click(
    screen.getByRole('button', { name: 'Comprobar reproducción estadística' }),
  );
  expect(
    await screen.findByText(/La reproducción no coincide.*Entorno diferente/),
  ).toBeTruthy();
  expect(call.mock.calls.filter(([, body]) => body)).toEqual([
    ['/lab/robustness/report/reproduce', {}],
  ]);
});

it('una respuesta tardía de otra candidata no aparece tras cambiar la revisión', async () => {
  const pending = deferred<RobustnessReport>();
  call.mockImplementation(async (_path, body) =>
    body ? pending.promise : { items: [], offset: 0, limit: 20 },
  );
  const { rerender } = render(
    <RobustnessPanel key="first" candidate={candidate} onError={vi.fn()} />,
  );
  fill();
  fireEvent.submit(screen.getByRole('form', { name: 'Calcular robustez' }));
  rerender(
    <RobustnessPanel
      key="second"
      candidate={{ ...candidate, candidate_id: 'second' }}
      onError={vi.fn()}
    />,
  );
  await act(async () => pending.resolve(fixture()));
  expect(
    screen.queryByRole('region', { name: 'Informe de robustez estadística' }),
  ).toBeNull();
  expect(
    (
      screen.getByLabelText(
        'Motivo de la consulta estadística',
      ) as HTMLTextAreaElement
    ).value,
  ).toBe('');
});
