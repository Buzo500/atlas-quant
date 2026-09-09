import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, datasetPricesPath } from '@/lib/api';
import type { DatasetPricesResponse } from '@/lib/api-types';
import { dataset, deferred } from '@/test/fixtures';
import { PriceExplorer, PricesPanel } from './prices-panel';
import { PriceChart } from './price-chart';
import { aggregateBars } from './aggregation';

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
function graphicLayout() {
  const graphic = screen.getByRole('img', { name: /Gráfico de precios/ });
  Object.defineProperty(graphic, 'getBoundingClientRect', {
    configurable: true,
    value: () => ({ left: 0, top: 0, width: 960, height: 380 }),
  });
  return graphic;
}
function hover(graphic: HTMLElement, x: number, y = 120) {
  fireEvent(
    graphic,
    new MouseEvent('pointermove', {
      bubbles: true,
      clientX: x,
      clientY: y,
    }),
  );
}
function mouseGesture(graphic: HTMLElement, type: string, x: number) {
  const event = new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    button: 0,
    clientX: x,
    clientY: 120,
  });
  Object.defineProperties(event, {
    pointerId: { value: 7 },
    pointerType: { value: 'mouse' },
  });
  fireEvent(graphic, event);
}
function tooltipField(name: string) {
  return screen
    .getByRole('tooltip')
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
  it('elimina el deslizador y muestra los OHLCV originales al lado del puntero solo durante la inspección', () => {
    render(<PriceExplorer response={response()} />);
    const graphic = graphicLayout();
    expect(
      screen.queryByRole('slider', { name: 'Inspeccionar barra' }),
    ).toBeNull();
    expect(
      screen.getByRole('slider', { name: 'Desplazar precios' }),
    ).toBeTruthy();
    expect(screen.queryByText('Inspeccionar barra')).toBeNull();
    expect(screen.queryByRole('tooltip')).toBeNull();
    hover(graphic, 443);
    const tooltip = screen.getByRole('tooltip');
    expect(tooltip.textContent).toContain('A · EUR');
    expect(within(tooltip).getByText('04/01/2021')).toBeTruthy();
    expect(tooltipField('open')?.getAttribute('value')).toBe('15');
    expect(tooltipField('high')?.getAttribute('value')).toBe('18');
    expect(tooltipField('low')?.getAttribute('value')).toBe('14');
    expect(tooltipField('close')?.getAttribute('value')).toBe('17');
    expect(tooltipField('volume')?.getAttribute('value')).toBe('3');
    expect(tooltip.style.left).toBe('459px');
    expect(tooltip.style.top).toBe('136px');
    expect(graphic.getAttribute('aria-describedby')).toContain(tooltip.id);
    fireEvent.pointerLeave(graphic);
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(field('close')?.getAttribute('value')).toBe('17');
    hover(graphic, 443);
    fireEvent.keyDown(graphic, { key: 'Escape' });
    expect(screen.queryByRole('tooltip')).toBeNull();
    hover(graphic, 900);
    expect(screen.queryByRole('tooltip')).toBeNull();
  });
  it('ancla la inspección por teclado al punto dibujado y la descarta al perder foco o cambiar de ventana', async () => {
    render(<PriceExplorer response={response()} />);
    const graphic = graphicLayout();
    fireEvent.focus(graphic);
    fireEvent.keyDown(graphic, { key: 'Home' });
    expect(tooltipField('close')?.getAttribute('value')).toBe('12');
    expect(tooltipField('volume')?.getAttribute('value')).toBe('0');
    expect(
      Number.parseFloat(screen.getByRole('tooltip').style.left),
    ).toBeCloseTo(114.2);
    fireEvent.keyDown(graphic, { key: 'ArrowRight' });
    expect(tooltipField('close')?.getAttribute('value')).toBe('15');
    fireEvent.blur(graphic);
    expect(screen.queryByRole('tooltip')).toBeNull();
    hover(graphic, 443);
    await userEvent
      .setup()
      .click(screen.getByRole('button', { name: 'Acercar precios' }));
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(screen.getByRole('img', { name: /Gráfico de precios/ })).toBe(
      graphic,
    );
    fireEvent.keyDown(graphic, { key: 'End' });
    expect(screen.getByRole('tooltip')).toBeTruthy();
    fireEvent(window, new Event('scroll'));
    expect(screen.queryByRole('tooltip')).toBeNull();
  });
  it('muestra OHLCV semanales exactos y las fechas realmente observadas', async () => {
    const data = response();
    render(<PriceExplorer response={data} />);
    const graphic = graphicLayout();
    hover(graphic, 443);
    await choice('Intervalo del gráfico', 'Semanal');
    expect(screen.queryByRole('tooltip')).toBeNull();
    fireEvent.keyDown(graphic, { key: 'Home' });
    const tooltip = screen.getByRole('tooltip');
    expect(within(tooltip).getByText('30/12/2020')).toBeTruthy();
    expect(within(tooltip).getByText('31/12/2020')).toBeTruthy();
    expect(tooltipField('open')?.getAttribute('value')).toBe('10');
    expect(tooltipField('high')?.getAttribute('value')).toBe('16');
    expect(tooltipField('low')?.getAttribute('value')).toBe('9');
    expect(tooltipField('close')?.getAttribute('value')).toBe('15');
    expect(tooltipField('volume')?.getAttribute('value')).toBe('2');
    expect(tooltip.textContent).toContain('2 sesiones agregadas');
    expect(tooltip.textContent).toContain('Periodo recortado');
  });
  it('mantiene el volumen ausente de un agregado sin presentarlo como cero', () => {
    const bars = aggregateBars(
      response().bars.map((bar, index) => ({
        ...bar,
        volume: index === 1 ? null : bar.volume,
      })),
      'W',
    );
    render(
      <PriceChart
        bars={bars}
        selected={0}
        onSelect={vi.fn()}
        representation="candles"
        volume
        symbol="A"
        currency="EUR"
      />,
    );
    fireEvent.keyDown(graphicLayout(), { key: 'Home' });
    expect(tooltipField('volume')?.hasAttribute('value')).toBe(false);
    expect(tooltipField('volume')?.textContent).toBe('Sin dato');
  });
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
    fireEvent.keyDown(graphic, { key: 'End' });
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
    const monthlyGraphic = screen.getByRole('img', {
      name: /Gráfico de precios/,
    });
    fireEvent.keyDown(monthlyGraphic, { key: 'Home' });
    fireEvent.keyDown(monthlyGraphic, { key: 'ArrowRight' });
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
      document.querySelectorAll(
        '.price-chart-svg .price-rise, .price-chart-svg .price-fall',
      ),
    ).toHaveLength(120);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Acercar precios' }));
    expect(
      document.querySelectorAll(
        '.price-chart-svg .price-rise, .price-chart-svg .price-fall',
      ),
    ).toHaveLength(60);
    fireEvent.change(
      screen.getByRole('slider', { name: 'Desplazar precios' }),
      { target: { value: '0' } },
    );
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
  it('conserva la fecha original inspeccionada al cambiar el zoom y desplazar una ventana que aún la contiene', async () => {
    render(<PriceExplorer response={response()} />);
    const graphic = graphicLayout();
    const user = userEvent.setup();
    hover(graphic, 443);
    expect(field('close')?.getAttribute('value')).toBe('17');
    await user.click(screen.getByRole('button', { name: 'Acercar precios' }));
    expect(
      document.querySelectorAll(
        '.price-chart-svg .price-rise, .price-chart-svg .price-fall',
      ),
    ).toHaveLength(3);
    expect(field('close')?.getAttribute('value')).toBe('17');
    const navigation = screen.getByRole('slider', {
      name: 'Desplazar precios',
    });
    fireEvent.change(navigation, { target: { value: '2' } });
    expect(navigation.getAttribute('value')).toBe('2');
    expect(field('close')?.getAttribute('value')).toBe('17');
    fireEvent.change(navigation, { target: { value: '0' } });
    expect(navigation.getAttribute('value')).toBe('0');
    expect(field('close')?.getAttribute('value')).toBe('17');
    await user.click(screen.getByRole('button', { name: 'Alejar precios' }));
    expect(field('close')?.getAttribute('value')).toBe('17');
    expect(
      screen.queryByRole('button', { name: 'Primera ventana' }),
    ).toBeNull();
    expect(
      screen.queryByRole('button', { name: 'Barras anteriores' }),
    ).toBeNull();
    expect(
      screen.queryByRole('button', { name: 'Barras siguientes' }),
    ).toBeNull();
  });
  it('activa rueda y arrastre solo en pantalla completa y conserva la lectura al volver', async () => {
    render(<PriceExplorer response={response()} />);
    const graphic = graphicLayout();
    const wheel = (ctrlKey = false) => {
      const event = new WheelEvent('wheel', {
        bubbles: true,
        cancelable: true,
        clientX: 443,
        clientY: 120,
        deltaY: -100,
        ctrlKey,
      });
      fireEvent(graphic, event);
      return event;
    };
    expect(wheel().defaultPrevented).toBe(false);
    hover(graphic, 443);
    const original = field('close')?.getAttribute('value');
    await userEvent
      .setup()
      .click(
        screen.getByRole('button', { name: 'Pantalla completa: Precios de A' }),
      );
    expect(screen.getByRole('dialog', { name: 'Precios de A' })).toBeTruthy();
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(screen.getByRole('img', { name: /Gráfico de precios/ })).toBe(
      graphic,
    );
    expect(wheel(true).defaultPrevented).toBe(false);
    expect(wheel().defaultPrevented).toBe(true);
    expect(
      document.querySelectorAll(
        '.price-chart-svg .price-rise, .price-chart-svg .price-fall',
      ),
    ).toHaveLength(4);
    const navigation = screen.getByRole('slider', {
      name: 'Desplazar precios',
    });
    expect(navigation.getAttribute('value')).toBe('1');
    hover(graphic, 330);
    expect(screen.getByRole('tooltip')).toBeTruthy();
    mouseGesture(graphic, 'pointerdown', 443);
    mouseGesture(graphic, 'pointermove', 643);
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(navigation.getAttribute('value')).toBe('0');
    mouseGesture(graphic, 'pointerup', 643);
    fireEvent.click(graphic);
    expect(screen.queryByRole('tooltip')).toBeNull();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.getByRole('img', { name: /Gráfico de precios/ })).toBe(
      graphic,
    );
    expect(field('close')?.getAttribute('value')).toBe(original);
    expect(wheel().defaultPrevented).toBe(false);
  });
  it.each([
    ['Home', '12', 'Sesión 30/12/2020'],
    ['End', '20', 'Sesión 01/02/2021'],
  ])(
    'ancla las lupas a la observación %s hasta una vela y al volver a ampliar',
    async (key, close, heading) => {
      render(<PriceExplorer response={response()} />);
      fireEvent.keyDown(graphicLayout(), { key });
      const user = userEvent.setup();
      for (let index = 0; index < 3; index++) {
        await user.click(
          screen.getByRole('button', { name: 'Acercar precios' }),
        );
        expect(field('close')?.getAttribute('value')).toBe(close);
        expect(screen.getByRole('heading', { name: heading })).toBeTruthy();
      }
      expect(
        document.querySelectorAll(
          '.price-chart-svg .price-rise, .price-chart-svg .price-fall',
        ),
      ).toHaveLength(1);
      for (let index = 0; index < 3; index++) {
        await user.click(
          screen.getByRole('button', { name: 'Alejar precios' }),
        );
        expect(field('close')?.getAttribute('value')).toBe(close);
        expect(screen.getByRole('heading', { name: heading })).toBeTruthy();
      }
      expect(
        document.querySelectorAll(
          '.price-chart-svg .price-rise, .price-chart-svg .price-fall',
        ),
      ).toHaveLength(5);
    },
  );
  it('mantiene el límite de mil velas y permite recorrer el histórico completo con la barra de navegación', async () => {
    const data = response();
    data.bars = Array.from({ length: 1200 }, (_, index) => ({
      date: new Date(Date.UTC(2020, 0, index + 1)).toISOString().slice(0, 10),
      open: 10 + index,
      high: 12 + index,
      low: 9 + index,
      close: 11 + index,
      volume: index,
    }));
    data.available_start = data.first_date = data.bars[0].date;
    data.available_end = data.last_date = data.bars[data.bars.length - 1].date;
    render(<PriceExplorer response={data} />);
    const user = userEvent.setup();
    for (let index = 0; index < 4; index++) {
      await user.click(screen.getByRole('button', { name: 'Alejar precios' }));
      expect(field('close')?.getAttribute('value')).toBe('1210');
    }
    expect(
      document.querySelectorAll(
        '.price-chart-svg .price-rise, .price-chart-svg .price-fall',
      ),
    ).toHaveLength(1000);
    expect(
      screen
        .getByRole('button', { name: 'Alejar precios' })
        .hasAttribute('disabled'),
    ).toBe(true);
    const navigation = screen.getByRole('slider', {
      name: 'Desplazar precios',
    });
    expect(navigation.getAttribute('max')).toBe('200');
    fireEvent.change(navigation, { target: { value: '0' } });
    const graphic = graphicLayout();
    fireEvent.keyDown(graphic, { key: 'Home' });
    expect(field('close')?.getAttribute('value')).toBe('11');
    fireEvent.change(navigation, { target: { value: '200' } });
    fireEvent.keyDown(graphic, { key: 'End' });
    expect(field('close')?.getAttribute('value')).toBe('1210');
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
