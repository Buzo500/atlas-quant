/** Calendar aggregation of supplied daily observations; never invent sessions. */
export type Interval = 'D' | 'W' | 'M';
export type DailyBar = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
};
export type PriceBar = DailyBar & {
  first_date: string;
  last_date: string;
  period_start: string;
  period_end: string;
  observations: number;
  partial_start: boolean;
  partial_end: boolean;
  completeness: 'observed' | 'unknown';
};
export const MAX_VISIBLE_BARS = 1000;
export const DEFAULT_VISIBLE_BARS = 120;
export const MAX_SOURCE_BARS = 100_000;

export function validDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith('0000'))
    return false;
  const instant = new Date(value + 'T00:00:00Z');
  return (
    Number.isFinite(instant.getTime()) &&
    instant.toISOString().slice(0, 10) === value
  );
}

export function validateBars(bars: readonly DailyBar[]): void {
  if (bars.length > MAX_SOURCE_BARS)
    throw new Error('El gráfico admite hasta 100.000 observaciones diarias.');
  let previous = '';
  for (const bar of bars) {
    if (!validDate(bar.date) || bar.date <= previous)
      throw new Error(
        'Las fechas de precios deben ser válidas, únicas y estar ordenadas.',
      );
    if (
      ![bar.open, bar.high, bar.low, bar.close].every(
        (value) => Number.isFinite(value) && value > 0,
      ) ||
      bar.low > Math.min(bar.open, bar.close) ||
      bar.high < Math.max(bar.open, bar.close)
    )
      throw new Error(
        'Hay precios OHLC no válidos; no se dibujará una serie alterada.',
      );
    if (bar.volume !== null && (!Number.isFinite(bar.volume) || bar.volume < 0))
      throw new Error('El volumen debe ser no negativo o estar ausente.');
    previous = bar.date;
  }
}

function civil(instant: Date): string {
  if (instant.getUTCFullYear() < 1) return '0001-01-01';
  if (instant.getUTCFullYear() > 9999) return '9999-12-31';
  return instant.toISOString().slice(0, 10);
}

export function period(date: string, interval: Interval): [string, string] {
  if (!validDate(date)) throw new Error('Fecha de sesión no válida.');
  if (interval === 'D') return [date, date];
  const begin = new Date(date + 'T00:00:00Z');
  if (interval === 'W')
    begin.setUTCDate(begin.getUTCDate() - ((begin.getUTCDay() + 6) % 7));
  else begin.setUTCDate(1);
  const end = new Date(begin);
  if (interval === 'W') end.setUTCDate(end.getUTCDate() + 6);
  else end.setUTCMonth(end.getUTCMonth() + 1, 0);
  return [civil(begin), civil(end)];
}

export function aggregateBars(
  bars: readonly DailyBar[],
  interval: Interval,
  bounds?: { start: string; end: string },
): PriceBar[] {
  validateBars(bars);
  if (!['D', 'W', 'M'].includes(interval))
    throw new Error('Intervalo no válido.');
  if (!bars.length) return [];
  const start = bounds?.start ?? bars[0].date;
  const end = bounds?.end ?? bars[bars.length - 1].date;
  if (
    !validDate(start) ||
    !validDate(end) ||
    start > end ||
    start > bars[0].date ||
    end < bars[bars.length - 1].date
  )
    throw new Error('Límites de agregación no válidos.');
  const result: PriceBar[] = [];
  for (const bar of bars) {
    const [first, last] = period(bar.date, interval);
    const current = result[result.length - 1];
    if (!current || current.period_start !== first) {
      result.push({
        ...bar,
        first_date: bar.date,
        last_date: bar.date,
        period_start: first,
        period_end: last,
        observations: 1,
        partial_start: interval !== 'D' && start > first,
        partial_end: interval !== 'D' && end < last,
        completeness: interval === 'D' ? 'observed' : 'unknown',
      });
    } else {
      current.high = Math.max(current.high, bar.high);
      current.low = Math.min(current.low, bar.low);
      current.close = bar.close;
      current.date = current.last_date = bar.date;
      current.observations += 1;
      current.volume =
        current.volume === null || bar.volume === null
          ? null
          : current.volume + bar.volume;
      if (current.volume !== null && !Number.isFinite(current.volume))
        throw new Error('Volumen agregado fuera de rango.');
    }
  }
  return result;
}

export function priceChange(close: number, previous: number | null) {
  if (
    !Number.isFinite(close) ||
    close <= 0 ||
    (previous !== null && (!Number.isFinite(previous) || previous <= 0))
  )
    throw new Error('El cambio requiere cierres positivos y finitos.');
  const relative = previous === null ? null : close / previous - 1;
  return {
    absolute: previous === null ? null : close - previous,
    relative: relative !== null && !Number.isFinite(relative) ? null : relative,
    relativeUnavailable: relative !== null && !Number.isFinite(relative),
  };
}

export function visibleWindow(total: number, start: number, count: number) {
  const size = Math.min(
    total,
    MAX_VISIBLE_BARS,
    Math.max(1, Math.floor(count)),
  );
  const first = Math.max(0, Math.min(Math.floor(start), total - size));
  return { start: first, end: first + size, count: size };
}
