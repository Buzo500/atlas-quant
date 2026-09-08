import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
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
    await user.tab();
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
