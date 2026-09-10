import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import { PlanningWorkspace, NativePlanning } from './native-planning';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));
const call = vi.mocked(api);
let targetsRevision: number;
beforeEach(() => {
  targetsRevision = 2;
  call.mockReset();
  call.mockImplementation(async (path, body) => {
    if (body)
      return {
        preview_token: 'token',
        committed: false,
        report: {
          id: 'report',
          saved: false,
          current: true,
          inputs: body,
          result: {
            kind: 'aggregate',
            combined: {
              spec: { name: 'Combinado', rows: [] },
              contributors: [],
              unassigned_budget: '0',
              rounding_cash_pp: '0',
              labels: {},
            },
          },
        },
      };
    if (path === '/catalog')
      return { revision: 0, instruments: [], listings: [], aliases: [] };
    if (path.includes('/targets?'))
      return {
        revision: targetsRevision,
        active: { id: 'target', spec: { name: 'Global', rows: [] } },
        targets: [],
        offset: 0,
        limit: 100,
      };
    if (path.includes('/valuations?'))
      return { cuts: [], offset: 0, limit: 100 };
    return { reports: [], offset: 0, limit: 20 };
  });
});
async function preview() {
  await waitFor(() =>
    expect(
      (screen.getByRole('button', { name: 'Calcular análisis' }) as HTMLButtonElement).disabled,
    ).toBe(false),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Calcular análisis' }));
  await screen.findByRole('button', { name: 'Guardar análisis' });
}

it('does not read analysis until expanded and keeps form values when closed', async () => {
  render(<NativePlanning portfolioId="p" revision={1} active />);
  expect(call).not.toHaveBeenCalled();
  const details = screen
    .getByText('Abrir análisis de cartera')
    .closest('details')!;
  details.open = true;
  fireEvent(details, new Event('toggle'));
  await screen.findByLabelText('Aportación hipotética EUR');
  fireEvent.change(screen.getByLabelText('Aportación hipotética EUR'), {
    target: { value: '250' },
  });
  details.open = false;
  fireEvent(details, new Event('toggle'));
  details.open = true;
  fireEvent(details, new Event('toggle'));
  expect((screen.getByLabelText('Aportación hipotética EUR') as HTMLInputElement).value).toBe('250');
});

it('editing invalidates a reviewed plan and cannot save stale input', async () => {
  render(<PlanningWorkspace portfolioId="p" revision={1} active />);
  await preview();
  fireEvent.change(screen.getByLabelText('Aportación hipotética USD'), {
    target: { value: '100' },
  });
  expect(screen.queryByRole('button', { name: 'Guardar análisis' })).toBeNull();
});

it('saves only the frozen reviewed body without modifying the book', async () => {
  render(<PlanningWorkspace portfolioId="p" revision={1} active />);
  await preview();
  fireEvent.click(screen.getByRole('button', { name: 'Guardar análisis' }));
  await screen.findByText(/Confirmación guardada/);
  const writes = call.mock.calls.filter(([, body]) => body);
  expect(writes).toHaveLength(2);
  expect(writes[1][1]).toEqual({
    ...(writes[0][1] as Record<string, unknown>),
    commit: true,
    preview_token: 'token',
  });
  expect(
    writes.every(([path]) => path === '/v2/portfolios/p/planning-reports'),
  ).toBe(true);
});

it('hides a preview when target revision changes and does not retry failures', async () => {
  const view = render(
    <PlanningWorkspace portfolioId="p" revision={1} auditSequence={1} active />,
  );
  await preview();
  targetsRevision = 3;
  view.rerender(
    <PlanningWorkspace portfolioId="p" revision={1} auditSequence={2} active />,
  );
  await waitFor(() =>
    expect(
      screen.queryByRole('button', { name: 'Guardar análisis' }),
    ).toBeNull(),
  );
  call.mockRejectedValueOnce(new Error('Contexto obsoleto'));
  fireEvent.click(screen.getByRole('button', { name: 'Calcular análisis' }));
  await screen.findByText('Contexto obsoleto');
  expect(call.mock.calls.filter(([, body]) => body)).toHaveLength(2);
});
