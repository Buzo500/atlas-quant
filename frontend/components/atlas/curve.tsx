'use client';

import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { BacktestPoint, PortfolioPoint } from '@/lib/api-types';
import { date as dateLabel, moneyEUR, number } from '@/shared/format';
import './curve.css';

type CurvePoint = PortfolioPoint | BacktestPoint;
const TABLE_PAGE_SIZE = 50;
const BENCHMARK_COLOR = '#69767F';

const axisNumber = new Intl.NumberFormat('es-ES', {
  maximumFractionDigits: 2,
  notation: 'compact',
});

/** Preserve each bucket's extrema in their original order, plus both endpoints. */
function visualIndices(values: number[], budget: number) {
  if (values.length <= budget) return values.map((_, index) => index);
  const buckets = Math.max(1, Math.floor((budget - 2) / 2));
  const indices = [0];
  for (let bucket = 0; bucket < buckets; bucket++) {
    const start = 1 + Math.floor((bucket * (values.length - 2)) / buckets);
    const end = 1 + Math.floor(((bucket + 1) * (values.length - 2)) / buckets);
    let low = start;
    let high = start;
    for (let index = start + 1; index < end; index++) {
      if (values[index] < values[low]) low = index;
      if (values[index] > values[high]) high = index;
    }
    indices.push(Math.min(low, high));
    if (low !== high) indices.push(Math.max(low, high));
  }
  indices.push(values.length - 1);
  return indices;
}

function seriesValue(point: CurvePoint) {
  return 'nav' in point ? point.nav : point.equity;
}

/** A measured SVG keeps type and stroke sizes stable on wide and narrow panels. */
export function Curve({ data }: { data: CurvePoint[] }) {
  const viewport = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 640, height: 280 });
  const id = useId();
  const [tableOpen, setTableOpen] = useState(false);
  const [requestedPage, setRequestedPage] = useState(0);

  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const measure = () => {
      const { width, height } = element.getBoundingClientRect();
      // Hidden tabs have no box. Keep the last size until they are visible again.
      if (width <= 0 || height <= 0) return;
      const next = { width: Math.round(width), height: Math.round(height) };
      setSize((previous) =>
        previous.width === next.width && previous.height === next.height
          ? previous
          : next,
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const { values, benchmark, minimum, maximum, valid } = useMemo(() => {
    const values: number[] = [];
    const comparison: number[] = [];
    let valid = data.length > 0;
    let completeBenchmark = data.length > 0;
    let minimum = Infinity;
    let maximum = -Infinity;
    for (const point of data) {
      const value = seriesValue(point);
      values.push(value);
      if (Number.isFinite(value)) {
        minimum = Math.min(minimum, value);
        maximum = Math.max(maximum, value);
      } else {
        valid = false;
      }
      if ('benchmark' in point && Number.isFinite(point.benchmark)) {
        comparison.push(point.benchmark);
      } else {
        completeBenchmark = false;
      }
    }
    const benchmark = valid && completeBenchmark ? comparison : null;
    if (benchmark) {
      for (const value of benchmark) {
        minimum = Math.min(minimum, value);
        maximum = Math.max(maximum, value);
      }
    }
    return {
      values,
      benchmark,
      valid,
      minimum: Number.isFinite(minimum) ? minimum : 0,
      maximum: Number.isFinite(maximum) ? maximum : 0,
    };
  }, [data]);
  const isBacktest = data.length > 0 && 'equity' in data[0];
  const seriesName = isBacktest ? 'Estrategia' : 'Patrimonio';

  // Work in normalized units so the domain remains finite for all finite inputs.
  const magnitude = Math.max(Math.abs(minimum), Math.abs(maximum), 1);
  const span = maximum / magnitude - minimum / magnitude;
  const padding = span > 0 ? span * 0.08 : 0.04;
  const lower = Math.max(
    -Number.MAX_VALUE / magnitude,
    minimum / magnitude - padding,
  );
  const upper = Math.min(
    Number.MAX_VALUE / magnitude,
    maximum / magnitude + padding,
  );
  const range = upper - lower || 1;
  const ticks = Array.from(
    { length: 5 },
    (_, index) => lower + (index / 4) * range,
  );
  const tickLabels = ticks.map((value) => axisNumber.format(value * magnitude));
  const left = Math.min(
    100,
    Math.max(48, ...tickLabels.map((label) => label.length * 7 + 12)),
  );
  const right = 16;
  const top = 28;
  const bottom = size.height - 34;
  const plotWidth = Math.max(1, size.width - left - right);
  const plotHeight = Math.max(1, bottom - top);
  const x = (index: number) =>
    left +
    (values.length === 1 ? 0.5 : index / (values.length - 1)) * plotWidth;
  const y = (value: number) =>
    bottom - ((value / magnitude - lower) / range) * plotHeight;
  const visualBudget = Math.max(128, Math.floor(plotWidth) * 2);
  const { primaryPoints, benchmarkPoints, reduced } = useMemo(() => {
    const points = (series: number[]) =>
      visualIndices(series, visualBudget)
        .map((index) => {
          const x =
            left +
            (series.length === 1 ? 0.5 : index / (series.length - 1)) *
              plotWidth;
          const y =
            bottom - ((series[index] / magnitude - lower) / range) * plotHeight;
          return `${x.toFixed(2)},${y.toFixed(2)}`;
        })
        .join(' ');
    return {
      primaryPoints: valid ? points(values) : '',
      benchmarkPoints: benchmark ? points(benchmark) : '',
      reduced: values.length > visualBudget,
    };
  }, [
    values,
    benchmark,
    valid,
    visualBudget,
    left,
    plotWidth,
    bottom,
    magnitude,
    lower,
    range,
    plotHeight,
  ]);
  const firstDate = dateLabel(data[0]?.date || '');
  const lastDate = dateLabel(data.at(-1)?.date || '');
  const lastValue = values.at(-1) ?? 0;
  const description = valid
    ? `${seriesName} en EUR. Escala lineal; eje horizontal por observaciones, sin distancias proporcionales entre fechas. ${number(values.length)} observaciones del ${firstDate} al ${lastDate}. Valor inicial ${moneyEUR(values[0])}; valor final ${moneyEUR(lastValue)}.${benchmark ? ` Mantener, con el mismo peso: valor final ${moneyEUR(benchmark.at(-1))}. La línea discontinua representa este benchmark.` : ''}${reduced ? ' El dibujo reduce puntos conservando los extremos de cada tramo; la tabla mantiene todos los datos originales.' : ''}`
    : data.length === 0
      ? 'No hay observaciones disponibles para representar la evolución.'
      : 'La serie contiene valores no válidos y no se puede representar.';
  const lastPage = Math.max(0, Math.ceil(data.length / TABLE_PAGE_SIZE) - 1);
  const page = Math.min(requestedPage, lastPage);
  const firstRow = page * TABLE_PAGE_SIZE;
  const lastRow = Math.min(firstRow + TABLE_PAGE_SIZE, data.length);

  return (
    <figure className="chart">
      <div className="chart-viewport" ref={viewport}>
        {!valid ? (
          <p className="chart-empty muted">{description}</p>
        ) : (
          /* oxlint-disable jsx-a11y/prefer-tag-over-role -- Inline SVG supplies the financial series and accessible description. */
          <svg
            viewBox={`0 0 ${size.width} ${size.height}`}
            role="img"
            aria-labelledby={`${id}-title ${id}-description`}
            style={{
              fontFamily: 'inherit',
              fontVariantNumeric: 'tabular-nums',
              fontSize: 12,
            }}
          >
            <title
              id={`${id}-title`}
            >{`${seriesName}: evolución en EUR`}</title>
            <desc id={`${id}-description`}>{description}</desc>
            <text x={left} y={14} fill="#62666A" fontSize="11">
              EUR
            </text>
            {ticks.map((_, index) => {
              const position = bottom - (index / 4) * plotHeight;
              return (
                <g key={index}>
                  <line
                    x1={left}
                    y1={position}
                    x2={left + plotWidth}
                    y2={position}
                    stroke="#DCD7CF"
                    strokeWidth="1"
                  />
                  <text
                    x={left - 10}
                    y={position}
                    dy="0.35em"
                    textAnchor="end"
                    fill="#62666A"
                  >
                    {tickLabels[index]}
                  </text>
                </g>
              );
            })}
            {benchmark && benchmark.length > 1 && (
              <polyline
                points={benchmarkPoints}
                fill="none"
                stroke={BENCHMARK_COLOR}
                strokeWidth="2"
                strokeDasharray="5 5"
                strokeLinejoin="round"
              />
            )}
            {values.length > 1 && (
              <polyline
                points={primaryPoints}
                fill="none"
                stroke="#526B80"
                strokeWidth="2.5"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            )}
            {values.length === 1 && (
              <>
                {benchmark && (
                  <circle
                    cx={x(0)}
                    cy={y(benchmark[0])}
                    r="5"
                    fill="#FFFCF6"
                    stroke={BENCHMARK_COLOR}
                    strokeWidth="2"
                  />
                )}
                <circle cx={x(0)} cy={y(values[0])} r="3.5" fill="#526B80" />
              </>
            )}
            {values.length === 1 ? (
              <text
                x={x(0)}
                y={size.height - 9}
                textAnchor="middle"
                fill="#62666A"
              >
                {firstDate}
              </text>
            ) : (
              <>
                <text
                  x={left}
                  y={size.height - 9}
                  textAnchor="start"
                  fill="#62666A"
                >
                  {firstDate}
                </text>
                {size.width >= 560 && data.length > 2 && (
                  <text
                    x={x(Math.floor((data.length - 1) / 2))}
                    y={size.height - 9}
                    textAnchor="middle"
                    fill="#62666A"
                  >
                    {dateLabel(data[Math.floor((data.length - 1) / 2)].date)}
                  </text>
                )}
                <text
                  x={left + plotWidth}
                  y={size.height - 9}
                  textAnchor="end"
                  fill="#62666A"
                >
                  {lastDate}
                </text>
              </>
            )}
          </svg>
          /* oxlint-enable jsx-a11y/prefer-tag-over-role */
        )}
      </div>
      {valid && (
        <figcaption className="chart-caption">
          <div className="chart-legend">
            <span>
              <i className="chart-key" aria-hidden="true" />
              {seriesName}
            </span>
            {benchmark && (
              <span>
                <i
                  className="chart-key benchmark"
                  style={{ borderColor: BENCHMARK_COLOR }}
                  aria-hidden="true"
                />
                Mantener · mismo peso
              </span>
            )}
          </div>
          <span className="chart-period">
            {number(data.length)} observaciones
          </span>
        </figcaption>
      )}
      {valid && (
        <p className="chart-context">
          EUR · Escala lineal · Eje horizontal por observaciones; las fechas no
          están separadas proporcionalmente.
          {reduced &&
            ' Dibujo reducido conservando los extremos de cada tramo. La tabla contiene todos los datos originales.'}
        </p>
      )}
      {data.length > 0 && (
        <div className="chart-data">
          <button
            type="button"
            className="chart-data-button"
            aria-expanded={tableOpen}
            aria-controls={`${id}-data`}
            onClick={() => setTableOpen((open) => !open)}
          >
            {tableOpen ? 'Ocultar datos de la curva' : 'Ver datos de la curva'}
          </button>
          <div
            id={`${id}-data`}
            className="chart-data-content"
            hidden={!tableOpen}
          >
            {tableOpen && (
              <>
                {/* oxlint-disable jsx-a11y/no-noninteractive-tabindex -- The scrollable data region must be reachable to scroll the table using a keyboard. */}
                <section
                  className="chart-data-scroll"
                  tabIndex={0}
                  aria-label="Tabla de valores de la curva"
                >
                  <table>
                    <caption>
                      Valores originales de{' '}
                      {seriesName.toLocaleLowerCase('es-ES')} en EUR
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Observación</th>
                        <th scope="col">Fecha de sesión</th>
                        <th scope="col">{seriesName} (EUR)</th>
                        {benchmark && (
                          <th scope="col">Mantener · mismo peso (EUR)</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {data.slice(firstRow, lastRow).map((point, offset) => (
                        <tr key={firstRow + offset}>
                          <th scope="row">{number(firstRow + offset + 1)}</th>
                          <td>{dateLabel(point.date)}</td>
                          <td>{moneyEUR(seriesValue(point))}</td>
                          {benchmark && (
                            <td>{moneyEUR(benchmark[firstRow + offset])}</td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
                {/* oxlint-enable jsx-a11y/no-noninteractive-tabindex */}
                <div className="chart-data-pagination">
                  <button
                    type="button"
                    className="chart-data-button"
                    disabled={page === 0}
                    onClick={() => setRequestedPage(page - 1)}
                  >
                    Anterior
                  </button>
                  <output aria-live="polite">
                    Filas {number(firstRow + 1)}–{number(lastRow)} de{' '}
                    {number(data.length)}
                  </output>
                  <button
                    type="button"
                    className="chart-data-button"
                    disabled={page === lastPage}
                    onClick={() => setRequestedPage(page + 1)}
                  >
                    Siguiente
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </figure>
  );
}
