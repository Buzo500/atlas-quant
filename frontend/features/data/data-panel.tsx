'use client';
import { useEffect, useRef, useState } from 'react';
import { Download, Upload, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
import type { DatasetResponse } from '@/lib/api-types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Choice, Field } from '@/shared/ui';
import { useAction } from '@/shared/use-action';
import { LedgerImport } from './ledger-import';
import { date, dateTime, number } from '@/shared/format';

export function DataPanel({
  dataset,
  refresh,
  selectDataset,
  onError,
}: {
  dataset: DatasetResponse | undefined;
  refresh: () => Promise<void>;
  selectDataset: (id: string) => void;
  onError: (s: string) => void;
}) {
  const [kind, setKind] = useState('prices'),
    [csv, setCsv] = useState(''),
    [name, setName] = useState('Mi mercado'),
    [source, setSource] = useState(''),
    [update, setUpdate] = useState(false),
    [synthetic, setSynthetic] = useState(false),
    [csvRevision, setCsvRevision] = useState(0),
    [ticker, setTicker] = useState(''),
    [start, setStart] = useState('2022-01-01'),
    [end, setEnd] = useState(''),
    [message, setMessage] = useState('');
  const { busy, run } = useAction(onError);
  const csvEditor = useRef<HTMLTextAreaElement | null>(null);
  const [readingFile, setReadingFile] = useState(false);
  const fileRevision = useRef(0);
  const fileMounted = useRef(true);
  useEffect(() => {
    fileMounted.current = true;
    return () => {
      fileMounted.current = false;
    };
  }, []);
  function invalidateFile() {
    ++fileRevision.current;
    setReadingFile(false);
    setCsvRevision((value) => value + 1);
    setMessage('');
  }
  async function importFile(file: File | undefined) {
    if (!file) return;
    const revision = ++fileRevision.current;
    setCsvRevision((value) => value + 1);
    setReadingFile(true);
    setMessage('');
    onError('');
    try {
      if (file.size > 8_000_000) throw new Error('Máximo 8 MB.');
      const content = await file.text();
      if (fileMounted.current && revision === fileRevision.current)
        setCsv(content);
    } catch (error) {
      if (fileMounted.current && revision === fileRevision.current)
        onError(error instanceof Error ? error.message : String(error));
    } finally {
      if (fileMounted.current && revision === fileRevision.current)
        setReadingFile(false);
    }
  }
  async function submit() {
    if (kind === 'prices') {
      if (!name.trim() || name.length > 100)
        throw new Error(
          'Indica un nombre de conjunto de entre 1 y 100 caracteres.',
        );
      if (source.trim().length < 3 || source.length > 500)
        throw new Error(
          'Indica la procedencia de los precios (entre 3 y 500 caracteres).',
        );
      const d = await api<DatasetResponse>('/datasets', {
        csv,
        name,
        source,
        source_kind: synthetic ? 'synthetic' : 'observed',
        dataset_id: update ? dataset?.id : null,
      });
      selectDataset(d.id);
      setMessage('Precios importados y versión guardada.');
      await refresh();
    }
  }
  return (
    <div className="data-layout">
      <section className="panel data-import">
        <div className="panel-heading">
          <h2>Importar CSV</h2>
          <Upload size={20} />
        </div>
        <Field label="Tipo de archivo">
          <Choice
            value={kind}
            onChange={(v) => {
              setKind(v);
              invalidateFile();
            }}
            label="Tipo de archivo"
            options={[
              { value: 'prices', label: 'Precios diarios OHLCV' },
              { value: 'ledger', label: 'Movimientos de cartera' },
            ]}
          />
        </Field>
        <p className="muted">
          EUR en esta versión. Separador coma o punto y coma; punto decimal. Se
          validan fechas, duplicados y coherencia de precios.
        </p>
        {kind === 'prices' && (
          <>
            <Field label="Nombre del conjunto">
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field
              label="Procedencia"
              hint="Proveedor, exportación y tipo de ajuste. Esta declaración no verifica por sí sola la calidad."
            >
              <Input
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="Ej.: exportación de mi proveedor, OHLC sin ajustar"
              />
            </Field>
            <label className="switch-row" htmlFor="synthetic-data">
              <Switch
                id="synthetic-data"
                checked={synthetic}
                onCheckedChange={setSynthetic}
              />
              Son datos sintéticos
            </label>
            {dataset && (
              <label className="switch-row" htmlFor="update-data">
                <Switch
                  id="update-data"
                  checked={update}
                  onCheckedChange={setUpdate}
                />
                Actualizar {dataset.name} conservando su historial
              </label>
            )}
          </>
        )}
        <Field label="Archivo CSV">
          <Input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => void importFile(e.target.files?.[0])}
          />
        </Field>
        {readingFile && <output className="muted">Leyendo archivo…</output>}
        <Field label="Contenido CSV">
          <Textarea
            ref={csvEditor}
            rows={7}
            value={csv}
            onChange={(e) => {
              setCsv(e.target.value);
              invalidateFile();
            }}
            placeholder={
              kind === 'prices'
                ? 'date,symbol,open,high,low,close,volume,currency'
                : 'id,date,kind,symbol,quantity,price,amount,fee,currency'
            }
          />
        </Field>
        {kind === 'ledger' ? (
          <LedgerImport
            key={`${dataset?.id}:${dataset?.version}:${csvRevision}`}
            dataset={dataset}
            csv={readingFile ? '' : csv}
            refresh={refresh}
            onError={onError}
            onMessage={setMessage}
            onConfirmationRemoved={(button) => {
              // The editor survives a ledger remount after the dataset refresh.
              if (
                button &&
                button === document.activeElement &&
                !button.closest('[hidden], [inert]')
              )
                csvEditor.current?.focus();
            }}
          />
        ) : (
          <div className="actions">
            <Button
              disabled={busy || readingFile || !csv}
              onClick={() => run(submit)}
            >
              {busy ? 'Validando…' : 'Importar precios'}
            </Button>
            <a className="text-link" href="/api/templates/prices" download>
              <Download size={15} />
              Plantilla CSV
            </a>
          </div>
        )}
        {message && <output className="success">{message}</output>}
      </section>
      <section className="panel data-feed">
        <div className="panel-heading">
          <h2>Fuente diaria</h2>
          <RefreshCw size={20} />
        </div>
        <p className="muted">
          Yahoo mediante yfinance. Solo cotizaciones en EUR y días cerrados. Se
          actualizarán cada 6 horas mientras el motor esté encendido.
        </p>
        <Field
          label="Símbolo de Yahoo"
          hint="Usa el ticker exacto del mercado, incluido su sufijo."
        >
          <Input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="Ej.: un ticker europeo en EUR"
          />
        </Field>
        <div className="form-grid">
          <Field label="Histórico desde">
            <Input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </Field>
          <Field
            label="Fin inicial, exclusivo (opcional)"
            hint="Solo para cargar un corte histórico explícito. Las actualizaciones posteriores intentarán obtener todos los días cerrados."
          >
            <Input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </Field>
        </div>
        <Button
          disabled={busy || !ticker}
          onClick={() =>
            run(async () => {
              const d = await api<DatasetResponse>('/feeds', {
                symbol: ticker,
                start,
                end: end || null,
              });
              selectDataset(d.id);
              setMessage('Fuente diaria conectada.');
              await refresh();
            })
          }
        >
          {busy ? 'Consultando…' : 'Conectar fuente diaria'}
        </Button>
        <p className="footnote">
          Disponibilidad y licencia sujetas al proveedor. Si aparecen dividendos
          o splits sin ajustar, se bloquea la promoción automática.
        </p>
      </section>
      {dataset && (
        <section className="panel data-metadata">
          <div className="panel-heading">
            <h2>Conjunto seleccionado</h2>
            <span className="tag">v{dataset.version}</span>
          </div>
          <p className="dataset-name">{dataset.name}</p>
          <dl className="metadata">
            <dt>Fuente</dt>
            <dd>{dataset.source}</dd>
            <dt>Versión</dt>
            <dd>{dataset.version}</dd>
            <dt>Rango</dt>
            <dd>
              {date(dataset.manifest.date_min)} →{' '}
              {date(dataset.manifest.date_max)}
            </dd>
            <dt>Barras</dt>
            <dd>
              {number(dataset.manifest.row_count, { maximumFractionDigits: 0 })}
            </dd>
            <dt>Huella SHA256</dt>
            <dd className="hash">{dataset.manifest.sha256}</dd>
          </dl>
          {dataset.feed && (
            <>
              <p className="muted">
                Última consulta:{' '}
                {dataset.feed.last_attempt
                  ? dateTime(dataset.feed.last_attempt)
                  : 'Pendiente'}
              </p>
              {dataset.feed.error && (
                <p className="error">{dataset.feed.error}</p>
              )}
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    await api('/feeds/' + dataset.id + '/refresh', {});
                    await refresh();
                  })
                }
              >
                Actualizar ahora
              </Button>
            </>
          )}
        </section>
      )}
    </div>
  );
}
