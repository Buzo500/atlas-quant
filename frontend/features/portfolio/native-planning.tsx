'use client';
import { useState } from 'react';
import type {
  CatalogResponse,
  TargetHistory,
  ValuationHistory,
  PerformanceHistory,
  PlanningInput,
  PlanningReport,
  PlanningPreview,
  PlanningHistory,
  TradeRule,
  StrategyBudget,
  PriceShock,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { Choice, DataTable, Field } from '@/shared/ui';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  CsvEditor,
  useCorporateReview,
} from '@/features/data/corporate-shared';
import { PlanningDetails } from './planning-results';

type Props = {
  portfolioId: string;
  revision: number;
  auditSequence?: number;
  active: boolean;
};
const kinds = [
  { value: 'allocation', label: 'Aportaciones y rebalanceo' },
  { value: 'aggregate', label: 'Combinar estrategias' },
  { value: 'benchmark', label: 'Comparar referencia' },
  { value: 'scenario', label: 'Escenarios de cartera' },
];

export function PlanningWorkspace({
  portfolioId,
  revision,
  auditSequence,
  active,
}: Props) {
  const base = `/v2/portfolios/${portfolioId}`;
  const [error, setError] = useState('');
  const [kind, setKind] = useState<PlanningInput['kind']>('allocation');
  const [cut, setCut] = useState('');
  const [eur, setEur] = useState('0');
  const [usd, setUsd] = useState('0');
  const [existing, setExisting] = useState(false);
  const [rules, setRules] = useState<TradeRule[]>([]);
  const [listing, setListing] = useState('');
  const [strategies, setStrategies] = useState<StrategyBudget[]>([]);
  const [strategy, setStrategy] = useState('');
  const [shocks, setShocks] = useState<PriceShock[]>([]);
  const [instrument, setInstrument] = useState('');
  const [fx, setFx] = useState('0');
  const [performance, setPerformance] = useState('');
  const [name, setName] = useState('');
  const [source, setSource] = useState('');
  const [csv, setCsv] = useState('');
  const [basis, setBasis] = useState(false);
  const [selected, setSelected] = useState('');
  const [offset, setOffset] = useState(0);
  const rev = `${revision}:${auditSequence}`;
  const history = useRead<TargetHistory>({
    path: `${base}/targets?limit=100`,
    revision: rev,
    enabled: active,
  });
  const catalog = useRead<CatalogResponse>({
    path: '/catalog',
    revision: auditSequence,
    enabled: active,
  });
  const cuts = useRead<ValuationHistory>({
    path: `${base}/valuations?limit=100`,
    revision: rev,
    enabled: active && (kind === 'allocation' || kind === 'scenario'),
  });
  const performances = useRead<PerformanceHistory>({
    path: `${base}/performance?limit=100`,
    revision: rev,
    enabled: active && kind === 'benchmark',
  });
  const reports = useRead<PlanningHistory>({
    path: `${base}/planning-reports?offset=${offset}&limit=20`,
    revision: rev,
    enabled: active,
  });
  const saved = useRead<PlanningReport>({
    path: selected ? `${base}/planning-reports/${selected}` : null,
    revision: rev,
    enabled: active,
  });
  const review = useCorporateReview<PlanningPreview>(
    `${base}/planning-reports`,
    reports.refresh,
    setError,
  );
  const current =
    review.preview &&
    review.preview.report.inputs.expected_targets_revision ===
      history.data?.revision
      ? review.preview
      : null;
  const shown = selected ? saved.data : current?.report;
  const busy = review.busy || !active;
  function edit(action: () => void) {
    review.invalidate();
    setSelected('');
    setError('');
    action();
  }
  function title(id: string) {
    const l = catalog.data?.listings.find((l) => l.id === id);
    return `${catalog.data?.instruments.find((i) => i.id === l?.instrument_id)?.name || id} · ${l?.market || ''} · ${l?.currency || ''}`;
  }
  function calculate() {
    setSelected('');
    setError('');
    const body: PlanningInput = {
      kind,
      expected_revision: revision,
      expected_targets_revision: history.data?.revision || 0,
    };
    if (kind === 'allocation')
      Object.assign(body, {
        cut_id: cut,
        contribution_eur: eur,
        contribution_usd: usd,
        use_existing_cash: existing,
        rules,
        strategies,
      });
    if (kind === 'aggregate') Object.assign(body, { strategies });
    if (kind === 'scenario')
      Object.assign(body, {
        cut_id: cut,
        price_shocks: shocks,
        usd_eur_change_percent: fx,
      });
    if (kind === 'benchmark')
      Object.assign(body, {
        performance_id: performance,
        benchmark_name: name,
        benchmark_source: source,
        benchmark_csv: csv,
        benchmark_basis_confirmed: basis,
      });
    void review.review(body);
  }
  return (
    <>
      <QueryStatus label="Objetivos de planificación" query={history} />
      <QueryStatus label="Catálogo de planificación" query={catalog} />
      <Choice
        label="Tipo de análisis"
        value={kind}
        options={kinds}
        onChange={(v) => edit(() => setKind(v as PlanningInput['kind']))}
      />
      {!history.data?.active && kind !== 'benchmark' && (
        <p className="notice">
          Primero guarda y activa los objetivos globales en «Objetivos y
          desviaciones».
        </p>
      )}
      {(kind === 'allocation' || kind === 'scenario') && (
        <>
          <QueryStatus label="Cortes de planificación" query={cuts} />
          <Choice
            label="Patrimonio de partida"
            value={cut}
            onChange={(v) => edit(() => setCut(v))}
            options={(cuts.data?.cuts || []).map((c) => ({
              value: c.id,
              label: `${c.as_of_date} · ${c.value ?? 'No disponible'} EUR · ${c.status}`,
            }))}
          />
          <p className="muted">
            Selecciona uno de los 100 cortes guardados más recientes. Se
            comprobará que sigue vigente.
          </p>
        </>
      )}
      {kind === 'allocation' && (
        <>
          <div className="form-grid">
            <Field label="Aportación hipotética EUR">
              <Input
                aria-label="Aportación hipotética EUR"
                type="number"
                min="0"
                step="0.01"
                value={eur}
                onChange={(e) => edit(() => setEur(e.target.value))}
              />
            </Field>
            <Field label="Aportación hipotética USD">
              <Input
                aria-label="Aportación hipotética USD"
                type="number"
                min="0"
                step="0.01"
                value={usd}
                onChange={(e) => edit(() => setUsd(e.target.value))}
              />
            </Field>
          </div>
          <label className="check-field">
            <input
              type="checkbox"
              checked={existing}
              onChange={(e) => edit(() => setExisting(e.target.checked))}
            />{' '}
            Permitir usar también efectivo existente
          </label>
          <p className="muted">
            Sin conversiones de moneda. Prioridad menor se atiende antes; a
            igual prioridad, primero el mayor déficit EUR. Los lotes se
            redondean hacia abajo y las comisiones hacia arriba al céntimo. Las
            ventas solo forman parte de la alternativa de rebalanceo.
          </p>
          {rules.map((r, index) => (
            <fieldset className="planning-rule" key={r.listing_id}>
              <legend>{title(r.listing_id)}</legend>
              <div className="form-grid">
                {(
                  ['quantity_step', 'fixed_fee', 'fee_bps', 'priority'] as const
                ).map((key) => {
                  const labels = {
                    quantity_step: 'Lote mínimo',
                    fixed_fee: 'Comisión fija nativa',
                    fee_bps: 'Comisión proporcional (pb)',
                    priority: 'Prioridad',
                  };
                  return (
                    <Field key={key} label={labels[key]}>
                      <Input
                        aria-label={`${labels[key]} · ${index + 1}`}
                        type="number"
                        min="0"
                        step={key === 'priority' ? '1' : 'any'}
                        value={r[key]}
                        onChange={(e) =>
                          edit(() =>
                            setRules(
                              rules.map((old, i) =>
                                i === index
                                  ? {
                                      ...old,
                                      [key]:
                                        key === 'priority'
                                          ? Number(e.target.value)
                                          : e.target.value,
                                    }
                                  : old,
                              ),
                            ),
                          )
                        }
                      />
                    </Field>
                  );
                })}
              </div>
              <Button
                variant="outline"
                onClick={() =>
                  edit(() => setRules(rules.filter((_, i) => i !== index)))
                }
              >
                Quitar cotización {index + 1}
              </Button>
            </fieldset>
          ))}
          <div className="form-grid">
            <Choice
              label="Cotización para simular"
              value={listing}
              onChange={setListing}
              options={(catalog.data?.listings || [])
                .filter((l) => !rules.some((r) => r.listing_id === l.id))
                .map((l) => ({ value: l.id, label: title(l.id) }))}
            />
            <Button
              variant="outline"
              disabled={!listing || rules.length >= 199}
              onClick={() =>
                edit(() => {
                  setRules([
                    ...rules,
                    {
                      listing_id: listing,
                      quantity_step: '1',
                      fixed_fee: '',
                      fee_bps: '',
                      priority: 0,
                    },
                  ]);
                  setListing('');
                })
              }
            >
              Añadir cotización al plan
            </Button>
          </div>
        </>
      )}
      {(kind === 'allocation' || kind === 'aggregate') && (
        <details className="details" open={kind === 'aggregate'}>
          <summary>Presupuestos de varias estrategias</summary>
          <p className="muted">
            Cada conjunto de objetivos representa una estrategia manual. Los
            presupuestos comparten una sola cartera y suman como máximo 100 %.
            El resto queda en efectivo. Se conservan los límites globales
            activos. Sin selección se usan únicamente esos objetivos activos.
          </p>
          {strategies.map((s, i) => (
            <div className="form-grid" key={s.target_id}>
              <Field
                label={`${history.data?.targets.find((t) => t.id === s.target_id)?.spec.name || s.target_id} · presupuesto %`}
              >
                <Input
                  aria-label={`Presupuesto de estrategia ${i + 1}`}
                  type="number"
                  min="0"
                  max="100"
                  step="any"
                  value={s.budget}
                  onChange={(e) =>
                    edit(() =>
                      setStrategies(
                        strategies.map((old, j) =>
                          j === i ? { ...old, budget: e.target.value } : old,
                        ),
                      ),
                    )
                  }
                />
              </Field>
              <Button
                variant="outline"
                onClick={() =>
                  edit(() =>
                    setStrategies(strategies.filter((_, j) => j !== i)),
                  )
                }
              >
                Quitar estrategia {i + 1}
              </Button>
            </div>
          ))}
          <div className="form-grid">
            <Choice
              label="Objetivos de estrategia"
              value={strategy}
              onChange={setStrategy}
              options={(history.data?.targets || [])
                .filter((t) => !strategies.some((s) => s.target_id === t.id))
                .map((t) => ({
                  value: t.id,
                  label: `${t.spec.name} · v${t.version}`,
                }))}
            />
            <Button
              variant="outline"
              disabled={!strategy || strategies.length >= 20}
              onClick={() =>
                edit(() => {
                  setStrategies([
                    ...strategies,
                    { target_id: strategy, budget: '' },
                  ]);
                  setStrategy('');
                })
              }
            >
              Añadir estrategia al presupuesto
            </Button>
          </div>
        </details>
      )}
      {kind === 'scenario' && (
        <>
          <Field label="Variación de EUR por USD (%)">
            <Input
              aria-label="Variación de EUR por USD (%)"
              type="number"
              step="any"
              value={fx}
              onChange={(e) => edit(() => setFx(e.target.value))}
            />
          </Field>
          <p className="muted">
            Por ejemplo, +5 significa que cada USD vale un 5 % más de EUR. Los
            instrumentos sin cambio mantienen su precio.
          </p>
          {shocks.map((s, i) => (
            <div className="form-grid" key={s.instrument_id}>
              <Field
                label={`Cambio de precio · ${catalog.data?.instruments.find((v) => v.id === s.instrument_id)?.name || s.instrument_id} (%)`}
              >
                <Input
                  aria-label={`Cambio de precio ${i + 1}`}
                  type="number"
                  min="-100"
                  max="1000"
                  step="any"
                  value={s.change_percent}
                  onChange={(e) =>
                    edit(() =>
                      setShocks(
                        shocks.map((old, j) =>
                          i === j
                            ? { ...old, change_percent: e.target.value }
                            : old,
                        ),
                      ),
                    )
                  }
                />
              </Field>
              <Button
                variant="outline"
                onClick={() =>
                  edit(() => setShocks(shocks.filter((_, j) => i !== j)))
                }
              >
                Quitar cambio {i + 1}
              </Button>
            </div>
          ))}
          <div className="form-grid">
            <Choice
              label="Instrumento del escenario"
              value={instrument}
              onChange={setInstrument}
              options={(catalog.data?.instruments || [])
                .filter((i) => !shocks.some((s) => s.instrument_id === i.id))
                .map((i) => ({ value: i.id, label: i.name }))}
            />
            <Button
              variant="outline"
              disabled={!instrument || shocks.length >= 199}
              onClick={() =>
                edit(() => {
                  setShocks([
                    ...shocks,
                    { instrument_id: instrument, change_percent: '0' },
                  ]);
                  setInstrument('');
                })
              }
            >
              Añadir cambio de precio
            </Button>
          </div>
        </>
      )}
      {kind === 'benchmark' && (
        <>
          <QueryStatus
            label="Rentabilidades para comparar"
            query={performances}
          />
          <Choice
            label="Rentabilidad de cartera para comparar"
            value={performance}
            onChange={(v) => edit(() => setPerformance(v))}
            options={(performances.data?.reports || []).map((p) => ({
              value: p.id,
              label: `${p.start_date} a ${p.end_date} · ${p.twr.status}`,
            }))}
          />
          <div className="form-grid">
            <Field label="Nombre de referencia">
              <Input
                aria-label="Nombre de referencia"
                maxLength={120}
                value={name}
                onChange={(e) => edit(() => setName(e.target.value))}
              />
            </Field>
            <Field label="Fuente de referencia">
              <Input
                aria-label="Fuente de referencia"
                maxLength={500}
                value={source}
                onChange={(e) => edit(() => setSource(e.target.value))}
              />
            </Field>
          </div>
          <p className="muted">
            CSV UTF-8 con cabecera <code>date,value</code>: un índice de
            rentabilidad total en EUR para cada fecha del informe, incluidos
            días sin sesión. Debe incorporar dividendos, reinversión y
            conversión a EUR según su fuente; una serie de precios brutos no es
            comparable. Máximo 3.661 filas y 500.000 caracteres.
          </p>
          <CsvEditor
            label="CSV de referencia"
            value={csv}
            onChange={(v) => edit(() => setCsv(v))}
            onError={setError}
          />
          <label className="check-field">
            <input
              type="checkbox"
              checked={basis}
              onChange={(e) => edit(() => setBasis(e.target.checked))}
            />{' '}
            Confirmo que la referencia representa rentabilidad total en EUR
          </label>
        </>
      )}
      {error && (
        <p role="alert" className="notice">
          {error}
        </p>
      )}
      <div className="actions">
        <Button
          disabled={
            busy ||
            history.loading ||
            !history.data ||
            (kind !== 'benchmark' && !history.data.active)
          }
          onClick={calculate}
        >
          Calcular análisis
        </Button>
        {current && (
          <Button disabled={busy} onClick={() => void review.confirm()}>
            Guardar análisis
          </Button>
        )}
      </div>
      {review.message && <output>{review.message}</output>}
      {shown && <PlanningDetails report={shown} />}
      <details className="details">
        <summary>Análisis guardados</summary>
        <QueryStatus label="Historial de planificación" query={reports} />
        {selected && <QueryStatus label="Análisis guardado" query={saved} />}
        <DataTable
          heads={['Tipo', 'Creación', 'Acción']}
          rows={(reports.data?.reports || []).map((r) => [
            kinds.find((k) => k.value === r.kind)?.label || r.kind,
            r.created_at,
            <Button
              key={r.id}
              variant="outline"
              onClick={() => {
                review.invalidate();
                setSelected(r.id);
              }}
            >
              Consultar análisis {r.created_at}
            </Button>,
          ])}
        />
        <div className="actions">
          <Button
            variant="outline"
            disabled={offset === 0 || reports.loading}
            onClick={() => setOffset(Math.max(0, offset - 20))}
          >
            Análisis recientes
          </Button>
          <Button
            variant="outline"
            disabled={
              (reports.data?.reports.length || 0) < 20 || reports.loading
            }
            onClick={() => setOffset(offset + 20)}
          >
            Análisis anteriores
          </Button>
        </div>
      </details>
    </>
  );
}

export function NativePlanning(props: Props) {
  const [open, setOpen] = useState(false);
  const [visited, setVisited] = useState(false);
  return (
    <section
      className="panel native-planning"
      aria-label="Planificación y escenarios"
    >
      <div className="panel-heading">
        <h2>Planificación y escenarios</h2>
        <span className="tag neutral">Simulación</span>
      </div>
      <p className="muted">
        Compara aportaciones y rebalanceo, combina objetivos y explora
        referencias o cambios de mercado.
      </p>
      <details
        className="details"
        onToggle={(e) => {
          setOpen(e.currentTarget.open);
          if (e.currentTarget.open) setVisited(true);
        }}
      >
        <summary>Abrir análisis de cartera</summary>
        {visited && (
          <PlanningWorkspace {...props} active={props.active && open} />
        )}
      </details>
    </section>
  );
}
