'use client';
import type { ResearchResult as StoredResearch } from '@/lib/api-types';
import { Curve } from '@/components/atlas/curve';
import { DataTable, Metric } from '@/shared/ui';
import {
  moneyEUR as money,
  percent as pct,
  date,
  dateTime,
  number,
} from '@/shared/format';

export function ResearchResult({ result }: { result: StoredResearch }) {
  if (!result.out_of_sample || !result.candidate_results || !result.sensitivity)
    return (
      <p className="muted">
        La investigación aún no tiene resultados completos.
      </p>
    );
  const m = result.out_of_sample.metrics;
  return (
    <div className="research-result">
      {result.execution && (
        <section
          className="panel research-context"
          aria-label="Contexto de la ejecución"
        >
          <div className="panel-heading">
            <div>
              <p className="eyebrow">RESULTADO DE ESTA EJECUCIÓN</p>
              <h2>
                {result.execution.symbol} · {result.execution.dataset_name}
              </h2>
              <p className="muted">
                Versión {result.execution.dataset_version} ·{' '}
                {date(result.execution.period.start)} →{' '}
                {date(result.execution.period.end)} ·{' '}
                {number(result.execution.period.observations, {
                  maximumFractionDigits: 0,
                })}{' '}
                observaciones
              </p>
            </div>
            <time className="muted" dateTime={result.execution.completed_at}>
              {dateTime(result.execution.completed_at)}
            </time>
          </div>
          <details className="details">
            <summary>Parámetros y trazabilidad de la ejecución</summary>
            <dl className="metadata">
              <dt>Capital simulado</dt>
              <dd>{money(result.execution.costs.initial_cash)}</dd>
              <dt>Comisión</dt>
              <dd>
                {number(result.execution.costs.commission_bps, {
                  maximumFractionDigits: 6,
                })}{' '}
                pb
              </dd>
              <dt>Deslizamiento</dt>
              <dd>
                {number(result.execution.costs.slippage_bps, {
                  maximumFractionDigits: 6,
                })}{' '}
                pb
              </dd>
              <dt>Comisión mínima</dt>
              <dd>{money(result.execution.costs.minimum_fee)}</dd>
              <dt>Peso máximo</dt>
              <dd>{pct(result.execution.costs.max_position_weight)}</dd>
              <dt>Ejecución</dt>
              <dd className="hash">
                <code>{result.execution.id}</code>
              </dd>
              <dt>Conjunto</dt>
              <dd className="hash">
                <code>{result.execution.dataset_id}</code>
              </dd>
              <dt>Inicio del cálculo</dt>
              <dd>
                <time dateTime={result.execution.started_at}>
                  {dateTime(result.execution.started_at)}
                </time>
              </dd>
              <dt>Huella del conjunto</dt>
              <dd className="hash">
                <code>{result.execution.dataset_manifest_hash}</code>
              </dd>
              <dt>Huella de investigación</dt>
              <dd className="hash">
                <code>{result.data_hash}</code>
              </dd>
            </dl>
          </details>
        </section>
      )}
      <div className="stats">
        <Metric
          title="Rentabilidad fuera de muestra"
          value={pct(m.total_return)}
        />
        <Metric title="Frente a mantener" value={pct(m.excess_return)} />
        <Metric title="Máxima caída" value={pct(m.max_drawdown)} />
        <Metric
          title="Sharpe fuera de muestra"
          value={
            m.sharpe == null
              ? 'No definido'
              : number(m.sharpe, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })
          }
        />
      </div>
      <div className="research-panels">
        <section className="panel research-curve">
          <div className="panel-heading">
            <h2>Resultado fuera de muestra</h2>
            <span className="tag">{result.selected_strategy.kind}</span>
          </div>
          <Curve data={result.out_of_sample.curve ?? []} />
          <div className="split-periods">
            {(
              ['train_period', 'validation_period', 'test_period'] as const
            ).map((k, i) => (
              <div key={k}>
                <span>
                  {['Preparación', 'Selección', 'Prueba reservada'][i]}
                </span>
                <strong>
                  {result[k] != null
                    ? date(result[k].start) + ' → ' + date(result[k].end)
                    : 'Periodo no disponible'}
                </strong>
              </div>
            ))}
          </div>
          <p className="muted">
            {number(m.observations, { maximumFractionDigits: 0 })} observaciones
            · {number(m.trade_count, { maximumFractionDigits: 0 })} ejecuciones
            · {money(m.costs)} de costes simulados. Peso máximo:{' '}
            {pct(result.max_position_weight)}.
          </p>
        </section>
        <section className="panel research-comparison">
          <div className="panel-heading">
            <h2>Comparación de candidatos</h2>
            <span className="tag">Validación</span>
          </div>
          <DataTable
            numericColumns={[1, 2, 3]}
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
            numericColumns={[0, 1, 2, 3]}
            heads={['Multiplicador', 'Retorno', 'Exceso', 'Caída']}
            rows={result.sensitivity.map((s) => [
              number(s.cost_multiplier) + '×',
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
      </div>
    </div>
  );
}
