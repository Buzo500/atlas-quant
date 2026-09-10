'use client';

import { useState } from 'react';
import type {
  ValuationPreview,
  ValuationCut,
  ValuationHistory,
  Mark,
} from '@/lib/api-types';
import { useRead } from '@/shared/use-read';
import { QueryStatus } from '@/shared/query-status';
import { Field, Metric, DataTable } from '@/shared/ui';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useCorporateReview } from '@/features/data/corporate-shared';

export const valuationStatus = {
  complete: 'Completo',
  provisional: 'Provisional',
  incomplete: 'Incompleto',
};
const reasons: Record<string, string> = {
  missing_fx: 'Falta un tipo de cambio válido',
  missing_price: 'Falta un precio válido',
  stale_mark: 'La marca provisional supera 7 días',
  calendar_unknown: 'Calendario o cobertura sin acreditar',
  missing_session: 'Falta una sesión esperada',
  unexpected_bar: 'Observación en un día cerrado acreditado',
  price_basis_incompatible: 'Falta una base de precios bruta acreditada',
  corporate_action_unresolved: 'Evento corporativo pendiente de revisión',
  availability_unknown: 'Disponibilidad histórica desconocida',
  available_after_decision: 'Observación disponible después de la decisión',
  corporate_availability_unknown:
    'Disponibilidad histórica del evento desconocida',
  corporate_available_after_decision:
    'Evento disponible después de la decisión',
  reconstruction_incomplete: 'La reconstrucción está incompleta',
};
export const reasonText = (code: string) => reasons[code] || code;
const markText = (mark: Mark | null) =>
  mark
    ? `${mark.value ?? '—'} · ${mark.date ?? 'sin fecha'} · ${mark.source ?? 'sin fuente'} · v${mark.version ?? '—'}`
    : 'No necesario';

export function ValuationDetails({ cut }: { cut: ValuationCut }) {
  return (
    <section aria-label="Detalle de patrimonio">
      <div className="stats portfolio-stats">
        <Metric
          title={`Patrimonio EUR · ${valuationStatus[cut.status]}`}
          value={cut.value === null ? 'No disponible' : cut.value + ' EUR'}
        />
        <Metric title="Fecha de cierre" value={cut.as_of_date} />
        <Metric title="Subtotal conocido" value={cut.known_subtotal + ' EUR'} />
      </div>
      <p className="muted">
        Reconstrucción contable con las versiones elegidas.{' '}
        {!cut.saved
          ? 'Contexto comprobado al calcular; se comprobará de nuevo al guardar.'
          : cut.current
            ? 'Contexto vigente en la última consulta.'
            : 'El contexto ha cambiado: se conserva este corte histórico.'}{' '}
        {cut.status === 'incomplete'
          ? 'El subtotal conocido no es el patrimonio total.'
          : ''}
      </p>
      {!!cut.reasons.length && (
        <p className="notice">{cut.reasons.map(reasonText).join('. ')}.</p>
      )}
      <DataTable
        heads={[
          'Componente',
          'Referencia',
          'Moneda',
          'Cantidad',
          'Valor nativo',
          'Valor EUR',
          'Precio / fecha / fuente',
          'FX EUR por USD / fecha / fuente',
          'Estado',
        ]}
        numericColumns={[3, 4, 5]}
        rows={cut.components.map((c) => [
          c.kind === 'cash'
            ? 'Efectivo'
            : c.kind === 'position'
              ? 'Posición'
              : 'Derecho pendiente',
          <code key="ref" title={c.reference}>
            {c.reference.slice(0, 12)}
          </code>,
          c.currency,
          c.quantity ?? '—',
          c.native_value ?? '—',
          c.display_eur ?? '—',
          markText(c.price),
          markText(c.fx),
          `${valuationStatus[c.status]}${c.reasons.length ? ' · ' + c.reasons.map(reasonText).join('; ') : ''}`,
        ])}
      />
      <p className="muted">
        El total se redondea una sola vez. Diferencia frente a sumar filas
        redondeadas: {cut.rounding_difference} EUR.
      </p>
      <details className="details">
        <summary>Flujos externos y disponibilidad histórica</summary>
        <p>
          Este corte{' '}
          {cut.historical_known
            ? 'tiene disponibilidad acreditada para la fecha de decisión indicada'
            : 'no acredita qué información estaba disponible para una decisión histórica'}
          .
        </p>
        <p className="muted">
          Decisión consultada: {cut.decision_at}.{' '}
          {cut.historical_reasons.map(reasonText).join('. ')}
        </p>
        <DataTable
          heads={[
            'Fecha',
            'Movimiento',
            'Moneda',
            'Flujo nativo',
            'Equivalente EUR',
            'FX aplicado',
            'Estado',
          ]}
          rows={cut.flows.map((f) => [
            f.date,
            <code key="id" title={f.event_id}>
              {f.event_id.slice(0, 12)}
            </code>,
            f.currency,
            f.native_amount,
            f.eur_amount ?? 'No disponible',
            markText(f.fx),
            valuationStatus[f.status],
          ])}
        />
      </details>
      <details className="details">
        <summary>Identificación del corte</summary>
        <p className="muted">
          Libro r{cut.portfolio_revision} · catálogo r{cut.catalog_revision} ·
          eventos r{cut.corporate_revision} · {cut.policy}
        </p>
        <p className="native-hash">
          <code>{cut.context_hash}</code>
        </p>
      </details>
    </section>
  );
}

export function NativeValuation({
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
  const [day, setDay] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState('');
  const [selected, setSelected] = useState('');
  const [offset, setOffset] = useState(0);
  const history = useRead<ValuationHistory>({
    path: `/v2/portfolios/${portfolioId}/valuations?offset=${offset}&limit=20`,
    revision: `${revision}:${auditSequence}`,
    enabled: active,
  });
  const saved = useRead<ValuationCut>({
    path: selected
      ? `/v2/portfolios/${portfolioId}/valuations/${selected}`
      : null,
    revision: `${revision}:${auditSequence}`,
    enabled: active,
  });
  const operation = useCorporateReview<ValuationPreview>(
    `/v2/portfolios/${portfolioId}/valuations`,
    async () => {
      await history.refresh();
    },
    setError,
  );
  const value =
    operation.preview?.cut ??
    (selected && saved.data?.id === selected ? saved.data : null);
  return (
    <section className="panel native-valuation" aria-label="Patrimonio en EUR">
      <div className="panel-heading">
        <h2>Patrimonio en EUR</h2>
        <span className="tag neutral">Corte diario · fuentes versionadas</span>
      </div>
      <form
        className="form-grid"
        onSubmit={(e) => {
          e.preventDefault();
          setSelected('');
          void operation.review({
            as_of_date: day,
            expected_revision: revision,
          });
        }}
      >
        <Field label="Fecha de valoración">
          <Input
            type="date"
            required
            value={day}
            max={new Date().toISOString().slice(0, 10)}
            onChange={(e) => {
              operation.invalidate();
              setSelected('');
              setDay(e.target.value);
            }}
          />
        </Field>
        <Button type="submit" disabled={operation.busy}>
          Calcular patrimonio
        </Button>
      </form>
      {error && (
        <p className="notice" role="alert">
          {error}
        </p>
      )}
      {selected && <QueryStatus label="Corte guardado" query={saved} />}
      {value && <ValuationDetails cut={value} />}
      {operation.preview && (
        <Button
          disabled={operation.busy}
          onClick={() => void operation.confirm()}
        >
          Guardar corte de patrimonio
        </Button>
      )}
      {operation.message && <output>{operation.message}</output>}
      <details className="details">
        <summary>Cortes guardados</summary>
        <QueryStatus label="Historial de patrimonio" query={history} />
        {history.data && (
          <>
            <DataTable
              heads={['Fecha', 'Libro', 'Estado', 'Patrimonio EUR', 'Acción']}
              rows={history.data.cuts.map((c) => [
                c.as_of_date,
                c.portfolio_revision,
                valuationStatus[c.status],
                c.value ?? 'No disponible',
                <Button
                  variant="outline"
                  key={c.id}
                  onClick={() => {
                    operation.invalidate();
                    setSelected(c.id);
                  }}
                >
                  Consultar corte {c.as_of_date}
                </Button>,
              ])}
            />
            <div className="actions">
              <Button
                variant="outline"
                disabled={offset === 0 || history.loading}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Cortes anteriores
              </Button>
              <Button
                variant="outline"
                disabled={history.data.cuts.length < 20 || history.loading}
                onClick={() => setOffset(offset + 20)}
              >
                Más cortes
              </Button>
            </div>
          </>
        )}
      </details>
    </section>
  );
}
