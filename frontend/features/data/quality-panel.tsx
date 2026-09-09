'use client';
import { useId, useState } from 'react';
import type {
  DatasetResponse,
  QualityReport,
  EvidenceRequest,
  EvidencePreview,
  RevisionPreview,
} from '@/lib/api-types';
import { api } from '@/lib/api';
import { useRead } from '@/shared/use-read';
import { useAction } from '@/shared/use-action';
import { QueryStatus } from '@/shared/query-status';
import { Choice, DataTable, Field } from '@/shared/ui';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { date, moneyEUR } from '@/shared/format';

import { qualityLabel } from '@/shared/quality';

export function QualityPanel({
  dataset,
  active,
  refresh,
  onError,
}: {
  dataset: DatasetResponse;
  active: boolean;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [symbol, setSymbol] = useState(dataset.manifest.symbols[0]);
  const [start, setStart] = useState(dataset.manifest.date_min);
  const [end, setEnd] = useState(dataset.manifest.date_max);
  const [range, setRange] = useState({ start, end });
  const [offset, setOffset] = useState(0);
  const query = useRead<QualityReport>({
    path: `/datasets/${dataset.id}/quality?${new URLSearchParams({ version: String(dataset.version), symbol, ...range, offset: String(offset) })}`,
    enabled: active,
  });
  const result = query.data;
  return (
    <section className="panel quality-panel" aria-label="Calidad de precios">
      <div className="panel-heading">
        <h2>Calidad de precios</h2>
        <span className="tag neutral">Versión {dataset.version}</span>
      </div>
      <p className="muted">
        Cobertura y marcas para el período elegido. Un hueco no acredita un
        cierre de mercado.
      </p>
      <form
        className="form-grid"
        onSubmit={(e) => {
          e.preventDefault();
          setOffset(0);
          setRange({ start, end });
        }}
      >
        <Field label="Activo del informe">
          <Choice
            label="Activo del informe"
            value={symbol}
            onChange={(v) => {
              setSymbol(v);
              setOffset(0);
            }}
            options={dataset.manifest.symbols.map((s) => ({
              value: s,
              label: s,
            }))}
          />
        </Field>
        <Field label="Calidad desde">
          <Input
            type="date"
            required
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </Field>
        <Field label="Calidad hasta">
          <Input
            type="date"
            required
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </Field>
        <Button type="submit">Consultar calidad</Button>
      </form>
      <QueryStatus label="Calidad" query={query} />
      {result && (
        <>
          <p>
            {result.calendar_name || 'Sin calendario documentado'} ·{' '}
            {result.calendar_verified
              ? 'Verificado por el usuario'
              : 'Sin verificar'}
          </p>
          {result.calendar_source && (
            <p className="muted">Fuente: {result.calendar_source}</p>
          )}
          <DataTable
            heads={['Uso de los precios', 'Estado']}
            rows={[
              ['Dibujar', qualityLabel[result.capabilities.draw]],
              [
                'Valorar el precio al corte',
                qualityLabel[result.capabilities.valuation],
              ],
              [
                'Investigación exploratoria',
                qualityLabel[result.capabilities.exploratory],
              ],
              [
                'Investigación acreditada al cierre',
                qualityLabel[result.capabilities.historical],
              ],
              ['Promoción a paper', qualityLabel[result.capabilities.paper]],
            ]}
          />
          <p className="muted">
            Última marca:{' '}
            {result.last.price_date
              ? date(result.last.price_date)
              : 'No disponible'}{' '}
            · {result.last.age_days ?? '—'} días civiles ·{' '}
            {qualityLabel[result.last.status]}.
          </p>
          <p className="muted">
            {result.last.reasons.map((r) => qualityLabel[r] || r).join(' · ')}
          </p>
          <details className="details">
            <summary>Cobertura por fecha</summary>
            <p>
              {result.total_days} días en el informe.{' '}
              {Object.entries(result.counts)
                .map(([key, count]) => `${qualityLabel[key]}: ${count}`)
                .join(' · ')}
            </p>
            <DataTable
              heads={[
                'Fecha',
                'Estado',
                'Precio usado',
                'Fecha del precio',
                'Antigüedad',
                'Motivos',
              ]}
              rows={result.days.map((d) => [
                date(d.date),
                qualityLabel[d.status],
                d.price === null ? '—' : moneyEUR(d.price),
                d.price_date ? date(d.price_date) : '—',
                d.age_days === null ? '—' : `${d.age_days} días`,
                d.reasons.map((r) => qualityLabel[r] || r).join(' · ') ||
                  'Sin incidencias detectadas',
              ])}
            />
            <div className="actions">
              <Button
                variant="outline"
                disabled={offset === 0 || query.loading}
                onClick={() => setOffset(Math.max(0, offset - 100))}
              >
                Fechas anteriores
              </Button>
              <span>
                {offset + 1}–{Math.min(offset + 100, result.total_days)} de{' '}
                {result.total_days}
              </span>
              <Button
                variant="outline"
                disabled={offset + 100 >= result.total_days || query.loading}
                onClick={() => setOffset(offset + 100)}
              >
                Fechas siguientes
              </Button>
            </div>
          </details>
          <p className="muted">
            La aptitud de estos precios no acredita el patrimonio completo ni la
            conciliación de la cartera. La disponibilidad histórica no se deduce
            de la fecha de descarga.
          </p>
        </>
      )}
      <EvidenceEditor
        key={`${dataset.id}:${dataset.version}:${symbol}`}
        dataset={dataset}
        symbol={symbol}
        refresh={refresh}
        onError={onError}
      />
      <PriceRevision
        key={`revision:${dataset.id}:${dataset.version}`}
        dataset={dataset}
        refresh={refresh}
        onError={onError}
      />
    </section>
  );
}

function EvidenceEditor({
  dataset,
  symbol,
  refresh,
  onError,
}: {
  dataset: DatasetResponse;
  symbol: string;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const calendarId = useId();
  const basisId = useId();
  const [form, setForm] = useState<EvidenceRequest>({
    expected_version: dataset.version,
    symbol,
    calendar_name: '',
    market: '',
    timezone: 'UTC',
    calendar_source: '',
    calendar_verified: false,
    calendar_csv: '',
    price_basis: 'unknown',
    basis_verified: false,
    basis_source: '',
    availability_csv: '',
    availability_source: '',
  });
  const [preview, setPreview] = useState<EvidencePreview | null>(null);
  const action = useAction(onError);
  function update(patch: Partial<EvidenceRequest>) {
    setForm({ ...form, ...patch });
    setPreview(null);
  }
  async function submit(commit: boolean) {
    try {
      const result = await api<EvidencePreview>(
        `/datasets/${dataset.id}/quality`,
        {
          ...form,
          commit,
          preview_token: commit ? preview?.preview_token : undefined,
        },
      );
      if (commit) {
        setPreview(null);
        await refresh();
      } else setPreview(result);
    } catch (error) {
      setPreview(null);
      throw error;
    }
  }
  return (
    <details className="details">
      <summary>Documentar calendario y base de precios</summary>
      <p className="muted">
        Sustituye la evidencia de {symbol} en una nueva versión. Los campos
        vacíos quedan desconocidos. Las carteras conservan su versión fijada.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void action.run(() => submit(false));
        }}
      >
        <fieldset disabled={action.busy} className="quality-fields">
          <legend>Calendario declarado</legend>
          <div className="form-grid">
            <Field label="Nombre del calendario">
              <Input
                maxLength={100}
                value={form.calendar_name}
                onChange={(e) => update({ calendar_name: e.target.value })}
              />
            </Field>
            <Field label="Mercado del calendario">
              <Input
                maxLength={50}
                value={form.market}
                onChange={(e) => update({ market: e.target.value })}
              />
            </Field>
            <Field label="Zona IANA">
              <Input
                maxLength={100}
                value={form.timezone}
                onChange={(e) => update({ timezone: e.target.value })}
              />
            </Field>
            <Field label="Fuente del calendario">
              <Input
                maxLength={500}
                value={form.calendar_source}
                onChange={(e) => update({ calendar_source: e.target.value })}
              />
            </Field>
          </div>
          <Field
            label="CSV del calendario"
            hint="date,status,close_at · Todos los días de cobertura; open con cierre y offset, closed sin hora."
          >
            <Textarea
              rows={5}
              spellCheck={false}
              value={form.calendar_csv}
              maxLength={4000000}
              onChange={(e) => update({ calendar_csv: e.target.value })}
            />
          </Field>
          <label className="toggle" htmlFor={calendarId}>
            <Switch
              id={calendarId}
              checked={form.calendar_verified}
              onCheckedChange={(v) => update({ calendar_verified: v })}
            />
            Calendario contrastado con su fuente
          </label>
        </fieldset>
        <fieldset disabled={action.busy} className="quality-fields">
          <legend>Precios y disponibilidad</legend>
          <div className="form-grid">
            <Field label="Base de los precios">
              <Choice
                label="Base de los precios"
                value={form.price_basis || 'unknown'}
                onChange={(v) =>
                  update({ price_basis: v as EvidenceRequest['price_basis'] })
                }
                options={[
                  { value: 'unknown', label: 'Desconocida' },
                  { value: 'raw', label: 'Observados sin ajustar' },
                  { value: 'split_adjusted', label: 'Ajustados por split' },
                  { value: 'total_return', label: 'Retorno total' },
                ]}
              />
            </Field>
            <Field label="Fuente de la base de precios">
              <Input
                maxLength={500}
                value={form.basis_source}
                onChange={(e) => update({ basis_source: e.target.value })}
              />
            </Field>
          </div>
          <label className="toggle" htmlFor={basisId}>
            <Switch
              id={basisId}
              checked={form.basis_verified}
              onCheckedChange={(v) => update({ basis_verified: v })}
            />
            Base contrastada con su fuente
          </label>
          <Field label="Fuente de la disponibilidad">
            <Input
              maxLength={500}
              value={form.availability_source}
              onChange={(e) => update({ availability_source: e.target.value })}
            />
          </Field>
          <Field
            label="CSV de disponibilidad"
            hint="date,available_at · Timestamp con offset; ausencia significa desconocido."
          >
            <Textarea
              rows={5}
              spellCheck={false}
              maxLength={4000000}
              value={form.availability_csv}
              onChange={(e) => update({ availability_csv: e.target.value })}
            />
          </Field>
        </fieldset>
        <Button type="submit" disabled={action.busy}>
          Previsualizar evidencia
        </Button>
      </form>
      {preview && (
        <output className="notice vertical">
          <strong>Evidencia revisada · {symbol}</strong>
          <span>
            {preview.quality.calendar_name || 'Sin calendario'} ·{' '}
            {preview.quality.calendar_verified
              ? 'Contrastado por el usuario'
              : 'Sin verificar'}{' '}
            · Base: {preview.quality.price_basis}
          </span>
          <span>
            Investigación al cierre:{' '}
            {qualityLabel[preview.quality.capabilities.historical]}. Paper:{' '}
            {qualityLabel[preview.quality.capabilities.paper]}.
          </span>
          <Button
            disabled={action.busy}
            onClick={() => void action.run(() => submit(true))}
          >
            Confirmar evidencia
          </Button>
        </output>
      )}
    </details>
  );
}

function PriceRevision({
  dataset,
  refresh,
  onError,
}: {
  dataset: DatasetResponse;
  refresh: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [csv, setCsv] = useState('');
  const [reason, setReason] = useState('');
  const [preview, setPreview] = useState<RevisionPreview | null>(null);
  const action = useAction(onError);
  async function submit(commit: boolean) {
    try {
      const result = await api<RevisionPreview>(
        `/datasets/${dataset.id}/revisions`,
        {
          expected_version: dataset.version,
          csv,
          reason,
          commit,
          preview_token: commit ? preview?.preview_token : undefined,
        },
      );
      if (commit) {
        setPreview(null);
        await refresh();
      } else setPreview(result);
    } catch (error) {
      setPreview(null);
      throw error;
    }
  }
  return (
    <details className="details">
      <summary>Revisar precios históricos</summary>
      <p className="muted">
        Pega la serie completa en el formato CSV de precios. La revisión
        conserva las versiones anteriores, exige revisar la evidencia de los
        activos afectados y pausa su fuente automática si existe.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void action.run(() => submit(false));
        }}
      >
        <fieldset disabled={action.busy} className="quality-fields">
          <legend>Corrección de la versión {dataset.version}</legend>
          <Field label="Motivo de la revisión">
            <Input
              required
              minLength={3}
              maxLength={500}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                setPreview(null);
              }}
            />
          </Field>
          <Field label="CSV de precios revisados">
            <Textarea
              rows={5}
              required
              maxLength={8000000}
              spellCheck={false}
              value={csv}
              onChange={(e) => {
                setCsv(e.target.value);
                setPreview(null);
              }}
            />
          </Field>
          <Button type="submit" disabled={action.busy}>
            Previsualizar revisión
          </Button>
        </fieldset>
      </form>
      {preview && (
        <output className="notice vertical">
          <strong>
            {preview.changed} barras corregidas · {preview.added} añadidas
          </strong>
          <span>
            Revisar evidencia de: {preview.affected_symbols.join(', ')}.{' '}
            {preview.feed_paused ? 'La fuente automática quedará pausada.' : ''}{' '}
            El libro y sus vínculos se conservan.
          </span>
          <Button
            disabled={action.busy}
            onClick={() => void action.run(() => submit(true))}
          >
            Confirmar revisión de precios
          </Button>
        </output>
      )}
    </details>
  );
}
