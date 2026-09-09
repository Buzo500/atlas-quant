'use client';

import {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { BacktestPoint, PortfolioPoint } from '@/lib/api-types';
import { date as dateLabel, moneyEUR, number, percent } from '@/shared/format';
import {
  ChartTooltip,
  type ChartTooltipAnchor,
} from '@/shared/components/chart-tooltip';
import { ChartWorkspace } from '@/shared/components/chart-workspace';
import { useChartGestures } from '@/shared/components/chart-gestures';
import {
  dateWindow,
  nearestObservation,
  zoomWindow,
  type CurveWindow,
} from './curve-window';
import './curve.css';

type CurvePoint = PortfolioPoint | BacktestPoint;
const TABLE_PAGE_SIZE = 50;
const BENCHMARK_COLOR = '#69767F';

const axisNumber = new Intl.NumberFormat('es-ES', {
  maximumFractionDigits: 2,
  notation: 'compact',
});
const axisPercent = new Intl.NumberFormat('es-ES', {
  style: 'percent',
  maximumFractionDigits: 2,
  notation: 'compact',
});
const axisScientific = new Intl.NumberFormat('es-ES', {
  maximumFractionDigits: 2,
  notation: 'scientific',
});
const axisScientificPercent = new Intl.NumberFormat('es-ES', {
  style: 'percent',
  maximumFractionDigits: 2,
  notation: 'scientific',
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
export function Curve({ data: original }: { data: CurvePoint[] }) {
  const viewport = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [size, setSize] = useState({ width: 640, height: 280 });
  const measuredSize = useRef(size);
  const keyboardGeometry = useRef(size);
  const id = useId();
  const [tableOpen, setTableOpen] = useState(false);
  const [requestedPage, setRequestedPage] = useState(0);
  const [metric, setMetric] = useState<'value' | 'twr'>('value');
  const [style, setStyle] = useState<'line' | 'area'>('line');
  const [requestedRange, setRequestedRange] = useState({ from: '', to: '' });
  const [draftRange, setDraftRange] = useState({ from: '', to: '' });
  const [rangeError, setRangeError] = useState('');
  const [selection, setSelection] = useState<{
    date: string;
    source: CurvePoint[];
  } | null>(null);
  const [tooltip, setTooltip] = useState<{
    anchor: ChartTooltipAnchor;
    source: CurvePoint[];
    range: typeof requestedRange;
    metric: typeof metric;
    style: typeof style;
    keyboard: boolean;
  } | null>(null);
  const selectedDate = selection?.source === original ? selection.date : null;
  const setSelectedDate = (date: string | null) =>
    setSelection(date === null ? null : { date, source: original });

  const source = useMemo(() => {
    let ordered = true;
    let valid = original.length > 0;
    let hasTwr = original.length > 0;
    for (let index = 0; index < original.length; index++) {
      const point = original[index];
      const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(point.date);
      const year = Number(match?.[1]),
        month = Number(match?.[2]),
        day = Number(match?.[3]);
      const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
      const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
      if (
        !match ||
        year < 1 ||
        month < 1 ||
        month > 12 ||
        day < 1 ||
        day > days[month - 1] ||
        (index > 0 && original[index - 1].date >= point.date)
      )
        ordered = false;
      if (!Number.isFinite(seriesValue(point))) valid = false;
      if (!('twr_index' in point) || !Number.isFinite(point.twr_index))
        hasTwr = false;
    }
    return { ordered, valid: valid && ordered, hasTwr };
  }, [original]);
  const twrMode = metric === 'twr' && source.hasTwr;
  const window = useMemo(
    () => dateWindow(original, requestedRange.from, requestedRange.to),
    [original, requestedRange],
  );
  const data = useMemo(
    () => original.slice(window.start, Math.max(window.start, window.end + 1)),
    [original, window],
  );
  const selectedIndex = useMemo(() => {
    if (selectedDate === null || data.length === 0) return null;
    const index = dateWindow(original, selectedDate, selectedDate).start;
    return index >= window.start &&
      index <= window.end &&
      original[index]?.date === selectedDate
      ? index
      : null;
  }, [original, selectedDate, data.length, window]);
  const valueOf = useCallback(
    (point: CurvePoint) =>
      twrMode && 'twr_index' in point ? point.twr_index - 1 : seriesValue(point),
    [twrMode],
  );
  const formatValue = (value: number | null | undefined) =>
    twrMode ? percent(value) : moneyEUR(value);
  const unit = twrMode ? '%' : 'EUR';
  const selectedPoint = selectedIndex === null ? null : original[selectedIndex];
  const setWindow = (next: CurveWindow) => {
    const from = original[next.start]?.date ?? '',
      to = original[next.end]?.date ?? '';
    setRequestedRange({ from, to });
    setDraftRange({ from, to });
    setRangeError('');
    setRequestedPage(0);
    if (selectedIndex !== null)
      setSelectedDate(
        original[Math.max(next.start, Math.min(next.end, selectedIndex))]
          ?.date ?? null,
      );
  };
  const zoom = (factor: number) =>
    setWindow(
      zoomWindow(
        window,
        original.length,
        factor,
        selectedIndex ?? Math.floor((window.start + window.end) / 2),
      ),
    );
  const reset = () => {
    setRequestedRange({ from: '', to: '' });
    setDraftRange({ from: '', to: '' });
    setRangeError('');
    setRequestedPage(0);
  };

  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const measure = () => {
      const { width, height } = element.getBoundingClientRect();
      // Hidden tabs have no box. Keep the last size until they are visible again.
      if (width <= 0 || height <= 0) return;
      const next = { width: Math.round(width), height: Math.round(height) };
      // The inspection readout can wrap and take height from the expanded plot.
      // That must not dismiss the first hover that caused the readout to appear.
      // Pointer anchors remain in viewport pixels; width changes invalidate them.
      if (measuredSize.current.width !== next.width) setTooltip(null);
      measuredSize.current = next;
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
    let valid = source.valid && data.length > 0;
    let completeBenchmark = data.length > 0;
    let minimum = Infinity;
    let maximum = -Infinity;
    for (const point of data) {
      const value =
        twrMode && 'twr_index' in point
          ? point.twr_index - 1
          : seriesValue(point);
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
  }, [data, twrMode, source.valid]);
  const isBacktest = original.length > 0 && 'equity' in original[0];
  const seriesName = twrMode
    ? 'TWR desde el origen'
    : isBacktest
      ? 'Estrategia'
      : 'Patrimonio';

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
  const tickLabels = ticks.map((value) => {
    const real = value * magnitude;
    const label = (twrMode ? axisPercent : axisNumber).format(real);
    return label.length > 14
      ? (twrMode ? axisScientificPercent : axisScientific).format(real)
      : label;
  });
  const left = Math.min(
    100,
    Math.max(48, ...tickLabels.map((label) => label.length * 7 + 12)),
  );
  const right = 16;
  const top = 28;
  const bottom = size.height - 34;
  const plotWidth = Math.max(1, size.width - left - right);
  const plotHeight = Math.max(1, bottom - top);
  const navigate = (start: number, count: number) => {
    if (
      !source.valid ||
      !Number.isFinite(start) ||
      !Number.isFinite(count) ||
      count < 1
    )
      return;
    const boundedCount = Math.min(
      original.length,
      Math.max(1, Math.round(count)),
    );
    const boundedStart = Math.min(
      original.length - boundedCount,
      Math.max(0, Math.round(start)),
    );
    setWindow({ start: boundedStart, end: boundedStart + boundedCount - 1 });
  };
  const gestures = useChartGestures({
    svgRef,
    enabled: expanded && valid,
    start: window.start,
    count: data.length,
    total: source.valid ? original.length : 0,
    onNavigate: navigate,
    onGesture: () => setTooltip(null),
    plotLeft: left,
    plotWidth,
  });
  const x = useCallback(
    (index: number) =>
      left +
      (values.length === 1 ? 0.5 : index / (values.length - 1)) * plotWidth,
    [left, values.length, plotWidth],
  );
  const y = useCallback(
    (value: number) =>
      bottom - ((value / magnitude - lower) / range) * plotHeight,
    [bottom, magnitude, lower, range, plotHeight],
  );
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
    ? `${seriesName} en ${unit}. Escala lineal; eje horizontal por observaciones, sin distancias proporcionales entre fechas. ${number(values.length)} observaciones del ${firstDate} al ${lastDate}. Valor inicial ${formatValue(values[0])}; valor final ${formatValue(lastValue)}.${benchmark ? ` Mantener, con el mismo peso: valor final ${moneyEUR(benchmark.at(-1))}. La línea discontinua representa este benchmark.` : ''}${reduced ? ' El dibujo reduce puntos conservando los extremos de cada tramo; la tabla mantiene todos los datos originales.' : ''}`
    : data.length === 0
      ? original.length === 0
        ? 'No hay observaciones disponibles para representar la evolución.'
        : 'No hay observaciones en el intervalo seleccionado.'
      : !source.ordered
        ? 'La serie contiene fechas no válidas, duplicadas o desordenadas y no se puede representar.'
        : 'La serie contiene valores no válidos y no se puede representar.';
  const pointSummary = selectedPoint
    ? `Sesión ${dateLabel(selectedPoint.date)}. ${'nav' in selectedPoint ? `Patrimonio ${moneyEUR(selectedPoint.nav)}. TWR desde el origen ${percent(Number.isFinite(selectedPoint.twr_index) ? selectedPoint.twr_index - 1 : undefined)}.` : `Estrategia ${moneyEUR(selectedPoint.equity)}. Mantener ${moneyEUR(selectedPoint.benchmark)}.`}`
    : 'Selecciona una observación con el cursor o el teclado.';
  const tooltipAnchor =
    valid &&
    selectedPoint &&
    tooltip?.source === original &&
    tooltip.range === requestedRange &&
    tooltip.metric === metric &&
    tooltip.style === style
      ? tooltip.anchor
      : null;
  const showTooltip = (anchor: ChartTooltipAnchor, keyboard = false) =>
    setTooltip({
      anchor,
      source: original,
      range: requestedRange,
      metric,
      style,
      keyboard,
    });
  const pointAnchor = useCallback(
    (index: number, svg: SVGSVGElement): ChartTooltipAnchor => {
      const point = original[index];
      const localX = x(index - window.start);
      const localY = y(valueOf(point));
      const matrix = svg.getScreenCTM?.();
      if (matrix) {
        return {
          x: matrix.a * localX + matrix.c * localY + matrix.e,
          y: matrix.b * localX + matrix.d * localY + matrix.f,
        };
      }
      const box = svg.getBoundingClientRect();
      const scale = Math.min(
        (box.width || size.width) / size.width,
        (box.height || size.height) / size.height,
      );
      return {
        x:
          box.left +
          ((box.width || size.width) - size.width * scale) / 2 +
          localX * scale,
        y:
          box.top +
          ((box.height || size.height) - size.height * scale) / 2 +
          localY * scale,
      };
    },
    [original, window.start, x, y, valueOf, size],
  );
  const selectByKeyboard = (index: number, svg: SVGSVGElement) => {
    const next = Math.min(window.end, Math.max(window.start, index));
    setSelectedDate(original[next].date);
    showTooltip(pointAnchor(next, svg), true);
  };
  useLayoutEffect(() => {
    if (keyboardGeometry.current === size) return;
    keyboardGeometry.current = size;
    // Read the committed SVG transform after a height change, without scanning
    // the source or changing selection. Pointer tooltips keep their own anchor.
    const svg = svgRef.current;
    if (!svg || !valid || selectedIndex === null) return;
    setTooltip((previous) => {
      if (
        !previous?.keyboard ||
        previous.source !== original ||
        previous.range !== requestedRange ||
        previous.metric !== metric ||
        previous.style !== style
      )
        return previous;
      const anchor = pointAnchor(selectedIndex, svg);
      return anchor.x === previous.anchor.x && anchor.y === previous.anchor.y
        ? previous
        : { ...previous, anchor };
    });
  }, [
    size,
    valid,
    selectedIndex,
    original,
    requestedRange,
    metric,
    style,
    pointAnchor,
  ]);
  const selectAt = (event: {
    clientX: number;
    clientY?: number;
    currentTarget: SVGSVGElement;
  }) => {
    if (!valid || !Number.isFinite(event.clientX)) return;
    const box = event.currentTarget.getBoundingClientRect();
    // Pointer coordinates must follow the painted viewBox, including letterboxing
    // or transforms. A box-width ratio alone selects the wrong observation there.
    const scale = Math.min(
      (box.width || size.width) / size.width,
      (box.height || size.height) / size.height,
    );
    let localX =
      (event.clientX -
        box.left -
        ((box.width || size.width) - size.width * scale) / 2) /
      scale;
    const matrix = event.currentTarget.getScreenCTM?.();
    if (matrix) {
      const inverse = matrix.inverse();
      localX =
        inverse.a * event.clientX +
        inverse.c * (event.clientY ?? 0) +
        inverse.e;
    }
    setSelectedDate(
      original[nearestObservation((localX - left) / plotWidth, window)].date,
    );
    showTooltip({ x: event.clientX, y: event.clientY ?? box.top });
  };
  const lastPage = Math.max(0, Math.ceil(data.length / TABLE_PAGE_SIZE) - 1);
  const page = Math.min(requestedPage, lastPage);
  const firstRow = page * TABLE_PAGE_SIZE;
  const lastRow = Math.min(firstRow + TABLE_PAGE_SIZE, data.length);

  return (
    <figure className="chart">
      {source.valid && (
        <fieldset className="curve-controls" aria-label="Opciones de la curva">
          <div className="curve-control-row">
            <label>
              Representación de la curva
              <select
                value={style}
                onChange={(event) =>
                  setStyle(event.target.value as 'line' | 'area')
                }
              >
                <option value="line">Línea</option>
                <option value="area">Área</option>
              </select>
            </label>
            {source.hasTwr && (
              <label>
                Serie de la curva
                <select
                  value={metric}
                  onChange={(event) =>
                    setMetric(event.target.value as 'value' | 'twr')
                  }
                >
                  <option value="value">Patrimonio</option>
                  <option value="twr">TWR desde el origen</option>
                </select>
              </label>
            )}
          </div>
          <form
            className="curve-control-row"
            onSubmit={(event) => {
              event.preventDefault();
              if (
                draftRange.from &&
                draftRange.to &&
                draftRange.from > draftRange.to
              ) {
                setRangeError(
                  'El inicio no puede ser posterior al fin. Se conserva la vista anterior.',
                );
                return;
              }
              setRequestedRange({ ...draftRange });
              setRangeError('');
              setRequestedPage(0);
            }}
          >
            <label>
              Inicio de la curva
              <input
                type="date"
                value={draftRange.from}
                onChange={(event) =>
                  setDraftRange((previous) => ({
                    ...previous,
                    from: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              Fin de la curva
              <input
                type="date"
                value={draftRange.to}
                onChange={(event) =>
                  setDraftRange((previous) => ({
                    ...previous,
                    to: event.target.value,
                  }))
                }
              />
            </label>
            <button className="chart-data-button" type="submit">
              Aplicar rango
            </button>
          </form>
          {rangeError && (
            <p role="alert" className="chart-context">
              {rangeError}
            </p>
          )}
        </fieldset>
      )}
      <ChartWorkspace
        title={isBacktest ? 'Curva de backtest' : 'Curva de cartera'}
        noun="curva"
        expanded={expanded}
        onExpandedChange={(next) => {
          setTooltip(null);
          setExpanded(next);
        }}
        start={window.start}
        count={valid ? data.length : 0}
        total={source.valid ? original.length : 0}
        zoomAnchor={
          selectedIndex !== null && data.length > 1
            ? (selectedIndex - window.start) / (data.length - 1)
            : 0.5
        }
        onNavigate={navigate}
        onReset={reset}
      >
        <div className="curve-workspace-content">
          <div
            className={`chart-viewport${expanded ? ' curve-expanded-viewport' : ''}`}
            ref={viewport}
          >
            {!valid ? (
              <p className="chart-empty muted">{description}</p>
            ) : (
              /* oxlint-disable jsx-a11y/prefer-tag-over-role, jsx-a11y/no-noninteractive-tabindex, jsx-a11y/no-noninteractive-element-interactions -- The SVG is a keyboard-operable chart: arrows, Home/End and zoom inspect the same original observations as the pointer. Its image title and description remain available. */
              <svg
                ref={svgRef}
                viewBox={`0 0 ${size.width} ${size.height}`}
                preserveAspectRatio="xMidYMid meet"
                role="img"
                tabIndex={0}
                aria-labelledby={`${id}-title ${id}-description`}
                aria-describedby={`${id}-keys ${id}-detail`}
                onPointerMove={(event) => {
                  if (!gestures.onPointerMove(event)) selectAt(event);
                }}
                onPointerLeave={() => setTooltip(null)}
                onBlur={() => setTooltip(null)}
                onPointerDown={(event) => {
                  event.currentTarget.focus({ preventScroll: true });
                  if (!gestures.onPointerDown(event)) selectAt(event);
                }}
                onPointerUp={(event) => {
                  gestures.onPointerUp(event);
                }}
                onPointerCancel={(event) => {
                  gestures.onPointerCancel(event);
                }}
                onLostPointerCapture={(event) => {
                  gestures.onLostPointerCapture(event);
                }}
                onKeyDown={(event) => {
                  const key = event.key;
                  if (key === '+' || key === '=' || key === '-') {
                    event.preventDefault();
                    zoom(key === '-' ? 2 : 0.5);
                    return;
                  }
                  if (key === 'Escape') {
                    event.preventDefault();
                    setSelectedDate(null);
                    setTooltip(null);
                    return;
                  }
                  const current = selectedIndex ?? window.end;
                  const next =
                    key === 'Home'
                      ? window.start
                      : key === 'End'
                        ? window.end
                        : key === 'ArrowLeft' || key === 'ArrowDown'
                          ? current - 1
                          : key === 'ArrowRight' || key === 'ArrowUp'
                            ? current + 1
                            : null;
                  if (next !== null) {
                    event.preventDefault();
                    selectByKeyboard(next, event.currentTarget);
                  }
                }}
                style={{
                  fontFamily: 'inherit',
                  fontVariantNumeric: 'tabular-nums',
                  fontSize: 12,
                }}
              >
                <title
                  id={`${id}-title`}
                >{`${seriesName}: evolución en ${unit}`}</title>
                <desc id={`${id}-description`}>{description}</desc>
                <text x={left} y={14} fill="#62666A" fontSize="11">
                  {unit}
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
                {style === 'area' && values.length > 1 && (
                  <polygon
                    points={`${left},${bottom} ${primaryPoints} ${left + plotWidth},${bottom}`}
                    fill="#526B80"
                    fillOpacity="0.1"
                  />
                )}
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
                    <circle
                      cx={x(0)}
                      cy={y(values[0])}
                      r="3.5"
                      fill="#526B80"
                    />
                  </>
                )}
                {selectedIndex !== null && selectedPoint && (
                  <g className="curve-crosshair" aria-hidden="true">
                    <line
                      x1={x(selectedIndex - window.start)}
                      x2={x(selectedIndex - window.start)}
                      y1={top}
                      y2={bottom}
                      stroke="#975435"
                      strokeWidth="1"
                      strokeDasharray="3 3"
                    />
                    <line
                      x1={left}
                      x2={left + plotWidth}
                      y1={y(valueOf(selectedPoint))}
                      y2={y(valueOf(selectedPoint))}
                      stroke="#975435"
                      strokeWidth="1"
                      strokeDasharray="3 3"
                    />
                    <circle
                      cx={x(selectedIndex - window.start)}
                      cy={y(valueOf(selectedPoint))}
                      r="4"
                      fill="#FFFCF6"
                      stroke="#975435"
                      strokeWidth="2"
                    />
                  </g>
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
                        {dateLabel(
                          data[Math.floor((data.length - 1) / 2)].date,
                        )}
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
              /* oxlint-enable jsx-a11y/prefer-tag-over-role, jsx-a11y/no-noninteractive-tabindex, jsx-a11y/no-noninteractive-element-interactions */
            )}
          </div>
          {valid && (
            <div className="curve-inspection">
              <p id={`${id}-keys`} className="chart-context">
                Flechas: observación anterior/siguiente. Inicio/Fin: extremos.
                +/−: zoom. Escape: {expanded ? 'salir de pantalla completa' : 'quitar selección'}.
                {' '}Fechas de sesión; sin hora intradía.
              </p>
              <section
                id={`${id}-detail`}
                className="curve-point-detail"
                aria-label="Detalle de la observación"
                aria-live={tooltip?.keyboard ? 'polite' : 'off'}
              >
                {selectedPoint ? (
                  <>
                    <time dateTime={selectedPoint.date}>
                      {dateLabel(selectedPoint.date)}
                    </time>
                    {'nav' in selectedPoint ? (
                      <>
                        <span>
                          Patrimonio{' '}
                          <data value={selectedPoint.nav}>
                            {moneyEUR(selectedPoint.nav)}
                          </data>
                        </span>
                        <span>
                          TWR desde el origen{' '}
                          <data
                            value={
                              Number.isFinite(selectedPoint.twr_index)
                                ? selectedPoint.twr_index
                                : undefined
                            }
                          >
                            {percent(
                              Number.isFinite(selectedPoint.twr_index)
                                ? selectedPoint.twr_index - 1
                                : undefined,
                            )}
                          </data>
                        </span>
                      </>
                    ) : (
                      <>
                        <span>
                          Estrategia{' '}
                          <data value={selectedPoint.equity}>
                            {moneyEUR(selectedPoint.equity)}
                          </data>
                        </span>
                        <span>
                          Mantener · mismo peso{' '}
                          <data
                            value={
                              Number.isFinite(selectedPoint.benchmark)
                                ? selectedPoint.benchmark
                                : undefined
                            }
                          >
                            {moneyEUR(selectedPoint.benchmark)}
                          </data>
                        </span>
                      </>
                    )}
                  </>
                ) : (
                  <span>{pointSummary}</span>
                )}
              </section>
            </div>
          )}
          <ChartTooltip
            id={`${id}-tooltip`}
            anchor={tooltipAnchor}
            onDismiss={() => setTooltip(null)}
          >
            {selectedPoint && (
              <>
                <time
                  className="chart-tooltip-heading"
                  dateTime={selectedPoint.date}
                >
                  {dateLabel(selectedPoint.date)}
                </time>
                <dl>
                  {'nav' in selectedPoint ? (
                    <>
                      <dt>Patrimonio</dt>
                      <dd>
                        <data value={selectedPoint.nav}>
                          {moneyEUR(selectedPoint.nav)}
                        </data>
                      </dd>
                      <dt>TWR desde el origen</dt>
                      <dd>
                        <data
                          value={
                            Number.isFinite(selectedPoint.twr_index)
                              ? selectedPoint.twr_index
                              : undefined
                          }
                        >
                          {percent(
                            Number.isFinite(selectedPoint.twr_index)
                              ? selectedPoint.twr_index - 1
                              : undefined,
                          )}
                        </data>
                      </dd>
                    </>
                  ) : (
                    <>
                      <dt>Estrategia</dt>
                      <dd>
                        <data value={selectedPoint.equity}>
                          {moneyEUR(selectedPoint.equity)}
                        </data>
                      </dd>
                      <dt>Mantener · mismo peso</dt>
                      <dd>
                        <data
                          value={
                            Number.isFinite(selectedPoint.benchmark)
                              ? selectedPoint.benchmark
                              : undefined
                          }
                        >
                          {moneyEUR(selectedPoint.benchmark)}
                        </data>
                      </dd>
                    </>
                  )}
                </dl>
                <p className="chart-tooltip-note">
                  Observación original · Fecha de sesión
                </p>
              </>
            )}
          </ChartTooltip>
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
        </div>
      </ChartWorkspace>
      {valid && (
        <p className="chart-context">
          {unit} · Escala lineal · Eje horizontal por observaciones; las fechas
          no están separadas proporcionalmente.
          {reduced &&
            ' Dibujo reducido conservando los extremos de cada tramo. La tabla contiene todos los datos originales.'}
        </p>
      )}
      {source.valid && (
        <p className="chart-context">
          El rango y el zoom cambian solo la vista; las métricas del resultado
          conservan su periodo original.
          {twrMode &&
            ' TWR acumulado desde el origen de la serie, sin reiniciar la base al recortar.'}
          {style === 'area' &&
            ' El relleno termina en el borde inferior de la escala visible; no representa una base cero.'}
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
                      {seriesName.toLocaleLowerCase('es-ES')} en {unit}
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Observación</th>
                        <th scope="col">Fecha de sesión</th>
                        <th scope="col">
                          {seriesName} ({unit})
                        </th>
                        {benchmark && (
                          <th scope="col">Mantener · mismo peso (EUR)</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {data.slice(firstRow, lastRow).map((point, offset) => (
                        <tr key={firstRow + offset}>
                          <th scope="row">
                            {number(window.start + firstRow + offset + 1)}
                          </th>
                          <td>{dateLabel(point.date)}</td>
                          <td>{formatValue(valueOf(point))}</td>
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
