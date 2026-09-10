'use client';
import type {
  PlanningReport,
  TargetExposure,
  CombinedTargets,
} from '@/lib/api-types';
import { DataTable, Metric } from '@/shared/ui';
import { ValuationDetails } from './native-valuation';

const number = (v: string | null, suffix = '') =>
  v === null
    ? 'No disponible'
    : new Intl.NumberFormat('es-ES', { maximumFractionDigits: 6 }).format(
        Number(v),
      ) + suffix;
const reasons: Record<string, string> = {
  below_band: 'Por debajo de la banda',
  above_band: 'Por encima de la banda',
  concentration_exceeded: 'Supera concentración',
  no_target: 'Sin objetivo',
};
function Exposures({ rows }: { rows: TargetExposure[] }) {
  return (
    <DataTable
      heads={[
        'Instrumento',
        'Valor EUR',
        'Peso %',
        'Objetivo %',
        'Desviación EUR',
        'Límites',
      ]}
      numericColumns={[1, 2, 3, 4]}
      rows={rows.map((r) => [
        r.label,
        number(r.value_eur),
        number(r.weight),
        number(r.target_weight),
        number(r.deviation_eur),
        r.reasons.map((s) => reasons[s] || s).join(' · ') || 'Dentro de banda',
      ])}
    />
  );
}
function Combined({ value }: { value: CombinedTargets }) {
  return (
    <>
      <h4>Presupuesto compartido</h4>
      <DataTable
        heads={['Estrategia / objetivos', 'Versión', 'Presupuesto %']}
        rows={value.contributors.map((c) => [
          c.target.spec.name,
          `v${c.target.version}`,
          c.budget,
        ])}
      />
      <p className="muted">
        Sin asignar: {value.unassigned_budget} %. Se mantiene en efectivo.
        Redondeo añadido al efectivo: {value.rounding_cash_pp} pp.
      </p>
      <DataTable
        heads={[
          'Instrumento',
          'Objetivo %',
          'Mínimo %',
          'Máximo %',
          'Límite %',
        ]}
        rows={value.spec.rows.map((r) => [
          r.instrument_id
            ? value.labels[r.instrument_id] || r.instrument_id
            : 'Efectivo',
          r.weight,
          r.minimum,
          r.maximum,
          r.concentration_limit,
        ])}
      />
    </>
  );
}
export function PlanningDetails({ report }: { report: PlanningReport }) {
  const result = report.result;
  return (
    <section aria-label="Resultado de planificación">
      <p className="muted">
        {report.saved
          ? report.current
            ? 'Informe guardado · contexto vigente en la última consulta.'
            : 'Informe histórico · el contexto ha cambiado.'
          : 'Previsualización · se comprobarán las fuentes al guardar.'}
      </p>
      {result.kind === 'aggregate' && <Combined value={result.combined} />}
      {result.kind === 'allocation' && (
        <>
          <p className="notice">
            Simulación sin órdenes. Las ventas suponen ejecución y liquidación
            completas antes de comprar. No hay reservas de órdenes, impuestos de
            venta ni diferencial de ejecución estimados.
          </p>
          {result.combined && (
            <details className="details">
              <summary>Objetivos combinados utilizados</summary>
              <Combined value={result.combined} />
            </details>
          )}
          <DataTable
            heads={[
              'Alternativa',
              'Estado',
              'Costes EUR',
              'Patrimonio final EUR',
              'Operaciones simuladas',
            ]}
            rows={result.variants.map((v) => [
              v.mode === 'contributions'
                ? 'Solo aportaciones'
                : 'Rebalanceo con ventas',
              v.status === 'feasible'
                ? 'Dentro de límites'
                : v.status === 'conflicts'
                  ? 'Conflictos pendientes'
                  : 'No disponible',
              number(v.costs_eur),
              number(v.nav_after),
              String(v.trades.length),
            ])}
          />
          {result.variants.map((v) => (
            <details className="details" key={v.mode} open>
              <summary>
                {v.mode === 'contributions'
                  ? 'Detalle de aportaciones'
                  : 'Detalle de rebalanceo'}
              </summary>
              {v.provisional && (
                <p className="notice">Escenario con fuentes provisionales.</p>
              )}
              {v.reasons.length > 0 && (
                <ul>
                  {v.reasons.map((r) => (
                    <li key={r}>
                      {r.replace(
                        /below_band|above_band|concentration_exceeded|no_target/g,
                        (s) => reasons[s],
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <DataTable
                heads={[
                  'Instrumento',
                  'Acción',
                  'Cantidad',
                  'Precio nativo',
                  'Bruto nativo',
                  'Comisión nativa',
                  'Moneda',
                ]}
                numericColumns={[2, 3, 4, 5]}
                rows={v.trades.map((t) => [
                  t.label,
                  t.side === 'buy' ? 'Compra simulada' : 'Venta simulada',
                  number(t.quantity),
                  number(t.price),
                  number(t.gross_native),
                  number(t.fee_native),
                  t.currency,
                ])}
              />
              <DataTable
                heads={[
                  'Efectivo',
                  'Inicial',
                  'Aportación hipotética',
                  'Final hipotético',
                ]}
                rows={v.cash.map((c) => [
                  c.currency,
                  number(c.initial),
                  number(c.contribution),
                  number(c.final),
                ])}
              />
              <Exposures rows={v.rows} />
              <details className="details">
                <summary>
                  Precios utilizados en las operaciones simuladas
                </summary>
                <DataTable
                  heads={[
                    'Instrumento',
                    'Fecha',
                    'Fuente',
                    'Precio',
                    'EUR por USD',
                  ]}
                  rows={v.trades.map((t) => [
                    t.label,
                    t.price_mark.date || 'Sin fecha',
                    t.price_mark.source || 'Sin fuente',
                    t.price,
                    t.fx_mark?.value || 'No aplica',
                  ])}
                />
              </details>
            </details>
          ))}
        </>
      )}
      {result.kind === 'scenario' && (
        <>
          <p className="notice">
            Escenario hipotético. El cambio de divisa afecta a todo el saldo
            USD; el cambio de precio afecta solo a posiciones, no a dividendos
            ya devengados.
          </p>
          <div className="stats portfolio-stats">
            <Metric
              title="Patrimonio inicial"
              value={number(result.nav_before, ' EUR')}
            />
            <Metric
              title="Patrimonio hipotético"
              value={number(result.nav_after, ' EUR')}
            />
            <Metric
              title="Variación hipotética"
              value={number(result.change_eur, ' EUR')}
            />
          </div>
          <p>
            {result.status === 'complete'
              ? 'Cálculo completo'
              : result.status === 'provisional'
                ? 'Fuentes provisionales'
                : 'No disponible'}
          </p>
          {result.reasons.length > 0 && (
            <p className="notice">{result.reasons.join(' · ')}</p>
          )}
          <Exposures rows={result.rows} />
        </>
      )}
      {result.kind === 'benchmark' && (
        <>
          <h3>
            {result.name} · {result.start_date} a {result.end_date}
          </h3>
          <p className="muted">
            Fuente: {result.source}. Rentabilidad total en EUR declarada por el
            usuario. Se normalizan ambas curvas a 100 en el cierre inicial.{' '}
            {result.status === 'provisional'
              ? 'Rentabilidad de cartera provisional.'
              : ''}
          </p>
          <div className="stats portfolio-stats">
            <Metric
              title="Rentabilidad de cartera"
              value={number(
                String(Number(result.portfolio_return) * 100),
                ' %',
              )}
            />
            <Metric
              title="Rentabilidad de referencia"
              value={number(
                String(Number(result.benchmark_return) * 100),
                ' %',
              )}
            />
            <Metric
              title="Diferencia"
              value={number(result.excess_pp, ' pp')}
            />
          </div>
          <DataTable
            heads={['Fecha', 'Cartera · base 100', 'Referencia · base 100']}
            numericColumns={[1, 2]}
            rows={result.points.map((p) => [
              p.date,
              number(p.portfolio_index),
              number(p.benchmark_index),
            ])}
          />
        </>
      )}
      {'cut' in result && (
        <details className="details">
          <summary>Patrimonio y fuentes de partida</summary>
          <ValuationDetails cut={result.cut} />
        </details>
      )}
      <details className="details">
        <summary>Hipótesis y trazabilidad</summary>
        <p className="muted">
          Política {report.policy} · informe <code>{report.id}</code>
        </p>
        <pre className="csv-editor">
          {JSON.stringify(report.inputs, null, 2)}
        </pre>
      </details>
    </section>
  );
}
