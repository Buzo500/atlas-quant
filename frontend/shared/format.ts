/** Display-only formatting. Values retain their API units and are never coerced. */
export const DISPLAY_LOCALE = 'es-ES';
export const DISPLAY_TIME_ZONE = 'Europe/Madrid';
export const MISSING_VALUE = '—';
export const INVALID_VALUE = 'Dato no válido';

type NumericValue = number | null | undefined;
type DateValue = string | null | undefined;
type Precision = Pick<
  Intl.NumberFormatOptions,
  'minimumFractionDigits' | 'maximumFractionDigits'
>;

const eurFormatter = new Intl.NumberFormat(DISPLAY_LOCALE, {
  style: 'currency',
  currency: 'EUR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const usdFormatter = new Intl.NumberFormat(DISPLAY_LOCALE, {
  style: 'currency',
  currency: 'USD',
  currencyDisplay: 'code',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const apiUsdFormatter = new Intl.NumberFormat(DISPLAY_LOCALE, {
  style: 'currency',
  currency: 'USD',
  currencyDisplay: 'code',
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
});
const percentFormatter = new Intl.NumberFormat(DISPLAY_LOCALE, {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const numberFormatters = new Map<string, Intl.NumberFormat>();

function numeric(value: NumericValue, formatter: Intl.NumberFormat): string {
  if (value == null) return MISSING_VALUE;
  if (!Number.isFinite(value)) return INVALID_VALUE;
  return formatter.format(value);
}

export const moneyEUR = (value: NumericValue): string =>
  numeric(value, eurFormatter);
export const moneyUSD = (value: NumericValue): string =>
  numeric(value, usdFormatter);
/** API spend and reservations use USD with four decimal places, not EUR. */
export const apiCostUSD = (value: NumericValue): string =>
  numeric(value, apiUsdFormatter);
/** Input is a ratio: 0.25 is 25 %, not 0.25 %. */
export const percent = (value: NumericValue): string =>
  numeric(value, percentFormatter);

/** Set precision for the displayed quantity: counts 0, holdings up to 6, Sharpe 2. */
export function number(value: NumericValue, precision: Precision = {}): string {
  if (value == null) return MISSING_VALUE;
  if (!Number.isFinite(value)) return INVALID_VALUE;
  const minimumFractionDigits = precision.minimumFractionDigits ?? 0;
  const maximumFractionDigits =
    precision.maximumFractionDigits ?? Math.max(2, minimumFractionDigits);
  // A bad precision is a programming error. Bound it to keep the cache finite.
  if (
    !Number.isInteger(minimumFractionDigits) ||
    !Number.isInteger(maximumFractionDigits) ||
    minimumFractionDigits < 0 ||
    maximumFractionDigits > 20 ||
    maximumFractionDigits < minimumFractionDigits
  ) {
    throw new RangeError('La precisión debe estar entre 0 y 20 decimales.');
  }
  const key = `${minimumFractionDigits}:${maximumFractionDigits}`;
  let formatter = numberFormatters.get(key);
  if (!formatter) {
    formatter = new Intl.NumberFormat(DISPLAY_LOCALE, {
      minimumFractionDigits,
      maximumFractionDigits,
    });
    numberFormatters.set(key, formatter);
  }
  return formatter.format(value);
}

const civilDateFormatter = new Intl.DateTimeFormat(DISPLAY_LOCALE, {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  timeZone: 'UTC',
});
const timestampDateFormatter = new Intl.DateTimeFormat(DISPLAY_LOCALE, {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  timeZone: DISPLAY_TIME_ZONE,
});
const timestampClockFormatter = new Intl.DateTimeFormat(DISPLAY_LOCALE, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hourCycle: 'h23',
  timeZone: DISPLAY_TIME_ZONE,
});

function isCivilDate(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const year = Number(match[1]),
    month = Number(match[2]),
    day = Number(match[3]);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return (
    year >= 1 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1]
  );
}

/** An ISO civil date is a calendar label, not an instant. Its day never shifts. */
export function date(value: DateValue): string {
  if (value == null) return MISSING_VALUE;
  if (typeof value !== 'string' || !isCivilDate(value)) return INVALID_VALUE;
  const [year, month, day] = value.split('-').map(Number);
  const civil = new Date(0);
  // setUTCFullYear also handles years 0001–0099 without Date.UTC's 1900 offset.
  civil.setUTCFullYear(year, month - 1, day);
  return civilDateFormatter.format(civil);
}

function instant(value: string): Date | null {
  // Require a zone: a naive timestamp must not silently inherit the PC's zone.
  const match =
    /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})$/.exec(
      value,
    );
  if (!match || !isCivilDate(match[1])) return null;
  if (Number(match[2]) > 23 || Number(match[3]) > 59 || Number(match[4]) > 59)
    return null;
  const zone = match[6];
  if (
    zone !== 'Z' &&
    (Number(zone.slice(1, 3)) > 23 || Number(zone.slice(4)) > 59)
  )
    return null;
  // Python emits microseconds. Normalize explicitly to JS milliseconds.
  const fraction = (match[5] ?? '').padEnd(3, '0').slice(0, 3);
  const parsed = new Date(
    `${match[1]}T${match[2]}:${match[3]}:${match[4]}.${fraction}${zone}`,
  );
  return Number.isFinite(parsed.getTime()) ? parsed : null;
}

function timestamp(value: DateValue, format: (parsed: Date) => string): string {
  if (value == null) return MISSING_VALUE;
  if (typeof value !== 'string') return INVALID_VALUE;
  const parsed = instant(value);
  return parsed ? format(parsed) : INVALID_VALUE;
}

/** Instants always use Europe/Madrid, including its daylight-saving rules. */
export const dateTime = (value: DateValue): string =>
  timestamp(
    value,
    (parsed) =>
      `${timestampDateFormatter.format(parsed)}, ${timestampClockFormatter.format(parsed)} (${DISPLAY_TIME_ZONE})`,
  );
/** Parts for a two-line <time>; label the clock zone in its accessible text. */
export const dateTimeDate = (value: DateValue): string =>
  timestamp(value, (parsed) => timestampDateFormatter.format(parsed));
export const dateTimeClock = (value: DateValue): string =>
  timestamp(
    value,
    (parsed) =>
      `${timestampClockFormatter.format(parsed)} (${DISPLAY_TIME_ZONE})`,
  );
