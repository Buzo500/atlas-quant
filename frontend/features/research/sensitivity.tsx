'use client';
import type { SensitivityConfig, SensitivityReport } from '@/lib/api-types';
import { Input } from '@/components/ui/input';
import { Field, DataTable } from '@/shared/ui';
import { number } from '@/shared/format';
import { PeriodResult } from './simulation-result';

export type SensitivityDraft = { fast: string; slow: string; costs: string };
export const initialSensitivity: SensitivityDraft = {
  fast: '',
  slow: '',
  costs: '1, 2',
};
const tokens = (value: string) =>
  value.trim() ? value.split(',').map((v) => v.trim()) : [];
export function sensitivityInput(draft: SensitivityDraft): SensitivityConfig {
  const windows = (value: string) =>
    tokens(value).map((v) => {
      if (!/^\d+$/.test(v))
        throw new Error(
          'Las ventanas de sensibilidad deben ser enteros separados por comas.',
        );
      return Number(v);
    });
  const costs = tokens(draft.costs);
  if (costs.some((v) => !/^\d+(\.\d+)?$/.test(v)))
    throw new Error(
      'Usa punto decimal y comas para separar multiplicadores de costes.',
    );
  return {
    policy: 'atlas-sensitivity-oat-v1',
    fast_windows: windows(draft.fast),
    slow_windows: windows(draft.slow),
    cost_multipliers: costs,
  };
}
const percent = (value: string | null) =>
  value === null
    ? 'No disponible'
    : `${number(Number(value), { maximumFractionDigits: 3 })} %`;
export const caseLabel = (label: string) =>
  label === 'base'
    ? 'Configuración base'
    : label.startsWith('fast:')
      ? `Media rápida ${label.slice(5)}`
      : label.startsWith('slow:')
        ? `Media lenta ${label.slice(5)}`
        : `Costes × ${label.slice(5)}`;

export function SensitivityEditor({
  enabled,
  onEnabled,
  value,
  onChange,
}: {
  enabled: boolean;
  onEnabled: (enabled: boolean) => void;
  value: SensitivityDraft;
  onChange: (draft: SensitivityDraft) => void;
}) {
  return (
    <section aria-label="Configuración de sensibilidad">
      <label className="check-row">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onEnabled(e.target.checked)}
        />{' '}
        Añadir análisis de sensibilidad
      </label>
      {enabled && (
        <>
          <p className="muted">
            Variar un factor cada vez sobre el desarrollo: una media o los
            costes. Sin combinación de ejes ni selección automática. Hasta ocho
            casos distintos incluida la base. Valores separados por comas; punto
            para decimales.
          </p>
          <div className="form-grid">
            <Field label="Ventanas rápidas alternativas">
              <Input
                maxLength={100}
                value={value.fast}
                placeholder="15, 25"
                onChange={(e) => onChange({ ...value, fast: e.target.value })}
              />
            </Field>
            <Field label="Ventanas lentas alternativas">
              <Input
                maxLength={100}
                value={value.slow}
                placeholder="40, 60"
                onChange={(e) => onChange({ ...value, slow: e.target.value })}
              />
            </Field>
            <Field label="Multiplicadores de costes">
              <Input
                maxLength={100}
                value={value.costs}
                placeholder="1, 1.5, 2"
                onChange={(e) => onChange({ ...value, costs: e.target.value })}
              />
            </Field>
          </div>
          <p className="muted">
            Deja vacío un eje para no variarlo. Multiplica comisión fija,
            proporcional y deslizamiento; la comisión fija se redondea hacia
            arriba al céntimo. Capital y límites se conservan. La prueba final
            permanece reservada.
          </p>
        </>
      )}
    </section>
  );
}

export function SensitivityResult({ result }: { result: SensitivityReport }) {
  const summary = result.summary;
  return (
    <section className="panel" aria-label="Resultado de sensibilidad">
      <div className="panel-heading">
        <h2>Sensibilidad en desarrollo</h2>
        <span className="tag neutral">Un factor cada vez</span>
      </div>
      <p>
        {summary.evaluable_cases} de {summary.cases} casos evaluables ·{' '}
        {summary.nonnegative_cases} con rentabilidad neta no negativa.
      </p>
      <p className="muted">
        Rango de retornos SMA: {percent(summary.min_return_pct)} a{' '}
        {percent(summary.max_return_pct)}. Dispersión:{' '}
        {summary.return_spread_pp === null
          ? 'no disponible'
          : `${number(Number(summary.return_spread_pp), { maximumFractionDigits: 3 })} puntos porcentuales`}
        . Peor caída: {percent(summary.worst_drawdown_pct)}. Resumen
        descriptivo, sin aprobar ni elegir una estrategia.
      </p>
      {summary.reasons.length > 0 && (
        <ul>
          {summary.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      <DataTable
        heads={[
          'Caso',
          'SMA',
          'Rentabilidad neta',
          'Caída máxima',
          'Ejecuciones',
          'Evidencia',
        ]}
        numericColumns={[2, 3, 4]}
        rows={result.cases.map((c) => [
          caseLabel(c.label),
          `${c.fast}/${c.slow}`,
          percent(c.result.metrics[0].return_pct),
          percent(c.result.metrics[0].max_drawdown_pct),
          c.result.metrics[0].fills,
          c.evaluable ? 'Evaluable' : 'Insuficiente',
        ])}
      />
      {result.cases.map((c) => (
        <details key={c.label} className="details">
          <summary>Detalle: {caseLabel(c.label)}</summary>
          <p>
            Comisión fija {c.config.fixed_fee_eur} EUR · proporcional{' '}
            {c.config.fee_bps} pb · deslizamiento {c.config.slippage_bps} pb.
          </p>
          {c.reasons.length > 0 && (
            <ul>
              {c.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
          <PeriodResult
            result={c.result}
            title={`Sensibilidad: ${caseLabel(c.label)}`}
          />
        </details>
      ))}
      <details className="details">
        <summary>Supuestos y trazabilidad de sensibilidad</summary>
        <ul>
          {result.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
        <p className="mono native-hash">
          Huella de sensibilidad: {result.report_hash}
        </p>
      </details>
    </section>
  );
}
