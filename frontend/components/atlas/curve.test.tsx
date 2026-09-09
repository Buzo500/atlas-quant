import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { BacktestPoint, PortfolioPoint } from '@/lib/api-types';
import { Curve } from './curve';

function portfolio(values: number[]): PortfolioPoint[] {
  return values.map((nav, index) => ({
    date: new Date(Date.UTC(2000, 0, index + 1)).toISOString().slice(0, 10),
    nav,
    twr_index: 1,
  }));
}

function drawnPoints(container: HTMLElement) {
  return (
    container
      .querySelector('.chart-viewport polyline')
      ?.getAttribute('points') ?? ''
  )
    .split(' ')
    .map((point) => point.split(',').map(Number));
}

describe('Curva accesible y representación de valores', () => {
  it('distingue una serie vacía de un patrimonio cero', () => {
    render(<Curve data={[]} />);
    expect(screen.getByText(/No hay observaciones disponibles/)).not.toBeNull();
    expect(screen.queryByRole('img')).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
  });

  it.each([NaN, Infinity, -Infinity])(
    'explica valores inválidos sin dibujar una evolución inventada (%s)',
    async (value) => {
      render(<Curve data={portfolio([100, value])} />);
      expect(
        screen.getByText(/La serie contiene valores no válidos/),
      ).not.toBeNull();
      expect(screen.queryByRole('img')).toBeNull();
      await userEvent.click(
        screen.getByRole('button', { name: 'Ver datos de la curva' }),
      );
      expect(
        screen.getByRole('cell', { name: 'Dato no válido' }),
      ).not.toBeNull();
    },
  );

  it.each([0, -100, 100])(
    'representa una serie constante de %s sin geometría inválida',
    (value) => {
      const { container } = render(
        <Curve data={portfolio([value, value, value])} />,
      );
      expect(
        screen.getByRole('img', { name: /Patrimonio: evolución en EUR/ }),
      ).not.toBeNull();
      const points = drawnPoints(container);
      expect(
        points.every(([x, y]) => Number.isFinite(x) && Number.isFinite(y)),
      ).toBe(true);
      expect(new Set(points.map(([, y]) => y)).size).toBe(1);
    },
  );

  it('admite extremos finitos de ambos signos sin desbordamiento numérico', () => {
    const { container } = render(
      <Curve data={portfolio([-Number.MAX_VALUE, 0, Number.MAX_VALUE])} />,
    );
    expect(
      drawnPoints(container).every(
        ([x, y]) => Number.isFinite(x) && Number.isFinite(y),
      ),
    ).toBe(true);
    expect(container.innerHTML).not.toMatch(/\b(NaN|Infinity)\b/);
  });

  it('hace visible una observación única', () => {
    const { container } = render(<Curve data={portfolio([0])} />);
    expect(
      screen.getByRole('img', { name: /Valor inicial 0,00/ }),
    ).not.toBeNull();
    expect(container.querySelector('.chart-viewport circle')).not.toBeNull();
    expect(container.querySelector('.chart-viewport polyline')).toBeNull();
  });

  it('explica escala lineal y distancia por observaciones aunque existan saltos de fechas', () => {
    const data = portfolio([100, 110, 120]);
    data[2].date = '2001-01-01';
    const { container } = render(<Curve data={data} />);
    expect(
      screen.getByText(
        /EUR · Escala lineal · Eje horizontal por observaciones/,
      ),
    ).not.toBeNull();
    const [first, middle, last] = drawnPoints(container);
    expect(middle[0] - first[0]).toBeCloseTo(last[0] - middle[0], 1);
  });

  it('identifica un benchmark completo con línea discontinua, contraste y valores tabulados', async () => {
    const data: BacktestPoint[] = [
      { date: '2026-09-01', equity: 100, benchmark: 100 },
      { date: '2026-09-02', equity: 120, benchmark: 115 },
    ];
    const { container } = render(<Curve data={data} />);
    const benchmark = container.querySelector(
      '.chart-viewport polyline[stroke-dasharray]',
    );
    expect(benchmark).not.toBeNull();
    const luminance = (hex: string) => {
      const channels = hex
        .match(/[0-9a-f]{2}/gi)!
        .map((part) => Number.parseInt(part, 16) / 255)
        .map((value) =>
          value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4,
        );
      return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    };
    expect(
      (luminance('#FFFCF6') + 0.05) /
        (luminance(benchmark!.getAttribute('stroke')!) + 0.05),
    ).toBeGreaterThanOrEqual(3);
    await userEvent.click(
      screen.getByRole('button', { name: 'Ver datos de la curva' }),
    );
    expect(
      screen.getByRole('columnheader', { name: 'Mantener · mismo peso (EUR)' }),
    ).not.toBeNull();
    expect(screen.getByRole('cell', { name: /115,00/ })).not.toBeNull();
  });

  it('omite el benchmark completo cuando falta en alguna observación', () => {
    const { container } = render(
      <Curve
        data={[
          { date: '2026-09-01', equity: 100, benchmark: 90 },
          { date: '2026-09-02', nav: 120, twr_index: 1 },
        ]}
      />,
    );
    expect(
      container.querySelector('.chart-viewport polyline[stroke-dasharray]'),
    ).toBeNull();
    expect(screen.queryByText('Mantener · mismo peso')).toBeNull();
  });

  it('abre, pagina y cierra la alternativa tabular usando teclado', async () => {
    const user = userEvent.setup();
    render(
      <Curve
        data={portfolio(Array.from({ length: 120 }, (_, index) => 100 + index))}
      />,
    );
    expect(screen.queryByRole('table')).toBeNull();
    screen.getByRole('button', { name: 'Ver datos de la curva' }).focus();
    await user.keyboard('{Enter}');
    const table = screen.getByRole('table', {
      name: 'Valores originales de patrimonio en EUR',
    });
    expect(within(table).getAllByRole('rowheader')).toHaveLength(50);
    expect(
      screen.getByRole('button', { name: 'Anterior' }).hasAttribute('disabled'),
    ).toBe(true);
    screen.getByRole('button', { name: 'Siguiente' }).focus();
    await user.keyboard('{Enter}');
    expect(screen.getByText('Filas 51–100 de 120')).not.toBeNull();
    expect(screen.getByRole('rowheader', { name: '51' })).not.toBeNull();
    await user.keyboard('{Enter}');
    expect(screen.getByText('Filas 101–120 de 120')).not.toBeNull();
    expect(within(table).getAllByRole('rowheader')).toHaveLength(20);
    expect(
      screen
        .getByRole('button', { name: 'Siguiente' })
        .hasAttribute('disabled'),
    ).toBe(true);
    screen.getByRole('button', { name: 'Ocultar datos de la curva' }).focus();
    await user.keyboard(' ');
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('reduce solo el dibujo de una serie grande y conserva extremos, endpoints y filas originales', async () => {
    const data = portfolio(Array.from({ length: 100_000 }, () => 100));
    data[43_210].nav = 500;
    data[55_555].nav = -100;
    const { container } = render(<Curve data={data} />);
    expect(
      screen.getByText(/Dibujo reducido conservando los extremos/),
    ).not.toBeNull();
    expect(screen.queryByRole('table')).toBeNull();
    const points = drawnPoints(container);
    expect(points.length).toBeLessThan(2000);
    const first = points[0][0];
    const last = points.at(-1)![0];
    const highest = points.reduce((best, point) =>
      point[1] < best[1] ? point : best,
    );
    const lowest = points.reduce((best, point) =>
      point[1] > best[1] ? point : best,
    );
    expect(highest[0]).toBeCloseTo(
      first + (43_210 / 99_999) * (last - first),
      1,
    );
    expect(lowest[0]).toBeCloseTo(
      first + (55_555 / 99_999) * (last - first),
      1,
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Ver datos de la curva' }),
    );
    expect(screen.getByText('Filas 1–50 de 100.000')).not.toBeNull();
    expect(screen.getAllByRole('rowheader')).toHaveLength(50);
    expect(screen.getByRole('cell', { name: '19/02/2000' })).not.toBeNull();
    expect(data[43_210].nav).toBe(500);
    expect(data[55_555].nav).toBe(-100);
  });
});

describe('Inspección y navegación de la curva', () => {
  const detail = () =>
    screen.getByRole('region', { name: 'Detalle de la observación' });
  const control = () => screen.getByRole('img') as unknown as SVGSVGElement;
  const measuredCurve = () => {
    const observations = new Map<Element, ResizeObserverCallback>();
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(private callback: ResizeObserverCallback) {}
        observe(element: Element) {
          observations.set(element, this.callback);
        }
        disconnect() {}
      },
    );
    const result = render(<Curve data={portfolio([100, 105, 110])} />);
    const viewport = result.container.querySelector('.chart-viewport')!;
    let dimensions = { width: 366, height: 521.59375 };
    const box = () => ({
      ...dimensions,
      left: 0,
      top: 0,
      right: dimensions.width,
      bottom: dimensions.height,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
    vi.spyOn(viewport, 'getBoundingClientRect').mockImplementation(box);
    vi.spyOn(control(), 'getBoundingClientRect').mockImplementation(box);
    const matrix = { a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 };
    Object.defineProperty(control(), 'getScreenCTM', {
      value: () => ({ ...matrix, inverse: () => matrix }),
    });
    const resize = (next = dimensions) => {
      dimensions = next;
      act(() => observations.get(viewport)?.([], {} as ResizeObserver));
    };
    fireEvent.click(
      screen.getByRole('button', {
        name: 'Pantalla completa: Curva de cartera',
      }),
    );
    resize();
    return { ...result, resize };
  };
  const range = async (from: string, to: string) => {
    fireEvent.change(screen.getByLabelText('Inicio de la curva'), {
      target: { value: from },
    });
    fireEvent.change(screen.getByLabelText('Fin de la curva'), {
      target: { value: to },
    });
    await userEvent.click(
      screen.getByRole('button', { name: 'Aplicar rango' }),
    );
  };

  it('lee una observación original interior omitida por el dibujo reducido', () => {
    const data = portfolio(
      Array.from({ length: 100_000 }, (_, index) => 100 + index),
    );
    const { container } = render(<Curve data={data} />);
    const points = drawnPoints(container);
    const first = points[0][0],
      last = points.at(-1)![0];
    const gaps = points.slice(1).map((point, index) => ({
      width: point[0] - points[index][0],
      from: points[index][0],
      to: point[0],
    }));
    const gap = gaps.reduce((best, candidate) =>
      candidate.width > best.width ? candidate : best,
    );
    const x = (gap.from + gap.to) / 2;
    const index = Math.round(
      ((x - first) / (last - first)) * (data.length - 1),
    );
    expect(points.some(([drawnX]) => Math.abs(drawnX - x) < 0.05)).toBe(false);
    fireEvent.pointerMove(container.querySelector('.chart-viewport svg')!, {
      clientX: x,
    });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      data[index].date,
    );
    expect(detail().querySelector('data')?.getAttribute('value')).toBe(
      String(data[index].nav),
    );
    const tooltip = screen.getByRole('tooltip');
    expect(tooltip.querySelector('time')?.getAttribute('dateTime')).toBe(
      data[index].date,
    );
    expect(tooltip.querySelector('data')?.getAttribute('value')).toBe(
      String(data[index].nav),
    );
  });

  it('mantiene coordenadas originales tras resize y selecciona los extremos reales', () => {
    let resize: ResizeObserverCallback | undefined;
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(callback: ResizeObserverCallback) {
          resize = callback;
        }
        observe() {}
        disconnect() {}
      },
    );
    const { container } = render(<Curve data={portfolio([100, 105, 110])} />);
    const viewport = container.querySelector('.chart-viewport')!;
    vi.spyOn(viewport, 'getBoundingClientRect').mockReturnValue({
      width: 1200,
      height: 350,
      left: 0,
      right: 1200,
      top: 0,
      bottom: 350,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
    act(() => resize?.([], {} as ResizeObserver));
    const svg = container.querySelector('.chart-viewport svg')!;
    vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({
      width: 600,
      height: 175,
      left: 100,
      right: 700,
      top: 0,
      bottom: 175,
      x: 100,
      y: 0,
      toJSON: () => ({}),
    });
    fireEvent.pointerMove(svg, { clientX: 100 });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-01',
    );
    fireEvent.pointerMove(svg, { clientX: 700 });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-03',
    );
  });

  it('conserva la primera ficha del ratón cuando la lectura amplía su alto de 24 a 42 píxeles', () => {
    const { resize } = measuredCurve();
    fireEvent.pointerMove(control(), { clientX: 200, clientY: 200 });
    const before = screen.getByRole('tooltip');
    const position = { left: before.style.left, top: before.style.top };
    // Real narrow fullscreen geometry: the flex readout grows by 18.28125 px.
    resize({ width: 366, height: 503.3125 });
    const after = screen.getByRole('tooltip');
    expect(after.querySelector('data')?.getAttribute('value')).toBe('105');
    expect({ left: after.style.left, top: after.style.top }).toEqual(position);
    // ResizeObserver may notify again without a new effective SVG size.
    resize({ width: 366, height: 503.3125 });
    expect(screen.getByRole('tooltip')).toBe(after);
  });

  it('reancla la ficha del teclado al punto original tras cambiar solo el alto', () => {
    const { container, resize } = measuredCurve();
    act(() => control().focus());
    fireEvent.keyDown(control(), { key: 'Home' });
    fireEvent.keyDown(control(), { key: 'ArrowRight' });
    const oldTop = Number.parseFloat(screen.getByRole('tooltip').style.top);
    resize({ width: 366, height: 503.3125 });
    const tip = screen.getByRole('tooltip');
    const [pointX, pointY] = drawnPoints(container)[1];
    expect(tip.querySelector('data')?.getAttribute('value')).toBe('105');
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-02',
    );
    expect(Number.parseFloat(tip.style.left)).toBeCloseTo(pointX + 16, 1);
    expect(Number.parseFloat(tip.style.top)).toBeCloseTo(pointY + 16, 1);
    expect(Number.parseFloat(tip.style.top)).not.toBe(oldTop);
  });

  it('cierra la ficha ante cambio de ancho, resize de ventana y scroll conservando la selección', () => {
    const { resize } = measuredCurve();
    const hover = () =>
      fireEvent.pointerMove(control(), { clientX: 200, clientY: 200 });
    hover();
    resize({ width: 384, height: 503.3125 });
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(detail().querySelector('data')?.getAttribute('value')).toBe('105');
    hover();
    fireEvent(window, new Event('resize'));
    expect(screen.queryByRole('tooltip')).toBeNull();
    hover();
    fireEvent.scroll(window);
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(detail().querySelector('data')?.getAttribute('value')).toBe('105');
  });

  it('no recorre de nuevo la serie de 100.000 puntos al mover el cursor', () => {
    let reads = 0;
    const data = new Proxy(
      portfolio(Array.from({ length: 100_000 }, (_, index) => 100 + index)),
      {
        get(target, property, receiver) {
          if (typeof property === 'string' && /^\d+$/.test(property)) reads++;
          return Reflect.get(target, property, receiver);
        },
      },
    );
    const { container } = render(<Curve data={data} />);
    reads = 0;
    fireEvent.pointerMove(container.querySelector('.chart-viewport svg')!, {
      clientX: 300,
    });
    fireEvent.pointerMove(container.querySelector('.chart-viewport svg')!, {
      clientX: 330,
    });
    expect(reads).toBeLessThan(200);
    expect(detail().querySelector('data')).not.toBeNull();
  });

  it('usa el área pintada del SVG cuando hay márgenes por preserveAspectRatio', () => {
    const { container } = render(<Curve data={portfolio([100, 110, 120])} />);
    const svg = container.querySelector('.chart-viewport svg')!;
    vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({
      width: 1200,
      height: 280,
      left: 50,
      right: 1250,
      top: 0,
      bottom: 280,
      x: 50,
      y: 0,
      toJSON: () => ({}),
    });
    const points = drawnPoints(container);
    // 640x280 viewBox in a 1200x280 box: 280 CSS px of horizontal padding.
    fireEvent.pointerMove(svg, { clientX: 50 + 280 + points[0][0] });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-01',
    );
    fireEvent.pointerMove(svg, { clientX: 50 + 280 + points[1][0] });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-02',
    );
  });

  it('aplica la matriz real de transformación antes de elegir una observación', () => {
    const { container } = render(<Curve data={portfolio([100, 110, 120])} />);
    const svg = container.querySelector('.chart-viewport svg')!;
    const points = drawnPoints(container);
    Object.defineProperty(svg, 'getScreenCTM', {
      value: () => ({ inverse: () => ({ a: 2, c: 0, e: -100 }) }),
    });
    fireEvent.pointerMove(svg, { clientX: (points[1][0] + 100) / 2 });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-02',
    );
  });

  it('permite flechas, Inicio/Fin, zoom y Escape sin sustituir fechas por días rellenados', async () => {
    const data = portfolio([100, 105, 110, 115]);
    data[2].date = '2001-01-01';
    data[3].date = '2001-01-09';
    render(<Curve data={data} />);
    act(() => control().focus());
    await userEvent.keyboard('{Home}{ArrowRight}{ArrowRight}');
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2001-01-01',
    );
    expect(
      screen
        .getByRole('tooltip')
        .querySelector('time')
        ?.getAttribute('dateTime'),
    ).toBe('2001-01-01');
    await userEvent.keyboard('{End}');
    expect(detail().querySelector('data')?.getAttribute('value')).toBe('115');
    await userEvent.keyboard('+');
    expect(
      screen.getByRole('img').getAttribute('aria-labelledby'),
    ).toBeTruthy();
    expect(screen.getByText('2 observaciones')).not.toBeNull();
    await userEvent.keyboard('-');
    expect(screen.getByText('4 observaciones')).not.toBeNull();
    await userEvent.keyboard('{Escape}');
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(
      within(detail()).getByText(/Selecciona una observación/),
    ).not.toBeNull();
    expect(document.activeElement).toBe(control());
  });

  it('acota fechas inclusivas, pagina originales del tramo y restablece', async () => {
    const data = portfolio(
      Array.from({ length: 120 }, (_, index) => 100 + index),
    );
    render(<Curve data={data} />);
    await range(data[50].date, data[51].date);
    expect(screen.getByText('2 observaciones')).not.toBeNull();
    await userEvent.click(
      screen.getByRole('button', { name: 'Ver datos de la curva' }),
    );
    expect(
      screen.getAllByRole('rowheader').map((node) => node.textContent),
    ).toEqual(['51', '52']);
    expect(
      screen
        .getByRole('button', { name: 'Siguiente' })
        .hasAttribute('disabled'),
    ).toBe(true);
    await userEvent.click(
      screen.getByRole('button', { name: 'Restablecer curva' }),
    );
    expect(screen.getByText('120 observaciones')).not.toBeNull();
    expect(screen.getByRole('rowheader', { name: '1' })).not.toBeNull();
  });

  it('distingue intervalo vacío y rechazo de fechas invertidas, sin cambiar silenciosamente la vista', async () => {
    render(<Curve data={portfolio([100, 110])} />);
    await range('2000-01-02', '2000-01-01');
    expect(screen.getByRole('alert').textContent).toMatch(/posterior al fin/);
    expect(screen.getByText('2 observaciones')).not.toBeNull();
    await range('2001-01-01', '2001-01-02');
    expect(
      screen.getByText('No hay observaciones en el intervalo seleccionado.'),
    ).not.toBeNull();
    expect(
      screen.queryByRole('slider', { name: 'Observación de la curva' }),
    ).toBeNull();
    expect(
      screen
        .getByRole('slider', { name: 'Desplazar curva' })
        .hasAttribute('disabled'),
    ).toBe(true);
    expect(
      screen
        .getByRole('button', { name: 'Acercar curva' })
        .hasAttribute('disabled'),
    ).toBe(true);
    await userEvent.click(
      screen.getByRole('button', { name: 'Restablecer curva' }),
    );
    expect(screen.getByText('2 observaciones')).not.toBeNull();
  });

  it('muestra TWR desde el origen al recortar, sin modificar NAV ni datos', async () => {
    const data = portfolio([100, 200, 210]);
    data[1].twr_index = 1.05;
    data[2].twr_index = 1.1;
    const snapshot = JSON.stringify(data);
    render(<Curve data={data} />);
    await range('2000-01-02', '2000-01-03');
    await userEvent.selectOptions(
      screen.getByLabelText('Serie de la curva'),
      'twr',
    );
    act(() => control().focus());
    await userEvent.keyboard('{Home}');
    expect(within(detail()).getByText('5,00 %')).not.toBeNull();
    expect(
      within(screen.getByRole('tooltip')).getByText('5,00 %'),
    ).not.toBeNull();
    expect(
      screen.getByRole('tooltip').querySelector('data')?.getAttribute('value'),
    ).toBe('200');
    expect(detail().querySelector('data')?.getAttribute('value')).toBe('200');
    expect(
      screen.getByText(/sin reiniciar la base al recortar/),
    ).not.toBeNull();
    await userEvent.click(
      screen.getByRole('button', { name: 'Ver datos de la curva' }),
    );
    expect(screen.getByRole('cell', { name: /5,00\s%/ })).not.toBeNull();
    expect(JSON.stringify(data)).toBe(snapshot);
  });

  it('muestra estrategia y benchmark de la misma observación al cambiar a área y hacer zoom', async () => {
    const data: BacktestPoint[] = [
      { date: '2026-01-02', equity: 100, benchmark: 102 },
      { date: '2026-01-05', equity: 111, benchmark: 107 },
      { date: '2026-01-06', equity: 114, benchmark: 108 },
    ];
    const { container } = render(<Curve data={data} />);
    await userEvent.selectOptions(
      screen.getByLabelText('Representación de la curva'),
      'area',
    );
    expect(container.querySelector('.chart-viewport polygon')).not.toBeNull();
    expect(
      container.querySelector('.chart-viewport polyline[stroke-dasharray]'),
    ).not.toBeNull();
    act(() => control().focus());
    await userEvent.keyboard('{Home}{ArrowRight}');
    expect(
      Array.from(detail().querySelectorAll('data')).map((node) =>
        node.getAttribute('value'),
      ),
    ).toEqual(['111', '107']);
    expect(
      Array.from(screen.getByRole('tooltip').querySelectorAll('data')).map(
        (node) => node.getAttribute('value'),
      ),
    ).toEqual(['111', '107']);
    expect(
      screen
        .getByRole('tooltip')
        .querySelector('time')
        ?.getAttribute('dateTime'),
    ).toBe('2026-01-05');
    await userEvent.click(
      screen.getByRole('button', { name: 'Acercar curva' }),
    );
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2026-01-05',
    );
    expect(
      screen.getByText(/métricas del resultado conservan su periodo original/),
    ).not.toBeNull();
    expect(screen.queryByLabelText('Serie de la curva')).toBeNull();
  });

  it('mantiene el extremo final inspeccionado al ampliar con la lupa dentro de un rango y cambiar de estilo', async () => {
    const data: BacktestPoint[] = [
      { date: '2026-01-02', equity: 100, benchmark: 102 },
      { date: '2026-01-05', equity: 111, benchmark: 107 },
      { date: '2026-01-06', equity: 114, benchmark: 108 },
      { date: '2026-01-07', equity: 115, benchmark: 109 },
      { date: '2026-01-08', equity: 118, benchmark: 110 },
      { date: '2026-01-09', equity: 120, benchmark: 112 },
    ];
    const snapshot = JSON.stringify(data);
    const { container } = render(<Curve data={data} />);
    await range('2026-01-05', '2026-01-08');
    act(() => control().focus());
    await userEvent.keyboard('{End}');
    await userEvent.click(
      screen.getByRole('button', { name: 'Acercar curva' }),
    );
    expect(screen.getByText('2 observaciones')).not.toBeNull();
    expect(
      (
        screen.getByRole('slider', {
          name: 'Desplazar curva',
        }) as HTMLInputElement
      ).value,
    ).toBe('3');
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2026-01-08',
    );
    expect(
      Array.from(detail().querySelectorAll('data')).map((node) =>
        node.getAttribute('value'),
      ),
    ).toEqual(['118', '110']);
    await userEvent.selectOptions(
      screen.getByLabelText('Representación de la curva'),
      'area',
    );
    expect(container.querySelector('.chart-viewport polygon')).not.toBeNull();
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2026-01-08',
    );
    act(() => control().focus());
    await userEvent.keyboard('{End}');
    expect(
      screen
        .getByRole('tooltip')
        .querySelector('time')
        ?.getAttribute('dateTime'),
    ).toBe('2026-01-08');
    expect(
      Array.from(screen.getByRole('tooltip').querySelectorAll('data')).map(
        (node) => node.getAttribute('value'),
      ),
    ).toEqual(['118', '110']);
    expect(JSON.stringify(data)).toBe(snapshot);
  });

  it('desplaza una ventana conservando su cantidad y acota el cursor', async () => {
    render(<Curve data={portfolio([100, 101, 102, 103, 104, 105])} />);
    await range('2000-01-01', '2000-01-03');
    act(() => control().focus());
    await userEvent.keyboard('{Home}');
    const navigation = screen.getByRole('slider', { name: 'Desplazar curva' });
    fireEvent.change(navigation, { target: { value: '1' } });
    expect(screen.getByText('3 observaciones')).not.toBeNull();
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-02',
    );
    fireEvent.change(navigation, { target: { value: '0' } });
    expect((navigation as HTMLInputElement).value).toBe('0');
    expect((navigation as HTMLInputElement).max).toBe('3');
    expect(
      screen.queryByRole('button', { name: /Desplazar curva/ }),
    ).toBeNull();
  });

  it('abre y cierra la curva ampliada conservando el SVG, el rango y las observaciones', async () => {
    const data = portfolio([100, 105, 110, 115, 120, 125]);
    const snapshot = JSON.stringify(data);
    const { container } = render(<Curve data={data} />);
    await range('2000-01-02', '2000-01-05');
    const svg = control();
    await userEvent.click(
      screen.getByRole('button', {
        name: 'Pantalla completa: Curva de cartera',
      }),
    );
    expect(
      container.querySelector('.chart-workspace.is-expanded'),
    ).not.toBeNull();
    expect(control()).toBe(svg);
    expect(screen.getByText('4 observaciones')).not.toBeNull();
    act(() => control().focus());
    await userEvent.keyboard('{Home}');
    expect(detail().querySelector('data')?.getAttribute('value')).toBe('105');
    await userEvent.click(
      screen.getByRole('button', { name: /Salir de pantalla completa/ }),
    );
    expect(container.querySelector('.chart-workspace.is-expanded')).toBeNull();
    expect(control()).toBe(svg);
    expect(screen.getByText('4 observaciones')).not.toBeNull();
    expect(JSON.stringify(data)).toBe(snapshot);
  });

  it('reserva la rueda para la vista ampliada y conserva los datos originales', async () => {
    const data = portfolio(
      Array.from({ length: 12 }, (_, index) => 100 + index),
    );
    const snapshot = JSON.stringify(data);
    const { container } = render(<Curve data={data} />);
    vi.spyOn(control(), 'getBoundingClientRect').mockReturnValue({
      width: 640,
      height: 280,
      left: 0,
      right: 640,
      top: 0,
      bottom: 280,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
    fireEvent.wheel(control(), { deltaY: -100, clientX: 300, clientY: 100 });
    expect(screen.getByText('12 observaciones')).not.toBeNull();
    await userEvent.click(
      screen.getByRole('button', {
        name: 'Pantalla completa: Curva de cartera',
      }),
    );
    fireEvent.wheel(control(), { deltaY: -100, clientX: 300, clientY: 100 });
    await waitFor(() =>
      expect(container.querySelector('.chart-period')?.textContent).not.toBe(
        '12 observaciones',
      ),
    );
    expect(JSON.stringify(data)).toBe(snapshot);
    await userEvent.click(
      screen.getByRole('button', { name: 'Restablecer curva' }),
    );
    expect(screen.getByText('12 observaciones')).not.toBeNull();
  });

  it('arrastra la ventana ampliada sin variar su cantidad ni reabrir el tooltip con el click posterior', async () => {
    const data = portfolio(
      Array.from({ length: 12 }, (_, index) => 100 + index),
    );
    const snapshot = JSON.stringify(data);
    render(<Curve data={data} />);
    await range('2000-01-04', '2000-01-09');
    await userEvent.click(
      screen.getByRole('button', {
        name: 'Pantalla completa: Curva de cartera',
      }),
    );
    const svg = control();
    vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({
      width: 640,
      height: 280,
      left: 0,
      right: 640,
      top: 0,
      bottom: 280,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
    Object.defineProperty(svg, 'setPointerCapture', { value: vi.fn() });
    Object.defineProperty(svg, 'releasePointerCapture', { value: vi.fn() });
    Object.defineProperty(svg, 'hasPointerCapture', { value: () => true });
    fireEvent.pointerMove(svg, {
      clientX: 300,
      clientY: 100,
      pointerId: 1,
      pointerType: 'mouse',
    });
    expect(screen.getByRole('tooltip')).not.toBeNull();
    fireEvent.pointerDown(svg, {
      clientX: 300,
      clientY: 100,
      pointerId: 1,
      pointerType: 'mouse',
      button: 0,
    });
    fireEvent.pointerMove(svg, {
      clientX: 460,
      clientY: 100,
      pointerId: 1,
      pointerType: 'mouse',
      buttons: 1,
    });
    fireEvent.pointerUp(svg, {
      clientX: 460,
      clientY: 100,
      pointerId: 1,
      pointerType: 'mouse',
      button: 0,
    });
    fireEvent.click(svg, { clientX: 460, clientY: 100 });
    expect(screen.queryByRole('tooltip')).toBeNull();
    await waitFor(() =>
      expect(
        Number(
          (
            screen.getByRole('slider', {
              name: 'Desplazar curva',
            }) as HTMLInputElement
          ).value,
        ),
      ).toBeLessThan(3),
    );
    expect(screen.getByText('6 observaciones')).not.toBeNull();
    const start = Number(
      (
        screen.getByRole('slider', {
          name: 'Desplazar curva',
        }) as HTMLInputElement
      ).value,
    );
    act(() => svg.focus());
    await userEvent.keyboard('{Home}');
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      data[start].date,
    );
    expect(JSON.stringify(data)).toBe(snapshot);
  });

  it('no mantiene una selección cuyo día desaparece de una nueva serie', async () => {
    const { rerender } = render(<Curve data={portfolio([100, 110])} />);
    act(() => control().focus());
    await userEvent.keyboard('{End}');
    rerender(<Curve data={[{ date: '2026-01-01', nav: 500, twr_index: 1 }]} />);
    expect(within(detail()).queryByText(/110,00/)).toBeNull();
    expect(
      within(detail()).getByText(/Selecciona una observación/),
    ).not.toBeNull();
    expect(screen.queryByRole('tooltip')).toBeNull();
  });

  it('quita el deslizador y abre el detalle flotante solo al inspeccionar el SVG', () => {
    render(<Curve data={portfolio([100, 105, 110])} />);
    expect(
      screen.queryByRole('slider', { name: 'Observación de la curva' }),
    ).toBeNull();
    expect(screen.queryByText('Observación de la curva')).toBeNull();
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(control().getAttribute('tabindex')).toBe('0');
    act(() => control().focus());
    expect(screen.queryByRole('tooltip')).toBeNull();
    fireEvent.pointerMove(control(), { clientX: 300, clientY: 180 });
    const tooltip = screen.getByRole('tooltip');
    expect(tooltip.querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-02',
    );
    expect(tooltip.querySelector('data')?.getAttribute('value')).toBe('105');
    fireEvent.pointerLeave(control());
    expect(screen.queryByRole('tooltip')).toBeNull();
    fireEvent.pointerMove(control(), { clientX: 350, clientY: 200 });
    expect(screen.getByRole('tooltip')).not.toBeNull();
    fireEvent.blur(control());
    expect(screen.queryByRole('tooltip')).toBeNull();
  });

  it('admite eventos de puntero y oculta el detalle al abandonar el gráfico', () => {
    render(<Curve data={portfolio([100, 105, 110])} />);
    fireEvent.pointerMove(control(), {
      clientX: 300,
      clientY: 180,
      pointerType: 'mouse',
    });
    expect(
      screen.getByRole('tooltip').querySelector('data')?.getAttribute('value'),
    ).toBe('105');
    fireEvent.pointerLeave(control());
    expect(screen.queryByRole('tooltip')).toBeNull();
  });

  it('conserva el punto elegido con precisión fraccionaria tras el evento compatible de ratón', () => {
    const data = portfolio(
      Array.from({ length: 1100 }, (_, index) => 100 + index),
    );
    const { container } = render(<Curve data={data} />);
    const lastX = drawnPoints(container).at(-1)![0];
    Object.defineProperty(control(), 'getScreenCTM', {
      value: () => ({
        a: 1,
        b: 0,
        c: 0,
        d: 1,
        e: 0.75,
        f: 0,
        inverse: () => ({ a: 1, c: 0, e: -0.75 }),
      }),
    });
    const clientX = lastX + 0.75;
    fireEvent.pointerMove(control(), {
      clientX,
      clientY: 100,
      pointerType: 'mouse',
    });
    expect(
      screen
        .getByRole('tooltip')
        .querySelector('time')
        ?.getAttribute('dateTime'),
    ).toBe(data.at(-1)!.date);
    // Chromium follows PointerEvent coordinates with a compatibility MouseEvent
    // whose clientX is an integer. It must not replace the precise selection.
    fireEvent.mouseMove(control(), {
      clientX: Math.trunc(clientX),
      clientY: 100,
    });
    expect(
      screen
        .getByRole('tooltip')
        .querySelector('time')
        ?.getAttribute('dateTime'),
    ).toBe(data.at(-1)!.date);
    expect(
      screen.getByRole('tooltip').querySelector('data')?.getAttribute('value'),
    ).toBe(String(data.at(-1)!.nav));
    fireEvent.pointerDown(control(), {
      clientX,
      clientY: 100,
      button: 0,
      pointerId: 1,
      pointerType: 'mouse',
    });
    fireEvent.click(control(), {
      clientX: Math.trunc(clientX),
      clientY: 100,
    });
    expect(
      screen.getByRole('tooltip').querySelector('data')?.getAttribute('value'),
    ).toBe(String(data.at(-1)!.nav));
  });

  it('ancla la inspección por teclado al punto transformado al espacio de pantalla', async () => {
    const { container } = render(<Curve data={portfolio([100, 105, 110])} />);
    const point = drawnPoints(container)[1];
    Object.defineProperty(control(), 'getScreenCTM', {
      value: () => ({ a: 0.5, b: 0, c: 0, d: 0.5, e: 100, f: 50 }),
    });
    act(() => control().focus());
    await userEvent.keyboard('{Home}{ArrowRight}');
    const tooltip = screen.getByRole('tooltip');
    expect(tooltip.querySelector('data')?.getAttribute('value')).toBe('105');
    // In jsdom the tooltip has no dimensions; it sits within 32 CSS px of
    // the transformed original point, rather than using raw SVG coordinates.
    const left = Number.parseFloat(tooltip.style.left);
    const top = Number.parseFloat(tooltip.style.top);
    expect(left - (point[0] * 0.5 + 100)).toBeGreaterThan(0);
    expect(left - (point[0] * 0.5 + 100)).toBeLessThan(32);
    expect(top - (point[1] * 0.5 + 50)).toBeGreaterThan(0);
    expect(top - (point[1] * 0.5 + 50)).toBeLessThan(32);
  });

  it('oculta el detalle flotante al cambiar de fuente aunque conserve las fechas', () => {
    const { rerender } = render(<Curve data={portfolio([100, 110])} />);
    fireEvent.pointerMove(control(), { clientX: 620, clientY: 100 });
    expect(
      screen.getByRole('tooltip').querySelector('data')?.getAttribute('value'),
    ).toBe('110');
    rerender(<Curve data={portfolio([500, 600])} />);
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(
      within(detail()).getByText(/Selecciona una observación/),
    ).not.toBeNull();
    fireEvent.pointerMove(control(), { clientX: 620, clientY: 100 });
    expect(
      screen.getByRole('tooltip').querySelector('data')?.getAttribute('value'),
    ).toBe('600');
  });

  it('oculta el detalle flotante al cambiar la representación o la métrica', async () => {
    render(<Curve data={portfolio([100, 110])} />);
    fireEvent.pointerMove(control(), { clientX: 620, clientY: 100 });
    expect(screen.getByRole('tooltip')).not.toBeNull();
    await userEvent.selectOptions(
      screen.getByLabelText('Representación de la curva'),
      'area',
    );
    expect(screen.queryByRole('tooltip')).toBeNull();
    fireEvent.pointerMove(control(), { clientX: 620, clientY: 100 });
    expect(screen.getByRole('tooltip')).not.toBeNull();
    await userEvent.selectOptions(
      screen.getByLabelText('Serie de la curva'),
      'twr',
    );
    expect(screen.queryByRole('tooltip')).toBeNull();
  });

  it.each(['2026-02-30', '2000-01-01'])(
    'rechaza fechas inválidas o duplicadas (%s)',
    (date) => {
      const data = portfolio([100, 110]);
      data[1].date = date;
      render(<Curve data={data} />);
      expect(
        screen.getByText(/fechas no válidas, duplicadas o desordenadas/),
      ).not.toBeNull();
      expect(screen.queryByRole('slider')).toBeNull();
    },
  );
});
