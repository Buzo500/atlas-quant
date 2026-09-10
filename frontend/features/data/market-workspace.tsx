'use client';

import { useState } from 'react';
import type {
  CatalogResponse,
  PortfolioRecord,
  MarketCatalog,
  MarketSeries,
  MarketDetail,
  MarketImport,
  MarketPreview,
  FxBinding,
  FxBindingPreview,
  BindingPreview,
  EvidenceInput,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { Choice, DataTable, Field } from '@/shared/ui';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { CsvEditor, useCorporateReview } from './corporate-shared';
import { PriceExplorer } from '@/features/prices/prices-panel';

export function MarketWorkspace({
  catalog,
  portfolio,
  revision,
  active,
  refresh,
  onError,
}: {
  catalog: CatalogResponse;
  portfolio?: PortfolioRecord;
  revision?: number;
  active: boolean;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const query = useRead<MarketCatalog>({
    path: '/v2/market',
    revision,
    enabled: active,
  });
  const [selected, setSelected] = useState('');
  const [kind, setKind] = useState<'prices' | 'fx'>('prices');
  const [editing, setEditing] = useState(false);
  const series = query.data?.series.find((s) => s.id === selected);
  const refreshAll = async () => {
    await refresh();
    await query.refresh();
  };
  return (
    <section className="panel" aria-label="Precios nativos y tipos de cambio">
      <div className="panel-heading">
        <h2>Precios y tipos de cambio</h2>
        <span className="tag neutral">CSV propio · EUR / USD</span>
      </div>
      <p className="muted">
        Las series conservan sus versiones. Cada cartera elige sus precios y su
        FX; importar otra fuente no sustituye la elegida.
      </p>
      <QueryStatus label="Series de mercado" query={query} />
      {query.data && (
        <DataTable
          heads={[
            'Serie',
            'Unidad',
            'Versión',
            'Cobertura',
            'Base / calendario',
            'Acción',
          ]}
          rows={query.data.series.map((s) => [
            s.name,
            s.kind === 'fx' ? 'EUR por USD' : s.currency,
            s.version,
            `${s.date_min} → ${s.date_max}`,
            `${s.kind === 'fx' ? 'Tipo de cambio' : s.basis_verified ? s.price_basis : 'Base sin acreditar'} · ${s.calendar_verified ? 'Calendario acreditado' : 'Calendario sin acreditar'}`,
            <Button
              key={s.id}
              variant="outline"
              onClick={() => {
                setSelected(s.id);
                setKind(s.kind);
                setEditing(false);
              }}
            >
              Consultar {s.name}
            </Button>,
          ])}
          emptyMessage="Todavía no hay series nativas. Elige una cotización y aporta tu CSV."
        />
      )}
      <div className="actions">
        <Button
          variant="outline"
          onClick={() => {
            setSelected('');
            setKind('prices');
            setEditing(true);
          }}
        >
          Importar precios EUR/USD
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            setSelected('');
            setKind('fx');
            setEditing(true);
          }}
        >
          Importar FX USD → EUR
        </Button>
        {series && (
          <Button variant="outline" onClick={() => setEditing(!editing)}>
            Revisar la serie seleccionada
          </Button>
        )}
      </div>
      {editing && (
        <MarketImportForm
          key={`${kind}:${series?.id}:${series?.version}`}
          kind={kind}
          series={series}
          catalog={catalog}
          refresh={refreshAll}
          onError={onError}
        />
      )}
      {series && (
        <>
          <MarketRead
            key={series.id + ':' + series.version}
            series={series}
            active={active}
          />
          {portfolio?.accounting_policy === 'atlas-accounting-v2' && (
            <MarketBinding
              key={`${portfolio.id}:${portfolio.revision}:${series.id}:${series.version}`}
              portfolio={portfolio}
              series={series}
              active={active}
              refresh={refreshAll}
              onError={onError}
            />
          )}
        </>
      )}
    </section>
  );
}

function MarketImportForm({
  kind,
  series,
  catalog,
  refresh,
  onError,
}: {
  kind: 'prices' | 'fx';
  series?: MarketSeries;
  catalog: CatalogResponse;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [name, setName] = useState(series?.name || '');
  const [source, setSource] = useState(series?.source || '');
  const [listing, setListing] = useState(series?.listing_id || '');
  const [reference, setReference] = useState(series?.symbol || 'ASSET');
  const [csv, setCsv] = useState('');
  const [reason, setReason] = useState('');
  const [revision, setRevision] = useState(false);
  const [raw, setRaw] = useState(false);
  const [basisSource, setBasisSource] = useState('');
  const [calendar, setCalendar] = useState('');
  const [calendarName, setCalendarName] = useState('');
  const [calendarSource, setCalendarSource] = useState('');
  const [market, setMarket] = useState('');
  const [zone, setZone] = useState('UTC');
  const [verified, setVerified] = useState(false);
  const review = useCorporateReview<MarketPreview>(
    `/v2/market/${kind}/imports`,
    refresh,
    onError,
  );
  const change = <T,>(set: (v: T) => void, value: T) => {
    review.invalidate();
    set(value);
  };
  const text = (
    label: string,
    value: string,
    set: (s: string) => void,
    disabled = false,
  ) => (
    <Field label={label}>
      <Input
        value={value}
        disabled={disabled || review.busy}
        onChange={(e) => change(set, e.target.value)}
      />
    </Field>
  );
  const submit = () => {
    const evidence: EvidenceInput = {
      symbol: kind === 'fx' ? 'USD_EUR' : reference,
      calendar_name: calendarName,
      calendar_source: calendarSource,
      market,
      timezone: zone,
      calendar_csv: calendar,
      calendar_verified: verified,
      price_basis: raw ? 'raw' : 'unknown',
      basis_verified: raw,
      basis_source: basisSource,
    };
    const payload: MarketImport = {
      name,
      source,
      listing_id: kind === 'prices' ? listing : null,
      listing_ref: kind === 'prices' ? reference : 'ASSET',
      csv,
      series_id: series?.id,
      expected_version: series?.version ?? 0,
      revise_history: revision,
      reason,
      evidence,
    };
    void review.review(payload);
  };
  return (
    <section className="details" aria-label="Importación de serie nativa">
      <h3>
        {series ? 'Revisar' : 'Importar'}{' '}
        {kind === 'fx'
          ? 'tipo de cambio EUR por USD'
          : 'precios de una cotización'}
      </h3>
      <fieldset disabled={review.busy}>
        <div className="form-grid">
          {text('Nombre de la serie', name, setName, !!series)}
          {text('Fuente de la serie', source, setSource, !!series)}
          {kind === 'prices' && (
            <>
              <Field label="Cotización de los precios">
                <Choice
                  label="Cotización de los precios"
                  value={listing}
                  onChange={(v) => {
                    if (!series) change(setListing, v);
                  }}
                  options={catalog.listings.map((l) => ({
                    value: l.id,
                    label: `${catalog.instruments.find((i) => i.id === l.instrument_id)?.name || l.id} · ${l.market || 'Local'} · ${l.currency} · ${l.id.slice(0, 8)}`,
                  }))}
                />
              </Field>
              {text(
                'Referencia listing_ref del CSV',
                reference,
                setReference,
                !!series,
              )}
            </>
          )}
        </div>
        <p>
          <a href={`/api/v2/market/${kind}/template`} download>
            Descargar plantilla ficticia
          </a>
        </p>
        <CsvEditor
          label="CSV de observaciones"
          value={csv}
          onChange={(v) => change(setCsv, v)}
          onError={onError}
        />
        <details className="details">
          <summary>Base de precios y calendario acreditado</summary>
          <p className="muted">
            Adjunta evidencia de tu fuente. Un calendario vacío queda sin
            acreditar; no se infieren sesiones ni festivos. available_at se
            declara en cada observación y puede quedar vacío.
          </p>
          {kind === 'prices' && (
            <>
              <label className="switch-row">
                <input
                  type="checkbox"
                  checked={raw}
                  onChange={(e) => change(setRaw, e.target.checked)}
                />{' '}
                He contrastado que los precios son brutos, sin ajustar
              </label>
              {text('Evidencia de la base bruta', basisSource, setBasisSource)}
            </>
          )}
          <div className="form-grid">
            {text('Nombre del calendario', calendarName, setCalendarName)}
            {text('Mercado del calendario', market, setMarket)}
            {text('Zona IANA del calendario', zone, setZone)}
            {text('Fuente del calendario', calendarSource, setCalendarSource)}
          </div>
          <Field label="Calendario CSV date,status,close_at">
            <Textarea
              rows={5}
              value={calendar}
              onChange={(e) => change(setCalendar, e.target.value)}
              spellCheck={false}
            />
          </Field>
          <label className="switch-row">
            <input
              type="checkbox"
              checked={verified}
              onChange={(e) => change(setVerified, e.target.checked)}
            />{' '}
            He contrastado la cobertura completa de este calendario
          </label>
        </details>
        {series && (
          <>
            <label className="switch-row">
              <input
                type="checkbox"
                checked={revision}
                onChange={(e) => change(setRevision, e.target.checked)}
              />{' '}
              Revisar explícitamente historia o evidencia
            </label>
            {text('Motivo de la revisión histórica', reason, setReason)}
          </>
        )}
        <Button
          onClick={submit}
          disabled={!csv || !name || !source || (kind === 'prices' && !listing)}
        >
          Previsualizar serie
        </Button>
      </fieldset>
      {review.preview && (
        <section className="notice" aria-label="Previsualización de serie">
          <p>
            {review.preview.series.name} · versión{' '}
            {review.preview.series.version} · {review.preview.added}{' '}
            observaciones nuevas · {review.preview.changed} corregidas.
          </p>
          <p>
            {review.preview.affected_portfolios.length} carteras vinculadas. Sus
            versiones elegidas y cortes guardados se conservan.
          </p>
          <Button disabled={review.busy} onClick={() => void review.confirm()}>
            Confirmar serie
          </Button>
        </section>
      )}
      {review.message && <output>{review.message}</output>}
    </section>
  );
}

function MarketRead({
  series,
  active,
}: {
  series: MarketSeries;
  active: boolean;
}) {
  const [version, setVersion] = useState(series.version);
  const [offset, setOffset] = useState(0);
  const query = useRead<MarketDetail>({
    path: `/v2/market/${series.kind}/${series.id}/versions/${version}?offset=${offset}&limit=500`,
    enabled: active,
  });
  const value = query.data;
  const current =
    value?.series.id === series.id &&
    value.series.version === version &&
    value.offset === offset
      ? value
      : null;
  const info = current?.series;
  return (
    <section className="details" aria-label="Consulta de serie nativa">
      <h3>
        {series.name} · {series.kind === 'fx' ? 'EUR por USD' : series.currency}
      </h3>
      <Field label="Versión de la serie">
        <Input
          type="number"
          min={1}
          max={series.version}
          value={version}
          onChange={(e) => {
            const v = Number(e.target.value);
            if (Number.isInteger(v) && v >= 1 && v <= series.version) {
              setVersion(v);
              setOffset(0);
            }
          }}
        />
      </Field>
      <QueryStatus label="Observaciones de la serie" query={query} />
      {current && info && (
        <>
          <p className="muted">
            Fuente: {info.source} · recibido: {info.received_at}. Mostrando{' '}
            {offset + 1}–{Math.min(offset + 500, current.total)} de{' '}
            {current.total}; textos originales en la tabla.
          </p>
          {series.kind === 'prices' && (
            <PriceExplorer
              key={`${series.id}:${version}:${offset}`}
              response={{
                dataset_id: series.id,
                dataset_version: version,
                manifest_hash: info.sha256,
                symbol: info.symbol,
                currency: info.currency,
                source_kind: 'observed',
                source: info.source,
                source_metadata: null,
                price_basis: info.price_basis,
                calendar: info.calendar_verified
                  ? 'acreditado'
                  : 'sin acreditar',
                warnings: [
                  'Consulta contable; no habilita investigación ni paper con estas series.',
                ],
                available_start: info.date_min,
                available_end: info.date_max,
                first_date: current.observations[0]?.date ?? null,
                last_date: current.observations.at(-1)?.date ?? null,
                preceding_close: null,
                preceding_date: null,
                bars: current.observations.map((b) => ({
                  date: b.date,
                  open: Number(b.open),
                  high: Number(b.high),
                  low: Number(b.low),
                  close: Number(b.close),
                  volume: Number(b.volume),
                })),
              }}
            />
          )}
          <DataTable
            heads={
              series.kind === 'fx'
                ? ['Fecha', 'EUR por USD', 'Disponible desde']
                : [
                    'Fecha',
                    'Apertura',
                    'Máximo',
                    'Mínimo',
                    'Cierre',
                    'Volumen',
                    'Disponible desde',
                  ]
            }
            rows={current.observations.map((b) =>
              series.kind === 'fx'
                ? [b.date, b.rate, b.available_at || 'Sin acreditar']
                : [
                    b.date,
                    b.open,
                    b.high,
                    b.low,
                    b.close,
                    b.volume,
                    b.available_at || 'Sin acreditar',
                  ],
            )}
          />
          <div className="actions">
            <Button
              variant="outline"
              disabled={offset === 0 || query.loading}
              onClick={() => setOffset(Math.max(0, offset - 500))}
            >
              Observaciones anteriores
            </Button>
            <Button
              variant="outline"
              disabled={offset + 500 >= current.total || query.loading}
              onClick={() => setOffset(offset + 500)}
            >
              Observaciones siguientes
            </Button>
          </div>
          <details>
            <summary>Evidencia y huella de esta versión</summary>
            <pre className="technical-data">
              {JSON.stringify(
                { sha256: info.sha256, evidence: current.evidence },
                null,
                2,
              )}
            </pre>
          </details>
        </>
      )}
    </section>
  );
}

function MarketBinding({
  portfolio,
  series,
  active,
  refresh,
  onError,
}: {
  portfolio: PortfolioRecord;
  series: MarketSeries;
  active: boolean;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const fx = useRead<FxBinding>({
    path: `/v2/portfolios/${portfolio.id}/fx-binding`,
    revision: portfolio.revision,
    enabled: active,
  });
  const operation = useCorporateReview<BindingPreview | FxBindingPreview>(
    series.kind === 'fx'
      ? `/v2/portfolios/${portfolio.id}/fx-binding`
      : `/portfolios/${portfolio.id}/bindings`,
    refresh,
    onError,
  );
  const review = () => {
    const bindings = portfolio.bindings.filter(
      (b) => b.listing_id !== series.listing_id,
    );
    const payload =
      series.kind === 'fx'
        ? {
            expected_revision: portfolio.revision,
            series_id: series.id,
            series_version: series.version,
          }
        : {
            bindings: [
              ...bindings,
              {
                listing_id: series.listing_id,
                dataset_id: series.id,
                dataset_version: series.version,
                symbol: series.symbol,
              },
            ],
          };
    void operation.review(payload);
  };
  return (
    <section className="details" aria-label="Vincular serie a cartera">
      <h3>Fuente de valoración de {portfolio.name}</h3>
      {series.kind === 'fx' && fx.data && (
        <p className="muted">
          FX elegido:{' '}
          {fx.data.series_id
            ? `${fx.data.series_id.slice(0, 8)} · v${fx.data.series_version}`
            : 'Sin serie vinculada'}
        </p>
      )}
      <p>
        Elegir {series.name}, versión {series.version}, para{' '}
        {series.kind === 'fx'
          ? 'la conversión contable EUR por USD'
          : 'los precios de esta cotización'}
        . Sustituye el vínculo de esta fuente al confirmar.
      </p>
      <Button variant="outline" disabled={operation.busy} onClick={review}>
        Previsualizar vínculo de serie
      </Button>
      {operation.preview && (
        <div className="notice">
          <p>
            Vínculo revisado para {portfolio.name}, revisión{' '}
            {portfolio.revision}. La serie queda fijada en su versión{' '}
            {series.version}.
          </p>
          <Button
            disabled={operation.busy}
            onClick={() => void operation.confirm()}
          >
            Confirmar vínculo de serie
          </Button>
        </div>
      )}
      {operation.message && <output>{operation.message}</output>}
    </section>
  );
}
