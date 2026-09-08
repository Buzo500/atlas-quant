import { describe, expect, it, vi } from 'vitest';
import {
  apiCostUSD,
  date,
  dateTime,
  dateTimeClock,
  dateTimeDate,
  INVALID_VALUE,
  MISSING_VALUE,
  moneyEUR,
  moneyUSD,
  number,
  percent,
} from './format';

// Currency/percent separators are nonbreaking spaces in Intl output.
const spaces = (value: string) => value.replace(/[\u00a0\u202f]/g, ' ');

describe('Unidades y números es-ES', () => {
  it('distingue EUR y USD sin convertir el importe', () => {
    expect(spaces(moneyEUR(12345.678))).toBe('12.345,68 €');
    expect(spaces(moneyUSD(12345.678))).toBe('12.345,68 USD');
    expect(spaces(moneyEUR(-12.5))).toBe('-12,50 €');
  });
  it('conserva cuatro decimales de gasto API, incluida una fracción de céntimo', () => {
    expect(spaces(apiCostUSD(0.0001))).toBe('0,0001 USD');
    expect(spaces(apiCostUSD(0.025))).toBe('0,0250 USD');
  });
  it('formatea ratios como porcentajes y Sharpe como número sin unidad', () => {
    expect(spaces(percent(0.25))).toBe('25,00 %');
    expect(spaces(percent(-0.062))).toBe('-6,20 %');
    expect(number(0.5, { minimumFractionDigits: 2 })).toBe('0,50');
  });
  it('respeta la precisión de cantidades y contadores', () => {
    expect(number(12345.123456, { maximumFractionDigits: 6 })).toBe(
      '12.345,123456',
    );
    expect(number(220, { maximumFractionDigits: 0 })).toBe('220');
    expect(
      number(1.25, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
    ).toBe('1,3');
  });
  it('presenta cero como un valor existente', () => {
    expect(spaces(moneyEUR(0))).toBe('0,00 €');
    expect(spaces(moneyUSD(0))).toBe('0,00 USD');
    expect(spaces(apiCostUSD(0))).toBe('0,0000 USD');
    expect(spaces(percent(0))).toBe('0,00 %');
    expect(number(0)).toBe('0');
  });
  it.each([moneyEUR, moneyUSD, apiCostUSD, percent, number])(
    'distingue ausencia de invalidez con %s',
    (format) => {
      expect(format(null)).toBe(MISSING_VALUE);
      expect(format(undefined)).toBe(MISSING_VALUE);
      for (const value of [NaN, Infinity, -Infinity])
        expect(format(value)).toBe(INVALID_VALUE);
    },
  );
  it('no crea formateadores de números repetidamente para una misma precisión', () => {
    const constructor = vi.spyOn(Intl, 'NumberFormat');
    const precision = { minimumFractionDigits: 7, maximumFractionDigits: 7 };
    number(1, precision);
    number(2, precision);
    expect(constructor).toHaveBeenCalledTimes(1);
  });
});

describe('Fechas civiles y zona explícita', () => {
  it('conserva fechas civiles junto a cambios de día y horario de verano', () => {
    expect(date('2026-01-01')).toBe('01/01/2026');
    expect(date('2026-03-29')).toBe('29/03/2026');
    expect(date('2026-10-25')).toBe('25/10/2026');
    expect(date('2024-02-29')).toBe('29/02/2024');
    expect(date('2000-02-29')).toBe('29/02/2000');
  });
  it.each([
    '2025-02-29',
    '1900-02-29',
    '2026-02-30',
    '2026-04-31',
    '2026-00-01',
    '2026-13-01',
    '2026-01-00',
    '0000-01-01',
    '2026-1-1',
    '01/01/2026',
    '',
    '2026-01-01T00:00:00Z',
  ])('rechaza la fecha civil inválida %s', (value) => {
    expect(date(value)).toBe(INVALID_VALUE);
  });
  it('convierte instantes con offset a Madrid, incluso a otro día o año', () => {
    expect(dateTime('2025-12-31T23:30:00Z')).toBe(
      '01/01/2026, 00:30:00 (Europe/Madrid)',
    );
    expect(dateTime('2026-07-01T23:30:00+00:00')).toBe(
      '02/07/2026, 01:30:00 (Europe/Madrid)',
    );
    expect(dateTime('2026-01-01T00:30:00+03:00')).toBe(
      '31/12/2025, 22:30:00 (Europe/Madrid)',
    );
  });
  it('respeta el salto de primavera y la hora repetida de otoño', () => {
    expect(dateTimeClock('2026-03-29T00:59:59Z')).toBe(
      '01:59:59 (Europe/Madrid)',
    );
    expect(dateTimeClock('2026-03-29T01:00:00Z')).toBe(
      '03:00:00 (Europe/Madrid)',
    );
    expect(dateTimeClock('2026-10-25T00:30:00Z')).toBe(
      '02:30:00 (Europe/Madrid)',
    );
    expect(dateTimeClock('2026-10-25T01:30:00Z')).toBe(
      '02:30:00 (Europe/Madrid)',
    );
  });
  it('acepta precisión de microsegundos del motor sin alterar la fecha', () => {
    expect(dateTimeDate('2026-09-08T23:59:59.123456+00:00')).toBe('09/09/2026');
    expect(dateTimeClock('2026-09-08T23:59:59.123456+00:00')).toBe(
      '01:59:59 (Europe/Madrid)',
    );
  });
  it.each([
    '2026-01-01',
    '2026-01-01T12:00:00',
    '2026-02-30T12:00:00Z',
    '2026-01-01T24:00:00Z',
    '2026-01-01T23:60:00Z',
    '2026-01-01T23:59:60Z',
    '2026-01-01T12:00:00+24:00',
    '2026-01-01T12:00:00+01:60',
    '',
    'malformed',
  ])('no interpreta ni normaliza el timestamp inválido %s', (value) => {
    expect(dateTime(value)).toBe(INVALID_VALUE);
    expect(dateTimeDate(value)).toBe(INVALID_VALUE);
    expect(dateTimeClock(value)).toBe(INVALID_VALUE);
  });
  it.each([date, dateTime, dateTimeDate, dateTimeClock])(
    'mantiene explícita la ausencia con %s',
    (format) => {
      expect(format(null)).toBe(MISSING_VALUE);
      expect(format(undefined)).toBe(MISSING_VALUE);
    },
  );
});
