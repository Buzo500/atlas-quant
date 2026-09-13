'use client';

import { useMemo, useState } from 'react';
import type {
  PerformanceReport,
  PerformancePreview,
  PerformanceHistory,
  PerformanceMetric,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { Field, Metric, DataTable } from '@/shared/ui';
import { moneyEUR, percent } from '@/shared/format';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Curve } from '@/components/atlas/curve';
import { useCorporateReview } from '@/features/data/corporate-shared';
import { reasonText, valuationStatus } from './native-valuation';
import { PerformanceExport } from './performance-export';

const statusLabel = { ...valuationStatus, unavailable: 'No disponible' };
const explanations: Record<string, string> = {
  no_positive_recovery:
    'No hay recuperación positiva; la pérdida total queda fuera del dominio de tasas finitas',
  no_duration: 'No hay dos fechas distintas para medir la inversión',
  no_investment:
    'Faltan inversión y recuperación de capital con signos opuestos',
  unsupported_cashflow_pattern:
    'El orden de aportaciones y retiradas no permite acreditar una raíz única con este método',
  out_of_domain: 'La tasa queda fuera del dominio de búsqueda admitido',
  no_convergence: 'No se alcanzó la precisión exigida',
  numeric_range: 'El cálculo supera el rango numérico admitido',
  discontinuous_nav:
    'Falta patrimonio continuo y positivo en la base de cada tramo',
  negative_daily_factor:
    'Los flujos al cierre producen un factor diario incompatible',
  missing_flow_fx: 'Falta FX para convertir un flujo externo del periodo',
  missing_cost_fx: 'Falta FX para convertir un coste del periodo',
  unlinked_dividend_history:
    'Hay un cobro sin derecho histórico acreditado que puede afectar al periodo',
};
const explain = (codes: string[]) =>
  codes.map((c) => explanations[c] || reasonText(c)).join('. ');
const amount = (value: string | null) =>
  value === null ? 'No disponible' : moneyEUR(Number(value));
const rate = (value: string | null) =>
  value === null ? 'No disponible' : percent(Number(value));

function Qualification({
  name,
  metric,
}: {
  name: string;
  metric: PerformanceMetric;
}) {
  return (
    <p className={metric.reasons.length ? 'notice' : 'muted'}>
      {name}: {statusLabel[metric.status]}
      {metric.reasons.length ? '. ' + explain(metric.reasons) : ''}.
    </p>
  );
}

export function PerformanceDetails({ report }: { report: PerformanceReport }) {
  const [page, setPage] = useState(0);
  const [movementPage, setMovementPage] = useState(0);
  const curve = useMemo(() => {
    if (report.twr.value === null || report.points.some((p) => p.nav === null))
      return null;
    let index = 1;
    return report.points.map((point, i) => {
      if (i > 0 && point.twr_factor !== null) index *= Number(point.twr_factor);
      return { date: point.date, nav: Number(point.nav), twr_index: index };
    });
  }, [report]);
  return (
    <section aria-label="Detalle de rentabilidad">
      {report.saved && (
        <PerformanceExport
          key={`${report.portfolio_id}:${report.id}`}
          portfolioId={report.portfolio_id}
          reportId={report.id}
        />
      )}
      <p className="muted">
        Cierres del {report.start_date} al {report.end_date}.{' '}
        {!report.saved
          ? 'Contexto comprobado al calcular; se comprobará de nuevo al guardar.'
          : report.current
            ? 'Contexto vigente en la última consulta.'
            : 'Informe histórico: el contexto ha cambiado.'}
      </p>
      <div className="stats portfolio-stats">
        <Metric
          title="Resultado neto EUR"
          value={amount(report.pnl.display_value)}
        />
        <Metric title="TWR del periodo" value={rate(report.twr.value)} />
        <Metric title="MWR anual · XIRR" value={rate(report.mwr.value)} />
        <Metric
          title="Costes y retenciones EUR"
          value={amount(report.costs_eur.value)}
        />
      </div>
      <Qualification name="Resultado neto" metric={report.pnl} />
      <Qualification name="TWR" metric={report.twr} />
      <Qualification name="MWR" metric={report.mwr} />
      <Qualification name="Costes" metric={report.costs_eur} />
      <p>
        Patrimonio inicial {amount(report.initial_nav)} → patrimonio final{' '}
        {amount(report.final_nav)}. Flujos externos netos:{' '}
        {amount(report.external_net.value)}.
      </p>
      <p className="muted">
        El resultado ya incluye costes y retenciones: no se descuentan otra vez.
        TWR usa la aproximación de flujos al cierre; MWR es una tasa anual con
        días reales/365. Los movimientos de la fecha inicial están incluidos en
        el patrimonio de apertura del periodo.
      </p>
      {curve ? (
        <Curve data={curve} />
      ) : (
        <p className="muted">
          Consulta los cortes diarios y los tramos disponibles. No se dibuja una
          curva continua a través de datos ausentes o bases de rentabilidad
          discontinuas.
        </p>
      )}
      <details className="details">
        <summary>Tramos TWR y cortes diarios</summary>
        <DataTable
          heads={['Inicio', 'Fin', 'TWR', 'Calidad']}
          rows={report.twr.segments.map((s) => [
            s.start_date,
            s.end_date,
            rate(s.value),
            statusLabel[s.status],
          ])}
        />
        <DataTable
          heads={[
            'Cierre',
            'Patrimonio EUR',
            'Flujo externo EUR',
            'Factor diario TWR',
            'Calidad',
          ]}
          rows={report.points
            .slice(page * 100, (page + 1) * 100)
            .map((p) => [
              p.date,
              p.nav ?? 'No disponible',
              p.flow_eur ?? 'No disponible',
              p.twr_factor ?? 'Sin base',
              statusLabel[p.status] +
                (p.reasons.length ? ' · ' + explain(p.reasons) : ''),
            ])}
        />
        <div className="actions">
          <Button
            variant="outline"
            disabled={!page}
            onClick={() => setPage(page - 1)}
          >
            Días anteriores
          </Button>
          <span className="muted">
            {page * 100 + 1}–{Math.min((page + 1) * 100, report.points.length)}{' '}
            de {report.points.length} cortes
          </span>
          <Button
            variant="outline"
            disabled={(page + 1) * 100 >= report.points.length}
            onClick={() => setPage(page + 1)}
          >
            Más días
          </Button>
        </div>
      </details>
      <details className="details">
        <summary>Flujos, costes y tipos de cambio</summary>
        <DataTable
          heads={[
            'Fecha',
            'Flujo nativo',
            'Moneda',
            'Equivalente EUR',
            'FX / fuente / versión',
          ]}
          rows={report.flows
            .slice(movementPage * 100, (movementPage + 1) * 100)
            .map((f) => [
              f.date,
              f.native_amount,
              f.currency,
              f.eur_amount ?? 'No disponible',
              f.fx
                ? `${f.fx.value ?? 'Ausente'} · ${f.fx.source} · v${f.fx.version}`
                : 'Identidad EUR',
            ])}
        />
        <DataTable
          heads={[
            'Fecha',
            'Concepto',
            'Coste nativo',
            'Moneda',
            'Equivalente EUR',
            'FX / fuente / versión',
          ]}
          rows={report.costs
            .slice(movementPage * 100, (movementPage + 1) * 100)
            .map((c) => [
              c.date,
              c.kind === 'tax'
                ? 'Retención'
                : c.kind === 'charge'
                  ? 'Cargo'
                  : 'Comisión',
              c.native_amount,
              c.currency,
              c.eur_amount ?? 'No disponible',
              c.fx
                ? `${c.fx.value ?? 'Ausente'} · ${c.fx.source} · v${c.fx.version}`
                : 'Identidad EUR',
            ])}
        />
        <div className="actions">
          <Button
            variant="outline"
            disabled={!movementPage}
            onClick={() => setMovementPage(movementPage - 1)}
          >
            Movimientos anteriores
          </Button>
          <span className="muted">
            Página {movementPage + 1} · {report.flows.length} flujos y{' '}
            {report.costs.length} costes
          </span>
          <Button
            variant="outline"
            disabled={
              (movementPage + 1) * 100 >=
              Math.max(report.flows.length, report.costs.length)
            }
            onClick={() => setMovementPage(movementPage + 1)}
          >
            Más movimientos
          </Button>
        </div>
      </details>
      <details className="details">
        <summary>Convenciones y procedencia del informe</summary>
        <p>
          {report.historical_known
            ? 'Disponibilidad histórica acreditada en todos los cortes.'
            : 'Este informe no acredita toda la información disponible para decisiones históricas.'}{' '}
          Política {report.policy}.
        </p>
        <p>
          Libro r{report.portfolio_revision}; catálogo r
          {report.source_context.catalog_revision}; eventos r
          {report.source_context.corporate_revision}.
        </p>
        <DataTable
          heads={['Serie de precios', 'Versión elegida']}
          rows={report.source_context.bindings.map((b) => [
            b.dataset_id,
            b.dataset_version,
          ])}
        />
        <p className="native-hash">
          FX: {report.source_context.fx_binding?.series_id ?? 'Sin vínculo'} · v
          {report.source_context.fx_binding?.series_version ?? '—'}.
        </p>
        <p>
          XIRR: dominio [{report.mwr.domain.join(', ')}], hasta{' '}
          {report.mwr.max_iterations} iteraciones; tolerancia de tasa{' '}
          {report.mwr.rate_tolerance} y de residual normalizado{' '}
          {report.mwr.residual_tolerance}. Iteraciones usadas:{' '}
          {report.mwr.iterations}.
        </p>
        <p className="muted">
          Intervalo final: {report.mwr.bracket_width ?? 'No calculado'}.
          Residual: {report.mwr.normalized_residual ?? 'No calculado'}.
        </p>
        <p className="native-hash">
          <code>{report.context_hash}</code>
        </p>
      </details>
    </section>
  );
}

export function NativePerformance({
  portfolioId,
  revision,
  auditSequence,
  active,
}: {
  portfolioId: string;
  revision: number;
  auditSequence?: number;
  active: boolean;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const [start, setStart] = useState(today.slice(0, 4) + '-01-01');
  const [end, setEnd] = useState(today);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState('');
  const [offset, setOffset] = useState(0);
  const path = `/v2/portfolios/${portfolioId}/performance`;
  const history = useRead<PerformanceHistory>({
    path: `${path}?offset=${offset}&limit=20`,
    revision: `${revision}:${auditSequence}`,
    enabled: active,
  });
  const saved = useRead<PerformanceReport>({
    path: selected ? `${path}/${selected}` : null,
    revision: `${revision}:${auditSequence}`,
    enabled: active,
  });
  const operation = useCorporateReview<PerformancePreview>(
    path,
    async () => {
      await history.refresh();
    },
    setError,
  );
  const report =
    operation.preview?.report ??
    (saved.data?.id === selected ? saved.data : null);
  function invalidate() {
    operation.invalidate();
    setSelected('');
    setError('');
  }
  return (
    <section className="panel" aria-label="Rentabilidad por periodo">
      <div className="panel-heading">
        <h2>Rentabilidad por periodo</h2>
        <span className="tag neutral">P&L · TWR · MWR</span>
      </div>
      <form
        className="form-grid"
        onSubmit={(e) => {
          e.preventDefault();
          setSelected('');
          setError('');
          void operation.review({
            start_date: start,
            end_date: end,
            expected_revision: revision,
          });
        }}
      >
        <Field label="Cierre de referencia del periodo">
          <Input
            type="date"
            required
            value={start}
            max={end}
            onChange={(e) => {
              invalidate();
              setStart(e.target.value);
            }}
          />
        </Field>
        <Field label="Cierre final del periodo">
          <Input
            type="date"
            required
            value={end}
            min={start}
            max={today}
            onChange={(e) => {
              invalidate();
              setEnd(e.target.value);
            }}
          />
        </Field>
        <Button
          type="submit"
          disabled={operation.busy || !start || !end || start >= end}
        >
          Calcular rentabilidad
        </Button>
      </form>
      <p className="muted">
        Hasta 3.660 días por consulta. Para TWR continuo, elige como inicio un
        cierre con patrimonio financiado. Para MWR desde la primera aportación,
        usa el cierre anterior con saldo cero conocido. Para informar de todo
        enero, usa 31/12 como referencia y 31/01 como cierre final.
      </p>
      {error && (
        <p className="notice" role="alert">
          {error}
        </p>
      )}
      {operation.busy && (
        <output aria-live="polite">
          Calculando y comprobando el contexto…
        </output>
      )}
      {selected && <QueryStatus label="Informe guardado" query={saved} />}
      {report && <PerformanceDetails key={report.id} report={report} />}
      {operation.preview && (
        <Button
          disabled={operation.busy}
          onClick={() => void operation.confirm()}
        >
          Guardar informe de rentabilidad
        </Button>
      )}
      {operation.message && <output>{operation.message}</output>}
      <details className="details">
        <summary>Informes de rentabilidad guardados</summary>
        <QueryStatus label="Historial de rentabilidad" query={history} />
        {history.data && (
          <>
            <DataTable
              heads={['Inicio', 'Fin', 'P&L EUR', 'TWR', 'MWR anual', 'Acción']}
              rows={history.data.reports.map((r) => [
                r.start_date,
                r.end_date,
                amount(r.pnl.display_value),
                rate(r.twr.value),
                rate(r.mwr.value),
                <Button
                  key={r.id}
                  variant="outline"
                  onClick={() => {
                    operation.invalidate();
                    setSelected(r.id);
                  }}
                >
                  Consultar informe {r.start_date} a {r.end_date}
                </Button>,
              ])}
            />
            <div className="actions">
              <Button
                variant="outline"
                disabled={!offset || history.loading}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Página anterior
              </Button>
              <Button
                variant="outline"
                disabled={history.data.reports.length < 20 || history.loading}
                onClick={() => setOffset(offset + 20)}
              >
                Más informes
              </Button>
            </div>
          </>
        )}
      </details>
    </section>
  );
}
