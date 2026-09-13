'use client';
import { useRef, useState } from 'react';
import { Download, FileCheck2 } from 'lucide-react';
import { api } from '@/lib/api';
import type {
  RetrospectiveContext,
  RetrospectivePreview,
  RetrospectiveSettings,
  RetrospectiveView,
  SimulationConfig,
} from '@/lib/api-types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { DataTable, Field } from '@/shared/ui';
import { useAction } from '@/shared/use-action';
import { date } from '@/shared/format';
import { PeriodResult } from './simulation-result';

const initialConfig: SimulationConfig = {
  policy: 'sma-economics-eur-v1',
  initial_cash_eur: '10000',
  strategy_weight: '1',
  max_position_weight: '1',
  quantity_step: '1',
  fixed_fee_eur: '1',
  fee_bps: '5',
  slippage_bps: '5',
  purchases_enabled: true,
};
const costFields = [
  ['initial_cash_eur', 'Capital inicial EUR'],
  ['strategy_weight', 'Peso de la estrategia (0–1)'],
  ['max_position_weight', 'Límite de posición (0–1)'],
  ['quantity_step', 'Lote mínimo'],
  ['fixed_fee_eur', 'Comisión fija EUR'],
  ['fee_bps', 'Comisión proporcional (pb)'],
  ['slippage_bps', 'Deslizamiento (pb)'],
] as const;
const lines = (text: string) =>
  text
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter((s) => s && s !== 'date');

export function saveResearchFile(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function Context({ value }: { value: RetrospectiveContext }) {
  return (
    <section className="panel" aria-label="Contexto retrospectivo congelado">
      <div className="panel-heading">
        <h3>
          {value.symbol} · SMA {value.fast}/{value.slow}
        </h3>
        <span className="tag">Retrospectivo · sin acreditación</span>
      </div>
      <DataTable
        heads={['Tramo', 'Desde', 'Hasta', 'Sesiones', 'Estado']}
        numericColumns={[3]}
        rows={[
          [
            'Desarrollo',
            date(value.start_date),
            date(value.development_end),
            value.development_sessions,
            'Tramo del estudio',
          ],
          [
            'Reserva',
            date(value.holdout_start),
            date(value.holdout_end),
            value.holdout_sessions,
            'Sin calcular · precios excluidos',
          ],
        ]}
      />
      <p className="muted">
        {value.instrument_id} · {value.market} · EUR. Capital{' '}
        {value.config.initial_cash_eur} EUR; comisión{' '}
        {value.config.fixed_fee_eur ?? '1'} EUR + {value.config.fee_bps ?? '5'}{' '}
        pb; deslizamiento {value.config.slippage_bps ?? '5'} pb.
      </p>
      <details className="details">
        <summary>Procedencia, condiciones y supuestos congelados</summary>
        <p>{value.provider}</p>
        <p>{value.calendar_source}</p>
        <p>{value.event_review}</p>
        <p>
          Peso {value.config.strategy_weight ?? '1'} · límite{' '}
          {value.config.max_position_weight ?? '1'} · lote{' '}
          {value.config.quantity_step ?? '1'}. Apertura modelada 09:00, cierre
          17:30 (14:00 en sesiones abreviadas), decisión 18:00 Europe/Berlin.
        </p>
        <ul>
          {value.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
        <p className="mono native-hash">Protocolo: {value.frozen_hash}</p>
        <p className="mono native-hash">CSV: {value.source_sha256}</p>
      </details>
    </section>
  );
}

export function RetrospectiveLab({
  onError,
}: {
  onError: (message: string) => void;
}) {
  const { busy, run } = useAction(onError);
  const revision = useRef(0);
  const [symbol, setSymbol] = useState(''),
    [instrument, setInstrument] = useState('');
  const [market, setMarket] = useState('XETR'),
    [csv, setCsv] = useState('');
  const [calendar, setCalendar] = useState(''),
    [early, setEarly] = useState('');
  const [holdout, setHoldout] = useState(''),
    [provider, setProvider] = useState('');
  const [calendarSource, setCalendarSource] = useState(''),
    [events, setEvents] = useState('');
  const [fast, setFast] = useState('20'),
    [slow, setSlow] = useState('50');
  const [config, setConfig] = useState(initialConfig);
  const [assumptions, setAssumptions] = useState(false),
    [reviewed, setReviewed] = useState(false);
  const [preview, setPreview] = useState<RetrospectivePreview | null>(null);
  const [result, setResult] = useState<RetrospectiveView | null>(null);
  const [fileStatus, setFileStatus] = useState('');
  function changed(action: () => void) {
    revision.current++;
    setPreview(null);
    setReviewed(false);
    action();
  }
  async function readFile(file: File | undefined, limit: number) {
    if (!file) throw new Error('Selecciona un archivo.');
    if (file.size > limit)
      throw new Error('El archivo supera el tamaño permitido.');
    return file.text();
  }
  async function prepare() {
    const submittedRevision = revision.current;
    const settings: RetrospectiveSettings = {
      symbol: symbol.trim(),
      instrument_id: instrument.trim(),
      market: market.trim(),
      currency: 'EUR',
      timezone: 'Europe/Berlin',
      expected_dates: lines(calendar),
      early_close_dates: lines(early),
      holdout_date: holdout,
      fast: Number(fast),
      slow: Number(slow),
      config,
      provider,
      calendar_source: calendarSource,
      event_review: events,
      acknowledge_assumptions: true,
    };
    const response = await api<RetrospectivePreview>(
      '/lab/retrospective/prepare',
      { settings, csv },
    );
    if (revision.current !== submittedRevision) return;
    setPreview(response);
    setResult(null);
    setReviewed(false);
  }
  async function calculate() {
    if (!preview || !reviewed) return;
    const submittedRevision = revision.current;
    const response = await api<RetrospectiveView>(
      '/lab/retrospective/calculate',
      {
        frozen_json: preview.frozen_json,
        expected_frozen_hash: preview.context.frozen_hash,
      },
    );
    if (revision.current !== submittedRevision) return;
    setResult(response);
    setPreview(null);
    setReviewed(false);
    setFileStatus('Resultado calculado. Descarga el informe para conservarlo.');
  }
  async function reopen(file: File | undefined) {
    const report_json = await readFile(file, 3_000_000);
    const response = await api<RetrospectiveView>('/lab/retrospective/reopen', {
      report_json,
    });
    setResult(response);
    setPreview(null);
    setReviewed(false);
    setFileStatus('Informe reabierto y cálculo reproducido.');
  }
  async function downloadZip() {
    if (!result) return;
    const response = await fetch('/api/lab/retrospective/export', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Atlas-Client': 'local-v1',
      },
      body: JSON.stringify({ report_json: result.report_json }),
    });
    if (
      !response.ok ||
      !response.headers.get('content-type')?.includes('application/zip')
    )
      throw new Error(
        'No se pudo verificar y exportar el informe. No se ha descargado un paquete.',
      );
    saveResearchFile(
      await response.blob(),
      `atlas-retrospectivo-${result.report_hash.slice(0, 12)}.zip`,
    );
    setFileStatus('Descarga del paquete solicitada al navegador.');
  }
  return (
    <div className="research-result retrospective-panel">
      <div className="notice amber vertical">
        <strong>
          Investigación retrospectiva · disponibilidad y ejecución supuestas
        </strong>
        <span>
          Trabaja con precios EUR sin acreditar su disponibilidad histórica. No
          habilita órdenes ni crea una candidata apta para operar.
        </span>
        <span>
          Los informes se conservan descargándolos. Al recargar esta página se
          pierde el borrador; puedes reabrir un informe descargado.
        </span>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>Preparar investigación retrospectiva</h2>
          <span className="tag">SMA · EUR</span>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (assumptions) void run(prepare);
          }}
        >
          <fieldset disabled={busy} className="simulation-fields">
            <div className="form-grid">
              <Field label="Símbolo retrospectivo">
                <Input
                  required
                  value={symbol}
                  maxLength={100}
                  onChange={(e) => changed(() => setSymbol(e.target.value))}
                />
              </Field>
              <Field label="Identificador del instrumento / ISIN">
                <Input
                  required
                  value={instrument}
                  maxLength={100}
                  onChange={(e) => changed(() => setInstrument(e.target.value))}
                />
              </Field>
              <Field label="Mercado retrospectivo">
                <Input
                  required
                  value={market}
                  maxLength={100}
                  onChange={(e) => changed(() => setMarket(e.target.value))}
                />
              </Field>
              <Field label="Reserva desde">
                <Input
                  required
                  type="date"
                  value={holdout}
                  onChange={(e) => changed(() => setHoldout(e.target.value))}
                />
              </Field>
            </div>
            <Field label="Archivo de precios retrospectivos (CSV, máximo 2 MB)">
              <Input
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  e.target.value = '';
                  if (file)
                    void run(async () => {
                      const text = await readFile(file, 2_000_000);
                      changed(() => setCsv(text));
                    });
                }}
              />
            </Field>
            <Field label="CSV retrospectivo">
              <Textarea
                required
                rows={5}
                maxLength={2_000_000}
                value={csv}
                placeholder="date,open,high,low,close,volume,dividends,splits"
                onChange={(e) => changed(() => setCsv(e.target.value))}
              />
            </Field>
            <p className="muted">
              Cabecera exacta: date,open,high,low,close,volume,dividends,splits.
              Fechas ISO, punto decimal, OHLC positivo y volumen entero
              positivo. Se rechazan huecos y dividendos/splits conocidos.
            </p>
            <div className="form-grid">
              <Field label="Calendario esperado · una fecha ISO por línea">
                <Textarea
                  required
                  rows={5}
                  maxLength={30_000}
                  value={calendar}
                  onChange={(e) => changed(() => setCalendar(e.target.value))}
                />
              </Field>
              <Field label="Sesiones abreviadas · una fecha ISO por línea">
                <Textarea
                  rows={5}
                  maxLength={30_000}
                  value={early}
                  onChange={(e) => changed(() => setEarly(e.target.value))}
                />
              </Field>
            </div>
            <Field label="Archivo de calendario (una fecha por línea)">
              <Input
                type="file"
                accept=".csv,.txt,text/plain,text/csv"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  e.target.value = '';
                  if (file)
                    void run(async () => {
                      const text = await readFile(file, 30_000);
                      changed(() => setCalendar(text));
                    });
                }}
              />
            </Field>
            <p className="muted">
              Declara las fechas contrastadas con tu fuente del calendario,
              incluidas desarrollo y reserva. No se infieren sesiones ausentes a
              partir del CSV de precios.
            </p>
            <Field label="Procedencia de los precios">
              <Input
                required
                minLength={3}
                maxLength={500}
                value={provider}
                onChange={(e) => changed(() => setProvider(e.target.value))}
              />
            </Field>
            <Field label="Fuente del calendario">
              <Input
                required
                minLength={3}
                maxLength={3000}
                value={calendarSource}
                onChange={(e) =>
                  changed(() => setCalendarSource(e.target.value))
                }
              />
            </Field>
            <Field label="Revisión de dividendos y splits">
              <Textarea
                required
                minLength={10}
                maxLength={3000}
                rows={2}
                value={events}
                onChange={(e) => changed(() => setEvents(e.target.value))}
              />
            </Field>
            <div className="form-grid">
              <Field label="Media rápida retrospectiva">
                <Input
                  required
                  type="number"
                  min={2}
                  max={249}
                  value={fast}
                  onChange={(e) => changed(() => setFast(e.target.value))}
                />
              </Field>
              <Field label="Media lenta retrospectiva">
                <Input
                  required
                  type="number"
                  min={3}
                  max={250}
                  value={slow}
                  onChange={(e) => changed(() => setSlow(e.target.value))}
                />
              </Field>
              {costFields.map(([key, label]) => (
                <Field label={label} key={key}>
                  <Input
                    required
                    inputMode="decimal"
                    value={config[key]}
                    onChange={(e) =>
                      changed(() =>
                        setConfig((c) => ({ ...c, [key]: e.target.value })),
                      )
                    }
                  />
                </Field>
              ))}
            </div>
            <label className="check-row">
              <input
                type="checkbox"
                checked={assumptions}
                onChange={(e) =>
                  changed(() => setAssumptions(e.target.checked))
                }
              />
              Acepto los horarios y la ejecución modelados, la base no
              acreditada y los límites de este estudio retrospectivo.
            </label>
            <Button type="submit" disabled={!assumptions || busy}>
              <FileCheck2 />
              Congelar y revisar protocolo
            </Button>
          </fieldset>
        </form>
      </section>
      {preview && (
        <>
          <Context value={preview.context} />
          <div className="panel">
            <label className="check-row">
              <input
                type="checkbox"
                checked={reviewed}
                disabled={busy}
                onChange={(e) => setReviewed(e.target.checked)}
              />
              He revisado el protocolo congelado, el periodo, la reserva y los
              costes.
            </label>
            <Button
              disabled={busy || !reviewed}
              onClick={() => void run(calculate)}
            >
              Calcular desarrollo retrospectivo
            </Button>
          </div>
        </>
      )}
      <section className="panel">
        <h3>Reabrir un informe descargado</h3>
        <p className="muted">
          Selecciona el JSON del informe (máximo 3 MB). ATLAS recalcula el
          desarrollo y comprueba su contenido antes de mostrarlo.
        </p>
        <Field label="Informe retrospectivo guardado">
          <Input
            type="file"
            accept=".json,application/json"
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = '';
              if (file) void run(() => reopen(file));
            }}
          />
        </Field>
      </section>
      {result && (
        <>
          <Context value={result.context} />
          <p className={result.code_matches ? 'notice' : 'notice amber'}>
            {result.code_matches
              ? 'Cálculo reproducido con el mismo código registrado en el informe.'
              : 'El cálculo coincide con el informe original, pero el código ha cambiado. Se conserva su procedencia original; no se afirma igualdad del entorno de código.'}
          </p>
          <PeriodResult
            result={result.development}
            title="Resultado retrospectivo de desarrollo"
          />
          <div className="panel">
            <div className="actions">
              <Button
                disabled={busy}
                onClick={() => {
                  saveResearchFile(
                    new Blob([result.report_json], {
                      type: 'application/json',
                    }),
                    `atlas-retrospectivo-${result.report_hash.slice(0, 12)}.json`,
                  );
                  setFileStatus(
                    'Descarga del informe solicitada al navegador.',
                  );
                }}
              >
                <Download />
                Descargar informe JSON
              </Button>
              <Button
                disabled={busy}
                variant="outline"
                onClick={() => void run(downloadZip)}
              >
                <Download />
                Exportar paquete JSON/CSV
              </Button>
            </div>
            <p className="muted">
              La reserva sigue sin calcular. El paquete no contiene sus precios
              ni autoriza operaciones.
            </p>
            <p className="mono native-hash">Informe: {result.report_hash}</p>
          </div>
        </>
      )}
      <output>
        {busy ? 'Procesando investigación retrospectiva…' : fileStatus}
      </output>
    </div>
  );
}
