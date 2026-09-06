'use client';
import { useEffect, useState, useRef } from 'react';
import { api } from '@/lib/api';
import type { DatasetResponse, StateResponse, LedgerResponse, ResearchResponse, ResearchResult as StoredResearch, ExperimentResponse, PortfolioPoint, BacktestPoint } from '@/lib/api-types';
import {
  Play,
  Download,
  Upload,
  Bot,
  Pause,
  ShieldAlert,
  Check,
  X,
  Clock3,
  RefreshCw,
  FileText,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export const money = (n: number) =>
  new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 2,
  }).format(n || 0);
export const pct = (n: number | null | undefined) =>
  n == null ? '—' : (n * 100).toFixed(2) + ' %';
export function Metric({ title, value }: { title: string; value: string }) {
  return (
    <div className="metric">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function Choice({
  value,
  onChange,
  options,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  label: string;
}) {
  return (
    <Select value={value} onValueChange={(v) => onChange(v || '')}>
      <SelectTrigger aria-label={label}>
        <SelectValue placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
export function DataTable({
  heads,
  rows,
}: {
  heads: string[];
  rows: React.ReactNode[][];
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {heads.map((h) => (
            <TableHead key={h}>{h}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r, i) => (
          <TableRow key={i}>
            {r.map((c, j) => (
              <TableCell key={j}>{c}</TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
/* oxlint-disable jsx-a11y/prefer-tag-over-role -- Inline SVG requires image semantics and cannot be replaced by an img containing paths. */
export function Curve({ data }: { data: (PortfolioPoint | BacktestPoint)[] }) {
  const values = data.map((p) => 'nav' in p ? p.nav : p.equity),
    bench = data.every((p) => 'benchmark' in p && p.benchmark != null)
      ? data.map((p) => 'benchmark' in p ? p.benchmark : 0)
      : null,
    all = bench ? [...values, ...bench] : values,
    min = Math.min(...all) * 0.96,
    max = Math.max(...all) * 1.02,
    range = max - min || 1;
  const points = (v: number[]) =>
    v
      .map(
        (x, i) =>
          `${10 + (i / (v.length - 1 || 1)) * 980},${210 - ((x - min) / range) * 190}`,
      )
      .join(' ');
  return (
    <div className="chart">
      <svg
        viewBox="0 0 1000 230"
        role="img"
        aria-label={
          bench
            ? 'Estrategia en verde y benchmark en azul'
            : 'Evolución del patrimonio'
        }
      >
        <defs>
          <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#43ddb8" stopOpacity=".22" />
            <stop offset="1" stopColor="#43ddb8" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[35, 95, 155, 215].map((y) => (
          <line
            key={y}
            x1="0"
            y1={y}
            x2="1000"
            y2={y}
            stroke="#29374a"
            strokeDasharray="4 6"
          />
        ))}
        <polygon
          points={`10,225 ${points(values)} 990,225`}
          fill="url(#area)"
        />
        {bench && (
          <polyline
            points={points(bench)}
            fill="none"
            stroke="#699fe9"
            strokeWidth="2"
            strokeDasharray="6 4"
            vectorEffect="non-scaling-stroke"
          />
        )}
        <polyline
          points={points(values)}
          fill="none"
          stroke="#43ddb8"
          strokeWidth="3"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div className="chart-dates">
        <span>{data[0]?.date}</span>
        {bench && <span>Verde: estrategia · Azul: mantener, mismo peso</span>}
        <span>{data.at(-1)?.date}</span>
      </div>
    </div>
  );
}

/* oxlint-enable jsx-a11y/prefer-tag-over-role */

const DEFAULT_COSTS = {
  initial_cash: 10000,
  commission_bps: 5,
  slippage_bps: 5,
  minimum_fee: 1.25,
  max_position_weight: 0.25,
};
function CostForm({
  costs,
  setCosts,
}: {
  costs: typeof DEFAULT_COSTS;
  setCosts: (c: typeof DEFAULT_COSTS) => void;
}) {
  return (
    <div className="form-grid costs">
      {Object.entries({
        initial_cash: 'Capital simulado (€)',
        commission_bps: 'Comisión (pb)',
        slippage_bps: 'Deslizamiento (pb)',
        minimum_fee: 'Comisión mínima (€)',
        max_position_weight: 'Peso máximo (0–1)',
      }).map(([key, label]) => (
        <Field key={key} label={label}>
          <Input
            type="number"
            min={key === 'initial_cash' ? 100 : 0}
            step={key === 'max_position_weight' ? '.05' : '.25'}
            max={key === 'max_position_weight' ? 1 : undefined}
            value={costs[key as keyof typeof costs]}
            onChange={(e) =>
              setCosts({ ...costs, [key]: Number(e.target.value) })
            }
          />
        </Field>
      ))}
    </div>
  );
}
function useAction(onError: (s: string) => void) {
  const [busy, setBusy] = useState(false);
  async function run(fn: () => Promise<void>) {
    setBusy(true);
    onError('');
    try {
      await fn();
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  return { busy, run };
}

function useDatasetSymbol(dataset: DatasetResponse | undefined) {
  const [selection, setSelection] = useState<{ datasetId?: string; symbol: string } | null>(null);
  const symbols = dataset?.manifest.symbols ?? [];
  const symbol = selection?.datasetId === dataset?.id ? selection?.symbol ?? symbols[0] ?? '' : symbols[0] ?? '';
  const setSymbol = (value: string) => setSelection({ datasetId: dataset?.id, symbol: value });
  return { symbols, symbol, setSymbol };
}

export function Lab({
  dataset,
  onError,
}: {
  dataset: DatasetResponse | undefined;
  onError: (s: string) => void;
}) {
  const { symbols, symbol, setSymbol } = useDatasetSymbol(dataset);
  const [costs, setCosts] = useState(DEFAULT_COSTS),
    [savedResult, setResult] = useState<{ datasetId?: string; result: ResearchResponse } | null>(null);
  const result = savedResult?.datasetId === dataset?.id ? savedResult?.result : null;
  const { busy, run } = useAction(onError);
  return (
    <>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">VALIDACIÓN CRONOLÓGICA</p>
            <h2>Compara antes de confiar.</h2>
          </div>
          <span className="tag">60 % / 20 % / 20 %</span>
        </div>
        <p className="muted">
          Compara mantener el activo y dos cruces de medias. Se elige en
          validación; el último tramo se reserva para evaluar al ganador.
        </p>
        <Field label="Activo">
          <Choice
            value={symbol}
            onChange={setSymbol}
            label="Activo"
            options={symbols.map((s: string) => ({ value: s, label: s }))}
          />
        </Field>
        <CostForm costs={costs} setCosts={setCosts} />
        <Button
          disabled={!symbol || busy}
          onClick={() =>
            run(async () =>
              setResult({
                datasetId: dataset?.id,
                result: await api<ResearchResponse>('/research', {
                  dataset_id: dataset?.id,
                  symbol,
                  costs,
                }),
              }),
            )
          }
        >
          <Play />
          {busy ? 'Calculando…' : 'Ejecutar comparación'}
        </Button>
      </section>
      {result && <ResearchResult result={result} />}
    </>
  );
}
export function ResearchResult({ result }: { result: StoredResearch }) {
  if (!result.out_of_sample || !result.candidate_results || !result.sensitivity)
    return <p className="muted">La investigación aún no tiene resultados completos.</p>;
  const m = result.out_of_sample.metrics;
  return (
    <>
      <div className="stats">
        <Metric
          title="Rentabilidad fuera de muestra"
          value={pct(m.total_return)}
        />
        <Metric title="Frente a mantener" value={pct(m.excess_return)} />
        <Metric title="Máxima caída" value={pct(m.max_drawdown)} />
        <Metric
          title="Sharpe fuera de muestra"
          value={m.sharpe == null ? 'No definido' : m.sharpe.toFixed(2)}
        />
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>Resultado fuera de muestra</h2>
          <span className="tag">{result.selected_strategy.kind}</span>
        </div>
        <Curve data={result.out_of_sample.curve ?? []} />
        <div className="split-periods">
          {(['train_period', 'validation_period', 'test_period'] as const).map((k, i) => (
            <div key={k}>
              <span>{['Preparación', 'Selección', 'Prueba reservada'][i]}</span>
              <strong>
                {result[k] != null
                  ? result[k].start + ' → ' + result[k].end
                  : String(result[k])}
              </strong>
            </div>
          ))}
        </div>
        <p className="muted">
          {m.observations} observaciones · {m.trade_count} ejecuciones ·{' '}
          {money(m.costs)} de costes simulados. Peso máximo:{' '}
          {pct(result.max_position_weight ?? 0.25)}.
        </p>
      </section>
      <section className="panel">
        <h2>La elección, a la vista</h2>
        <DataTable
          heads={[
            'Candidato',
            'Retorno validación',
            'Exceso sobre mantener',
            'Caída máxima',
          ]}
          rows={result.candidate_results.map((c) => [
            c.strategy.kind +
              (c.strategy.kind === 'sma_cross'
                ? ` ${c.strategy.fast_window}/${c.strategy.slow_window}`
                : ''),
            pct(c.validation_metrics.total_return),
            pct(c.validation_metrics.excess_return),
            pct(c.validation_metrics.max_drawdown),
          ])}
        />
        <h3>Sensibilidad a los costes</h3>
        <DataTable
          heads={['Multiplicador', 'Retorno', 'Exceso', 'Caída']}
          rows={result.sensitivity.map((s) => [
            s.cost_multiplier + '×',
            pct(s.metrics.total_return),
            pct(s.metrics.excess_return),
            pct(s.metrics.max_drawdown),
          ])}
        />
        <details className="details">
          <summary>Supuestos y límites del cálculo</summary>
          <ul>
            {(result.warnings ?? []).map((w: string, i: number) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </details>
      </section>
    </>
  );
}

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
    [preview, setPreview] = useState<LedgerResponse | null>(null),
    [ticker, setTicker] = useState(''),
    [start, setStart] = useState('2022-01-01'),
    [end, setEnd] = useState(''),
    [message, setMessage] = useState('');
  const { busy, run } = useAction(onError);
  async function importFile(file: File | undefined) {
    if (file) {
      if (file.size > 8_000_000) throw new Error('Máximo 8 MB.');
      setCsv(await file.text());
      setPreview(null);
    }
  }
  async function submit(commit = false) {
    if (kind === 'prices') {
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
    } else {
      const p = await api<LedgerResponse>('/datasets/' + dataset?.id + '/ledger', {
        csv,
        commit,
      });
      setPreview(p);
      if (commit) {
        setMessage(
          `${p.added} movimientos añadidos; ${p.duplicates} duplicados omitidos.`,
        );
        await refresh();
      }
    }
  }
  return (
    <div className="two-col">
      <section className="panel">
        <div className="panel-heading">
          <h2>Importar tus datos</h2>
          <Upload size={20} />
        </div>
        <Field label="Tipo de archivo">
          <Choice
            value={kind}
            onChange={(v) => {
              setKind(v);
              setPreview(null);
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
              <Switch id="synthetic-data" checked={synthetic} onCheckedChange={setSynthetic} />
              Son datos sintéticos
            </label>
            {dataset && (
              <label className="switch-row" htmlFor="update-data">
                <Switch id="update-data" checked={update} onCheckedChange={setUpdate} />
                Actualizar {dataset.name} conservando su historial
              </label>
            )}
          </>
        )}
        <Field label="Archivo CSV">
          <Input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => run(() => importFile(e.target.files?.[0]))}
          />
        </Field>
        <Field label="Contenido CSV">
          <Textarea
            rows={7}
            value={csv}
            onChange={(e) => {
              setCsv(e.target.value);
              setPreview(null);
            }}
            placeholder={
              kind === 'prices'
                ? 'date,symbol,open,high,low,close,volume,currency'
                : 'id,date,kind,symbol,quantity,price,amount,fee,currency'
            }
          />
        </Field>
        <div className="actions">
          <Button
            disabled={busy || !csv || (kind === 'ledger' && !dataset)}
            onClick={() => run(() => submit(false))}
          >
            {busy
              ? 'Validando…'
              : kind === 'prices'
                ? 'Importar precios'
                : 'Previsualizar movimientos'}
          </Button>
          <a className="text-link" href={'/api/templates/' + kind}>
            <Download size={15} />
            Plantilla CSV
          </a>
        </div>
        {preview && !preview.committed && (
          <div className="notice vertical">
            <strong>
              {preview.added} nuevos · {preview.duplicates} duplicados
            </strong>
            <span>Valor resultante: {money(preview.portfolio.nav)}</span>
            <Button disabled={busy} onClick={() => run(() => submit(true))}>
              Confirmar importación
            </Button>
          </div>
        )}
        {message && (
          <output className="success">
            {message}
          </output>
        )}
      </section>
      <div>
        <section className="panel">
          <div className="panel-heading">
            <h2>Datos diarios gratuitos</h2>
            <RefreshCw size={20} />
          </div>
          <p className="muted">
            Yahoo mediante yfinance. Solo cotizaciones en EUR y días cerrados.
            Se actualizarán cada 6 horas mientras el motor esté encendido.
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
            Disponibilidad y licencia sujetas al proveedor. Si aparecen
            dividendos o splits sin ajustar, se bloquea la promoción automática.
          </p>
        </section>
        {dataset && (
          <section className="panel">
            <h2>Procedencia del conjunto</h2>
            <dl className="metadata">
              <dt>Fuente</dt>
              <dd>{dataset.source}</dd>
              <dt>Versión</dt>
              <dd>{dataset.version}</dd>
              <dt>Rango</dt>
              <dd>
                {dataset.manifest.date_min} → {dataset.manifest.date_max}
              </dd>
              <dt>Barras</dt>
              <dd>{dataset.manifest.row_count}</dd>
              <dt>Huella SHA256</dt>
              <dd className="hash">{dataset.manifest.sha256}</dd>
            </dl>
            {dataset.feed && (
              <>
                <p className="muted">
                  Última consulta: {dataset.feed.last_attempt || 'Pendiente'}
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
    </div>
  );
}

const statusLabels: Record<string, string> = {
  queued: 'En cola',
  running: 'Investigando',
  observing: 'Observando',
  eligible_paper: 'Apto para simulación',
  completed: 'Finalizado',
  failed: 'Error',
  paused: 'Pausado',
  cancelled: 'Cancelado',
  interrupted: 'Interrumpido',
};
export function AgentPanel({
  dataset,
  state,
  refresh,
  onError,
}: {
  dataset: DatasetResponse | undefined;
  state: StateResponse;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const { symbols, symbol, setSymbol } = useDatasetSymbol(dataset);
  const [provider, setProvider] = useState('none'),
    [prompt, setPrompt] = useState(
      'Compara mantener este activo con filtros de tendencia. Busca una reducción de caídas y evalúa el resultado neto de costes frente al benchmark.',
    ),
    [budget, setBudget] = useState(0),
    [hours, setHours] = useState(48),
    [autoPaper, setAutoPaper] = useState(false),
    [costs, setCosts] = useState(DEFAULT_COSTS),
    [selected, setSelected] = useState(''),
    [detail, setDetail] = useState<ExperimentResponse | null>(null),
    [minOos, setMinOos] = useState(126),
    [minSharpe, setMinSharpe] = useState(0.5),
    [maxDrawdown, setMaxDrawdown] = useState(0.15),
    [minForward, setMinForward] = useState(20);
  const { busy, run } = useAction(onError);
  const detailRevision = useRef(0);
  useEffect(() => {
    if (!selected) return;
    let active = true;
    const read = () => {
      const revision = ++detailRevision.current;
      return api<ExperimentResponse>('/experiments/' + selected)
        .then((d) => {
          if (active && revision === detailRevision.current) setDetail(d);
        })
        .catch((e) => {
          if (active) onError(String(e));
        });
    };
    void read();
    const t = setInterval(read, 5000);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, [selected, onError]);
  const providerConfig = state.providers.find(
    (p) => p.provider === provider,
  );
  const missing = provider !== 'none' && !providerConfig?.configured;
  async function create() {
    const j = await api<ExperimentResponse>('/experiments', {
      dataset_id: dataset?.id,
      symbol,
      prompt,
      provider,
      budget_usd: provider === 'none' ? 0 : budget,
      hours,
      auto_paper: autoPaper,
      costs,
      policy: {
        min_oos_observations: minOos,
        min_trades: 10,
        min_sharpe: minSharpe,
        max_drawdown: maxDrawdown,
        min_excess_return: 0,
        min_forward_sessions: minForward,
      },
    });
    setSelected(j.id);
    await refresh();
  }
  async function control(action: 'pause' | 'resume' | 'cancel') {
    ++detailRevision.current;
    const result = await api<ExperimentResponse>('/experiments/' + selected + '/control', { action });
    ++detailRevision.current;
    setDetail(result);
    await refresh();
  }
  return (
    <>
      <div className="two-col agent-layout">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">INVESTIGACIÓN ASISTIDA</p>
              <h2>De una hipótesis a evidencia.</h2>
            </div>
            <Bot size={25} />
          </div>
          <Field label="Qué quieres investigar">
            <Textarea
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </Field>
          <div className="form-grid">
            <Field label="Activo">
              <Choice
                value={symbol}
                onChange={setSymbol}
                label="Activo"
                options={symbols.map((s: string) => ({ value: s, label: s }))}
              />
            </Field>
            <Field label="Analista">
              <Choice
                value={provider}
                onChange={setProvider}
                label="Proveedor de IA"
                options={[
                  { value: 'none', label: 'Catálogo fijo · sin IA' },
                  { value: 'openai', label: 'OpenAI · GPT-5.4 mini' },
                  { value: 'anthropic', label: 'Anthropic · Haiku 4.5' },
                ]}
              />
            </Field>
            <Field
              label="Duración (horas)"
              hint="48 horas son una revisión inicial; la promoción exige al menos 20 sesiones nuevas."
            >
              <Input
                type="number"
                min="1"
                max="8760"
                value={hours}
                onChange={(e) => setHours(Number(e.target.value))}
              />
            </Field>
            <Field
              label="Presupuesto máximo API (USD)"
              hint="Solo se envían la hipótesis y métricas; nunca tus claves ni movimientos de cartera."
            >
              <Input
                type="number"
                min="0"
                max="25"
                step=".25"
                value={budget}
                disabled={provider === 'none'}
                onChange={(e) => setBudget(Number(e.target.value))}
              />
            </Field>
          </div>
          {missing && (
            <div className="notice amber">
              Falta la clave local de {provider}. Puedes configurarla en el
              archivo .env y reiniciar ATLAS; consulta Ajustes.
            </div>
          )}
          <details className="details">
            <summary>Costes y criterios de aprobación</summary>
            <CostForm costs={costs} setCosts={setCosts} />
            <div className="form-grid">
              <Field label="Observaciones fuera de muestra">
                <Input
                  type="number"
                  min="60"
                  value={minOos}
                  onChange={(e) => setMinOos(Number(e.target.value))}
                />
              </Field>
              <Field label="Sharpe mínimo">
                <Input
                  type="number"
                  min="0"
                  step=".1"
                  value={minSharpe}
                  onChange={(e) => setMinSharpe(Number(e.target.value))}
                />
              </Field>
              <Field label="Caída máxima permitida (0–1)">
                <Input
                  type="number"
                  min=".01"
                  max=".5"
                  step=".01"
                  value={maxDrawdown}
                  onChange={(e) => setMaxDrawdown(Number(e.target.value))}
                />
              </Field>
              <Field label="Sesiones nuevas mínimas">
                <Input
                  type="number"
                  min="20"
                  max="504"
                  value={minForward}
                  onChange={(e) => setMinForward(Number(e.target.value))}
                />
              </Field>
            </div>
            <p className="muted">
              Además: ≥10 ejecuciones, exceso no negativo frente al benchmark y
              pruebas con costes duplicados. Los criterios quedan congelados al
              crear el experimento.
            </p>
          </details>
          <label className="switch-row" htmlFor="automatic-paper">
            <Switch id="automatic-paper" checked={autoPaper} onCheckedChange={setAutoPaper} />
            Activar simulación automáticamente si supera los criterios
          </label>
          <Button
            disabled={
              busy || !symbol || missing || (provider !== 'none' && budget <= 0)
            }
            onClick={() => run(create)}
          >
            <Play />
            {busy ? 'Creando…' : 'Iniciar experimento'}
          </Button>
          <p className="footnote">
            Máximo 8 candidatos y 2 llamadas de IA. El motor debe permanecer
            encendido; cerrar esta pestaña no lo detiene. No se enviarán órdenes
            reales.
          </p>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Experimentos</h2>
            <span className="tag">{state.experiments.length}</span>
          </div>
          {state.experiments.length === 0 ? (
            <div className="empty">
              <Clock3 size={30} />
              <h3>El primer experimento empieza aquí</h3>
              <p>
                Sus pruebas, gastos y decisiones quedarán guardados para
                revisarlos después.
              </p>
            </div>
          ) : (
            <div className="jobs">
              {state.experiments.map((j) => (
                <button
                  key={j.id}
                  onClick={() => setSelected(j.id)}
                  className={'job ' + (j.id === selected ? 'selected' : '')}
                >
                  <span className="job-top">
                    <strong>{j.symbol}</strong>
                    <span className="tag">
                      {statusLabels[j.status] || j.status}
                    </span>
                  </span>
                  <span>{j.prompt.slice(0, 110)}</span>
                  <small>
                    {new Date(j.created_at).toLocaleString('es-ES')} · {j.hours}{' '}
                    h · {j.provider === 'none' ? 'Sin IA' : j.provider}
                  </small>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
      {detail && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">EXPEDIENTE {detail.id.slice(0, 8)}</p>
              <h2>
                {detail.symbol} · {statusLabels[detail.status]}
              </h2>
            </div>
            <a
              className="text-link"
              href={'/api/experiments/' + detail.id + '/report'}
            >
              <Download size={16} />
              Exportar informe JSON
            </a>
          </div>
          <div className="stats">
            <Metric
              title="Gasto API estimado"
              value={'$' + detail.spent_usd.toFixed(4)}
            />
            <Metric
              title="Reserva por conciliar"
              value={'$' + detail.reserved_usd.toFixed(4)}
            />
            <Metric
              title="Sesiones nuevas"
              value={String(detail.observation?.new_sessions || 0)}
            />
            <Metric
              title="Observación transcurrida"
              value={(detail.observation?.elapsed_hours || 0).toFixed(1) + ' h'}
            />
          </div>
          {detail.execution_active && detail.control_requested && (
            <output className="muted">
              {detail.control_requested === 'pause' ? 'Pausa solicitada.' : 'Cancelación solicitada.'}{' '}
              Cerrando la operación en curso. No se iniciarán nuevas fases ni llamadas de IA.
            </output>
          )}
          {detail.error && <p className="error">{detail.error}</p>}
          {detail.summary && (
            <div className="report-copy">
              <span className="tag">
                {detail.summary.provider === 'none'
                  ? 'INFORME DEL MOTOR'
                  : 'INFORME DE IA · CONSULTIVO'}
              </span>
              <p>{detail.summary.summary}</p>
              {detail.completion_note && <p>{detail.completion_note}</p>}
              <details className="details">
                <summary>Limitaciones del informe</summary>
                <ul>
                  {detail.summary.limitations.map((s: string, i: number) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </details>
            </div>
          )}
          {detail.gate && (
            <>
              <h3>
                {detail.gate.passed
                  ? 'Criterios superados para simulación'
                  : 'No se autoriza ejecución'}
              </h3>
              <div className="checks">
                {detail.gate.checks.map((c, i: number) => (
                  <div key={i} className="check">
                    {c.passed ? (
                      <Check className="positive" size={18} />
                    ) : (
                      <X className="negative" size={18} />
                    )}
                    <div>
                      <strong>{c.reason || c.name}</strong>
                      <small>
                        Actual: {JSON.stringify(c.actual)} · Requerido:{' '}
                        {JSON.stringify(c.required)}
                      </small>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
          {detail.paper_account && (
            <>
              <h3>Cuenta simulada</h3>
              <p>
                {money(detail.paper_account.equity)} ·{' '}
                {detail.paper_account.fills.length} ejecuciones ·{' '}
                {
                  detail.paper_account.orders.filter(
                    (o) => o.status === 'pending',
                  ).length
                }{' '}
                pendientes
              </p>
              <DataTable
                heads={['Fecha', 'Activo', 'Lado', 'Cantidad', 'Precio']}
                rows={detail.paper_account.fills.map((f) => [
                  f.date,
                  f.symbol,
                  f.side,
                  f.quantity,
                  money(f.price),
                ])}
              />
            </>
          )}
          <div className="actions">
            {['queued', 'running', 'observing', 'eligible_paper'].includes(
              detail.status,
            ) && (
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => run(() => control('pause'))}
              >
                <Pause />
                Pausar
              </Button>
            )}
            {detail.status === 'paused' && (
              <Button
                disabled={busy || detail.execution_active || detail.reserved_usd > 0}
                onClick={() => run(() => control('resume'))}
              >
                Reanudar
              </Button>
            )}
            {['queued', 'running', 'observing', 'eligible_paper', 'paused', 'interrupted'].includes(
              detail.status,
            ) && (
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => run(() => control('cancel'))}
              >
                Cancelar experimento
              </Button>
            )}
          </div>
          {detail.research && (
            <details className="details">
              <summary>Ver pruebas y comparación completa</summary>
              <ResearchResult result={detail.research} />
            </details>
          )}
        </section>
      )}
    </>
  );
}

export function SettingsPanel({
  state,
  refresh,
  onError,
}: {
  state: StateResponse;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const { busy, run } = useAction(onError);
  const [weight, setWeight] = useState(state.settings.max_position_weight);
  return (
    <div className="two-col">
      <div>
        <section className="panel">
          <div className="panel-heading">
            <h2>Control de ejecución</h2>
            <ShieldAlert size={23} />
          </div>
          <p className="muted">
            La parada bloquea nuevas órdenes simuladas y cancela las pendientes.
            Las posiciones existentes permanecen abiertas y se siguen valorando.
          </p>
          <div className="switch-row">
            <Switch
              aria-label="Parada de ejecución"
              disabled={busy}
              checked={state.settings.kill_switch}
              onCheckedChange={(checked) =>
                run(async () => {
                  await api('/settings', {
                    kill_switch: checked,
                    max_position_weight: state.settings.max_position_weight,
                  });
                  await refresh();
                })
              }
            />
            <strong>
              {state.settings.kill_switch
                ? 'Parada activada'
                : 'Simulación habilitada bajo reglas'}
            </strong>
          </div>
          <Field label="Peso máximo por posición (0–1)">
            <Input
              type="number"
              min=".01"
              max="1"
              step=".05"
              value={weight}
              onChange={(e) => setWeight(Number(e.target.value))}
            />
          </Field>
          <Button
            disabled={busy}
            onClick={() =>
              run(async () => {
                await api('/settings', {
                  kill_switch: state.settings.kill_switch,
                  max_position_weight: weight,
                });
                await refresh();
              })
            }
          >
            Guardar límite
          </Button>
          <p className="footnote">
            Cada experimento tiene una cuenta simulada independiente. No se
            agregan como una única cartera. Si su peso validado supera este
            límite, su ejecución se bloquea.
          </p>
        </section>
        <section className="panel">
          <h2>Conectar la IA</h2>
          {state.providers.map((p) => (
            <div key={p.provider} className="provider">
              <div>
                <strong>
                  {p.provider === 'openai' ? 'OpenAI' : 'Anthropic'}
                </strong>
                <span className={'tag ' + (!p.configured ? 'amber' : '')}>
                  {p.configured ? 'CLAVE CONFIGURADA' : 'SIN CLAVE'}
                </span>
              </div>
              <p className="muted">
                {p.models[0].id} · ${p.models[0].input_per_million} entrada / $
                {p.models[0].output_per_million} salida por millón de tokens.
              </p>
            </div>
          ))}
          <p>
            Crea un archivo <code>.env</code> en la carpeta del proyecto, usando{' '}
            <code>.env.example</code> como plantilla. Añade la clave del
            proveedor elegido y reinicia ATLAS.
          </p>
          <p className="muted">
            Las claves solo se leen en el motor local. El archivo queda excluido
            de Git. Los importes son estimaciones en USD; la factura del
            proveedor prevalece.
          </p>
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>Registro de actividad</h2>
          <FileText size={20} />
        </div>
        <div className="audit">
          {state.audit.map((a) => (
            <div key={a.seq}>
              <span className="audit-node" />
              <div>
                <strong>{a.event}</strong>
                <small>{new Date(a.at).toLocaleString('es-ES')}</small>
                <p>{a.entity?.slice(0, 12) || 'Sistema'}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
