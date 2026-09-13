import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { PerformanceExport } from './performance-export';

afterEach(() => vi.restoreAllMocks());

test('downloads saved server report by IDs without client financial data', async () => {
  const fetcher = vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValue(
      new Response('zip', { headers: { 'content-type': 'application/zip' } }),
    );
  const create = vi
    .spyOn(URL, 'createObjectURL')
    .mockReturnValue('blob:period');
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => {});
  render(<PerformanceExport portfolioId="p/1" reportId="abc" />);
  fireEvent.click(
    screen.getByRole('button', { name: 'Exportar fuente LaTeX de cartera' }),
  );
  await screen.findByText(
    'Fuente LaTeX y datos del informe guardado descargados.',
  );
  expect(fetcher).toHaveBeenCalledWith(
    '/api/v2/portfolios/p%2F1/performance/abc/latex',
    expect.objectContaining({
      method: 'POST',
      headers: { 'X-Atlas-Client': 'local-v1' },
    }),
  );
  expect(fetcher.mock.calls[0][1]).not.toHaveProperty('body');
  expect(create).toHaveBeenCalledOnce();
  expect(click).toHaveBeenCalledOnce();
});

test('failed response shows error without downloading or retrying', async () => {
  const fetcher = vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValue(new Response('{}', { status: 404 }));
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => {});
  render(<PerformanceExport portfolioId="p" reportId="old" />);
  fireEvent.click(screen.getByRole('button'));
  expect((await screen.findByRole('alert')).textContent).toContain(
    'ya no está disponible',
  );
  expect(fetcher).toHaveBeenCalledOnce();
  expect(click).not.toHaveBeenCalled();
});

test('changing selected report aborts old download before creating a file', async () => {
  let finish: (r: Response) => void = () => {};
  const fetcher = vi.spyOn(globalThis, 'fetch').mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:old');
  const { unmount } = render(
    <PerformanceExport portfolioId="p" reportId="old" />,
  );
  fireEvent.click(screen.getByRole('button'));
  unmount();
  expect(fetcher.mock.calls[0][1]?.signal?.aborted).toBe(true);
  await act(async () => {
    finish(
      new Response('zip', { headers: { 'content-type': 'application/zip' } }),
    );
  });
  await waitFor(() => expect(create).not.toHaveBeenCalled());
});
