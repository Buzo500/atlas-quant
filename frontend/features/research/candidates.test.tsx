import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import type { CandidateRevision } from '@/lib/api-types';
import { deferred } from '@/test/fixtures';
import { Candidates } from './candidates';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const call = vi.mocked(api);
const revision = (id: string): CandidateRevision => ({
  id: id + ':1',
  candidate_id: id,
  revision: 1,
  name: 'Candidata ' + id,
  hypothesis: 'Hipótesis inicial de tendencias.',
  reason: 'Pendiente de evidencia observada.',
  status: 'researching',
  created_at: '2026-01-01T23:30:00.123456+00:00',
  policy: 'atlas-candidate-research-v1',
  protocol_ids: ['p'],
  evidence: [],
  revision_hash: 'hash-' + id,
});
function defaults(path: string) {
  if (path.startsWith('/lab/protocols?'))
    return {
      items: [
        {
          id: 'p',
          name: 'Protocolo conservado',
          fast: 2,
          slow: 3,
          opened: false,
        },
      ],
      offset: 0,
      limit: 20,
    };
  if (path.startsWith('/lab/candidates?'))
    return {
      items: ['a', 'b'].map((id) => ({
        id,
        name: 'Candidata ' + id,
        revision: 1,
        status: 'researching',
        protocols: 1,
      })),
      offset: 0,
      limit: 20,
    };
  if (path.includes('/revisions?'))
    return {
      items: [revision(path.includes('/a/') ? 'a' : 'b')],
      offset: 0,
      limit: 20,
    };
  return revision(path.endsWith('/a') ? 'a' : 'b');
}
beforeEach(() => {
  call.mockReset();
});

it('conserva el borrador y la revisión esperada ante un conflicto sin reintentar', async () => {
  const onError = vi.fn();
  call.mockImplementation(async (path, body) => {
    if (body)
      throw new Error('La candidata cambió. Consulta su revisión actual.');
    return defaults(path);
  });
  render(<Candidates onError={onError} />);
  fireEvent.click(
    await screen.findByRole('button', { name: 'Ver candidata Candidata a' }),
  );
  fireEvent.click(
    await screen.findByRole('button', { name: 'Revisar candidata' }),
  );
  const reason = screen.getByLabelText(
    'Motivo y limitaciones de esta revisión',
  );
  fireEvent.change(reason, {
    target: { value: 'El descarte se mantiene por evidencia insuficiente.' },
  });
  expect(
    (await screen.findByLabelText(/Protocolo conservado/)).hasAttribute(
      'disabled',
    ),
  ).toBe(true);
  expect(
    screen
      .getByRole('button', { name: 'Actualizar candidatas' })
      .hasAttribute('disabled'),
  ).toBe(true);
  fireEvent.submit(screen.getByRole('form', { name: 'Revisar candidata' }));
  await waitFor(() =>
    expect(onError).toHaveBeenCalledWith(
      expect.stringContaining('La candidata cambió'),
    ),
  );
  expect((reason as HTMLTextAreaElement).value).toContain(
    'El descarte se mantiene',
  );
  const writes = call.mock.calls.filter(([, body]) => body !== undefined);
  expect(writes).toHaveLength(1);
  expect(writes[0]).toEqual([
    '/lab/candidates/a/revisions',
    expect.objectContaining({ expected_revision: 1, protocol_ids: ['p'] }),
  ]);
});

it('bloquea envíos repetidos y cambios de candidata durante el guardado', async () => {
  const pending = deferred<CandidateRevision>();
  call.mockImplementation(async (path, body) =>
    body ? pending.promise : defaults(path),
  );
  render(<Candidates onError={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Nueva candidata' }));
  fireEvent.change(screen.getByLabelText('Nombre de la candidata'), {
    target: { value: 'Candidata nueva' },
  });
  fireEvent.change(screen.getByLabelText('Hipótesis'), {
    target: { value: 'Hipótesis de tendencias persistentes.' },
  });
  fireEvent.change(
    screen.getByLabelText('Motivo y limitaciones de esta revisión'),
    { target: { value: 'Registrar antes de calcular.' } },
  );
  const form = screen.getByRole('form', { name: 'Nueva candidata' });
  fireEvent.submit(form);
  fireEvent.submit(form);
  await waitFor(() =>
    expect(
      call.mock.calls.filter(([, body]) => body !== undefined),
    ).toHaveLength(1),
  );
  expect(
    screen
      .getByRole('button', { name: 'Cancelar edición' })
      .hasAttribute('disabled'),
  ).toBe(true);
  await act(async () =>
    pending.resolve({ ...revision('c'), name: 'Candidata nueva' }),
  );
  expect(
    await screen.findByRole('heading', {
      name: 'Candidata nueva · revisión 1',
    }),
  ).toBeTruthy();
});

it('ignora la evidencia de una candidata cuya lectura llegó tarde', async () => {
  const late = deferred<CandidateRevision>();
  call.mockImplementation(async (path) =>
    path === '/lab/candidates/a' ? late.promise : defaults(path),
  );
  render(<Candidates onError={vi.fn()} />);
  fireEvent.click(
    await screen.findByRole('button', { name: 'Ver candidata Candidata a' }),
  );
  fireEvent.click(
    screen.getByRole('button', { name: 'Ver candidata Candidata b' }),
  );
  await screen.findAllByRole('heading', { name: 'Candidata b · revisión 1' });
  expect(screen.getAllByText(/02\/01\/2026, 00:30:00/).length).toBeGreaterThan(
    0,
  );
  expect(screen.queryByText(/Dato no válido/)).toBeNull();
  await act(async () => late.resolve(revision('a')));
  expect(
    screen.queryByRole('heading', { name: 'Candidata a · revisión 1' }),
  ).toBeNull();
});
