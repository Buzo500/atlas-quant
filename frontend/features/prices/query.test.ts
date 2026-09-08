import { expect, it, vi } from 'vitest';
import { api, datasetPricesPath } from '@/lib/api';

it('consulta precios mediante GET con versión y codificación explícitas, sin cuerpo ni claves', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(
      new Response(JSON.stringify({ bars: [] }), { status: 200 }),
    );
  vi.stubGlobal('fetch', fetch);
  const controller = new AbortController();
  const path = datasetPricesPath('datos/1', 2, 'A B&EUR', {
    start: '2026-01-01',
    end: '2026-02-01',
  });
  expect(path).toBe(
    '/datasets/datos%2F1/prices?version=2&symbol=A+B%26EUR&start=2026-01-01&end=2026-02-01',
  );
  expect(await api(path, undefined, controller.signal)).toEqual({ bars: [] });
  expect(fetch).toHaveBeenCalledWith('/api' + path, {
    cache: 'no-store',
    signal: controller.signal,
  });
});
it.each([0, -1, 1.5, NaN, Infinity])(
  'rechaza una versión no válida %s antes de consultar',
  (version) => {
    expect(() => datasetPricesPath('a', version, 'A')).toThrow();
  },
);
