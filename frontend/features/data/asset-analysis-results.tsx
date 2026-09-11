'use client';
import { useState } from 'react';
import type { AssetAnalysisReport } from '@/lib/api-types';
import { Choice, DataTable } from '@/shared/ui';

const reasons: Record<string, string> = {
  calendar_unverified_or_outside_coverage:
    'Calendario sin verificar o fuera de cobertura.',
  raw_price_basis_required:
    'Se necesitan precios brutos con su base verificada.',
  known_corporate_adjustment_required:
    'Hay un evento corporativo que requiere ajustar la serie.',
  missing_price_session: 'Faltan precios de sesiones abiertas.',
  unexpected_price_session: 'Hay precios fuera de las sesiones declaradas.',
  missing_fx_series: 'Falta una serie de cambio EUR por USD.',
  missing_same_date_fx: 'Falta un cambio válido de la misma fecha.',
  availability_unknown: 'No consta cuándo estuvo disponible el dato.',
  available_after_decision: 'El dato estuvo disponible después del corte.',
  insufficient_sessions: 'Se necesitan al menos dos sesiones.',
  insufficient_common_dates: 'No hay dos fechas válidas comunes.',
  insufficient_common_intervals: 'Se necesitan al menos 20 intervalos comunes.',
  constant_return_series:
    'La correlación no está definida para variaciones constantes.',
  calendar_unknown: 'No hay evidencia suficiente del calendario.',
  missing_session: 'Falta una sesión.',
  stale_mark: 'El precio no corresponde a la sesión requerida.',
  missing_fx: 'Falta un cambio válido.',
  missing_price: 'Falta un precio válido.',
  unexpected_bar: 'Hay un precio fuera del calendario.',
  price_basis_incompatible: 'La base del precio es incompatible.',
};
export const analysisReason = (code: string) =>
  reasons[code] || 'La fuente no cumple los requisitos de este análisis.';
export const analyticalNumber = (value: string | null, suffix = '') =>
  value === null
    ? '—'
    : Number(value).toLocaleString('es-ES', { maximumFractionDigits: 4 }) +
      suffix;

export function AssetAnalysisResults({
  report,
}: {
  report: AssetAnalysisReport;
}) {
  const { profiles, comparison, correlations, fx } = report.result;
  const [selected, setSelected] = useState(profiles[0]?.source.key || '');
  const profile = profiles.find((p) => p.source.key === selected);
  const label = (key: string) => {
    const i = profiles.findIndex((p) => p.source.key === key);
    return `${i + 1}. ${profiles[i]?.source.name || key}`;
  };
  return (
    <section
      aria-label="Resultado del comparador"
      className="asset-analysis-results"
    >
      <h3>Fichas de activos · EUR</h3>
      <p>
        {report.inputs.start_date} — {report.inputs.end_date}. Evolución del
        precio: excluye dividendos, costes e impuestos.
      </p>
      <p>
        {report.saved ? 'Informe guardado' : 'Vista previa'} ·{' '}
        {report.current
          ? 'Contexto vigente'
          : 'Las fuentes o el catálogo han cambiado'}
      </p>
      <DataTable
        heads={[
          'Activo / fuente',
          'Sesiones válidas',
          'Último cierre EUR',
          'Variación del periodo',
          'Vol. por sesión',
          'Vol. anualizada',
          'Caída máxima',
          'Cobertura',
        ]}
        numericColumns={[1, 2, 3, 4, 5, 6]}
        rows={profiles.map((p) => [
          `${label(p.source.key)} · ${p.source.dataset_name} · v${p.source.ref.version}`,
          `${p.valid_sessions} / ${p.expected_sessions}`,
          analyticalNumber(p.last_close_eur),
          analyticalNumber(p.price_change_pct, ' %'),
          analyticalNumber(p.session_volatility_pct, ' %'),
          analyticalNumber(p.annualized_volatility_pct, ' %'),
          analyticalNumber(p.max_drawdown_pct, ' %'),
          p.status === 'complete'
            ? 'Completa'
            : p.status === 'partial'
              ? 'Parcial'
              : 'No disponible',
        ])}
      />
      <p className="muted">
        Volatilidad muestral: mínimo dos intervalos. La anualización usa la
        convención de 252 sesiones, no una previsión.
      </p>
      <details>
        <summary>Detalle y procedencia de una ficha</summary>
        <Choice
          label="Ficha del activo"
          value={selected}
          onChange={setSelected}
          options={profiles.map((p) => ({
            value: p.source.key,
            label: label(p.source.key),
          }))}
        />
        {profile && (
          <>
            <DataTable
              heads={['Dato', 'Valor']}
              rows={[
                ['Instrumento', profile.source.instrument_id],
                ['Tipo', profile.source.instrument_type],
                [
                  'Mercado / moneda',
                  `${profile.source.market || 'Sin declarar'} / ${profile.source.currency}`,
                ],
                ['Procedencia', profile.source.source],
                [
                  'Fechas observadas',
                  `${profile.first_date || '—'} — ${profile.last_date || '—'}`,
                ],
                [
                  'Último precio recibido en moneda original (puede no estar validado)',
                  analyticalNumber(profile.last_close_native),
                ],
                ['Intervalos válidos', profile.valid_intervals],
                [
                  'Dividendos conocidos, excluidos del cálculo',
                  profile.known_dividends,
                ],
                [
                  'Huella de la fuente',
                  <code key="sha">{profile.source.sha256}</code>,
                ],
              ]}
            />
            {profile.reasons.length > 0 && (
              <ul>
                {profile.reasons.map((r) => (
                  <li key={r}>{analysisReason(r)}</li>
                ))}
              </ul>
            )}
          </>
        )}
      </details>
      <h3>Comparación sobre fechas comunes</h3>
      <p>
        {comparison.start_date
          ? `${comparison.start_date} — ${comparison.end_date} · ${comparison.points.length} fechas comunes`
          : 'No hay dos fechas válidas comunes.'}
      </p>
      <p className="muted">
        Solo fechas observadas en todas las fuentes; no se rellenan huecos. Este
        tramo puede ser más corto que el periodo solicitado.
      </p>
      {comparison.reasons.includes('partial_source_coverage') && (
        <p role="note">
          Cobertura parcial: la comparación no representa todo el periodo.
        </p>
      )}
      <DataTable
        heads={['Activo', 'Inicio EUR', 'Fin EUR', 'Variación del precio']}
        numericColumns={[1, 2, 3]}
        rows={comparison.rows.map((r) => [
          label(r.source_key),
          analyticalNumber(r.start_eur),
          analyticalNumber(r.end_eur),
          analyticalNumber(r.price_change_pct, ' %'),
        ])}
      />
      <details>
        <summary>Índices de precio · base 100</summary>
        <DataTable
          heads={['Fecha', ...profiles.map((p) => label(p.source.key))]}
          numericColumns={profiles.map((_, i) => i + 1)}
          rows={comparison.points.map((p) => [
            p.date,
            ...p.indices.map((v) => analyticalNumber(v)),
          ])}
        />
      </details>
      <h3>Correlaciones de variaciones en EUR</h3>
      <p>
        Pearson · {correlations.observations} intervalos idénticos para todos
        los activos · mínimo {correlations.minimum_observations}.
      </p>
      <p className="muted">
        Entre sesiones consecutivas del calendario de cada fuente. Una sesión
        abierta sin dato interrumpe el intervalo. La correlación histórica no
        predice el comportamiento futuro.
      </p>
      <DataTable
        heads={['Activo', ...profiles.map((p) => label(p.source.key))]}
        numericColumns={profiles.map((_, i) => i + 1)}
        rows={profiles.map((p) => [
          label(p.source.key),
          ...profiles.map((q) => {
            const c = correlations.cells.find(
              (cell) =>
                cell.left === p.source.key && cell.right === q.source.key,
            );
            const value = analyticalNumber(c?.value ?? null);
            return (
              <span
                key={q.source.key}
                title={c?.reason ? analysisReason(c.reason) : value}
                aria-label={`${label(p.source.key)} con ${label(q.source.key)}: ${c?.reason ? analysisReason(c.reason) : value}`}
              >
                {value}
              </span>
            );
          }),
        ])}
      />
      {correlations.reasons.includes('partial_source_coverage') && (
        <p>
          Cobertura parcial: la matriz utiliza únicamente los intervalos válidos
          comunes.
        </p>
      )}
      <ul>
        {[
          ...new Set(
            correlations.cells.flatMap((c) => (c.reason ? [c.reason] : [])),
          ),
        ].map((r) => (
          <li key={r}>{analysisReason(r)}</li>
        ))}
      </ul>
      <details>
        <summary>Muestra y fuentes del análisis</summary>
        <DataTable
          heads={['Inicio del intervalo', 'Fin del intervalo']}
          rows={correlations.intervals.map((i) => [i.start_date, i.end_date])}
        />
        <p>
          {fx
            ? `Cambio EUR por USD: ${fx.name} · v${fx.ref.version} · ${fx.source}`
            : 'Sin fuente de cambio seleccionada.'}
        </p>
        {fx && <code>{fx.sha256}</code>}
        <p>
          No se infieren eventos corporativos ausentes de las fuentes. Las
          métricas dependen de la evidencia declarada.
        </p>
        <pre className="asset-analysis-trace">
          {JSON.stringify(
            {
              policy: report.policy,
              context: report.context_hash,
              catalog_revision: report.catalog_revision,
              corporate_revision: report.corporate_revision,
              inputs: report.inputs,
            },
            null,
            2,
          )}
        </pre>
      </details>
    </section>
  );
}
