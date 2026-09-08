import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, datasetPricesPath } from '@/lib/api';
import type { DatasetPricesResponse } from '@/lib/api-types';
import { dataset, deferred } from '@/test/fixtures';
import { PriceExplorer, PricesPanel } from './prices-panel';

vi.mock('@/lib/api', async (original) => ({
  ...(await original<typeof import('@/lib/api')>()),
  api: vi.fn(),
}));
const request = vi.mocked(api);
function response(id = 'a', version = 1, symbol = 'A'): DatasetPricesResponse {
  return {
    dataset_id: id,
    dataset_version: version,
    manifest_hash: 'a'.repeat(64),
    symbol,
    currency: 'EUR',
    source_kind: 'synthetic',
    source: 'Observaciones sintéticas de prueba',
    source_metadata: null,
    price_basis: 'Sin ajustar',
    calendar: 'No declarado',
    warnings: [],
    available_start: '2020-12-30',
    available_end: '2021-02-01',
    first_date: '2020-12-30',
    last_date: '2021-02-01',
    preceding_close: null,
    preceding_date: null,
    bars: [
      { date: '2020-12-30', open: 10, high: 14, low: 9, close: 12, volume: 0 },
      { date: '2020-12-31', open: 12, high: 16, low: 11, close: 15, volume: 2 },
      { date: '2021-01-04', open: 15, high: 18, low: 14, close: 17, volume: 3 },
      { date: '2021-01-05', open: 17, high: 19, low: 16, close: 18, volume: 4 },
      { date: '2021-02-01', open: 18, high: 22, low: 17, close: 20, volume: 5 },
    ],
  };
}
function field(name: string) {
  return screen
    .getByRole('region', { name: 'Lectura de precios' })
    .querySelector(`[data-price-field="${name}"] data`);
}
async function choice(label: string, option: string) {
  const user = userEvent.setup();
  await user.click(screen.getByRole('combobox', { name: label }));
  await user.click(await screen.findByRole('option', { name: option }));
}
beforeEach(() => request.mockReset());

describe('Consulta de precios con identidad inmutable', () => {
  it.each(['dataset', 'version'])(
    'descarta el resultado y el error antiguos al cambiar %s',
    async (kind) => {
      const pending = deferred<DatasetPricesResponse>();
      request.mockImplementationOnce(() => pending.promise);
      const initial = dataset();
      const view = render(<PricesPanel dataset={initial} />);
      const firstSignal = request.mock.calls[0][2];
      const next = kind === 'dataset' ? dataset('b') : dataset('a', 2);
      request.mockResolvedValueOnce(
        response(next.id, next.version, next.manifest.symbols[0]),
      );
      view.rerender(<PricesPanel dataset={next} />);
      await screen.findByRole('region', { name: 'Lectura de precios' });
      expect(firstSignal?.aborted).toBe(true);
      expect(request.mock.calls[1][0]).toBe(
        datasetPricesPath(next.id, next.version, next.manifest.symbols[0]),
      );
      await act(async () => pending.resolve(response()));
      expect(
        view.container.querySelector('.prices-context strong')?.textContent,
      ).toBe(`${next.manifest.symbols[0]} · EUR`);
      expect(
        view.container.querySelector('.prices-trace-grid')?.textContent,
      ).toContain(`Versión${next.version}`);
      expect(screen.queryByText(/no coincide/)).toBeNull();
    },
  );
  it('cambia de activo, aborta una respuesta tardía y mantiene el último símbolo', async () => {
    const pending = deferred<DatasetPricesResponse>();
    request.mockImplementationOnce(() => pending.promise);
    render(<PricesPanel dataset={dataset()} />);
    request.mockResolvedValueOnce(response('a', 1, 'B'));
    await choice('Activo del gráfico', 'B');
    await screen.findByRole('region', { name: 'Lectura de precios' });
    await act(async () => pending.reject(new Error('Error anterior')));
    expect(screen.queryByText(/Error anterior/)).toBeNull();
    expect(screen.getByText('B · EUR')).toBeTruthy();
  });
  it('expone carga, error y reintento sin cambiar la versión solicitada', async () => {
    const pending = deferred<DatasetPricesResponse>();
    request.mockImplementationOnce(() => pending.promise);
    render(<PricesPanel dataset={dataset()} />);
    expect(screen.getAllByText(/Cargando precios/).length).toBeGreaterThan(0);
    await act(async () => pending.reject(new Error('Lectura no disponible')));
    request.mockResolvedValueOnce(response());
    await userEvent
      .setup()
      .click(screen.getByRole('button', { name: 'Reintentar precios' }));
    await screen.findByRole('region', { name: 'Lectura de precios' });
    expect(request.mock.calls[0][0]).toBe(request.mock.calls[1][0]);
    expect(field('close')?.getAttribute('value')).toBe('20');
  });
  it('permite recortar la consulta tras superar el límite de filas', async () => {
    request.mockRejectedValueOnce(new Error('Supera 100.000 observaciones'));
    render(<PricesPanel dataset={dataset()} />);
    await screen.findByRole('button', { name: 'Reintentar precios' });
    await userEvent
      .setup()
      .click(screen.getByText('Fechas de consulta al motor'));
    fireEvent.change(screen.getByLabelText('Consulta desde'), {
      target: { value: '2020-12-30' },
    });
    fireEvent.change(screen.getByLabelText('Consulta hasta'), {
      target: { value: '2021-02-01' },
    });
    request.mockResolvedValueOnce(response());
    await userEvent
      .setup()
      .click(screen.getByRole('button', { name: 'Consultar precios' }));
    await screen.findByRole('region', { name: 'Lectura de precios' });
    expect(request.mock.calls[1][0]).toBe(
      '/datasets/a/prices?version=1&symbol=A&start=2020-12-30&end=2021-02-01',
    );
  });
  it('no consulta un panel inactivo ni atribuye una respuesta de otro símbolo', async () => {
    const view = render(<PricesPanel dataset={dataset()} active={false} />);
    expect(request).not.toHaveBeenCalled();
    request.mockResolvedValueOnce(response('a', 1, 'AJENO'));
    view.rerender(<PricesPanel dataset={dataset()} active />);
    await screen.findByText(
      'La respuesta de precios no coincide con el activo y la versión solicitados.',
    );
    expect(
      screen.queryByRole('slider', { name: 'Inspeccionar barra' }),
    ).toBeNull();
  });
});

describe('Exploración fiel y accesible de OHLCV', () => {
  it('presenta el cambio redondeado y conserva sus datos numéricos y el OHLC original', () => {
    const data = response();
    const close = 1.050801;
    data.bars = [
      { date: '2021-02-01', open: 1, high: 2, low: 0.5, close, volume: 3 },
    ];
    data.first_date = data.last_date = '2021-02-01';
    data.preceding_close = 1;
    data.preceding_date = '2021-01-29';
    render(<PriceExplorer response={data} />);
    expect(field('change')?.textContent).toBe('0,050801 EUR');
    expect(field('change')?.getAttribute('value')).toBe(String(close - 1));
    expect(field('close')?.getAttribute('value')).toBe(String(close));
    expect(field('close')?.textContent).toBe('1,050801 EUR');
    expect(field('open')?.getAttribute('value')).toBe('1');
    expect(field('high')?.getAttribute('value')).toBe('2');
    expect(field('low')?.getAttribute('value')).toBe('0.5');
    expect(field('volume')?.getAttribute('value')).toBe('3');
  });
  it('usa observaciones originales con teclado y cursor más cercano, incluso con márgenes SVG', () => {
    render(<PriceExplorer response={response()} />);
    const graphic = screen.getByRole('img', { name: /Gráfico de precios/ });
    expect(field('close')?.getAttribute('value')).toBe('20');
    fireEvent.keyDown(graphic, { key: 'Home' });
    expect(field('close')?.getAttribute('value')).toBe('12');
    expect(field('volume')?.getAttribute('value')).toBe('0');
    expect(field('change')?.hasAttribute('value')).toBe(false);
    fireEvent.keyDown(graphic, { key: 'ArrowRight' });
    expect(field('close')?.getAttribute('value')).toBe('15');
    expect(field('change')?.getAttribute('value')).toBe('3');
    Object.defineProperty(graphic, 'getBoundingClientRect', {
      value: () => ({ left: 0, top: 0, width: 960, height: 190 }),
    });
    fireEvent(
      graphic,
      new MouseEvent('pointermove', {
        bubbles: true,
        clientX: 289.1,
        clientY: 50,
      }),
    );
    expect(field('close')?.getAttribute('value')).toBe('12');
    fireEvent.change(
      screen.getByRole('slider', { name: 'Inspeccionar barra' }),
      { target: { value: '4' } },
    );
    expect(field('close')?.getAttribute('value')).toBe('20');
    expect(field('previous-close')?.getAttribute('value')).toBe('18');
  });
  it('agrega semanal y mensual, conserva trazabilidad y el cambio entre intervalos', async () => {
    render(<PriceExplorer response={response()} />);
    await choice('Intervalo del gráfico', 'Semanal');
    fireEvent.keyDown(screen.getByRole('img', { name: /Gráfico de precios/ }), {
      key: 'Home',
    });
    expect(field('open')?.getAttribute('value')).toBe('10');
    expect(field('high')?.getAttribute('value')).toBe('16');
    expect(field('low')?.getAttribute('value')).toBe('9');
    expect(field('close')?.getAttribute('value')).toBe('15');
    expect(field('volume')?.getAttribute('value')).toBe('2');
    expect(screen.getByText(/Completitud desconocida/)).toBeTruthy();
    expect(screen.getByText(/Periodo civil recortado:/)).toBeTruthy();
    await choice('Intervalo del gráfico', 'Mensual');
    fireEvent.change(
      screen.getByRole('slider', { name: 'Inspeccionar barra' }),
      { target: { value: '1' } },
    );
    expect(field('open')?.getAttribute('value')).toBe('15');
    expect(field('close')?.getAttribute('value')).toBe('18');
    expect(field('volume')?.getAttribute('value')).toBe('7');
    expect(field('change')?.getAttribute('value')).toBe('3');
    expect(field('previous-close')?.getAttribute('value')).toBe('15');
  });
  it.each(['Línea', 'Área', 'Barras OHLC'])(
    'cambia a %s sin alterar el cierre inspeccionado',
    async (style) => {
      const view = render(<PriceExplorer response={response()} />);
      await choice('Representación de precios', style);
      expect(field('close')?.getAttribute('value')).toBe('20');
      expect(
        view.container.querySelector('.price-chart-svg')?.innerHTML,
      ).not.toMatch(/NaN|Infinity/);
    },
  );
  it('filtra fechas sin rellenar huecos y usa el cierre previo al rango para el primer cambio', async () => {
    render(<PriceExplorer response={response()} />);
    fireEvent.change(screen.getByLabelText('Precios desde'), {
      target: { value: '2021-01-04' },
    });
    fireEvent.change(screen.getByLabelText('Precios hasta'), {
      target: { value: '2021-01-05' },
    });
    await userEvent
      .setup()
      .click(screen.getByRole('button', { name: 'Aplicar fechas' }));
    fireEvent.keyDown(screen.getByRole('img', { name: /Gráfico de precios/ }), {
      key: 'Home',
    });
    expect(field('previous-close')?.getAttribute('value')).toBe('15');
    expect(field('change')?.getAttribute('value')).toBe('2');
    fireEvent.change(screen.getByLabelText('Precios desde'), {
      target: { value: '2021-01-06' },
    });
    fireEvent.change(screen.getByLabelText('Precios hasta'), {
      target: { value: '2021-01-10' },
    });
    await userEvent
      .setup()
      .click(screen.getByRole('button', { name: 'Aplicar fechas' }));
    expect(
      screen.getByText('No hay observaciones diarias en las fechas elegidas.'),
    ).toBeTruthy();
    expect(
      screen.queryByRole('img', { name: /Gráfico de precios/ }),
    ).toBeNull();
  });
  it('limita el render inicial y pagina los originales independientemente del zoom', async () => {
    const data = response();
    data.bars = Array.from({ length: 130 }, (_, index) => ({
      ...data.bars[0],
      date: new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10),
    }));
    data.available_start = data.first_date = data.bars[0].date;
    data.available_end = data.last_date = data.bars[129].date;
    render(<PriceExplorer response={data} />);
    expect(
      screen
        .getByRole('slider', { name: 'Inspeccionar barra' })
        .getAttribute('max'),
    ).toBe('119');
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Acercar precios' }));
    expect(
      screen
        .getByRole('slider', { name: 'Inspeccionar barra' })
        .getAttribute('max'),
    ).toBe('59');
    await user.click(screen.getByRole('button', { name: 'Primera ventana' }));
    fireEvent.keyDown(screen.getByRole('img', { name: /Gráfico de precios/ }), {
      key: 'Home',
    });
    expect(
      screen.getByRole('heading', { name: 'Sesión 01/01/2026' }),
    ).toBeTruthy();
    await user.click(screen.getByText('Datos diarios originales'));
    expect(screen.getAllByRole('row')).toHaveLength(51);
    const pagination = screen.getByRole('navigation', {
      name: 'Paginación de precios diarios',
    });
    await user.click(
      within(pagination).getByRole('button', { name: 'Siguiente' }),
    );
    expect(screen.getAllByRole('row')).toHaveLength(51);
    expect(screen.getByRole('rowheader', { name: '20/02/2026' })).toBeTruthy();
  });
  it.each([Number.MAX_VALUE, Number.MIN_VALUE])(
    'dibuja una sola barra extrema finita %s sin geometría inválida',
    (amount) => {
      const data = response();
      data.bars = [
        {
          date: data.first_date!,
          open: amount,
          high: amount,
          low: amount,
          close: amount,
          volume: 0,
        },
      ];
      data.last_date = data.first_date;
      const view = render(<PriceExplorer response={data} />);
      expect(
        view.container.querySelector('.price-chart-svg')?.innerHTML,
      ).not.toMatch(/NaN|Infinity/);
      expect(field('close')?.getAttribute('value')).toBe(String(amount));
      expect(field('close')?.textContent).not.toBe('0 EUR');
    },
  );
  it('rechaza OHLC alterados sin emitir geometría ni ocultar el fallo', () => {
    const data = response();
    data.bars[0].high = 1;
    render(<PriceExplorer response={data} />);
    expect(screen.getByRole('alert').textContent).toContain('OHLC no válidos');
    expect(
      screen.queryByRole('img', { name: /Gráfico de precios/ }),
    ).toBeNull();
  });
});
