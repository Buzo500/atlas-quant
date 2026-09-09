'use client';
// A real SVG plot supports pointer and keyboard inspection; an <img> cannot.
// Keyboard inspection and the original data table remain available without hover.
/* oxlint-disable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex, jsx-a11y/prefer-tag-over-role */
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
} from 'react';
import {
  ChartTooltip,
  type ChartTooltipAnchor,
} from '@/shared/components/chart-tooltip';
import { useChartGestures } from '@/shared/components/chart-gestures';
import { date } from '@/shared/format';
import { MAX_VISIBLE_BARS, type PriceBar } from './aggregation';
import { priceValue as price, priceTick } from './format';

export type Representation = 'candles' | 'line' | 'area' | 'ohlc';

export function PriceChart({
  bars,
  selected,
  onSelect,
  representation,
  volume,
  symbol,
  currency,
  expanded = false,
  start = 0,
  total = bars.length,
  onNavigate = () => {},
}: {
  bars: PriceBar[];
  selected: number;
  onSelect: (index: number) => void;
  representation: Representation;
  volume: boolean;
  symbol: string;
  currency: string;
  expanded?: boolean;
  start?: number;
  total?: number;
  onNavigate?: (start: number, count: number) => void;
}) {
  const holder = useRef<HTMLDivElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const description = useId();
  const tooltipId = useId();
  const [inspection, setInspection] = useState<{
    anchor: ChartTooltipAnchor;
    bars: PriceBar[];
    index: number;
    context: string;
  } | null>(null);
  const dismiss = useCallback(() => setInspection(null), []);
  const context = `${representation}:${volume}:${symbol}:${currency}:${expanded}`;
  const [{ width, height }, setSize] = useState({ width: 960, height: 380 });
  useEffect(() => {
    const element = holder.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry && entry.contentRect.width > 0) {
        dismiss();
        setSize({
          width: Math.max(280, entry.contentRect.width),
          height: Math.max(220, entry.contentRect.height),
        });
      }
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [dismiss]);
  // Discard an old selection as part of deriving this render, without remounting
  // the focused SVG or waiting for an effect to remove stale floating content.
  if (
    inspection &&
    (inspection.bars !== bars || inspection.context !== context)
  )
    setInspection(null);
  const left = 12,
    right = 86,
    top = 20,
    bottom = volume ? height * 0.64 : height - 38;
  const plot = Math.max(80, width - left - right);
  const gestures = useChartGestures({
    svgRef: svg,
    enabled: expanded,
    start,
    count: bars.length,
    total,
    maxCount: MAX_VISIBLE_BARS,
    onNavigate,
    onGesture: dismiss,
    plotLeft: left,
    plotWidth: plot,
  });
  if (!bars.length) return null;
  const step = plot / bars.length;
  const x = (index: number) => left + (index + 0.5) * step;
  let low = Infinity,
    high = -Infinity,
    maxVolume = 0;
  for (const bar of bars) {
    low = Math.min(low, bar.low);
    high = Math.max(high, bar.high);
    maxVolume = Math.max(maxVolume, bar.volume ?? 0);
  }
  // Normalize before padding: finite extremes must not produce Infinity/NaN geometry.
  const scale = high;
  low /= scale;
  high = 1;
  const padding = (high - low || 0.01) * 0.08;
  low = Math.max(0, low - padding);
  high = Math.min(Number.MAX_VALUE / scale, high + padding);
  const y = (value: number) =>
    bottom - ((value / scale - low) / (high - low)) * (bottom - top);
  const volumeTop = bottom + 35,
    volumeBottom = height - 38;
  const volumeY = (value: number) =>
    volumeBottom -
    (maxVolume ? value / maxVolume : 0) * (volumeBottom - volumeTop);
  const path = bars
    .map((bar, index) => `${index ? 'L' : 'M'}${x(index)},${y(bar.close)}`)
    .join(' ');
  const current = bars[Math.max(0, Math.min(selected, bars.length - 1))];
  const ticks = [
    ...new Set([0, Math.floor((bars.length - 1) / 2), bars.length - 1]),
  ];
  const currentLabel = `${date(current.first_date)}${current.last_date === current.first_date ? '' : ' a ' + date(current.last_date)}; apertura ${price(current.open)}, máximo ${price(current.high)}, mínimo ${price(current.low)}, cierre ${price(current.close)} ${currency}; volumen ${current.volume === null ? 'sin dato' : price(current.volume)}`;
  const anchor =
    inspection?.bars === bars &&
    inspection.context === context &&
    inspection.index === selected
      ? inspection.anchor
      : null;
  function pointAnchor(index: number): ChartTooltipAnchor | null {
    const element = svg.current;
    if (!element) return null;
    const matrix = element.getScreenCTM?.();
    if (matrix && typeof DOMPoint !== 'undefined') {
      const point = new DOMPoint(
        x(index),
        y(bars[index].close),
      ).matrixTransform(matrix);
      return Number.isFinite(point.x) && Number.isFinite(point.y)
        ? { x: point.x, y: point.y }
        : null;
    }
    const box = element.getBoundingClientRect();
    if (box.width <= 0 || box.height <= 0) return null;
    const fit = Math.min(box.width / width, box.height / height);
    return {
      x: box.left + (box.width - width * fit) / 2 + x(index) * fit,
      y: box.top + (box.height - height * fit) / 2 + y(bars[index].close) * fit,
    };
  }
  function keyboard(event: KeyboardEvent<SVGSVGElement>) {
    if (event.key === 'Escape') {
      event.preventDefault();
      dismiss();
      return;
    }
    const next =
      event.key === 'ArrowLeft'
        ? selected - 1
        : event.key === 'ArrowRight'
          ? selected + 1
          : event.key === 'Home'
            ? 0
            : event.key === 'End'
              ? bars.length - 1
              : null;
    if (next !== null) {
      event.preventDefault();
      const index = Math.max(0, Math.min(bars.length - 1, next));
      const nextAnchor = pointAnchor(index);
      onSelect(index);
      setInspection(
        nextAnchor ? { anchor: nextAnchor, bars, index, context } : null,
      );
    }
  }
  return (
    <figure className="price-figure">
      <div ref={holder} className="price-plot">
        <svg
          ref={svg}
          className={`price-chart-svg${expanded ? ' price-chart-interactive' : ''}`}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          tabIndex={0}
          aria-label={`Gráfico de precios · ${symbol}. ${currentLabel}`}
          aria-describedby={
            anchor ? `${description} ${tooltipId}` : description
          }
          onKeyDown={keyboard}
          onBlur={dismiss}
          onPointerLeave={dismiss}
          onPointerDown={(event) => gestures.onPointerDown(event)}
          onPointerUp={(event) => gestures.onPointerUp(event)}
          onPointerCancel={(event) => gestures.onPointerCancel(event)}
          onLostPointerCapture={(event) => gestures.onLostPointerCapture(event)}
          onPointerMove={(event) => {
            if (gestures.onPointerMove(event)) return;
            const box = event.currentTarget.getBoundingClientRect();
            if (box.width <= 0 || box.height <= 0) return;
            const matrix = event.currentTarget.getScreenCTM?.();
            const fit = Math.min(box.width / width, box.height / height);
            const position =
              matrix && typeof DOMPoint !== 'undefined'
                ? new DOMPoint(event.clientX, event.clientY).matrixTransform(
                    matrix.inverse(),
                  )
                : {
                    x:
                      (event.clientX -
                        box.left -
                        (box.width - width * fit) / 2) /
                      fit,
                    y:
                      (event.clientY -
                        box.top -
                        (box.height - height * fit) / 2) /
                      fit,
                  };
            if (
              !Number.isFinite(position.x) ||
              !Number.isFinite(position.y) ||
              position.x < left ||
              position.x > left + plot ||
              position.y < top ||
              position.y > (volume ? volumeBottom : bottom)
            ) {
              dismiss();
              return;
            }
            const index = Math.max(
              0,
              Math.min(bars.length - 1, Math.floor((position.x - left) / step)),
            );
            onSelect(index);
            setInspection({
              anchor: { x: event.clientX, y: event.clientY },
              bars,
              index,
              context,
            });
          }}
          onClick={() => {
            if (!gestures.onClick()) svg.current?.focus();
          }}
        >
          <g aria-hidden="true">
            {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
              const value = (low + (high - low) * ratio) * scale;
              return (
                <g key={ratio}>
                  <line
                    className="price-grid"
                    x1={left}
                    x2={left + plot}
                    y1={y(value)}
                    y2={y(value)}
                  />
                  <text
                    className="price-axis"
                    x={left + plot + 8}
                    y={y(value) + 4}
                  >
                    {priceTick(value)}
                  </text>
                </g>
              );
            })}
            {(representation === 'line' || representation === 'area') && (
              <>
                {representation === 'area' && (
                  <path
                    className="price-area"
                    d={`${path} L${x(bars.length - 1)},${bottom} L${x(0)},${bottom} Z`}
                  />
                )}
                <path className="price-close-line" d={path} />
                {bars.length === 1 && (
                  <circle
                    className="price-single"
                    cx={x(0)}
                    cy={y(bars[0].close)}
                    r={3}
                  />
                )}
              </>
            )}
            {(representation === 'candles' || representation === 'ohlc') &&
              bars.map((bar, index) => {
                const half = Math.max(0.4, Math.min(10, step * 0.31));
                const className =
                  bar.close >= bar.open ? 'price-rise' : 'price-fall';
                return (
                  <g key={bar.date} className={className}>
                    <line
                      x1={x(index)}
                      x2={x(index)}
                      y1={y(bar.high)}
                      y2={y(bar.low)}
                    />
                    {representation === 'ohlc' ? (
                      <>
                        <line
                          x1={x(index) - half}
                          x2={x(index)}
                          y1={y(bar.open)}
                          y2={y(bar.open)}
                        />
                        <line
                          x1={x(index)}
                          x2={x(index) + half}
                          y1={y(bar.close)}
                          y2={y(bar.close)}
                        />
                      </>
                    ) : bar.open === bar.close ? (
                      <line
                        x1={x(index) - half}
                        x2={x(index) + half}
                        y1={y(bar.close)}
                        y2={y(bar.close)}
                      />
                    ) : (
                      <rect
                        x={x(index) - half}
                        width={half * 2}
                        y={Math.min(y(bar.open), y(bar.close))}
                        height={Math.abs(y(bar.open) - y(bar.close))}
                      />
                    )}
                  </g>
                );
              })}
            {volume && (
              <>
                <text className="price-axis" x={left} y={volumeTop - 10}>
                  Volumen
                </text>
                <line
                  className="price-grid"
                  x1={left}
                  x2={left + plot}
                  y1={volumeBottom}
                  y2={volumeBottom}
                />
                <text
                  className="price-axis"
                  x={left + plot + 8}
                  y={volumeTop + 4}
                >
                  {priceTick(maxVolume)}
                </text>
                <text
                  className="price-axis"
                  x={left + plot + 8}
                  y={volumeBottom + 4}
                >
                  0
                </text>
                {bars.map((bar, index) =>
                  bar.volume === null ? null : (
                    <rect
                      key={bar.date}
                      className="price-volume-bar"
                      x={x(index) - Math.max(0.35, step * 0.31)}
                      width={Math.max(0.7, step * 0.62)}
                      y={volumeY(bar.volume)}
                      height={volumeBottom - volumeY(bar.volume)}
                    />
                  ),
                )}
              </>
            )}
            <line
              className="price-cursor"
              x1={x(selected)}
              x2={x(selected)}
              y1={top}
              y2={volume ? volumeBottom : bottom}
            />
            <circle
              className="price-cursor-point"
              cx={x(selected)}
              cy={y(current.close)}
              r={4}
            />
            {ticks.map((index) => (
              <text
                key={index}
                className="price-axis"
                x={x(index)}
                y={height - 10}
                textAnchor={
                  index === 0
                    ? 'start'
                    : index === bars.length - 1
                      ? 'end'
                      : 'middle'
                }
              >
                {date(bars[index].last_date)}
              </text>
            ))}
          </g>
        </svg>
      </div>
      <ChartTooltip anchor={anchor} onDismiss={dismiss} id={tooltipId}>
        <div className="chart-tooltip-heading">
          <strong>
            {symbol} · {currency}
          </strong>
          <span>
            <time dateTime={current.first_date}>
              {date(current.first_date)}
            </time>
            {current.last_date !== current.first_date && (
              <>
                {' → '}
                <time dateTime={current.last_date}>
                  {date(current.last_date)}
                </time>
              </>
            )}
          </span>
        </div>
        <dl>
          {(
            [
              ['Apertura', current.open, 'open'],
              ['Máximo', current.high, 'high'],
              ['Mínimo', current.low, 'low'],
              ['Cierre', current.close, 'close'],
              ['Volumen', current.volume, 'volume'],
            ] as const
          ).map(([label, amount, field]) => (
            <div key={field}>
              <dt>{label}</dt>
              <dd data-price-field={field}>
                <data value={amount === null ? undefined : String(amount)}>
                  {amount === null ? 'Sin dato' : price(amount)}
                </data>
              </dd>
            </div>
          ))}
        </dl>
        {current.completeness === 'unknown' && (
          <p className="chart-tooltip-note">
            {current.observations} sesiones agregadas · cobertura sin verificar.
            {(current.partial_start || current.partial_end) &&
              ' Periodo recortado.'}
          </p>
        )}
      </ChartTooltip>
      <figcaption id={description}>
        Precio en {currency}; eje vertical ajustado al rango visible. Sesiones
        observadas equidistantes, sin rellenar días ausentes. Flechas
        izquierda/derecha y teclas Inicio/Fin para inspeccionar. Esc {expanded
          ? 'sale de pantalla completa'
          : 'cierra la lectura flotante'}; la tabla conserva los datos originales.
        {representation === 'area' &&
          ' El área parte del mínimo del eje visible, no de cero.'}
        {representation === 'candles' || representation === 'ohlc'
          ? ' Azul: cierre ≥ apertura. Cobre: cierre < apertura.'
          : ''}
        {volume &&
          ' Volumen en su escala independiente; ausencia de dato no equivale a cero.'}
      </figcaption>
    </figure>
  );
}
