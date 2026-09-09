import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import { dataset } from '@/test/fixtures';
import type { QualityReport } from '@/lib/api-types';
import { QualityPanel } from './quality-panel';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const request = vi.mocked(api);
const result: QualityReport = {
  policy: 'quality-v1',
  dataset_id: 'a',
  dataset_version: 1,
  symbol: 'A',
  start: '2026-01-01',
  end: '2026-09-07',
  evidence_hash: 'a'.repeat(64),
  calendar_name: null,
  calendar_verified: false,
  calendar_source: null,
  price_basis: 'unknown',
  basis_verified: false,
  capabilities: {
    draw: 'allowed',
    valuation: 'provisional',
    exploratory: 'provisional',
    historical: 'blocked',
    paper: 'blocked',
  },
  counts: { calendar_unknown: 250 },
  total_days: 250,
  offset: 0,
  days: [],
  last: {
    date: '2026-09-07',
    status: 'calendar_unknown',
    price_date: '2026-09-07',
    age_days: 0,
    price: 100,
    valuation: 'provisional',
    reasons: ['availability_unknown'],
  },
  warnings: [],
};
const props = {
  dataset: dataset(),
  active: true,
  refresh: vi.fn(async () => {}),
  onError: vi.fn(),
};
beforeEach(() => {
  request.mockReset();
  props.refresh.mockClear();
  props.onError.mockClear();
});

it('explica disponibilidad desconocida sin presentar investigación acreditada', async () => {
  request.mockResolvedValue(result);
  render(<QualityPanel {...props} />);
  await screen.findByText('Disponibilidad histórica desconocida');
  expect(
    screen.getByRole('row', {
      name: 'Investigación acreditada al cierre No apta',
    }),
  ).not.toBeNull();
  expect(
    screen.getByRole('row', { name: 'Investigación exploratoria Provisional' }),
  ).not.toBeNull();
});

it('editar la evidencia invalida la confirmación y no escribe', async () => {
  request.mockImplementation(async (_path, body) =>
    body
      ? {
          dataset_id: 'a',
          version: 1,
          committed: false,
          preview_token: 'b'.repeat(64),
          quality: result,
        }
      : result,
  );
  const user = userEvent.setup();
  render(<QualityPanel {...props} />);
  await screen.findByText('Disponibilidad histórica desconocida');
  await user.click(screen.getByText('Documentar calendario y base de precios'));
  await user.click(
    screen.getByRole('button', { name: 'Previsualizar evidencia' }),
  );
  await screen.findByRole('button', { name: 'Confirmar evidencia' });
  fireEvent.change(
    screen.getByLabelText('Fuente del calendario', { exact: true }),
    { target: { value: 'Fuente corregida' } },
  );
  expect(
    screen.queryByRole('button', { name: 'Confirmar evidencia' }),
  ).toBeNull();
  expect(
    request.mock.calls.filter(
      ([, body]) =>
        body &&
        typeof body === 'object' &&
        'commit' in body &&
        body.commit === true,
    ),
  ).toHaveLength(0);
});

it('un conflicto de confirmación exige nueva previsualización', async () => {
  request.mockImplementation(async (_path, body) => {
    if (body && typeof body === 'object' && 'commit' in body && body.commit)
      throw new Error('La versión ha cambiado.');
    return body
      ? {
          dataset_id: 'a',
          version: 1,
          committed: false,
          preview_token: 'b'.repeat(64),
          quality: result,
        }
      : result;
  });
  const user = userEvent.setup();
  render(<QualityPanel {...props} />);
  await user.click(screen.getByText('Documentar calendario y base de precios'));
  await user.click(
    screen.getByRole('button', { name: 'Previsualizar evidencia' }),
  );
  await user.click(
    await screen.findByRole('button', { name: 'Confirmar evidencia' }),
  );
  await waitFor(() =>
    expect(props.onError).toHaveBeenLastCalledWith('La versión ha cambiado.'),
  );
  expect(
    screen.queryByRole('button', { name: 'Confirmar evidencia' }),
  ).toBeNull();
  expect(props.refresh).not.toHaveBeenCalled();
});
