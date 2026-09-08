import { act, fireEvent, render, screen, within } from '@testing-library/react';
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
  return (container.querySelector('polyline')?.getAttribute('points') ?? '')
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
    expect(container.querySelector('circle')).not.toBeNull();
    expect(container.querySelector('polyline')).toBeNull();
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
    const benchmark = container.querySelector('polyline[stroke-dasharray]');
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
    expect(container.querySelector('polyline[stroke-dasharray]')).toBeNull();
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
  const control = () =>
    screen.getByRole('slider', { name: 'Observación de la curva' });
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
    const gaps = points
      .slice(1)
      .map((point, index) => ({
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
    fireEvent.mouseMove(container.querySelector('svg')!, { clientX: x });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      data[index].date,
    );
    expect(detail().querySelector('data')?.getAttribute('value')).toBe(
      String(data[index].nav),
    );
    expect(Number((control() as HTMLInputElement).value)).toBe(index);
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
    const svg = container.querySelector('svg')!;
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
    fireEvent.mouseMove(svg, { clientX: 100 });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-01',
    );
    fireEvent.mouseMove(svg, { clientX: 700 });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-03',
    );
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
    fireEvent.mouseMove(container.querySelector('svg')!, { clientX: 300 });
    fireEvent.mouseMove(container.querySelector('svg')!, { clientX: 330 });
    expect(reads).toBeLessThan(200);
    expect(detail().querySelector('data')).not.toBeNull();
  });

  it('usa el área pintada del SVG cuando hay márgenes por preserveAspectRatio', () => {
    const { container } = render(<Curve data={portfolio([100, 110, 120])} />);
    const svg = container.querySelector('svg')!;
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
    fireEvent.mouseMove(svg, { clientX: 50 + 280 + points[0][0] });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-01',
    );
    fireEvent.mouseMove(svg, { clientX: 50 + 280 + points[1][0] });
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-02',
    );
  });

  it('aplica la matriz real de transformación antes de elegir una observación', () => {
    const { container } = render(<Curve data={portfolio([100, 110, 120])} />);
    const svg = container.querySelector('svg')!;
    const points = drawnPoints(container);
    Object.defineProperty(svg, 'getScreenCTM', {
      value: () => ({ inverse: () => ({ a: 2, c: 0, e: -100 }) }),
    });
    fireEvent.mouseMove(svg, { clientX: (points[1][0] + 100) / 2 });
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
    expect(screen.queryByRole('slider')).toBeNull();
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
    expect(container.querySelector('polygon')).not.toBeNull();
    expect(
      container.querySelector('polyline[stroke-dasharray]'),
    ).not.toBeNull();
    act(() => control().focus());
    await userEvent.keyboard('{Home}{ArrowRight}');
    expect(
      Array.from(detail().querySelectorAll('data')).map((node) =>
        node.getAttribute('value'),
      ),
    ).toEqual(['111', '107']);
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

  it('desplaza una ventana conservando su cantidad y acota el cursor', async () => {
    render(<Curve data={portfolio([100, 101, 102, 103, 104, 105])} />);
    await range('2000-01-01', '2000-01-03');
    act(() => control().focus());
    await userEvent.keyboard('{Home}');
    await userEvent.click(
      screen.getByRole('button', { name: 'Desplazar curva adelante' }),
    );
    expect(screen.getByText('3 observaciones')).not.toBeNull();
    expect(detail().querySelector('time')?.getAttribute('dateTime')).toBe(
      '2000-01-02',
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Desplazar curva atrás' }),
    );
    expect(
      screen
        .getByRole('button', { name: 'Desplazar curva atrás' })
        .hasAttribute('disabled'),
    ).toBe(true);
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
