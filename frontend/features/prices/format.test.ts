import { expect, it } from 'vitest';
import { priceDifference, priceValue } from './format';

it('redondea solo la presentación del cambio derivado a seis decimales', () => {
  const raw = 0.050800999999999874;
  expect(priceDifference(raw)).toBe('0,050801');
  expect(priceDifference(-raw)).toBe('-0,050801');
  expect(priceValue(raw)).toBe('0,050800999999999874');
});

it('distingue cambios pequeños no nulos de cero y de un dato ausente', () => {
  expect(priceDifference(1e-8)).toBe('1E-8');
  expect(priceDifference(-1e-8)).toBe('-1E-8');
  expect(priceDifference(Number.MIN_VALUE)).toBe('5E-324');
  expect(priceDifference(0)).toBe('0');
  expect(priceDifference(null)).toBe('—');
});
