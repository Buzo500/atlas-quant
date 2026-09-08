import { describe, expect, it } from 'vitest';
import {
  aggregateBars,
  period,
  priceChange,
  validateBars,
  visibleWindow,
  type DailyBar,
} from './aggregation';
import { priceTick, priceValue } from './format';

const bar = (date: string, change: Partial<DailyBar> = {}): DailyBar => ({
  date,
  open: 10,
  high: 14,
  low: 9,
  close: 12,
  volume: 0,
  ...change,
});

describe('Agregación de observaciones originales', () => {
  it('agrupa la semana ISO que cruza el año sin partirla el 1 de enero', () => {
    expect(period('2021-01-01', 'W')).toEqual(['2020-12-28', '2021-01-03']);
    const original = [
      bar('2020-12-30'),
      bar('2021-01-01', { open: 12, high: 20, low: 11, close: 18, volume: 7 }),
      bar('2021-01-04'),
    ];
    expect(aggregateBars(original, 'W')).toEqual([
      expect.objectContaining({
        period_start: '2020-12-28',
        first_date: '2020-12-30',
        last_date: '2021-01-01',
        open: 10,
        high: 20,
        low: 9,
        close: 18,
        volume: 7,
        observations: 2,
        partial_start: true,
        partial_end: false,
        completeness: 'unknown',
      }),
      expect.objectContaining({
        period_start: '2021-01-04',
        observations: 1,
        partial_start: false,
        partial_end: true,
      }),
    ]);
    expect(original[0].close).toBe(12);
  });
  it('respeta febrero bisiesto y un mes de 28 días', () => {
    expect(period('2024-02-29', 'M')).toEqual(['2024-02-01', '2024-02-29']);
    expect(period('2023-02-15', 'M')).toEqual(['2023-02-01', '2023-02-28']);
    const result = aggregateBars(
      [bar('2024-02-01'), bar('2024-02-29'), bar('2024-03-01')],
      'M',
    );
    expect(result[0]).toMatchObject({
      period_end: '2024-02-29',
      observations: 2,
      partial_start: false,
      partial_end: false,
      completeness: 'unknown',
    });
    expect(result[1]).toMatchObject({
      period_start: '2024-03-01',
      observations: 1,
      partial_end: true,
    });
  });
  it('mantiene huecos, meses ausentes y no afirma completitud por contar sesiones', () => {
    const result = aggregateBars(
      [bar('2026-01-01'), bar('2026-01-31'), bar('2026-03-01')],
      'M',
    );
    expect(result).toHaveLength(2);
    expect(result[0]).toMatchObject({
      observations: 2,
      completeness: 'unknown',
      partial_start: false,
      partial_end: false,
    });
  });
  it('distingue un volumen ausente de cero y no publica una suma parcial', () => {
    expect(
      aggregateBars([bar('2026-02-02'), bar('2026-02-03')], 'W')[0].volume,
    ).toBe(0);
    expect(
      aggregateBars(
        [
          bar('2026-02-02', { volume: 100 }),
          bar('2026-02-03', { volume: null }),
        ],
        'W',
      )[0].volume,
    ).toBeNull();
  });
  it('conserva una sola observación y los extremos de un rango parcial', () => {
    const source = [bar('2026-02-04')];
    expect(aggregateBars(source, 'D')[0]).toMatchObject({
      ...source[0],
      observations: 1,
      completeness: 'observed',
      partial_start: false,
      partial_end: false,
    });
    expect(
      aggregateBars(source, 'W', { start: '2026-02-03', end: '2026-02-05' })[0],
    ).toMatchObject({ partial_start: true, partial_end: true });
    expect(aggregateBars([], 'W')).toEqual([]);
  });
  it.each([
    [bar('2026-02-30')],
    [bar('2026-01-01'), bar('2026-01-01')],
    [bar('2026-01-02'), bar('2026-01-01')],
    [bar('2026-01-01', { close: NaN })],
    [bar('2026-01-01', { high: Infinity })],
    [bar('2026-01-01', { low: 0 })],
    [bar('2026-01-01', { close: 20 })],
    [bar('2026-01-01', { volume: -1 })],
    [bar('2026-01-01', { volume: Infinity })],
  ])(
    'rechaza datos inválidos sin corregirlos silenciosamente: %j',
    (...source) => {
      expect(() => validateBars(source)).toThrow();
    },
  );
  it('rechaza sumas fuera de rango y respuestas de más de 100.000 filas', () => {
    expect(() =>
      aggregateBars(
        [
          bar('2026-01-01', { volume: Number.MAX_VALUE }),
          bar('2026-01-02', { volume: Number.MAX_VALUE }),
        ],
        'M',
      ),
    ).toThrow('Volumen agregado fuera de rango');
    expect(() => validateBars(Array(100001).fill(bar('2026-01-01')))).toThrow(
      '100.000',
    );
  });
  it('usa cierre anterior real y deja explícito el porcentaje fuera de rango', () => {
    expect(priceChange(110, 100)).toMatchObject({
      absolute: 10,
      relative: expect.closeTo(0.1),
      relativeUnavailable: false,
    });
    expect(priceChange(110, null)).toMatchObject({
      absolute: null,
      relative: null,
      relativeUnavailable: false,
    });
    expect(priceChange(Number.MAX_VALUE, Number.MIN_VALUE)).toMatchObject({
      relative: null,
      relativeUnavailable: true,
    });
    expect(() => priceChange(1, 0)).toThrow();
  });
  it('limita solo la ventana y permite llegar a ambos extremos de 100.000 barras', () => {
    expect(visibleWindow(100000, 99000, 90000)).toEqual({
      start: 99000,
      end: 100000,
      count: 1000,
    });
    expect(visibleWindow(100000, -15, 120)).toEqual({
      start: 0,
      end: 120,
      count: 120,
    });
    expect(visibleWindow(1, 0, 120)).toEqual({ start: 0, end: 1, count: 1 });
  });
  it('no redondea a cero valores pequeños ni imprime cientos de dígitos en un eje', () => {
    expect(priceValue(1e-8)).toBe('0,00000001');
    expect(priceValue(Number.MIN_VALUE)).toBe('5e-324');
    expect(priceTick(Number.MAX_VALUE)).toBe('1.80e+308');
    expect(priceTick(1e-8)).toBe('1.00e-8');
  });
});
