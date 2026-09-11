'use client';
import type { WalkForwardConfig, WalkForwardReport } from '@/lib/api-types';
import { Input } from '@/components/ui/input';
import { DataTable, Field } from '@/shared/ui';
import { date, number } from '@/shared/format';
import { PeriodResult } from './simulation-result';

export const initialWalkForward: WalkForwardConfig = {
  policy: 'atlas-walk-forward-fixed-v1',
  context_sessions: 252,
  evaluation_sessions: 63,
  minimum_windows: 3,
  minimum_pass_pct: '60',
  maximum_drawdown_pct: '15',
  minimum_fills: 1,
};
const percentage = (value: string | null) =>
  value === null
    ? 'No disponible'
    : `${number(Number(value), { maximumFractionDigits: 3 })} %`;
const fields = [
  ['context_sessions', 'Sesiones de contexto', 5, 1000],
  ['evaluation_sessions', 'Sesiones por evaluación', 2, 500],
  ['minimum_windows', 'Ventanas mínimas para el diagnóstico', 2, 20],
  ['minimum_fills', 'Ejecuciones SMA mínimas por ventana', 1, 1000],
] as const;

export function WalkForwardEditor({
  enabled,
  onEnabled,
  value,
  onChange,
}: {
  enabled: boolean;
  onEnabled: (value: boolean) => void;
  value: WalkForwardConfig;
  onChange: (value: WalkForwardConfig) => void;
}) {
  return (
    <section aria-label="Configuración walk-forward">
      <label className="check-row">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onEnabled(e.target.checked)}
        />{' '}
        Añadir validación walk-forward
      </label>
      {enabled && (
        <>
          <p className="muted">
            Ventanas móviles dentro del desarrollo, con SMA y costes fijos. Cada
            evaluación empieza en efectivo y usa cierres previos para calentar
            las medias. Mínimo dos ventanas completas; máximo veinte. La prueba
            final permanece reservada.
          </p>
          <div className="form-grid">
            {fields.map(([key, label, min, max]) => (
              <Field key={key} label={label}>
                <Input
                  type="number"
                  required
                  min={min}
                  max={max}
                  step={1}
                  value={value[key] ?? ''}
                  onChange={(e) =>
                    onChange({
                      ...value,
                      [key]:
                        e.target.value === ''
                          ? undefined
                          : Number(e.target.value),
                    })
                  }
                />
              </Field>
            ))}
            <Field label="Ventanas que deben cumplir (%)">
              <Input
                required
                inputMode="decimal"
                maxLength={32}
                value={value.minimum_pass_pct}
                onChange={(e) =>
                  onChange({ ...value, minimum_pass_pct: e.target.value })
                }
              />
            </Field>
            <Field label="Caída máxima permitida (%)">
              <Input
                required
                inputMode="decimal"
                maxLength={32}
                value={value.maximum_drawdown_pct}
                onChange={(e) =>
                  onChange({ ...value, maximum_drawdown_pct: e.target.value })
                }
              />
            </Field>
          </div>
          <p className="muted">
            Además: rentabilidad neta no negativa y al menos igual a
            comprar/mantener. Todas las ventanas deben tener evidencia
            suficiente. Los criterios quedan congelados al guardar; cumplirlos
            no autoriza operaciones.
          </p>
        </>
      )}
    </section>
  );
}

export function WalkForwardResult({ result }: { result: WalkForwardReport }) {
  const summary = result.summary;
  const label = {
    meets_criteria: 'Cumple criterios iniciales',
    does_not_meet: 'No cumple los criterios',
    insufficient_data: 'Evidencia insuficiente',
  }[summary.status];
  return (
    <section className="panel" aria-label="Resultado walk-forward">
      <div className="panel-heading">
        <h2>Validación walk-forward</h2>
        <span
          className={`tag ${summary.status === 'meets_criteria' ? '' : summary.status === 'insufficient_data' ? 'neutral' : 'amber'}`}
        >
          {label}
        </span>
      </div>
      <p>
        {summary.passing_windows} de {summary.windows} ventanas cumplen ·{' '}
        {summary.evaluable_windows} evaluables.
      </p>
      <p className="muted">
        Contexto: {result.config.context_sessions} sesiones · evaluación:{' '}
        {result.config.evaluation_sessions} sesiones. Ventanas de evaluación
        consecutivas sin solapamiento; cuentas independientes.
      </p>
      <DataTable
        heads={['Resumen de ventanas evaluables', 'Valor']}
        numericColumns={[1]}
        rows={[
          [
            'Media aritmética de rentabilidades SMA',
            percentage(summary.mean_return_pct),
          ],
          [
            'Media del exceso frente a comprar/mantener (puntos porcentuales)',
            summary.mean_excess_pct === null
              ? 'No disponible'
              : number(Number(summary.mean_excess_pct), {
                  maximumFractionDigits: 3,
                }),
          ],
          ['Peor caída máxima SMA', percentage(summary.worst_drawdown_pct)],
          [
            'Proporción que cumple sobre todas las ventanas',
            percentage(summary.passing_pct),
          ],
        ]}
      />
      {summary.reasons.length > 0 && (
        <ul>
          {summary.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      <DataTable
        heads={[
          'Ventana',
          'Contexto',
          'Evaluación',
          'SMA neta',
          'Comprar/mantener',
          'Caída SMA',
          'Ejecuciones SMA',
          'Diagnóstico',
        ]}
        numericColumns={[3, 4, 5, 6]}
        rows={result.windows.map((w) => [
          w.index,
          `${date(w.context_start)} → ${date(w.context_end)}`,
          `${date(w.evaluation.start_date)} → ${date(w.evaluation.end_date)}`,
          percentage(w.evaluation.metrics[0].return_pct),
          percentage(w.evaluation.metrics[1].return_pct),
          percentage(w.evaluation.metrics[0].max_drawdown_pct),
          w.evaluation.metrics[0].fills,
          !w.evaluable
            ? 'Evidencia insuficiente'
            : w.passed
              ? 'Cumple'
              : 'No cumple',
        ])}
      />
      <p className="muted">
        {result.unused_sessions} sesiones al final del desarrollo sin evaluar
        por no completar otra ventana.
        {result.unused_start &&
          result.unused_end &&
          ` ${date(result.unused_start)} → ${date(result.unused_end)}.`}
      </p>
      {result.windows.map((w) => (
        <details key={w.index} className="details">
          <summary>Detalle de la ventana {w.index}</summary>
          <p>
            Calentamiento: {w.warmup_sessions} cierres desde{' '}
            {date(w.warmup_start)}. Sin operaciones durante el calentamiento.
          </p>
          {w.reasons.length > 0 && (
            <ul>
              {w.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
          <DataTable
            heads={[
              'Referencia en el contexto previo',
              'Rentabilidad',
              'Caída máxima',
            ]}
            numericColumns={[1, 2]}
            rows={w.context_metrics.map((m) => [
              m.name,
              percentage(m.return_pct),
              percentage(m.max_drawdown_pct),
            ])}
          />
          <p className="muted">
            El contexto es una simulación histórica independiente, sin ajuste de
            parámetros.
          </p>
          <PeriodResult
            result={w.evaluation}
            title={`Evaluación de la ventana ${w.index}`}
          />
        </details>
      ))}
      <details className="details">
        <summary>Criterios congelados y límites de interpretación</summary>
        <p>
          Mínimo {result.config.minimum_windows} ventanas;{' '}
          {result.config.minimum_pass_pct} % deben cumplir. Al menos{' '}
          {result.config.minimum_fills} ejecuciones SMA por ventana; caída
          máxima ≤ {result.config.maximum_drawdown_pct} %, retorno neto ≥ 0 y ≥
          comprar/mantener. Todas las ventanas deben ser evaluables.
        </p>
        <ul>
          {result.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
        <p className="mono native-hash">
          Huella walk-forward: {result.report_hash}
        </p>
      </details>
    </section>
  );
}
