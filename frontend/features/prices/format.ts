import { number } from '@/shared/format';

const differenceScientific = new Intl.NumberFormat('es-ES', {
  notation: 'scientific',
  maximumFractionDigits: 6,
});

/** Derived differences round display noise without changing their numeric value. */
export function priceDifference(amount: number | null): string {
  if (
    amount !== null &&
    Number.isFinite(amount) &&
    amount !== 0 &&
    (Math.abs(amount) < 1e-6 || Math.abs(amount) >= 1e21)
  ) {
    return differenceScientific.format(amount);
  }
  return number(amount, { maximumFractionDigits: 6 });
}

/** Preserve nonzero tiny values; the original table/readout keeps full precision. */
export function priceValue(amount: number | null): string {
  if (
    amount !== null &&
    amount !== 0 &&
    (Math.abs(amount) < 1e-20 || Math.abs(amount) >= 1e21)
  )
    return amount.toString();
  return number(amount, { maximumFractionDigits: 20 });
}

export function priceTick(amount: number): string {
  return amount !== 0 && (Math.abs(amount) < 0.0001 || Math.abs(amount) >= 1e7)
    ? amount.toExponential(2)
    : number(amount, { maximumFractionDigits: 6 });
}
