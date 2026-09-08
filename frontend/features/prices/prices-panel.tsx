'use client';
import { memo, useId, useMemo, useState, type SubmitEvent } from 'react';
import type { DatasetPricesResponse, DatasetResponse } from '@/lib/api-types';
import { datasetPricesPath } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Choice, Field } from '@/shared/ui';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { Pagination, usePagination } from '@/shared/pagination';
import { date, dateTime, number, percent } from '@/shared/format';
import {
  aggregateBars,
  priceChange,
  validDate,
  validateBars,
  visibleWindow,
  DEFAULT_VISIBLE_BARS,
  MAX_VISIBLE_BARS,
  type DailyBar,
  type Interval,
} from './aggregation';
import { PriceChart, type Representation } from './price-chart';
import './price-chart.css';
import { priceDifference, priceValue as value } from './format';

const intervals = [
  { value: 'D', label: 'Diario' },
  { value: 'W', label: 'Semanal' },
  { value: 'M', label: 'Mensual' },
];
const representations = [
  { value: 'candles', label: 'Velas' },
  { value: 'line', label: 'Línea' },
  { value: 'area', label: 'Área' },
  { value: 'ohlc', label: 'Barras OHLC' },
];

export function PricesPanel({
  dataset,
  active = true,
}: {
  dataset: DatasetResponse | undefined;
  active?: boolean;
}) {
  const heading = useId();
  const [selection, setSelection] = useState({ dataset: '', symbol: '' });
  const [sourceDraft, setSourceDraft] = useState({ start: '', end: '' });
  const [sourceRange, setSourceRange] = useState({
    scope: '',
    start: '',
    end: '',
  });
  const [sourceError, setSourceError] = useState('');
  const symbols = dataset?.manifest.symbols ?? [];
  const symbol =
    selection.dataset === dataset?.id && symbols.includes(selection.symbol)
      ? selection.symbol
      : (symbols[0] ?? '');
  const scope = `${dataset?.id}:${dataset?.version}:${symbol}`;
  const path =
    dataset && symbol
      ? datasetPricesPath(
          dataset.id,
          dataset.version,
          symbol,
          sourceRange.scope === scope ? sourceRange : {},
        )
      : null;
  const query = useRead<DatasetPricesResponse>({ path, enabled: active });
  const response = query.data;
  const identityError =
    response &&
    (response.dataset_id !== dataset?.id ||
      response.dataset_version !== dataset?.version ||
      response.symbol !== symbol)
      ? 'La respuesta de precios no coincide con el activo y la versión solicitados.'
      : '';
  return (
    <section className="panel prices-panel" aria-labelledby={heading}>
      <div className="panel-heading">
        <div>
          <h2 id={heading}>Precios del activo</h2>
          <p className="muted">
            Observaciones diarias de la versión seleccionada. Inspección de
            precios y volumen.
          </p>
        </div>
      </div>
      {!dataset || !symbols.length ? (
        <p className="muted">
          Selecciona o importa un conjunto con precios para explorar sus
          activos.
        </p>
      ) : (
        <>
          <div className="prices-source-selector">
            <Field label="Activo del gráfico">
              <Choice
                value={symbol}
                label="Activo del gráfico"
                options={symbols.map((item) => ({ value: item, label: item }))}
                onChange={(next) =>
                  setSelection({ dataset: dataset.id, symbol: next })
                }
              />
            </Field>
            <p className="muted">
              {dataset.name} · Versión {number(dataset.version)}
            </p>
          </div>
          <QueryStatus label="Precios" query={query} />
          <details className="details prices-query-range">
            <summary>Fechas de consulta al motor</summary>
            <p className="muted">
              Opcional: reduce el rango si supera 100.000 observaciones. Las
              fechas son inclusivas; consulta solo la base local. Deja ambas
              vacías para solicitar toda la serie.
            </p>
            <form
              className="prices-date-controls"
              onSubmit={(event) => {
                event.preventDefault();
                if (
                  (sourceDraft.start && !validDate(sourceDraft.start)) ||
                  (sourceDraft.end && !validDate(sourceDraft.end)) ||
                  (sourceDraft.start &&
                    sourceDraft.end &&
                    sourceDraft.start > sourceDraft.end)
                ) {
                  setSourceError(
                    'Elige fechas de consulta válidas y ordenadas.',
                  );
                  return;
                }
                setSourceError('');
                setSourceRange({ scope, ...sourceDraft });
              }}
            >
              <Field label="Consulta desde">
                <Input
                  type="date"
                  aria-label="Consulta desde"
                  value={sourceDraft.start}
                  onChange={(event) =>
                    setSourceDraft((old) => ({
                      ...old,
                      start: event.target.value,
                    }))
                  }
                />
              </Field>
              <Field label="Consulta hasta">
                <Input
                  type="date"
                  aria-label="Consulta hasta"
                  value={sourceDraft.end}
                  onChange={(event) =>
                    setSourceDraft((old) => ({
                      ...old,
                      end: event.target.value,
                    }))
                  }
                />
              </Field>
              <Button type="submit" variant="outline">
                Consultar precios
              </Button>
            </form>
            {sourceError && (
              <p role="alert" className="notice amber">
                {sourceError}
              </p>
            )}
          </details>
          {identityError && (
            <p role="alert" className="notice amber">
              {identityError}
            </p>
          )}
          {response && !identityError && (
            <PriceExplorer key={path} response={response} />
          )}
        </>
      )}
    </section>
  );
}

export function PriceExplorer({
  response,
}: {
  response: DatasetPricesResponse;
}) {
  const loadedStart = response.first_date ?? response.available_start;
  const loadedEnd = response.last_date ?? response.available_end;
  const [interval, setInterval] = useState<Interval>('D');
  const [representation, setRepresentation] =
    useState<Representation>('candles');
  const [volume, setVolume] = useState(true);
  const [draft, setDraft] = useState({ start: loadedStart, end: loadedEnd });
  const [range, setRange] = useState(draft);
  const [rangeError, setRangeError] = useState('');
  const [viewport, setViewport] = useState({
    key: '',
    start: 0,
    count: DEFAULT_VISIBLE_BARS,
  });
  const [cursor, setCursor] = useState({ key: '', index: 0 });
  const viewKey = `${interval}:${range.start}:${range.end}`;
  const prepared = useMemo(() => {
    try {
      validateBars(response.bars);
      const original = response.bars.filter(
        (bar) => bar.date >= range.start && bar.date <= range.end,
      );
      const firstIndex = original.length
        ? response.bars.findIndex((bar) => bar.date === original[0].date)
        : -1;
      return {
        original,
        aggregated: aggregateBars(original, interval, range),
        previous:
          firstIndex > 0
            ? response.bars[firstIndex - 1].close
            : response.preceding_close,
        previousDate:
          firstIndex > 0
            ? response.bars[firstIndex - 1].date
            : response.preceding_date,
        error: '',
      };
    } catch (error) {
      return {
        original: [],
        aggregated: [],
        previous: null,
        previousDate: null,
        error:
          error instanceof Error
            ? error.message
            : 'No se pudieron interpretar los precios.',
      };
    }
  }, [response, interval, range]);
  const total = prepared.aggregated.length;
  const window = visibleWindow(
    total,
    viewport.key === viewKey ? viewport.start : total - DEFAULT_VISIBLE_BARS,
    viewport.key === viewKey ? viewport.count : DEFAULT_VISIBLE_BARS,
  );
  const bars = prepared.aggregated.slice(window.start, window.end);
  const windowKey = `${viewKey}:${window.start}:${window.end}`;
  const selected =
    cursor.key === windowKey
      ? Math.max(0, Math.min(bars.length - 1, cursor.index))
      : bars.length - 1;
  const current = bars[selected];
  const previous =
    window.start + selected > 0
      ? prepared.aggregated[window.start + selected - 1]
      : null;
  const previousClose = previous?.close ?? prepared.previous;
  const previousDate = previous?.last_date ?? prepared.previousDate;
  const change = current
    ? priceChange(current.close, previousClose)
    : { absolute: null, relative: null, relativeUnavailable: false };
  function navigate(start: number, count = window.count) {
    const next = visibleWindow(total, start, count);
    setViewport({ key: viewKey, start: next.start, count: next.count });
  }
  function zoom(factor: number) {
    const count = Math.max(
      1,
      Math.min(total, MAX_VISIBLE_BARS, Math.round(window.count * factor)),
    );
    navigate(
      window.start + Math.max(0, selected) - Math.floor(count / 2),
      count,
    );
  }
  function applyDates(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !validDate(draft.start) ||
      !validDate(draft.end) ||
      draft.start > draft.end ||
      draft.start < loadedStart ||
      draft.end > loadedEnd
    ) {
      setRangeError(
        'Elige fechas válidas y ordenadas dentro de la cobertura disponible.',
      );
      return;
    }
    setRange({ ...draft });
    setRangeError('');
    setViewport({ key: '', start: 0, count: DEFAULT_VISIBLE_BARS });
  }
  const metadata = response.source_metadata;
  return (
    <div className="prices-explorer">
      <div className="prices-context">
        <strong>
          {response.symbol} · {response.currency}
        </strong>
        <span>
          {response.source_kind === 'synthetic'
            ? 'Datos sintéticos'
            : 'Datos observados'}
        </span>
        <span>
          Disponible: {date(response.available_start)} →{' '}
          {date(response.available_end)}
        </span>
      </div>
      <p className="muted prices-provenance">
        Origen: {response.source} · Ajuste: {response.price_basis} · Calendario:{' '}
        {response.calendar}
      </p>
      {response.warnings.length > 0 && (
        <div className="notice amber">
          <ul>
            {response.warnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))}
          </ul>
        </div>
      )}
      <details className="details prices-trace">
        <summary>Procedencia y versión de precios</summary>
        <dl className="prices-trace-grid">
          <div>
            <dt>Conjunto</dt>
            <dd className="mono">{response.dataset_id}</dd>
          </div>
          <div>
            <dt>Versión</dt>
            <dd>{number(response.dataset_version)}</dd>
          </div>
          <div>
            <dt>Huella del manifiesto</dt>
            <dd className="mono">{response.manifest_hash}</dd>
          </div>
          <div>
            <dt>Sesiones recibidas</dt>
            <dd>
              {date(response.first_date)} → {date(response.last_date)}
            </dd>
          </div>
          {metadata && (
            <>
              <div>
                <dt>Proveedor / adaptador</dt>
                <dd>
                  {metadata.provider} · {metadata.adapter}{' '}
                  {metadata.adapter_version}
                </dd>
              </div>
              <div>
                <dt>Mercado / zona de origen</dt>
                <dd>
                  {metadata.exchange ?? 'No consta'} ·{' '}
                  {metadata.exchange_timezone ?? 'No consta'}
                </dd>
              </div>
              <div>
                <dt>Consulta de origen</dt>
                <dd>{dateTime(metadata.fetched_at)}</dd>
              </div>
              <div>
                <dt>Ajustes del proveedor</dt>
                <dd>
                  Automático: {metadata.auto_adjust ? 'sí' : 'no'};
                  retrospectivo: {metadata.back_adjust ? 'sí' : 'no'};
                  reparación: {metadata.repair ? 'sí' : 'no'}
                </dd>
              </div>
              <div>
                <dt>Acciones corporativas aplicadas</dt>
                <dd>{metadata.corporate_actions_applied ? 'Sí' : 'No'}</dd>
              </div>
            </>
          )}
        </dl>
      </details>
      <div className="prices-controls">
        <Field label="Representación de precios">
          <Choice
            value={representation}
            onChange={(next) => setRepresentation(next as Representation)}
            label="Representación de precios"
            options={representations}
          />
        </Field>
        <Field label="Intervalo del gráfico">
          <Choice
            value={interval}
            onChange={(next) => setInterval(next as Interval)}
            label="Intervalo del gráfico"
            options={intervals}
          />
        </Field>
        <label className="prices-volume-toggle">
          <input
            type="checkbox"
            checked={volume}
            onChange={(event) => setVolume(event.target.checked)}
          />
          Mostrar volumen
        </label>
      </div>
      <form className="prices-date-controls" onSubmit={applyDates}>
        <Field label="Precios desde">
          <Input
            type="date"
            aria-label="Precios desde"
            min={loadedStart}
            max={loadedEnd}
            value={draft.start}
            onChange={(event) =>
              setDraft((old) => ({ ...old, start: event.target.value }))
            }
          />
        </Field>
        <Field label="Precios hasta">
          <Input
            type="date"
            aria-label="Precios hasta"
            min={loadedStart}
            max={loadedEnd}
            value={draft.end}
            onChange={(event) =>
              setDraft((old) => ({ ...old, end: event.target.value }))
            }
          />
        </Field>
        <Button type="submit" variant="outline">
          Aplicar fechas
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            const all = { start: loadedStart, end: loadedEnd };
            setDraft(all);
            setRange(all);
            setRangeError('');
            setViewport({ key: '', start: 0, count: DEFAULT_VISIBLE_BARS });
          }}
        >
          Restablecer vista
        </Button>
      </form>
      {(loadedStart !== response.available_start ||
        loadedEnd !== response.available_end) && (
        <p className="muted">
          Consulta recibida: {date(loadedStart)} → {date(loadedEnd)}. Para
          consultar otras fechas, modifica las fechas de consulta al motor.
        </p>
      )}
      {rangeError && (
        <p role="alert" className="notice amber">
          {rangeError}
        </p>
      )}
      {prepared.error ? (
        <p role="alert" className="notice amber">
          {prepared.error}
        </p>
      ) : !bars.length ? (
        <output className="price-empty">
          No hay observaciones diarias en las fechas elegidas.
        </output>
      ) : (
        <>
          <fieldset
            className="prices-view-controls"
            aria-label="Navegación del gráfico de precios"
          >
            <Button
              variant="outline"
              size="sm"
              disabled={window.start === 0}
              onClick={() => navigate(0)}
            >
              Primera ventana
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={window.start === 0}
              onClick={() => navigate(window.start - window.count)}
            >
              Barras anteriores
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={window.end === total}
              onClick={() => navigate(window.start + window.count)}
            >
              Barras siguientes
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={window.end === total}
              onClick={() => navigate(total - window.count)}
            >
              Última ventana
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={window.count <= 1}
              onClick={() => zoom(0.5)}
            >
              Acercar precios
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={window.count >= Math.min(total, MAX_VISIBLE_BARS)}
              onClick={() => zoom(2)}
            >
              Alejar precios
            </Button>
          </fieldset>
          <output className="prices-window-summary">
            Barras {number(window.start + 1)}–{number(window.end)} de{' '}
            {number(total)} · {date(bars[0].first_date)} →{' '}
            {date(bars[bars.length - 1].last_date)}. Máximo{' '}
            {number(MAX_VISIBLE_BARS)} barras visibles; navega para recorrer
            toda la serie.
          </output>
          {interval !== 'D' && (
            <p className="notice prices-aggregation-note">
              {interval === 'W'
                ? 'Semanas civiles de lunes a domingo.'
                : 'Meses civiles.'}{' '}
              Apertura inicial, máximo, mínimo, último cierre y suma de
              volúmenes presentes. Completitud desconocida: no hay un calendario
              de sesiones validado. Los extremos recortados del periodo civil se
              indican en la lectura.
            </p>
          )}
          <PriceChart
            bars={bars}
            selected={selected}
            onSelect={(index) =>
              setCursor((old) =>
                old.key === windowKey && old.index === index
                  ? old
                  : { key: windowKey, index },
              )
            }
            representation={representation}
            volume={volume}
            symbol={response.symbol}
            currency={response.currency}
          />
          <section className="price-readout" aria-label="Lectura de precios">
            <div className="price-readout-heading">
              <h3>
                {interval === 'D'
                  ? `Sesión ${date(current.last_date)}`
                  : `${interval === 'W' ? 'Semana' : 'Mes'} ${date(current.period_start)} → ${date(current.period_end)}`}
              </h3>
              <span>
                {number(current.observations)} observaciones ·{' '}
                {date(current.first_date)} → {date(current.last_date)}
              </span>
            </div>
            {(current.partial_start || current.partial_end) && (
              <p className="muted">
                Periodo civil recortado: {current.partial_start && 'inicio'}
                {current.partial_start && current.partial_end && ' y '}
                {current.partial_end && 'fin'}. La barra utiliza solo las
                observaciones disponibles.
              </p>
            )}
            <dl>
              {[
                ['Apertura', current.open, 'open'],
                ['Máximo', current.high, 'high'],
                ['Mínimo', current.low, 'low'],
                ['Cierre', current.close, 'close'],
                ['Volumen', current.volume, 'volume'],
                ['Cambio', change.absolute, 'change'],
              ].map(([label, amount, field]) => (
                <div key={String(field)}>
                  <dt>{label}</dt>
                  <dd data-price-field={String(field)}>
                    <data value={amount == null ? undefined : String(amount)}>
                      {field === 'change'
                        ? priceDifference(amount as number | null)
                        : value(amount as number | null)}
                      {field !== 'volume' && amount !== null
                        ? ` ${response.currency}`
                        : ''}
                    </data>
                  </dd>
                </div>
              ))}
              <div>
                <dt>Cambio (%)</dt>
                <dd data-price-field="change-percent">
                  <data value={change.relative ?? undefined}>
                    {change.relativeUnavailable
                      ? 'Fuera de rango numérico'
                      : percent(change.relative)}
                  </data>
                </dd>
              </div>
              <div>
                <dt>Cierre anterior</dt>
                <dd data-price-field="previous-close">
                  <data value={previousClose ?? undefined}>
                    {value(previousClose)}
                    {previousClose !== null ? ` ${response.currency}` : ''}
                  </data>
                  <small>
                    {previousDate ? (
                      <time dateTime={previousDate}>{date(previousDate)}</time>
                    ) : (
                      date(null)
                    )}
                  </small>
                </dd>
              </div>
            </dl>
            <p className="muted">
              Cambio frente a la barra agregada anterior o, al inicio del tramo,
              la última sesión anterior disponible. Sin cierre anterior
              disponible, el cambio queda sin dato. Precios conservados en{' '}
              {response.currency}, sin conversión.
            </p>
          </section>
        </>
      )}
      {!prepared.error && (
        <OriginalPricesTable
          key={`${range.start}:${range.end}`}
          bars={prepared.original}
          symbol={response.symbol}
          currency={response.currency}
        />
      )}
    </div>
  );
}

const OriginalPricesTable = memo(function OriginalPricesTable({
  bars,
  symbol,
  currency,
}: {
  bars: readonly DailyBar[];
  symbol: string;
  currency: string;
}) {
  const pagination = usePagination(bars.length);
  return (
    <details className="details prices-original-table">
      <summary>Datos diarios originales</summary>
      <p className="muted">
        Todas las observaciones diarias del rango de fechas, sin agregación ni
        reducción. El zoom del gráfico no modifica esta tabla.
      </p>
      <div className="prices-table-scroll">
        <table>
          <caption>Precios diarios originales · {symbol}</caption>
          <thead>
            <tr>
              {[
                'Sesión',
                `Apertura (${currency})`,
                `Máximo (${currency})`,
                `Mínimo (${currency})`,
                `Cierre (${currency})`,
                'Volumen',
              ].map((label) => (
                <th key={label} scope="col">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bars.slice(pagination.start, pagination.end).map((bar) => (
              <tr key={bar.date}>
                <th scope="row">{date(bar.date)}</th>
                {[bar.open, bar.high, bar.low, bar.close, bar.volume].map(
                  (amount, index) => (
                    <td key={index}>{value(amount)}</td>
                  ),
                )}
              </tr>
            ))}
            {!bars.length && (
              <tr>
                <td colSpan={6}>No hay observaciones en este rango.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <Pagination pagination={pagination} label="precios diarios" />
    </details>
  );
});
