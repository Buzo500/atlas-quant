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
  CandidateComparison,
  CandidateRevision,
  SourcePreflight,
} from '@/lib/api-types';
import { deferred } from '@/test/fixtures';
import { CandidateBrowser } from './candidate-browser';
import { SourcePrevalidation } from './source-preflight';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const call = vi.mocked(api);
beforeEach(() => {
  call.mockReset();
});
const revision = (id: string): CandidateRevision => ({
  id: id + ':1',
  candidate_id: id,
  revision: 1,
  name: 'Candidata ' + id,
  hypothesis: 'Hipótesis de investigación',
  reason: 'Descarte conservado con sus limitaciones',
  status: 'discarded',
  created_at: '2026-09-11T10:00:00Z',
  policy: 'atlas-candidate-research-v1',
  protocol_ids: [],
  evidence: [],
  revision_hash: 'h' + id,
});
const preflight = (id: string): SourcePreflight => ({
  series_id: id,
  series_version: 1,
  rows: 14,
  source_hash: 'h',
  corporate_revision: 0,
  start: '2025-01-01',
  end: '2025-01-14',
  context_hash: 'h',
  checks: [
    { code: 'basis', status: 'block', message: 'Falta evidencia ' + id },
  ],
});

it('prevalida explícitamente y descarta la respuesta de una versión anterior', async () => {
  const old = deferred<SourcePreflight>();
  call.mockImplementation(async (path) =>
    path.includes('series_id=a') ? old.promise : preflight('b'),
  );
  const view = render(<SourcePrevalidation key="a" id="a" version={1} />);
  expect(call).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole('button', { name: 'Prevalidar CSV antes de configurar' }),
  );
  await waitFor(() => expect(call).toHaveBeenCalledTimes(1));
  view.rerender(<SourcePrevalidation key="b" id="b" version={1} />);
  fireEvent.click(
    screen.getByRole('button', { name: 'Prevalidar CSV antes de configurar' }),
  );
  expect(await screen.findByText('Falta evidencia b')).toBeTruthy();
  await act(async () => old.resolve(preflight('a')));
  expect(screen.queryByText('Falta evidencia a')).toBeNull();
  expect(call.mock.calls.every(([, body]) => body === undefined)).toBe(true);
});

it('un error de prevalidación no muestra una certificación positiva', async () => {
  call.mockRejectedValue(new Error('Versión no encontrada'));
  render(<SourcePrevalidation id="a" version={1} />);
  fireEvent.click(
    screen.getByRole('button', { name: 'Prevalidar CSV antes de configurar' }),
  );
  expect((await screen.findByRole('alert')).textContent).toContain(
    'Versión no encontrada',
  );
  expect(screen.queryByText('Revisión del protocolo pendiente')).toBeNull();
});

it('busca al enviar y conserva revisiones seleccionadas entre consultas', async () => {
  call.mockImplementation(async (path) => ({
    items: [revision(path.includes('q=otra') ? 'b' : 'a')],
    offset: 0,
    limit: 20,
  }));
  render(<CandidateBrowser onError={vi.fn()} />);
  await waitFor(() => expect(call).toHaveBeenCalled());
  expect(
    new URL(call.mock.calls[0][0], 'http://atlas.local').searchParams.has(
      'status',
    ),
  ).toBe(false);
  fireEvent.click(
    await screen.findByRole('checkbox', {
      name: 'Comparar Candidata a revisión 1',
    }),
  );
  const calls = call.mock.calls.length;
  fireEvent.change(screen.getByLabelText('Texto de búsqueda'), {
    target: { value: 'otra' },
  });
  expect(call).toHaveBeenCalledTimes(calls);
  fireEvent.click(screen.getByRole('button', { name: 'Buscar revisiones' }));
  fireEvent.click(
    await screen.findByRole('checkbox', {
      name: 'Comparar Candidata b revisión 1',
    }),
  );
  expect(
    screen.getByRole('button', { name: 'Quitar Candidata a r1' }),
  ).toBeTruthy();
  expect(
    screen.getByRole('button', { name: 'Comparar revisiones seleccionadas' }),
  ).toHaveProperty('disabled', false);
});

it('congela las referencias, evita doble comparación y limpia el resultado al cambiar selección', async () => {
  const pending = deferred<CandidateComparison>();
  call.mockImplementation(async (path, body) =>
    body
      ? pending.promise
      : { items: [revision('a'), revision('b')], offset: 0, limit: 20 },
  );
  render(<CandidateBrowser onError={vi.fn()} />);
  for (const id of ['a', 'b'])
    fireEvent.click(
      await screen.findByRole('checkbox', {
        name: `Comparar Candidata ${id} revisión 1`,
      }),
    );
  const button = screen.getByRole('button', {
    name: 'Comparar revisiones seleccionadas',
  });
  fireEvent.click(button);
  fireEvent.click(button);
  expect(
    screen.getByRole('checkbox', { name: 'Comparar Candidata a revisión 1' }),
  ).toHaveProperty('disabled', true);
  expect(call.mock.calls.filter(([, b]) => b)).toHaveLength(1);
  expect(call.mock.calls.find(([, b]) => b)?.[1]).toEqual({
    items: [
      { candidate_id: 'a', revision: 1 },
      { candidate_id: 'b', revision: 1 },
    ],
  });
  await act(async () =>
    pending.resolve({
      items: [revision('a'), revision('b')],
      contexts: [],
      same_context: false,
      warnings: ['Sin evidencia suficiente'],
      comparison_hash: 'hash',
    }),
  );
  expect(
    await screen.findByText('Contextos distintos o evidencia insuficiente'),
  ).toBeTruthy();
  fireEvent.click(
    screen.getByRole('button', { name: 'Quitar Candidata a r1' }),
  );
  expect(
    screen.queryByRole('region', { name: 'Comparación de revisiones' }),
  ).toBeNull();
});

it('una comparación fallida conserva selección sin reintentar', async () => {
  const onError = vi.fn();
  call.mockImplementation(async (path, body) => {
    if (body) throw new Error('Evidencia no coincide');
    return { items: [revision('a'), revision('b')], offset: 0, limit: 20 };
  });
  render(<CandidateBrowser onError={onError} />);
  for (const id of ['a', 'b'])
    fireEvent.click(
      await screen.findByRole('checkbox', {
        name: `Comparar Candidata ${id} revisión 1`,
      }),
    );
  fireEvent.click(
    screen.getByRole('button', { name: 'Comparar revisiones seleccionadas' }),
  );
  await waitFor(() =>
    expect(onError).toHaveBeenCalledWith('Evidencia no coincide'),
  );
  expect(
    screen.getByRole('button', { name: 'Quitar Candidata a r1' }),
  ).toBeTruthy();
  expect(call.mock.calls.filter(([, b]) => b)).toHaveLength(1);
});
