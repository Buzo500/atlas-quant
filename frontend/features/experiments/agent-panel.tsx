'use client';
import { useRef, useState } from 'react';
import {
  Play,
  Download,
  Bot,
  Pause,
  Check,
  X,
  Clock3,
  Plus,
} from 'lucide-react';
import { api } from '@/lib/api';
import type {
  DatasetResponse,
  StateResponse,
  ExperimentResponse,
} from '@/lib/api-types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { DataTable, Metric, Choice, Field } from '@/shared/ui';
import { CostForm, DEFAULT_COSTS } from '@/shared/research-forms';
import { useAction } from '@/shared/use-action';
import { useDatasetSymbol } from '@/shared/use-dataset-symbol';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { Pagination, usePagination } from '@/shared/pagination';
import {
  moneyEUR as money,
  apiCostUSD,
  date,
  dateTimeDate,
  dateTimeClock,
  number,
} from '@/shared/format';
import { ResearchResult } from '@/features/research/research-result';
import { CriterionValues } from './criterion-values';

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
  selectedId = '',
  onSelect,
  active = true,
}: {
  dataset: DatasetResponse | undefined;
  state: StateResponse;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
  selectedId?: string;
  onSelect?: (id: string) => void;
  active?: boolean;
}) {
  const { symbols, symbol, setSymbol } = useDatasetSymbol(dataset);
  const createButton = useRef<HTMLButtonElement | null>(null);
  const createToggle = useRef<HTMLButtonElement | null>(null);
  const [provider, setProvider] = useState('none'),
    [prompt, setPrompt] = useState(
      'Compara mantener este activo con filtros de tendencia. Busca una reducción de caídas y evalúa el resultado neto de costes frente al benchmark.',
    ),
    [budget, setBudget] = useState(0),
    [hours, setHours] = useState(48),
    [autoPaper, setAutoPaper] = useState(false),
    [costs, setCosts] = useState(DEFAULT_COSTS),
    [localSelected, setLocalSelected] = useState(''),
    [showCreate, setShowCreate] = useState(state.experiments.length === 0),
    [minOos, setMinOos] = useState(126),
    [minSharpe, setMinSharpe] = useState(0.5),
    [maxDrawdown, setMaxDrawdown] = useState(0.15),
    [minForward, setMinForward] = useState(20);
  const { busy, run } = useAction(onError);
  const selected =
    selectedId || localSelected || state.experiments[0]?.id || '';
  const pagination = usePagination(
    state.experiments.length,
    selected,
    state.experiments.findIndex((experiment) => experiment.id === selected),
  );
  const setSelected = (id: string) => {
    if (onSelect) onSelect(id);
    else setLocalSelected(id);
  };
  const detailQuery = useRead<ExperimentResponse>({
    path: selected ? '/experiments/' + selected : null,
    intervalMs: 5000,
    enabled: active && !busy,
  });
  const detail = detailQuery.data;
  const providerConfig = state.providers.find((p) => p.provider === provider);
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
    // Move focus only if the disappearing submit still owns it. A user may
    // have moved to another field or section while the request was running.
    const submit = createButton.current;
    if (
      submit === document.activeElement &&
      submit &&
      !submit.closest('[hidden], [inert]')
    )
      createToggle.current?.focus();
    setShowCreate(false);
    await refresh();
  }
  async function control(action: 'pause' | 'resume' | 'cancel') {
    detailQuery.invalidate();
    try {
      await api<ExperimentResponse>('/experiments/' + selected + '/control', {
        action,
      });
    } finally {
      await Promise.all([detailQuery.refresh(), refresh()]);
    }
  }
  return (
    <div className={'agent-workspace' + (showCreate ? ' has-config' : '')}>
      <section className="panel experiments-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">INVESTIGACIÓN Y OBSERVACIÓN</p>
            <h2>
              Experimentos{' '}
              <span className="count">{state.experiments.length}</span>
            </h2>
          </div>
          <Button
            ref={createToggle}
            variant="secondary"
            onClick={() => setShowCreate((value) => !value)}
            aria-expanded={showCreate}
            aria-controls="experiment-configuration"
          >
            {showCreate ? <X /> : <Plus />}
            {showCreate ? 'Cerrar formulario' : 'Nuevo experimento'}
          </Button>
        </div>
        {state.experiments.length === 0 ? (
          <div className="empty compact-empty">
            <Clock3 size={28} />
            <h3>Aún no hay experimentos</h3>
            <p>
              Configura una hipótesis para guardar sus pruebas, gastos y
              decisiones.
            </p>
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Activo / hipótesis</TableHead>
                  <TableHead scope="col">Estado</TableHead>
                  <TableHead scope="col">Analista</TableHead>
                  <TableHead scope="col">Creado</TableHead>
                  <TableHead scope="col" className="numeric">
                    Duración
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {state.experiments
                  .slice(pagination.start, pagination.end)
                  .map((j) => (
                    <TableRow
                      key={j.id}
                      className={j.id === selected ? 'selected-row' : undefined}
                    >
                      <TableCell>
                        <div className="experiment-cell">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="experiment-select"
                            aria-label={
                              'Ver experimento ' +
                              j.symbol +
                              ' ' +
                              j.id.slice(0, 8)
                            }
                            aria-pressed={j.id === selected}
                            onClick={() => setSelected(j.id)}
                          >
                            <strong className="code">{j.symbol}</strong>
                          </Button>
                          <span title={j.prompt}>{j.prompt}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className={'tag status-' + j.status}>
                          {statusLabels[j.status] || j.status}
                        </span>
                      </TableCell>
                      <TableCell>
                        {j.provider === 'none' ? 'Sin IA' : j.provider}
                      </TableCell>
                      <TableCell>
                        <time dateTime={j.created_at}>
                          {dateTimeDate(j.created_at)}
                          <br />
                          <span className="muted">
                            {dateTimeClock(j.created_at)}
                          </span>
                        </time>
                      </TableCell>
                      <TableCell className="numeric">{j.hours} h</TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
            <Pagination pagination={pagination} label="experimentos" />
          </>
        )}
      </section>
      {showCreate && (
        <section
          className="panel experiment-config"
          id="experiment-configuration"
        >
          <div className="panel-heading">
            <div>
              <p className="eyebrow">CONFIGURACIÓN</p>
              <h2>Nuevo experimento</h2>
            </div>
            <Bot size={25} />
          </div>
          <Field label="Hipótesis de investigación">
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
            <Switch
              id="automatic-paper"
              checked={autoPaper}
              onCheckedChange={setAutoPaper}
            />
            Activar simulación automáticamente si supera los criterios
          </label>
          <Button
            ref={createButton}
            disabled={
              busy || !symbol || missing || (provider !== 'none' && budget <= 0)
            }
            focusableWhenDisabled={busy}
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
      )}
      {detail && detail.id === selected && (
        <section className="panel experiment-detail">
          <QueryStatus label="Expediente" query={detailQuery} />
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                EXPEDIENTE <code>{detail.id.slice(0, 8)}</code>
              </p>
              <h2>
                {detail.symbol} · {statusLabels[detail.status]}
              </h2>
            </div>
            <a
              className="text-link"
              href={'/api/experiments/' + detail.id + '/report'}
              download
            >
              <Download size={16} />
              Exportar informe JSON
            </a>
          </div>
          <div className="stats">
            <Metric
              title="Gasto API estimado"
              value={apiCostUSD(detail.spent_usd)}
            />
            <Metric
              title="Reserva por conciliar"
              value={apiCostUSD(detail.reserved_usd)}
            />
            <Metric
              title="Sesiones nuevas"
              value={number(detail.observation?.new_sessions, {
                maximumFractionDigits: 0,
              })}
            />
            <Metric
              title="Observación transcurrida"
              value={
                number(detail.observation?.elapsed_hours, {
                  minimumFractionDigits: 1,
                  maximumFractionDigits: 1,
                }) + ' h'
              }
            />
          </div>
          {detail.execution_active && detail.control_requested && (
            <output className="muted">
              {detail.control_requested === 'pause'
                ? 'Pausa solicitada.'
                : 'Cancelación solicitada.'}{' '}
              Cerrando la operación en curso. No se iniciarán nuevas fases ni
              llamadas de IA.
            </output>
          )}
          {detail.error && <p className="error">{detail.error}</p>}
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
                disabled={
                  busy || detail.execution_active || detail.reserved_usd > 0
                }
                onClick={() => run(() => control('resume'))}
              >
                Reanudar
              </Button>
            )}
            {[
              'queued',
              'running',
              'observing',
              'eligible_paper',
              'paused',
              'interrupted',
            ].includes(detail.status) && (
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => run(() => control('cancel'))}
              >
                Cancelar experimento
              </Button>
            )}
          </div>
          <div className="experiment-evidence">
            {detail.summary && (
              <div className="report-copy">
                <h3>Informe de investigación</h3>
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
              <section className="gate-panel">
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
                        <CriterionValues
                          actual={c.actual}
                          required={c.required}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
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
                numericColumns={[3, 4]}
                heads={['Fecha', 'Activo', 'Lado', 'Cantidad', 'Precio']}
                rows={detail.paper_account.fills.map((f) => [
                  date(f.date),
                  <code key="symbol">{f.symbol}</code>,
                  f.side,
                  number(f.quantity, { maximumFractionDigits: 6 }),
                  money(f.price),
                ])}
              />
            </>
          )}
          {detail.research && (
            <details className="details">
              <summary>Ver pruebas y comparación completa</summary>
              <ResearchResult result={detail.research} />
            </details>
          )}
        </section>
      )}
      {selected && detail?.id !== selected && (
        <section className="panel experiment-detail">
          <QueryStatus label="Expediente" query={detailQuery} />
        </section>
      )}
    </div>
  );
}
