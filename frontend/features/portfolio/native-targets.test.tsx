import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import type { TargetSet, TargetHistory } from '@/lib/api-types';
import { NativeTargets, TargetsWorkspace } from './native-targets';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const call = vi.mocked(api);
const target: TargetSet = {
  id: 'a'.repeat(64),
  portfolio_id: 'p',
  version: 1,
  portfolio_revision: 1,
  catalog_revision: 0,
  created_at: '2026-01-06T00:00:00Z',
  spec: {
    name: 'Mi distribución',
    rows: [
      {
        instrument_id: null,
        weight: '100',
        minimum: '90',
        maximum: '100',
        concentration_limit: '100',
      },
    ],
  },
};
let head: TargetHistory;
beforeEach(() => {
  head = { revision: 0, active: null, targets: [], offset: 0, limit: 20 };
  call.mockReset();
  call.mockImplementation(async (path, body) => {
    if (body)
      return {
        target,
        preview_token: 'review-token',
        committed: false,
        action: 'draft',
      };
    if (path === '/catalog')
      return { revision: 0, instruments: [], listings: [], aliases: [] };
    if (path.includes('/targets?')) return head;
    if (path.includes('/valuations?'))
      return { cuts: [], offset: 0, limit: 20 };
    return { reports: [], offset: 0, limit: 20 };
  });
});

async function fillDraft() {
  await screen.findByText('Sin objetivos activos');
  fireEvent.click(screen.getByText('Crear o editar un borrador de objetivos'));
  fireEvent.change(screen.getByLabelText('Nombre de los objetivos'), {
    target: { value: 'Mi distribución' },
  });
  for (const [field, value] of [
    ['Objetivo', '100'],
    ['Mínimo', '90'],
    ['Máximo', '100'],
    ['Límite', '100'],
  ])
    fireEvent.change(screen.getByLabelText(`${field} % · Efectivo`), {
      target: { value },
    });
  fireEvent.click(screen.getByRole('button', { name: 'Revisar borrador' }));
  await screen.findByRole('button', { name: 'Guardar borrador' });
}

it('reads only when opened and preserves a draft when details are closed', async () => {
  render(<NativeTargets portfolioId="p" revision={1} active />);
  expect(call).not.toHaveBeenCalled();
  const details = screen
    .getByText('Consultar y editar objetivos')
    .closest('details')!;
  // jsdom does not implement the native summary default action.
  details.open = true;
  fireEvent(details, new Event('toggle'));
  await fillDraft();
  details.open = false;
  fireEvent(details, new Event('toggle'));
  details.open = true;
  fireEvent(details, new Event('toggle'));
  expect(
    (screen.getByLabelText('Nombre de los objetivos') as HTMLInputElement)
      .value,
  ).toBe('Mi distribución');
  expect(screen.getByRole('button', { name: 'Guardar borrador' })).toBeTruthy();
});

it('audit polling preserves the reviewed draft; editing invalidates it', async () => {
  const view = render(
    <TargetsWorkspace portfolioId="p" revision={1} auditSequence={1} active />,
  );
  await fillDraft();
  view.rerender(
    <TargetsWorkspace portfolioId="p" revision={1} auditSequence={2} active />,
  );
  await waitFor(() =>
    expect(call.mock.calls.filter(([, body]) => !!body)).toHaveLength(1),
  );
  expect(screen.getByRole('button', { name: 'Guardar borrador' })).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Mínimo % · Efectivo'), {
    target: { value: '80' },
  });
  expect(screen.queryByRole('button', { name: 'Guardar borrador' })).toBeNull();
});

it('saving a draft does not activate it and submits the exact reviewed body', async () => {
  render(<TargetsWorkspace portfolioId="p" revision={1} active />);
  await fillDraft();
  fireEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }));
  await screen.findByText(/Confirmación guardada/);
  const writes = call.mock.calls.filter(([, body]) => !!body);
  expect(writes).toHaveLength(2);
  expect(writes[1][1]).toEqual({
    ...(writes[0][1] as object),
    commit: true,
    preview_token: 'review-token',
  });
  expect(writes.some(([path]) => path.endsWith('/activate'))).toBe(false);
});

it('server context rejection clears the review and never retries a mutation', async () => {
  render(<TargetsWorkspace portfolioId="p" revision={1} active />);
  await fillDraft();
  call.mockRejectedValueOnce(
    new Error('El libro o los objetivos han cambiado.'),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }));
  await screen.findByText('El libro o los objetivos han cambiado.');
  expect(screen.queryByRole('button', { name: 'Guardar borrador' })).toBeNull();
  expect(call.mock.calls.filter(([, body]) => !!body)).toHaveLength(2);
});

it('activation needs review and separate explicit confirmation', async () => {
  head = { ...head, revision: 1, targets: [target] };
  render(<TargetsWorkspace portfolioId="p" revision={1} active />);
  await screen.findByText('Sin objetivos activos');
  fireEvent.click(screen.getByText('Versiones y activación'));
  fireEvent.click(
    screen.getByRole('button', { name: 'Revisar activación v1' }),
  );
  await screen.findByRole('button', {
    name: 'Confirmar activación de objetivos',
  });
  const writes = call.mock.calls.filter(([, body]) => !!body);
  expect(writes).toHaveLength(1);
  expect(writes[0][1]).toEqual({
    expected_revision: 1,
    expected_targets_revision: 1,
    target_id: target.id,
  });
  fireEvent.click(
    screen.getByRole('button', { name: 'Confirmar activación de objetivos' }),
  );
  await screen.findByText(/Confirmación guardada/);
  expect(call.mock.calls.filter(([, body]) => !!body)).toHaveLength(2);
});
